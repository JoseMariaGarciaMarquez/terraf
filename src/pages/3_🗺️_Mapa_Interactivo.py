"""
TERRAF - Mapa Interactivo
=========================

Visualización interactiva de:
- Landsat 9 (escena T13RDN)
- Análisis mineral (ratios, gossan, alteración)
- Magnetometría

Autor: TERRAF
Fecha: 4 de diciembre de 2025
"""

import streamlit as st
from pathlib import Path
import folium
from streamlit_folium import st_folium
import rasterio
import numpy as np
from branca.colormap import LinearColormap
import fiona
from shapely.geometry import shape
from pyproj import Transformer
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Mapa Interactivo - TERRAF",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Mapa Interactivo: Landsat + Mineral + Magnetometría")
st.markdown("---")

@st.cache_resource
def crear_mapa_interactivo():
    """Crea el mapa interactivo con todas las capas."""
    
    # Directorios
    landsat_dir = Path('datos/landsat9')
    mineral_dir = Path('resultados/mineral')
    magne_path = Path('datos/magnetometria/Carta/D01122025163452P/CampoMagnetico_H13_11.shp')
    
    # Buscar escena 1 (T13RDN)
    archivos_t13rdn = list(landsat_dir.glob('*T13RDN*.tif'))
    
    if not archivos_t13rdn:
        st.error("❌ No se encontró Escena 1 (T13RDN)")
        return None
    
    # Organizar bandas
    bandas_dict = {}
    for archivo in archivos_t13rdn:
        banda = archivo.stem.split('.')[-1]
        if banda in ['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07']:
            bandas_dict[banda] = archivo
    
    # Obtener centro en WGS84
    with rasterio.open(bandas_dict['B04']) as src:
        bounds = src.bounds
        transformer = Transformer.from_crs("EPSG:32613", "EPSG:4326", always_xy=True)
        west, south = transformer.transform(bounds.left, bounds.bottom)
        east, north = transformer.transform(bounds.right, bounds.top)
    
    center_lon = (west + east) / 2
    center_lat = (south + north) / 2
    
    # Crear mapa base
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        tiles=None
    )
    
    # Capas base
    folium.TileLayer('OpenStreetMap', name='Calles', overlay=False, control=True).add_to(m)
    folium.TileLayer('CartoDB positron', name='Claro', overlay=False, control=True).add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satélite',
        overlay=False,
        control=True
    ).add_to(m)
    
    # Agregar magnetometría
    if magne_path.exists():
        try:
            with fiona.open(magne_path) as src:
                features = list(src)
                
                feature_group = folium.FeatureGroup(name='🧲 Magnetometría', show=True)
                
                for feature in features:
                    folium.GeoJson(
                        feature,
                        style_function=lambda x: {
                            'color': 'red',
                            'weight': 1.5,
                            'fillOpacity': 0.2,
                            'fillColor': 'orange'
                        }
                    ).add_to(feature_group)
                
                feature_group.add_to(m)
        except Exception as e:
            st.warning(f"⚠️ No se pudo cargar magnetometría: {e}")
    
    # Agregar ratios minerales
    ratios_mineral = [
        ('FeOxidos_T13RDN_2023002.tif', '🔴 Óxidos de Hierro', 'YlOrRd', 0.8, 2.0),
        ('Gossan_T13RDN_2023002.tif', '🟠 Gossan', 'hot', 1.2, 2.5),
        ('Hidrotermal_T13RDN_2023002.tif', '💎 Alteración Hidrotermal', 'RdPu', 0.9, 1.3),
        ('Arcillas_T13RDN_2023002.tif', '🟤 Arcillas', 'YlGnBu', 0.7, 1.5),
        ('Carbonatos_T13RDN_2023002.tif', '⚪ Carbonatos', 'Greys', 0.9, 1.3),
    ]
    
    for filename, nombre, cmap, vmin_val, vmax_val in ratios_mineral:
        ratio_file = mineral_dir / filename
        
        if ratio_file.exists():
            try:
                with rasterio.open(ratio_file) as src:
                    ratio = src.read(1).astype(float)
                    bounds_utm = src.bounds
                    
                    transformer = Transformer.from_crs("EPSG:32613", "EPSG:4326", always_xy=True)
                    west_r, south_r = transformer.transform(bounds_utm.left, bounds_utm.bottom)
                    east_r, north_r = transformer.transform(bounds_utm.right, bounds_utm.top)
                
                # Normalizar
                ratio_norm = (ratio - vmin_val) / (vmax_val - vmin_val)
                ratio_norm = np.clip(ratio_norm, 0, 1)
                
                # Reducir resolución
                factor = 6
                ratio_small = ratio_norm[::factor, ::factor]
                
                folium.raster_layers.ImageOverlay(
                    image=ratio_small,
                    bounds=[[south_r, west_r], [north_r, east_r]],
                    opacity=0.6,
                    name=nombre,
                    show=False,
                    colormap=lambda x: plt.colormaps[cmap](x)
                ).add_to(m)
                
            except Exception as e:
                st.warning(f"⚠️ No se pudo cargar {nombre}: {e}")
    
    # Agregar marcador central
    folium.Marker(
        location=[center_lat, center_lon],
        popup=f'Centro: {center_lat:.4f}°, {center_lon:.4f}°',
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)
    
    # Controles
    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    
    from folium import plugins
    plugins.MiniMap(toggle_display=True).add_to(m)
    plugins.MeasureControl(position='topleft', primary_length_unit='meters').add_to(m)
    plugins.MousePosition().add_to(m)
    plugins.Fullscreen().add_to(m)
    
    return m

# Descripción
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.info("""
    ### 🎯 Controles del Mapa
    
    - **Panel derecho**: Activa/desactiva capas
    - **🧲 Magnetometría**: Polígonos de anomalías magnéticas
    - **⛏️ Ratios minerales**: Overlays semi-transparentes
    - **📏 Medición**: Herramienta superior izquierda
    - **🔍 Zoom**: Rueda del ratón
    - **🖱️ Coordenadas**: Esquina inferior
    """)

# Crear y mostrar mapa
with st.spinner("🗺️ Cargando mapa interactivo..."):
    mapa = crear_mapa_interactivo()
    
    if mapa:
        st_folium(mapa, width=1400, height=700)
    else:
        st.error("❌ No se pudo crear el mapa")

# Información adicional
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 🔴 Óxidos de Hierro
    - Ratio: B04/B02
    - Detecta: Hematita, Goethita
    - Uso: Zonas oxidadas
    """)

with col2:
    st.markdown("""
    ### 🟠 Gossan
    - Ratio: (B04+B05)/B03
    - Detecta: Caps de sulfuros oxidados
    - Uso: Exploración mineral
    """)

with col3:
    st.markdown("""
    ### 💎 Alteración Hidrotermal
    - Ratio: B06/B07
    - Detecta: Arcillas, alunita
    - Uso: Sistemas epitermales
    """)

st.markdown("---")

# Footer
st.caption("""
**TERRAF** - Análisis de percepción remota para exploración minera  
Escena: HLS L30 T13RDN (2 Enero 2023) | CRS: UTM Zone 13N → WGS84
""")
