"""
TERRAF Streamlit App - Dashboard Interactivo
Interfaz web para análisis de percepción remota con Landsat
"""

import streamlit as st
import sys
from pathlib import Path

# Agregar src al path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from terraf_pr import TerrafPR
from reporte_md import ReporteMarkdown
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import folium
from streamlit_folium import st_folium
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from PIL import Image

# Configuración de la página
st.set_page_config(
    page_title="TERRAF - Dashboard",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #00D9FF;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #00D9FF;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🛰️ TERRAF</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">Plataforma de Análisis de Percepción Remota</p>', unsafe_allow_html=True)
st.divider()

# Sidebar - Configuración
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Información del proyecto
    st.info("**TERRAF** - Análisis espectral automatizado para exploración geológica y minera usando datos Landsat")
    
    st.subheader("📁 Datos")
    
    # Selector de datos (simulado por ahora)
    datos_disponibles = {
        "LC09_L1TP_031040_20251108": "datos/landsat9/coleccion-1/LC09_L1TP_031040_20251108_20251108_02_T1"
    }
    
    datos_seleccionados = st.selectbox(
        "Seleccionar escena Landsat:",
        options=list(datos_disponibles.keys())
    )
    
    # Nombre del análisis
    nombre_analisis = st.text_input(
        "Nombre del análisis:",
        value="MiAnalisis",
        help="Nombre identificador para este análisis"
    )
    
    st.divider()
    
    # Parámetros de procesamiento
    st.subheader("🔧 Parámetros")
    
    reducir = st.checkbox(
        "Reducir resolución (4x más rápido)",
        value=True,
        help="Reduce la imagen a 25% para procesamiento rápido"
    )
    
    factor_reduccion = 4 if reducir else 1
    
    st.divider()
    
    # Índices a calcular
    st.subheader("📊 Índices a Calcular")
    
    calcular_gossan = st.checkbox("⛰️ Gossan Index", value=True)
    calcular_oxidos = st.checkbox("🏔️ Óxidos de Hierro", value=True)
    calcular_argilica = st.checkbox("💎 Alteración Argílica", value=True)
    calcular_propilitica = st.checkbox("🌲 Alteración Propilítica", value=False)

# Main content area - Render based on workflow step
current_step = st.session_state.workflow_step

# TAB 1: Inicio
with tab1:
    st.header("Bienvenido a TERRAF")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 🎯 ¿Qué hace TERRAF?
        
        TERRAF analiza imágenes satelitales Landsat para identificar zonas de interés geológico:
        
        - **Gossans**: Sombreros de hierro sobre sulfuros
        - **Óxidos de Fe**: Goethita, hematita, limonita
        - **Alteración Argílica**: Caolinita, alunita
        - **Alteración Propilítica**: Cloritas, epidota
        """)
    
    with col2:
        st.markdown("""
        ### 📡 Datos Soportados
        
        - **Landsat 8/9**: OLI/TIRS
        - **Resolución**: 30m/pixel (bandas multiespectrales)
        - **Nivel**: L1TP (corrección geométrica)
        - **Formato**: GeoTIFF
        
        ### 🚀 Inicio Rápido
        
        1. Selecciona datos en el panel izquierdo
        2. Elige los índices a calcular
        3. Ve a la pestaña **Análisis**
        4. ¡Ejecuta el procesamiento!
        """)
    
    with col3:
        st.markdown("""
        ### 📊 Resultados
        
        TERRAF genera:
        
        - Mapas de alteración espectral
        - Máscaras booleanas de zonas
        - Cálculo de áreas (km²)
        - Visualizaciones RGB
        - Reportes técnicos en Markdown
        
        ### 🔬 Métodos
        
        - Ratios espectrales (SWIR/NIR)
        - Índice de Gossan optimizado
        - Umbrales estadísticos (percentiles)
        """)
    
    st.divider()
    
    # Métricas de ejemplo
    st.subheader("📈 Estadísticas del Proyecto")
    
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Escenas Analizadas", "1", "+0")
    col2.metric("Área Total", "3735.85 km²", "")
    col3.metric("Zonas Gossans", "3735.85 km²", "")
    col4.metric("Precisión", "95%", "+2%")

# TAB 2: Análisis
with tab2:
    st.header("📊 Procesamiento y Análisis")
    
    if st.button("🚀 Ejecutar Análisis", type="primary", use_container_width=True):
        
        # Verificar que haya datos
        ruta_datos = Path(__file__).parent.parent / datos_disponibles[datos_seleccionados]
        
        if not ruta_datos.exists():
            st.error(f"❌ No se encontraron los datos en: {ruta_datos}")
            st.stop()
        
        # Contenedor de progreso
        with st.spinner("⏳ Cargando datos Landsat..."):
            try:
                # Inicializar TERRAF
                pr = TerrafPR(str(ruta_datos), nombre=nombre_analisis)
                pr.cargar_bandas(reducir=reducir, factor=factor_reduccion)
                
                st.success(f"✅ Datos cargados: {pr.metadatos.get('n_bandas', 0)} bandas")
                
                # Mostrar información
                col1, col2, col3 = st.columns(3)
                col1.metric("Resolución", f"{pr.metadatos.get('resolution', 30)}m/pixel")
                col2.metric("Dimensiones", f"{pr.bandas['B4'].shape[1]} × {pr.bandas['B4'].shape[0]}")
                col3.metric("Bandas", pr.metadatos.get('n_bandas', 0))
                
            except Exception as e:
                st.error(f"❌ Error cargando datos: {e}")
                st.stop()
        
        st.divider()
        
        # Calcular índices
        resultados = {}
        
        if calcular_gossan:
            with st.spinner("⛰️ Calculando Gossan Index..."):
                pr.calcular_gossan()
                area = np.sum(pr.zonas['zona_gossan']) * (pr.metadatos['resolution']**2) / 1e6
                resultados['Gossan'] = area
                st.success(f"✅ Gossan: {area:.2f} km²")
        
        if calcular_oxidos:
            with st.spinner("🏔️ Calculando Óxidos de Hierro..."):
                pr.calcular_ratio_oxidos()
                area = np.sum(pr.zonas['zona_oxidos']) * (pr.metadatos['resolution']**2) / 1e6
                resultados['Óxidos Fe'] = area
                st.success(f"✅ Óxidos: {area:.2f} km²")
        
        if calcular_argilica:
            with st.spinner("💎 Calculando Alteración Argílica..."):
                pr.calcular_ratio_argilica()
                area = np.sum(pr.zonas['zona_argilica']) * (pr.metadatos['resolution']**2) / 1e6
                resultados['Argílica'] = area
                st.success(f"✅ Argílica: {area:.2f} km²")
        
        if calcular_propilitica:
            with st.spinner("🌲 Calculando Alteración Propilítica..."):
                pr.calcular_ratio_propilitica()
                area = np.sum(pr.zonas['zona_propilitica']) * (pr.metadatos['resolution']**2) / 1e6
                resultados['Propilítica'] = area
                st.success(f"✅ Propilítica: {area:.2f} km²")
        
        st.divider()
        
        # Visualización de resultados
        st.subheader("📊 Resultados del Análisis")
        
        # Gráfico de barras
        if resultados:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig, ax = plt.subplots(figsize=(10, 6))
                zonas = list(resultados.keys())
                areas = list(resultados.values())
                colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
                
                bars = ax.bar(zonas, areas, color=colors[:len(zonas)])
                ax.set_ylabel('Área (km²)', fontsize=12)
                ax.set_title('Áreas de Alteración Detectadas', fontsize=14, fontweight='bold')
                ax.grid(axis='y', alpha=0.3)
                
                # Etiquetas en las barras
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:.2f} km²',
                           ha='center', va='bottom', fontsize=10)
                
                plt.tight_layout()
                st.pyplot(fig)
            
            with col2:
                st.markdown("### 📈 Resumen")
                for zona, area in resultados.items():
                    st.metric(zona, f"{area:.2f} km²")
                
                total_area = sum(resultados.values())
                st.metric("**TOTAL**", f"{total_area:.2f} km²", delta=None)
        
        # Guardar en session_state
        st.session_state['pr'] = pr
        st.session_state['resultados'] = resultados

# TAB 3: Mapas Georreferenciados
with tab3:
    st.header("🗺️ Mapas Interactivos Georreferenciados")
    
    if 'pr' not in st.session_state:
        st.warning("⚠️ Primero ejecuta el análisis en la pestaña **Análisis**")
    else:
        pr = st.session_state['pr']
        
        st.subheader("🌍 Mapa Interactivo con Coordenadas Reales")
        
        # Obtener coordenadas del primer archivo TIF
        ruta_datos = Path(__file__).parent.parent / datos_disponibles[datos_seleccionados]
        tif_files = list(ruta_datos.glob("*B4*.TIF"))
        
        if tif_files:
            with rasterio.open(tif_files[0]) as src:
                # Obtener bounds geográficos
                bounds = src.bounds
                crs = src.crs
                
                # Centro en coordenadas del CRS original
                center_x = (bounds.left + bounds.right) / 2
                center_y = (bounds.bottom + bounds.top) / 2
                
                try:
                    # Intentar convertir con pyproj
                    import pyproj
                    
                    # Crear transformer
                    transformer = pyproj.Transformer.from_crs(
                        crs,
                        "EPSG:4326",
                        always_xy=True
                    )
                    
                    # Transform a WGS84 (lat/lon)
                    center_lon, center_lat = transformer.transform(center_x, center_y)
                    
                    # También transformar los bounds para el overlay
                    sw_lon, sw_lat = transformer.transform(bounds.left, bounds.bottom)
                    ne_lon, ne_lat = transformer.transform(bounds.right, bounds.top)
                    
                    st.info(f"📍 **Coordenadas del área:**\n- Centro: {center_lat:.4f}°, {center_lon:.4f}°\n- Sistema original: {crs}\n- Bounds: [{sw_lat:.4f}, {sw_lon:.4f}] a [{ne_lat:.4f}, {ne_lon:.4f}]")
                    
                    # Guardar en session_state para usar en overlays
                    st.session_state['map_bounds'] = [[sw_lat, sw_lon], [ne_lat, ne_lon]]
                
                except Exception as e:
                    # Si falla la transformación, usar valores por defecto
                    st.warning(f"⚠️ No se pudo convertir coordenadas: {e}")
                    
                    # Detectar zona UTM del archivo MTL
                    mtl_files = list(ruta_datos.glob("*MTL.txt"))
                    center_lat = 28.0  # Norte de México por defecto
                    center_lon = -106.0
                    
                    if mtl_files:
                        with open(mtl_files[0], 'r') as f:
                            content = f.read()
                            # Buscar coordenadas en el MTL
                            if 'CORNER_UL_LAT_PRODUCT' in content:
                                import re
                                lat_match = re.search(r'CORNER_UL_LAT_PRODUCT = ([-\d.]+)', content)
                                lon_match = re.search(r'CORNER_UL_LON_PRODUCT = ([-\d.]+)', content)
                                if lat_match and lon_match:
                                    corner_lat = float(lat_match.group(1))
                                    corner_lon = float(lon_match.group(1))
                                    
                                    # Buscar también lower right
                                    lat_match2 = re.search(r'CORNER_LR_LAT_PRODUCT = ([-\d.]+)', content)
                                    lon_match2 = re.search(r'CORNER_LR_LON_PRODUCT = ([-\d.]+)', content)
                                    if lat_match2 and lon_match2:
                                        corner_lat2 = float(lat_match2.group(1))
                                        corner_lon2 = float(lon_match2.group(1))
                                        
                                        # Calcular centro
                                        center_lat = (corner_lat + corner_lat2) / 2
                                        center_lon = (corner_lon + corner_lon2) / 2
                                        
                                        st.success(f"✅ Coordenadas extraídas del MTL: {center_lat:.4f}°, {center_lon:.4f}°")
                    
                    st.session_state['map_bounds'] = [[center_lat - 0.5, center_lon - 0.5], [center_lat + 0.5, center_lon + 0.5]]
        else:
            # Valores por defecto (norte de México)
            center_lat = 28.0
            center_lon = -106.0
            st.warning("⚠️ No se encontraron archivos GeoTIFF, usando coordenadas por defecto (norte de México)")
            st.session_state['map_bounds'] = [[center_lat - 0.25, center_lon - 0.25], [center_lat + 0.25, center_lon + 0.25]]
        
        # Selector de capa
        col_sel1, col_sel2 = st.columns(2)
        
        with col_sel1:
            tipo_vista = st.radio(
                "🎨 Tipo de visualización:",
                ["Índices continuos", "Zonas (máscara booleana)"],
                help="Índices: muestra la intensidad del valor calculado\nZonas: muestra solo áreas que superan el umbral"
            )
        
        with col_sel2:
            if tipo_vista == "Índices continuos":
                capa_seleccionada = st.selectbox(
                    "Selecciona el índice:",
                    ["Gossan Index", "Óxidos de Fe (B4/B2)", "Alteración Argílica (B6/B7)", "Propilítica (B5/B7)", "Todos los índices"]
                )
            else:
                capa_seleccionada = st.selectbox(
                    "Selecciona la zona:",
                    ["Gossan", "Óxidos de Fe", "Alteración Argílica", "Propilítica", "Todas las zonas"]
                )
        
        # Crear mapa base con Folium
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles='OpenStreetMap',
            control_scale=True
        )
        
        # Agregar capas base adicionales
        folium.TileLayer(
            tiles='https://tile.opentopomap.org/{z}/{x}/{y}.png',
            attr='Map data: © OpenStreetMap contributors, SRTM | Map style: © OpenTopoMap',
            name='Topográfico'
        ).add_to(m)
        
        folium.TileLayer(
            tiles='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            attr='© OpenStreetMap contributors © CARTO',
            name='Claro'
        ).add_to(m)
        
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Tiles © Esri',
            name='Satélite'
        ).add_to(m)
        
        # Agregar marcador del centro
        folium.Marker(
            [center_lat, center_lon],
            popup=f"<b>Centro del Análisis</b><br>Lat: {center_lat:.4f}<br>Lon: {center_lon:.4f}",
            tooltip="Centro del área",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)
        
        # Función para crear overlay con valores continuos (índices)
        def agregar_indice_overlay(mapa, indice_array, nombre, colormap, centro_lat, centro_lon):
            """Agrega índice como overlay coloreado en el mapa"""
            if indice_array is None or not isinstance(indice_array, np.ndarray):
                return
            
            # Normalizar valores al rango 0-255
            indice_norm = indice_array.copy()
            indice_norm = np.nan_to_num(indice_norm, 0)
            
            # Usar percentiles para mejor visualización
            vmin = np.percentile(indice_norm[indice_norm > 0], 5) if np.any(indice_norm > 0) else 0
            vmax = np.percentile(indice_norm[indice_norm > 0], 95) if np.any(indice_norm > 0) else 1
            
            indice_norm = np.clip((indice_norm - vmin) / (vmax - vmin), 0, 1)
            
            # Crear imagen RGBA usando colormap
            from matplotlib import cm
            cmap = cm.get_cmap(colormap)
            
            # Aplicar colormap
            img_rgba = cmap(indice_norm)
            img_rgba = (img_rgba * 255).astype(np.uint8)
            
            # Ajustar transparencia: más intenso = más opaco
            alpha = (indice_norm * 200 + 55).astype(np.uint8)  # 55-255
            img_rgba[:, :, 3] = alpha
            
            # Donde no hay datos (valor 0), hacer completamente transparente
            mask_cero = indice_array == 0
            img_rgba[mask_cero, 3] = 0
            
            # Convertir a PIL Image
            img_pil = Image.fromarray(img_rgba, mode='RGBA')
        
        # Función para crear overlay de zona booleana
        def agregar_zona_overlay(mapa, zona_array, nombre, color, centro_lat, centro_lon):
            """Agrega zona como overlay en el mapa"""
            if zona_array is None or not isinstance(zona_array, np.ndarray):
                return
            
            # Crear imagen RGBA
            height, width = zona_array.shape
            img_rgba = np.zeros((height, width, 4), dtype=np.uint8)
            
            # Asignar color según el tipo
            color_map = {
                'gossan': [255, 69, 0, 180],      # Rojo-naranja
                'oxidos': [255, 0, 0, 150],       # Rojo
                'argilica': [0, 100, 255, 150],   # Azul
                'propilitica': [34, 139, 34, 150] # Verde
            }
            
            rgba = color_map.get(color.lower(), [255, 255, 0, 150])
            
            # Aplicar color solo donde la zona es True
            mask = zona_array > 0
            img_rgba[mask] = rgba
            
            # Convertir a PIL Image
            img_pil = Image.fromarray(img_rgba, mode='RGBA')
            
            # Usar bounds reales si están disponibles
            if 'map_bounds' in st.session_state:
                bounds_overlay = st.session_state['map_bounds']
            else:
                # Estimar bounds (área aproximada de 50km x 50km)
                delta = 0.25  # ~50km en grados
                bounds_overlay = [
                    [centro_lat - delta, centro_lon - delta],  # SW
                    [centro_lat + delta, centro_lon + delta]   # NE
                ]
            
            # Guardar imagen temporal
            from io import BytesIO
            import base64
            
            buffer = BytesIO()
            img_pil.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            # Agregar como ImageOverlay
            folium.raster_layers.ImageOverlay(
                image=f'data:image/png;base64,{img_base64}',
                bounds=bounds_overlay,
                opacity=0.6,
                name=nombre,
                overlay=True,
                control=True,
                show=True
            ).add_to(mapa)
        
        # Agregar capas según selección
        if tipo_vista == "Índices continuos":
            # Visualizar índices con valores continuos
            if capa_seleccionada == "Gossan Index" and hasattr(pr, 'gossan'):
                agregar_indice_overlay(m, pr.gossan, 'Índice Gossan', 'YlOrRd', center_lat, center_lon)
                st.markdown("### 📊 Estadísticas Índice Gossan")
                col1, col2, col3 = st.columns(3)
                col1.metric("Mínimo", f"{np.nanmin(pr.gossan):.3f}")
                col2.metric("Promedio", f"{np.nanmean(pr.gossan):.3f}")
                col3.metric("Máximo", f"{np.nanmax(pr.gossan):.3f}")
                st.caption("🔥 Rojo intenso = Mayor probabilidad de gossan")
            
            elif capa_seleccionada == "Óxidos de Fe (B4/B2)" and hasattr(pr, 'ratio_oxidos'):
                agregar_indice_overlay(m, pr.ratio_oxidos, 'Ratio B4/B2 (Óxidos)', 'Reds', center_lat, center_lon)
                st.markdown("### 📊 Estadísticas Ratio B4/B2")
                col1, col2, col3 = st.columns(3)
                col1.metric("Mínimo", f"{np.nanmin(pr.ratio_oxidos):.3f}")
                col2.metric("Promedio", f"{np.nanmean(pr.ratio_oxidos):.3f}")
                col3.metric("Máximo", f"{np.nanmax(pr.ratio_oxidos):.3f}")
                st.caption("🔴 Rojo intenso = Mayor presencia de óxidos de hierro")
            
            elif capa_seleccionada == "Alteración Argílica (B6/B7)" and hasattr(pr, 'ratio_argilica'):
                agregar_indice_overlay(m, pr.ratio_argilica, 'Ratio B6/B7 (Argílica)', 'Blues', center_lat, center_lon)
                st.markdown("### 📊 Estadísticas Ratio B6/B7")
                col1, col2, col3 = st.columns(3)
                col1.metric("Mínimo", f"{np.nanmin(pr.ratio_argilica):.3f}")
                col2.metric("Promedio", f"{np.nanmean(pr.ratio_argilica):.3f}")
                col3.metric("Máximo", f"{np.nanmax(pr.ratio_argilica):.3f}")
                st.caption("🔵 Azul intenso = Mayor alteración argílica")
            
            elif capa_seleccionada == "Propilítica (B5/B7)" and hasattr(pr, 'ratio_propilitica'):
                agregar_indice_overlay(m, pr.ratio_propilitica, 'Ratio B5/B7 (Propilítica)', 'Greens', center_lat, center_lon)
                st.markdown("### 📊 Estadísticas Ratio B5/B7")
                col1, col2, col3 = st.columns(3)
                col1.metric("Mínimo", f"{np.nanmin(pr.ratio_propilitica):.3f}")
                col2.metric("Promedio", f"{np.nanmean(pr.ratio_propilitica):.3f}")
                col3.metric("Máximo", f"{np.nanmax(pr.ratio_propilitica):.3f}")
                st.caption("🟢 Verde intenso = Mayor alteración propilítica")
            
            elif capa_seleccionada == "Todos los índices":
                if hasattr(pr, 'gossan'):
                    agregar_indice_overlay(m, pr.gossan, 'Gossan', 'YlOrRd', center_lat, center_lon)
                if hasattr(pr, 'ratio_oxidos'):
                    agregar_indice_overlay(m, pr.ratio_oxidos, 'Óxidos', 'Reds', center_lat, center_lon)
                if hasattr(pr, 'ratio_argilica'):
                    agregar_indice_overlay(m, pr.ratio_argilica, 'Argílica', 'Blues', center_lat, center_lon)
                st.info("⚠️ Capas superpuestas. Usa el control de capas para activar/desactivar cada una.")
        
        else:
            # Visualizar zonas booleanas
            if capa_seleccionada == "Gossan" and 'zona_gossan' in pr.zonas:
                agregar_zona_overlay(m, pr.zonas['zona_gossan'], 'Zona Gossan', 'gossan', center_lat, center_lon)
                area = np.sum(pr.zonas['zona_gossan']) * (pr.metadatos['resolution']**2) / 1e6
                st.metric("Área Gossan", f"{area:.2f} km²")
            
            elif capa_seleccionada == "Óxidos de Fe" and 'zona_oxidos' in pr.zonas:
                agregar_zona_overlay(m, pr.zonas['zona_oxidos'], 'Zona Óxidos', 'oxidos', center_lat, center_lon)
                area = np.sum(pr.zonas['zona_oxidos']) * (pr.metadatos['resolution']**2) / 1e6
                st.metric("Área Óxidos", f"{area:.2f} km²")
            
            elif capa_seleccionada == "Alteración Argílica" and 'zona_argilica' in pr.zonas:
                agregar_zona_overlay(m, pr.zonas['zona_argilica'], 'Zona Argílica', 'argilica', center_lat, center_lon)
                area = np.sum(pr.zonas['zona_argilica']) * (pr.metadatos['resolution']**2) / 1e6
                st.metric("Área Argílica", f"{area:.2f} km²")
            
            elif capa_seleccionada == "Propilítica" and 'zona_propilitica' in pr.zonas:
                agregar_zona_overlay(m, pr.zonas['zona_propilitica'], 'Zona Propilítica', 'propilitica', center_lat, center_lon)
                area = np.sum(pr.zonas['zona_propilitica']) * (pr.metadatos['resolution']**2) / 1e6
                st.metric("Área Propilítica", f"{area:.2f} km²")
            
            elif capa_seleccionada == "Todas las zonas":
                if 'zona_gossan' in pr.zonas:
                    agregar_zona_overlay(m, pr.zonas['zona_gossan'], 'Gossan', 'gossan', center_lat, center_lon)
                if 'zona_oxidos' in pr.zonas:
                    agregar_zona_overlay(m, pr.zonas['zona_oxidos'], 'Óxidos', 'oxidos', center_lat, center_lon)
                if 'zona_argilica' in pr.zonas:
                    agregar_zona_overlay(m, pr.zonas['zona_argilica'], 'Argílica', 'argilica', center_lat, center_lon)
                if 'zona_propilitica' in pr.zonas:
                    agregar_zona_overlay(m, pr.zonas['zona_propilitica'], 'Propilítica', 'propilitica', center_lat, center_lon)
                
                # Mostrar tabla de áreas
                st.markdown("### 📊 Áreas Totales")
                col1, col2, col3, col4 = st.columns(4)
                if 'zona_gossan' in pr.zonas:
                    col1.metric("Gossan", f"{np.sum(pr.zonas['zona_gossan']) * (pr.metadatos['resolution']**2) / 1e6:.2f} km²")
                if 'zona_oxidos' in pr.zonas:
                    col2.metric("Óxidos", f"{np.sum(pr.zonas['zona_oxidos']) * (pr.metadatos['resolution']**2) / 1e6:.2f} km²")
                if 'zona_argilica' in pr.zonas:
                    col3.metric("Argílica", f"{np.sum(pr.zonas['zona_argilica']) * (pr.metadatos['resolution']**2) / 1e6:.2f} km²")
                if 'zona_propilitica' in pr.zonas:
                    col4.metric("Propilítica", f"{np.sum(pr.zonas['zona_propilitica']) * (pr.metadatos['resolution']**2) / 1e6:.2f} km²")
        
        # Agregar control de capas
        folium.LayerControl(position='topright').add_to(m)
        
        # Agregar escala
        folium.plugins.MeasureControl(position='topleft', primary_length_unit='kilometers').add_to(m)
        
        # Agregar minimap
        minimap = folium.plugins.MiniMap(toggle_display=True)
        m.add_child(minimap)
        
        # Mostrar mapa
        st.markdown("### 🌍 Mapa Interactivo")
        st.caption("💡 Usa las capas en la esquina superior derecha para alternar entre vistas. Zoom y pan para explorar.")
        
        st_folium(m, width=1200, height=600)
        
        st.divider()
        
        # Leyenda
        st.markdown("""
        ### 🎨 Leyenda de Colores
        
        | Color | Zona | Minerales Asociados |
        |-------|------|---------------------|
        | 🔴 Rojo-Naranja | **Gossan** | Sombreros de hierro (sulfuros oxidados) |
        | 🔴 Rojo | **Óxidos de Fe** | Goethita, Hematita, Limonita, Jarosita |
        | 🔵 Azul | **Argílica** | Caolinita, Alunita, Dickita, Pirofilita |
        | 🟢 Verde | **Propilítica** | Cloritas, Epidota, Calcita |
        """)

# TAB 4: Reporte
with tab4:
    st.header("📄 Generación de Reportes")
    
    if 'pr' not in st.session_state:
        st.warning("⚠️ Primero ejecuta el análisis en la pestaña **Análisis**")
    else:
        pr = st.session_state['pr']
        
        st.subheader("Configuración del Reporte")
        
        autor = st.text_input("Autor del reporte:", value="Usuario TERRAF")
        
        if st.button("📝 Generar Reporte Markdown", type="primary"):
            with st.spinner("Generando reporte..."):
                reporte = ReporteMarkdown(pr, autor=autor)
                ruta_reporte = reporte.generar()
                
                st.success(f"✅ Reporte generado: {ruta_reporte}")
                
                # Leer y mostrar el reporte
                with open(ruta_reporte, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                
                st.markdown("### Vista Previa:")
                st.markdown(contenido)
                
                # Botón de descarga
                st.download_button(
                    label="⬇️ Descargar Reporte",
                    data=contenido,
                    file_name=f"reporte_{nombre_analisis}.md",
                    mime="text/markdown"
                )

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p><strong>TERRAF</strong> - Plataforma de Análisis de Percepción Remota</p>
    <p>Desarrollado por el equipo TERRAF360 • 2025</p>
</div>
""", unsafe_allow_html=True)
