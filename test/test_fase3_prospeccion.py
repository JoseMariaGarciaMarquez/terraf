"""
FASE 3: PROSPECCIÓN POR SIMILITUD MULTI-CRITERIO
================================================

Calcula prospectividad basada en similitud espectral con las minas.
Usa los mejores indicadores identificados en Fase 2.

Objetivo:
- Calcular score de similitud espectral (CMR + GOSSAN + FeO)
- Integrar con magnetometría (peso bajo)
- Identificar targets por similitud con minas
- Generar mapa de prospectividad integrado
- Ranking de targets por distancia a minas + scores

Salidas:
- mapa_similitud_espectral.png: Heatmap de similitud
- mapa_prospectividad_integrada.png: Prospectividad final
- targets_similitud.csv: Lista de targets
- targets_similitud.geojson: Para visualización
"""

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
from scipy.interpolate import Rbf
from scipy.ndimage import gaussian_filter, label
from scipy.stats import percentileofscore
import warnings
warnings.filterwarnings('ignore')

# Agregar path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from terraf_pr import TerrafPR

# Para transformación de coordenadas
from pyproj import Transformer

print("=" * 80)
print("🎯 FASE 3: PROSPECCIÓN POR SIMILITUD MULTI-CRITERIO")
print("=" * 80)
print()

# ============================================================================
# 1. CARGAR RESULTADOS DE FASES ANTERIORES
# ============================================================================

print("📊 Cargando resultados de fases anteriores...")

# Firma espectral promedio
with open("resultados/fase1_caracterizacion/minas_firma_promedio.json", 'r') as f:
    firma_promedio = json.load(f)

# Ranking de indicadores
df_ranking = pd.read_csv("resultados/fase2_integracion/ranking_indicadores.csv")

# Minas
with open("resultados/minas_caracterizacion.json", 'r') as f:
    minas = json.load(f)
    for info in minas.values():
        if isinstance(info.get('centroide_utm'), list):
            info['centroide_utm'] = tuple(info['centroide_utm'])

print(f"   ✅ Firma espectral: {len(firma_promedio)} índices")
print(f"   ✅ Ranking: {len(df_ranking)} indicadores")
print(f"   ✅ Minas: {len(minas)}")
print()

# ============================================================================
# 2. CARGAR ESCENA LANDSAT Y CALCULAR ÍNDICES
# ============================================================================

print("🛰️  Cargando escena Landsat...")

escena_path = Path("datos/landsat9/coleccion-2/LC09_L2SP_031043_20251124_20251126_02_T1")
if not escena_path.exists():
    print("❌ No se encontró la escena")
    sys.exit(1)

pr = TerrafPR(str(escena_path))
pr.cargar_bandas(reducir=True, factor=4)

print(f"   ✅ Escena cargada: {escena_path.name}")
print(f"   Dimensiones: {pr.bandas['B4'].shape if 'B4' in pr.bandas else pr.bandas['B04'].shape}")
print()

# Función helper
def get_band(pr, num):
    for key in [f'B{num}', f'B0{num}', f'B{num:02d}']:
        if key in pr.bandas:
            return pr.bandas[key]
    raise KeyError(f"No se encontró banda {num}")

# Calcular índices
print("🔬 Calculando índices espectrales en región completa...")

b2 = get_band(pr, 2)
b4 = get_band(pr, 4)
b5 = get_band(pr, 5)
b6 = get_band(pr, 6)
b7 = get_band(pr, 7)

indices = {}
indices['GOSSAN'] = np.where(b2 > 0, b4 / b2, np.nan)
indices['FMI'] = np.where(b5 > 0, b6 / b5, np.nan)
indices['FeO'] = np.where(b5 > 0, b4 / b5, np.nan)
indices['CMR'] = np.where(b7 > 0, b6 / b7, np.nan)
indices['NDII'] = np.where((b4 + b2) > 0, (b4 - b2) / (b4 + b2), np.nan)
indices['AI'] = np.where(b5 > 0, (b6 + b7) / b5, np.nan)

print(f"   ✅ {len(indices)} índices calculados")
print()

# ============================================================================
# 3. CALCULAR SCORE DE SIMILITUD ESPECTRAL
# ============================================================================

print("=" * 80)
print("📊 CALCULANDO SIMILITUD ESPECTRAL")
print("=" * 80)
print()

# Usar top 3 indicadores según Fase 2
# CMR (score 0.861), GOSSAN (0.802), FeO (0.791)

# Pesos basados en scores normalizados
indices_principales = ['CMR', 'GOSSAN', 'FeO']
scores_principales = [0.861, 0.802, 0.791]
pesos_norm = np.array(scores_principales) / np.sum(scores_principales)

print(f"📊 ÍNDICES SELECCIONADOS:")
for idx, peso in zip(indices_principales, pesos_norm):
    print(f"   {idx:8s}: {peso*100:.1f}%")
print()

# Calcular similitud para cada índice
similitudes = {}

for idx_name in indices_principales:
    print(f"   Calculando similitud {idx_name}...")
    
    # Valor target (de las minas)
    target_mean = firma_promedio[idx_name]['mean']
    target_std = firma_promedio[idx_name]['std']
    
    # Datos de la región
    datos_region = indices[idx_name]
    
    # Calcular Z-score (distancia normalizada al target)
    z_score = np.abs(datos_region - target_mean) / target_std
    
    # Convertir a similitud (gaussiana: 1.0 si igual, 0.0 si muy diferente)
    # exp(-z²/2) da valores entre 0 y 1
    similitud = np.exp(-z_score**2 / 2)
    
    similitudes[idx_name] = similitud
    
    # Estadísticas
    valores_validos = similitud[~np.isnan(similitud)]
    print(f"      Range: {np.min(valores_validos):.3f} - {np.max(valores_validos):.3f}")
    print(f"      Mean: {np.mean(valores_validos):.3f}")

print()

# Combinar similitudes con pesos
print("🎯 Combinando similitudes con pesos...")

similitud_espectral = np.zeros_like(indices['CMR'])

for idx_name, peso in zip(indices_principales, pesos_norm):
    similitud_espectral += peso * similitudes[idx_name]

# Normalizar a 0-1
similitud_espectral = np.nan_to_num(similitud_espectral, nan=0.0)

print(f"   ✅ Similitud espectral calculada")
print(f"   Range: {np.min(similitud_espectral):.3f} - {np.max(similitud_espectral):.3f}")
print(f"   Mean: {np.mean(similitud_espectral):.3f}")
print()

# ============================================================================
# 4. INTEGRAR CON MAGNETOMETRÍA (PESO BAJO)
# ============================================================================

print("=" * 80)
print("🧲 INTEGRANDO MAGNETOMETRÍA")
print("=" * 80)
print()

# Cargar datos de magnetometría
mag_file = Path("resultados/magnetometria_combinada.csv")

if mag_file.exists():
    df_mag = pd.read_csv(mag_file)
    
    print(f"   {len(df_mag):,} puntos de magnetometría")
    
    # Submuestrear datos para evitar memory error
    # Con 6000+ puntos, RBF es demasiado costoso en memoria
    # Usar submuestreo cada 4 puntos
    df_mag_sub = df_mag.iloc[::4].copy()
    print(f"   Submuestreando a {len(df_mag_sub):,} puntos...")
    
    # Obtener transform de imagen
    transform = pr.metadatos['transform']
    height, width = similitud_espectral.shape
    
    minx = transform.c
    maxy = transform.f
    maxx = minx + (width * transform.a)
    miny = maxy + (height * transform.e)
    
    # Crear grid más pequeño (100x100) para interpolar
    print("   Interpolando a grid 100x100...")
    
    grid_x, grid_y = np.mgrid[minx:maxx:100j, miny:maxy:100j]
    
    valores = df_mag_sub['valor_norm'].values if 'valor_norm' in df_mag_sub.columns else df_mag_sub['valor'].values
    mask_valid = ~np.isnan(valores)
    
    # Usar RBF con datos submuestreados
    rbf_mag = Rbf(df_mag_sub['x'].values[mask_valid], 
                  df_mag_sub['y'].values[mask_valid], 
                  valores[mask_valid],
                  function='multiquadric', smooth=2.0)  # Smooth mayor para datos submuestreados
    
    grid_mag_small = rbf_mag(grid_x, grid_y)
    
    # Redimensionar a tamaño de imagen Landsat
    from scipy.ndimage import zoom
    factor_y = height / 100
    factor_x = width / 100
    grid_mag = zoom(grid_mag_small, (factor_y, factor_x), order=1)
    
    # Normalizar a 0-1
    grid_mag_norm = (grid_mag - np.min(grid_mag)) / (np.max(grid_mag) - np.min(grid_mag))
    
    print(f"   ✅ Magnetometría interpolada a {height}x{width}")
    print(f"   Range: {np.min(grid_mag_norm):.3f} - {np.max(grid_mag_norm):.3f}")
    
    tiene_magnetometria = True
else:
    print("   ⚠️  Sin datos de magnetometría")
    grid_mag_norm = np.zeros_like(similitud_espectral)
    tiene_magnetometria = False

print()

# ============================================================================
# 5. CALCULAR PROSPECTIVIDAD INTEGRADA
# ============================================================================

print("=" * 80)
print("🎯 CALCULANDO PROSPECTIVIDAD INTEGRADA")
print("=" * 80)
print()

# Pesos basados en resultados de Fase 2
# Magnetometría tiene bajo poder discriminatorio (percentil 38%)
if tiene_magnetometria:
    peso_espectral = 0.90  # 90% a índices espectrales
    peso_magnetico = 0.10  # 10% a magnetometría
else:
    peso_espectral = 1.0
    peso_magnetico = 0.0

print(f"⚖️  PESOS:")
print(f"   Similitud espectral: {peso_espectral*100:.0f}%")
print(f"   Magnetometría: {peso_magnetico*100:.0f}%")
print()

# Calcular prospectividad
prospectividad = (peso_espectral * similitud_espectral + 
                 peso_magnetico * grid_mag_norm)

# Aplicar suavizado gaussiano para reducir ruido
print("   Aplicando suavizado gaussiano (sigma=2)...")
prospectividad = gaussian_filter(prospectividad, sigma=2)

# Normalizar
prospectividad = (prospectividad - np.min(prospectividad)) / (np.max(prospectividad) - np.min(prospectividad))

print(f"   ✅ Prospectividad calculada")
print(f"   Range: {np.min(prospectividad):.3f} - {np.max(prospectividad):.3f}")
print(f"   Mean: {np.mean(prospectividad):.3f}")
print()

# Clasificar prospectividad
p90 = np.percentile(prospectividad, 90)
p70 = np.percentile(prospectividad, 70)

clasificacion = np.zeros_like(prospectividad)
clasificacion[prospectividad >= p90] = 3  # MUY ALTA
clasificacion[(prospectividad >= p70) & (prospectividad < p90)] = 2  # ALTA
clasificacion[(prospectividad >= np.percentile(prospectividad, 50)) & (prospectividad < p70)] = 1  # MEDIA

print(f"   Umbral MUY ALTA (p90): {p90:.3f}")
print(f"   Umbral ALTA (p70): {p70:.3f}")
print(f"   Píxeles MUY ALTA: {np.sum(clasificacion == 3):,}")
print(f"   Píxeles ALTA: {np.sum(clasificacion == 2):,}")
print()

# ============================================================================
# 6. IDENTIFICACIÓN DE TARGETS
# ============================================================================

print("=" * 80)
print("🎯 IDENTIFICACIÓN DE TARGETS")
print("=" * 80)
print()

# Identificar regiones contiguas de MUY ALTA prospectividad
mask_muy_alta = clasificacion == 3
labeled_array, num_features = label(mask_muy_alta)

print(f"   Regiones MUY ALTA encontradas: {num_features}")
print()

# Analizar cada target
targets = []

transformer_utm_wgs84 = Transformer.from_crs("EPSG:32613", "EPSG:4326", always_xy=True)

for target_id in range(1, num_features + 1):
    mask = labeled_array == target_id
    
    # Tamaño del target
    n_pixeles = np.sum(mask)
    area_ha = n_pixeles * (transform.a * abs(transform.e)) / 10000  # hectáreas
    
    # Si muy pequeño, ignorar
    if area_ha < 50:  # Mínimo 50 ha
        continue
    
    # Centroide
    indices_y, indices_x = np.where(mask)
    centroid_y = int(np.mean(indices_y))
    centroid_x = int(np.mean(indices_x))
    
    # Coordenadas UTM del centroide
    utm_x = minx + (centroid_x * transform.a)
    utm_y = maxy + (centroid_y * transform.e)
    
    # Convertir a WGS84
    lon, lat = transformer_utm_wgs84.transform(utm_x, utm_y)
    
    # Prospectividad promedio y máxima
    prosp_promedio = np.mean(prospectividad[mask])
    prosp_maxima = np.max(prospectividad[mask])
    
    # Similitud espectral promedio
    simil_promedio = np.mean(similitud_espectral[mask])
    
    # Distancia a mina más cercana
    dist_minas = []
    for nombre_mina, info_mina in minas.items():
        mina_x, mina_y = info_mina['centroide_utm']
        dist = np.sqrt((utm_x - mina_x)**2 + (utm_y - mina_y)**2) / 1000  # km
        dist_minas.append((dist, nombre_mina))
    
    dist_minas.sort(key=lambda x: x[0])
    dist_cercana, mina_cercana = dist_minas[0]
    
    targets.append({
        'id': target_id,
        'lat': lat,
        'lon': lon,
        'utm_x': utm_x,
        'utm_y': utm_y,
        'area_ha': area_ha,
        'n_pixeles': n_pixeles,
        'prospectividad_mean': prosp_promedio,
        'prospectividad_max': prosp_maxima,
        'similitud_espectral': simil_promedio,
        'dist_mina_cercana_km': dist_cercana,
        'mina_cercana': mina_cercana
    })

print(f"✅ {len(targets)} targets significativos identificados (>50 ha)")
print()

# Ordenar por prospectividad combinada con distancia
# Score = prospectividad * (1 - dist_normalizada/50)  # Penalizar >50km
for target in targets:
    dist_norm = min(target['dist_mina_cercana_km'], 50) / 50
    target['score_ranking'] = target['prospectividad_mean'] * (1 - 0.3 * dist_norm)

targets.sort(key=lambda x: x['score_ranking'], reverse=True)

# Mostrar top 10
print("🏆 TOP 10 TARGETS:")
print()

for i, target in enumerate(targets[:10], 1):
    print(f"   {i}. Target #{target['id']}")
    print(f"      📍 {target['lat']:.6f}°N, {target['lon']:.6f}°W")
    print(f"      📊 Prospectividad: {target['prospectividad_mean']:.3f} (max: {target['prospectividad_max']:.3f})")
    print(f"      🎯 Similitud espectral: {target['similitud_espectral']:.3f}")
    print(f"      📐 Área: {target['area_ha']:.1f} ha")
    print(f"      🏭 {target['mina_cercana']}: {target['dist_mina_cercana_km']:.2f} km")
    print(f"      ⭐ Score ranking: {target['score_ranking']:.3f}")
    print()

# ============================================================================
# 7. GUARDAR RESULTADOS
# ============================================================================

print("💾 Guardando resultados...")

resultados_dir = Path("resultados/fase3_prospeccion")
resultados_dir.mkdir(parents=True, exist_ok=True)

# CSV
df_targets = pd.DataFrame(targets)
df_targets.to_csv(resultados_dir / "targets_similitud.csv", index=False)
print(f"   ✅ {resultados_dir / 'targets_similitud.csv'}")

# GeoJSON para visualización
geojson = {
    'type': 'FeatureCollection',
    'features': []
}

for target in targets:
    feature = {
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [target['lon'], target['lat']]
        },
        'properties': {
            'id': int(target['id']),
            'prospectividad': float(target['prospectividad_mean']),
            'similitud': float(target['similitud_espectral']),
            'area_ha': float(target['area_ha']),
            'dist_mina_km': float(target['dist_mina_cercana_km']),
            'mina_cercana': target['mina_cercana'],
            'score': float(target['score_ranking'])
        }
    }
    geojson['features'].append(feature)

with open(resultados_dir / "targets_similitud.geojson", 'w') as f:
    json.dump(geojson, f, indent=2)
print(f"   ✅ {resultados_dir / 'targets_similitud.geojson'}")

# ============================================================================
# 8. VISUALIZACIONES
# ============================================================================

print("\n📊 Generando visualizaciones...")

# Transformar bounds a lat/lon para plotting
lon_sw, lat_sw = transformer_utm_wgs84.transform(minx, miny)
lon_ne, lat_ne = transformer_utm_wgs84.transform(maxx, maxy)
extent = [lon_sw, lon_ne, lat_sw, lat_ne]

# 8.1 Mapa de similitud espectral
fig, ax = plt.subplots(figsize=(14, 12))

im = ax.imshow(similitud_espectral, cmap='YlOrRd', aspect='auto', 
               extent=extent, origin='upper', vmin=0, vmax=1)

# Minas
for nombre, info in minas.items():
    if 'centroide_wgs84' in info:
        lon_m, lat_m = info['centroide_wgs84']
        ax.plot(lon_m, lat_m, marker='*', markersize=20, color='blue', 
               markeredgecolor='white', markeredgewidth=2, label=nombre if nombre == list(minas.keys())[0] else "")

# Targets
for i, target in enumerate(targets[:5], 1):
    ax.plot(target['lon'], target['lat'], marker='o', markersize=12, 
           color='cyan', markeredgecolor='black', markeredgewidth=2)
    ax.text(target['lon'], target['lat'], f"{i}", fontsize=10, 
           fontweight='bold', ha='center', va='center')

ax.set_title('Similitud Espectral con Minas (CMR + GOSSAN + FeO)', 
            fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel('Longitud', fontsize=12)
ax.set_ylabel('Latitud', fontsize=12)
ax.legend(loc='upper left', fontsize=10)
ax.grid(True, alpha=0.3)

cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label('Similitud (0-1)', fontsize=12)

plt.tight_layout()
plt.savefig(resultados_dir / "mapa_similitud_espectral.png", dpi=150, bbox_inches='tight')
print(f"   ✅ {resultados_dir / 'mapa_similitud_espectral.png'}")
plt.close()

# 8.2 Mapa de prospectividad integrada
fig, ax = plt.subplots(figsize=(14, 12))

im = ax.imshow(prospectividad, cmap='hot_r', aspect='auto', 
               extent=extent, origin='upper', vmin=0, vmax=1)

# Minas
for nombre, info in minas.items():
    if 'centroide_wgs84' in info:
        lon_m, lat_m = info['centroide_wgs84']
        ax.plot(lon_m, lat_m, marker='*', markersize=20, color='cyan', 
               markeredgecolor='black', markeredgewidth=2)

# Targets top 10
for i, target in enumerate(targets[:10], 1):
    color = 'lime' if i <= 3 else 'yellow'
    ax.plot(target['lon'], target['lat'], marker='o', markersize=14, 
           color=color, markeredgecolor='black', markeredgewidth=2)
    ax.text(target['lon'], target['lat'], f"{i}", fontsize=9, 
           fontweight='bold', ha='center', va='center', color='black')

ax.set_title(f'Prospectividad Integrada ({peso_espectral*100:.0f}% Espectral + {peso_magnetico*100:.0f}% Mag)', 
            fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel('Longitud', fontsize=12)
ax.set_ylabel('Latitud', fontsize=12)
ax.grid(True, alpha=0.3)

cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label('Prospectividad (0-1)', fontsize=12)

# Leyenda
from matplotlib.patches import Patch
legend_elements = [
    plt.Line2D([0], [0], marker='*', color='w', markerfacecolor='cyan', 
               markeredgecolor='black', markersize=15, label='Minas'),
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='lime', 
               markeredgecolor='black', markersize=12, label='Top 3 Targets'),
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='yellow', 
               markeredgecolor='black', markersize=12, label='Targets 4-10')
]
ax.legend(handles=legend_elements, loc='upper left', fontsize=10)

plt.tight_layout()
plt.savefig(resultados_dir / "mapa_prospectividad_integrada.png", dpi=150, bbox_inches='tight')
print(f"   ✅ {resultados_dir / 'mapa_prospectividad_integrada.png'}")
plt.close()

# 8.3 Panel de 4 visualizaciones
fig, axes = plt.subplots(2, 2, figsize=(18, 16))

# Panel 1: CMR
im1 = axes[0, 0].imshow(indices['CMR'], cmap='RdYlBu_r', aspect='auto', 
                        extent=extent, origin='upper')
axes[0, 0].set_title('CMR (B6/B7) - Alteración Arcillosa', fontsize=14, fontweight='bold')
plt.colorbar(im1, ax=axes[0, 0], fraction=0.046)

# Panel 2: GOSSAN
im2 = axes[0, 1].imshow(indices['GOSSAN'], cmap='YlOrRd', aspect='auto', 
                        extent=extent, origin='upper')
axes[0, 1].set_title('GOSSAN (B4/B2) - Óxidos Fe', fontsize=14, fontweight='bold')
plt.colorbar(im2, ax=axes[0, 1], fraction=0.046)

# Panel 3: Similitud Espectral
im3 = axes[1, 0].imshow(similitud_espectral, cmap='YlGn', aspect='auto', 
                        extent=extent, origin='upper', vmin=0, vmax=1)
axes[1, 0].set_title('Similitud Espectral', fontsize=14, fontweight='bold')
plt.colorbar(im3, ax=axes[1, 0], fraction=0.046)

# Panel 4: Prospectividad
im4 = axes[1, 1].imshow(prospectividad, cmap='hot_r', aspect='auto', 
                        extent=extent, origin='upper', vmin=0, vmax=1)
axes[1, 1].set_title('Prospectividad Integrada', fontsize=14, fontweight='bold')
plt.colorbar(im4, ax=axes[1, 1], fraction=0.046)

# Agregar minas a todos
for ax in axes.flatten():
    for nombre, info in minas.items():
        if 'centroide_wgs84' in info:
            lon_m, lat_m = info['centroide_wgs84']
            ax.plot(lon_m, lat_m, marker='*', markersize=15, color='cyan', 
                   markeredgecolor='black', markeredgewidth=1.5)
    ax.set_xlabel('Longitud', fontsize=10)
    ax.set_ylabel('Latitud', fontsize=10)
    ax.grid(True, alpha=0.3)

plt.suptitle('Análisis Multi-Índice - Prospección Mina Santa Rita', 
            fontsize=18, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig(resultados_dir / "panel_analisis_completo.png", dpi=150, bbox_inches='tight')
print(f"   ✅ {resultados_dir / 'panel_analisis_completo.png'}")
plt.close()

print()

# ============================================================================
# RESUMEN FINAL
# ============================================================================

print("=" * 80)
print("✅ FASE 3 COMPLETADA")
print("=" * 80)
print()

print("📊 RESUMEN:")
print(f"   Targets identificados: {len(targets)}")
print(f"   Top target: {targets[0]['dist_mina_cercana_km']:.2f} km de {targets[0]['mina_cercana']}")
print(f"   Prospectividad promedio targets: {np.mean([t['prospectividad_mean'] for t in targets]):.3f}")
print(f"   Área total targets: {sum([t['area_ha'] for t in targets]):.1f} ha")
print()

print("📁 ARCHIVOS GENERADOS:")
print(f"   {resultados_dir / 'targets_similitud.csv'}")
print(f"   {resultados_dir / 'targets_similitud.geojson'}")
print(f"   {resultados_dir / 'mapa_similitud_espectral.png'}")
print(f"   {resultados_dir / 'mapa_prospectividad_integrada.png'}")
print(f"   {resultados_dir / 'panel_analisis_completo.png'}")
print()

print("🏆 TOP 3 TARGETS PARA EXPLORACIÓN:")
for i, target in enumerate(targets[:3], 1):
    print(f"   {i}. Target #{target['id']}: {target['lat']:.6f}°N, {target['lon']:.6f}°W")
    print(f"      Distancia: {target['dist_mina_cercana_km']:.2f} km de {target['mina_cercana']}")
    print(f"      Prospectividad: {target['prospectividad_mean']:.3f}, Área: {target['area_ha']:.0f} ha")
print()

print("💡 PRÓXIMO PASO:")
print("   Ejecutar Fase 4 para generar mapa interactivo y fichas de targets")
print()
