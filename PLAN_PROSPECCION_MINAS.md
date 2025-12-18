# 📋 PLAN DETALLADO - PROSPECCIÓN MINA SANTA RITA

## 🎯 OBJETIVO
Identificar zonas con potencial económico similar a las minas existentes (Candelaria, El Pino, Fortuna, Santa Rita) usando **TODA** la información disponible, especialmente los datos satelitales que sí cubren las zonas mineras.

---

## 📊 INVENTARIO DE DATOS DISPONIBLES

### ✅ Datos con Cobertura en Minas
1. **Imágenes Landsat 9** (LC09_L2SP_031043)
   - Resolución: 30m
   - Cobertura: COMPLETA sobre las 4 minas
   - Bandas: B1-B7 + térmicas
   - **VENTAJA**: Único dataset que SÍ cubre las minas

2. **Índices Espectrales Calculados**
   - GOSSAN (B4/B2): Óxidos de hierro → 0.998-1.256
   - FMI (B6/B5): Minerales ferrosos → 0.781-1.174
   - FeO (B4/B5): Óxidos férricos → 0.507-0.775
   - CMR (B6/B7): Alteración arcillosa → 1.137-1.331
   - NDII: Índice normalizado de hierro → -0.001-0.113
   - AI: Alteración hidrotermal → 1.392-2.143
   - **VENTAJA**: Ya calculados, listos para extraer valores en minas

### ⚠️ Datos con Cobertura Parcial
3. **Magnetometría SGM** (6,325 puntos totales)
   - En zona minas (30 km radio): 209 puntos
   - Interpolación RBF disponible
   - **LIMITACIÓN**: Sin datos <500m de minas
   - **VENTAJA**: Interpolación da valores aproximados

4. **Geoquímica SGM** (1,070 muestras totales)
   - En zona minas (30 km radio): 115 muestras
   - Elementos: AU, AG, CU, FE, ZN, PB, MO, NI, MG, MN, GA, P
   - **LIMITACIÓN**: Sin muestras <500m de minas
   - **VENTAJA**: Distribución regional conocida

### 📍 Datos de Referencia
5. **Ubicaciones de Minas** (4 minas productivas)
   - Candelaria: 24.601°N, -106.033°W
   - El Pino: 24.606°N, -106.026°W
   - Fortuna: 24.604°N, -106.033°W
   - Santa Rita: 24.604°N, -106.034°W
   - **VENTAJA**: Ground truth de viabilidad económica

---

## 🔬 FASE 1: CARACTERIZACIÓN ESPECTRAL DE MINAS (NUEVO)

### Objetivo
**Extraer la "firma espectral" de las minas usando Landsat**, que es el único dato que SÍ las cubre.

### Metodología
1. **Extracción de Valores en Minas**
   ```python
   # Para cada mina (radio 500m):
   for mina in [Candelaria, ElPino, Fortuna, SantaRita]:
       # Extraer valores de todos los índices
       valores_gossan = extract_pixels(GOSSAN, mina, radio=500m)
       valores_fmi = extract_pixels(FMI, mina, radio=500m)
       valores_feo = extract_pixels(FeO, mina, radio=500m)
       valores_cmr = extract_pixels(CMR, mina, radio=500m)
       valores_ai = extract_pixels(AI, mina, radio=500m)
       
       # Calcular estadísticas
       firma_mina[mina] = {
           'GOSSAN_mean': mean(valores_gossan),
           'GOSSAN_std': std(valores_gossan),
           'FMI_mean': mean(valores_fmi),
           # ... etc para todos los índices
       }
   ```

2. **Análisis Estadístico**
   - Media ± desviación estándar de cada índice
   - Percentiles (p25, p50, p75, p90)
   - Distribuciones (histogramas)
   - **¿Son consistentes entre las 4 minas?**

3. **Definir Firma Espectral Promedio**
   ```python
   firma_target = {
       'GOSSAN': (mean_all_minas, std_all_minas),
       'FMI': (mean_all_minas, std_all_minas),
       'FeO': (mean_all_minas, std_all_minas),
       'CMR': (mean_all_minas, std_all_minas),
       'AI': (mean_all_minas, std_all_minas),
   }
   ```

### Preguntas a Responder
- ✅ ¿Las 4 minas tienen firmas espectrales similares?
- ✅ ¿Qué índices son más distintivos?
- ✅ ¿Hay índices que TODOS tengan valores altos/bajos?
- ✅ ¿Qué rangos definen una zona "tipo mina"?

### Salidas Esperadas
- `minas_firma_espectral.json`: Estadísticas por mina
- `minas_firma_promedio.json`: Firma target para búsqueda
- `minas_indices_distribucion.png`: Histogramas comparativos
- `minas_indices_boxplot.png`: Comparación entre minas

---

## 🗺️ FASE 2: INTEGRACIÓN MULTI-FUENTE EN ZONA MINAS

### Objetivo
**Combinar magnetometría interpolada + geoquímica regional + firma espectral** para caracterizar las zonas mineras.

### Metodología

#### 2.1 Valores Magnetométricos en Minas (Interpolados)
```python
# Usar interpolación RBF existente
for mina in minas:
    mag_interpolada = rbf_magnetometria(mina.utm_x, mina.utm_y)
    print(f"{mina.nombre}: {mag_interpolada:.2f} ± σ")
```
**Hipótesis**: Si las minas tienen valores magnéticos altos, buscar anomalías similares.

#### 2.2 Contexto Geoquímico Regional
```python
# Analizar muestras cercanas (aunque no estén a <500m)
for mina in minas:
    muestras_cercanas = geoquimica[distancia < 2000m]  # Expandir a 2 km
    if len(muestras_cercanas) > 0:
        print(f"AU promedio a <2km: {mean(muestras_cercanas['AU'])}")
        print(f"CU promedio a <2km: {mean(muestras_cercanas['CU'])}")
```
**Objetivo**: Entender contexto geoquímico aunque no tengamos datos exactos en las minas.

#### 2.3 Validación de Índices Espectrales
```python
# ¿Los índices tienen sentido en las minas?
for indice in ['GOSSAN', 'FMI', 'FeO', 'CMR', 'AI']:
    valores_minas = extract_values(indice, minas)
    percentil_regional = calculate_percentile(indice, zona_30km)
    
    print(f"{indice}:")
    print(f"  Valor en minas: {mean(valores_minas):.3f}")
    print(f"  Percentil regional: {percentil_regional:.1f}%")
    
    if percentil_regional > 75:
        print("  ✅ Minas tienen valores ALTOS (buen indicador)")
    elif percentil_regional < 25:
        print("  ✅ Minas tienen valores BAJOS (indicador inverso)")
    else:
        print("  ⚠️ Valores medios (indicador débil)")
```

### Preguntas a Responder
- ✅ ¿Qué valor magnético (interpolado) tienen las minas?
- ✅ ¿Están en percentil alto/bajo/medio?
- ✅ ¿Hay muestras geoquímicas a 1-3 km? ¿Qué muestran?
- ✅ ¿Los índices espectrales en minas son anómalos o normales?
- ✅ ¿Cuál es el mejor discriminador: mag, geo, o espectral?

### Salidas Esperadas
- `minas_caracterizacion_completa.json`: Todos los valores
- `minas_contexto_regional.png`: Mapa con minas + datos cercanos
- `minas_validacion_indices.csv`: Tabla de validación
- `mejor_indicador_analisis.txt`: Recomendación de qué usar

---

## 🎯 FASE 3: PROSPECCIÓN BASADA EN SIMILITUD MULTI-CRITERIO

### Objetivo
**Buscar píxeles con firma similar a las minas** usando todos los datos disponibles.

### Metodología

#### 3.1 Score de Similitud Espectral
```python
def calcular_similitud_espectral(pixel_x, pixel_y, firma_target):
    """
    Calcula qué tan similar es un píxel a la firma de las minas
    """
    score = 0
    n_indices = 0
    
    for indice in ['GOSSAN', 'FMI', 'FeO', 'CMR', 'AI']:
        valor_pixel = extraer_valor(indice, pixel_x, pixel_y)
        target_mean, target_std = firma_target[indice]
        
        # Distancia normalizada (Z-score invertido)
        z_score = abs(valor_pixel - target_mean) / target_std
        similitud = exp(-z_score**2 / 2)  # Gaussiana: 1.0 si igual, 0.0 si muy diferente
        
        score += similitud
        n_indices += 1
    
    return score / n_indices  # Score entre 0 y 1
```

#### 3.2 Score Magnetométrico
```python
def calcular_score_magnetometria(pixel_x, pixel_y, mag_target):
    """
    Compara magnetometría interpolada con valor en minas
    """
    mag_pixel = rbf_interpolada(pixel_x, pixel_y)
    mag_minas_mean, mag_minas_std = mag_target
    
    z_score = abs(mag_pixel - mag_minas_mean) / mag_minas_std
    score = exp(-z_score**2 / 2)
    
    return score
```

#### 3.3 Score Geoquímico (Densidad de Anomalías)
```python
def calcular_score_geoquimico(pixel_x, pixel_y, radio=2000):
    """
    Densidad de muestras anómalas en Au, Cu, Ag cerca del píxel
    """
    muestras_cercanas = geoquimica[distancia < radio]
    
    if len(muestras_cercanas) == 0:
        return 0.5  # Neutral si no hay datos
    
    # Contar muestras con valores altos
    anomalas_au = sum(muestras_cercanas['AU'] > percentil(AU, 75))
    anomalas_cu = sum(muestras_cercanas['CU'] > percentil(CU, 75))
    anomalas_ag = sum(muestras_cercanas['AG'] > percentil(AG, 75))
    
    score = (anomalas_au + anomalas_cu + anomalas_ag) / (3 * len(muestras_cercanas))
    
    return score
```

#### 3.4 Prospectividad Integrada
```python
# Pesos adaptativos según validación de Fase 2
peso_espectral = 0.60  # Alto porque SÍ cubre minas
peso_magnetico = 0.25  # Medio porque es interpolado
peso_geoquimico = 0.15  # Bajo porque datos lejanos

prospectividad = (
    peso_espectral * score_espectral +
    peso_magnetico * score_magnetico +
    peso_geoquimico * score_geoquimico
)
```

### Criterios de Targets
1. **Prospectividad > p90** (top 10%)
2. **Área contigua > 100 ha** (viable para exploración)
3. **Distancia minas < 30 km** (área de interés)
4. **Score espectral > 0.7** (firma similar)

### Salidas Esperadas
- `mapa_similitud_espectral.png`: Heatmap de similitud
- `mapa_prospectividad_integrada.png`: Prospectividad final
- `targets_validados.csv`: Lista de targets con todos los scores
- `targets_prioridad.geojson`: Para visualizar en QGIS/folium

---

## 🔍 FASE 4: VALIDACIÓN Y RANKING

### Objetivo
**Priorizar targets según múltiples criterios** y generar mapa interactivo.

### Metodología

#### 4.1 Tabla de Scoring Multi-Criterio
```python
for target in targets:
    tabla[target] = {
        'prospectividad': target.score_total,
        'similitud_espectral': target.score_espectral,
        'anomalia_magnetica': target.score_magnetico,
        'contexto_geoquimico': target.score_geoquimico,
        'area_ha': target.area,
        'distancia_mina_km': target.dist_mina_cercana,
        'ranking': calcular_ranking(target)
    }
```

#### 4.2 Criterios de Ranking
```python
def calcular_ranking(target):
    """
    Priorización: más peso a similitud espectral y cercanía a minas
    """
    puntos = 0
    
    # Similitud espectral (0-40 puntos)
    puntos += target.score_espectral * 40
    
    # Distancia a mina (0-30 puntos, mejor si cerca)
    puntos += (30 - target.dist_mina_km) if target.dist_mina_km < 30 else 0
    
    # Prospectividad total (0-20 puntos)
    puntos += target.prospectividad * 20
    
    # Área (0-10 puntos, mejor 100-1000 ha)
    if 100 <= target.area_ha <= 1000:
        puntos += 10
    elif target.area_ha < 100:
        puntos += 5
    
    return puntos / 100  # Score 0-1
```

#### 4.3 Mapa Interactivo Final
```python
# Capas:
1. Landsat RGB
2. GOSSAN (óxidos de hierro)
3. FeO (óxidos férricos)
4. AI (alteración hidrotermal)
5. Similitud Espectral (NUEVO)
6. Magnetometría Interpolada
7. Densidad Au (geoquímica)
8. Prospectividad Integrada
9. Clasificación (MUY ALTA, ALTA, MEDIA)
10. Minas (markers con firmas)
11. Targets (markers con ranking)

# Popups en targets:
- Ranking: ★★★★☆ (4.2/5.0)
- Prospectividad: 0.87
- Similitud espectral: 0.91 ✅
- Anomalía magnética: 1.8σ
- Contexto geoquímico: 0.65
- Área: 245 ha
- Distancia: 8.3 km de Mina El Pino
```

### Salidas Esperadas
- `mapa_prospeccion_final_v2.html`: Interactivo con 11 capas
- `targets_ranking.csv`: Tabla completa ordenada
- `top5_targets.pdf`: Fichas detalladas de mejores 5
- `reporte_prospeccion.md`: Documento técnico completo

---

## 📊 FASE 5: ANÁLISIS DE SENSIBILIDAD Y RECOMENDACIONES

### Objetivo
**Evaluar robustez del modelo** y dar recomendaciones de exploración.

### Metodología

#### 5.1 Análisis de Sensibilidad
```python
# Variar pesos y ver cómo cambian targets
pesos_test = [
    (0.60, 0.25, 0.15),  # Actual
    (0.70, 0.20, 0.10),  # Más espectral
    (0.50, 0.30, 0.20),  # Más magnético
    (0.50, 0.20, 0.30),  # Más geoquímico
    (0.33, 0.33, 0.33),  # Igual peso
]

for pesos in pesos_test:
    recalcular_prospectividad(pesos)
    targets_nuevos = identificar_targets()
    
    # ¿Los top 5 targets se mantienen?
    estabilidad = len(set(top5_actual) & set(targets_nuevos[:5])) / 5
    print(f"Pesos {pesos}: Estabilidad = {estabilidad:.2%}")
```

#### 5.2 Comparación con Targets Anteriores
```python
# ¿Qué tan diferentes son los targets corregidos vs iniciales?
targets_v1 = load('targets_paso3.csv')  # Los del mar
targets_v2 = load('targets_corregidos.csv')  # Overlap zone
targets_v3 = load('targets_zona_minas.csv')  # 30 km radio
targets_v4 = load('targets_validados.csv')  # Multi-criterio (NUEVO)

comparar_versiones([v1, v2, v3, v4])
```

#### 5.3 Recomendaciones de Exploración
```markdown
## RECOMENDACIONES

### Targets Prioritarios (Exploración Inmediata)
1. **Target #X** (Ranking 4.8/5.0)
   - Ubicación: [lat, lon]
   - Justificación: Similitud espectral 0.95, a 5 km de Mina El Pino
   - Siguiente paso: Muestreo geoquímico detallado
   - Presupuesto estimado: $X USD

### Targets Secundarios (Exploración Fase 2)
...

### Zonas a Evitar
- Targets con score espectral <0.5
- Targets a >25 km de minas conocidas
- Targets con área <50 ha (demasiado pequeños)

### Necesidades de Datos Adicionales
1. **Geoquímica de suelos** en zona de minas (actualmente gap)
2. **Magnetometría terrestre** detallada en top 5 targets
3. **Imágenes multiespectrales** adicionales (Sentinel-2, ASTER)
4. **Información geológica** de las minas (tipo de depósito)
```

---

## 📁 ESTRUCTURA DE ARCHIVOS ESPERADA

```
resultados/
├── fase1_caracterizacion/
│   ├── minas_firma_espectral.json
│   ├── minas_firma_promedio.json
│   ├── minas_indices_distribucion.png
│   └── minas_indices_boxplot.png
│
├── fase2_integracion/
│   ├── minas_caracterizacion_completa.json
│   ├── minas_contexto_regional.png
│   ├── minas_validacion_indices.csv
│   └── mejor_indicador_analisis.txt
│
├── fase3_prospeccion/
│   ├── mapa_similitud_espectral.png
│   ├── mapa_prospectividad_integrada.png
│   ├── targets_validados.csv
│   └── targets_prioridad.geojson
│
├── fase4_validacion/
│   ├── mapa_prospeccion_final_v2.html
│   ├── targets_ranking.csv
│   ├── top5_targets.pdf
│   └── reporte_prospeccion.md
│
└── fase5_sensibilidad/
    ├── analisis_sensibilidad.csv
    ├── comparacion_versiones.png
    └── recomendaciones_exploracion.md
```

---

## 🚀 ORDEN DE EJECUCIÓN

### Sesión 1 (2-3 horas)
1. ✅ **Fase 1 completa**: Caracterizar firmas espectrales
2. ✅ **Fase 2.1-2.2**: Magnetometría y geoquímica en minas
3. 📊 **Análisis intermedio**: ¿Qué datos son más útiles?

### Sesión 2 (2-3 horas)
4. ✅ **Fase 2.3**: Validar índices espectrales
5. ✅ **Fase 3 completa**: Calcular prospectividad multi-criterio
6. 🎯 **Identificar targets v4**

### Sesión 3 (1-2 horas)
7. ✅ **Fase 4 completa**: Ranking y mapa interactivo
8. ✅ **Fase 5 completa**: Sensibilidad y recomendaciones
9. 📄 **Reporte final**

---

## 💡 VENTAJAS DE ESTE ENFOQUE

### ✅ Usa el Dato Más Confiable
- **Landsat CUBRE las minas** → firma espectral es ground truth real
- No dependemos de interpolaciones lejanas

### ✅ Multi-Criterio Robusto
- No confiamos en un solo indicador
- Pesos adaptativos según validación

### ✅ Validación Cruzada
- Comparamos mag interpolada, geo regional, y espectral directo
- Identificamos qué indicadores funcionan mejor

### ✅ Ranking Objetivo
- Criterios cuantitativos
- Análisis de sensibilidad
- Comparación con versiones previas

### ✅ Interpretación Geológica
- ¿Qué índices se correlacionan con mineralización?
- ¿Es un sistema de alta/baja susceptibilidad magnética?
- ¿Qué tipo de alteración hidrotermal?

---

## 🔬 PREGUNTAS CIENTÍFICAS A RESPONDER

1. **Espectral**
   - ¿Las 4 minas tienen firmas GOSSAN/FeO/AI similares?
   - ¿Qué índice discrimina mejor?
   - ¿Hay patrones espaciales (ej. halos de alteración)?

2. **Magnético**
   - ¿Qué valor magnético (interpolado) tienen las minas?
   - ¿Están sobre anomalías positivas o negativas?
   - ¿Es un sistema magnético (skarn) o no-magnético (epitermal)?

3. **Geoquímico**
   - ¿Hay correlación Au-Cu-Ag en zona regional?
   - ¿Qué elementos son pathfinders?
   - ¿Hay gradientes hacia las minas?

4. **Integración**
   - ¿Cuál es el mejor predictor de mineralización económica?
   - ¿Los pesos 60/25/15 son óptimos?
   - ¿Hay targets estables en diferentes configuraciones?

---

## ⚠️ LIMITACIONES Y SUPUESTOS

### Limitaciones Conocidas
1. **Sin datos geoquímicos <500m de minas** → usamos contexto regional
2. **Magnetometría interpolada en minas** → aproximación, no medición directa
3. **1 escena Landsat** → sin validación temporal
4. **No sabemos tipo de depósito** → asumimos que firma espectral es representativa

### Supuestos Clave
1. **Zonas con firma espectral similar tienen potencial similar**
2. **Interpolación RBF es razonablemente precisa a 2-3 km de datos**
3. **Las 4 minas son del mismo tipo de depósito** (a validar en Fase 1)
4. **Landsat L2 (superficie) representa alteración en profundidad**

---

## 📝 NOTAS TÉCNICAS

### Parámetros Clave
- **Radio extracción en minas**: 500m (flexible a 250-1000m)
- **Radio búsqueda geoquímica**: 2000m (flexible a 1000-5000m)
- **Grid prospectividad**: 100×100 (60 km × 60 km)
- **Umbral prospectividad**: p90 (top 10%)
- **Área mínima target**: 100 ha

### Software/Librerías
- `rasterio`: Leer bandas Landsat
- `scipy.interpolate.Rbf`: Magnetometría
- `sklearn.preprocessing`: Normalización
- `scipy.ndimage.label`: Identificar targets
- `folium`: Mapa interactivo
- `matplotlib`: Visualizaciones

### Performance
- Fase 1: ~5 min (lectura bandas + extracción)
- Fase 2: ~10 min (interpolación + validación)
- Fase 3: ~15 min (cálculo similitud en 10,000 píxeles)
- Fase 4: ~5 min (ranking + mapa HTML)
- Fase 5: ~10 min (sensibilidad + reporte)
- **TOTAL: ~45 minutos de cómputo**

---

## 🎯 CRITERIO DE ÉXITO

### Resultados Esperados
1. ✅ **Firma espectral de minas caracterizada** con estadísticas robustas
2. ✅ **3-10 targets validados** dentro de 30 km de minas
3. ✅ **Ranking objetivo** con múltiples criterios
4. ✅ **Mapa interactivo** con 11 capas + popups informativos
5. ✅ **Reporte técnico** con recomendaciones de exploración

### Métricas de Validación
- **Consistencia espectral**: ¿Las 4 minas tienen σ_inter/σ_intra < 0.5?
- **Estabilidad de targets**: ¿Top 5 se mantiene en 80% de configuraciones?
- **Distancia a minas**: ¿Targets a <15 km en promedio?
- **Similitud espectral**: ¿Targets con score >0.7?

---

## 🛠️ PRÓXIMOS PASOS (SIGUIENTE SESIÓN)

1. Crear script `test/test_fase1_firma_espectral.py`
2. Ejecutar Fase 1 completa
3. Analizar resultados: ¿Minas tienen firmas consistentes?
4. Decidir pesos para Fase 3 según hallazgos Fase 2
5. Continuar con pipeline completo

---

**FECHA CREACIÓN**: 2025-12-10  
**ÚLTIMA ACTUALIZACIÓN**: 2025-12-10  
**AUTOR**: GitHub Copilot  
**PROYECTO**: Prospección Mina Santa Rita - Chihuahua, México
