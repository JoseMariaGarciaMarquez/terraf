"""
TERRAF Inversión Geofísica
Módulo para inversión de datos geofísicos (magnetometría, gravimetría, etc.)
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize, least_squares
from scipy.spatial.distance import cdist
import warnings

class TerrafInv:
    """
    Clase para inversión geofísica de datos magnéticos y gravimétricos
    
    Métodos disponibles:
    - Deconvolución de Euler (localización de fuentes)
    - Inversión de susceptibilidad magnética 3D
    - Modelado directo (forward modeling)
    - Inversión conjunta con datos espectrales
    """
    
    def __init__(self):
        """
        Inicializa el módulo de inversión
        """
        self.datos_observados = None
        self.modelo = None
        self.residuales = None
        self.parametros = {}
    
    # ========================================================================
    # DECONVOLUCIÓN DE EULER
    # ========================================================================
    
    def euler_deconvolution(self, x, y, mag, dx_mag, dy_mag, dz_mag, 
                           structural_index=1.0, ventana=5):
        """
        Deconvolución de Euler para localizar fuentes magnéticas
        
        Resuelve: (x-x0)∂T/∂x + (y-y0)∂T/∂y + (z-z0)∂T/∂z = N(B-T)
        
        Args:
            x, y (np.ndarray): Coordenadas de observación
            mag (np.ndarray): Campo magnético total
            dx_mag, dy_mag, dz_mag (np.ndarray): Derivadas del campo
            structural_index (float): Índice estructural (0=contacto, 1=dique, 2=cilindro, 3=esfera)
            ventana (int): Tamaño de ventana para solución móvil (puntos)
        
        Returns:
            pd.DataFrame: Soluciones de Euler (x0, y0, z0, base_level)
        """
        print(f"\n🧮 Deconvolución de Euler")
        print(f"   Índice estructural: {structural_index}")
        print(f"   Ventana: {ventana} puntos")
        
        soluciones = []
        
        # Crear grilla de ventanas
        n = len(x)
        for i in range(0, n - ventana, ventana // 2):
            # Ventana de datos
            idx = slice(i, min(i + ventana, n))
            
            x_w = x[idx]
            y_w = y[idx]
            T_w = mag[idx]
            dTdx_w = dx_mag[idx]
            dTdy_w = dy_mag[idx]
            dTdz_w = dz_mag[idx]
            
            # Saltar si hay NaN
            if np.any(np.isnan([x_w, y_w, T_w, dTdx_w, dTdy_w, dTdz_w])):
                continue
            
            # Matriz de diseño: [dT/dx, dT/dy, dT/dz, -N]
            N = structural_index
            A = np.column_stack([dTdx_w, dTdy_w, dTdz_w, np.full(len(x_w), -N)])
            
            # Vector de datos: [x*dT/dx + y*dT/dy + z*dT/dz]
            # Asumir z=0 para observaciones en superficie
            b = x_w * dTdx_w + y_w * dTdy_w + 0 * dTdz_w
            
            # Resolver sistema (mínimos cuadrados)
            try:
                sol = np.linalg.lstsq(A, b, rcond=None)[0]
                
                x0, y0, z0, base = sol
                
                # Filtrar soluciones no físicas
                if z0 > 0 and z0 < 5000:  # Profundidad entre 0 y 5 km
                    # Calcular error
                    residual = np.linalg.norm(A @ sol - b)
                    
                    soluciones.append({
                        'x0': x0,
                        'y0': y0,
                        'z0': z0,
                        'base_level': base,
                        'residual': residual,
                        'n_points': len(x_w)
                    })
            except:
                continue
        
        df_euler = pd.DataFrame(soluciones)
        
        if len(df_euler) > 0:
            print(f"   ✅ {len(df_euler)} soluciones encontradas")
            print(f"   Profundidad media: {df_euler['z0'].mean():.1f} m")
            print(f"   Profundidad min/max: {df_euler['z0'].min():.1f} / {df_euler['z0'].max():.1f} m")
        else:
            print(f"   ⚠️  No se encontraron soluciones válidas")
        
        return df_euler
    
    # ========================================================================
    # MODELADO DIRECTO (FORWARD MODELING)
    # ========================================================================
    
    def forward_magnetic_sphere(self, x_obs, y_obs, z_obs, x_src, y_src, z_src, 
                                radius, susceptibility, inclination=45, declination=0):
        """
        Calcula anomalía magnética de una esfera (modelado directo)
        
        Args:
            x_obs, y_obs, z_obs (np.ndarray): Coordenadas de observación
            x_src, y_src, z_src (float): Centro de la esfera
            radius (float): Radio de la esfera (m)
            susceptibility (float): Susceptibilidad magnética (SI)
            inclination (float): Inclinación del campo magnético (grados)
            declination (float): Declinación del campo magnético (grados)
        
        Returns:
            np.ndarray: Anomalía magnética calculada (nT)
        """
        # Convertir ángulos a radianes
        inc_rad = np.radians(inclination)
        dec_rad = np.radians(declination)
        
        # Vector de magnetización
        Mx = susceptibility * np.cos(inc_rad) * np.cos(dec_rad)
        My = susceptibility * np.cos(inc_rad) * np.sin(dec_rad)
        Mz = susceptibility * np.sin(inc_rad)
        
        # Distancias
        dx = x_obs - x_src
        dy = y_obs - y_src
        dz = z_obs - z_src
        r = np.sqrt(dx**2 + dy**2 + dz**2)
        
        # Evitar división por cero
        r = np.maximum(r, 1.0)
        
        # Volumen de la esfera
        V = (4/3) * np.pi * radius**3
        
        # Momento magnético
        m = V * susceptibility
        
        # Componente vertical de la anomalía (simplificado)
        # T ≈ (2πμ₀/4π) * m * (3cos²(θ) - 1) / r³
        cos_theta = dz / r
        
        # Constante magnética μ₀ = 4π × 10^-7 T·m/A
        # Conversión a nT: × 10^9
        mu_0 = 4 * np.pi * 1e-7
        factor = (mu_0 * 1e9) / (4 * np.pi)
        
        anomaly = factor * m * (3 * cos_theta**2 - 1) / r**3
        
        return anomaly
    
    def forward_magnetic_prism(self, x_obs, y_obs, z_obs, prism_params, susceptibility,
                               inclination=45, declination=0):
        """
        Calcula anomalía magnética de un prisma rectangular (modelado directo)
        
        Args:
            x_obs, y_obs, z_obs (np.ndarray): Coordenadas de observación
            prism_params (dict): {'x1', 'x2', 'y1', 'y2', 'z1', 'z2'}
            susceptibility (float): Susceptibilidad magnética (SI)
            inclination, declination (float): Ángulos del campo (grados)
        
        Returns:
            np.ndarray: Anomalía magnética (nT)
        """
        # Extraer límites del prisma
        x1, x2 = prism_params['x1'], prism_params['x2']
        y1, y2 = prism_params['y1'], prism_params['y2']
        z1, z2 = prism_params['z1'], prism_params['z2']
        
        # Aproximación: descomponer en múltiples fuentes puntuales
        nx, ny, nz = 3, 3, 3
        x_grid = np.linspace(x1, x2, nx)
        y_grid = np.linspace(y1, y2, ny)
        z_grid = np.linspace(z1, z2, nz)
        
        anomaly_total = np.zeros_like(x_obs)
        
        # Volumen de cada subcubo
        dV = ((x2-x1)/nx) * ((y2-y1)/ny) * ((z2-z1)/nz)
        
        for xi in x_grid:
            for yi in y_grid:
                for zi in z_grid:
                    # Simular como esfera equivalente
                    r_equiv = (3 * dV / (4 * np.pi))**(1/3)
                    anomaly = self.forward_magnetic_sphere(
                        x_obs, y_obs, z_obs, xi, yi, zi,
                        r_equiv, susceptibility, inclination, declination
                    )
                    anomaly_total += anomaly
        
        return anomaly_total
    
    # ========================================================================
    # INVERSIÓN DE SUSCEPTIBILIDAD MAGNÉTICA 3D
    # ========================================================================
    
    def inversion_susceptibility_3d(self, x_obs, y_obs, mag_obs, 
                                    mesh_params, inclination=45, declination=0,
                                    alpha=1.0, max_iter=50):
        """
        Inversión 3D de susceptibilidad magnética usando mínimos cuadrados regularizados
        
        Args:
            x_obs, y_obs (np.ndarray): Coordenadas de observación
            mag_obs (np.ndarray): Anomalía magnética observada (nT)
            mesh_params (dict): Parámetros de la malla 3D
                {'nx', 'ny', 'nz', 'dx', 'dy', 'dz', 'z_top'}
            inclination, declination (float): Ángulos del campo (grados)
            alpha (float): Parámetro de regularización
            max_iter (int): Iteraciones máximas
        
        Returns:
            dict: Modelo 3D de susceptibilidad
        """
        print(f"\n🔄 Inversión 3D de susceptibilidad magnética")
        print(f"   Observaciones: {len(x_obs)}")
        print(f"   Malla: {mesh_params['nx']}×{mesh_params['ny']}×{mesh_params['nz']}")
        print(f"   Regularización α: {alpha}")
        
        # Crear malla 3D
        nx, ny, nz = mesh_params['nx'], mesh_params['ny'], mesh_params['nz']
        dx, dy, dz = mesh_params['dx'], mesh_params['dy'], mesh_params['dz']
        z_top = mesh_params['z_top']
        
        # Centros de celdas
        x_cells = np.linspace(x_obs.min(), x_obs.max(), nx)
        y_cells = np.linspace(y_obs.min(), y_obs.max(), ny)
        z_cells = np.linspace(z_top, z_top + nz*dz, nz)
        
        X_cells, Y_cells, Z_cells = np.meshgrid(x_cells, y_cells, z_cells, indexing='ij')
        X_cells = X_cells.flatten()
        Y_cells = Y_cells.flatten()
        Z_cells = Z_cells.flatten()
        
        n_cells = len(X_cells)
        n_obs = len(x_obs)
        
        print(f"   Celdas del modelo: {n_cells}")
        print(f"   Construyendo matriz de sensibilidad...")
        
        # Matriz de sensibilidad (kernel)
        # Cada fila: respuesta de una celda en todas las observaciones
        G = np.zeros((n_obs, n_cells))
        
        # Volumen de celda
        cell_volume = dx * dy * dz
        
        # Calcular kernel (simplificado - esfera equivalente)
        for j in range(n_cells):
            if j % 1000 == 0:
                print(f"      Procesando celda {j}/{n_cells}...")
            
            # Radio equivalente de la celda
            r_equiv = (3 * cell_volume / (4 * np.pi))**(1/3)
            
            # Anomalía por susceptibilidad unitaria
            anomaly = self.forward_magnetic_sphere(
                x_obs, y_obs, np.zeros_like(x_obs),
                X_cells[j], Y_cells[j], Z_cells[j],
                r_equiv, 1.0, inclination, declination
            )
            
            G[:, j] = anomaly
        
        print(f"   ✅ Matriz de sensibilidad construida: {G.shape}")
        
        # Inversión con regularización de Tikhonov
        # (G^T G + α I) m = G^T d
        print(f"   Resolviendo sistema regularizado...")
        
        GTG = G.T @ G
        GTd = G.T @ mag_obs
        
        # Matriz de regularización (suavidad)
        L = np.eye(n_cells)
        
        # Sistema regularizado
        A_reg = GTG + alpha * L
        
        # Resolver
        susceptibility = np.linalg.solve(A_reg, GTd)
        
        # Calcular ajuste
        mag_calc = G @ susceptibility
        residuales = mag_obs - mag_calc
        rms = np.sqrt(np.mean(residuales**2))
        
        print(f"   ✅ Inversión completada")
        print(f"   RMS residual: {rms:.2f} nT")
        print(f"   Susceptibilidad min/max: {susceptibility.min():.4f} / {susceptibility.max():.4f} SI")
        
        # Reorganizar en 3D
        susceptibility_3d = susceptibility.reshape((nx, ny, nz))
        
        resultado = {
            'susceptibility_3d': susceptibility_3d,
            'x_cells': x_cells,
            'y_cells': y_cells,
            'z_cells': z_cells,
            'mag_calculated': mag_calc,
            'residuals': residuales,
            'rms': rms,
            'G_matrix': G
        }
        
        return resultado
    
    # ========================================================================
    # INVERSIÓN CONJUNTA (MAGNÉTICA + ESPECTRAL)
    # ========================================================================
    
    def inversion_conjunta(self, mag_data, spectral_data, weights={'mag': 0.5, 'spec': 0.5}):
        """
        Inversión conjunta de datos magnéticos y espectrales
        
        Combina información magnética (estructuras en profundidad) con
        información espectral (alteraciones en superficie)
        
        Args:
            mag_data (dict): {'x', 'y', 'mag', 'derivadas'}
            spectral_data (dict): {'x', 'y', 'indices': {'CMR', 'GOSSAN', etc.}}
            weights (dict): Pesos para cada tipo de dato
        
        Returns:
            dict: Modelo integrado de prospectividad
        """
        print(f"\n🔗 Inversión Conjunta (Magnética + Espectral)")
        print(f"   Peso magnético: {weights['mag']:.2f}")
        print(f"   Peso espectral: {weights['spec']:.2f}")
        
        # Extraer datos
        x_mag = mag_data['x']
        y_mag = mag_data['y']
        mag = mag_data['mag']
        
        x_spec = spectral_data['x']
        y_spec = spectral_data['y']
        indices = spectral_data['indices']
        
        # Interpolar datos a una grilla común
        from scipy.interpolate import griddata
        
        # Definir grilla común
        x_min = max(x_mag.min(), x_spec.min())
        x_max = min(x_mag.max(), x_spec.max())
        y_min = max(y_mag.min(), y_spec.min())
        y_max = min(y_mag.max(), y_spec.max())
        
        nx, ny = 100, 100
        x_grid = np.linspace(x_min, x_max, nx)
        y_grid = np.linspace(y_min, y_max, ny)
        X_grid, Y_grid = np.meshgrid(x_grid, y_grid)
        
        print(f"   Grilla común: {nx}×{ny}")
        
        # Interpolar magnética
        mag_grid = griddata((x_mag, y_mag), mag, (X_grid, Y_grid), method='linear')
        
        # Normalizar magnética (0-1)
        mag_norm = (mag_grid - np.nanmin(mag_grid)) / (np.nanmax(mag_grid) - np.nanmin(mag_grid))
        
        # Interpolar índices espectrales y combinar
        spec_combined = np.zeros_like(mag_grid)
        n_indices = 0
        
        for idx_name, idx_values in indices.items():
            idx_grid = griddata((x_spec, y_spec), idx_values, (X_grid, Y_grid), method='linear')
            
            if not np.all(np.isnan(idx_grid)):
                # Normalizar
                idx_norm = (idx_grid - np.nanmin(idx_grid)) / (np.nanmax(idx_grid) - np.nanmin(idx_grid))
                spec_combined += idx_norm
                n_indices += 1
        
        if n_indices > 0:
            spec_combined /= n_indices
        
        # Combinar con pesos
        prospectivity = weights['mag'] * mag_norm + weights['spec'] * spec_combined
        
        # Normalizar resultado final
        prospectivity = (prospectivity - np.nanmin(prospectivity)) / (np.nanmax(prospectivity) - np.nanmin(prospectivity))
        
        print(f"   ✅ Inversión conjunta completada")
        print(f"   Prospectividad: {np.nanmin(prospectivity):.3f} - {np.nanmax(prospectivity):.3f}")
        
        resultado = {
            'x_grid': X_grid,
            'y_grid': Y_grid,
            'prospectivity': prospectivity,
            'mag_component': mag_norm,
            'spectral_component': spec_combined
        }
        
        return resultado
    
    # ========================================================================
    # UTILIDADES
    # ========================================================================
    
    def calcular_rms(self, observado, calculado):
        """
        Calcula RMS entre datos observados y calculados
        
        Args:
            observado (np.ndarray): Datos observados
            calculado (np.ndarray): Datos calculados
        
        Returns:
            float: RMS
        """
        residuales = observado - calculado
        rms = np.sqrt(np.mean(residuales**2))
        return rms
    
    def filtro_profundidad(self, soluciones_euler, z_min=0, z_max=5000):
        """
        Filtra soluciones de Euler por profundidad
        
        Args:
            soluciones_euler (pd.DataFrame): Soluciones de Euler
            z_min, z_max (float): Límites de profundidad (m)
        
        Returns:
            pd.DataFrame: Soluciones filtradas
        """
        mask = (soluciones_euler['z0'] >= z_min) & (soluciones_euler['z0'] <= z_max)
        return soluciones_euler[mask].copy()
    
    def clustering_fuentes(self, soluciones_euler, radio=100):
        """
        Agrupa soluciones de Euler cercanas (clustering)
        
        Args:
            soluciones_euler (pd.DataFrame): Soluciones de Euler
            radio (float): Radio de agrupamiento (m)
        
        Returns:
            pd.DataFrame: Centroides de clusters
        """
        from scipy.cluster.hierarchy import fclusterdata
        
        coords = soluciones_euler[['x0', 'y0', 'z0']].values
        
        # Clustering jerárquico
        clusters = fclusterdata(coords, radio, criterion='distance', method='complete')
        
        # Calcular centroides
        centroides = []
        for cluster_id in np.unique(clusters):
            mask = clusters == cluster_id
            centroide = {
                'x0': soluciones_euler.loc[mask, 'x0'].mean(),
                'y0': soluciones_euler.loc[mask, 'y0'].mean(),
                'z0': soluciones_euler.loc[mask, 'z0'].mean(),
                'n_solutions': mask.sum()
            }
            centroides.append(centroide)
        
        return pd.DataFrame(centroides)