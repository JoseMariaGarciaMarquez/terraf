"""
TERRAF Magnetometría
Módulo para procesamiento y análisis de datos magnetométricos
"""

import numpy as np
import pandas as pd
from scipy import ndimage
from scipy.signal import savgol_filter
import warnings
import os

# Suprimir warnings de PROJ/GDAL
warnings.filterwarnings('ignore')
os.environ['PROJ_LIB'] = ''
os.environ['CPL_LOG'] = 'OFF'

# Importar utilidades centralizadas
try:
    from .terraf_utils import (
        extraer_coordenadas_geometrias,
        transformar_coordenadas,
        obtener_bounds_geometrias,
        interpolar_a_grid,
        interpolar_desde_grid,
        calcular_estadisticas_basicas,
        crear_mascara_valida
    )
except ImportError:
    # Si falla import relativo, intentar absoluto
    from terraf_utils import (
        extraer_coordenadas_geometrias,
        transformar_coordenadas,
        obtener_bounds_geometrias,
        interpolar_a_grid,
        interpolar_desde_grid,
        calcular_estadisticas_basicas,
        crear_mascara_valida
    )

class TerrafMag:
    """
    Clase para procesamiento de datos de magnetometría
    
    Atributos:
        datos (pd.DataFrame): DataFrame con los datos magnetométricos
        campo_total (np.ndarray): Campo magnético total (nT)
        anomalia (np.ndarray): Anomalía magnética calculada
        reduccion_polo (np.ndarray): Reducción al polo magnético
        derivadas (dict): Derivadas del campo (1ra, 2da horizontal y vertical)
    """
    
    def __init__(self, ruta_datos=None, dataframe=None):
        """
        Inicializa el módulo de magnetometría
        
        Args:
            ruta_datos (str): Ruta al archivo shapefile/csv con datos magnéticos
            dataframe (pd.DataFrame): DataFrame con datos ya cargados
        """
        self.datos = None
        self.campo_total = None
        self.anomalia = None
        self.reduccion_polo = None
        self.derivadas = {}
        self.estadisticas = {}
        
        # Cache de coordenadas (calcular una sola vez)
        self._coords_cache = None
        self._bounds_cache = None
        
        if dataframe is not None:
            self.datos = dataframe
        elif ruta_datos is not None:
            self.cargar_datos(ruta_datos)
    
    def cargar_datos(self, ruta):
        """
        Carga datos magnetométricos desde shapefile o CSV
        
        Args:
            ruta (str): Ruta al archivo
        """
        try:
            if ruta.endswith('.shp'):
                import geopandas as gpd
                self.datos = gpd.read_file(ruta)
                print(f"✅ Shapefile cargado: {len(self.datos)} registros")
            elif ruta.endswith('.csv'):
                self.datos = pd.read_csv(ruta)
                print(f"✅ CSV cargado: {len(self.datos)} registros")
            else:
                raise ValueError("Formato no soportado. Use .shp o .csv")
            
            # Detectar columnas relevantes
            self._detectar_columnas()
            
        except Exception as e:
            print(f"❌ Error al cargar datos: {str(e)}")
            raise
    
    def _detectar_columnas(self):
        """Detecta automáticamente las columnas de campo magnético"""
        if self.datos is None:
            return
        
        # Buscar columnas con valores de campo magnético
        # RANGO_CODE es el campo oficial del SGM México
        keywords = ['campo', 'magnet', 'nt', 'total', 'anomal', 'tmi', 'rango_code', 'rango', 'cmt']
        exclude_keywords = ['objectid', 'shape_leng', 'shape_area', 'fid', 'carid']
        columnas = self.datos.columns.tolist()
        
        for col in columnas:
            col_lower = col.lower()
            # Saltar columnas de geometría
            if any(ex in col_lower for ex in exclude_keywords):
                continue
                
            # Buscar columnas con keywords magnéticos
            if any(kw in col_lower for kw in keywords):
                if self.datos[col].dtype in [np.float64, np.float32, np.int64, np.int32]:
                    self.campo_total = self.datos[col].values
                    print(f"📊 Campo magnético detectado en columna: '{col}'")
                    print(f"   📊 Rango de valores: {np.nanmin(self.campo_total):.2f} - {np.nanmax(self.campo_total):.2f}")
                    break
        
        if self.campo_total is None:
            print("⚠️ No se detectó automáticamente la columna de campo magnético")
    
    def obtener_coordenadas(self, forzar_recalculo=False):
        """
        Obtiene coordenadas X, Y de las geometrías (con cache).
        
        Args:
            forzar_recalculo: Si True, recalcula aunque exista cache
        
        Returns:
            tuple: (x, y) arrays numpy
        """
        if self._coords_cache is None or forzar_recalculo:
            if 'geometry' not in self.datos.columns:
                raise ValueError("Datos no tienen columna 'geometry'")
            
            self._coords_cache = extraer_coordenadas_geometrias(self.datos.geometry)
        
        return self._coords_cache
    
    def obtener_bounds(self, target_crs='EPSG:4326', forzar_recalculo=False):
        """
        Obtiene bounds en sistema de coordenadas especificado (con cache).
        
        Args:
            target_crs: CRS objetivo
            forzar_recalculo: Si True, recalcula aunque exista cache
        
        Returns:
            tuple: (min_x, min_y, max_x, max_y)
        """
        cache_key = target_crs
        
        if self._bounds_cache is None:
            self._bounds_cache = {}
        
        if cache_key not in self._bounds_cache or forzar_recalculo:
            if 'geometry' not in self.datos.columns:
                raise ValueError("Datos no tienen columna 'geometry'")
            
            crs = self.datos.crs if hasattr(self.datos, 'crs') else None
            self._bounds_cache[cache_key] = obtener_bounds_geometrias(
                self.datos.geometry, crs, target_crs
            )
        
        return self._bounds_cache[cache_key]
    
    def calcular_estadisticas(self):
        """Calcula estadísticas básicas del campo magnético"""
        if self.campo_total is None:
            raise ValueError("No hay datos de campo magnético cargados")
        
        # Usar función centralizada
        self.estadisticas = calcular_estadisticas_basicas(
            self.campo_total, 
            nombre="Campo Magnético Total"
        )
        
        return self.estadisticas
    
    def calcular_anomalia_residual(self, metodo='polinomial', grado=2):
        """
        Calcula la anomalía magnética residual removiendo el campo regional
        
        Args:
            metodo (str): 'polinomial', 'media_movil', o 'upward_continuation'
            grado (int): Grado del polinomio para ajuste regional
        
        Returns:
            np.ndarray: Anomalía residual
        """
        if self.campo_total is None:
            raise ValueError("No hay datos de campo magnético")
        
        if metodo == 'polinomial':
            # Ajustar superficie polinomial como campo regional
            if 'geometry' in self.datos.columns:
                # Extraer coordenadas (usar centroide para polígonos)
                centroids = self.datos.geometry.centroid
                x = centroids.x.values
                y = centroids.y.values
            else:
                # Asumir índices como coordenadas
                x = np.arange(len(self.campo_total))
                y = np.zeros_like(x)
            
            # Crear matriz de diseño para polinomio 2D
            A = np.column_stack([
                np.ones_like(x),
                x, y,
                x**2, x*y, y**2
            ])
            
            # Resolver por mínimos cuadrados
            coef = np.linalg.lstsq(A, self.campo_total, rcond=None)[0]
            campo_regional = A @ coef
            
            self.anomalia = self.campo_total - campo_regional
            print(f"✅ Anomalía residual calculada (método: {metodo})")
            
        elif metodo == 'media_movil':
            # Filtro de media móvil como campo regional
            ventana = len(self.campo_total) // 10
            campo_regional = ndimage.uniform_filter1d(self.campo_total, ventana)
            self.anomalia = self.campo_total - campo_regional
        
        else:
            raise ValueError(f"Método '{metodo}' no implementado")
        
        return self.anomalia
    
    def calcular_derivada_horizontal(self, direccion='total'):
        """
        Calcula la derivada horizontal del campo magnético
        
        Args:
            direccion (str): 'x', 'y', o 'total' (módulo del gradiente)
        
        Returns:
            np.ndarray: Derivada horizontal
        """
        if self.campo_total is None:
            raise ValueError("No hay datos de campo magnético")
        
        # Para datos 1D, aproximar derivada con diferencias finitas
        dx = np.gradient(self.campo_total)
        
        if direccion == 'total':
            derivada = np.abs(dx)
        else:
            derivada = dx
        
        self.derivadas['horizontal'] = derivada
        print(f"✅ Derivada horizontal calculada")
        
        return derivada
    
    def calcular_derivada_direccional(self, azimuth):
        """
        Calcula la derivada direccional del campo magnético en una dirección específica
        
        Args:
            azimuth (float): Ángulo en grados (0=Norte, 90=Este, 180=Sur, 270=Oeste)
        
        Returns:
            np.ndarray: Derivada direccional
        """
        if self.campo_total is None:
            raise ValueError("No hay datos de campo magnético")
        
        # Obtener coordenadas (con cache)
        x, y = self.obtener_coordenadas()
        
        # Interpolar a grid
        Xi, Yi, Zi = interpolar_a_grid(x, y, self.campo_total, resolution=100, method='cubic')
        
        # Calcular gradientes
        grad_y, grad_x = np.gradient(Zi)
        
        # Convertir azimuth a radianes (ajustar para convención matemática)
        theta = np.radians(90 - azimuth)
        
        # Derivada direccional = grad_x * cos(theta) + grad_y * sin(theta)
        derivada_direccional = grad_x * np.cos(theta) + grad_y * np.sin(theta)
        
        # Interpolar de vuelta a posiciones originales
        derivada = interpolar_desde_grid(Xi, Yi, derivada_direccional, x, y, method='linear')
        
        self.derivadas[f'direccional_{azimuth}'] = derivada
        print(f"✅ Derivada direccional calculada (azimuth: {azimuth}°)")
        
        return derivada
    
    def calcular_tilt_angle(self):
        """
        Calcula el ángulo de inclinación (Tilt Angle) del campo magnético
        
        El Tilt Angle es útil para delinear bordes de estructuras geológicas
        
        Returns:
            np.ndarray: Ángulo de inclinación en radianes
        """
        if self.campo_total is None:
            raise ValueError("No hay datos de campo magnético")
        
        # Calcular derivadas horizontales y verticales
        if 'horizontal' not in self.derivadas:
            self.calcular_derivada_horizontal()
        
        if 'vertical_1' not in self.derivadas:
            self.calcular_derivada_vertical(orden=1)
        
        # Tilt angle = arctan(derivada_vertical / derivada_horizontal)
        dh = self.derivadas['horizontal']
        dv = self.derivadas['vertical_1']
        
        # Evitar división por cero
        with np.errstate(divide='ignore', invalid='ignore'):
            tilt = np.arctan2(dv, dh)
        
        self.derivadas['tilt_angle'] = tilt
        print("✅ Tilt Angle calculado")
        
        return tilt
    
    def calcular_gradiente_horizontal_total(self):
        """
        Calcula el gradiente horizontal total (THG - Total Horizontal Gradient)
        
        THG es útil para detectar bordes de cuerpos magnéticos
        
        Returns:
            np.ndarray: Gradiente horizontal total
        """
        if self.campo_total is None:
            raise ValueError("No hay datos de campo magnético")
        
        # Obtener coordenadas (con cache)
        x, y = self.obtener_coordenadas()
        
        # Interpolar a grid
        Xi, Yi, Zi = interpolar_a_grid(x, y, self.campo_total, resolution=100, method='cubic')
        
        # Calcular gradientes
        grad_y, grad_x = np.gradient(Zi)
        
        # THG = sqrt(grad_x^2 + grad_y^2)
        thg_grid = np.sqrt(grad_x**2 + grad_y**2)
        
        # Interpolar de vuelta a posiciones originales
        thg = interpolar_desde_grid(Xi, Yi, thg_grid, x, y, method='linear')
        
        self.derivadas['thg'] = thg
        print("✅ Gradiente Horizontal Total (THG) calculado")
        
        return thg
    
    def calcular_gradiente_analitic_signal(self):
        """
        Calcula la señal analítica (Analytic Signal) del campo magnético
        
        AS = sqrt(dx^2 + dy^2 + dz^2)
        Útil para localizar fuentes magnéticas independiente de la magnetización
        
        Returns:
            np.ndarray: Amplitud de la señal analítica
        """
        if self.campo_total is None:
            raise ValueError("No hay datos de campo magnético")
        
        # Calcular THG si no existe
        if 'thg' not in self.derivadas:
            self.calcular_gradiente_horizontal_total()
        
        # Calcular derivada vertical si no existe
        if 'vertical_1' not in self.derivadas:
            self.calcular_derivada_vertical(orden=1)
        
        thg = self.derivadas['thg']
        dz = self.derivadas['vertical_1']
        
        # AS = sqrt(THG^2 + dz^2)
        analytic_signal = np.sqrt(thg**2 + dz**2)
        
        self.derivadas['analytic_signal'] = analytic_signal
        print("✅ Señal Analítica calculada")
        
        return analytic_signal
    
    def continuacion_hacia_arriba(self, altura):
        """
        Continúa el campo magnético hacia arriba a una altura específica
        
        Útil para suprimir anomalías superficiales y resaltar estructuras profundas
        
        Args:
            altura (float): Altura en metros para la continuación
        
        Returns:
            np.ndarray: Campo magnético continuado hacia arriba
        """
        if self.campo_total is None:
            raise ValueError("No hay datos de campo magnético")
        
        # Implementación usando FFT
        campo_fft = np.fft.fft(self.campo_total)
        k = np.fft.fftfreq(len(self.campo_total))
        
        # Factor de continuación hacia arriba: exp(-2*pi*|k|*h)
        factor = np.exp(-2 * np.pi * np.abs(k) * altura)
        
        # Aplicar continuación
        campo_continuado_fft = campo_fft * factor
        campo_continuado = np.real(np.fft.ifft(campo_continuado_fft))
        
        self.derivadas[f'upward_continuation_{altura}m'] = campo_continuado
        print(f"✅ Continuación hacia arriba a {altura}m calculada")
        
        return campo_continuado
    
    def aplicar_filtro_paso_alto(self, cutoff_freq=0.1):
        """
        Aplica un filtro pasa-altos para resaltar anomalías locales
        
        Args:
            cutoff_freq (float): Frecuencia de corte normalizada (0-1)
        
        Returns:
            np.ndarray: Campo magnético filtrado
        """
        if self.campo_total is None:
            raise ValueError("No hay datos de campo magnético")
        
        from scipy import signal
        
        # Diseñar filtro Butterworth pasa-altos
        b, a = signal.butter(4, cutoff_freq, btype='high')
        
        # Aplicar filtro
        campo_filtrado = signal.filtfilt(b, a, self.campo_total)
        
        self.derivadas['highpass_filter'] = campo_filtrado
        print(f"✅ Filtro pasa-altos aplicado (cutoff: {cutoff_freq})")
        
        return campo_filtrado
    
    def aplicar_filtro_paso_bajo(self, cutoff_freq=0.5):
        """
        Aplica un filtro pasa-bajos para resaltar anomalías regionales
        
        Args:
            cutoff_freq (float): Frecuencia de corte normalizada (0-1)
        
        Returns:
            np.ndarray: Campo magnético filtrado
        """
        if self.campo_total is None:
            raise ValueError("No hay datos de campo magnético")
        
        from scipy import signal
        
        # Diseñar filtro Butterworth pasa-bajos
        b, a = signal.butter(4, cutoff_freq, btype='low')
        
        # Aplicar filtro
        campo_filtrado = signal.filtfilt(b, a, self.campo_total)
        
        self.derivadas['lowpass_filter'] = campo_filtrado
        print(f"✅ Filtro pasa-bajos aplicado (cutoff: {cutoff_freq})")
        
        return campo_filtrado
    
    def calcular_derivada_vertical(self, orden=1):
        """
        Calcula la derivada vertical del campo magnético
        
        Args:
            orden (int): Orden de la derivada (1 o 2)
        
        Returns:
            np.ndarray: Derivada vertical
        """
        if self.campo_total is None:
            raise ValueError("No hay datos de campo magnético")
        
        # Aproximación usando transformada de Fourier
        # Para datos espaciales, asumir grid regular
        campo_fft = np.fft.fft(self.campo_total)
        k = np.fft.fftfreq(len(self.campo_total))
        
        # Multiplicar por (i*k)^orden en frecuencia
        derivada_fft = campo_fft * (2j * np.pi * k) ** orden
        derivada = np.real(np.fft.ifft(derivada_fft))
        
        self.derivadas[f'vertical_{orden}'] = derivada
        print(f"✅ Derivada vertical de orden {orden} calculada")
        
        return derivada
    
    def reduccion_al_polo(self, inclinacion, declinacion):
        """
        Reduce el campo magnético al polo magnético
        
        Args:
            inclinacion (float): Inclinación magnética en grados
            declinacion (float): Declinación magnética en grados
        
        Returns:
            np.ndarray: Campo reducido al polo
        """
        if self.campo_total is None:
            raise ValueError("No hay datos de campo magnético")
        
        # Implementación simplificada (requiere FFT 2D para datos gridded)
        # Por ahora, aproximación básica
        print("⚠️ Reducción al polo requiere datos en grid regular")
        print("   Implementación completa próximamente")
        
        # Placeholder: aplicar corrección angular simple
        inc_rad = np.radians(inclinacion)
        factor = 1 / np.cos(inc_rad)
        self.reduccion_polo = self.campo_total * factor
        
        return self.reduccion_polo
    
    def detectar_anomalias(self, umbral_sigma=2.0):
        """
        Detecta anomalías magnéticas significativas
        
        Args:
            umbral_sigma (float): Número de desviaciones estándar para umbral
        
        Returns:
            dict: Información de anomalías detectadas
        """
        if self.campo_total is None:
            raise ValueError("No hay datos de campo magnético")
        
        # Calcular umbral
        mean = np.nanmean(self.campo_total)
        std = np.nanstd(self.campo_total)
        umbral_alto = mean + umbral_sigma * std
        umbral_bajo = mean - umbral_sigma * std
        
        # Detectar anomalías
        anomalias_altas = self.campo_total > umbral_alto
        anomalias_bajas = self.campo_total < umbral_bajo
        
        resultados = {
            'n_anomalias_altas': np.sum(anomalias_altas),
            'n_anomalias_bajas': np.sum(anomalias_bajas),
            'umbral_alto': umbral_alto,
            'umbral_bajo': umbral_bajo,
            'indices_altas': np.where(anomalias_altas)[0],
            'indices_bajas': np.where(anomalias_bajas)[0],
            'valores_altas': self.campo_total[anomalias_altas],
            'valores_bajas': self.campo_total[anomalias_bajas]
        }
        
        print(f"✅ Detectadas {resultados['n_anomalias_altas']} anomalías altas")
        print(f"✅ Detectadas {resultados['n_anomalias_bajas']} anomalías bajas")
        
        return resultados
    
    def suavizar_datos(self, metodo='savgol', ventana=11, orden=3):
        """
        Suaviza los datos magnéticos para reducir ruido
        
        Args:
            metodo (str): 'savgol' o 'gaussian'
            ventana (int): Tamaño de la ventana
            orden (int): Orden del polinomio (solo para Savitzky-Golay)
        
        Returns:
            np.ndarray: Datos suavizados
        """
        if self.campo_total is None:
            raise ValueError("No hay datos de campo magnético")
        
        if metodo == 'savgol':
            datos_suavizados = savgol_filter(self.campo_total, ventana, orden)
        elif metodo == 'gaussian':
            sigma = ventana / 4
            datos_suavizados = ndimage.gaussian_filter1d(self.campo_total, sigma)
        else:
            raise ValueError(f"Método '{metodo}' no soportado")
        
        print(f"✅ Datos suavizados con {metodo}")
        return datos_suavizados
    
    def exportar_resultados(self, ruta_salida, formato='csv'):
        """
        Exporta los resultados del análisis
        
        Args:
            ruta_salida (str): Ruta del archivo de salida
            formato (str): 'csv' o 'shapefile'
        """
        if self.datos is None:
            raise ValueError("No hay datos para exportar")
        
        # Crear DataFrame con resultados
        df_export = self.datos.copy()
        
        if self.anomalia is not None:
            df_export['anomalia_residual'] = self.anomalia
        
        if 'horizontal' in self.derivadas:
            df_export['derivada_horizontal'] = self.derivadas['horizontal']
        
        if 'vertical_1' in self.derivadas:
            df_export['derivada_vertical'] = self.derivadas['vertical_1']
        
        # Exportar
        if formato == 'csv':
            df_export.to_csv(ruta_salida, index=False)
            print(f"✅ Resultados exportados a {ruta_salida}")
        elif formato == 'shapefile':
            import geopandas as gpd
            if isinstance(df_export, gpd.GeoDataFrame):
                df_export.to_file(ruta_salida)
                print(f"✅ Shapefile exportado a {ruta_salida}")
            else:
                raise ValueError("Los datos no tienen geometría para shapefile")
        else:
            raise ValueError(f"Formato '{formato}' no soportado")
    
    # ========================================================================
    # MÉTODOS PARA DERIVADAS EN GRILLA 2D (sin interpolar huecos)
    # ========================================================================
    
    @staticmethod
    def calcular_derivadas_grid(grid_mag, dx=25, dy=25):
        """
        Calcula derivadas magnéticas sobre una grilla 2D sin interpolar huecos
        
        Args:
            grid_mag (np.ndarray): Grilla 2D con campo magnético (puede tener NaN)
            dx (float): Espaciado en X (metros)
            dy (float): Espaciado en Y (metros)
        
        Returns:
            dict: Diccionario con todas las derivadas calculadas
        """
        results = {}
        
        # 1. Derivadas Horizontales usando Sobel (respeta NaN)
        dT_dx = ndimage.sobel(grid_mag, axis=1, mode='constant', cval=np.nan) / dx
        dT_dy = ndimage.sobel(grid_mag, axis=0, mode='constant', cval=np.nan) / dy
        
        results['dT_dx'] = dT_dx
        results['dT_dy'] = dT_dy
        
        # 2. Gradiente Horizontal Total (THG)
        THG = np.sqrt(dT_dx**2 + dT_dy**2)
        results['THG'] = THG
        
        # 3. Derivada Vertical (aproximación con Laplaciano)
        laplacian = ndimage.laplace(grid_mag, mode='constant', cval=np.nan)
        dT_dz = -laplacian / 2.0
        results['dT_dz'] = dT_dz
        
        # 4. Tilt Angle
        THG_safe = np.where(THG < 1e-10, 1e-10, THG)
        tilt_angle = np.arctan(dT_dz / THG_safe)
        tilt_angle_deg = np.degrees(tilt_angle)
        results['tilt_angle'] = tilt_angle
        results['tilt_angle_deg'] = tilt_angle_deg
        
        # 5. Analytic Signal
        AS = np.sqrt(dT_dx**2 + dT_dy**2 + dT_dz**2)
        results['analytic_signal'] = AS
        
        return results
    
    @staticmethod
    def calcular_residual_grid(grid_mag, grado=2):
        """
        Calcula anomalía residual removiendo tendencia regional con polinomio
        
        Args:
            grid_mag (np.ndarray): Grilla 2D con campo magnético
            grado (int): Grado del polinomio (1=linear, 2=cuadrático, 3=cúbico)
        
        Returns:
            tuple: (regional, residual)
        """
        # Crear coordenadas normalizadas
        ny, nx = grid_mag.shape
        x_norm = np.linspace(0, 1, nx)
        y_norm = np.linspace(0, 1, ny)
        X, Y = np.meshgrid(x_norm, y_norm)
        
        # Extraer puntos válidos
        mask = ~np.isnan(grid_mag)
        x_valid = X[mask].flatten()
        y_valid = Y[mask].flatten()
        z_valid = grid_mag[mask].flatten()
        
        # Construir matriz de diseño según grado
        if grado == 1:
            # Linear: z = a + bx + cy
            X_matrix = np.column_stack([
                np.ones(len(x_valid)),
                x_valid,
                y_valid
            ])
        elif grado == 2:
            # Cuadrático: z = a + bx + cy + dx² + exy + fy²
            X_matrix = np.column_stack([
                np.ones(len(x_valid)),
                x_valid,
                y_valid,
                x_valid**2,
                x_valid * y_valid,
                y_valid**2
            ])
        elif grado == 3:
            # Cúbico
            X_matrix = np.column_stack([
                np.ones(len(x_valid)),
                x_valid,
                y_valid,
                x_valid**2,
                x_valid * y_valid,
                y_valid**2,
                x_valid**3,
                x_valid**2 * y_valid,
                x_valid * y_valid**2,
                y_valid**3
            ])
        else:
            raise ValueError(f"Grado {grado} no soportado")
        
        # Ajustar polinomio
        coeffs = np.linalg.lstsq(X_matrix, z_valid, rcond=None)[0]
        
        # Evaluar tendencia regional en toda la grilla
        if grado == 1:
            X_grid = np.column_stack([
                np.ones(X.size),
                X.flatten(),
                Y.flatten()
            ])
        elif grado == 2:
            X_grid = np.column_stack([
                np.ones(X.size),
                X.flatten(),
                Y.flatten(),
                X.flatten()**2,
                X.flatten() * Y.flatten(),
                Y.flatten()**2
            ])
        elif grado == 3:
            X_grid = np.column_stack([
                np.ones(X.size),
                X.flatten(),
                Y.flatten(),
                X.flatten()**2,
                X.flatten() * Y.flatten(),
                Y.flatten()**2,
                X.flatten()**3,
                X.flatten()**2 * Y.flatten(),
                X.flatten() * Y.flatten()**2,
                Y.flatten()**3
            ])
        
        regional = (X_grid @ coeffs).reshape(grid_mag.shape)
        residual = grid_mag - regional
        
        return regional, residual
