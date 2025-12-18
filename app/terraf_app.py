"""
TERRAF - Vista tipo Earth Engine con Mapa Central
==================================================
Interfaz centrada en visualización geoespacial con mapa permanente
Version: 2.0.1
"""

import streamlit as st

# ============================================================================
# PAGE CONFIG - DEBE SER LO PRIMERO
# ============================================================================
st.set_page_config(
    page_title="TERRAF Map View",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Imports básicos necesarios para todo
import os
import sys
from pathlib import Path

# Agregar directorio src al path
src_path = Path(__file__).parent.parent / 'src'
if src_path.exists():
    sys.path.insert(0, str(src_path))

# Intentar importar módulos de TERRAF
MODULES_LOADED = False
TerrafPR = None
TerrafMag = None
TerrafDownload = None

try:
    from terraf_pr import TerrafPR
    from terraf_mag import TerrafMag
    from terraf_download import TerrafDownload
    MODULES_LOADED = True
except ImportError:
    pass
except Exception:
    pass

# ============================================================================
# CHECK TEMPRANO PARA CLOUD - DETENER SI NO HAY MÓDULOS
# ============================================================================
if not MODULES_LOADED:
    st.error("⚠️ TERRAF Core Modules Not Available")
    st.info("This application requires local installation of TERRAF modules.")
    
    st.markdown("""
    ### 🚀 How to Run TERRAF Locally:
    
    1. **Clone the repository:**
    ```bash
    git clone https://github.com/terraf360/terraf.git
    cd terraf
    ```
    
    2. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    
    3. **Run the app:**
    ```bash
    streamlit run app/terraf_app.py
    ```
    
    ### 📌 Why Local Only?
    
    TERRAF requires custom modules (`TerrafPR`, `TerrafMag`, `TerrafDownload`) from the `src/` directory that are not accessible in Streamlit Cloud's environment.
    
    **Repository:** [github.com/terraf360/terraf](https://github.com/terraf360/terraf)
    """)
    
    st.stop()

# ============================================================================
# IMPORTS COMPLETOS (solo después de verificar módulos)
# ============================================================================

import folium
from streamlit_folium import st_folium
import numpy as np
import warnings

# Silenciar warnings molestos
warnings.filterwarnings('ignore')

import rasterio
from rasterio.plot import show
from rasterio.transform import from_bounds
from matplotlib import pyplot as plt
from matplotlib import cm
import json
import pandas as pd
import fiona
from PIL import Image
import io
import base64
from io import BytesIO

try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except (ImportError, AttributeError):
    GEOPANDAS_AVAILABLE = False

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def crear_rgb_para_mapa(pr, r_band='B4', g_band='B3', b_band='B2', percentile=2):
    """
    Crea imagen RGB normalizada para overlay en mapa.
    Retorna: imagen_array, bounds, center
    """
    try:
        # Obtener bandas
        r = pr.bandas[r_band]
        g = pr.bandas[g_band]
        b = pr.bandas[b_band]
        
        # Stack
        rgb = np.dstack([r, g, b])
        
        # Crear máscara para datos válidos (eliminar áreas negras/NoData)
        # Máscara donde todas las bandas tienen valores válidos y > 0
        mask = (r > 0) & (g > 0) & (b > 0) & (~np.isnan(r)) & (~np.isnan(g)) & (~np.isnan(b))
        
        # Normalizar con percentiles para mejor contraste
        rgb_norm = np.zeros((*rgb.shape[:2], 4), dtype=np.uint8)  # RGBA
        for i in range(3):
            band = rgb[:, :, i]
            valid = band[mask]
            if len(valid) > 0:
                p_low = np.percentile(valid, percentile)
                p_high = np.percentile(valid, 100 - percentile)
                band_norm = np.clip((band - p_low) / (p_high - p_low) * 255, 0, 255)
                rgb_norm[:, :, i] = band_norm.astype(np.uint8)
        
        # Canal alpha: transparente donde no hay datos
        rgb_norm[:, :, 3] = (mask * 255).astype(np.uint8)
        
        # Obtener bounds geográficos desde metadatos
        transform = pr.metadatos['transform']
        height = pr.metadatos['height']
        width = pr.metadatos['width']
        crs = pr.metadatos['crs']
        
        # DEBUG: Verificar dimensiones
        print(f"🗺️  Metadatos: width={width}, height={height}")
        print(f"🗺️  Transform pixel size: a={transform.a}, e={transform.e}")
        print(f"🗺️  Array shapes: R={r.shape}, G={g.shape}, B={b.shape}")
        
        # Calcular bounds en coordenadas proyectadas
        minx = transform.c
        maxy = transform.f
        maxx = minx + (width * transform.a)
        miny = maxy + (height * transform.e)
        
        # DEBUG: Imprimir bounds originales
        print(f"🗺️  Bounds UTM: X=[{minx}, {maxx}], Y=[{miny}, {maxy}]")
        print(f"🗺️  CRS: {crs}")
        
        # Convertir a lat/lon si es necesario
        crs_string = str(crs)
        if 'EPSG:4326' not in crs_string and '4326' not in crs_string:
            try:
                # Intentar con pyproj
                from pyproj import Transformer
                
                # Detectar EPSG del CRS
                if 'UTM' in crs_string or '32613' in crs_string:
                    # UTM Zone 13N (común en norte de México)
                    transformer = Transformer.from_crs("EPSG:32613", "EPSG:4326", always_xy=True)
                elif '32612' in crs_string:
                    transformer = Transformer.from_crs("EPSG:32612", "EPSG:4326", always_xy=True)
                elif '32614' in crs_string:
                    transformer = Transformer.from_crs("EPSG:32614", "EPSG:4326", always_xy=True)
                else:
                    # Asumir WGS84 si no se puede determinar
                    st.warning(f"CRS desconocido: {crs_string}, asumiendo coordenadas geográficas")
                    transformer = None
                
                if transformer:
                    # Transformar las 4 esquinas correctamente
                    # minx, miny = esquina inferior izquierda (suroeste)
                    # maxx, maxy = esquina superior derecha (noreste)
                    lon_sw, lat_sw = transformer.transform(minx, miny)  # Southwest
                    lon_ne, lat_ne = transformer.transform(maxx, maxy)  # Northeast
                    
                    print(f"🗺️  Esquina SW: Lat={lat_sw:.4f}, Lon={lon_sw:.4f}")
                    print(f"🗺️  Esquina NE: Lat={lat_ne:.4f}, Lon={lon_ne:.4f}")
                    
                    # Para Folium ImageOverlay: [[south, west], [north, east]]
                    bounds_list = [[lat_sw, lon_sw], [lat_ne, lon_ne]]
                    center = [(lat_sw + lat_ne) / 2, (lon_sw + lon_ne) / 2]
                else:
                    # Ya está en coordenadas geográficas
                    bounds_list = [[miny, minx], [maxy, maxx]]
                    center = [(miny + maxy) / 2, (minx + maxx) / 2]
            except Exception as e:
                st.warning(f"No se pudo transformar CRS: {e}. Asumiendo coordenadas ya están en grados.")
                bounds_list = [[miny, minx], [maxy, maxx]]
                center = [(miny + maxy) / 2, (minx + maxx) / 2]
        else:
            # Ya está en WGS84
            bounds_list = [[miny, minx], [maxy, maxx]]
            center = [(miny + maxy) / 2, (minx + maxx) / 2]
        
        return rgb_norm, bounds_list, center
    except Exception as e:
        st.error(f"Error creating RGB: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None, None, None

def array_to_png_base64(array):
    """
    Convierte array numpy a PNG en base64 para folium ImageOverlay
    
    IMPORTANTE: Folium espera que la imagen tenga el origen en la esquina
    superior izquierda correspondiendo al norte-oeste geográfico.
    Los arrays de rasterio ya vienen así (fila 0 = norte), así que NO voltear.
    """
    # DEBUG: Imprimir dimensiones
    print(f"🖼️  Array shape para PNG: {array.shape}")
    
    # Detectar si es RGB o RGBA
    if array.shape[2] == 4:
        img = Image.fromarray(array, mode='RGBA')
    else:
        img = Image.fromarray(array, mode='RGB')
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode()
    return f"data:image/png;base64,{img_base64}"

def crear_index_para_mapa(index_data, bounds, cmap='RdYlGn'):
    """
    Crea visualización de índice con colormap para el mapa
    Retorna: imagen_array en base64
    """
    try:
        # Normalizar datos
        valid = index_data[~np.isnan(index_data)]
        if len(valid) == 0:
            return None
        
        vmin, vmax = np.percentile(valid, [2, 98])
        norm_data = np.clip((index_data - vmin) / (vmax - vmin), 0, 1)
        
        # Aplicar colormap
        from matplotlib import cm
        colormap = cm.get_cmap(cmap)
        rgba = colormap(norm_data)
        
        # Convertir a RGB uint8
        rgb = (rgba[:, :, :3] * 255).astype(np.uint8)
        
        # Aplicar transparencia a NaN
        alpha = (~np.isnan(index_data)).astype(np.uint8) * 255
        rgba_final = np.dstack([rgb, alpha])
        
        # Convertir a imagen
        img = Image.fromarray(rgba_final, mode='RGBA')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        st.error(f"Error creating index visualization: {e}")
        return None
# ============================================================================
# SESSION STATE - PERSISTENTE
# ============================================================================
if 'map_center' not in st.session_state:
    st.session_state.map_center = [28.5, -105.5]  # Norte de México
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 7
if 'active_layers' not in st.session_state:
    st.session_state.active_layers = {}
if 'landsat_data' not in st.session_state:
    st.session_state.landsat_data = None
if 'mag_data' not in st.session_state:
    st.session_state.mag_data = None
if 'indices' not in st.session_state:
    st.session_state.indices = {}
if 'prevent_rerun' not in st.session_state:
    st.session_state.prevent_rerun = False
if 'map_rendered' not in st.session_state:
    st.session_state.map_rendered = False
if 'downloader' not in st.session_state:
    if MODULES_LOADED:
        st.session_state.downloader = TerrafDownload()
    else:
        st.session_state.downloader = None
if 'search_results' not in st.session_state:
    st.session_state.search_results = None

# ============================================================================
# SIDEBAR - CONTROLES
# ============================================================================
with st.sidebar:
    st.markdown("# 🎛️ TERRAF Controls")
    
    st.markdown("---")
    
    # ========================================================================
    # SECCIÓN 1: LAYER MANAGER (ARRIBA DEL TODO)
    # ========================================================================
    st.markdown("### 🗂️ Layer Manager")
    
    # Basemap selector
    basemap = st.selectbox(
        "Base Map",
        ["OpenStreetMap", "Satellite", "Topographic"],
        index=1
    )
    
    # Active layers
    if st.session_state.landsat_data:
        st.markdown("**🛰️ Satellite Imagery:**")
        st.session_state.active_layers['rgb_natural'] = st.checkbox(
            "RGB Natural Color",
            value=st.session_state.active_layers.get('rgb_natural', True),
            key="layer_rgb_nat"
        )
        st.session_state.active_layers['rgb_false_color'] = st.checkbox(
            "False Color (NIR-R-G)",
            value=st.session_state.active_layers.get('rgb_false_color', False),
            key="layer_rgb_fc"
        )
        st.session_state.active_layers['rgb_swir'] = st.checkbox(
            "SWIR Composite (7-5-3)",
            value=st.session_state.active_layers.get('rgb_swir', False),
            key="layer_rgb_swir"
        )
    
    if st.session_state.indices:
        st.markdown("**🔥 Mineral Indices:**")
        display_names = {
            'gossan': '🔥 Gossan',
            'oxidos': '🟠 Iron Oxides',
            'argilica': '🟡 Argillic Alteration',
            'propilitica': '🟢 Propylitic',
            'carbonatos': '⚪ Carbonates',
            'clay': '🟤 Clay',
            'ndvi': '🌱 NDVI'
        }
        for idx_name in sorted(st.session_state.indices.keys()):
            display = display_names.get(idx_name, idx_name.title())
            st.session_state.active_layers[f'idx_{idx_name}'] = st.checkbox(
                display,
                value=st.session_state.active_layers.get(f'idx_{idx_name}', False),
                key=f"layer_idx_{idx_name}"
            )
    
    if st.session_state.mag_data:
        st.markdown("**🧲 Geophysical:**")
        st.session_state.active_layers['magnetometry'] = st.checkbox(
            "Magnetometry",
            value=st.session_state.active_layers.get('magnetometry', False),
            key="layer_mag"
        )
    
    # Opacity control
    layer_opacity = st.slider("Layer Opacity", 0.0, 1.0, 0.7, 0.1)
    
    st.markdown("---")
    
    # ========================================================================
    # SECCIÓN 2: DATOS LANDSAT
    # ========================================================================
    with st.expander("🛰️ LANDSAT DATA", expanded=False):
        if not MODULES_LOADED:
            st.warning("⚠️ Data loading features are not available in cloud mode")
            st.info("TERRAF modules (TerrafPR, TerrafMag) require local installation")
        else:
            st.markdown("### Load Landsat Scene")
            
            # Tabs para elegir fuente de datos
            tab1, tab2 = st.tabs(["📁 Local Files", "☁️ Upload Files"])
    
            with tab1:
                # Buscar escenas en múltiples directorios
                search_dirs = [
                    Path("datos/landsat9"),
                    Path("datos/downloaded")
                ]
            
            all_scenes = []
            scene_paths = {}  # Mapear nombre -> path completo
            
            for base_dir in search_dirs:
                if not base_dir.exists():
                    continue
                
                # Buscar subdirectorios con archivos TIF
                for item in base_dir.rglob("*"):
                    if item.is_dir():
                        tif_files = list(item.glob("*.TIF")) + list(item.glob("*.tif"))
                        # Solo agregar si tiene archivos TIF (evitar carpetas vacías)
                        if tif_files and len(tif_files) > 0:
                            scene_name = item.name
                            # Agregar etiqueta de ubicación
                            if "downloaded" in str(item):
                                display_name = f"📥 {scene_name}"
                            else:
                                display_name = f"📂 {scene_name}"
                            all_scenes.append(display_name)
                            scene_paths[display_name] = item
                
                # Buscar archivos HLS
                hls_files = list(base_dir.glob("*.tif"))
                if hls_files:
                    hls_scenes = set()
                    for f in hls_files:
                        parts = f.stem.split('.')
                        if len(parts) >= 4:
                            scene_id = '.'.join(parts[:4])
                            display_name = f"🌐 {scene_id}"
                            hls_scenes.add(display_name)
                            scene_paths[display_name] = base_dir
                    all_scenes.extend(list(hls_scenes))
            
            if not all_scenes:
                st.info("📂 No local scenes found in datos/landsat9 or datos/downloaded")
            else:
                selected_display = st.selectbox("Select Scene", sorted(all_scenes), key="local_landsat_select")
                selected_scene_path = scene_paths[selected_display]
                # Extraer nombre sin emoji para compatibilidad
                selected_scene = selected_display.split(' ', 1)[1] if ' ' in selected_display else selected_display
                
                if st.button("📂 Load Local Scene", type="primary", key="load_landsat_btn"):
                    with st.spinner("Loading Landsat data..."):
                        try:
                            # Usar el path que ya encontramos
                            scene_path = selected_scene_path
                            
                            # Cargar escena
                            pr = TerrafPR(str(scene_path))
                            pr.cargar_bandas(reducir=True, factor=4)
                            st.session_state.landsat_data = pr
                            st.session_state.landsat_scene_name = selected_scene
                            st.success(f"✅ Loaded {len(pr.bandas)} bands")
                            
                            # Activar capa RGB Natural automáticamente
                            st.session_state.active_layers['rgb_natural'] = True
                            
                            # Limpiar flag de bounds para recentrar
                            if 'landsat_bounds_calculated' in st.session_state:
                                del st.session_state['landsat_bounds_calculated']
                            
                            st.rerun()
                            
                        except ValueError as e:
                            st.error(f"❌ Format Error: {str(e)[:200]}")
                            st.info("💡 Supported formats:\n- Landsat Level-1: *_B*.TIF\n- Landsat Level-2: *_SR_B*.TIF\n- HLS: HLS.L30.*.B*.tif")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)[:200]}")
                            import traceback
                            st.code(traceback.format_exc()[:500])
        
            with tab2:
                st.info("☁️ Upload Landsat band files (.TIF) from your computer")
                uploaded_files = st.file_uploader(
                "Select Landsat band files",
                type=["tif", "TIF"],
                accept_multiple_files=True,
                key="landsat_uploader"
            )
            
            if uploaded_files:
                st.write(f"📤 {len(uploaded_files)} files selected")
                
                # Mostrar preview de archivos
                with st.expander("View uploaded files", expanded=False):
                    for f in uploaded_files:
                        st.text(f"• {f.name}")
                
                if st.button("☁️ Load Uploaded Scene", type="primary", key="load_uploaded_landsat"):
                    with st.spinner("Processing uploaded files..."):
                        try:
                            # Crear directorio temporal para los archivos
                            import tempfile
                            temp_dir = Path(tempfile.mkdtemp())
                            
                            # Guardar archivos subidos
                            for uploaded_file in uploaded_files:
                                file_path = temp_dir / uploaded_file.name
                                with open(file_path, "wb") as f:
                                    f.write(uploaded_file.getbuffer())
                            
                            # Cargar escena desde directorio temporal
                            pr = TerrafPR(str(temp_dir))
                            pr.cargar_bandas(reducir=True, factor=4)
                            st.session_state.landsat_data = pr
                            st.session_state.landsat_scene_name = "Uploaded Scene"
                            st.success(f"✅ Loaded {len(pr.bandas)} bands from uploaded files")
                            
                            # Activar capa RGB Natural automáticamente
                            st.session_state.active_layers['rgb_natural'] = True
                            
                            # Limpiar flag de bounds para recentrar
                            if 'landsat_bounds_calculated' in st.session_state:
                                del st.session_state['landsat_bounds_calculated']
                            
                            st.rerun()
                            
                        except ValueError as e:
                            st.error(f"❌ Format Error: {str(e)[:200]}")
                            st.info("💡 Supported formats:\n- Landsat Level-1: *_B*.TIF\n- Landsat Level-2: *_SR_B*.TIF\n- HLS: HLS.L30.*.B*.tif")
                            import traceback
                            with st.expander("Ver detalles del error"):
                                st.code(traceback.format_exc())
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)[:200]}")
                            import traceback
                            with st.expander("Ver detalles del error"):
                                st.code(traceback.format_exc())
    # ========================================================================
    # SECCIÓN 3: ÍNDICES ESPECTRALES
    # ========================================================================
    if st.session_state.landsat_data is not None and MODULES_LOADED:
        with st.expander("🔥 SPECTRAL INDICES", expanded=False):
            st.markdown("### Calculate Indices")
            
            pr = st.session_state.landsat_data
            
            indices_options = {
                'Gossan (Kaufmann)': 'gossan',
                'Iron Oxides': 'oxidos',
                'Argillic Alteration': 'argilica',
                'Propylitic': 'propilitica',
                'Carbonates': 'carbonatos',
                'Clay Index': 'clay',
                'NDVI': 'ndvi'
            }
            
            for display_name, key in indices_options.items():
                if st.button(f"Calculate {display_name}", key=f"calc_{key}"):
                    with st.spinner(f"Calculating {display_name}..."):
                        try:
                            if key == 'gossan':
                                pr.calcular_gossan()
                                st.session_state.indices['gossan'] = pr.indices['gossan']
                            elif key == 'oxidos':
                                pr.calcular_ratio_oxidos()
                                st.session_state.indices['oxidos'] = pr.ratios['oxidos']
                            elif key == 'argilica':
                                pr.calcular_ratio_argilica()
                                st.session_state.indices['argilica'] = pr.ratios['argilica']
                            elif key == 'propilitica':
                                pr.calcular_propilitica()
                                st.session_state.indices['propilitica'] = pr.indices['propilitica']
                            elif key == 'carbonatos':
                                pr.calcular_carbonatos()
                                st.session_state.indices['carbonatos'] = pr.indices['carbonatos']
                            elif key == 'clay':
                                pr.calcular_clay_index()
                                st.session_state.indices['clay'] = pr.indices['clay']
                            elif key == 'ndvi':
                                pr.calcular_ndvi()
                                st.session_state.indices['ndvi'] = pr.indices['ndvi']
                            
                            st.success(f"✅ {display_name} calculated")
                            st.session_state.landsat_data = pr
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
    
    # ========================================================================
    # SECCIÓN 4: MAGNETOMETRÍA
    # ========================================================================
    with st.expander("🧲 MAGNETOMETRY", expanded=False):
        if not MODULES_LOADED:
            st.warning("⚠️ Data loading features are not available in cloud mode")
            st.info("TERRAF modules (TerrafPR, TerrafMag) require local installation")
        else:
            st.markdown("### Load Magnetic Data")
            
            # Botón para limpiar datos viejos
            if st.session_state.mag_data is not None:
                if st.button("🗑️ Clear Magnetometry", key="clear_mag"):
                    st.session_state.mag_data = None
                    st.rerun()
            
            # Tabs para elegir fuente de datos
            tab1, tab2 = st.tabs(["📁 Local Files", "☁️ Upload Files"])
        
            with tab1:
                mag_dir = Path("datos/magnetometria")
                if mag_dir.exists():
                    shapefiles = list(mag_dir.rglob("*.shp"))
                    
                    if shapefiles:
                        shp_names = [f.name for f in shapefiles]
                        selected_shp = st.selectbox("Select shapefile", shp_names, key="local_mag_select")
                        
                        if st.button("📂 Load Local Magnetometry", key="load_local_mag"):
                            with st.spinner("Loading magnetic data..."):
                                try:
                                    shp_path = [f for f in shapefiles if f.name == selected_shp][0]
                                    
                                    # Cargar features con fiona (siempre funciona)
                                    features = []
                                    crs_info = None
                                    with fiona.open(str(shp_path), 'r') as src:
                                        crs_info = src.crs
                                        for feature in src:
                                            features.append(feature)
                                    
                                    # Extraer propiedades para DataFrame
                                    records = [f['properties'] for f in features]
                                    df = pd.DataFrame(records)
                                    
                                    # Crear TerrafMag
                                    mag = TerrafMag(dataframe=df)
                                    mag._detectar_columnas()
                                    
                                    # Activar capa de magnetometría automáticamente
                                    st.session_state.active_layers['magnetometry'] = True
                                    
                                    # Extraer coordenadas de geometrías para cache
                                    from shapely.geometry import shape
                                    coords_x = []
                                    coords_y = []
                                    for feature in features:
                                        geom = shape(feature['geometry'])
                                        centroid = geom.centroid
                                        coords_x.append(centroid.x)
                                        coords_y.append(centroid.y)
                                    
                                    # Guardar coordenadas en cache de TerrafMag
                                    mag._coords_cache = (np.array(coords_x), np.array(coords_y))
                                    
                                    # Guardar CRS
                                    mag._crs_info = crs_info
                                    
                                    if mag.campo_total is None:
                                        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                                        mag_col = st.selectbox("Select magnetic column", numeric_cols)
                                        if st.button("Confirm", key="confirm_mag_col"):
                                            mag.campo_total = df[mag_col].values
                                            st.session_state.mag_data = {
                                                'mag': mag,
                                                'features': features,
                                                'df': df,
                                                'crs': crs_info
                                            }
                                            st.success("✅ Magnetometry loaded")
                                    else:
                                        st.session_state.mag_data = {
                                            'mag': mag,
                                            'features': features,
                                            'df': df,
                                            'crs': crs_info
                                        }
                                        st.success(f"✅ {len(features)} features loaded | Campo: {mag.campo_total.min():.1f} - {mag.campo_total.max():.1f} nT")
                                        
                                except Exception as e:
                                    st.error(f"❌ Error: {e}")
                    else:
                        st.warning("📂 No shapefiles in datos/magnetometria/")
                else:
                    st.info("📂 Create folder: datos/magnetometria/")
        
            with tab2:
                st.info("☁️ Upload shapefile components (.shp, .shx, .dbf, .prj) from your computer")
                
                uploaded_shp = st.file_uploader("Select .shp file", type=["shp"], key="mag_shp_uploader")
            uploaded_shx = st.file_uploader("Select .shx file", type=["shx"], key="mag_shx_uploader")
            uploaded_dbf = st.file_uploader("Select .dbf file", type=["dbf"], key="mag_dbf_uploader")
            uploaded_prj = st.file_uploader("Select .prj file (optional)", type=["prj"], key="mag_prj_uploader")
            
            if uploaded_shp and uploaded_shx and uploaded_dbf:
                st.success("✅ All required files uploaded")
                
                if st.button("☁️ Load Uploaded Magnetometry", type="primary", key="load_uploaded_mag"):
                    with st.spinner("Processing uploaded shapefile..."):
                        try:
                            # Crear directorio temporal
                            import tempfile
                            temp_dir = Path(tempfile.mkdtemp())
                            
                            # Guardar archivos con el mismo nombre base
                            base_name = "uploaded_mag"
                            shp_path = temp_dir / f"{base_name}.shp"
                            shx_path = temp_dir / f"{base_name}.shx"
                            dbf_path = temp_dir / f"{base_name}.dbf"
                            
                            with open(shp_path, "wb") as f:
                                f.write(uploaded_shp.getbuffer())
                            with open(shx_path, "wb") as f:
                                f.write(uploaded_shx.getbuffer())
                            with open(dbf_path, "wb") as f:
                                f.write(uploaded_dbf.getbuffer())
                            
                            if uploaded_prj:
                                prj_path = temp_dir / f"{base_name}.prj"
                                with open(prj_path, "wb") as f:
                                    f.write(uploaded_prj.getbuffer())
                            
                            # Cargar features con fiona
                            features = []
                            crs_info = None
                            with fiona.open(str(shp_path), 'r') as src:
                                crs_info = src.crs
                                for feature in src:
                                    features.append(feature)
                            
                            # Extraer propiedades para DataFrame
                            records = [f['properties'] for f in features]
                            df = pd.DataFrame(records)
                            
                            # Crear TerrafMag
                            mag = TerrafMag(dataframe=df)
                            mag._detectar_columnas()
                            
                            # Extraer coordenadas de geometrías para cache
                            from shapely.geometry import shape
                            coords_x = []
                            coords_y = []
                            for feature in features:
                                geom = shape(feature['geometry'])
                                centroid = geom.centroid
                                coords_x.append(centroid.x)
                                coords_y.append(centroid.y)
                            
                            # Guardar coordenadas en cache de TerrafMag
                            mag._coords_cache = (np.array(coords_x), np.array(coords_y))
                            
                            # Guardar CRS
                            mag._crs_info = crs_info
                            
                            if mag.campo_total is None:
                                st.warning("⚠️ Could not auto-detect magnetic field column")
                                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                                mag_col = st.selectbox("Select magnetic column", numeric_cols, key="uploaded_mag_col")
                                if st.button("Confirm Column", key="confirm_uploaded_mag_col"):
                                    mag.campo_total = df[mag_col].values
                                    st.session_state.mag_data = {
                                        'mag': mag,
                                        'features': features,
                                        'df': df,
                                        'crs': crs_info
                                    }
                                    st.success("✅ Uploaded magnetometry loaded")
                                    st.rerun()
                            else:
                                st.session_state.mag_data = {
                                    'mag': mag,
                                    'features': features,
                                    'df': df,
                                    'crs': crs_info
                                }
                                # Activar capa de magnetometría automáticamente
                                st.session_state.active_layers['magnetometry'] = True
                                st.success(f"✅ {len(features)} features loaded from upload | Campo: {mag.campo_total.min():.1f} - {mag.campo_total.max():.1f} nT")
                                st.rerun()
                                
                        except Exception as e:
                            st.error(f"❌ Error loading shapefile: {e}")
                            import traceback
                            st.code(traceback.format_exc()[:500])
            else:
                st.warning("⚠️ Please upload all required files (.shp, .shx, .dbf)")
    
    # Sección de cálculos magnéticos
    if st.session_state.mag_data is not None:
        with st.expander("🧮 MAGNETIC PROCESSING", expanded=False):
            st.markdown("### Calculate Magnetic Derivatives")
            
            mag = st.session_state.mag_data['mag']
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📊 Horizontal Gradient"):
                    with st.spinner("Calculating..."):
                        try:
                            mag.calcular_derivada_horizontal()
                            st.session_state.mag_data['mag'] = mag
                            st.success("✅ THG calculated")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
                
                if st.button("🔺 Tilt Angle"):
                    with st.spinner("Calculating..."):
                        try:
                            mag.calcular_tilt_angle()
                            st.session_state.mag_data['mag'] = mag
                            st.success("✅ Tilt Angle calculated")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
            
            with col2:
                if st.button("📉 Vertical Derivative"):
                    with st.spinner("Calculating..."):
                        try:
                            mag.calcular_derivada_vertical(orden=1)
                            st.session_state.mag_data['mag'] = mag
                            st.success("✅ 1st derivative calculated")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
                
                if st.button("🔬 Analytic Signal"):
                    with st.spinner("Calculating..."):
                        try:
                            mag.calcular_gradiente_analitic_signal()
                            st.session_state.mag_data['mag'] = mag
                            st.success("✅ Analytic Signal calculated")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
            
            # Anomalía residual
            st.markdown("**Residual Anomaly:**")
            metodo = st.selectbox("Method", ["polinomial", "media_movil"], key="mag_residual_method")
            if metodo == "polinomial":
                grado = st.slider("Polynomial degree", 1, 5, 2, key="mag_poly_degree")
                if st.button("🎯 Calculate Residual"):
                    with st.spinner("Calculating..."):
                        try:
                            mag.calcular_anomalia_residual(metodo='polinomial', grado=grado)
                            st.session_state.mag_data['mag'] = mag
                            st.success("✅ Residual anomaly calculated")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
            else:
                if st.button("🎯 Calculate Residual"):
                    with st.spinner("Calculating..."):
                        try:
                            mag.calcular_anomalia_residual(metodo='media_movil')
                            st.session_state.mag_data['mag'] = mag
                            st.success("✅ Residual anomaly calculated")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")

# ============================================================================
# MAIN - MAPA CENTRAL
# ============================================================================

st.markdown("""
<div style='text-align: center; padding: 10px; background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); border-radius: 10px; margin-bottom: 20px;'>
    <h1 style='color: white; margin: 0;'>🗺️ TERRAF Map View</h1>
    <p style='color: #e0e0e0; margin: 5px 0 0 0;'>Interactive Geospatial Visualization Platform</p>
</div>
""", unsafe_allow_html=True)

# Crear columnas: mapa grande | inspector a la derecha
col_map, col_inspector = st.columns([4, 1])

with col_map:
    # ========================================================================
    # MAPA PRINCIPAL - SIEMPRE VISIBLE
    # ========================================================================
    
    # Determinar centro y zoom (actualizar si hay datos Landsat)
    map_center = st.session_state.map_center
    map_zoom = st.session_state.map_zoom
    
    if (st.session_state.landsat_data is not None and 
        'landsat_bounds_calculated' not in st.session_state):
        # Calcular centro una sola vez
        try:
            pr = st.session_state.landsat_data
            _, _, center = crear_rgb_para_mapa(pr, 'B4', 'B3', 'B2')
            if center:
                map_center = center
                map_zoom = 10
                st.session_state.landsat_bounds_calculated = True
        except:
            pass
    
    # Crear mapa base
    m = folium.Map(
        location=map_center,
        zoom_start=map_zoom,
        tiles=None  # No default tile
    )
    
    # Agregar basemap según selección
    if basemap == "OpenStreetMap":
        folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    elif basemap == "Satellite":
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='ESRI World Imagery',
            name='Satellite'
        ).add_to(m)
    elif basemap == "Topographic":
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
            attr='ESRI Topographic',
            name='Topographic'
        ).add_to(m)
    
    # ========================================================================
    # AGREGAR CAPAS ACTIVAS
    # ========================================================================
    
    # ========== LANDSAT RGB COMPOSITES ==========
    if st.session_state.landsat_data is not None:
        pr = st.session_state.landsat_data
        
        # RGB Natural Color
        if st.session_state.active_layers.get('rgb_natural', False):
            try:
                rgb_img, bounds, center = crear_rgb_para_mapa(pr, 'B4', 'B3', 'B2')
                if rgb_img is not None and bounds is not None:
                    img_base64 = array_to_png_base64(rgb_img)
                    folium.raster_layers.ImageOverlay(
                        image=img_base64, bounds=bounds, opacity=layer_opacity,
                        name='RGB Natural', interactive=False, cross_origin=False
                    ).add_to(m)
            except Exception as e:
                st.sidebar.error(f"❌ RGB Natural: {str(e)[:50]}")
        
        # False Color (NIR-R-G)
        if st.session_state.active_layers.get('rgb_false_color', False):
            try:
                rgb_img, bounds, center = crear_rgb_para_mapa(pr, 'B5', 'B4', 'B3')
                if rgb_img is not None and bounds is not None:
                    img_base64 = array_to_png_base64(rgb_img)
                    folium.raster_layers.ImageOverlay(
                        image=img_base64, bounds=bounds, opacity=layer_opacity,
                        name='False Color', interactive=False, cross_origin=False
                    ).add_to(m)
            except Exception as e:
                st.sidebar.error(f"❌ False Color: {str(e)[:50]}")
        
        # SWIR Composite (7-5-3)
        if st.session_state.active_layers.get('rgb_swir', False):
            try:
                rgb_img, bounds, center = crear_rgb_para_mapa(pr, 'B7', 'B5', 'B3')
                if rgb_img is not None and bounds is not None:
                    img_base64 = array_to_png_base64(rgb_img)
                    folium.raster_layers.ImageOverlay(
                        image=img_base64, bounds=bounds, opacity=layer_opacity,
                        name='SWIR Composite', interactive=False, cross_origin=False
                    ).add_to(m)
            except Exception as e:
                st.sidebar.error(f"❌ SWIR: {str(e)[:50]}")
        
        # Bandas individuales en escala de grises
        for band in [b for b in pr.bandas.keys() if b.startswith('B') and len(b) <= 3]:
            if st.session_state.active_layers.get(f'band_{band}', False):
                try:
                    band_data = pr.bandas[band]
                    _, bounds, _ = crear_rgb_para_mapa(pr, 'B4', 'B3', 'B2')
                    
                    # Normalizar banda a 0-255
                    valid = band_data[~np.isnan(band_data)]
                    if len(valid) > 0:
                        vmin, vmax = np.percentile(valid, [2, 98])
                        band_norm = np.clip((band_data - vmin) / (vmax - vmin) * 255, 0, 255).astype(np.uint8)
                        
                        # Escala de grises
                        gray_img = np.dstack([band_norm, band_norm, band_norm])
                        img_base64 = array_to_png_base64(gray_img)
                        
                        folium.raster_layers.ImageOverlay(
                            image=img_base64, bounds=bounds, opacity=layer_opacity,
                            name=f'Band {band}', interactive=False, cross_origin=False
                        ).add_to(m)
                except Exception as e:
                    st.sidebar.error(f"❌ Band {band}: {str(e)[:50]}")
    
    # ========== MINERAL INDICES ==========
    for idx_name in ['gossan', 'oxidos', 'argilica', 'propilitica', 'carbonatos', 'clay', 'ndvi']:
        if (st.session_state.active_layers.get(f'idx_{idx_name}', False) and 
            idx_name in st.session_state.indices):
            
            try:
                pr = st.session_state.landsat_data
                index_data = st.session_state.indices[idx_name]
                
                # Obtener bounds
                _, bounds, center = crear_rgb_para_mapa(pr, 'B4', 'B3', 'B2')
                
                if bounds is not None:
                    # Seleccionar colormap según índice
                    cmaps = {
                        'gossan': 'RdYlBu_r',
                        'oxidos': 'OrRd',
                        'argilica': 'YlOrBr',
                        'propilitica': 'YlGn',
                        'carbonatos': 'Greys',
                        'clay': 'PuRd',
                        'ndvi': 'RdYlGn'
                    }
                    
                    img_base64 = crear_index_para_mapa(index_data, bounds, cmaps.get(idx_name, 'viridis'))
                    
                    if img_base64:
                        folium.raster_layers.ImageOverlay(
                            image=img_base64,
                            bounds=bounds,
                            opacity=layer_opacity,
                            name=idx_name.title(),
                            interactive=False,
                            cross_origin=False
                        ).add_to(m)
            except Exception as e:
                st.sidebar.error(f"❌ {idx_name}: {str(e)[:50]}")
    
    # Magnetometría
    if (st.session_state.active_layers.get('magnetometry', False) and 
        st.session_state.mag_data is not None):
        
        try:
            mag = st.session_state.mag_data['mag']
            features = st.session_state.mag_data['features']
            crs_info = st.session_state.mag_data.get('crs')
            
            # Calcular estadísticas si no existen
            if not mag.estadisticas:
                mag.calcular_estadisticas()
            
            stats = mag.estadisticas
            campo_min = stats['min']
            campo_max = stats['max']
            campo_mean = stats['mean']
            campo_std = stats['std']
            
            # Debug info
            crs_name = str(crs_info) if crs_info else 'No CRS'
            st.sidebar.info(f"🗺️ CRS: {crs_name[:50]}")
            
            # NO transformar coordenadas - dejar que folium lo maneje
            # Folium puede manejar diferentes CRS automáticamente
            coords_transformed = False
            
            # Transformar features manualmente (sin pyproj/shapely problemáticos)
            features_wgs84 = []
            need_transform = False
            utm_zone = None
            
            # Detectar UTM
            crs_code = str(crs_info).upper() if crs_info else ''
            st.sidebar.info(f"📍 Source CRS detected")
            
            # Detectar zona UTM desde string PROJCS o EPSG
            if 'UTM_ZONE_13' in crs_code or 'EPSG:32613' in crs_code:
                need_transform = True
                utm_zone = 13
            elif 'UTM_ZONE_12' in crs_code or 'EPSG:32612' in crs_code:
                need_transform = True
                utm_zone = 12
            elif 'UTM_ZONE_14' in crs_code or 'EPSG:32614' in crs_code:
                need_transform = True
                utm_zone = 14
            elif 'EPSG:4326' in crs_code or 'WGS 84' in crs_code and 'UTM' not in crs_code:
                need_transform = False
            
            # Transformar geometrías manualmente
            if need_transform and utm_zone:
                st.sidebar.info(f"🔄 Transform UTM {utm_zone}N → WGS84")
                
                def utm_to_latlon_simple(x, y, zone=13):
                    """Conversión aproximada UTM a Lat/Lon para Hemisferio Norte"""
                    # Centro de la zona UTM
                    lon_center = (zone - 1) * 6 - 180 + 3
                    
                    # Conversión simplificada (aproximada)
                    # Para hemisferio NORTE: y es directamente metros desde ecuador
                    lat = y / 111320.0  # NO restar 10000000 (eso es para hemisferio sur)
                    lon = lon_center + (x - 500000) / (111320.0 * np.cos(np.radians(lat)))
                    
                    return lon, lat
                
                for feature in features:
                    try:
                        geom = feature['geometry']
                        geom_type = geom['type']
                        
                        if geom_type == 'Polygon':
                            # Transformar cada coordenada del polígono
                            new_coords = []
                            for ring in geom['coordinates']:
                                new_ring = []
                                for coord in ring:
                                    lon, lat = utm_to_latlon_simple(coord[0], coord[1], utm_zone)
                                    new_ring.append([lon, lat])
                                new_coords.append(new_ring)
                            
                            feature_wgs84 = {
                                'type': 'Feature',
                                'geometry': {
                                    'type': 'Polygon',
                                    'coordinates': new_coords
                                },
                                'properties': dict(feature['properties'])  # Convertir a dict
                            }
                            features_wgs84.append(feature_wgs84)
                        
                        elif geom_type == 'Point':
                            lon, lat = utm_to_latlon_simple(geom['coordinates'][0], geom['coordinates'][1], utm_zone)
                            feature_wgs84 = {
                                'type': 'Feature',
                                'geometry': {
                                    'type': 'Point',
                                    'coordinates': [lon, lat]
                                },
                                'properties': dict(feature['properties'])  # Convertir a dict
                            }
                            features_wgs84.append(feature_wgs84)
                        else:
                            features_wgs84.append(feature)
                    except Exception as e:
                        features_wgs84.append(feature)
                
                st.sidebar.success(f"✅ Transformed {len(features_wgs84)} features")
            else:
                features_wgs84 = features
                st.sidebar.info("📍 Using original coordinates")
            
            # Crear FeatureGroup con pane de z-index alto
            mag_group = folium.FeatureGroup(name='Magnetometry', show=True, overlay=True)
            
            features_added = 0
            max_features = min(len(features_wgs84), len(mag.campo_total), 3000)
            
            # Agregar features transformados
            for i in range(max_features):
                valor = mag.campo_total[i]
                if np.isnan(valor) or np.isinf(valor):
                    continue
                
                # Color
                norm_val = (valor - campo_min) / (campo_max - campo_min) if campo_max != campo_min else 0.5
                norm_val = np.clip(norm_val, 0, 1)
                
                color = cm.get_cmap('jet')(norm_val)
                color_hex = '#{:02x}{:02x}{:02x}'.format(
                    int(color[0]*255), int(color[1]*255), int(color[2]*255)
                )
                
                # Anomalía
                desviacion = (valor - campo_mean) / campo_std if campo_std > 0 else 0
                anomalia = "🔴" if desviacion > 1 else ("🔵" if desviacion < -1 else "⚪")
                
                try:
                    folium.GeoJson(
                        features_wgs84[i],
                        style_function=lambda x, c=color_hex: {
                            'fillColor': c,
                            'color': 'black',
                            'weight': 0.8,
                            'fillOpacity': layer_opacity * 0.7,
                            'zIndex': 1000  # z-index alto para que se vea encima
                        },
                        tooltip=f"{anomalia} {valor:.1f} nT"
                    ).add_to(mag_group)
                    
                    features_added += 1
                    
                except Exception as geom_error:
                    if features_added == 0:  # Solo mostrar el primer error
                        st.sidebar.warning(f"⚠️ Geom error: {str(geom_error)[:80]}")
                    continue
            
            mag_group.add_to(m)
            
            # Info final
            st.sidebar.success(f"✅ Magnetometry: {features_added}/{max_features} rendered")
            st.sidebar.info(f"📊 Valores: min={campo_min:.1f}, max={campo_max:.1f}, mean={campo_mean:.1f}")
            st.sidebar.info(f"🎨 Colormap: jet")
            
            if features_added == 0:
                st.sidebar.error("❌ No features rendered. Check geometries and CRS.")
            else:
                # Verificar bounds del primer feature
                if len(features_wgs84) > 0:
                    first_geom = features_wgs84[0]['geometry']
                    if first_geom['type'] == 'Polygon':
                        coords = first_geom['coordinates'][0]
                        lons = [c[0] for c in coords]
                        lats = [c[1] for c in coords]
                        st.sidebar.info(f"📍 Bounds: Lon [{min(lons):.4f}, {max(lons):.4f}], Lat [{min(lats):.4f}, {max(lats):.4f}]")
            
        except Exception as e:
            st.sidebar.error(f"❌ Mag error: {str(e)[:200]}")
            import traceback
            tb = traceback.format_exc()
            st.sidebar.code(tb[-600:])
    
    # Controles del mapa
    folium.plugins.MeasureControl(position='topleft').add_to(m)
    folium.plugins.Fullscreen(position='topleft').add_to(m)
    folium.plugins.MousePosition().add_to(m)
    
    # Herramienta de dibujo para definir área de interés
    draw = folium.plugins.Draw(
        export=True,
        position='topleft',
        draw_options={
            'polyline': False,
            'circle': False,
            'circlemarker': False,
            'marker': False,
            'polygon': {
                'allowIntersection': False,
                'shapeOptions': {
                    'color': '#00ff00',
                    'weight': 3,
                    'fillOpacity': 0.2
                }
            },
            'rectangle': {
                'shapeOptions': {
                    'color': '#00ff00',
                    'weight': 3,
                    'fillOpacity': 0.2
                }
            }
        }
    )
    draw.add_to(m)
    
    # Mostrar mapa y capturar geometrías dibujadas
    map_data = st_folium(
        m,
        width=None,  # Full width
        height=700,
        returned_objects=['all_drawings'],  # Capturar geometrías dibujadas
        key="main_map"  # Key estable
    )

    # ========================================================================
    # PROCESAR GEOMETRÍA DIBUJADA (AOI)
    # ========================================================================
    if map_data and 'all_drawings' in map_data and map_data['all_drawings']:
        drawings = map_data['all_drawings']
        if drawings:
            geom = drawings[0]['geometry']
            coords = geom['coordinates'][0] if geom['type'] == 'Polygon' else geom['coordinates']
            
            # Calcular bounds
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            bbox = [min(lons), min(lats), max(lons), max(lats)]
            
            # Guardar en session_state
            st.session_state.aoi_bbox = bbox
            st.session_state.aoi_geom = geom
            
            st.sidebar.success(f"✅ AOI defined: {len(drawings)} polygon(s)")

with col_inspector:
    st.markdown("### 📊 Inspector")
    
    # Mostrar sección de descarga
    with st.expander("📐 AREA OF INTEREST & DOWNLOAD", expanded=False):
        if not MODULES_LOADED:
            st.warning("⚠️ Download features are not available in cloud mode")
            st.info("TerrafDownload module requires local installation")
        else:
            # Usar AOI si existe, sino pedir manual
            if 'aoi_bbox' in st.session_state:
                bbox = st.session_state.aoi_bbox
                st.success(f"✅ AOI: [{bbox[0]:.4f}, {bbox[1]:.4f}, {bbox[2]:.4f}, {bbox[3]:.4f}]")
            else:
                st.info("👆 Draw area on map OR enter manually:")
                col_a, col_b = st.columns(2)
                with col_a:
                    min_lon = st.number_input("Min Lon", value=-106.0, format="%.4f")
                    max_lon = st.number_input("Max Lon", value=-105.5, format="%.4f")
                with col_b:
                    min_lat = st.number_input("Min Lat", value=28.0, format="%.4f")
                    max_lat = st.number_input("Max Lat", value=28.5, format="%.4f")
                bbox = [min_lon, min_lat, max_lon, max_lat]
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start", value=pd.to_datetime("2023-01-01"), key="search_start")
            with col2:
                end_date = st.date_input("End", value=pd.to_datetime("2023-12-31"), key="search_end")
            
            cloud_cover = st.slider("Max Cloud %", 0, 100, 20, key="search_cloud")
        
            st.warning("⚠️ Automatic download requires authentication. Use 'Search Only' to find scenes, then download manually from USGS EarthExplorer.")
        
            download_mode = st.radio("Mode", ["Search Only", "Search & Download"], key="download_mode")
            data_source = st.selectbox("Source", ["Landsat (USGS)", "HLS", "Sentinel-2"], key="search_source")
        
            # Buscar escenas
            if st.button("🔍 Search Scenes", type="primary"):
                with st.spinner("Searching..."):
                    try:
                        downloader = st.session_state.downloader
                    
                        if "Landsat" in data_source:
                            # Usar AWS público para Landsat (sin autenticación)
                            scenes = downloader.get_landsat_scenes_aws(
                            bbox=bbox,
                            start_date=start_date.strftime('%Y-%m-%d'),
                            end_date=end_date.strftime('%Y-%m-%d')
                            )
                            # Filtrar por cloud cover
                            scenes = [s for s in scenes if s.get('cloud_cover', 100) <= cloud_cover]
                        elif data_source == "HLS":
                            # Usar Planetary Computer para HLS
                            scenes = downloader.get_planetary_computer_scenes(
                            bbox=bbox,
                            start_date=start_date.strftime('%Y-%m-%d'),
                            end_date=end_date.strftime('%Y-%m-%d'),
                            collection='hls'
                            )
                            scenes = [s for s in scenes if s.get('cloud_cover', 100) <= cloud_cover]
                        else:  # Sentinel-2
                            scenes = downloader.get_planetary_computer_scenes(
                            bbox=bbox,
                            start_date=start_date.strftime('%Y-%m-%d'),
                            end_date=end_date.strftime('%Y-%m-%d'),
                            collection='sentinel-2-l2a'
                            )
                            scenes = [s for s in scenes if s.get('cloud_cover', 100) <= cloud_cover]
                    
                        st.session_state.search_results = scenes
                        st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ Search error: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
                        st.session_state.search_results = None
        
            # Mostrar resultados de búsqueda (siempre visibles si existen)
            if 'search_results' in st.session_state and st.session_state.search_results:
                scenes = st.session_state.search_results
                st.success(f"✅ Found {len(scenes)} scenes")
            
                if st.button("🗑️ Clear Results", key="clear_search"):
                    st.session_state.search_results = None
                    st.rerun()
            
                if scenes:
                    # Tabla de resultados
                    scene_options = [f"{s['id']} | {s['date']} | ☁️{s.get('cloud_cover', 0):.1f}%" for s in scenes]
                    selected_scene_idx = st.selectbox("Select scene", range(len(scene_options)), format_func=lambda x: scene_options[x])
                
                    selected_scene = scenes[selected_scene_idx]
                
                    # Mostrar enlaces de descarga manual
                    st.markdown("### 📥 Download Options")
                
                    # Link a EarthExplorer
                    scene_id = selected_scene['id']
                    earthexplorer_url = f"https://earthexplorer.usgs.gov/"
                    st.markdown(f"**Manual Download (Recommended):**")
                    st.markdown(f"1. Go to [USGS EarthExplorer]({earthexplorer_url})")
                    st.markdown(f"2. Search for scene: `{scene_id}`")
                    st.markdown(f"3. Download to `datos/downloaded/{scene_id}/`")
                    st.markdown(f"4. Use 'Load Local Scene' in sidebar")
                
                    st.markdown("---")
                
                    # Botón de descarga automática (experimental)
                    if download_mode == "Search & Download":
                        if st.button("🧪 Try Automatic Download (Experimental)", type="secondary"):
                            with st.spinner(f"Downloading {selected_scene['id']}..."):
                                try:
                                    downloader = st.session_state.downloader
                                    
                                    if 'item' in selected_scene:
                                        # Determinar fuente y usar método apropiado
                                        source = selected_scene.get('source', 'unknown')
                                        
                                        if source == 'aws':
                                            # Descargar desde AWS (público, sin autenticación)
                                            downloaded = downloader.download_from_aws(selected_scene)
                                        elif source == 'planetary_computer':
                                            # Descargar desde Planetary Computer (puede fallar)
                                            downloaded = downloader.download_from_planetary_computer(selected_scene)
                                        else:
                                            # Intentar AWS por defecto
                                            downloaded = downloader.download_from_aws(selected_scene)
                                        
                                        if downloaded and len(downloaded) > 0:
                                            # Verificar que no sean archivos HTML de error
                                            scene_path = downloader.output_dir / selected_scene['id']
                                            first_file = list(scene_path.glob("*.TIF"))[0] if scene_path.exists() else None
                                            
                                            if first_file and first_file.stat().st_size < 100000:  # < 100KB es sospechoso
                                                st.error("❌ Download failed - files are too small (likely HTML error pages)")
                                                st.warning("⚠️ USGS requires authentication. Please use manual download from EarthExplorer.")
                                            else:
                                                st.success(f"✅ Downloaded {len(downloaded)} files")
                                                st.info(f"📂 Location: {scene_path}")
                                                
                                                # Auto-cargar la escena descargada
                                                if scene_path.exists():
                                                    pr = TerrafPR(str(scene_path))
                                                    pr.cargar_bandas(reducir=True, factor=4)
                                                    st.session_state.landsat_data = pr
                                                    st.session_state.landsat_scene_name = selected_scene['id']
                                                    # Activar capa RGB Natural automáticamente
                                                    st.session_state.active_layers['rgb_natural'] = True
                                                    st.success("✅ Scene loaded and ready!")
                                                    st.rerun()
                                        else:
                                            st.error("❌ No files were downloaded. Check logs for details.")
                                    else:
                                        st.warning("⚠️ Download not implemented for this source yet")
                                        
                                except Exception as e:
                                    st.error(f"❌ Download error: {str(e)}")
                                    import traceback
                                    st.code(traceback.format_exc())
    
    st.markdown("---")
    
    # Estadísticas generales
    if st.session_state.landsat_data:
        st.markdown("**Landsat Scene:**")
        pr = st.session_state.landsat_data
        st.text(f"Bands: {len(pr.bandas)}")
        st.text(f"Resolution: ~30m")
    
    if st.session_state.indices:
        st.markdown("**Indices Calculated:**")
        for idx_name, idx_data in st.session_state.indices.items():
            with st.expander(f"📈 {idx_name.title()}", expanded=False):
                st.text(f"Min: {np.nanmin(idx_data):.4f}")
                st.text(f"Max: {np.nanmax(idx_data):.4f}")
                st.text(f"Mean: {np.nanmean(idx_data):.4f}")
                
                # Mini histogram
                fig_mini, ax_mini = plt.subplots(figsize=(3, 2))
                data_flat = idx_data[~np.isnan(idx_data)].flatten()
                ax_mini.hist(data_flat, bins=30, color='steelblue', alpha=0.7)
                ax_mini.set_ylabel('Freq', fontsize=8)
                ax_mini.tick_params(labelsize=7)
                st.pyplot(fig_mini)
                plt.close()
    
    if st.session_state.mag_data:
        st.markdown("**🧲 Magnetometry:**")
        mag = st.session_state.mag_data['mag']
        
        # Campo total
        with st.expander("📡 Total Field", expanded=True):
            st.metric("Points", f"{len(mag.campo_total):,}")
            st.metric("Range (nT)", f"{np.nanmin(mag.campo_total):.1f} - {np.nanmax(mag.campo_total):.1f}")
            st.metric("Mean (nT)", f"{np.nanmean(mag.campo_total):.1f}")
            st.metric("Std Dev (nT)", f"{np.nanstd(mag.campo_total):.1f}")
            
            # Mini histogram
            fig_mag, ax_mag = plt.subplots(figsize=(3, 2))
            ax_mag.hist(mag.campo_total[~np.isnan(mag.campo_total)], bins=30, 
                       color='darkblue', alpha=0.7, edgecolor='black')
            ax_mag.set_ylabel('Freq', fontsize=8)
            ax_mag.set_xlabel('nT', fontsize=8)
            ax_mag.tick_params(labelsize=7)
            ax_mag.grid(True, alpha=0.3)
            st.pyplot(fig_mag)
            plt.close()
        
        # Derivadas calculadas
        if mag.derivadas:
            with st.expander(f"📈 Derivatives ({len(mag.derivadas)})", expanded=False):
                for deriv_name, deriv_data in mag.derivadas.items():
                    st.text(f"• {deriv_name.replace('_', ' ').title()}")
                    st.text(f"  Range: {np.nanmin(deriv_data):.2e} - {np.nanmax(deriv_data):.2e}")
        
        # Anomalía residual
        if mag.anomalia is not None:
            with st.expander("🎯 Residual Anomaly", expanded=False):
                st.metric("Range (nT)", f"{np.nanmin(mag.anomalia):.1f} - {np.nanmax(mag.anomalia):.1f}")
                st.metric("Mean (nT)", f"{np.nanmean(mag.anomalia):.1f}")
                
                # Mini histogram
                fig_anom, ax_anom = plt.subplots(figsize=(3, 2))
                ax_anom.hist(mag.anomalia[~np.isnan(mag.anomalia)], bins=30, 
                           color='darkred', alpha=0.7, edgecolor='black')
                ax_anom.set_ylabel('Freq', fontsize=8)
                ax_anom.set_xlabel('nT', fontsize=8)
                ax_anom.tick_params(labelsize=7)
                ax_anom.grid(True, alpha=0.3)
                st.pyplot(fig_anom)
                plt.close()

# ============================================================================
# PANEL INFERIOR - VISUALIZACIONES RÁPIDAS
# ============================================================================
if st.session_state.indices or st.session_state.mag_data:
    st.markdown("---")
    st.markdown("### 📊 Quick Visualizations")
    
    tabs = st.tabs(["📈 Profiles", "📊 Histograms", "🎨 Colormaps"])
    
    with tabs[0]:
        st.info("Profile plots coming soon")
    
    with tabs[1]:
        if st.session_state.indices:
            cols = st.columns(min(3, len(st.session_state.indices)))
            for i, (name, data) in enumerate(list(st.session_state.indices.items())[:3]):
                with cols[i]:
                    fig, ax = plt.subplots(figsize=(4, 3))
                    data_flat = data[~np.isnan(data)].flatten()
                    ax.hist(data_flat, bins=50, color='steelblue', alpha=0.7, edgecolor='black')
                    ax.set_title(name.title(), fontsize=10, fontweight='bold')
                    ax.set_xlabel('Value', fontsize=9)
                    ax.set_ylabel('Frequency', fontsize=9)
                    ax.tick_params(labelsize=8)
                    ax.grid(True, alpha=0.3)
                    st.pyplot(fig)
                    plt.close()
    
    with tabs[2]:
        if st.session_state.indices:
            # Mostrar miniaturas de colormaps
            st.info("Index colormaps preview coming soon")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 12px;'>
TERRAF v2.0 | Map-Centric Interface | Powered by Streamlit + Folium
</div>
""", unsafe_allow_html=True)
