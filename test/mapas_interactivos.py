"""
TERRAF - Mapas Interactivos
============================

Script unificado para crear mapas interactivos con Folium:
- Landsat + ratios minerales
- Magnetometría
- ICESat-2
- Correlaciones

Autor: TERRAF
Fecha: 5 de diciembre de 2025
"""

import folium
from folium import plugins
import rasterio
import numpy as np
from pathlib import Path
from branca.colormap import LinearColormap
import fiona
from pyproj import Transformer
import matplotlib.pyplot as plt

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def transformar_bounds_utm_a_wgs84(bounds_utm, crs='EPSG:32613'):
    """Transforma bounds de UTM a WGS84."""
    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    west, south = transformer.transform(bounds_utm.left, bounds_utm.bottom)
    east, north = transformer.transform(bounds_utm.right, bounds_utm.top)
    return (west, south, east, north)


def crear_mapa_base(center_lat, center_lon):
    """Crea mapa base con capas estándar."""
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles=None)
    
    folium.TileLayer('OpenStreetMap', name='Calles', overlay=False).add_to(m)
    folium.TileLayer('CartoDB positron', name='Claro', overlay=False).add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Satélite', overlay=False
    ).add_to(m)
    
    return m


# =============================================================================
# CAPAS DE DATOS
# =============================================================================

def agregar_magnetometria(mapa, shapefile_path):
    """Agrega capa de magnetometría con colores por código."""
    
    if not shapefile_path.exists():
        print(f"  ⚠️ No se encuentra: {shapefile_path}")
        return
    
    print("  🧲 Agregando magnetometría...")
    
    with fiona.open(shapefile_path) as src:
        features = list(src)
        
        if not features:
            return
        
        props = features[0]['properties']
        campo_codigo = None
        for col in ['RANGO_CODE', 'CODIGO', 'CODE']:
            if col in props:
                campo_codigo = col
                break
        
        if campo_codigo:
            valores = [f['properties'].get(campo_codigo) for f in features if f['properties'].get(campo_codigo) is not None]
            valores_unicos = sorted(set(valores))
            
            colores = ['#0000ff', '#00ffff', '#00ff00', '#ffff00', '#ff7700', '#ff0000']
            color_map = {val: colores[i % len(colores)] for i, val in enumerate(valores_unicos)}
            
            feature_group = folium.FeatureGroup(name='🧲 Magnetometría', show=True)
            
            for feature in features:
                valor = feature['properties'].get(campo_codigo)
                if valor is not None:
                    color = color_map.get(valor, '#888888')
                    
                    folium.GeoJson(
                        feature,
                        style_function=lambda x, c=color: {
                            'fillColor': c,
                            'color': '#000000',
                            'weight': 0.3,
                            'fillOpacity': 0.7
                        },
                        tooltip=f"Código: {valor}"
                    ).add_to(feature_group)
            
            feature_group.add_to(mapa)
            
            # Leyenda
            legend_html = '''<div style="position: fixed; bottom: 50px; right: 50px; z-index:9999; 
                        background-color: white; padding: 10px; border: 2px solid grey; border-radius: 5px;">
            <p style="margin:0; font-weight:bold;">Magnetometría</p>'''
            for val in valores_unicos[:10]:  # Limitar a 10 para no saturar
                color = color_map[val]
                legend_html += f'<p style="margin:2px;"><span style="background-color:{color}; padding:3px 10px;">&nbsp;</span> Código {val}</p>'
            legend_html += '</div>'
            mapa.get_root().html.add_child(folium.Element(legend_html))
            
            print(f"    ✓ {len(features)} polígonos")


def agregar_ratio_landsat(mapa, ratio_file, nombre, colormap='YlOrRd', vmin=None, vmax=None):
    """Agrega ratio mineral como overlay."""
    
    if not ratio_file.exists():
        return
    
    try:
        with rasterio.open(ratio_file) as src:
            ratio = src.read(1).astype(float)
            bounds_utm = src.bounds
        
        bounds_wgs84 = transformar_bounds_utm_a_wgs84(bounds_utm)
        
        if vmin is None:
            vmin = np.nanpercentile(ratio, 5)
        if vmax is None:
            vmax = np.nanpercentile(ratio, 95)
        
        ratio_norm = (ratio - vmin) / (vmax - vmin)
        ratio_norm = np.clip(ratio_norm, 0, 1)
        
        # Reducir resolución
        factor = 6
        ratio_small = ratio_norm[::factor, ::factor]
        
        folium.raster_layers.ImageOverlay(
            image=ratio_small,
            bounds=[[bounds_wgs84[1], bounds_wgs84[0]], [bounds_wgs84[3], bounds_wgs84[2]]],
            opacity=0.6,
            name=nombre,
            show=False,
            colormap=lambda x: plt.colormaps[colormap](x)
        ).add_to(mapa)
        
        print(f"    ✓ {nombre}")
        
    except Exception as e:
        print(f"    ❌ {nombre}: {e}")


# =============================================================================
# MAPAS PRINCIPALES
# =============================================================================

def crear_mapa_landsat_mineral(output_file='resultados/mapa_landsat_mineral.html'):
    """Mapa con Landsat + ratios minerales + magnetometría."""
    
    print("🗺️ Creando mapa Landsat + Mineral + Magnetometría...")
    
    # Buscar escena T13RDN
    landsat_dir = Path('datos/landsat9')
    archivos = list(landsat_dir.glob('*T13RDN*B04*.tif'))
    
    if not archivos:
        print("❌ No se encontró escena T13RDN")
        return
    
    # Obtener centro
    with rasterio.open(archivos[0]) as src:
        bounds = src.bounds
        bounds_wgs84 = transformar_bounds_utm_a_wgs84(bounds)
    
    center_lon = (bounds_wgs84[0] + bounds_wgs84[2]) / 2
    center_lat = (bounds_wgs84[1] + bounds_wgs84[3]) / 2
    
    # Crear mapa
    m = crear_mapa_base(center_lat, center_lon)
    
    # Magnetometría
    magne_path = Path('datos/magnetometria/Carta/D01122025163452P/CampoMagnetico_H13_11.shp')
    agregar_magnetometria(m, magne_path)
    
    # Ratios minerales
    mineral_dir = Path('resultados/mineral')
    ratios = [
        ('FeOxidos_T13RDN_2023002.tif', '🔴 Óxidos de Hierro', 'YlOrRd', 0.8, 2.0),
        ('Gossan_T13RDN_2023002.tif', '🟠 Gossan', 'hot', 1.2, 2.5),
        ('Hidrotermal_T13RDN_2023002.tif', '💎 Hidrotermal', 'RdPu', 0.9, 1.3),
        ('Arcillas_T13RDN_2023002.tif', '🟤 Arcillas', 'YlGnBu', 0.7, 1.5),
    ]
    
    print("  ⛏️ Agregando ratios minerales...")
    for filename, nombre, cmap, vmin, vmax in ratios:
        agregar_ratio_landsat(m, mineral_dir / filename, nombre, cmap, vmin, vmax)
    
    # Marcador central
    folium.Marker(
        [center_lat, center_lon],
        popup=f'{center_lat:.4f}°, {center_lon:.4f}°',
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)
    
    # Controles
    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    plugins.MiniMap().add_to(m)
    plugins.MeasureControl(position='topleft').add_to(m)
    plugins.MousePosition().add_to(m)
    plugins.Fullscreen().add_to(m)
    
    # Guardar
    Path(output_file).parent.mkdir(exist_ok=True, parents=True)
    m.save(str(output_file))
    
    print(f"✅ Mapa guardado: {output_file}")
    return m


# =============================================================================
# MAIN - EJEMPLO DE USO
# =============================================================================

if __name__ == "__main__":
    print("="*70)
    print("🗺️ TERRAF - Mapas Interactivos")
    print("="*70)
    
    mapa = crear_mapa_landsat_mineral()
    
    if mapa:
        # Abrir en navegador
        import webbrowser
        webbrowser.open('resultados/mapa_landsat_mineral.html')
