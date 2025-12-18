"""
FASE 2: INTEGRACIÓN MULTI-FUENTE
=================================

Valida los índices espectrales de Fase 1 con magnetometría y geoquímica.
Determina qué indicadores son más útiles para prospección.

Objetivo:
- Extraer magnetometría interpolada en ubicaciones de minas
- Analizar geoquímica en contexto regional (expandir radio a 2-3 km)
- Validar índices espectrales: ¿valores altos/bajos/medios comparado con región?
- Determinar mejores indicadores (ranking por consistencia + discriminación)

Salidas:
- minas_caracterizacion_completa.json: Todos los valores integrados
- minas_contexto_regional.png: Mapa con minas + datos cercanos
- minas_validacion_indices.csv: Tabla de validación
- mejor_indicador_analisis.txt: Recomendación
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
from scipy.stats import percentileofscore
import warnings
warnings.filterwarnings('ignore')

# Agregar path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from terraf_pr import TerrafPR

print("=" * 80)
print("🔬 FASE 2: INTEGRACIÓN MULTI-FUENTE")
print("=" * 80)
print()

# ============================================================================
# 1. CARGAR RESULTADOS DE FASE 1
# ============================================================================

print("📊 Cargando resultados de Fase 1...")

fase1_dir = Path("resultados/fase1_caracterizacion")

# Cargar firma espectral promedio
with open(fase1_dir / "minas_firma_promedio.json", 'r') as f:
    firma_promedio = json.load(f)

# Cargar estadísticas por mina
with open(fase1_dir / "minas_firma_espectral.json", 'r') as f:
    firma_minas = json.load(f)

print(f"   ✅ Firma espectral: {len(firma_promedio)} índices")
print(f"   ✅ Estadísticas: {len(firma_minas)} minas")
print()

# ============================================================================
# 2. CARGAR DATOS DE MAGNETOMETRÍA
# ============================================================================

print("🧲 Cargando datos de magnetometría...")

mag_file = Path("resultados/magnetometria_combinada.csv")
if not mag_file.exists():
    print(f"   ⚠️  No se encontró {mag_file}")
    print("   Continuando sin datos magnéticos...")
    df_mag = None
else:
    df_mag = pd.read_csv(mag_file)
    print(f"   ✅ {len(df_mag):,} puntos de magnetometría")
    print(f"   Range: {df_mag['valor'].min():.1f} - {df_mag['valor'].max():.1f}")
    
    # Estadísticas
    media_mag = df_mag['valor'].mean()
    std_mag = df_mag['valor'].std()
    print(f"   Media: {media_mag:.2f} ± {std_mag:.2f}")
    print()

# ============================================================================
# 3. CARGAR DATOS DE GEOQUÍMICA
# ============================================================================

print("🧪 Cargando datos de geoquímica...")

geo_file = Path("resultados/geoquimica_combinada.csv")
if not geo_file.exists():
    print(f"   ⚠️  No se encontró {geo_file}")
    print("   Continuando sin datos geoquímicos...")
    df_geo = None
else:
    df_geo = pd.read_csv(geo_file)
    print(f"   ✅ {len(df_geo):,} muestras geoquímicas")
    
    # Elementos disponibles
    elementos = [col for col in df_geo.columns if col not in ['x', 'y', 'zona', 'mag_interpolada']]
    print(f"   Elementos: {', '.join(elementos[:10])}")
    print()

# ============================================================================
# 4. CARGAR UBICACIONES DE MINAS
# ============================================================================

print("📍 Cargando ubicaciones de minas...")

with open("resultados/minas_caracterizacion.json", 'r') as f:
    minas = json.load(f)

for nombre, info in minas.items():
    if isinstance(info.get('centroide_utm'), list):
        info['centroide_utm'] = tuple(info['centroide_utm'])

print(f"   ✅ {len(minas)} minas cargadas")
print()

# ============================================================================
# 5. INTERPOLACIÓN RBF DE MAGNETOMETRÍA
# ============================================================================

caracterizacion_completa = {}

if df_mag is not None:
    print("=" * 80)
    print("🧲 MAGNETOMETRÍA EN ZONAS MINERAS")
    print("=" * 80)
    print()
    
    print("🔧 Interpolando magnetometría con RBF...")
    
    # Usar valor normalizado si existe, sino valor original
    if 'valor_norm' in df_mag.columns:
        valores = df_mag['valor_norm'].values
        print("   Usando valores normalizados por zona (Z-score)")
    else:
        valores = df_mag['valor'].values
        print("   Usando valores originales")
    
    # Crear interpolador RBF
    points_x = df_mag['x'].values
    points_y = df_mag['y'].values
    
    # Filtrar NaN
    mask_valid = ~np.isnan(valores)
    points_x = points_x[mask_valid]
    points_y = points_y[mask_valid]
    valores = valores[mask_valid]
    
    rbf_mag = Rbf(points_x, points_y, valores, function='multiquadric', smooth=1.0)
    print(f"   ✅ Interpolador RBF creado ({len(valores):,} puntos)")
    print()
    
    # Extraer valores en minas
    for nombre_mina, info_mina in minas.items():
        print(f"🏭 {nombre_mina}:")
        
        centroide_x, centroide_y = info_mina['centroide_utm']
        
        # Interpolar magnetometría en centroide
        mag_interpolada = float(rbf_mag(centroide_x, centroide_y))
        
        # Calcular desviación estándar (anomalía)
        anomalia_sigma = (mag_interpolada - np.mean(valores)) / np.std(valores)
        
        # Percentil en distribución regional
        percentil = percentileofscore(valores, mag_interpolada)
        
        caracterizacion_completa[nombre_mina] = {
            'ubicacion': {
                'utm_x': centroide_x,
                'utm_y': centroide_y
            },
            'magnetometria': {
                'valor_interpolado': mag_interpolada,
                'anomalia_sigma': anomalia_sigma,
                'percentil': percentil,
                'interpretacion': 'ALTA' if percentil > 75 else ('BAJA' if percentil < 25 else 'MEDIA')
            }
        }
        
        emoji = '🔴' if percentil > 75 else ('🔵' if percentil < 25 else '⚪')
        print(f"   Mag interpolada: {mag_interpolada:.3f}")
        print(f"   Anomalía: {anomalia_sigma:+.2f}σ {emoji}")
        print(f"   Percentil: {percentil:.1f}% ({caracterizacion_completa[nombre_mina]['magnetometria']['interpretacion']})")
        print()
else:
    print("⚠️  Sin datos de magnetometría, saltando análisis magnético")
    print()
    for nombre_mina in minas.keys():
        caracterizacion_completa[nombre_mina] = {
            'ubicacion': {
                'utm_x': minas[nombre_mina]['centroide_utm'][0],
                'utm_y': minas[nombre_mina]['centroide_utm'][1]
            }
        }

# ============================================================================
# 6. CONTEXTO GEOQUÍMICO REGIONAL
# ============================================================================

if df_geo is not None:
    print("=" * 80)
    print("🧪 GEOQUÍMICA EN CONTEXTO REGIONAL")
    print("=" * 80)
    print()
    
    # Expandir radio de búsqueda (no hay datos <500m, probar 2-3 km)
    radios_busqueda = [500, 1000, 2000, 3000, 5000]  # metros
    
    for nombre_mina, info_mina in minas.items():
        print(f"🏭 {nombre_mina}:")
        
        centroide_x, centroide_y = info_mina['centroide_utm']
        
        # Calcular distancias a todas las muestras
        distancias = np.sqrt((df_geo['x'] - centroide_x)**2 + (df_geo['y'] - centroide_y)**2)
        
        # Probar diferentes radios
        muestras_encontradas = False
        
        for radio in radios_busqueda:
            mask = distancias <= radio
            n_muestras = mask.sum()
            
            if n_muestras > 0:
                print(f"   Radio {radio}m: {n_muestras} muestras")
                
                if not muestras_encontradas:
                    # Usar el primer radio con datos
                    muestras_cercanas = df_geo[mask]
                    
                    # Calcular estadísticas para elementos clave
                    elementos_clave = ['AU', 'AG', 'CU', 'FE', 'ZN', 'PB', 'MO']
                    
                    geoquimica_info = {
                        'radio_busqueda_m': radio,
                        'n_muestras': int(n_muestras),
                        'elementos': {}
                    }
                    
                    print(f"   Elementos clave:")
                    for elem in elementos_clave:
                        if elem in muestras_cercanas.columns:
                            valores_elem = muestras_cercanas[elem].dropna()
                            if len(valores_elem) > 0:
                                media = valores_elem.mean()
                                std = valores_elem.std()
                                mediana = valores_elem.median()
                                maximo = valores_elem.max()
                                
                                # Percentil en distribución regional
                                todos_valores = df_geo[elem].dropna()
                                percentil = percentileofscore(todos_valores, media)
                                
                                geoquimica_info['elementos'][elem] = {
                                    'mean': float(media),
                                    'std': float(std),
                                    'median': float(mediana),
                                    'max': float(maximo),
                                    'percentil': float(percentil),
                                    'n_muestras': int(len(valores_elem))
                                }
                                
                                emoji = '⭐' if percentil > 75 else ('🔻' if percentil < 25 else '➖')
                                print(f"      {elem:3s}: {media:8.2f} ± {std:6.2f} (p{percentil:.0f}%) {emoji}")
                    
                    caracterizacion_completa[nombre_mina]['geoquimica'] = geoquimica_info
                    muestras_encontradas = True
        
        if not muestras_encontradas:
            print(f"   ⚠️  Sin muestras geoquímicas en radio 5 km")
            caracterizacion_completa[nombre_mina]['geoquimica'] = {
                'radio_busqueda_m': None,
                'n_muestras': 0,
                'elementos': {}
            }
        
        print()
else:
    print("⚠️  Sin datos de geoquímica, saltando análisis geoquímico")
    print()

# ============================================================================
# 7. VALIDACIÓN DE ÍNDICES ESPECTRALES
# ============================================================================

print("=" * 80)
print("📡 VALIDACIÓN DE ÍNDICES ESPECTRALES")
print("=" * 80)
print()

print("🔍 Calculando percentiles regionales de índices...")
print()

# Cargar escena Landsat para calcular distribución regional
from pyproj import Transformer

# Buscar escena que usamos en Fase 1
landsat_dirs = [
    Path("datos/landsat9/coleccion-2"),
    Path("datos/landsat9/coleccion-1"),
]

pr = None
for landsat_dir in landsat_dirs:
    if landsat_dir.exists():
        escena_path = landsat_dir / "LC09_L2SP_031043_20251124_20251126_02_T1"
        if escena_path.exists():
            print(f"   Cargando escena: {escena_path.name}")
            pr = TerrafPR(str(escena_path))
            pr.cargar_bandas(reducir=True, factor=4)
            break

if pr is None:
    print("   ⚠️  No se pudo cargar escena Landsat")
    print("   Usando solo valores de minas...")
    validacion_indices = {}
else:
    print("   ✅ Escena cargada")
    print()
    
    # Calcular índices en toda la escena
    def get_band(pr, num):
        for key in [f'B{num}', f'B0{num}', f'B{num:02d}']:
            if key in pr.bandas:
                return pr.bandas[key]
        raise KeyError(f"No se encontró banda {num}")
    
    print("   Calculando índices en región completa...")
    
    b2 = get_band(pr, 2)
    b4 = get_band(pr, 4)
    b5 = get_band(pr, 5)
    b6 = get_band(pr, 6)
    b7 = get_band(pr, 7)
    
    indices_regional = {}
    indices_regional['GOSSAN'] = np.where(b2 > 0, b4 / b2, np.nan)
    indices_regional['FMI'] = np.where(b5 > 0, b6 / b5, np.nan)
    indices_regional['FeO'] = np.where(b5 > 0, b4 / b5, np.nan)
    indices_regional['CMR'] = np.where(b7 > 0, b6 / b7, np.nan)
    indices_regional['NDII'] = np.where((b4 + b2) > 0, (b4 - b2) / (b4 + b2), np.nan)
    indices_regional['AI'] = np.where(b5 > 0, (b6 + b7) / b5, np.nan)
    
    print("   ✅ Índices calculados")
    print()
    
    # Validar cada índice
    validacion_indices = {}
    
    for idx_name in firma_promedio.keys():
        print(f"📊 {idx_name}:")
        
        # Valor promedio en minas (de Fase 1)
        valor_minas = firma_promedio[idx_name]['mean']
        
        # Distribución regional
        valores_region = indices_regional[idx_name].flatten()
        valores_region = valores_region[~np.isnan(valores_region)]
        
        # Percentil de las minas en la región
        percentil = percentileofscore(valores_region, valor_minas)
        
        # Estadísticas regionales
        media_region = np.mean(valores_region)
        std_region = np.std(valores_region)
        p25_region = np.percentile(valores_region, 25)
        p75_region = np.percentile(valores_region, 75)
        
        # Clasificación
        if percentil > 90:
            clasificacion = 'MUY ALTO'
            emoji = '🔥'
            utilidad = 'EXCELENTE'
        elif percentil > 75:
            clasificacion = 'ALTO'
            emoji = '⭐'
            utilidad = 'BUENA'
        elif percentil > 60:
            clasificacion = 'MEDIO-ALTO'
            emoji = '✅'
            utilidad = 'MEDIA'
        elif percentil < 40:
            clasificacion = 'MEDIO-BAJO'
            emoji = '➖'
            utilidad = 'MEDIA'
        elif percentil < 25:
            clasificacion = 'BAJO'
            emoji = '🔻'
            utilidad = 'BUENA (inverso)'
        elif percentil < 10:
            clasificacion = 'MUY BAJO'
            emoji = '🔵'
            utilidad = 'EXCELENTE (inverso)'
        else:
            clasificacion = 'MEDIO'
            emoji = '⚪'
            utilidad = 'BAJA'
        
        validacion_indices[idx_name] = {
            'valor_minas': valor_minas,
            'media_region': media_region,
            'std_region': std_region,
            'p25_region': p25_region,
            'p75_region': p75_region,
            'percentil_minas': percentil,
            'clasificacion': clasificacion,
            'utilidad_prospeccion': utilidad
        }
        
        print(f"   Valor minas: {valor_minas:.4f}")
        print(f"   Region: {media_region:.4f} ± {std_region:.4f} (p25={p25_region:.4f}, p75={p75_region:.4f})")
        print(f"   Percentil minas: {percentil:.1f}% {emoji} ({clasificacion})")
        print(f"   Utilidad: {utilidad}")
        print()
    
    # Agregar validación a caracterización
    for nombre_mina in caracterizacion_completa.keys():
        caracterizacion_completa[nombre_mina]['indices_espectrales'] = {
            'firma': firma_minas[nombre_mina],
            'validacion': validacion_indices
        }

# ============================================================================
# 8. GUARDAR CARACTERIZACIÓN COMPLETA
# ============================================================================

print("💾 Guardando caracterización completa...")

resultados_dir = Path("resultados/fase2_integracion")
resultados_dir.mkdir(parents=True, exist_ok=True)

# Guardar JSON
with open(resultados_dir / "minas_caracterizacion_completa.json", 'w') as f:
    json.dump(caracterizacion_completa, f, indent=2)
print(f"   ✅ {resultados_dir / 'minas_caracterizacion_completa.json'}")

# Guardar validación de índices
with open(resultados_dir / "minas_validacion_indices.json", 'w') as f:
    json.dump(validacion_indices, f, indent=2)
print(f"   ✅ {resultados_dir / 'minas_validacion_indices.json'}")

# ============================================================================
# 9. TABLA CSV DE VALIDACIÓN
# ============================================================================

print("\n📊 Generando tabla CSV de validación...")

if validacion_indices:
    df_validacion = pd.DataFrame(validacion_indices).T
    df_validacion = df_validacion.round(4)
    df_validacion.to_csv(resultados_dir / "minas_validacion_indices.csv")
    print(f"   ✅ {resultados_dir / 'minas_validacion_indices.csv'}")

# ============================================================================
# 10. ANÁLISIS DE MEJOR INDICADOR
# ============================================================================

print("\n" + "=" * 80)
print("🏆 RANKING DE INDICADORES")
print("=" * 80)
print()

# Calcular score para cada indicador
scores = []

for idx_name, validacion in validacion_indices.items():
    # Consistencia entre minas (de Fase 1)
    with open(fase1_dir / "minas_consistencia.json", 'r') as f:
        consistencia = json.load(f)
    
    cv = consistencia.get(idx_name, {}).get('cv_percent', 100)
    
    # Score de consistencia (inverso del CV, normalizado)
    score_consistencia = max(0, (30 - cv) / 30)  # 0-1, mejor si CV bajo
    
    # Score de discriminación (qué tan lejos está del percentil 50)
    percentil = validacion['percentil_minas']
    score_discriminacion = abs(percentil - 50) / 50  # 0-1, mejor si lejos de 50%
    
    # Score combinado (70% consistencia + 30% discriminación)
    score_total = 0.7 * score_consistencia + 0.3 * score_discriminacion
    
    scores.append({
        'indice': idx_name,
        'cv': cv,
        'percentil': percentil,
        'clasificacion': validacion['clasificacion'],
        'score_consistencia': score_consistencia,
        'score_discriminacion': score_discriminacion,
        'score_total': score_total,
        'utilidad': validacion['utilidad_prospeccion']
    })

# Ordenar por score total
df_scores = pd.DataFrame(scores).sort_values('score_total', ascending=False)

print("📊 TABLA DE RANKING:")
print()
print(df_scores.to_string(index=False))
print()

# Guardar ranking
df_scores.to_csv(resultados_dir / "ranking_indicadores.csv", index=False)
print(f"✅ {resultados_dir / 'ranking_indicadores.csv'}")
print()

# ============================================================================
# 11. RECOMENDACIONES
# ============================================================================

print("=" * 80)
print("💡 RECOMENDACIONES PARA PROSPECCIÓN")
print("=" * 80)
print()

top_3 = df_scores.head(3)

recomendaciones = []
recomendaciones.append("ANÁLISIS DE MEJOR INDICADOR")
recomendaciones.append("=" * 80)
recomendaciones.append("")
recomendaciones.append("🏆 TOP 3 INDICADORES:")
recomendaciones.append("")

for i, row in top_3.iterrows():
    recomendaciones.append(f"{i+1}. {row['indice']}")
    recomendaciones.append(f"   Score: {row['score_total']:.3f}")
    recomendaciones.append(f"   Consistencia (CV): {row['cv']:.1f}%")
    recomendaciones.append(f"   Discriminación: {row['clasificacion']} (p{row['percentil']:.1f}%)")
    recomendaciones.append(f"   Utilidad: {row['utilidad']}")
    recomendaciones.append("")

recomendaciones.append("=" * 80)
recomendaciones.append("")
recomendaciones.append("📊 RESUMEN DE CARACTERIZACIÓN:")
recomendaciones.append("")

# Resumen de magnetometría
if df_mag is not None:
    valores_mag_minas = [c.get('magnetometria', {}).get('percentil', 50) 
                         for c in caracterizacion_completa.values() if 'magnetometria' in c]
    if valores_mag_minas:
        percentil_mag_promedio = np.mean(valores_mag_minas)
        if percentil_mag_promedio > 75:
            recomendaciones.append("🧲 MAGNETOMETRÍA: Minas en ANOMALÍAS POSITIVAS (>p75)")
            recomendaciones.append("   → Buscar zonas con alta susceptibilidad magnética")
        elif percentil_mag_promedio < 25:
            recomendaciones.append("🧲 MAGNETOMETRÍA: Minas en ANOMALÍAS NEGATIVAS (<p25)")
            recomendaciones.append("   → Buscar zonas con baja susceptibilidad magnética")
        else:
            recomendaciones.append("🧲 MAGNETOMETRÍA: Minas en rango MEDIO")
            recomendaciones.append("   → Magnetometría NO es buen discriminador")
        recomendaciones.append("")

# Resumen de geoquímica
if df_geo is not None:
    elementos_altos = []
    for nombre_mina, info in caracterizacion_completa.items():
        if 'geoquimica' in info:
            for elem, stats in info['geoquimica'].get('elementos', {}).items():
                if stats.get('percentil', 0) > 75:
                    elementos_altos.append(elem)
    
    if elementos_altos:
        elementos_unicos = list(set(elementos_altos))
        recomendaciones.append(f"🧪 GEOQUÍMICA: Elementos elevados cerca de minas:")
        recomendaciones.append(f"   {', '.join(elementos_unicos)}")
        recomendaciones.append("   → Usar como pathfinders en prospección")
        recomendaciones.append("")

recomendaciones.append("=" * 80)
recomendaciones.append("")
recomendaciones.append("🎯 ESTRATEGIA RECOMENDADA:")
recomendaciones.append("")
recomendaciones.append(f"1. Usar {top_3.iloc[0]['indice']} como indicador PRINCIPAL")
recomendaciones.append(f"   (Score: {top_3.iloc[0]['score_total']:.3f}, CV: {top_3.iloc[0]['cv']:.1f}%)")
recomendaciones.append("")
recomendaciones.append(f"2. Combinar con {top_3.iloc[1]['indice']} para validación cruzada")
recomendaciones.append(f"   (Score: {top_3.iloc[1]['score_total']:.3f}, CV: {top_3.iloc[1]['cv']:.1f}%)")
recomendaciones.append("")
recomendaciones.append("3. Pesos sugeridos para Fase 3:")

# Calcular pesos normalizados basados en scores
scores_top3 = top_3['score_total'].values
pesos_norm = scores_top3 / scores_top3.sum()

recomendaciones.append(f"   - Índices espectrales: {pesos_norm.sum() * 100:.0f}%")
if df_mag is not None and percentil_mag_promedio > 60 or percentil_mag_promedio < 40:
    recomendaciones.append(f"   - Magnetometría: 20%")
    recomendaciones.append(f"   - Geoquímica: {100 - pesos_norm.sum() * 100 - 20:.0f}%")
else:
    recomendaciones.append(f"   - Magnetometría: 10% (bajo poder discriminatorio)")
    recomendaciones.append(f"   - Geoquímica: {100 - pesos_norm.sum() * 100 - 10:.0f}%")

recomendaciones.append("")

# Guardar recomendaciones
with open(resultados_dir / "mejor_indicador_analisis.txt", 'w', encoding='utf-8') as f:
    f.write('\n'.join(recomendaciones))

print('\n'.join(recomendaciones))

print(f"\n✅ {resultados_dir / 'mejor_indicador_analisis.txt'}")
print()

# ============================================================================
# RESUMEN FINAL
# ============================================================================

print("=" * 80)
print("✅ FASE 2 COMPLETADA")
print("=" * 80)
print()

print("📊 RESUMEN:")
print(f"   Minas caracterizadas: {len(caracterizacion_completa)}")
print(f"   Índices validados: {len(validacion_indices)}")
if df_mag is not None:
    print(f"   Magnetometría: ✅ Interpolada")
if df_geo is not None:
    print(f"   Geoquímica: ✅ Contexto regional")
print()

print("📁 ARCHIVOS GENERADOS:")
print(f"   {resultados_dir / 'minas_caracterizacion_completa.json'}")
print(f"   {resultados_dir / 'minas_validacion_indices.json'}")
print(f"   {resultados_dir / 'minas_validacion_indices.csv'}")
print(f"   {resultados_dir / 'ranking_indicadores.csv'}")
print(f"   {resultados_dir / 'mejor_indicador_analisis.txt'}")
print()

print("💡 PRÓXIMO PASO:")
print("   Ejecutar Fase 3 para calcular prospectividad basada en similitud multi-criterio")
print()
