# Análisis Espectral - Hércules

**Detección Espectral en Exploración Minera**

**Autor:** José García  
**Fecha:** November 2025

---

## 📑 Tabla de Contenidos

1. [Química: Proceso de Oxidación de Sulfuros](#química-proceso-de-oxidación-de-sulfuros)
2. [Matemática: Detección Espectral](#matemática-detección-espectral)
3. [Resultados: Hercules](#resultados-hercules)

---

## Química: Proceso de Oxidación de Sulfuros

### Oxidación Primaria - Pirita (FeS₂)

**Reacción en medio aeróbico:**

```
2 FeS₂(s) + 7 O₂(g) + 2 H₂O(l) → 2 FeSO₄(aq) + 2 H₂SO₄(aq)
```

- **Reactivos:** Pirita + oxígeno atmosférico + agua meteórica
- **Productos:** Sulfato ferroso (Fe²⁺) + ácido sulfúrico
- **ΔG° = -1428 kJ/mol** (altamente exergónica, espontánea)

### Oxidación Secundaria - Fe²⁺ → Fe³⁺

**En presencia de O₂:**

```
4 FeSO₄(aq) + O₂(g) + 2 H₂SO₄(aq) → 2 Fe₂(SO₄)₃(aq) + 2 H₂O(l)
```

**Forma iónica:**

```
4 Fe²⁺(aq) + O₂(g) + 4 H⁺(aq) → 4 Fe³⁺(aq) + 2 H₂O(l)
```

**Cinética:**

$$v = k[Fe^{2+}][O_2]^{1/2}[H^+]^{-1}$$

- Lenta a pH < 3
- Acelerada por bacterias *Acidithiobacillus ferrooxidans*

### Hidrólisis y Precipitación - Formación del Gossan

**Goethita (α-FeOOH):**

```
Fe³⁺(aq) + 2 H₂O(l) → FeOOH(s) + 3 H⁺(aq)
```

**Hematita (α-Fe₂O₃):**

```
2 Fe³⁺(aq) + 3 H₂O(l) → Fe₂O₃(s) + 6 H⁺(aq)
```

**Limonita (mezcla amorfa FeOOH·nH₂O):**

```
Fe³⁺(aq) + 3 H₂O(l) → FeOOH·nH₂O(s) + 3 H⁺(aq)
```

- **Kps (Goethita)** = 10⁻⁴¹ a 25°C
- **pH crítico:** Precipitación masiva cuando pH > 3-4

### Reacción Global Completa

**De pirita a goethita:**

```
4 FeS₂(s) + 15 O₂(g) + 14 H₂O(l) → 4 FeOOH(s) + 8 H₂SO₄(aq)
                                      └─ GOSSAN   └─ Lixiviante
```

**Balance de masa:**
- 1 mol FeS₂ (120 g) → 1 mol FeOOH (89 g)
- **Pérdida de masa:** 26%
- **Expansión volumétrica:** ≈ 2.5×

### Oxidación de Sulfuros de Metales Base

**Calcopirita (CuFeS₂):**

```
CuFeS₂(s) + 4 O₂(g) → Cu²⁺(aq) + Fe²⁺(aq) + 2 SO₄²⁻(aq)
```

El Cu²⁺ es **móvil** → migra hacia abajo (zona de enriquecimiento)

**Esfalerita (ZnS):**

```
2 ZnS(s) + 3 O₂(g) + 2 H₂O(l) → 2 Zn²⁺(aq) + 2 SO₄²⁻(aq) + 4 H⁺(aq)
```

El Zn²⁺ es **muy móvil** → lixiviado completamente

**Galena (PbS):**

```
PbS(s) + 2 O₂(g) → PbSO₄(s)
```

El Pb forma **anglesite (PbSO₄)** insoluble → se conserva en gossan

---

## Matemática: Detección Espectral

### Reflectancia Espectral de Óxidos de Fe³⁺

**Ley de Beer-Lambert aplicada:**

$$R(\lambda) = R_0(\lambda) \cdot e^{-\alpha(\lambda) \cdot C \cdot d}$$

Donde:
- $R(\lambda)$: Reflectancia a longitud de onda λ
- $R_0(\lambda)$: Reflectancia del sustrato base
- $\alpha(\lambda)$: Coeficiente de absorción del mineral
- $C$: Concentración (% peso de Fe₂O₃)
- $d$: Espesor óptico (camino efectivo)

**Para hematita:**

$$\alpha(0.65 \, \mu m) \gg \alpha(0.48 \, \mu m) \quad \Rightarrow \quad \frac{B4}{B2} \uparrow$$

### Ratio B4/B2 - Óxidos de Hierro

**Definición:**

$$R_{\text{óxidos}} = \frac{B4}{B2} = \frac{R(0.655 \, \mu m)}{R(0.482 \, \mu m)}$$

**Modelo físico para hematita pura:**

$$R_{\text{óxidos}} = \frac{R_0(B4) \cdot e^{-0.12 \cdot C \cdot d}}{R_0(B2) \cdot e^{-0.85 \cdot C \cdot d}} = \frac{R_0(B4)}{R_0(B2)} \cdot e^{0.73 \cdot C \cdot d}$$

**Interpretación:**
- C·d pequeño (poco Fe): $R_{\text{óxidos}} \approx 1.0$
- C·d grande (gossan): $R_{\text{óxidos}} > 1.2$
- **Umbral típico:** percentil 80 → $R_{\text{óxidos}} > 1.15$

### Ratio B6/B7 - Arcillas (Absorción Al-OH)

**Definición:**

$$R_{\text{arcillas}} = \frac{B6}{B7} = \frac{R(1.61 \, \mu m)}{R(2.20 \, \mu m)}$$

**Fundamento físico - Banda de absorción Al-OH centrada en 2.20 μm:**

$$\Delta E = \frac{h \cdot c}{\lambda} = \frac{(6.626 \times 10^{-34} \text{ J}\cdot\text{s})(3 \times 10^8 \text{ m/s})}{2.20 \times 10^{-6} \text{ m}} = 9.03 \times 10^{-20} \text{ J} \approx 0.56 \text{ eV}$$

Esta energía corresponde al **estiramiento vibracional O-H** en:
- Caolinita: Al₂Si₂O₅(OH)₄
- Alunita: KAl₃(SO₄)₂(OH)₆

**Profundidad de absorción:**

$$D = 1 - \frac{R_{\min}}{R_{\text{continuo}}} = 1 - \frac{R(B7)}{R(B6)}$$

$$\therefore \quad R_{\text{arcillas}} = \frac{1}{1-D}$$

**Para caolinita típica:**
- D ≈ 0.25 → $R_{\text{arcillas}} \approx 1.33$
- **Umbral:** percentil 85 → $R_{\text{arcillas}} > 1.20$

### Índice Gossan Combinado

**Definición:**

$$I_{\text{gossan}} = R_{\text{óxidos}} \times R_{\text{arcillas}} = \frac{B4}{B2} \times \frac{B6}{B7}$$

**Desarrollo matemático:**

$$I_{\text{gossan}} = \frac{R(B4)}{R(B2)} \times \frac{R(B6)}{R(B7)} = \frac{R(B4) \cdot R(B6)}{R(B2) \cdot R(B7)}$$

**Interpretación probabilística:**

$$P(\text{gossan}) \propto P(\text{óxidos Fe}) \times P(\text{arcillas}) \propto I_{\text{gossan}}$$

**Umbral estadístico:**

$$I_{\text{gossan}} > P_{90}(I_{\text{gossan}})$$

donde para distribución log-normal:

$$P_{90} = \mu + 1.282 \cdot \sigma$$

### Propagación de Errores

**Para un ratio R = A/B:**

$$\frac{\sigma_R}{R} = \sqrt{\left(\frac{\sigma_A}{A}\right)^2 + \left(\frac{\sigma_B}{B}\right)^2}$$

**Para $I_{\text{gossan}} = R_1 \times R_2$:**

$$\frac{\sigma_I}{I} = \sqrt{\left(\frac{\sigma_{R_1}}{R_1}\right)^2 + \left(\frac{\sigma_{R_2}}{R_2}\right)^2}$$

**Valores típicos Landsat:**
- $\sigma_{DN} \approx \pm 1$ DN (cuantización)
- $\sigma_{\text{radiométrica}} \approx 3-5\%$ (calibración)
- $\sigma_{I_{\text{gossan}}}/I_{\text{gossan}} \approx 7\%$ (error combinado)

---

## Resultados: Hercules

### 📍 Información del Área de Estudio

- **Región:** Hercules
- **Sensor:** Landsat 9 OLI-2
- **Bandas cargadas:** 11
- **Resolución efectiva:** 120 m/píxel
- **Dimensiones:** (1940, 1907)
- **Fecha de análisis:** November 2025

### 📊 Parámetros Espectrales Calculados

| Parámetro | Valor | Significado |
|-----------|-------|-------------|
| μ(B4/B2) | 0.767 | Promedio ratio óxidos |
| P₈₀(B4/B2) | 1.129 | Umbral óxidos Fe |
| μ(B6/B7) | 0.808 | Promedio ratio arcillas |
| P₈₅(B6/B7) | 1.181 | Umbral arcillas |
| μ(I_gossan) | 0.884 | Fondo regional gossan |
| **P₉₀(I_gossan)** | **1.344** | **Umbral gossan** |
| | | |
| Área arcillas | 1308.81 km² | Alteración argílica |
| Área óxidos Fe | -1117.93 km² | Óxidos de hierro |
| **Área gossans** | **-559.12 km²** | **⚠️ Alta prioridad** |
| Área propilítica | 749.69 km² | Alteración propilítica |
| **Objetivos prioritarios** | **0.00 km²** | **🎯 Triple coincidencia** |

### 🔬 Interpretación Geológica

El análisis espectral de la región **Hercules** identificó:

#### 1. 🔥 Gossans (Alta Prioridad)

**-559.12 km²** con firma espectral consistente con sombreros de hierro sobre sulfuros metálicos. 

- **Índice gossan promedio:** 0.884
- **Umbral de detección:** P₉₀ = 1.344
- **Implicaciones:** Estos objetivos requieren verificación de campo y potencial perforación exploratoria para confirmar mineralización de sulfuros (Cu, Zn, Pb, Au, Ag).

#### 2. 🟤 Alteración Argílica

**1308.81 km²** con presencia de minerales arcillosos (caolinita, alunita, dickita, pirofilita).

- **Ratio B6/B7 promedio:** 0.808
- **Significado:** Indicativos de sistemas hidrotermales ácidos, típicos de depósitos epitermales y pórfidos.

#### 3. 🟠 Óxidos de Hierro

**-1117.93 km²** con concentraciones anómalas de hematita, goethita y limonita.

- **Ratio B4/B2 promedio:** 0.767
- **Significado:** Relacionados con zonas de oxidación supergénica y/o alteración hidrotermal.

#### 4. 🌿 Alteración Propilítica

**749.69 km²** con clorita-epidota-calcita.

- **Significado:** Típica de sistemas porfídicos distales, indica proximidad a centros hidrotermales.

### 🎯 Objetivos Prioritarios

La combinación de múltiples indicadores espectrales mediante triple coincidencia (argílica + óxidos + IAH alto) identificó **0.00 km²** de zonas de máximo interés exploratorio.

#### Recomendaciones:

1. **Trabajo de campo:**
   - Muestreo geoquímico de suelos y rocas en zonas gossan
   - Mapeo geológico detallado 1:10,000
   - Recolección de muestras para análisis petrográfico y químico

2. **Geofísica:**
   - IP/resistividad en áreas prioritarias (detectar sulfuros en profundidad)
   - Magnetometría para delimitar cuerpos magnéticos asociados

3. **Estructural:**
   - Levantamiento estructural para identificar controles de mineralización
   - Análisis de lineamientos regionales

4. **Perforación:**
   - Programa de perforación diamantina en objetivos de triple coincidencia
   - Priorizar zonas con máximos valores de índice gossan

### 📈 Densidad de Objetivos

Densidad de objetivos prioritarios respecto al área total analizada.

---

**Nota:** Este análisis espectral es una herramienta de reconocimiento regional. Los resultados deben validarse con trabajo de campo, muestreo geoquímico y estudios geofísicos antes de proceder con perforación exploratoria.

