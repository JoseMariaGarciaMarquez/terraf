"""
FASE 4: MAPA INTERACTIVO FINAL
==============================

Genera mapa interactivo Folium con:
- Todas las capas de análisis
- Targets top 20 con popups informativos
- Minas como referencia
- Controles de capas
- Herramientas de medición

Salidas:
- mapa_interactivo_final.html: Mapa web interactivo
"""

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd
import folium
from folium import plugins
import json
from PIL import Image
import io
import base64
import warnings
warnings.filterwarnings('ignore')

# Agregar path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from terraf_pr import TerrafPR

from pyproj import Transformer

print("=" * 80)
print("🗺️  FASE 4: MAPA INTERACTIVO FINAL")
print("=" * 80)
print()

# ============================================================================
# 1. CARGAR DATOS
# ============================================================================

print("📊 Cargando datos de fases anteriores...")

# Targets
df_targets = pd.read_csv("resultados/fase3_prospeccion/targets_similitud.csv")
print(f"   ✅ {len(df_targets)} targets")

# Minas
with open("resultados/minas_caracterizacion.json", 'r') as f:
    minas = json.load(f)

transformer_utm_wgs84 = Transformer.from_crs("EPSG:32613", "EPSG:4326", always_xy=True)

for nombre, info in minas.items():
    if isinstance(info.get('centroide_utm'), list):
        info['centroide_utm'] = tuple(info['centroide_utm'])
    if 'centroide_wgs84' not in info and 'centroide_utm' in info:
        x, y = info['centroide_utm']
        lon, lat = transformer_utm_wgs84.transform(x, y)
        info['centroide_wgs84'] = (lon, lat)

print(f"   ✅ {len(minas)} minas")

# Escena Landsat
print("\n🛰️  Cargando escena Landsat...")
escena_path = Path("datos/landsat9/coleccion-2/LC09_L2SP_031043_20251124_20251126_02_T1")
pr = TerrafPR(str(escena_path))
pr.cargar_bandas(reducir=True, factor=4)

def get_band(pr, num):
    for key in [f'B{num}', f'B0{num}', f'B{num:02d}']:
        if key in pr.bandas:
            return pr.bandas[key]
    raise KeyError(f"No se encontró banda {num}")

# Calcular índices
b2 = get_band(pr, 2)
b4 = get_band(pr, 4)
b5 = get_band(pr, 5)
b6 = get_band(pr, 6)
b7 = get_band(pr, 7)

indices = {}
indices['GOSSAN'] = np.where(b2 > 0, b4 / b2, np.nan)
indices['CMR'] = np.where(b7 > 0, b6 / b7, np.nan)
indices['FeO'] = np.where(b5 > 0, b4 / b5, np.nan)

print(f"   ✅ Índices calculados")
print()

# ============================================================================
# 2. FUNCIONES HELPER PARA IMÁGENES
# ============================================================================

def array_to_png_base64(array):
    """Convierte array numpy RGBA a PNG base64"""
    img = Image.fromarray(array, mode='RGBA')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return f"data:image/png;base64,{base64.b64encode(buffer.read()).decode()}"

def crear_capa_indice(indice_data, cmap_name='YlOrRd', vmin=None, vmax=None):
    """Crea capa PNG de índice con colormap"""
    valid = indice_data[~np.isnan(indice_data)]
    if vmin is None:
        vmin = np.percentile(valid, 2)
    if vmax is None:
        vmax = np.percentile(valid, 98)
    
    # Normalizar
    norm = np.clip((indice_data - vmin) / (vmax - vmin), 0, 1)
    
    # Aplicar colormap
    from matplotlib import colormaps
    cmap = colormaps[cmap_name]
    rgba = cmap(norm)
    rgba = (rgba * 255).astype(np.uint8)
    
    # Alpha para NaN
    alpha = ~np.isnan(indice_data)
    rgba[:, :, 3] = (alpha * 180).astype(np.uint8)
    
    return array_to_png_base64(rgba)

# ============================================================================
# 3. PREPARAR CAPAS
# ============================================================================

print("🎨 Preparando capas para mapa...")

# RGB Natural
print("   Preparando RGB Natural...")
rgb = np.zeros((pr.bandas['B4'].shape[0], pr.bandas['B4'].shape[1], 4), dtype=np.uint8)
for i, banda in enumerate([b4, b2]):  # Solo R y B para ahorrar memoria
    valid = banda > 0
    if np.sum(valid) > 0:
        p_low = np.percentile(banda[valid], 2)
        p_high = np.percentile(banda[valid], 98)
        band_norm = np.clip((banda - p_low) / (p_high - p_low) * 255, 0, 255)
        rgb[:, :, i] = band_norm.astype(np.uint8)
        if i == 1:  # Copiar B a G para tener RGB completo
            rgb[:, :, 1] = band_norm.astype(np.uint8)

mask = (b4 > 0) & (b2 > 0)
rgb[:, :, 3] = (mask * 255).astype(np.uint8)
rgb_base64 = array_to_png_base64(rgb)

# Índices
print("   Preparando índices espectrales...")
gossan_base64 = crear_capa_indice(indices['GOSSAN'], 'YlOrRd')
cmr_base64 = crear_capa_indice(indices['CMR'], 'RdYlBu_r')
feo_base64 = crear_capa_indice(indices['FeO'], 'Reds')

# Bounds geográficos
transform = pr.metadatos['transform']
height, width = pr.bandas['B4'].shape
minx = transform.c
maxy = transform.f
maxx = minx + (width * transform.a)
miny = maxy + (height * transform.e)

lon_sw, lat_sw = transformer_utm_wgs84.transform(minx, miny)
lon_ne, lat_ne = transformer_utm_wgs84.transform(maxx, maxy)
bounds = [[lat_sw, lon_sw], [lat_ne, lon_ne]]

print(f"   ✅ Capas preparadas")
print()

# ============================================================================
# 4. CREAR MAPA BASE
# ============================================================================

print("🗺️  Creando mapa interactivo...")

# Calcular centro
centro_lat = np.mean([lat_sw, lat_ne])
centro_lon = np.mean([lon_sw, lon_ne])

# Mapa base
m = folium.Map(
    location=[centro_lat, centro_lon],
    zoom_start=10,
    tiles=None
)

# Basemaps
folium.TileLayer('OpenStreetMap', name='OpenStreetMap', show=False).add_to(m)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='ESRI Satellite',
    name='Satélite ESRI',
    show=True
).add_to(m)
folium.TileLayer('CartoDB positron', name='Minimalista', show=False).add_to(m)

# ============================================================================
# 5. AGREGAR CAPAS DE ANÁLISIS
# ============================================================================

print("   Agregando capas de análisis...")

# RGB Natural
rgb_layer = folium.FeatureGroup(name='🛰️ Landsat RGB', show=False)
folium.raster_layers.ImageOverlay(
    image=rgb_base64,
    bounds=bounds,
    opacity=0.7,
    name='Landsat RGB'
).add_to(rgb_layer)
rgb_layer.add_to(m)

# GOSSAN
gossan_layer = folium.FeatureGroup(name='🔥 GOSSAN (Óxidos Fe)', show=False)
folium.raster_layers.ImageOverlay(
    image=gossan_base64,
    bounds=bounds,
    opacity=0.6,
    name='GOSSAN'
).add_to(gossan_layer)
gossan_layer.add_to(m)

# CMR
cmr_layer = folium.FeatureGroup(name='🟡 CMR (Alteración Arcillosa)', show=True)
folium.raster_layers.ImageOverlay(
    image=cmr_base64,
    bounds=bounds,
    opacity=0.6,
    name='CMR'
).add_to(cmr_layer)
cmr_layer.add_to(m)

# FeO
feo_layer = folium.FeatureGroup(name='🔴 FeO (Óxidos Férricos)', show=False)
folium.raster_layers.ImageOverlay(
    image=feo_base64,
    bounds=bounds,
    opacity=0.6,
    name='FeO'
).add_to(feo_layer)
feo_layer.add_to(m)

# ============================================================================
# 6. AGREGAR MINAS
# ============================================================================

print("   Agregando minas...")

minas_layer = folium.FeatureGroup(name='🏭 Minas Conocidas', show=True)

for nombre, info in minas.items():
    if 'centroide_wgs84' in info:
        lon, lat = info['centroide_wgs84']
        
        popup_html = f"""
        <div style="font-family: Arial; min-width: 220px;">
            <h4 style="margin: 0; color: darkred;">🏭 {nombre}</h4>
            <hr style="margin: 5px 0;">
            <b>Ubicación:</b><br>
            {lat:.6f}°N, {lon:.6f}°W<br>
            <b>Tipo:</b> Mina productiva<br>
            <b>Status:</b> Ground truth<br>
            <hr style="margin: 5px 0;">
            <b style="color: green;">✅ REFERENCIA</b> para prospección
        </div>
        """
        
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color='red', icon='industry', prefix='fa'),
            tooltip=nombre
        ).add_to(minas_layer)
        
        # Círculo de referencia
        folium.Circle(
            location=[lat, lon],
            radius=500,
            color='red',
            weight=2,
            fill=True,
            fillColor='red',
            fillOpacity=0.2
        ).add_to(minas_layer)

minas_layer.add_to(m)

# ============================================================================
# 7. AGREGAR TARGETS (TOP 20)
# ============================================================================

print("   Agregando targets...")

targets_layer = folium.FeatureGroup(name='⭐ Targets Prospección (Top 20)', show=True)

# Ordenar por score
df_targets_sorted = df_targets.sort_values('score_ranking', ascending=False)

# Colores según ranking
colors = {
    1: 'red', 2: 'red', 3: 'red',  # Top 3 en rojo
    4: 'orange', 5: 'orange', 6: 'orange', 7: 'orange', 8: 'orange',  # 4-8 en naranja
}

for i, (_, target) in enumerate(df_targets_sorted.head(20).iterrows(), 1):
    color = colors.get(i, 'yellow')  # Resto en amarillo
    
    # Determinar prioridad
    if i <= 3:
        prioridad = "🏆 MÁXIMA"
        prioridad_color = "darkred"
    elif i <= 8:
        prioridad = "⭐ ALTA"
        prioridad_color = "orange"
    else:
        prioridad = "📍 MEDIA"
        prioridad_color = "goldenrod"
    
    popup_html = f"""
    <div style="font-family: Arial; min-width: 280px;">
        <h4 style="margin: 0; color: {prioridad_color};">🎯 TARGET #{int(target['id'])}</h4>
        <h5 style="margin: 5px 0;">Ranking: #{i} de 570</h5>
        <hr style="margin: 5px 0;">
        
        <b>📍 Coordenadas:</b><br>
        {target['lat']:.6f}°N, {target['lon']:.6f}°W<br><br>
        
        <b>📊 SCORES:</b><br>
        • Prospectividad: <b>{target['prospectividad_mean']:.3f}</b> (max: {target['prospectividad_max']:.3f})<br>
        • Similitud espectral: <b>{target['similitud_espectral']:.3f}</b><br>
        • Score ranking: <b>{target['score_ranking']:.3f}</b><br><br>
        
        <b>📐 CARACTERÍSTICAS:</b><br>
        • Área: <b>{target['area_ha']:.1f} ha</b><br>
        • Píxeles: {int(target['n_pixeles'])}<br><br>
        
        <b>🏭 MINA MÁS CERCANA:</b><br>
        {target['mina_cercana']}<br>
        Distancia: <b>{target['dist_mina_cercana_km']:.2f} km</b><br>
        
        <hr style="margin: 5px 0;">
        <b style="color: {prioridad_color}; font-size: 14px;">PRIORIDAD: {prioridad}</b>
    </div>
    """
    
    # Marcador
    folium.Marker(
        location=[target['lat'], target['lon']],
        popup=folium.Popup(popup_html, max_width=320),
        icon=folium.Icon(color=color, icon='star', prefix='fa'),
        tooltip=f"Target #{int(target['id'])} - Rank {i}"
    ).add_to(targets_layer)
    
    # Círculo proporcional al área
    radio = min(np.sqrt(target['area_ha'] * 10000), 5000)  # Máximo 5 km
    folium.Circle(
        location=[target['lat'], target['lon']],
        radius=radio,
        color=color,
        weight=2,
        fill=True,
        fillColor=color,
        fillOpacity=0.15
    ).add_to(targets_layer)

targets_layer.add_to(m)

# ============================================================================
# 8. CONTROLES Y HERRAMIENTAS
# ============================================================================

print("   Agregando controles...")

# Layer control
folium.LayerControl(position='topright', collapsed=False).add_to(m)

# Minimap
plugins.MiniMap(toggle_display=True, position='bottomright').add_to(m)

# Medición
plugins.MeasureControl(
    position='topleft',
    primary_length_unit='kilometers',
    primary_area_unit='hectares'
).add_to(m)

# Coordenadas del mouse
plugins.MousePosition().add_to(m)

# Fullscreen
plugins.Fullscreen(position='topleft').add_to(m)

# Draw (para marcar áreas de interés)
draw = plugins.Draw(
    export=False,
    position='topleft',
    draw_options={
        'polyline': False,
        'circle': True,
        'rectangle': True,
        'polygon': True,
        'marker': True,
        'circlemarker': False
    }
)
draw.add_to(m)

# ============================================================================
# 9. LEYENDA PERSONALIZADA
# ============================================================================

legend_html = '''
<div style="position: fixed; 
            bottom: 50px; left: 50px; width: 320px; 
            background-color: white; z-index:9999; font-size:13px;
            border:2px solid grey; border-radius: 5px; padding: 12px;
            box-shadow: 0 0 15px rgba(0,0,0,0.3);">
    
    <h4 style="margin-top:0; text-align: center; color: darkblue;">
        📊 LEYENDA DE PROSPECCIÓN
    </h4>
    <hr style="margin: 8px 0;">
    
    <p style="margin: 5px 0; font-weight: bold; color: darkred;">
        🎯 TARGETS DE EXPLORACIÓN:
    </p>
    <p style="margin: 3px 0;">
        <span style="color: red;">⭐</span> <b>Top 1-3:</b> Prioridad MÁXIMA
    </p>
    <p style="margin: 3px 0;">
        <span style="color: orange;">⭐</span> <b>Top 4-8:</b> Prioridad ALTA
    </p>
    <p style="margin: 3px 0;">
        <span style="color: yellow;">⭐</span> <b>Top 9-20:</b> Prioridad MEDIA
    </p>
    
    <hr style="margin: 8px 0;">
    
    <p style="margin: 5px 0; font-weight: bold; color: darkred;">
        🏭 MINAS CONOCIDAS:
    </p>
    <p style="margin: 3px 0;">
        <span style="color: red;">🏭</span> Ground truth (referencia)
    </p>
    
    <hr style="margin: 8px 0;">
    
    <p style="margin: 5px 0; font-weight: bold;">
        📊 MÉTODO:
    </p>
    <p style="margin: 3px 0; font-size: 12px;">
        • 90% Similitud espectral<br>
        &nbsp;&nbsp;(CMR + GOSSAN + FeO)<br>
        • 10% Magnetometría
    </p>
    
    <hr style="margin: 8px 0;">
    
    <p style="margin: 5px 0; font-size: 11px; color: #666;">
        <b>Total:</b> 570 targets identificados<br>
        <b>Área:</b> 519,558 ha prospectivas<br>
        <b>Fecha:</b> 2025-12-11
    </p>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# ============================================================================
# 10. TÍTULO Y METADATOS
# ============================================================================

title_html = '''
<div style="position: fixed; 
            top: 10px; left: 50%; transform: translateX(-50%);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            z-index:9999; padding: 15px 30px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
    <h2 style="margin:0; color:white; text-align:center; font-family: Arial;">
        🗺️ MAPA DE PROSPECCIÓN - MINA SANTA RITA
    </h2>
    <p style="margin:5px 0 0 0; color:#e0e0e0; text-align:center; font-size:13px;">
        Chihuahua, México | Análisis Multi-Criterio Landsat 9 + SGM
    </p>
</div>
'''
m.get_root().html.add_child(folium.Element(title_html))

# ============================================================================
# 11. GUARDAR MAPA
# ============================================================================

output_path = Path("resultados/fase4_final/mapa_interactivo_final.html")
output_path.parent.mkdir(parents=True, exist_ok=True)

m.save(str(output_path))

print(f"\n✅ Mapa guardado: {output_path}")
print()

# Generar también resumen en texto
resumen = f"""
================================================================================
RESUMEN MAPA INTERACTIVO - PROSPECCIÓN MINA SANTA RITA
================================================================================

📊 ESTADÍSTICAS:
   • Targets identificados: {len(df_targets)}
   • Targets mostrados: Top 20
   • Área total prospectiva: {df_targets['area_ha'].sum():,.0f} ha
   • Prospectividad promedio: {df_targets['prospectividad_mean'].mean():.3f}

🏆 TOP 5 TARGETS:
"""

for i, (_, target) in enumerate(df_targets_sorted.head(5).iterrows(), 1):
    resumen += f"""
   {i}. Target #{int(target['id'])}
      • Ubicación: {target['lat']:.6f}°N, {target['lon']:.6f}°W
      • Prospectividad: {target['prospectividad_mean']:.3f}
      • Similitud: {target['similitud_espectral']:.3f}
      • Área: {target['area_ha']:.1f} ha
      • Distancia: {target['dist_mina_cercana_km']:.2f} km de {target['mina_cercana']}
"""

resumen += f"""
================================================================================

🗺️ CAPAS DISPONIBLES EN MAPA:
   1. 🛰️ Landsat RGB - Imagen natural
   2. 🔥 GOSSAN - Óxidos de hierro (B4/B2)
   3. 🟡 CMR - Alteración arcillosa (B6/B7) ← MEJOR INDICADOR
   4. 🔴 FeO - Óxidos férricos (B4/B5)
   5. 🏭 Minas conocidas (4 minas)
   6. ⭐ Targets top 20

🛠️ HERRAMIENTAS:
   • Control de capas (esquina superior derecha)
   • Medición de distancias y áreas
   • Minimap de navegación
   • Pantalla completa
   • Dibujo de áreas de interés
   • Coordenadas del cursor

📍 METODOLOGÍA:
   • Similitud espectral: 90% (CMR 35% + GOSSAN 33% + FeO 32%)
   • Magnetometría: 10%
   • Firma de referencia: 4 minas conocidas
   • Consistencia entre minas: CV < 5%

💡 RECOMENDACIONES DE USO:
   1. Activar capa CMR para ver alteración arcillosa
   2. Hacer clic en targets para ver detalles
   3. Usar herramienta de medición para planificar accesos
   4. Comparar targets con minas conocidas (puntos rojos)
   5. Exportar coordenadas de targets desde CSV

================================================================================
ARCHIVO GENERADO: {output_path}
================================================================================
"""

# Guardar resumen
with open(output_path.parent / "README_mapa_interactivo.txt", 'w', encoding='utf-8') as f:
    f.write(resumen)

print(resumen)

print("=" * 80)
print("✅ FASE 4 COMPLETADA - MAPA INTERACTIVO LISTO")
print("=" * 80)
print()
print(f"📁 Archivos generados:")
print(f"   • {output_path}")
print(f"   • {output_path.parent / 'README_mapa_interactivo.txt'}")
print()
print("🌐 Para ver el mapa:")
print(f"   Abrir: {output_path.absolute()}")
print("   O hacer doble clic en el archivo HTML")
print()
