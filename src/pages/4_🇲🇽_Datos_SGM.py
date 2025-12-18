"""
Página de Streamlit para descarga automática de datos del SGM
"""

import streamlit as st
import sys
from pathlib import Path

# Agregar directorio test al path
test_dir = Path(__file__).parent.parent.parent / 'test'
sys.path.insert(0, str(test_dir))

try:
    from sgm_utils import descargar_magnetometria_sgm
    import folium
    from streamlit_folium import st_folium
    import json
    SGM_AVAILABLE = True
except ImportError as e:
    SGM_AVAILABLE = False
    import_error = str(e)

st.set_page_config(
    page_title="Datos SGM - TERRAF",
    page_icon="🇲🇽",
    layout="wide"
)

st.title("🇲🇽 Datos del Servicio Geológico Mexicano")
st.markdown("---")

if not SGM_AVAILABLE:
    st.error(f"❌ Error al importar módulos necesarios: {import_error}")
    st.stop()

# Información
with st.expander("ℹ️ Acerca de esta herramienta", expanded=False):
    st.markdown("""
    Esta página permite descargar automáticamente datos geológicos del SGM:
    
    **Disponibles:**
    - 🧲 **Magnetometría aérea** (Sonora, Chihuahua, Durango)
    
    **No disponibles temporalmente (WFS fuera de línea):**
    - 🪨 Geología regional
    - ⛏️ Yacimientos minerales
    - 🔴 Fallas y fracturas
    
    **Cómo usar:**
    1. Define tu área de interés en el mapa (dibuja un rectángulo)
    2. Haz clic en "Descargar Datos SGM"
    3. Los datos se filtran automáticamente a tu área
    4. Visualiza los resultados en el mapa
    """)

# Sidebar para configuración
st.sidebar.header("⚙️ Configuración")

# Método de selección de área
metodo_seleccion = st.sidebar.radio(
    "Método de selección de área:",
    ["Coordenadas manuales", "Dibujar en mapa"],
    index=0
)

# Inicializar session state
if 'bbox' not in st.session_state:
    st.session_state.bbox = None
if 'magnetometria_path' not in st.session_state:
    st.session_state.magnetometria_path = None

# Área de trabajo
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📍 1. Define el Área de Interés")
    
    if metodo_seleccion == "Coordenadas manuales":
        st.info("Ingresa las coordenadas del área (grados decimales)")
        
        col_lon, col_lat = st.columns(2)
        
        with col_lon:
            lon_min = st.number_input("Longitud mínima", value=-106.0, step=0.1, format="%.4f")
            lon_max = st.number_input("Longitud máxima", value=-104.0, step=0.1, format="%.4f")
        
        with col_lat:
            lat_min = st.number_input("Latitud mínima", value=28.0, step=0.1, format="%.4f")
            lat_max = st.number_input("Latitud máxima", value=29.0, step=0.1, format="%.4f")
        
        bbox = (lon_min, lat_min, lon_max, lat_max)
        st.session_state.bbox = bbox
        
        # Validación
        if lon_min >= lon_max or lat_min >= lat_max:
            st.error("⚠️ Las coordenadas mínimas deben ser menores que las máximas")
        else:
            area_km2 = abs(lon_max - lon_min) * 111 * abs(lat_max - lat_min) * 111
            st.success(f"✅ Área aproximada: {area_km2:,.0f} km²")
    
    else:  # Dibujar en mapa
        st.info("Dibuja un rectángulo en el mapa de la derecha →")
        st.markdown("*Función de dibujo en desarrollo*")
        bbox = st.session_state.bbox if st.session_state.bbox else (-106.0, 28.0, -104.0, 29.0)

with col2:
    st.subheader("🗺️ Mapa de Referencia")
    
    # Crear mapa centrado en México
    center_lat = (bbox[1] + bbox[3]) / 2
    center_lon = (bbox[0] + bbox[2]) / 2
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=7,
        tiles='OpenStreetMap'
    )
    
    # Agregar rectángulo del área
    folium.Rectangle(
        bounds=[[bbox[1], bbox[0]], [bbox[3], bbox[2]]],
        color='red',
        fill=True,
        fillOpacity=0.2,
        popup=f"Área de interés<br>{abs(bbox[2]-bbox[0]):.2f}° × {abs(bbox[3]-bbox[1]):.2f}°"
    ).add_to(m)
    
    # Agregar marcador del centro
    folium.Marker(
        [center_lat, center_lon],
        popup=f"Centro: {center_lat:.4f}, {center_lon:.4f}",
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)
    
    # Mostrar mapa
    st_folium(m, width=700, height=400)

# Sección de descarga
st.markdown("---")
st.subheader("📥 2. Descargar Datos SGM")

col_desc1, col_desc2 = st.columns([2, 1])

with col_desc1:
    st.markdown("""
    Los siguientes datos están disponibles para descarga automática:
    
    - 🧲 **Magnetometría aérea** (Sonora, Chihuahua, Durango)
      - Descarga automática del ZIP por estado
      - Filtrado automático por área de interés
      - Formato: GeoJSON
    """)

with col_desc2:
    # Detectar estado
    center_lon = (bbox[0] + bbox[2]) / 2
    center_lat = (bbox[1] + bbox[3]) / 2
    
    estado = "Desconocido"
    if center_lon > -111 and center_lon < -109 and center_lat > 28 and center_lat < 32:
        estado = "Sonora"
    elif center_lon > -109 and center_lon < -104 and center_lat > 26 and center_lat < 31:
        estado = "Chihuahua"
    elif center_lon > -107 and center_lon < -103 and center_lat > 22 and center_lat < 27:
        estado = "Durango"
    
    st.info(f"**Estado detectado:** {estado}")

# Botón de descarga
if st.button("🚀 Descargar Magnetometría SGM", type="primary", use_container_width=True):
    with st.spinner("Descargando y procesando datos..."):
        try:
            # Descargar magnetometría
            mag_path = descargar_magnetometria_sgm(
                bbox=bbox,
                output_dir='datos/sgm/magnetometria',
                auto_download=True
            )
            
            if mag_path:
                st.session_state.magnetometria_path = mag_path
                st.success(f"✅ ¡Descarga completada! Archivo: `{mag_path}`")
            else:
                st.warning("⚠️ No se encontraron datos para esta área")
                
        except Exception as e:
            st.error(f"❌ Error durante la descarga: {e}")
            st.exception(e)

# Visualización de resultados
if st.session_state.magnetometria_path:
    st.markdown("---")
    st.subheader("📊 3. Resultados")
    
    mag_path = Path(st.session_state.magnetometria_path)
    
    if mag_path.exists():
        # Leer GeoJSON
        with open(mag_path, 'r') as f:
            geojson_data = json.load(f)
        
        n_features = len(geojson_data.get('features', []))
        
        col_res1, col_res2, col_res3 = st.columns(3)
        
        with col_res1:
            st.metric("Polígonos", f"{n_features:,}")
        
        with col_res2:
            file_size = mag_path.stat().st_size / 1024  # KB
            st.metric("Tamaño", f"{file_size:.1f} KB")
        
        with col_res3:
            st.metric("Estado", estado)
        
        # Mostrar en mapa
        st.markdown("### 🗺️ Visualización")
        
        m_result = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=9,
            tiles='OpenStreetMap'
        )
        
        # Agregar capa de magnetometría
        folium.GeoJson(
            geojson_data,
            name='Magnetometría',
            style_function=lambda x: {
                'fillColor': 'blue',
                'color': 'blue',
                'weight': 1,
                'fillOpacity': 0.3
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['RANGO_CODE'] if 'RANGO_CODE' in geojson_data['features'][0].get('properties', {}) else [],
                aliases=['Código:']
            )
        ).add_to(m_result)
        
        # Agregar área de interés
        folium.Rectangle(
            bounds=[[bbox[1], bbox[0]], [bbox[3], bbox[2]]],
            color='red',
            fill=False,
            weight=2,
            popup="Área solicitada"
        ).add_to(m_result)
        
        folium.LayerControl().add_to(m_result)
        
        st_folium(m_result, width=900, height=500)
        
        # Botón de descarga del archivo
        with open(mag_path, 'r') as f:
            st.download_button(
                label="💾 Descargar GeoJSON",
                data=f.read(),
                file_name=mag_path.name,
                mime='application/json',
                use_container_width=True
            )
        
        # Información adicional
        with st.expander("📋 Ver propiedades de los datos"):
            if n_features > 0:
                first_feature = geojson_data['features'][0]
                st.json(first_feature['properties'])
    else:
        st.error("⚠️ Archivo no encontrado")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
<small>Datos proporcionados por el Servicio Geológico Mexicano (SGM)<br>
https://www.sgm.gob.mx/</small>
</div>
""", unsafe_allow_html=True)
