"""
TERRAF - Descarga Automática de Datos SGM
==========================================

Descarga automática de datos vectoriales del Servicio Geológico Mexicano:
- Cartas geológicas (WFS)
- Yacimientos minerales
- Magnetometría (shapefiles disponibles)
- Geofísica aérea

Autor: TERRAF
Fecha: 7 de diciembre de 2025
"""

import requests
from pathlib import Path
import zipfile
import io
import json
from owslib.wfs import WebFeatureService
import fiona
from shapely.geometry import box, shape, mapping
import matplotlib.pyplot as plt
from tqdm import tqdm
import pandas as pd

# =============================================================================
# CONFIGURACIÓN SGM
# =============================================================================

SGM_WFS_URL = "http://mapserver.sgm.gob.mx/cgi-bin/mapserv"
SGM_GEOINFOMEX = "https://mapasims.sgm.gob.mx/geoinfomex"

# Capas disponibles en WFS
CAPAS_SGM = {
    'geologia': 'geologia_1m',
    'yacimientos': 'yacimientos_minerales',
    'fallas': 'fallas_fracturas',
    'pliegues': 'pliegues',
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
        DataFrame con cartas disponibles
    """
    print("🗺️ Buscando cartas SGM disponibles...")
    
    try:
        wfs = WebFeatureService(SGM_WFS_URL, version='1.1.0')
        
        # Obtener índice de cartas
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
        print(f"  ⚠️ Error: {e}")
        return None


def descargar_geologia_sgm(bbox, output_dir='datos/sgm/geologia'):
    """
    Descarga geología del SGM por WFS.
    
    Args:
        bbox: (lon_min, lat_min, lon_max, lat_max)
        output_dir: carpeta de salida
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
            print("  ⚠️ No hay datos geológicos en esta área")
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


def descargar_magnetometria_sgm(bbox, output_dir='datos/sgm/magnetometria'):
    """
    Intenta descargar datos de magnetometría aérea del SGM.
    
    NOTA: La magnetometría no está disponible vía WFS directamente.
    Esta función busca archivos disponibles en el área.
    
    Args:
        bbox: (lon_min, lat_min, lon_max, lat_max)
        output_dir: carpeta de salida
    """
    print("🧲 Buscando magnetometría SGM...")
    
    # URLs conocidas de datasets de magnetometría
    magnetometria_urls = {
        'Sonora': 'https://mapasims.sgm.gob.mx/datos/geofisica/magnetometria/sonora.zip',
        'Chihuahua': 'https://mapasims.sgm.gob.mx/datos/geofisica/magnetometria/chihuahua.zip',
        'Durango': 'https://mapasims.sgm.gob.mx/datos/geofisica/magnetometria/durango.zip',
    }
    
    # Determinar estado aproximado por coordenadas
    lon_center = (bbox[0] + bbox[2]) / 2
    lat_center = (bbox[1] + bbox[3]) / 2
    
    estados_por_coord = {
        'Sonora': (-112, -109, 28, 31),
        'Chihuahua': (-109, -105, 26, 30),
        'Durango': (-106, -104, 23, 26),
    }
    
    estado_match = None
    for estado, (lon_min, lon_max, lat_min, lat_max) in estados_por_coord.items():
        if lon_min <= lon_center <= lon_max and lat_min <= lat_center <= lat_max:
            estado_match = estado
            break
    
    if estado_match and estado_match in magnetometria_urls:
        print(f"  📍 Área identificada como: {estado_match}")
        print(f"  ⚠️ Magnetometría SGM no tiene WFS directo")
        print(f"  💡 Puedes descargar manualmente desde:")
        print(f"     {magnetometria_urls[estado_match]}")
        print(f"  💡 O desde: https://mapasims.sgm.gob.mx/geoinfomex")
        return None
    else:
        print("  ⚠️ No se encontró dataset de magnetometría para esta área")
        print("  💡 Consulta manualmente en: https://mapasims.sgm.gob.mx/geoinfomex")
        return None


def descargar_fallas_sgm(bbox, output_dir='datos/sgm/estructuras'):
    """
    Descarga fallas y fracturas del SGM.
    
    Args:
        bbox: (lon_min, lat_min, lon_max, lat_max)
        output_dir: carpeta de salida
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


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def descargar_todo_sgm(bbox, incluir=['geologia', 'yacimientos', 'fallas'], output_base='datos/sgm'):
    """
    Descarga todos los datos SGM disponibles para un área.
    
    Args:
        bbox: (lon_min, lat_min, lon_max, lat_max)
        incluir: lista con tipos de datos ['geologia', 'yacimientos', 'fallas', 'magnetometria']
        output_base: directorio base de salida
        
    Returns:
        dict con GeoDataFrames descargados
    """
    print("="*70)
    print("🇲🇽 DESCARGA AUTOMÁTICA SGM")
    print("="*70)
    print(f"Área: {bbox}")
    print(f"Datos solicitados: {', '.join(incluir)}")
    print()
    
    datos = {}
    
    # Buscar cartas disponibles
    cartas = buscar_cartas_disponibles(bbox)
    if cartas is not None:
        datos['cartas'] = cartas
    print()
    
    # Descargar cada tipo de dato
    if 'geologia' in incluir:
        gdf = descargar_geologia_sgm(bbox, f"{output_base}/geologia")
        if gdf is not None:
            datos['geologia'] = gdf
        print()
    
    if 'yacimientos' in incluir:
        gdf = descargar_yacimientos_sgm(bbox, f"{output_base}/yacimientos")
        if gdf is not None:
            datos['yacimientos'] = gdf
        print()
    
    if 'fallas' in incluir:
        gdf = descargar_fallas_sgm(bbox, f"{output_base}/estructuras")
        if gdf is not None:
            datos['fallas'] = gdf
        print()
    
    if 'magnetometria' in incluir:
        descargar_magnetometria_sgm(bbox, f"{output_base}/magnetometria")
        print()
    
    print("="*70)
    print(f"✅ DESCARGA COMPLETA - {len(datos)} datasets obtenidos")
    print("="*70)
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
                x, y = geom.exterior.xy if hasattr(geom, 'exterior') else ([], [])
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


if __name__ == "__main__":
    # Test con área de estudio (Norte de México)
    bbox = (-106.0, 28.0, -104.0, 29.0)
    
    print("="*80)
    print("DESCARGA AUTOMÁTICA DE DATOS SGM")
    print("="*80)
    print(f"\n📍 Área de estudio: {bbox}")
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
