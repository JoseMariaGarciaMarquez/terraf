"""
FASE 1: CARACTERIZACIÓN ESPECTRAL DE MINAS
==========================================

Extrae la "firma espectral" de las 4 minas usando índices Landsat.
Este es el único dato que SÍ cubre las zonas mineras.

Objetivo:
- Calcular GOSSAN, FMI, FeO, CMR, NDII, AI en radio de 500m de cada mina
- Estadísticas: media, std, percentiles (p25, p50, p75, p90)
- Verificar consistencia entre las 4 minas
- Definir firma espectral promedio (ground truth)

Salidas:
- minas_firma_espectral.json: Estadísticas por mina
- minas_firma_promedio.json: Firma target
- minas_indices_distribucion.png: Histogramas comparativos
- minas_indices_boxplot.png: Comparación entre minas
- minas_valores_extraidos.csv: Todos los píxeles extraídos
"""

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Agregar path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from terraf_pr import TerrafPR

# Para KMZ
import zipfile
try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

# Para transformación de coordenadas
from pyproj import Transformer

print("=" * 80)
print("🎯 FASE 1: CARACTERIZACIÓN ESPECTRAL DE MINAS")
print("=" * 80)
print()

# ============================================================================
# 1. CARGAR UBICACIONES DE MINAS DESDE JSON
# ============================================================================

print("📍 Cargando ubicaciones de minas desde JSON...")

minas_json_path = Path("resultados/minas_caracterizacion.json")
if not minas_json_path.exists():
    print(f"❌ No se encontró {minas_json_path}")
    sys.exit(1)

# Cargar JSON con info de minas
with open(minas_json_path, 'r') as f:
    minas = json.load(f)

# Convertir listas a tuplas donde sea necesario
for nombre, info in minas.items():
    if 'centroide_utm' in info and isinstance(info['centroide_utm'], list):
        info['centroide_utm'] = tuple(info['centroide_utm'])
    
    # Reconstruir centroide_wgs84 desde UTM si no existe
    if 'centroide_wgs84' not in info and 'centroide_utm' in info:
        transformer_utm_wgs84 = Transformer.from_crs("EPSG:32613", "EPSG:4326", always_xy=True)
        x, y = info['centroide_utm']
        lon, lat = transformer_utm_wgs84.transform(x, y)
        info['centroide_wgs84'] = (lon, lat)

for nombre, info in minas.items():
    x, y = info['centroide_utm']
    if 'centroide_wgs84' in info:
        lon, lat = info['centroide_wgs84']
        print(f"   {nombre}: {lat:.6f}°N, {lon:.6f}°W → UTM: {x:.1f}, {y:.1f}")
    else:
        print(f"   {nombre}: UTM: {x:.1f}, {y:.1f}")

if len(minas) == 0:
    print("❌ No se encontraron minas en el KMZ")
    sys.exit(1)

print(f"\n✅ {len(minas)} minas cargadas")
print()

# ============================================================================
# 2. CARGAR ESCENA LANDSAT QUE CUBRA LAS MINAS
# ============================================================================

print("🛰️  Buscando escena Landsat que cubra las minas...")

# Calcular centroide promedio de las minas
lons_minas = []
lats_minas = []
for info in minas.values():
    if 'centroide_wgs84' in info:
        lon, lat = info['centroide_wgs84']
        lons_minas.append(lon)
        lats_minas.append(lat)

centro_minas_lon = np.mean(lons_minas)
centro_minas_lat = np.mean(lats_minas)

print(f"   Centro minas: {centro_minas_lat:.4f}°N, {centro_minas_lon:.4f}°W")

# Buscar escenas en múltiples ubicaciones
landsat_dirs = [
    Path("datos/landsat9/coleccion-2"),
    Path("datos/landsat9/coleccion-1"),
    Path("datos/landsat9"),
    Path("datos/downloaded")
]

escenas_disponibles = []

for landsat_dir in landsat_dirs:
    if not landsat_dir.exists():
        continue
    
    for item in landsat_dir.rglob("*"):
        if item.is_dir():
            # Buscar archivos Level-2 (SR) o Level-1
            tif_sr = list(item.glob("*_SR_B*.TIF"))
            tif_l1 = list(item.glob("*_B[1-7].TIF"))
            
            if len(tif_sr) > 0 or len(tif_l1) > 0:
                escenas_disponibles.append(item)

if len(escenas_disponibles) == 0:
    print("❌ No se encontraron escenas Landsat")
    print("Asegúrate de tener datos en:")
    print("  - datos/landsat9/coleccion-2/")
    print("  - datos/landsat9/coleccion-1/")
    sys.exit(1)

print(f"   Escenas encontradas: {len(escenas_disponibles)}")

# Probar cada escena hasta encontrar una que cubra las minas
escena_path = None
pr = None

for candidata in escenas_disponibles:
    print(f"\n   Probando: {candidata.name}...")
    
    try:
        pr_temp = TerrafPR(str(candidata))
        pr_temp.cargar_bandas(reducir=True, factor=4)
        
        # Verificar si cubre las minas
        transform = pr_temp.metadatos['transform']
        width = pr_temp.metadatos['width']
        height = pr_temp.metadatos['height']
        
        # Obtener bounds
        minx = transform.c
        maxy = transform.f
        maxx = minx + (width * transform.a)
        miny = maxy + (height * transform.e)
        
        # Transformar a lat/lon si es necesario
        crs_string = str(pr_temp.metadatos['crs'])
        if 'EPSG:4326' not in crs_string:
            transformer_to_wgs84 = Transformer.from_crs("EPSG:32613", "EPSG:4326", always_xy=True)
            lon_sw, lat_sw = transformer_to_wgs84.transform(minx, miny)
            lon_ne, lat_ne = transformer_to_wgs84.transform(maxx, maxy)
        else:
            lon_sw, lat_sw = minx, miny
            lon_ne, lat_ne = maxx, maxy
        
        # Verificar si centro de minas está dentro
        cubre = (lon_sw <= centro_minas_lon <= lon_ne and 
                lat_sw <= centro_minas_lat <= lat_ne)
        
        print(f"      Bounds: Lat [{lat_sw:.4f}, {lat_ne:.4f}], Lon [{lon_sw:.4f}, {lon_ne:.4f}]")
        
        if cubre:
            print(f"      ✅ Cubre las minas!")
            escena_path = candidata
            pr = pr_temp
            break
        else:
            print(f"      ❌ No cubre las minas")
            
    except Exception as e:
        print(f"      ⚠️  Error al cargar: {str(e)[:100]}")
        continue

if pr is None or escena_path is None:
    print("\n❌ No se encontró ninguna escena que cubra las minas")
    print(f"   Las minas están en: {centro_minas_lat:.4f}°N, {centro_minas_lon:.4f}°W")
    sys.exit(1)

print(f"\n✅ Escena seleccionada: {escena_path.name}")
print(f"   Bandas cargadas: {list(pr.bandas.keys())[:7]}")
print(f"   Dimensiones: {pr.bandas['B4'].shape if 'B4' in pr.bandas else pr.bandas['B04'].shape}")
print()

# ============================================================================
# 3. CALCULAR ÍNDICES ESPECTRALES
# ============================================================================

print("🔬 Calculando índices espectrales...")

indices = {}

# Detectar nombres de bandas (pueden ser B2 o B02)
def get_band(pr, num):
    """Obtiene banda sea que esté como B2 o B02"""
    for key in [f'B{num}', f'B0{num}', f'B{num:02d}']:
        if key in pr.bandas:
            return pr.bandas[key]
    raise KeyError(f"No se encontró banda {num}")

# GOSSAN (B4/B2) - Óxidos de hierro
print("   Calculando GOSSAN (B4/B2)...")
b2 = get_band(pr, 2)
b4 = get_band(pr, 4)
indices['GOSSAN'] = np.where(b2 > 0, b4 / b2, np.nan)
print(f"      Range: {np.nanmin(indices['GOSSAN']):.3f} - {np.nanmax(indices['GOSSAN']):.3f}")

# FMI (B6/B5) - Minerales ferrosos
print("   Calculando FMI (B6/B5)...")
b5 = get_band(pr, 5)
b6 = get_band(pr, 6)
indices['FMI'] = np.where(b5 > 0, b6 / b5, np.nan)
print(f"      Range: {np.nanmin(indices['FMI']):.3f} - {np.nanmax(indices['FMI']):.3f}")

# FeO (B4/B5) - Óxidos férricos
print("   Calculando FeO (B4/B5)...")
indices['FeO'] = np.where(b5 > 0, b4 / b5, np.nan)
print(f"      Range: {np.nanmin(indices['FeO']):.3f} - {np.nanmax(indices['FeO']):.3f}")

# CMR (B6/B7) - Alteración arcillosa
print("   Calculando CMR (B6/B7)...")
b7 = get_band(pr, 7)
indices['CMR'] = np.where(b7 > 0, b6 / b7, np.nan)
print(f"      Range: {np.nanmin(indices['CMR']):.3f} - {np.nanmax(indices['CMR']):.3f}")

# NDII (B4-B2)/(B4+B2) - Índice normalizado de hierro
print("   Calculando NDII...")
denominador = b4 + b2
indices['NDII'] = np.where(denominador > 0, (b4 - b2) / denominador, np.nan)
print(f"      Range: {np.nanmin(indices['NDII']):.3f} - {np.nanmax(indices['NDII']):.3f}")

# AI (B6+B7)/B5 - Alteración hidrotermal
print("   Calculando AI...")
indices['AI'] = np.where(b5 > 0, (b6 + b7) / b5, np.nan)
print(f"      Range: {np.nanmin(indices['AI']):.3f} - {np.nanmax(indices['AI']):.3f}")

print(f"\n✅ {len(indices)} índices calculados")
print()

# ============================================================================
# 4. EXTRAER VALORES EN MINAS (RADIO 500M)
# ============================================================================

print("📊 Extrayendo valores en zonas mineras...")

# Obtener transform de la imagen
transform = pr.metadatos['transform']
width = pr.metadatos['width']
height = pr.metadatos['height']

print(f"   Transform: pixel_size={transform.a:.2f}m")
print(f"   Radio búsqueda: 500m")
print()

# Calcular radio en píxeles
radio_metros = 500
radio_pixeles = int(radio_metros / abs(transform.a))
print(f"   Radio en píxeles: {radio_pixeles}")
print()

# Extraer valores para cada mina
valores_extraidos = {nombre: {idx: [] for idx in indices.keys()} for nombre in minas.keys()}

for nombre_mina, info_mina in minas.items():
    print(f"🏭 {nombre_mina}:")
    
    # Centroide en UTM
    centroide_x, centroide_y = info_mina['centroide_utm']
    
    # Convertir a coordenadas de píxel
    # x = transform.c + col * transform.a
    # y = transform.f + row * transform.e
    col = int((centroide_x - transform.c) / transform.a)
    row = int((centroide_y - transform.f) / transform.e)
    
    print(f"   Píxel central: col={col}, row={row}")
    
    # Verificar que esté dentro de la imagen
    if col < 0 or col >= width or row < 0 or row >= height:
        print(f"   ⚠️  Mina fuera de la imagen")
        continue
    
    # Extraer ventana circular
    n_pixeles_extraidos = 0
    
    for idx_name, idx_data in indices.items():
        valores_idx = []
        
        for dr in range(-radio_pixeles, radio_pixeles + 1):
            for dc in range(-radio_pixeles, radio_pixeles + 1):
                # Verificar que esté dentro del radio circular
                distancia_pixeles = np.sqrt(dr**2 + dc**2)
                if distancia_pixeles > radio_pixeles:
                    continue
                
                r = row + dr
                c = col + dc
                
                # Verificar límites
                if r < 0 or r >= height or c < 0 or c >= width:
                    continue
                
                # Extraer valor
                valor = idx_data[r, c]
                
                if not np.isnan(valor) and not np.isinf(valor):
                    valores_idx.append(valor)
        
        valores_extraidos[nombre_mina][idx_name] = valores_idx
        
        if idx_name == 'GOSSAN':  # Contar solo una vez
            n_pixeles_extraidos = len(valores_idx)
    
    print(f"   Píxeles extraídos: {n_pixeles_extraidos}")
    print()

# ============================================================================
# 5. CALCULAR ESTADÍSTICAS POR MINA
# ============================================================================

print("=" * 80)
print("📊 ESTADÍSTICAS POR MINA")
print("=" * 80)
print()

estadisticas_minas = {}

for nombre_mina in minas.keys():
    print(f"🏭 {nombre_mina}:")
    print()
    
    stats_mina = {}
    
    for idx_name in indices.keys():
        valores = valores_extraidos[nombre_mina][idx_name]
        
        if len(valores) == 0:
            print(f"   {idx_name}: Sin datos")
            continue
        
        valores_array = np.array(valores)
        
        stats_idx = {
            'mean': float(np.mean(valores_array)),
            'std': float(np.std(valores_array)),
            'median': float(np.median(valores_array)),
            'p25': float(np.percentile(valores_array, 25)),
            'p75': float(np.percentile(valores_array, 75)),
            'p90': float(np.percentile(valores_array, 90)),
            'min': float(np.min(valores_array)),
            'max': float(np.max(valores_array)),
            'n_pixels': len(valores_array)
        }
        
        stats_mina[idx_name] = stats_idx
        
        print(f"   {idx_name:8s}: {stats_idx['mean']:.4f} ± {stats_idx['std']:.4f} "
              f"(med={stats_idx['median']:.4f}, n={stats_idx['n_pixels']})")
    
    estadisticas_minas[nombre_mina] = stats_mina
    print()

# ============================================================================
# 6. CALCULAR FIRMA ESPECTRAL PROMEDIO (TODAS LAS MINAS)
# ============================================================================

print("=" * 80)
print("🎯 FIRMA ESPECTRAL PROMEDIO DE TODAS LAS MINAS")
print("=" * 80)
print()

firma_promedio = {}

for idx_name in indices.keys():
    # Combinar valores de todas las minas
    valores_todas = []
    for nombre_mina in minas.keys():
        valores_todas.extend(valores_extraidos[nombre_mina][idx_name])
    
    if len(valores_todas) == 0:
        print(f"   {idx_name}: Sin datos")
        continue
    
    valores_array = np.array(valores_todas)
    
    firma_idx = {
        'mean': float(np.mean(valores_array)),
        'std': float(np.std(valores_array)),
        'median': float(np.median(valores_array)),
        'p25': float(np.percentile(valores_array, 25)),
        'p75': float(np.percentile(valores_array, 75)),
        'p90': float(np.percentile(valores_array, 90)),
        'min': float(np.min(valores_array)),
        'max': float(np.max(valores_array)),
        'n_pixels_total': len(valores_array),
        'n_minas': len(minas)
    }
    
    firma_promedio[idx_name] = firma_idx
    
    print(f"   {idx_name:8s}: {firma_idx['mean']:.4f} ± {firma_idx['std']:.4f} "
          f"(med={firma_idx['median']:.4f}, p90={firma_idx['p90']:.4f})")
    print(f"               Range: [{firma_idx['min']:.4f}, {firma_idx['max']:.4f}]")
    print(f"               Total píxeles: {firma_idx['n_pixels_total']} ({len(minas)} minas)")
    print()

# ============================================================================
# 7. ANÁLISIS DE CONSISTENCIA ENTRE MINAS
# ============================================================================

print("=" * 80)
print("🔍 ANÁLISIS DE CONSISTENCIA ENTRE MINAS")
print("=" * 80)
print()

consistencia = {}

for idx_name in indices.keys():
    # Obtener medias de cada mina
    medias_minas = []
    for nombre_mina in minas.keys():
        if idx_name in estadisticas_minas[nombre_mina]:
            medias_minas.append(estadisticas_minas[nombre_mina][idx_name]['mean'])
    
    if len(medias_minas) < 2:
        continue
    
    medias_array = np.array(medias_minas)
    
    # Coeficiente de variación (CV = std/mean)
    cv = np.std(medias_array) / np.mean(medias_array) * 100 if np.mean(medias_array) != 0 else 0
    
    consistencia[idx_name] = {
        'cv_percent': float(cv),
        'interpretacion': 'ALTA' if cv < 15 else ('MEDIA' if cv < 30 else 'BAJA')
    }
    
    emoji = '✅' if cv < 15 else ('⚠️' if cv < 30 else '❌')
    print(f"   {idx_name:8s}: CV = {cv:5.1f}% {emoji} ({consistencia[idx_name]['interpretacion']})")

print()
print("💡 Interpretación CV:")
print("   CV < 15%: Alta consistencia (las minas tienen valores similares)")
print("   CV 15-30%: Consistencia media")
print("   CV > 30%: Baja consistencia (valores muy variables entre minas)")
print()

# ============================================================================
# 8. GUARDAR RESULTADOS JSON
# ============================================================================

print("💾 Guardando resultados...")

resultados_dir = Path("resultados/fase1_caracterizacion")
resultados_dir.mkdir(parents=True, exist_ok=True)

# Guardar estadísticas por mina
with open(resultados_dir / "minas_firma_espectral.json", 'w') as f:
    json.dump(estadisticas_minas, f, indent=2)
print(f"   ✅ {resultados_dir / 'minas_firma_espectral.json'}")

# Guardar firma promedio
with open(resultados_dir / "minas_firma_promedio.json", 'w') as f:
    json.dump(firma_promedio, f, indent=2)
print(f"   ✅ {resultados_dir / 'minas_firma_promedio.json'}")

# Guardar consistencia
with open(resultados_dir / "minas_consistencia.json", 'w') as f:
    json.dump(consistencia, f, indent=2)
print(f"   ✅ {resultados_dir / 'minas_consistencia.json'}")

# ============================================================================
# 9. GUARDAR CSV CON TODOS LOS VALORES EXTRAÍDOS
# ============================================================================

print("\n📊 Generando CSV con valores extraídos...")

# Crear DataFrame largo con todos los valores
registros = []
for nombre_mina in minas.keys():
    for idx_name in indices.keys():
        for valor in valores_extraidos[nombre_mina][idx_name]:
            registros.append({
                'mina': nombre_mina,
                'indice': idx_name,
                'valor': valor
            })

df_valores = pd.DataFrame(registros)
df_valores.to_csv(resultados_dir / "minas_valores_extraidos.csv", index=False)
print(f"   ✅ {resultados_dir / 'minas_valores_extraidos.csv'}")
print(f"   Total registros: {len(df_valores):,}")
print()

# ============================================================================
# 10. VISUALIZACIÓN: HISTOGRAMAS COMPARATIVOS
# ============================================================================

print("📈 Generando visualizaciones...")

# Figura con 6 subplots (uno por índice)
fig, axes = plt.subplots(2, 3, figsize=(18, 12))
axes = axes.flatten()

colores_minas = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']

for i, idx_name in enumerate(indices.keys()):
    ax = axes[i]
    
    # Histogramas por mina
    for j, nombre_mina in enumerate(minas.keys()):
        valores = valores_extraidos[nombre_mina][idx_name]
        if len(valores) > 0:
            ax.hist(valores, bins=30, alpha=0.6, label=nombre_mina, 
                   color=colores_minas[j], edgecolor='black', linewidth=0.5)
    
    # Línea vertical en la media global
    if idx_name in firma_promedio:
        media_global = firma_promedio[idx_name]['mean']
        ax.axvline(media_global, color='red', linestyle='--', linewidth=2, 
                  label=f'Media global: {media_global:.3f}')
    
    ax.set_title(f'{idx_name} - Distribución por Mina', fontsize=14, fontweight='bold')
    ax.set_xlabel('Valor', fontsize=12)
    ax.set_ylabel('Frecuencia', fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(resultados_dir / "minas_indices_distribucion.png", dpi=150, bbox_inches='tight')
print(f"   ✅ {resultados_dir / 'minas_indices_distribucion.png'}")
plt.close()

# ============================================================================
# 11. VISUALIZACIÓN: BOXPLOTS COMPARATIVOS
# ============================================================================

fig, axes = plt.subplots(2, 3, figsize=(18, 12))
axes = axes.flatten()

for i, idx_name in enumerate(indices.keys()):
    ax = axes[i]
    
    # Preparar datos para boxplot
    datos_boxplot = []
    etiquetas = []
    
    for nombre_mina in minas.keys():
        valores = valores_extraidos[nombre_mina][idx_name]
        if len(valores) > 0:
            datos_boxplot.append(valores)
            etiquetas.append(nombre_mina)
    
    if len(datos_boxplot) > 0:
        bp = ax.boxplot(datos_boxplot, labels=etiquetas, patch_artist=True,
                       showmeans=True, meanline=True)
        
        # Colorear cajas
        for patch, color in zip(bp['boxes'], colores_minas[:len(datos_boxplot)]):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        # Línea horizontal en la media global
        if idx_name in firma_promedio:
            media_global = firma_promedio[idx_name]['mean']
            ax.axhline(media_global, color='red', linestyle='--', linewidth=2,
                      label=f'Media global: {media_global:.3f}')
    
    ax.set_title(f'{idx_name} - Comparación entre Minas', fontsize=14, fontweight='bold')
    ax.set_ylabel('Valor', fontsize=12)
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend(fontsize=10)
    
    # Rotar etiquetas si son largas
    ax.tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig(resultados_dir / "minas_indices_boxplot.png", dpi=150, bbox_inches='tight')
print(f"   ✅ {resultados_dir / 'minas_indices_boxplot.png'}")
plt.close()

# ============================================================================
# 12. VISUALIZACIÓN: HEATMAP DE CONSISTENCIA
# ============================================================================

# Crear matriz de medias: minas × índices
matriz_medias = []
nombres_minas_ordenados = sorted(minas.keys())
indices_ordenados = sorted(indices.keys())

for nombre_mina in nombres_minas_ordenados:
    fila = []
    for idx_name in indices_ordenados:
        if idx_name in estadisticas_minas[nombre_mina]:
            fila.append(estadisticas_minas[nombre_mina][idx_name]['mean'])
        else:
            fila.append(np.nan)
    matriz_medias.append(fila)

matriz_medias = np.array(matriz_medias)

# Normalizar por columna (Z-score) para comparar patrones
matriz_norm = np.zeros_like(matriz_medias)
for j in range(matriz_medias.shape[1]):
    col = matriz_medias[:, j]
    if not np.all(np.isnan(col)):
        mean_col = np.nanmean(col)
        std_col = np.nanstd(col)
        if std_col > 0:
            matriz_norm[:, j] = (col - mean_col) / std_col
        else:
            matriz_norm[:, j] = 0

fig, ax = plt.subplots(figsize=(10, 6))
im = ax.imshow(matriz_norm, cmap='RdYlGn', aspect='auto', vmin=-2, vmax=2)

# Etiquetas
ax.set_xticks(np.arange(len(indices_ordenados)))
ax.set_yticks(np.arange(len(nombres_minas_ordenados)))
ax.set_xticklabels(indices_ordenados, fontsize=12)
ax.set_yticklabels(nombres_minas_ordenados, fontsize=12)

# Rotar etiquetas X
plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

# Valores en celdas
for i in range(len(nombres_minas_ordenados)):
    for j in range(len(indices_ordenados)):
        valor_orig = matriz_medias[i, j]
        valor_norm = matriz_norm[i, j]
        if not np.isnan(valor_orig):
            color = 'white' if abs(valor_norm) > 1 else 'black'
            ax.text(j, i, f'{valor_orig:.3f}', ha="center", va="center", 
                   color=color, fontsize=10, fontweight='bold')

ax.set_title('Firma Espectral por Mina (Z-score normalizado)', 
            fontsize=14, fontweight='bold', pad=20)
ax.set_xlabel('Índice Espectral', fontsize=12, fontweight='bold')
ax.set_ylabel('Mina', fontsize=12, fontweight='bold')

# Colorbar
cbar = plt.colorbar(im, ax=ax)
cbar.set_label('Desviación de la media (σ)', fontsize=11)

plt.tight_layout()
plt.savefig(resultados_dir / "minas_firma_heatmap.png", dpi=150, bbox_inches='tight')
print(f"   ✅ {resultados_dir / 'minas_firma_heatmap.png'}")
plt.close()

print()

# ============================================================================
# RESUMEN FINAL
# ============================================================================

print("=" * 80)
print("✅ FASE 1 COMPLETADA")
print("=" * 80)
print()

print("📊 RESUMEN:")
print(f"   Minas analizadas: {len(minas)}")
print(f"   Índices calculados: {len(indices)}")
print(f"   Total píxeles extraídos: {len(df_valores):,}")
print()

print("📁 ARCHIVOS GENERADOS:")
print(f"   {resultados_dir / 'minas_firma_espectral.json'}")
print(f"   {resultados_dir / 'minas_firma_promedio.json'}")
print(f"   {resultados_dir / 'minas_consistencia.json'}")
print(f"   {resultados_dir / 'minas_valores_extraidos.csv'}")
print(f"   {resultados_dir / 'minas_indices_distribucion.png'}")
print(f"   {resultados_dir / 'minas_indices_boxplot.png'}")
print(f"   {resultados_dir / 'minas_firma_heatmap.png'}")
print()

print("🎯 ÍNDICES MÁS CONSISTENTES:")
consistencia_ordenada = sorted(consistencia.items(), key=lambda x: x[1]['cv_percent'])
for idx_name, info in consistencia_ordenada[:3]:
    print(f"   1. {idx_name}: CV = {info['cv_percent']:.1f}% ({info['interpretacion']})")
print()

print("💡 PRÓXIMO PASO:")
print("   Ejecutar Fase 2 para validar estos índices con magnetometría y geoquímica")
print()
