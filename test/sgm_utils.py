"""
TERRAF - Descarga Automática de Datos SGM
==========================================

Descarga automática de datos vectoriales del Servicio Geológico Mexicano:
- Cartas geológicas (WFS) - ⚠️ SERVICIO NO DISPONIBLE
- Yacimientos minerales - ⚠️ SERVICIO NO DISPONIBLE  
- Fallas y fracturas - ⚠️ SERVICIO NO DISPONIBLE
- Magnetometría (URLs de descarga manual por estado)

ESTADO ACTUAL (7 dic 2025):
--------------------------
El servicio WFS del SGM (http://mapserver.sgm.gob.mx/) retorna Error 404.
Posibles causas:
1. URL del servicio ha cambiado
2. Servicio temporalmente fuera de línea
3. Requiere autenticación o parámetros adicionales

ALTERNATIVAS:
------------
1. Descarga manual desde GeoInfoMEX:
   https://mapasims.sgm.gob.mx/geoinfomex
   
2. Visualización (WMS, no descarga):
   http://mapserver.sgm.gob.mx/ (servicios WMS disponibles)
   
3. Magnetometría por estado (funcional):
   - Sonora: https://mapasims.sgm.gob.mx/datos/geofisica/magnetometria/sonora.zip
   - Chihuahua: https://mapasims.sgm.gob.mx/datos/geofisica/magnetometria/chihuahua.zip
   - Durango: https://mapasims.sgm.gob.mx/datos/geofisica/magnetometria/durango.zip

Autor: TERRAF
Fecha: 7 de diciembre de 2025
"""

import requests
from pathlib import Path
import json
import zipfile
import io
from owslib.wfs import WebFeatureService
import fiona
from shapely.geometry import shape, box
import matplotlib.pyplot as plt
import pandas as pd
from tqdm import tqdm

# =============================================================================
# CONFIGURACIÓN SGM
# =============================================================================

# NOTA: El servicio WFS del SGM no está respondiendo correctamente (Error 404)
# La URL puede haber cambiado o el servicio puede estar temporalmente fuera de línea.
# Alternativas:
# 1. Descargar datos manualmente desde: https://mapasims.sgm.gob.mx/geoinfomex
# 2. Verificar URLs actualizadas en: https://www.sgm.gob.mx/
# 3. Usar servicios WMS para visualización (no descarga): http://mapserver.sgm.gob.mx/

SGM_WFS_URL = "http://mapserver.sgm.gob.mx/cgi-bin/mapserv"  # ⚠️ No funcional
SGM_GEOINFOMEX = "https://mapasims.sgm.gob.mx/geoinfomex"

# Capas disponibles en WFS
CAPAS_SGM = {
    'geologia': 'geologia_1m',
    'yacimientos': 'yacimientos_minerales',
    'fallas': 'fallas_fracturas',
    'cartas': 'cartas_geologicas_50k'
}


# =============================================================================
# FUNCIONES DE DESCARGA
# =============================================================================

def buscar_cartas_disponibles(bbox):
    """
    Busca qué cartas SGM cubren el área de interés.
    
    Args:
        bbox: (lon_min, lat_min, lon_max, lat_max)
    
    Returns:
        list: Features GeoJSON de cartas disponibles
    """
    print("🗺️ Buscando cartas SGM disponibles...")
    
    try:
        wfs = WebFeatureService(SGM_WFS_URL, version='1.1.0')
        bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
        
        response = wfs.getfeature(
            typename='cartas_geologicas_50k',
            bbox=bbox_str,
            outputFormat='json'
        )
        
        data = json.loads(response.read())
        features = data.get('features', [])
        
        print(f"  ✅ Encontradas {len(features)} cartas")
        
        if len(features) > 0:
            print("\nCartas disponibles:")
            for feature in features:
                props = feature.get('properties', {})
                clave = props.get('CLAVE', 'N/A')
                nombre = props.get('NOMBRE', 'N/A')
                print(f"  • {clave}: {nombre}")
        
        return features
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def descargar_geologia_sgm(bbox, output_dir='datos/sgm/geologia'):
    """
    Descarga polígonos de geología del SGM.
    
    Args:
        bbox: (lon_min, lat_min, lon_max, lat_max)
        output_dir: carpeta de salida
    
    Returns:
        list: Features GeoJSON descargados
    """
    print("🪨 Descargando geología SGM...")
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        wfs = WebFeatureService(SGM_WFS_URL, version='1.1.0')
        bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
        
        response = wfs.getfeature(
            typename='geologia_1m',
            bbox=bbox_str,
            outputFormat='json'
        )
        
        data = json.loads(response.read())
        features = data.get('features', [])
        
        if len(features) > 0:
            output_file = Path(output_dir) / 'geologia_sgm.geojson'
            
            with open(output_file, 'w') as f:
                json.dump(data, f)
            
            print(f"  ✅ {len(features)} polígonos descargados")
            print(f"  💾 Guardado: {output_file}")
            
            # Estadísticas
            eras = [f['properties'].get('ERA') for f in features if 'ERA' in f.get('properties', {})]
            if eras:
                print("\n  📊 Unidades geológicas por era:")
                df_eras = pd.Series(eras).value_counts()
                print(df_eras.head())
            
            return features
        else:
            print("  ⚠️ No hay geología mapeada en esta área")
            return None
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def descargar_yacimientos_sgm(bbox, output_dir='datos/sgm/yacimientos'):
    """
    Descarga yacimientos minerales del SGM.
    
    Args:
        bbox: (lon_min, lat_min, lon_max, lat_max)
        output_dir: carpeta de salida
    
    Returns:
        list: Features GeoJSON descargados
    """
    print("⛏️ Descargando yacimientos minerales SGM...")
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        wfs = WebFeatureService(SGM_WFS_URL, version='1.1.0')
        bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
        
        response = wfs.getfeature(
            typename='yacimientos_minerales',
            bbox=bbox_str,
            outputFormat='json'
        )
        
        data = json.loads(response.read())
        features = data.get('features', [])
        
        if len(features) > 0:
            output_file = Path(output_dir) / 'yacimientos_sgm.geojson'
            
            with open(output_file, 'w') as f:
                json.dump(data, f)
            
            print(f"  ✅ {len(features)} yacimientos descargados")
            print(f"  💾 Guardado: {output_file}")
            
            # Estadísticas
            sustancias = [f['properties'].get('SUSTANCIA') for f in features if 'SUSTANCIA' in f.get('properties', {})]
            if sustancias:
                print("\n  📊 Principales sustancias:")
                df_sust = pd.Series(sustancias).value_counts()
                print(df_sust.head(10))
            
            return features
        else:
            print("  ⚠️ No hay yacimientos registrados en esta área")
            return None
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def descargar_fallas_sgm(bbox, output_dir='datos/sgm/estructuras'):
    """
    Descarga fallas y fracturas del SGM.
    
    Args:
        bbox: (lon_min, lat_min, lon_max, lat_max)
        output_dir: carpeta de salida
    
    Returns:
        list: Features GeoJSON descargados
    """
    print("🔴 Descargando fallas y fracturas SGM...")
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        wfs = WebFeatureService(SGM_WFS_URL, version='1.1.0')
        bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
        
        response = wfs.getfeature(
            typename='fallas_fracturas',
            bbox=bbox_str,
            outputFormat='json'
        )
        
        data = json.loads(response.read())
        features = data.get('features', [])
        
        if len(features) > 0:
            output_file = Path(output_dir) / 'fallas_sgm.geojson'
            
            with open(output_file, 'w') as f:
                json.dump(data, f)
            
            print(f"  ✅ {len(features)} fallas descargadas")
            print(f"  💾 Guardado: {output_file}")
            
            return features
        else:
            print("  ⚠️ No hay fallas mapeadas en esta área")
            return None
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def descargar_magnetometria_sgm(bbox, output_dir='datos/sgm/magnetometria', auto_download=True):
    """
    Descarga automáticamente datos de magnetometría aérea del SGM por estado.
    
    Args:
        bbox: (lon_min, lat_min, lon_max, lat_max)
        output_dir: carpeta de salida
        auto_download: Si True, descarga automáticamente el ZIP del estado
    
    Returns:
        str: Path al shapefile descargado y filtrado por bbox, o None
    """
    print("🧲 Descargando magnetometría SGM...")
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # URLs conocidas de datasets de magnetometría
    magnetometria_urls = {
        'Sonora': 'https://mapasims.sgm.gob.mx/datos/geofisica/magnetometria/sonora.zip',
        'Chihuahua': 'https://mapasims.sgm.gob.mx/datos/geofisica/magnetometria/chihuahua.zip',
        'Durango': 'https://mapasims.sgm.gob.mx/datos/geofisica/magnetometria/durango.zip',
    }
    
    # Determinar estado por coordenadas del centro
    center_lon = (bbox[0] + bbox[2]) / 2
    center_lat = (bbox[1] + bbox[3]) / 2
    
    estado_match = None
    if center_lon > -111 and center_lon < -109 and center_lat > 28 and center_lat < 32:
        estado_match = 'Sonora'
    elif center_lon > -109 and center_lon < -104 and center_lat > 26 and center_lat < 31:
        estado_match = 'Chihuahua'
    elif center_lon > -107 and center_lon < -103 and center_lat > 22 and center_lat < 27:
        estado_match = 'Durango'
    
    if not estado_match:
        print("  ⚠️ No se encontró dataset de magnetometría para esta área")
        return None
    
    print(f"  📍 Área en {estado_match}")
    
    if not auto_download:
        print(f"  📥 Descarga manual: {magnetometria_urls[estado_match]}")
        return None
    
    try:
        # Descargar ZIP
        url = magnetometria_urls[estado_match]
        print(f"  📥 Descargando desde {url}...")
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        # Descargar con barra de progreso
        zip_data = io.BytesIO()
        with tqdm(total=total_size, unit='B', unit_scale=True, desc=estado_match) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                zip_data.write(chunk)
                pbar.update(len(chunk))
        
        # Extraer ZIP
        print(f"  📦 Extrayendo archivos...")
        zip_data.seek(0)
        with zipfile.ZipFile(zip_data) as zf:
            zf.extractall(output_dir)
        
        # Buscar shapefiles en el directorio
        shapefiles = list(Path(output_dir).rglob('*.shp'))
        
        if not shapefiles:
            print("  ⚠️ No se encontraron shapefiles en el ZIP")
            return None
        
        print(f"  ✅ Encontrados {len(shapefiles)} shapefiles")
        
        # Filtrar por bbox
        bbox_geom = box(bbox[0], bbox[1], bbox[2], bbox[3])
        filtered_features = []
        
        for shp in shapefiles:
            try:
                with fiona.open(shp, 'r') as src:
                    for feature in src:
                        geom = shape(feature['geometry'])
                        if geom.intersects(bbox_geom):
                            filtered_features.append(feature)
            except Exception as e:
                print(f"  ⚠️ Error leyendo {shp.name}: {e}")
        
        if filtered_features:
            # Guardar features filtrados
            output_file = Path(output_dir) / f'magnetometria_{estado_match}_filtrada.geojson'
            
            geojson = {
                'type': 'FeatureCollection',
                'features': filtered_features
            }
            
            with open(output_file, 'w') as f:
                json.dump(geojson, f)
            
            print(f"  ✅ {len(filtered_features)} polígonos en el área de interés")
            print(f"  💾 Guardado: {output_file}")
            
            return str(output_file)
        else:
            print("  ⚠️ No hay datos de magnetometría en el área especificada")
            return None
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def descargar_todo_sgm(bbox, incluir=['geologia', 'yacimientos', 'fallas'], 
                       output_base='datos/sgm'):
    """
    Descarga todos los datos SGM disponibles para un área.
    
    Args:
        bbox: (lon_min, lat_min, lon_max, lat_max)
        incluir: lista de tipos de datos a descargar
        output_base: carpeta base de salida
    
    Returns:
        dict: {nombre: features} con todos los datos descargados
    """
    datos = {}
    
    print(f"\n{'='*80}")
    print(f"DESCARGANDO DATOS SGM")
    print(f"{'='*80}")
    print(f"Área: {bbox}")
    print(f"Tipos solicitados: {', '.join(incluir)}\n")
    
    # Buscar cartas primero
    cartas = buscar_cartas_disponibles(bbox)
    if cartas:
        datos['cartas'] = cartas
    print()
    
    # Descargar cada tipo solicitado
    if 'geologia' in incluir:
        geologia = descargar_geologia_sgm(bbox, f"{output_base}/geologia")
        if geologia:
            datos['geologia'] = geologia
        print()
    
    if 'yacimientos' in incluir:
        yacimientos = descargar_yacimientos_sgm(bbox, f"{output_base}/yacimientos")
        if yacimientos:
            datos['yacimientos'] = yacimientos
        print()
    
    if 'fallas' in incluir:
        fallas = descargar_fallas_sgm(bbox, f"{output_base}/estructuras")
        if fallas:
            datos['fallas'] = fallas
        print()
    
    if 'magnetometria' in incluir:
        descargar_magnetometria_sgm(bbox, f"{output_base}/magnetometria")
        print()
    
    print(f"{'='*80}")
    print(f"✅ DESCARGA COMPLETADA")
    print(f"{'='*80}")
    print(f"Datasets descargados: {len(datos)}")
    for nombre, features in datos.items():
        print(f"  • {nombre}: {len(features)} elementos")
    print()
    
    return datos


def visualizar_datos_sgm(datos, bbox=None, output_file='resultados/sgm_overview.png'):
    """
    Visualiza todos los datos SGM descargados.
    
    Args:
        datos: dict con features GeoJSON de descargar_todo_sgm()
        bbox: opcional, para mostrar área de interés
        output_file: ruta de salida
    """
    n_datasets = len(datos)
    if n_datasets == 0:
        print("⚠️ No hay datos para visualizar")
        return
    
    fig, axes = plt.subplots(1, n_datasets, figsize=(6*n_datasets, 6))
    if n_datasets == 1:
        axes = [axes]
    
    for i, (nombre, features) in enumerate(datos.items()):
        ax = axes[i]
        
        for feature in features:
            geom = shape(feature['geometry'])
            
            if nombre == 'cartas':
                x, y = geom.exterior.xy
                ax.plot(x, y, color='blue', linewidth=1)
                ax.set_title('Cartas SGM', fontweight='bold')
            
            elif nombre == 'geologia':
                if hasattr(geom, 'exterior'):
                    x, y = geom.exterior.xy
                    ax.fill(x, y, alpha=0.5)
                ax.set_title('Geología', fontweight='bold')
            
            elif nombre == 'yacimientos':
                ax.plot(geom.x, geom.y, 'ro', markersize=8, alpha=0.7)
                ax.set_title(f'Yacimientos ({len(features)})', fontweight='bold')
            
            elif nombre == 'fallas':
                if geom.geom_type == 'LineString':
                    x, y = geom.xy
                    ax.plot(x, y, color='darkred', linewidth=2, alpha=0.8)
                ax.set_title(f'Fallas ({len(features)})', fontweight='bold')
        
        ax.set_xlabel('Longitud')
        ax.set_ylabel('Latitud')
        ax.grid(True, alpha=0.3)
        
        # Bbox si se proporciona
        if bbox:
            from matplotlib.patches import Rectangle
            rect = Rectangle((bbox[0], bbox[1]), bbox[2]-bbox[0], bbox[3]-bbox[1],
                           linewidth=2, edgecolor='red', facecolor='none', linestyle='--')
            ax.add_patch(rect)
    
    plt.tight_layout()
    
    Path(output_file).parent.mkdir(exist_ok=True, parents=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Visualización guardada: {output_file}")
    plt.show()


# =============================================================================
# MAIN - EJEMPLO DE USO
# =============================================================================

if __name__ == "__main__":
    # Área de ejemplo (norte de México - Chihuahua/Durango)
    bbox = (-106.0, 28.0, -104.0, 29.0)
    
    # Descargar datos
    datos = descargar_todo_sgm(
        bbox,
        incluir=['geologia', 'yacimientos', 'fallas', 'magnetometria']
    )
    
    # Visualizar
    if datos:
        visualizar_datos_sgm(datos, bbox=bbox)
