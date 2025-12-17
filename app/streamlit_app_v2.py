import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, MeasureControl, MiniMap
import os
import numpy as np
import rasterio
import pyproj
from PIL import Image
from matplotlib import pyplot as plt
from matplotlib import cm
import sys
import json
from datetime import datetime
import pandas as pd

# Ajustar ruta para importar módulos locales
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from terraf_pr import TerrafPR
from reporte_md import ReporteMarkdown
from terraf_mag import TerrafMag

# ============================================================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================================================
st.set_page_config(
    page_title="TERRAF - Geospatial Intelligence Platform",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# INICIALIZACIÓN DE SESSION STATE
# ============================================================================
if 'workflow_step' not in st.session_state:
    st.session_state.workflow_step = 1
if 'aoi_defined' not in st.session_state:
    st.session_state.aoi_defined = False
if 'data_acquired' not in st.session_state:
    st.session_state.data_acquired = False
if 'project_name' not in st.session_state:
    st.session_state.project_name = f"TERRAF_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
if 'aoi_coords' not in st.session_state:
    st.session_state.aoi_coords = None
if 'selected_sensor' not in st.session_state:
    st.session_state.selected_sensor = "Landsat 9"
if 'projects_history' not in st.session_state:
    st.session_state.projects_history = []
if 'data_path' not in st.session_state:
    st.session_state.data_path = None
if 'indices_calculated' not in st.session_state:
    st.session_state.indices_calculated = False
if 'mag_data_loaded' not in st.session_state:
    st.session_state.mag_data_loaded = False
if 'mag' not in st.session_state:
    st.session_state.mag = None

# ============================================================================
# CSS PERSONALIZADO
# ============================================================================
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    .workflow-card {
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #cbd5e1;
        background-color: #f8fafc;
        margin: 1rem 0;
    }
    .step-active {
        border-left-color: #10b981 !important;
        background-color: #ecfdf5 !important;
    }
    .step-completed {
        border-left-color: #6b7280 !important;
        background-color: #f9fafb !important;
    }
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        text-align: center;
    }
    .info-box {
        background: #eff6ff;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HEADER
# ============================================================================
st.markdown("""
<div class="main-header">
    <h1>🌍 TERRAF - Geospatial Intelligence Platform</h1>
    <p style="font-size: 1.1rem; opacity: 0.9;">
        Professional Remote Sensing & Geophysical Analysis
    </p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR - NAVIGATION
# ============================================================================
with st.sidebar:
    st.markdown("### 🧭 Workflow Navigation")
    
    # Project info
    project_name = st.text_input("📁 Project Name", value=st.session_state.project_name)
    if project_name != st.session_state.project_name:
        st.session_state.project_name = project_name
    
    st.divider()
    
    # Workflow steps
    steps = [
        ("🟢", "1. Inicio", "Define AOI", 1),
        ("🛰️", "2. Adquisición", "Select data", 2),
        ("🧪", "3. Índices", "Process spectral", 3),
        ("📊", "4. Temporal", "Time analysis", 4),
        ("🌍", "5. Geofísica", "Physical data", 5),
        ("📤", "6. Exportación", "Export results", 6),
        ("📁", "7. Historial", "Projects", 7),
    ]
    
    for icon, title, desc, step_num in steps:
        # Determine status
        if step_num < st.session_state.workflow_step:
            status = "✅"
        elif step_num == st.session_state.workflow_step:
            status = "▶️"
        else:
            status = "⏸️"
        
        # Navigation button
        if st.button(f"{status} {icon} {title}", key=f"nav_{step_num}", use_container_width=True):
            st.session_state.workflow_step = step_num
            st.rerun()
        st.caption(f"   {desc}")
    
    st.divider()
    
    # Quick stats
    st.markdown("### 📊 Session Status")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("AOI", "✅" if st.session_state.aoi_defined else "❌")
    with col2:
        st.metric("Data", "✅" if st.session_state.data_acquired else "❌")
    
    if 'pr' in st.session_state and st.session_state.pr is not None:
        st.success("✅ Analysis ready")
    else:
        st.info("⏳ No analysis loaded")

# ============================================================================
# MAIN CONTENT AREA
# ============================================================================
current_step = st.session_state.workflow_step

# ============================================================================
# MÓDULO 1: INICIO - AOI SELECTION
# ============================================================================
if current_step == 1:
    st.markdown("## 🟢 Step 1: Define Area of Interest (AOI)")
    st.markdown("Select or upload your study area using one of the following methods:")
    
    # Method selector
    col1, col2 = st.columns([2, 1])
    with col1:
        aoi_method = st.radio(
            "AOI Input Method",
            ["🗺️ Draw on Map", "📁 Upload File (Shapefile/GeoJSON)", "📍 Enter Coordinates", "📂 Select Existing Scene"],
            horizontal=False
        )
    
    with col2:
        st.markdown("### 📋 AOI Status")
        if st.session_state.aoi_defined:
            st.success("✅ AOI Defined")
            if st.session_state.aoi_coords:
                with st.expander("View AOI Details"):
                    st.json(st.session_state.aoi_coords)
            if st.button("🔄 Reset AOI"):
                st.session_state.aoi_defined = False
                st.session_state.aoi_coords = None
                st.rerun()
        else:
            st.warning("⏳ AOI Not Defined")
    
    st.divider()
    
    # ============ Method 1: Draw on Map ============
    if aoi_method == "🗺️ Draw on Map":
        st.markdown("### 🖊️ Draw your AOI on the map")
        st.info("💡 Use the drawing tools on the left side of the map to define your area of interest")
        
        # Create map with drawing tools
        m = folium.Map(location=[28.0, -106.0], zoom_start=6)
        
        # Add drawing plugin
        Draw(
            export=True,
            position='topleft',
            draw_options={
                'polyline': False,
                'rectangle': True,
                'polygon': True,
                'circle': False,
                'marker': False,
                'circlemarker': False,
            }
        ).add_to(m)
        
        # Multiple basemaps
        folium.TileLayer('OpenStreetMap', name='Streets').add_to(m)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='ESRI World Imagery',
            name='Satellite'
        ).add_to(m)
        folium.LayerControl().add_to(m)
        
        map_data = st_folium(m, width=1200, height=600, key="aoi_map")
        
        # Process drawn features
        if map_data and map_data.get('all_drawings'):
            st.success(f"✅ {len(map_data['all_drawings'])} feature(s) drawn")
            st.session_state.aoi_coords = map_data['all_drawings']
            st.session_state.aoi_defined = True
            with st.expander("View GeoJSON"):
                st.json(map_data['all_drawings'])
    
    # ============ Method 2: Upload File ============
    elif aoi_method == "📁 Upload File (Shapefile/GeoJSON)":
        st.markdown("### 📤 Upload AOI File")
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['geojson', 'json', 'shp', 'zip'],
            help="Upload a GeoJSON or Shapefile (as .zip containing .shp, .shx, .dbf)"
        )
        
        if uploaded_file:
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            # TODO: Parse and validate geometry
            st.session_state.aoi_defined = True
            st.info("⚠️ File parsing will be implemented in next iteration")
    
    # ============ Method 3: Coordinates ============
    elif aoi_method == "📍 Enter Coordinates":
        st.markdown("### 📐 Enter Bounding Box Coordinates")
        
        col1, col2 = st.columns(2)
        with col1:
            north = st.number_input("North Latitude", value=28.5, format="%.6f")
            south = st.number_input("South Latitude", value=27.5, format="%.6f")
        with col2:
            east = st.number_input("East Longitude", value=-105.5, format="%.6f")
            west = st.number_input("West Longitude", value=-106.5, format="%.6f")
        
        if st.button("✅ Confirm AOI"):
            st.session_state.aoi_coords = {
                "type": "bbox",
                "coordinates": {"north": north, "south": south, "east": east, "west": west}
            }
            st.session_state.aoi_defined = True
            st.success("✅ AOI coordinates saved!")
            
            # Show preview map
            center_lat = (north + south) / 2
            center_lon = (east + west) / 2
            m = folium.Map(location=[center_lat, center_lon], zoom_start=8)
            folium.Rectangle(
                bounds=[[south, west], [north, east]],
                color='red',
                fill=True,
                fillOpacity=0.2
            ).add_to(m)
            st_folium(m, width=1200, height=400)
    
    # ============ Method 4: Existing Scene ============
    elif aoi_method == "📂 Select Existing Scene":
        st.markdown("### 📂 Select from Available Landsat Scenes")
        
        # Get available scenes
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'datos', 'landsat9', 'coleccion-1')
        carpetas_disponibles = []
        if os.path.exists(data_dir):
            carpetas_disponibles = [d for d in os.listdir(data_dir) 
                                  if os.path.isdir(os.path.join(data_dir, d)) and d.startswith('LC')]
        
        if carpetas_disponibles:
            selected_scene = st.selectbox("Available Landsat 9 Scenes", carpetas_disponibles)
            
            # Parse scene metadata
            scene_info = {
                "Sensor": selected_scene[0:4],
                "Path": selected_scene[10:13],
                "Row": selected_scene[13:16],
                "Date": selected_scene[17:25]
            }
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Scene Information:**")
                for key, value in scene_info.items():
                    st.text(f"{key}: {value}")
            
            with col2:
                if st.button("✅ Use This Scene", type="primary"):
                    st.session_state.aoi_coords = {
                        "type": "landsat_scene",
                        "scene": selected_scene,
                        "path": os.path.join(data_dir, selected_scene)
                    }
                    st.session_state.aoi_defined = True
                    st.session_state.data_path = os.path.join(data_dir, selected_scene)
                    st.success(f"✅ Scene selected: {selected_scene}")
        else:
            st.warning("⚠️ No Landsat scenes found in datos/landsat9/coleccion-1/")
            st.info("📍 Place your Landsat data in: `datos/landsat9/coleccion-1/`")
    
    # Navigation
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    with col3:
        if st.session_state.aoi_defined:
            if st.button("Next: Data Acquisition ➡️", type="primary", use_container_width=True):
                st.session_state.workflow_step = 2
                st.rerun()

# ============================================================================
# MÓDULO 2: ADQUISICIÓN DE DATOS
# ============================================================================
elif current_step == 2:
    st.markdown("## 🛰️ Step 2: Data Acquisition")
    st.markdown("Configure and acquire satellite data for your AOI")
    
    # Sensor selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📡 Sensor Selection")
        
        sensor = st.selectbox(
            "Select Satellite Sensor",
            ["Landsat 9", "Landsat 8", "Sentinel-2", "MODIS"],
            help="Choose the satellite sensor for your analysis"
        )
        st.session_state.selected_sensor = sensor
        
        # Date range
        st.markdown("### 📅 Date Range")
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            start_date = st.date_input("Start Date", value=datetime(2024, 1, 1))
        with col_date2:
            end_date = st.date_input("End Date", value=datetime.now())
        
        # Filters
        st.markdown("### 🔍 Data Filters")
        cloud_cover = st.slider("Maximum Cloud Cover (%)", 0, 100, 20)
        
        # Data source
        st.markdown("### 📦 Data Source")
        data_source = st.radio(
            "Select data source",
            ["📂 Local Files", "🌐 Google Earth Engine", "🌐 USGS Earth Explorer"],
            horizontal=True
        )
        
        if data_source == "📂 Local Files":
            st.info("Using local Landsat data from `datos/landsat9/coleccion-1/`")
            
            if st.session_state.data_path:
                st.success(f"✅ Data path: {os.path.basename(st.session_state.data_path)}")
                st.session_state.data_acquired = True
            else:
                st.warning("⚠️ No data path selected. Go back to Step 1 and select a scene.")
        
        elif data_source == "🌐 Google Earth Engine":
            st.info("🚧 GEE integration will be implemented in future iteration")
            st.markdown("**Requirements:**")
            st.markdown("- Google Earth Engine account")
            st.markdown("- Authenticated API access")
            st.markdown("- AOI defined as GeoJSON")
        
        else:  # USGS Earth Explorer
            st.info("🚧 USGS integration will be implemented in future iteration")
            st.markdown("**Manual workflow:**")
            st.markdown("1. Visit [USGS EarthExplorer](https://earthexplorer.usgs.gov/)")
            st.markdown("2. Search for scenes within your AOI")
            st.markdown("3. Download Level 1 data")
            st.markdown("4. Place in `datos/landsat9/coleccion-1/`")
    
    with col2:
        st.markdown("### 📊 Data Preview")
        
        if st.session_state.data_acquired and st.session_state.data_path:
            # Show scene thumbnail or info
            st.success("✅ Data Ready")
            
            # Coverage stats
            st.markdown("**Coverage:**")
            st.metric("Path/Row", "031/040")
            st.metric("Date", "2025-11-08")
            st.metric("Cloud Cover", "5%")
            
            # Quality indicators
            st.markdown("**Quality:**")
            st.progress(0.95, text="Data Quality: 95%")
            
        else:
            st.info("⏳ Select and validate data source")
    
    # Navigation
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ Back to AOI", use_container_width=True):
            st.session_state.workflow_step = 1
            st.rerun()
    with col3:
        if st.session_state.data_acquired:
            if st.button("Next: Process Indices ➡️", type="primary", use_container_width=True):
                st.session_state.workflow_step = 3
                st.rerun()

# ============================================================================
# MÓDULO 3: PROCESAMIENTO DE ÍNDICES
# ============================================================================
elif current_step == 3:
    st.markdown("## 🧪 Step 3: Spectral Index Processing")
    st.markdown("Calculate spectral indices for mineral exploration")
    
    # Configuration panel
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📋 Index Selection")
        
        # Index checkboxes
        calc_gossan = st.checkbox("🟠 Gossan Index", value=True, 
                                   help="Iron oxide detection using band ratios")
        calc_oxidos = st.checkbox("🔴 Iron Oxides (B4/B2)", value=True,
                                   help="Ferric iron absorption feature")
        calc_argilica = st.checkbox("🔵 Argillic Alteration (B6/B7)", value=True,
                                     help="Clay minerals detection")
        calc_propilitica = st.checkbox("🟢 Propylitic Alteration (B5/B7)", value=True,
                                        help="Chlorite-epidote detection")
        
        st.divider()
        
        # Processing options
        st.markdown("### ⚙️ Processing Options")
        
        reduce_resolution = st.checkbox(
            "🚀 Fast Mode (Reduce Resolution 4x)",
            value=True,
            help="Speeds up processing by 4x with minimal quality loss"
        )
        
        resolution = "120m/pixel" if reduce_resolution else "30m/pixel"
        st.info(f"Current resolution: **{resolution}**")
        
        st.divider()
        
        # Execute button
        if st.button("▶️ Execute Analysis", type="primary", use_container_width=True):
            if not st.session_state.data_acquired or not st.session_state.data_path:
                st.error("❌ No data available. Complete Step 2 first.")
            else:
                with st.spinner("🛰️ Processing satellite data..."):
                    try:
                        # Initialize TerrafPR
                        pr = TerrafPR(st.session_state.data_path)
                        
                        # Load bands
                        st.info("📡 Loading spectral bands...")
                        pr.cargar_bandas()
                        st.success(f"✅ {len(pr.bandas)} bands loaded")
                        
                        # Calculate indices
                        if calc_gossan:
                            st.info("⛰️ Calculating Gossan Index...")
                            pr.calcular_gossan()
                        
                        if calc_oxidos:
                            st.info("🔴 Calculating Iron Oxides...")
                            pr.calcular_ratio_oxidos()
                        
                        if calc_argilica:
                            st.info("🔵 Calculating Argillic Alteration...")
                            pr.calcular_ratio_argilica()
                        
                        if calc_propilitica:
                            st.info("🟢 Calculating Propylitic Alteration...")
                            pr.calcular_propilitica()
                        
                        # Save to session state
                        st.session_state.pr = pr
                        st.session_state.indices_calculated = True
                        
                        st.success("✅ Analysis completed successfully!")
                        st.info("📊 Scroll down to see visualizations")
                        
                    except Exception as e:
                        st.error(f"❌ Error during processing: {str(e)}")
                        st.exception(e)
    
    with col2:
        st.markdown("### 📊 Results Summary")
        
        if 'pr' in st.session_state and st.session_state.pr is not None:
            pr = st.session_state.pr
            
            st.success("✅ Analysis Complete")
            
            # Statistics
            if hasattr(pr, 'gossan'):
                area_gossan = np.sum(pr.zona_gossan) * (pr.resolucion_efectiva ** 2) / 1e6
                st.metric("Gossan Area", f"{area_gossan:.2f} km²")
            
            if hasattr(pr, 'zona_oxidos'):
                area_oxidos = np.sum(pr.zona_oxidos) * (pr.resolucion_efectiva ** 2) / 1e6
                st.metric("Iron Oxides Area", f"{area_oxidos:.2f} km²")
            
            if hasattr(pr, 'zona_argilica'):
                area_argilica = np.sum(pr.zona_argilica) * (pr.resolucion_efectiva ** 2) / 1e6
                st.metric("Argillic Area", f"{area_argilica:.2f} km²")
            
            if hasattr(pr, 'zona_propilitica'):
                area_propilitica = np.sum(pr.zona_propilitica) * (pr.resolucion_efectiva ** 2) / 1e6
                st.metric("Propylitic Area", f"{area_propilitica:.2f} km²")
            
            st.divider()
            
            # Quick visualization
            st.markdown("**Index Statistics:**")
            if hasattr(pr, 'gossan'):
                st.text(f"Gossan: {np.nanmin(pr.gossan):.3f} - {np.nanmax(pr.gossan):.3f}")
            
        else:
            st.info("⏳ No results yet")
            st.markdown("Click **Execute Analysis** to start processing")
    
    # ========================================================================
    # VISUALIZACIONES - MAPAS DE ÍNDICES
    # ========================================================================
    if 'pr' in st.session_state and st.session_state.pr is not None:
        st.markdown("---")
        st.markdown("## 🗺️ Interactive Visualizations")
        
        pr = st.session_state.pr
        
        # Tabs para diferentes visualizaciones
        tab1, tab2, tab3 = st.tabs(["📊 RGB Composites", "🔥 Mineral Indices", "📈 Statistics"])
        
        with tab1:
            st.markdown("### RGB Composites")
            col_rgb1, col_rgb2 = st.columns(2)
            
            with col_rgb1:
                if 'B04' in pr.bandas and 'B03' in pr.bandas and 'B02' in pr.bandas:
                    st.markdown("**Natural Color (RGB: 4-3-2)**")
                    fig_rgb, ax_rgb = plt.subplots(figsize=(8, 8))
                    
                    # Crear RGB natural
                    r = pr.bandas['B04']
                    g = pr.bandas['B03']
                    b = pr.bandas['B02']
                    
                    # Normalizar
                    r_norm = np.clip((r - np.nanpercentile(r, 2)) / (np.nanpercentile(r, 98) - np.nanpercentile(r, 2)), 0, 1)
                    g_norm = np.clip((g - np.nanpercentile(g, 2)) / (np.nanpercentile(g, 98) - np.nanpercentile(g, 2)), 0, 1)
                    b_norm = np.clip((b - np.nanpercentile(b, 2)) / (np.nanpercentile(b, 98) - np.nanpercentile(b, 2)), 0, 1)
                    
                    rgb = np.dstack([r_norm, g_norm, b_norm])
                    ax_rgb.imshow(rgb)
                    ax_rgb.set_title("Natural Color", fontsize=14, fontweight='bold')
                    ax_rgb.axis('off')
                    st.pyplot(fig_rgb)
                    plt.close()
            
            with col_rgb2:
                if 'B05' in pr.bandas and 'B04' in pr.bandas and 'B03' in pr.bandas:
                    st.markdown("**False Color (RGB: 5-4-3)**")
                    fig_fc, ax_fc = plt.subplots(figsize=(8, 8))
                    
                    # Crear RGB falso color
                    r = pr.bandas['B05']
                    g = pr.bandas['B04']
                    b = pr.bandas['B03']
                    
                    r_norm = np.clip((r - np.nanpercentile(r, 2)) / (np.nanpercentile(r, 98) - np.nanpercentile(r, 2)), 0, 1)
                    g_norm = np.clip((g - np.nanpercentile(g, 2)) / (np.nanpercentile(g, 98) - np.nanpercentile(g, 2)), 0, 1)
                    b_norm = np.clip((b - np.nanpercentile(b, 2)) / (np.nanpercentile(b, 98) - np.nanpercentile(b, 2)), 0, 1)
                    
                    rgb = np.dstack([r_norm, g_norm, b_norm])
                    ax_fc.imshow(rgb)
                    ax_fc.set_title("False Color (Vegetation in Red)", fontsize=14, fontweight='bold')
                    ax_fc.axis('off')
                    st.pyplot(fig_fc)
                    plt.close()
        
        with tab2:
            st.markdown("### Mineral Exploration Indices")
            
            indices_to_show = []
            if hasattr(pr, 'gossan'):
                indices_to_show.append(('Gossan (Kaufmann)', pr.gossan, 'hot'))
            if hasattr(pr, 'ratio_oxidos'):
                indices_to_show.append(('Iron Oxides', pr.ratio_oxidos, 'RdYlBu_r'))
            if hasattr(pr, 'ratio_argilica'):
                indices_to_show.append(('Argillic Alteration', pr.ratio_argilica, 'viridis'))
            if hasattr(pr, 'propilitica'):
                indices_to_show.append(('Propylitic Alteration', pr.propilitica, 'plasma'))
            
            if len(indices_to_show) > 0:
                # Mostrar en grid 2x2
                ncols = 2
                nrows = (len(indices_to_show) + 1) // 2
                
                fig_indices, axes = plt.subplots(nrows, ncols, figsize=(14, 7*nrows))
                if nrows == 1:
                    axes = axes.reshape(1, -1)
                
                for idx, (name, data, cmap) in enumerate(indices_to_show):
                    row = idx // ncols
                    col = idx % ncols
                    ax = axes[row, col]
                    
                    im = ax.imshow(data, cmap=cmap)
                    ax.set_title(name, fontsize=12, fontweight='bold')
                    ax.axis('off')
                    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
                
                # Ocultar ejes vacíos
                for idx in range(len(indices_to_show), nrows * ncols):
                    row = idx // ncols
                    col = idx % ncols
                    axes[row, col].axis('off')
                
                plt.tight_layout()
                st.pyplot(fig_indices)
                plt.close()
            else:
                st.warning("No indices calculated yet")
        
        with tab3:
            st.markdown("### Statistical Analysis")
            
            if hasattr(pr, 'gossan'):
                col_stat1, col_stat2 = st.columns(2)
                
                with col_stat1:
                    st.markdown("**Gossan Index Distribution**")
                    fig_hist, ax_hist = plt.subplots(figsize=(8, 5))
                    
                    gossan_flat = pr.gossan[~np.isnan(pr.gossan)].flatten()
                    ax_hist.hist(gossan_flat, bins=50, color='orangered', alpha=0.7, edgecolor='black')
                    ax_hist.set_xlabel('Gossan Index Value')
                    ax_hist.set_ylabel('Frequency')
                    ax_hist.set_title('Gossan Index Histogram')
                    ax_hist.grid(True, alpha=0.3)
                    
                    st.pyplot(fig_hist)
                    plt.close()
                
                with col_stat2:
                    st.markdown("**Summary Statistics**")
                    
                    stats_data = {
                        'Metric': ['Min', 'Max', 'Mean', 'Median', 'Std Dev', 'Valid Pixels'],
                        'Value': [
                            f"{np.nanmin(gossan_flat):.4f}",
                            f"{np.nanmax(gossan_flat):.4f}",
                            f"{np.nanmean(gossan_flat):.4f}",
                            f"{np.nanmedian(gossan_flat):.4f}",
                            f"{np.nanstd(gossan_flat):.4f}",
                            f"{len(gossan_flat):,}"
                        ]
                    }
                    
                    st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)
    
    # Navigation
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ Back to Data", use_container_width=True):
            st.session_state.workflow_step = 2
            st.rerun()
    with col3:
        if st.session_state.indices_calculated:
            if st.button("Next: Temporal Analysis ➡️", type="primary", use_container_width=True):
                st.session_state.workflow_step = 4
                st.rerun()

# ============================================================================
# MÓDULO 4: ANÁLISIS TEMPORAL
# ============================================================================
elif current_step == 4:
    st.markdown("## 📊 Step 4: Temporal Analysis")
    st.markdown("🚧 **Under Development** - Multi-temporal change detection")
    
    st.info("""
    **Planned Features:**
    - Timeline slider for date selection
    - Before/After comparison maps
    - Change detection algorithms
    - Trend analysis graphs
    - Anomaly detection
    - Statistical time series
    """)
    
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ Back", use_container_width=True):
            st.session_state.workflow_step = 3
            st.rerun()
    with col3:
        if st.button("Next: Geophysics ➡️", type="primary", use_container_width=True):
            st.session_state.workflow_step = 5
            st.rerun()

# ============================================================================
# MÓDULO 5: GEOFÍSICA - MAGNETOMETRÍA
# ============================================================================
elif current_step == 5:
    st.markdown("## 🌍 Step 5: Geophysical Analysis - Magnetometry")
    st.markdown("Process and analyze magnetic field data from SGM or custom sources")
    
    # Main layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📂 Load Magnetic Data")
        
        # Data source selector
        data_source = st.radio(
            "Select data source",
            ["📁 SGM Shapefile", "📤 Upload Custom Data", "🔢 Enter Manual Data"],
            horizontal=True
        )
        
        if data_source == "📁 SGM Shapefile":
            # Find available shapefiles
            mag_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'datos', 'magnetometria')
            
            # Search for shapefiles recursively
            import glob
            shapefiles = glob.glob(os.path.join(mag_dir, '**', '*.shp'), recursive=True)
            
            if shapefiles:
                st.success(f"✅ Found {len(shapefiles)} shapefile(s)")
                
                selected_shp = st.selectbox(
                    "Select magnetic data file",
                    shapefiles,
                    format_func=lambda x: os.path.basename(x)
                )
                
                # Show file info
                st.text(f"📍 Path: {selected_shp}")
                
                # Load button
                if st.button("📊 Load Magnetic Data", type="primary"):
                    with st.spinner("Loading magnetic field data..."):
                        try:
                            import fiona
                            
                            # Load shapefile with fiona (avoiding geopandas)
                            features = []
                            with fiona.open(selected_shp, 'r') as src:
                                for feature in src:
                                    features.append(feature)
                            
                            # Convert to DataFrame
                            records = [f['properties'] for f in features]
                            df = pd.DataFrame(records)
                            
                            # Store DataFrame in session state for manual column selection
                            st.session_state.temp_mag_df = df
                            
                            # Initialize TerrafMag
                            mag = TerrafMag(dataframe=df)
                            
                            # Auto-detect magnetic field column
                            mag._detectar_columnas()
                            
                            if mag.campo_total is not None:
                                st.session_state.mag = mag
                                st.session_state.mag_data_loaded = True
                                st.success(f"✅ Loaded {len(df)} magnetic measurements")
                                st.info(f"📊 Columns: {', '.join(df.columns[:5])}...")
                                if 'temp_mag_df' in st.session_state:
                                    del st.session_state.temp_mag_df
                            else:
                                st.session_state.mag_needs_column = True
                        
                        except Exception as e:
                            st.error(f"❌ Error loading data: {str(e)}")
                
                # Manual column selection (outside the load button)
                if 'mag_needs_column' in st.session_state and st.session_state.mag_needs_column:
                    st.warning("⚠️ Could not auto-detect magnetic field column")
                    
                    if 'temp_mag_df' in st.session_state:
                        df = st.session_state.temp_mag_df
                        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                        
                        st.info(f"Available numeric columns: {', '.join(numeric_cols)}")
                        selected_col = st.selectbox("Select magnetic field column", numeric_cols, key="mag_col_select")
                        
                        if st.button("✅ Confirm Column Selection", type="primary"):
                            mag = TerrafMag(dataframe=df)
                            mag.campo_total = df[selected_col].values
                            st.session_state.mag = mag
                            st.session_state.mag_data_loaded = True
                            st.session_state.mag_needs_column = False
                            del st.session_state.temp_mag_df
                            st.success(f"✅ Column '{selected_col}' selected successfully!")
                            st.rerun()
            else:
                st.warning("⚠️ No shapefiles found in datos/magnetometria/")
                st.info("📍 Place your SGM magnetic data in: `datos/magnetometria/`")
        
        elif data_source == "📤 Upload Custom Data":
            uploaded_file = st.file_uploader(
                "Upload magnetic data file",
                type=['shp', 'csv', 'txt'],
                help="Shapefile (.shp) or CSV with magnetic field measurements"
            )
            
            if uploaded_file:
                st.success(f"✅ File uploaded: {uploaded_file.name}")
                st.info("🚧 Custom upload processing will be implemented soon")
        
        else:  # Manual data
            st.info("🚧 Manual data entry will be implemented soon")
        
        st.divider()
        
        # ====================================================================
        # VISUALIZACIÓN INMEDIATA DE DATOS CARGADOS
        # ====================================================================
        if st.session_state.mag_data_loaded and st.session_state.mag is not None:
            st.markdown("---")
            st.success("✅ Magnetic data loaded successfully!")
            
            mag = st.session_state.mag
            
            # Mostrar estadísticas básicas inmediatamente
            col_info1, col_info2, col_info3, col_info4 = st.columns(4)
            with col_info1:
                st.metric("Total Points", f"{len(mag.campo_total):,}")
            with col_info2:
                st.metric("Min Value", f"{np.nanmin(mag.campo_total):.2f}")
            with col_info3:
                st.metric("Max Value", f"{np.nanmax(mag.campo_total):.2f}")
            with col_info4:
                st.metric("Mean", f"{np.nanmean(mag.campo_total):.2f}")
            
            st.markdown("### 🗺️ Data Preview")
            
            # Crear visualización rápida
            fig_preview, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
            
            # Histogram
            campo_valid = mag.campo_total[~np.isnan(mag.campo_total)]
            ax1.hist(campo_valid, bins=50, color='steelblue', edgecolor='black', alpha=0.7)
            ax1.set_xlabel('Magnetic Field Value', fontsize=12)
            ax1.set_ylabel('Frequency', fontsize=12)
            ax1.set_title('Data Distribution', fontsize=14, fontweight='bold')
            ax1.grid(True, alpha=0.3)
            
            # Scatter plot (si hay muchos puntos, muestrear)
            n_sample = min(5000, len(campo_valid))
            sample_idx = np.random.choice(len(campo_valid), n_sample, replace=False)
            scatter = ax2.scatter(range(n_sample), campo_valid[sample_idx], 
                                c=campo_valid[sample_idx], cmap='RdYlBu_r', 
                                s=10, alpha=0.6)
            ax2.set_xlabel('Sample Index', fontsize=12)
            ax2.set_ylabel('Magnetic Field Value', fontsize=12)
            ax2.set_title('Data Profile', fontsize=14, fontweight='bold')
            plt.colorbar(scatter, ax=ax2, label='Magnetic Field')
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            st.pyplot(fig_preview)
            plt.close()
            
            st.markdown("---")
        
        # Analysis options (only if data is loaded)
        if st.session_state.mag_data_loaded and st.session_state.mag is not None:
            st.markdown("### 🧪 Analysis Options")
            
            mag = st.session_state.mag
            
            # Calculate statistics
            col_stat1, col_stat2 = st.columns(2)
            
            with col_stat1:
                if st.button("📊 Calculate Statistics"):
                    stats = mag.calcular_estadisticas()
                    st.session_state.mag_stats = stats
                    st.success("✅ Statistics calculated")
            
            with col_stat2:
                if st.button("🔍 Detect Anomalies"):
                    umbral = st.slider("Threshold (σ)", 1.0, 4.0, 2.0, 0.5)
                    anomalias = mag.detectar_anomalias(umbral_sigma=umbral)
                    st.session_state.mag_anomalias = anomalias
                    st.success(f"✅ Found {anomalias['n_anomalias_altas'] + anomalias['n_anomalias_bajas']} anomalies")
            
            st.divider()
            
            # Advanced processing
            st.markdown("### ⚙️ Advanced Processing")
            
            col_proc1, col_proc2 = st.columns(2)
            
            with col_proc1:
                if st.button("📉 Calculate Residual Anomaly"):
                    metodo = st.selectbox("Method", ["polinomial", "media_movil"])
                    with st.spinner("Calculating residual anomaly..."):
                        mag.calcular_anomalia_residual(metodo=metodo)
                        st.success("✅ Residual anomaly calculated")
                        st.session_state.mag = mag
            
            with col_proc2:
                if st.button("📐 Horizontal Derivative"):
                    with st.spinner("Calculating horizontal derivative..."):
                        mag.calcular_derivada_horizontal()
                        st.success("✅ Horizontal derivative calculated")
                        st.session_state.mag = mag
            
            # Smoothing
            if st.checkbox("🌊 Apply Smoothing"):
                metodo_smooth = st.selectbox("Smoothing method", ["savgol", "gaussian"])
                ventana = st.slider("Window size", 5, 51, 11, step=2)
                
                if st.button("Apply Smoothing"):
                    datos_suavizados = mag.suavizar_datos(metodo=metodo_smooth, ventana=ventana)
                    st.success("✅ Data smoothed")
    
    with col2:
        st.markdown("### 📊 Results")
        
        if st.session_state.mag_data_loaded and st.session_state.mag is not None:
            mag = st.session_state.mag
            
            # Statistics display
            if 'mag_stats' in st.session_state:
                stats = st.session_state.mag_stats
                
                st.markdown("**Field Statistics (nT):**")
                st.metric("Min", f"{stats['min']:.2f}")
                st.metric("Max", f"{stats['max']:.2f}")
                st.metric("Mean", f"{stats['mean']:.2f}")
                st.metric("Std Dev", f"{stats['std']:.2f}")
                st.metric("Range", f"{stats['rango']:.2f}")
                st.metric("Points", f"{stats['n_puntos']:,}")
            
            st.divider()
            
            # Anomalies display
            if 'mag_anomalias' in st.session_state:
                anom = st.session_state.mag_anomalias
                
                st.markdown("**Detected Anomalies:**")
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    st.metric("High", anom['n_anomalias_altas'], 
                             delta=f"+{anom['umbral_alto']:.1f} nT")
                with col_a2:
                    st.metric("Low", anom['n_anomalias_bajas'],
                             delta=f"{anom['umbral_bajo']:.1f} nT")
            
            st.divider()
            
            # Visualizations
            st.markdown("**Quick Plots:**")
            
            if st.button("📈 Plot Histogram"):
                fig, ax = plt.subplots(figsize=(6, 4))
                ax.hist(mag.campo_total[~np.isnan(mag.campo_total)], bins=50, 
                       color='steelblue', edgecolor='black', alpha=0.7)
                ax.set_xlabel('Magnetic Field (nT)')
                ax.set_ylabel('Frequency')
                ax.set_title('Magnetic Field Distribution')
                ax.grid(True, alpha=0.3)
                st.pyplot(fig)
            
            if mag.anomalia is not None and st.button("📊 Plot Residual"):
                fig, ax = plt.subplots(figsize=(6, 4))
                ax.plot(mag.anomalia, color='red', linewidth=0.5)
                ax.set_xlabel('Sample')
                ax.set_ylabel('Residual Anomaly (nT)')
                ax.set_title('Magnetic Residual Anomaly')
                ax.grid(True, alpha=0.3)
                st.pyplot(fig)
        
        else:
            st.info("⏳ Load magnetic data to see results")
    
    # Map visualization (if geometry available)
    if st.session_state.mag_data_loaded and st.session_state.mag is not None:
        st.divider()
        st.markdown("### 🗺️ Spatial Visualization")
        
        mag = st.session_state.mag
        
        # Check if we have coordinate columns
        lat_col = lon_col = None
        for col in ['lat', 'latitude', 'LAT', 'LATITUDE', 'y', 'Y']:
            if col in mag.datos.columns:
                lat_col = col
                break
        for col in ['lon', 'longitude', 'LON', 'LONGITUDE', 'x', 'X']:
            if col in mag.datos.columns:
                lon_col = col
                break
        
        if lat_col and lon_col:
            # Get bounds
            lat_min, lat_max = mag.datos[lat_col].min(), mag.datos[lat_col].max()
            lon_min, lon_max = mag.datos[lon_col].min(), mag.datos[lon_col].max()
            center_lat = (lat_min + lat_max) / 2
            center_lon = (lon_min + lon_max) / 2
            
            # Create map
            m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
            
            # Add data points colored by magnetic field
            campo_norm = (mag.campo_total - np.nanmin(mag.campo_total)) / (np.nanmax(mag.campo_total) - np.nanmin(mag.campo_total))
            
            for idx, row in mag.datos.iterrows():
                if idx >= 1000:  # Limit for performance
                    break
                
                color_val = campo_norm[idx]
                color = cm.get_cmap('RdYlBu_r')(color_val)
                color_hex = '#{:02x}{:02x}{:02x}'.format(int(color[0]*255), int(color[1]*255), int(color[2]*255))
                
                folium.CircleMarker(
                    location=[row[lat_col], row[lon_col]],
                    radius=3,
                    color=color_hex,
                    fill=True,
                    fillColor=color_hex,
                    fillOpacity=0.7,
                    popup=f"{mag.campo_total[idx]:.2f} nT"
                ).add_to(m)
            
            # Add basemaps
            folium.TileLayer('OpenStreetMap').add_to(m)
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='ESRI',
                name='Satellite'
            ).add_to(m)
            folium.LayerControl().add_to(m)
            
            st_folium(m, width=1200, height=500)
            
            st.caption("🔴 Red = High field | 🔵 Blue = Low field (showing first 1000 points)")
        else:
            st.info("⏳ No spatial data available for mapping")
    
    # Navigation
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ Back", use_container_width=True):
            st.session_state.workflow_step = 4
            st.rerun()
    with col3:
        if st.button("Next: Export ➡️", type="primary", use_container_width=True):
            st.session_state.workflow_step = 6
            st.rerun()

# ============================================================================
# MÓDULO 6: EXPORTACIÓN
# ============================================================================
elif current_step == 6:
    st.markdown("## 📤 Step 6: Export Results")
    st.markdown("Download and share your analysis results")
    
    if 'pr' not in st.session_state or st.session_state.pr is None:
        st.warning("⚠️ No analysis results available. Complete Step 3 first.")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📦 Export Options")
            
            # Format selection
            export_format = st.multiselect(
                "Select export formats",
                ["GeoTIFF", "Shapefile", "GeoJSON", "PDF Report", "JSON Metadata", "PNG Images"],
                default=["PDF Report"]
            )
            
            # Resolution
            if "GeoTIFF" in export_format:
                st.selectbox("GeoTIFF Resolution", ["Original", "30m", "60m", "120m"])
            
            # Metadata
            st.markdown("### 📝 Metadata")
            author = st.text_input("Author", value="")
            description = st.text_area("Description", value="")
            
            # Export button
            if st.button("📥 Export Selected Formats", type="primary", use_container_width=True):
                st.success("✅ Export initiated")
                st.info("🚧 Full export functionality will be implemented soon")
        
        with col2:
            st.markdown("### 📋 Export Manifest")
            st.json({
                "project": st.session_state.project_name,
                "date": datetime.now().isoformat(),
                "formats": export_format if export_format else [],
                "aoi": "defined" if st.session_state.aoi_defined else "undefined"
            })
    
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ Back", use_container_width=True):
            st.session_state.workflow_step = 5
            st.rerun()
    with col3:
        if st.button("View History ➡️", type="primary", use_container_width=True):
            st.session_state.workflow_step = 7
            st.rerun()

# ============================================================================
# MÓDULO 7: HISTORIAL
# ============================================================================
elif current_step == 7:
    st.markdown("## 📁 Step 7: Project History")
    st.markdown("Manage and reopen previous analysis sessions")
    
    # Current project info
    st.markdown("### 📊 Current Session")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Project", st.session_state.project_name)
    with col2:
        st.metric("AOI", "✅" if st.session_state.aoi_defined else "❌")
    with col3:
        st.metric("Data", "✅" if st.session_state.data_acquired else "❌")
    with col4:
        st.metric("Analysis", "✅" if st.session_state.indices_calculated else "❌")
    
    st.divider()
    
    # Save current project
    if st.button("💾 Save Current Project"):
        project_data = {
            "name": st.session_state.project_name,
            "date": datetime.now().isoformat(),
            "aoi_defined": st.session_state.aoi_defined,
            "data_acquired": st.session_state.data_acquired,
            "indices_calculated": st.session_state.indices_calculated,
        }
        st.session_state.projects_history.append(project_data)
        st.success(f"✅ Project '{st.session_state.project_name}' saved!")
    
    st.divider()
    
    # Project history table
    st.markdown("### 🗂️ Previous Projects")
    
    if st.session_state.projects_history:
        df = pd.DataFrame(st.session_state.projects_history)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("📭 No previous projects saved")
    
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ Back", use_container_width=True):
            st.session_state.workflow_step = 6
            st.rerun()
    with col3:
        if st.button("🏠 Start New Project", type="primary", use_container_width=True):
            st.session_state.workflow_step = 1
            st.session_state.project_name = f"TERRAF_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            st.rerun()
