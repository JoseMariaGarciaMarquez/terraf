"""
🔍 TERRAF PR - Percepción Remota para Exploración Minera
==========================================================

Clase modular para análisis de imágenes satelitales Landsat
Orientada a exploración minera y detección de alteración hidrotermal

Autor: TERRAF Team
Fecha: Noviembre 2025
"""

import numpy as np
import matplotlib.pyplot as plt
import warnings
import os
import glob
from typing import Dict, Tuple, Optional, List
warnings.filterwarnings('ignore')

try:
    import rasterio
    from rasterio.enums import Resampling
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False
    print("⚠️ Rasterio no disponible - Instala con: conda install -c conda-forge rasterio")


class TerrafPR:
    """
    Clase para análisis de percepción remota orientado a exploración minera
    
    Funcionalidades:
    - Carga automática de bandas Landsat (8 o 9, Level-1 o Level-2)
    - Composiciones RGB (natural, falso color, geología)
    - Índices espectrales y ratios para minerales
    - Detección de alteración hidrotermal
    - Visualización interactiva
    - Exportación de resultados
    
    Ejemplo de uso:
        # Crear instancia
        pr = TerrafPR("vfm/datos/extraido", nombre="VFM")
        
        # Cargar bandas
        pr.cargar_bandas(reducir=True, factor=4)
        
        # Visualizar
        pr.show('natural_color')
        pr.show('false_color')
        
        # Análisis mineral
        pr.calcular_ratio_argilica()
        pr.calcular_ratio_oxidos()
        pr.show('argilica')
        
        # Análisis completo
        pr.analisis_completo()
        pr.exportar_todo()
    """
    
    def __init__(self, carpeta: str, nombre: str = "Region"):
        """
        Inicializa TerrafPR
        
        Args:
            carpeta: Ruta a la carpeta con bandas Landsat
            nombre: Nombre de la región (para títulos y archivos)
        """
        self.carpeta = carpeta
        self.nombre = nombre
        self.bandas = {}
        self.metadatos = {}
        self.ratios = {}
        self.indices = {}
        self.zonas = {}
        self.composiciones = {}
        
        print(f"\n{'='*80}")
        print(f"🛰️  TERRASF PR - Percepción Remota")
        print(f"📂 Región: {nombre}")
        print(f"📁 Carpeta: {carpeta}")
        print(f"{'='*80}\n")
        
        if not os.path.exists(carpeta):
            raise FileNotFoundError(f"Carpeta no encontrada: {carpeta}")
    
    
    def detectar_bandas(self) -> Dict[str, str]:
        """
        Detecta automáticamente archivos de bandas Landsat
        
        Returns:
            Diccionario con {banda: ruta_archivo}
        """
        print("🔍 Detectando bandas Landsat...")
        
        archivos_tif = glob.glob(os.path.join(self.carpeta, "*.TIF"))
        
        if not archivos_tif:
            raise FileNotFoundError(f"No se encontraron archivos .TIF en {self.carpeta}")
        
        bandas_encontradas = {}
        
        # Intentar Level-2 (_SR_B*.TIF)
        for i in range(1, 12):
            matches = [f for f in archivos_tif if f"_SR_B{i}.TIF" in f]
            if matches:
                bandas_encontradas[f'B{i}'] = matches[0]
        
        # Si no hay Level-2, intentar Level-1 (_B*.TIF)
        if not bandas_encontradas:
            for i in range(1, 12):
                matches = [f for f in archivos_tif if f"_B{i}.TIF" in f and "_SR_B" not in f]
                if matches:
                    bandas_encontradas[f'B{i}'] = matches[0]
        
        if not bandas_encontradas:
            raise ValueError("No se pudieron detectar bandas con formato Landsat estándar")
        
        # Determinar tipo
        tipo = "Level-2 SR" if '_SR_B' in list(bandas_encontradas.values())[0] else "Level-1"
        
        print(f"  ✅ Tipo: {tipo}")
        print(f"  ✅ Bandas: {', '.join(sorted(bandas_encontradas.keys()))}")
        
        return bandas_encontradas
    
    
    def cargar_bandas(self, reducir: bool = True, factor: int = 4, 
                      bandas_especificas: Optional[List[str]] = None):
        """
        Carga las bandas Landsat en memoria
        
        Args:
            reducir: Si True, reduce resolución para ahorrar memoria
            factor: Factor de reducción (2=50%, 4=25%, 8=12.5%)
            bandas_especificas: Lista de bandas a cargar (ej: ['B4','B5','B6'])
                               Si None, carga todas las disponibles
        """
        print(f"\n🛰️  Cargando bandas Landsat...")
        
        if reducir:
            print(f"  ⚙️  Reducción: {100/factor:.0f}% de resolución original")
        
        # Detectar bandas disponibles
        archivos_bandas = self.detectar_bandas()
        
        # Filtrar si se especificaron bandas
        if bandas_especificas:
            archivos_bandas = {b: archivos_bandas[b] for b in bandas_especificas 
                              if b in archivos_bandas}
        
        # Cargar cada banda
        for banda_nombre, ruta_archivo in sorted(archivos_bandas.items()):
            with rasterio.open(ruta_archivo) as src:
                if reducir:
                    banda = src.read(1,
                                   out_shape=(src.height // factor,
                                             src.width // factor),
                                   resampling=Resampling.average).astype(float)
                else:
                    banda = src.read(1).astype(float)
                
                self.bandas[banda_nombre] = banda
                
                # Guardar metadatos
                if not self.metadatos:
                    self.metadatos = {
                        'transform': src.transform,
                        'crs': src.crs,
                        'width': banda.shape[1],
                        'height': banda.shape[0],
                        'shape_original': (src.height, src.width),
                        'resolution': 30 * factor if reducir else 30
                    }
            
            print(f"     ✅ {banda_nombre}: {self.bandas[banda_nombre].shape}")
        
        print(f"\n  ✅ {len(self.bandas)} bandas cargadas")
        print(f"  📊 Resolución efectiva: {self.metadatos['resolution']}m/pixel")
        
        return self
    
    
    def _normalizar(self, banda: np.ndarray, percentiles: Tuple[int, int] = (2, 98)) -> np.ndarray:
        """Normaliza banda al rango 0-1"""
        banda_limpia = banda.copy()
        banda_limpia[banda_limpia == 0] = np.nan
        
        p_low, p_high = np.nanpercentile(banda_limpia, percentiles)
        banda_norm = np.clip((banda_limpia - p_low) / (p_high - p_low), 0, 1)
        banda_norm = np.nan_to_num(banda_norm, 0)
        
        return banda_norm
    
    
    def crear_rgb_natural(self):
        """Crea composición RGB en color natural (R=B4, G=B3, B=B2)"""
        if not all(b in self.bandas for b in ['B2', 'B3', 'B4']):
            raise ValueError("Faltan bandas B2, B3, B4 para RGB natural")
        
        print("🎨 Creando RGB natural...")
        rgb = np.dstack([
            self._normalizar(self.bandas['B4']),  # Rojo
            self._normalizar(self.bandas['B3']),  # Verde
            self._normalizar(self.bandas['B2'])   # Azul
        ])
        
        self.composiciones['natural_color'] = rgb
        print("  ✅ RGB natural creado")
        return self
    
    
    def crear_falso_color(self):
        """Crea composición falso color para vegetación (R=B5, G=B4, B=B3)"""
        if not all(b in self.bandas for b in ['B3', 'B4', 'B5']):
            raise ValueError("Faltan bandas B3, B4, B5 para falso color")
        
        print("🎨 Creando falso color (vegetación)...")
        rgb = np.dstack([
            self._normalizar(self.bandas['B5']),  # NIR -> Rojo
            self._normalizar(self.bandas['B4']),  # Rojo -> Verde
            self._normalizar(self.bandas['B3'])   # Verde -> Azul
        ])
        
        self.composiciones['false_color'] = rgb
        print("  ✅ Falso color creado")
        return self
    
    
    def crear_geologia_color(self):
        """Crea composición para geología (R=B7, G=B5, B=B2)"""
        if not all(b in self.bandas for b in ['B2', 'B5', 'B7']):
            raise ValueError("Faltan bandas B2, B5, B7 para geología")
        
        print("🎨 Creando composición geológica...")
        rgb = np.dstack([
            self._normalizar(self.bandas['B7']),  # SWIR2 -> Rojo
            self._normalizar(self.bandas['B5']),  # NIR -> Verde
            self._normalizar(self.bandas['B2'])   # Azul -> Azul
        ])
        
        self.composiciones['geology_color'] = rgb
        print("  ✅ Composición geológica creada")
        return self
    
    
    def calcular_ratio_argilica(self):
        """Calcula ratio B6/B7 para alteración argílica (arcillas)"""
        if not all(b in self.bandas for b in ['B6', 'B7']):
            raise ValueError("Faltan bandas B6, B7")
        
        print("💎 Calculando Ratio B6/B7 - Alteración Argílica...")
        
        ratio = np.divide(self.bandas['B6'], self.bandas['B7'],
                         out=np.zeros_like(self.bandas['B6']),
                         where=self.bandas['B7'] != 0)
        
        self.ratios['argilica'] = ratio
        
        # Zona de anomalía
        umbral = np.nanpercentile(ratio[ratio > 0], 85)
        self.zonas['zona_argilica'] = ratio > umbral
        
        area = np.sum(self.zonas['zona_argilica']) * (self.metadatos['resolution']**2) / 1e6
        
        print(f"  📊 Rango: {np.nanmin(ratio):.3f} - {np.nanmax(ratio):.3f}")
        print(f"  📊 Promedio: {np.nanmean(ratio):.3f}")
        print(f"  🎯 Área detectada: {area:.2f} km²")
        print(f"  🔬 Detecta: Caolinita, Alunita, Dickita, Pirofilita")
        
        return self
    
    
    def calcular_ratio_oxidos(self):
        """Calcula ratio B4/B2 para óxidos de hierro"""
        if not all(b in self.bandas for b in ['B2', 'B4']):
            raise ValueError("Faltan bandas B2, B4")
        
        print("🏔️  Calculando Ratio B4/B2 - Óxidos de Hierro...")
        
        ratio = np.divide(self.bandas['B4'], self.bandas['B2'],
                         out=np.zeros_like(self.bandas['B4']),
                         where=self.bandas['B2'] != 0)
        
        self.ratios['oxidos'] = ratio
        
        # Zona de anomalía
        umbral = np.nanpercentile(ratio[ratio > 0], 80)
        self.zonas['zona_oxidos'] = ratio > umbral
        
        area = np.sum(self.zonas['zona_oxidos']) * (self.metadatos['resolution']**2) / 1e6
        
        print(f"  📊 Rango: {np.nanmin(ratio):.3f} - {np.nanmax(ratio):.3f}")
        print(f"  📊 Promedio: {np.nanmean(ratio):.3f}")
        print(f"  🎯 Área detectada: {area:.2f} km²")
        print(f"  🔬 Detecta: Goethita, Hematita, Limonita, Jarosita")
        
        return self
    
    
    def calcular_ratio_oh(self):
        """Calcula ratio B6/B5 para minerales OH (hidroxilos)"""
        if not all(b in self.bandas for b in ['B5', 'B6']):
            raise ValueError("Faltan bandas B5, B6")
        
        print("🪨 Calculando Ratio B6/B5 - Minerales OH...")
        
        ratio = np.divide(self.bandas['B6'], self.bandas['B5'],
                         out=np.zeros_like(self.bandas['B6']),
                         where=self.bandas['B5'] != 0)
        
        self.ratios['oh'] = ratio
        
        print(f"  📊 Rango: {np.nanmin(ratio):.3f} - {np.nanmax(ratio):.3f}")
        print(f"  📊 Promedio: {np.nanmean(ratio):.3f}")
        print(f"  🔬 Detecta: Sericita, Epidota, Clorita, Montmorillonita")
        
        return self
    
    
    def calcular_propilitica(self):
        """Calcula ratio B5/B6 para alteración propilítica"""
        if not all(b in self.bandas for b in ['B5', 'B6']):
            raise ValueError("Faltan bandas B5, B6")
        
        print("🌿 Calculando Ratio B5/B6 - Alteración Propilítica...")
        
        ratio = np.divide(self.bandas['B5'], self.bandas['B6'],
                         out=np.zeros_like(self.bandas['B5']),
                         where=self.bandas['B6'] != 0)
        
        self.ratios['propilitica'] = ratio
        
        # Zona de anomalía
        umbral = np.nanpercentile(ratio[ratio > 0], 75)
        self.zonas['zona_propilitica'] = ratio > umbral
        
        area = np.sum(self.zonas['zona_propilitica']) * (self.metadatos['resolution']**2) / 1e6
        
        print(f"  📊 Rango: {np.nanmin(ratio):.3f} - {np.nanmax(ratio):.3f}")
        print(f"  📊 Promedio: {np.nanmean(ratio):.3f}")
        print(f"  🎯 Área detectada: {area:.2f} km²")
        print(f"  🔬 Detecta: Clorita, Epidota, Calcita (zona propilítica)")
        
        return self
    
    
    def calcular_carbonatos(self):
        """Calcula índice de carbonatos B6/(B6+B7)"""
        if not all(b in self.bandas for b in ['B6', 'B7']):
            raise ValueError("Faltan bandas B6, B7")
        
        print("🪨 Calculando Índice de Carbonatos...")
        
        indice = np.divide(self.bandas['B6'], 
                          self.bandas['B6'] + self.bandas['B7'],
                          out=np.zeros_like(self.bandas['B6']),
                          where=(self.bandas['B6'] + self.bandas['B7']) != 0)
        
        self.indices['carbonatos'] = indice
        
        # Zona de anomalía (valores bajos indican carbonatos)
        umbral = np.nanpercentile(indice[indice > 0], 30)
        self.zonas['zona_carbonatos'] = indice < umbral
        
        area = np.sum(self.zonas['zona_carbonatos']) * (self.metadatos['resolution']**2) / 1e6
        
        print(f"  📊 Rango: {np.nanmin(indice):.3f} - {np.nanmax(indice):.3f}")
        print(f"  📊 Promedio: {np.nanmean(indice):.3f}")
        print(f"  🎯 Área detectada: {area:.2f} km²")
        print(f"  🔬 Detecta: Calcita, Dolomita, Ankerita")
        
        return self
    
    
    def calcular_ndvi(self):
        """Calcula NDVI (Normalized Difference Vegetation Index)"""
        if not all(b in self.bandas for b in ['B4', 'B5']):
            raise ValueError("Faltan bandas B4, B5")
        
        print("🌱 Calculando NDVI - Índice de Vegetación...")
        
        ndvi = np.divide(self.bandas['B5'] - self.bandas['B4'],
                        self.bandas['B5'] + self.bandas['B4'],
                        out=np.zeros_like(self.bandas['B5']),
                        where=(self.bandas['B5'] + self.bandas['B4']) != 0)
        
        self.indices['ndvi'] = ndvi
        
        # Clasificación
        vegetacion_densa = ndvi > 0.6
        vegetacion_moderada = (ndvi > 0.3) & (ndvi <= 0.6)
        vegetacion_escasa = (ndvi > 0.2) & (ndvi <= 0.3)
        sin_vegetacion = ndvi <= 0.2
        
        self.zonas['vegetacion_densa'] = vegetacion_densa
        self.zonas['sin_vegetacion'] = sin_vegetacion
        
        area_veg = np.sum(vegetacion_densa) * (self.metadatos['resolution']**2) / 1e6
        area_sin_veg = np.sum(sin_vegetacion) * (self.metadatos['resolution']**2) / 1e6
        
        print(f"  📊 Rango: {np.nanmin(ndvi):.3f} - {np.nanmax(ndvi):.3f}")
        print(f"  📊 Promedio: {np.nanmean(ndvi):.3f}")
        print(f"  🌳 Vegetación densa: {area_veg:.2f} km²")
        print(f"  🏜️ Sin vegetación: {area_sin_veg:.2f} km²")
        print(f"  💡 Útil para: Filtrar áreas vegetadas del análisis mineral")
        
        return self
    
    
    def calcular_gossan(self):
        """Calcula Gossan Index (combinación óxidos + arcillas)"""
        # Calcular ratios base si no existen
        if 'argilica' not in self.ratios:
            self.calcular_ratio_argilica()
        if 'oxidos' not in self.ratios:
            self.calcular_ratio_oxidos()
        
        print("⛰️  Calculando Gossan Index...")
        
        # Gossan = (B4/B2) * (B6/B7)
        gossan = self.ratios['oxidos'] * self.ratios['argilica']
        
        self.indices['gossan'] = gossan
        
        # Zona de anomalía (valores altos = gossan)
        umbral = np.nanpercentile(gossan[gossan > 0], 90)
        self.zonas['zona_gossan'] = gossan > umbral
        
        area = np.sum(self.zonas['zona_gossan']) * (self.metadatos['resolution']**2) / 1e6
        
        print(f"  📊 Rango: {np.nanmin(gossan):.3f} - {np.nanmax(gossan):.3f}")
        print(f"  📊 Promedio: {np.nanmean(gossan):.3f}")
        print(f"  🎯 Área detectada: {area:.2f} km²")
        print(f"  🔬 Detecta: Gossans (sombreros de hierro sobre sulfuros)")
        print(f"  💡 Alta prioridad: Posibles depósitos de sulfuros metálicos")
        
        return self
    
    
    def calcular_clay_index(self):
        """Calcula Clay Index mejorado (B6*B6)/(B7*B5)"""
        if not all(b in self.bandas for b in ['B5', 'B6', 'B7']):
            raise ValueError("Faltan bandas B5, B6, B7")
        
        print("🧱 Calculando Clay Index (Índice de Arcillas Mejorado)...")
        
        indice = np.divide(self.bandas['B6'] * self.bandas['B6'],
                          self.bandas['B7'] * self.bandas['B5'],
                          out=np.zeros_like(self.bandas['B6']),
                          where=(self.bandas['B7'] * self.bandas['B5']) != 0)
        
        self.indices['clay_index'] = indice
        
        # Zona de anomalía
        umbral = np.nanpercentile(indice[indice > 0], 85)
        self.zonas['zona_clay'] = indice > umbral
        
        area = np.sum(self.zonas['zona_clay']) * (self.metadatos['resolution']**2) / 1e6
        
        print(f"  📊 Rango: {np.nanmin(indice):.3f} - {np.nanmax(indice):.3f}")
        print(f"  📊 Promedio: {np.nanmean(indice):.3f}")
        print(f"  🎯 Área detectada: {area:.2f} km²")
        print(f"  🔬 Detecta: Arcillas con mayor precisión que B6/B7")
        print(f"  💡 Mejor para: Mapeo detallado de alteración argílica")
        
        return self
    
    
    def calcular_iah(self):
        """Calcula Índice de Alteración Hidrotermal (B6+B7)/B5"""
        if not all(b in self.bandas for b in ['B5', 'B6', 'B7']):
            raise ValueError("Faltan bandas B5, B6, B7")
        
        print("🔬 Calculando IAH - Índice de Alteración Hidrotermal...")
        
        iah = np.divide(self.bandas['B6'] + self.bandas['B7'], self.bandas['B5'],
                       out=np.zeros_like(self.bandas['B5']),
                       where=self.bandas['B5'] != 0)
        
        self.indices['iah'] = iah
        
        # Zona de anomalía
        umbral = np.nanpercentile(iah[iah > 0], 90)
        self.zonas['zona_iah'] = iah > umbral
        
        area = np.sum(self.zonas['zona_iah']) * (self.metadatos['resolution']**2) / 1e6
        
        print(f"  📊 Rango: {np.nanmin(iah):.3f} - {np.nanmax(iah):.3f}")
        print(f"  📊 Promedio: {np.nanmean(iah):.3f}")
        print(f"  🎯 Área con alteración fuerte: {area:.2f} km²")
        
        return self
    
    
    def identificar_objetivos(self):
        """Identifica zonas prioritarias combinando múltiples indicadores"""
        print("\n🎯 Identificando objetivos prioritarios...")
        
        if not all(z in self.zonas for z in ['zona_argilica', 'zona_oxidos', 'zona_iah']):
            print("  ⚠️  Calculando ratios faltantes...")
            if 'zona_argilica' not in self.zonas:
                self.calcular_ratio_argilica()
            if 'zona_oxidos' not in self.zonas:
                self.calcular_ratio_oxidos()
            if 'zona_iah' not in self.zonas:
                self.calcular_iah()
        
        # Triple coincidencia
        zona_prioritaria = (self.zonas['zona_argilica'] & 
                           self.zonas['zona_oxidos'] & 
                           self.zonas['zona_iah'])
        
        self.zonas['objetivos_prioritarios'] = zona_prioritaria
        
        area = np.sum(zona_prioritaria) * (self.metadatos['resolution']**2) / 1e6
        n_pixeles = np.sum(zona_prioritaria)
        
        print(f"  ✅ Área prioritaria: {area:.3f} km²")
        print(f"  ✅ Píxeles: {n_pixeles}")
        print(f"  💡 Criterio: Argílica + Óxidos + IAH alto")
        
        return self
    
    
    def show(self, tipo: str, figsize: Tuple[int, int] = (12, 10), 
             guardar: bool = False, nombre_archivo: Optional[str] = None):
        """
        Muestra una visualización
        
        Args:
            tipo: Tipo de visualización
                  'natural_color', 'false_color', 'geology_color',
                  'argilica', 'oxidos', 'oh', 'iah', 'objetivos'
            figsize: Tamaño de figura
            guardar: Si True, guarda la imagen
            nombre_archivo: Nombre personalizado para guardar
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        titulo = ""
        
        # Composiciones RGB
        if tipo == 'natural_color':
            if 'natural_color' not in self.composiciones:
                self.crear_rgb_natural()
            ax.imshow(self.composiciones['natural_color'])
            titulo = f"{self.nombre} - Color Natural\n(R=B4, G=B3, B=B2)"
            ax.axis('off')
        
        elif tipo == 'false_color':
            if 'false_color' not in self.composiciones:
                self.crear_falso_color()
            ax.imshow(self.composiciones['false_color'])
            titulo = f"{self.nombre} - Falso Color (Vegetación)\n(R=B5, G=B4, B=B3)"
            ax.axis('off')
        
        elif tipo == 'geology_color':
            if 'geology_color' not in self.composiciones:
                self.crear_geologia_color()
            ax.imshow(self.composiciones['geology_color'])
            titulo = f"{self.nombre} - Composición Geológica\n(R=B7, G=B5, B=B2)"
            ax.axis('off')
        
        # Ratios
        elif tipo == 'argilica':
            if 'argilica' not in self.ratios:
                self.calcular_ratio_argilica()
            im = ax.imshow(self.ratios['argilica'], cmap='hot', vmin=0.8, vmax=1.3)
            if 'zona_argilica' in self.zonas:
                ax.contour(self.zonas['zona_argilica'], levels=[0.5], 
                          colors='cyan', linewidths=2)
            plt.colorbar(im, ax=ax, label='Ratio B6/B7')
            titulo = f"{self.nombre} - Alteración Argílica\nArcillas: Caolinita, Alunita"
            ax.axis('off')
        
        elif tipo == 'oxidos':
            if 'oxidos' not in self.ratios:
                self.calcular_ratio_oxidos()
            im = ax.imshow(self.ratios['oxidos'], cmap='YlOrRd', vmin=0.8, vmax=1.5)
            if 'zona_oxidos' in self.zonas:
                ax.contour(self.zonas['zona_oxidos'], levels=[0.5], 
                          colors='blue', linewidths=2)
            plt.colorbar(im, ax=ax, label='Ratio B4/B2')
            titulo = f"{self.nombre} - Óxidos de Hierro\nGoethita, Hematita, Limonita"
            ax.axis('off')
        
        elif tipo == 'oh':
            if 'oh' not in self.ratios:
                self.calcular_ratio_oh()
            im = ax.imshow(self.ratios['oh'], cmap='viridis', vmin=0.5, vmax=2.0)
            plt.colorbar(im, ax=ax, label='Ratio B6/B5')
            titulo = f"{self.nombre} - Minerales OH\nSericita, Epidota, Clorita"
            ax.axis('off')
        
        elif tipo == 'iah':
            if 'iah' not in self.indices:
                self.calcular_iah()
            im = ax.imshow(self.indices['iah'], cmap='plasma', vmin=1.0, vmax=3.0)
            if 'zona_iah' in self.zonas:
                ax.contour(self.zonas['zona_iah'], levels=[0.5], 
                          colors='white', linewidths=2)
            plt.colorbar(im, ax=ax, label='IAH')
            titulo = f"{self.nombre} - Índice de Alteración Hidrotermal\nIAH = (B6+B7)/B5"
            ax.axis('off')
        
        elif tipo == 'propilitica':
            if 'propilitica' not in self.ratios:
                self.calcular_propilitica()
            im = ax.imshow(self.ratios['propilitica'], cmap='viridis', vmin=0.5, vmax=1.5)
            if 'zona_propilitica' in self.zonas:
                ax.contour(self.zonas['zona_propilitica'], levels=[0.5], 
                          colors='yellow', linewidths=2)
            plt.colorbar(im, ax=ax, label='Ratio B5/B6')
            titulo = f"{self.nombre} - Alteración Propilítica\nClorita, Epidota, Calcita"
            ax.axis('off')
        
        elif tipo == 'carbonatos':
            if 'carbonatos' not in self.indices:
                self.calcular_carbonatos()
            im = ax.imshow(self.indices['carbonatos'], cmap='cool', vmin=0.3, vmax=0.7)
            if 'zona_carbonatos' in self.zonas:
                ax.contour(self.zonas['zona_carbonatos'], levels=[0.5], 
                          colors='red', linewidths=2)
            plt.colorbar(im, ax=ax, label='Índice Carbonatos')
            titulo = f"{self.nombre} - Carbonatos\nCalcita, Dolomita, Ankerita"
            ax.axis('off')
        
        elif tipo == 'ndvi':
            if 'ndvi' not in self.indices:
                self.calcular_ndvi()
            im = ax.imshow(self.indices['ndvi'], cmap='RdYlGn', vmin=-0.2, vmax=0.8)
            plt.colorbar(im, ax=ax, label='NDVI')
            titulo = f"{self.nombre} - Índice de Vegetación (NDVI)\nFiltro para análisis mineral"
            ax.axis('off')
        
        elif tipo == 'gossan':
            if 'gossan' not in self.indices:
                self.calcular_gossan()
            im = ax.imshow(self.indices['gossan'], cmap='hot', vmin=0.5, vmax=2.5)
            if 'zona_gossan' in self.zonas:
                ax.contour(self.zonas['zona_gossan'], levels=[0.5], 
                          colors='cyan', linewidths=3)
            plt.colorbar(im, ax=ax, label='Índice Gossan')
            titulo = f"{self.nombre} - GOSSAN (Alta Prioridad)\nCapas de Fe sobre sulfuros"
            ax.axis('off')
        
        elif tipo == 'clay_index':
            if 'clay_index' not in self.indices:
                self.calcular_clay_index()
            im = ax.imshow(self.indices['clay_index'], cmap='hot', vmin=0.8, vmax=2.0)
            if 'zona_clay_mejorada' in self.zonas:
                ax.contour(self.zonas['zona_clay_mejorada'], levels=[0.5], 
                          colors='lime', linewidths=2)
            plt.colorbar(im, ax=ax, label='Índice Arcillas Mejorado')
            titulo = f"{self.nombre} - Arcillas (Índice Mejorado)\nPrecisión aumentada vs B6/B7"
            ax.axis('off')
        
        elif tipo == 'objetivos':
            if 'objetivos_prioritarios' not in self.zonas:
                self.identificar_objetivos()
            
            # Falso color de ratios
            falso = np.dstack([
                self._normalizar(self.ratios.get('argilica', np.zeros_like(self.bandas['B4']))),
                self._normalizar(self.ratios.get('oh', np.zeros_like(self.bandas['B4']))),
                self._normalizar(self.ratios.get('oxidos', np.zeros_like(self.bandas['B4'])))
            ])
            ax.imshow(falso)
            
            # Overlay de objetivos
            mask = np.ma.masked_where(~self.zonas['objetivos_prioritarios'],
                                     self.zonas['objetivos_prioritarios'])
            ax.imshow(mask, cmap='Reds', alpha=0.5, vmin=0, vmax=1)
            
            titulo = f"{self.nombre} - OBJETIVOS PRIORITARIOS\nFalso Color: R=Argílica, G=OH, B=Óxidos"
            ax.axis('off')
        
        else:
            raise ValueError(f"Tipo '{tipo}' no reconocido. Opciones: natural_color, false_color, "
                           "geology_color, argilica, oxidos, oh, iah, propilitica, carbonatos, "
                           "ndvi, gossan, clay_index, objetivos")
        
        ax.set_title(titulo, fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()
        
        if guardar:
            if nombre_archivo is None:
                nombre_archivo = f"{self.nombre.lower().replace(' ','_')}_{tipo}.png"
            plt.savefig(nombre_archivo, dpi=300, bbox_inches='tight')
            print(f"  💾 Guardado: {nombre_archivo}")
        
        plt.show()
        
        return self
    
    
    def analisis_completo(self):
        """Ejecuta análisis completo de exploración minera"""
        print("\n" + "="*80)
        print("🔍 ANÁLISIS COMPLETO DE EXPLORACIÓN MINERA")
        print("="*80)
        
        # Composiciones
        self.crear_rgb_natural()
        self.crear_falso_color()
        self.crear_geologia_color()
        
        print()
        
        # Ratios básicos
        self.calcular_ratio_argilica()
        print()
        self.calcular_ratio_oxidos()
        print()
        self.calcular_ratio_oh()
        print()
        self.calcular_iah()
        
        print("\n" + "-"*80)
        print("📊 ÍNDICES AVANZADOS")
        print("-"*80)
        
        # Índices avanzados
        self.calcular_propilitica()
        print()
        self.calcular_carbonatos()
        print()
        self.calcular_ndvi()
        print()
        self.calcular_gossan()
        print()
        self.calcular_clay_index()
        
        print("\n" + "-"*80)
        
        # Objetivos
        self.identificar_objetivos()
        
        print("\n" + "="*80)
        print("✅ ANÁLISIS COMPLETADO")
        print("="*80)
        
        return self
    
    
    def exportar_todo(self, carpeta_salida: Optional[str] = None):
        """
        Exporta todas las visualizaciones generadas
        
        Args:
            carpeta_salida: Carpeta donde guardar (si None, usa directorio actual)
        """
        if carpeta_salida and not os.path.exists(carpeta_salida):
            os.makedirs(carpeta_salida)
        
        print("\n📁 Exportando resultados...")
        
        tipos = ['natural_color', 'false_color', 'geology_color',
                'argilica', 'oxidos', 'oh', 'iah', 'objetivos']
        
        for i, tipo in enumerate(tipos, 1):
            try:
                nombre = f"{i:02d}_{self.nombre.lower().replace(' ','_')}_{tipo}.png"
                if carpeta_salida:
                    nombre = os.path.join(carpeta_salida, nombre)
                self.show(tipo, guardar=True, nombre_archivo=nombre)
                plt.close()
            except Exception as e:
                print(f"  ⚠️  Error exportando {tipo}: {e}")
        
        print(f"\n✅ Exportación completada: {len(tipos)} imágenes")
        
        return self
    
    
    def resumen(self):
        """Imprime resumen del estado actual"""
        print("\n" + "="*80)
        print(f"📊 RESUMEN - {self.nombre}")
        print("="*80)
        
        print(f"\n🛰️  DATOS CARGADOS:")
        print(f"  • Bandas: {len(self.bandas)} ({', '.join(sorted(self.bandas.keys()))})")
        print(f"  • Resolución: {self.metadatos.get('resolution', 'N/A')}m/pixel")
        print(f"  • Tamaño: {self.metadatos.get('height', 'N/A')} × {self.metadatos.get('width', 'N/A')} píxeles")
        
        print(f"\n🎨 COMPOSICIONES:")
        for comp in self.composiciones:
            print(f"  ✅ {comp}")
        
        print(f"\n💎 RATIOS CALCULADOS:")
        for ratio in self.ratios:
            print(f"  ✅ {ratio}")
        
        print(f"\n🔬 ÍNDICES:")
        for indice in self.indices:
            print(f"  ✅ {indice}")
        
        print(f"\n🎯 ZONAS DETECTADAS:")
        for zona, mascara in self.zonas.items():
            area = np.sum(mascara) * (self.metadatos['resolution']**2) / 1e6
            print(f"  • {zona}: {area:.3f} km² ({np.sum(mascara)} píxeles)")
        
        print("\n" + "="*80)
        
        return self


# Ejemplo de uso
if __name__ == "__main__":
    print("\n💡 Ejemplo de uso de TerrafPR:\n")
    print("# Crear instancia")
    print("pr = TerrafPR('vfm/datos/extraido', nombre='VFM')")
    print()
    print("# Cargar bandas")
    print("pr.cargar_bandas(reducir=True, factor=4)")
    print()
    print("# Visualizaciones individuales")
    print("pr.show('natural_color')")
    print("pr.show('false_color')")
    print("pr.show('argilica')")
    print()
    print("# O análisis completo")
    print("pr.analisis_completo()")
    print("pr.show('objetivos')")
    print()
    print("# Exportar todo")
    print("pr.exportar_todo()")
