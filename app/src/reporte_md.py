"""
🔍 TERRASF - Generador de Reportes Markdown
============================================

Genera documentos técnicos desde análisis TerrafPR en formato Markdown

Autor: TERRASF Team
Fecha: Noviembre 2025
"""

import numpy as np
from datetime import datetime


class ReporteMarkdown:
    """
    Genera reportes técnicos en Markdown desde análisis TerrafPR
    
    Uso:    
        pr = TerrafPR("datos/", "MiProyecto")
        pr.analisis_completo()
        
        reporte = ReporteMarkdown(pr, autor="Tu Nombre")
        reporte.generar_reporte_completo("reporte_miproyecto.md")
    """
    
    def __init__(self, terrasf_pr_instance, autor="TERRASF Team", titulo_proyecto=None):
        """
        Inicializa generador de reportes
        
        Args:
            terrasf_pr_instance: Instancia de TerrafPR con análisis completado
            autor: Nombre del autor del reporte
            titulo_proyecto: Título personalizado (opcional)
        """
        self.pr = terrasf_pr_instance
        self.autor = autor
        self.titulo = titulo_proyecto or f"Análisis Espectral - {self.pr.nombre}"
        self.fecha = datetime.now().strftime("%B %Y")
        
    def generar_reporte_completo(self, archivo_salida="reporte.md"):
        """
        Genera reporte Markdown completo con teoría + resultados
        
        Args:
            archivo_salida: Nombre del archivo .md de salida
        """
        print(f"\n📄 Generando reporte completo: {archivo_salida}")
        
        contenido = self._header()
        contenido += self._teoria_quimica()
        contenido += self._teoria_matematica()
        contenido += self._seccion_resultados()
        
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        print(f"  ✅ Reporte generado: {archivo_salida}")
        print(f"  💡 Ver en VSCode, GitHub, o convertir a PDF con: pandoc {archivo_salida} -o reporte.pdf")
        
    def generar_teoria(self, archivo_salida="teoria_gossan.md"):
        """
        Solo la parte teórica (química + matemática)
        
        Args:
            archivo_salida: Nombre del archivo .md de salida
        """
        print(f"\n📚 Generando teoría: {archivo_salida}")
        
        contenido = self._header()
        contenido += self._teoria_quimica()
        contenido += self._teoria_matematica()
        
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        print(f"  ✅ Teoría generada: {archivo_salida}")
        
    def generar_resultados(self, archivo_salida="resultados.md"):
        """
        Solo resultados de la zona de estudio
        
        Args:
            archivo_salida: Nombre del archivo .md de salida
        """
        print(f"\n📊 Generando resultados: {archivo_salida}")
        
        contenido = f"# Resultados: {self.pr.nombre}\n\n"
        contenido += self._seccion_resultados()
        
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        print(f"  ✅ Resultados generados: {archivo_salida}")
    
    def _header(self):
        """Genera el encabezado Markdown"""
        return f"""# {self.titulo}

**Detección Espectral en Exploración Minera**

**Autor:** {self.autor}  
**Fecha:** {self.fecha}

---

## 📑 Tabla de Contenidos

1. [Química: Proceso de Oxidación de Sulfuros](#química-proceso-de-oxidación-de-sulfuros)
2. [Matemática: Detección Espectral](#matemática-detección-espectral)
3. [Resultados: {self.pr.nombre}](#resultados-{self.pr.nombre.lower().replace(' ', '-')})

---

"""
    
    def _teoria_quimica(self):
        """Genera la sección de teoría química en Markdown"""
        return """## Química: Proceso de Oxidación de Sulfuros

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

"""
    
    def _teoria_matematica(self):
        """Genera la sección de teoría matemática en Markdown"""
        return """## Matemática: Detección Espectral

### Reflectancia Espectral de Óxidos de Fe³⁺

**Ley de Beer-Lambert aplicada:**

$$R(\\lambda) = R_0(\\lambda) \\cdot e^{-\\alpha(\\lambda) \\cdot C \\cdot d}$$

Donde:
- $R(\\lambda)$: Reflectancia a longitud de onda λ
- $R_0(\\lambda)$: Reflectancia del sustrato base
- $\\alpha(\\lambda)$: Coeficiente de absorción del mineral
- $C$: Concentración (% peso de Fe₂O₃)
- $d$: Espesor óptico (camino efectivo)

**Para hematita:**

$$\\alpha(0.65 \\, \\mu m) \\gg \\alpha(0.48 \\, \\mu m) \\quad \\Rightarrow \\quad \\frac{B4}{B2} \\uparrow$$

### Ratio B4/B2 - Óxidos de Hierro

**Definición:**

$$R_{\\text{óxidos}} = \\frac{B4}{B2} = \\frac{R(0.655 \\, \\mu m)}{R(0.482 \\, \\mu m)}$$

**Modelo físico para hematita pura:**

$$R_{\\text{óxidos}} = \\frac{R_0(B4) \\cdot e^{-0.12 \\cdot C \\cdot d}}{R_0(B2) \\cdot e^{-0.85 \\cdot C \\cdot d}} = \\frac{R_0(B4)}{R_0(B2)} \\cdot e^{0.73 \\cdot C \\cdot d}$$

**Interpretación:**
- C·d pequeño (poco Fe): $R_{\\text{óxidos}} \\approx 1.0$
- C·d grande (gossan): $R_{\\text{óxidos}} > 1.2$
- **Umbral típico:** percentil 80 → $R_{\\text{óxidos}} > 1.15$

### Ratio B6/B7 - Arcillas (Absorción Al-OH)

**Definición:**

$$R_{\\text{arcillas}} = \\frac{B6}{B7} = \\frac{R(1.61 \\, \\mu m)}{R(2.20 \\, \\mu m)}$$

**Fundamento físico - Banda de absorción Al-OH centrada en 2.20 μm:**

$$\\Delta E = \\frac{h \\cdot c}{\\lambda} = \\frac{(6.626 \\times 10^{-34} \\text{ J}\\cdot\\text{s})(3 \\times 10^8 \\text{ m/s})}{2.20 \\times 10^{-6} \\text{ m}} = 9.03 \\times 10^{-20} \\text{ J} \\approx 0.56 \\text{ eV}$$

Esta energía corresponde al **estiramiento vibracional O-H** en:
- Caolinita: Al₂Si₂O₅(OH)₄
- Alunita: KAl₃(SO₄)₂(OH)₆

**Profundidad de absorción:**

$$D = 1 - \\frac{R_{\\min}}{R_{\\text{continuo}}} = 1 - \\frac{R(B7)}{R(B6)}$$

$$\\therefore \\quad R_{\\text{arcillas}} = \\frac{1}{1-D}$$

**Para caolinita típica:**
- D ≈ 0.25 → $R_{\\text{arcillas}} \\approx 1.33$
- **Umbral:** percentil 85 → $R_{\\text{arcillas}} > 1.20$

### Índice Gossan Combinado

**Definición:**

$$I_{\\text{gossan}} = R_{\\text{óxidos}} \\times R_{\\text{arcillas}} = \\frac{B4}{B2} \\times \\frac{B6}{B7}$$

**Desarrollo matemático:**

$$I_{\\text{gossan}} = \\frac{R(B4)}{R(B2)} \\times \\frac{R(B6)}{R(B7)} = \\frac{R(B4) \\cdot R(B6)}{R(B2) \\cdot R(B7)}$$

**Interpretación probabilística:**

$$P(\\text{gossan}) \\propto P(\\text{óxidos Fe}) \\times P(\\text{arcillas}) \\propto I_{\\text{gossan}}$$

**Umbral estadístico:**

$$I_{\\text{gossan}} > P_{90}(I_{\\text{gossan}})$$

donde para distribución log-normal:

$$P_{90} = \\mu + 1.282 \\cdot \\sigma$$

### Propagación de Errores

**Para un ratio R = A/B:**

$$\\frac{\\sigma_R}{R} = \\sqrt{\\left(\\frac{\\sigma_A}{A}\\right)^2 + \\left(\\frac{\\sigma_B}{B}\\right)^2}$$

**Para $I_{\\text{gossan}} = R_1 \\times R_2$:**

$$\\frac{\\sigma_I}{I} = \\sqrt{\\left(\\frac{\\sigma_{R_1}}{R_1}\\right)^2 + \\left(\\frac{\\sigma_{R_2}}{R_2}\\right)^2}$$

**Valores típicos Landsat:**
- $\\sigma_{DN} \\approx \\pm 1$ DN (cuantización)
- $\\sigma_{\\text{radiométrica}} \\approx 3-5\\%$ (calibración)
- $\\sigma_{I_{\\text{gossan}}}/I_{\\text{gossan}} \\approx 7\\%$ (error combinado)

---

"""
    
    def _seccion_resultados(self):
        """Genera la sección de resultados con datos del análisis"""
        
        # Extraer datos si existen
        area_gossan = self._calcular_area('zona_gossan') if 'zona_gossan' in self.pr.zonas else 0
        area_argilica = self._calcular_area('zona_argilica') if 'zona_argilica' in self.pr.zonas else 0
        area_oxidos = self._calcular_area('zona_oxidos') if 'zona_oxidos' in self.pr.zonas else 0
        area_propilitica = self._calcular_area('zona_propilitica') if 'zona_propilitica' in self.pr.zonas else 0
        area_objetivos = self._calcular_area('objetivos_prioritarios') if 'objetivos_prioritarios' in self.pr.zonas else 0
        
        mu_gossan = np.nanmean(self.pr.indices['gossan']) if 'gossan' in self.pr.indices else 0
        mu_argilica = np.nanmean(self.pr.ratios['argilica']) if 'argilica' in self.pr.ratios else 0
        mu_oxidos = np.nanmean(self.pr.ratios['oxidos']) if 'oxidos' in self.pr.ratios else 0
        
        p90_gossan = np.nanpercentile(self.pr.indices['gossan'], 90) if 'gossan' in self.pr.indices else 0
        p85_argilica = np.nanpercentile(self.pr.ratios['argilica'], 85) if 'argilica' in self.pr.ratios else 0
        p80_oxidos = np.nanpercentile(self.pr.ratios['oxidos'], 80) if 'oxidos' in self.pr.ratios else 0
        
        return f"""## Resultados: {self.pr.nombre}

### 📍 Información del Área de Estudio

- **Región:** {self.pr.nombre}
- **Sensor:** Landsat 9 OLI-2
- **Bandas cargadas:** {len(self.pr.bandas)}
- **Resolución efectiva:** {self.pr.metadatos.get('resolution', 30)} m/píxel
- **Dimensiones:** {list(self.pr.bandas.values())[0].shape if self.pr.bandas else 'N/A'}
- **Fecha de análisis:** {self.fecha}

### 📊 Parámetros Espectrales Calculados

| Parámetro | Valor | Significado |
|-----------|-------|-------------|
| μ(B4/B2) | {mu_oxidos:.3f} | Promedio ratio óxidos |
| P₈₀(B4/B2) | {p80_oxidos:.3f} | Umbral óxidos Fe |
| μ(B6/B7) | {mu_argilica:.3f} | Promedio ratio arcillas |
| P₈₅(B6/B7) | {p85_argilica:.3f} | Umbral arcillas |
| μ(I_gossan) | {mu_gossan:.3f} | Fondo regional gossan |
| **P₉₀(I_gossan)** | **{p90_gossan:.3f}** | **Umbral gossan** |
| | | |
| Área arcillas | {area_argilica:.2f} km² | Alteración argílica |
| Área óxidos Fe | {area_oxidos:.2f} km² | Óxidos de hierro |
| **Área gossans** | **{area_gossan:.2f} km²** | **⚠️ Alta prioridad** |
| Área propilítica | {area_propilitica:.2f} km² | Alteración propilítica |
| **Objetivos prioritarios** | **{area_objetivos:.2f} km²** | **🎯 Triple coincidencia** |

### 🔬 Interpretación Geológica

El análisis espectral de la región **{self.pr.nombre}** identificó:

#### 1. 🔥 Gossans (Alta Prioridad)

**{area_gossan:.2f} km²** con firma espectral consistente con sombreros de hierro sobre sulfuros metálicos. 

- **Índice gossan promedio:** {mu_gossan:.3f}
- **Umbral de detección:** P₉₀ = {p90_gossan:.3f}
- **Implicaciones:** Estos objetivos requieren verificación de campo y potencial perforación exploratoria para confirmar mineralización de sulfuros (Cu, Zn, Pb, Au, Ag).

#### 2. 🟤 Alteración Argílica

**{area_argilica:.2f} km²** con presencia de minerales arcillosos (caolinita, alunita, dickita, pirofilita).

- **Ratio B6/B7 promedio:** {mu_argilica:.3f}
- **Significado:** Indicativos de sistemas hidrotermales ácidos, típicos de depósitos epitermales y pórfidos.

#### 3. 🟠 Óxidos de Hierro

**{area_oxidos:.2f} km²** con concentraciones anómalas de hematita, goethita y limonita.

- **Ratio B4/B2 promedio:** {mu_oxidos:.3f}
- **Significado:** Relacionados con zonas de oxidación supergénica y/o alteración hidrotermal.

#### 4. 🌿 Alteración Propilítica

**{area_propilitica:.2f} km²** con clorita-epidota-calcita.

- **Significado:** Típica de sistemas porfídicos distales, indica proximidad a centros hidrotermales.

### 🎯 Objetivos Prioritarios

La combinación de múltiples indicadores espectrales mediante triple coincidencia (argílica + óxidos + IAH alto) identificó **{area_objetivos:.2f} km²** de zonas de máximo interés exploratorio.

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

"""
    
    def _calcular_area(self, zona_key):
        """Calcula área de una zona en km²"""
        if zona_key not in self.pr.zonas:
            return 0.0
        
        n_pixeles = np.sum(self.pr.zonas[zona_key])
        resolucion = self.pr.metadatos.get('resolution', 30)
        area_km2 = n_pixeles * (resolucion ** 2) / 1e6
        
        return area_km2
