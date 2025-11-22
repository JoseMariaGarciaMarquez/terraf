# 📝 Convención de Commits - TERRAF

Este documento establece las reglas para los mensajes de commit en el proyecto TERRAF.

## 🎯 Formato General

```
<tipo>: <alcance>: <descripción corta>

[Cuerpo opcional con más detalles]
```

## 📌 Tipos de Commit

### 🐛 `bugfix` - Corrección de errores

Para correcciones de bugs o errores en el código.

**Formato:**
```
bugfix: <archivo/módulo>: <descripción del bug corregido>
```

**Ejemplos:**
```
bugfix: terraf_pr.py: fixed division by zero in calcular_gossan
bugfix: pruebas.py: fixed import path for src module
bugfix: environment.yml: corrected rasterio version conflict
```

---

### ✨ `feature` - Nueva funcionalidad

Para agregar nuevas características o funcionalidades.

**Formato:**
```
feature: <módulo>: <descripción de la nueva funcionalidad>
```

**Ejemplos:**
```
feature: terraf_pr.py: added clay_index calculation method
feature: magnetometry: added magnetic anomaly detection
feature: gravity: implemented Bouguer anomaly correction
```

---

### 📚 `docs` - Documentación

Para cambios en documentación, comentarios o README.

**Formato:**
```
docs: <archivo/sección>: <descripción del cambio>
```

**Ejemplos:**
```
docs: README.md: added installation instructions
docs: terraf_pr.py: improved docstrings for all methods
docs: COMMIT_CONVENTION.md: created commit guidelines
```

---

### 🎨 `style` - Formato de código

Para cambios de estilo, formato, espacios, etc. (sin cambiar funcionalidad).

**Formato:**
```
style: <archivo>: <descripción del cambio de formato>
```

**Ejemplos:**
```
style: terraf_pr.py: applied black formatter
style: pruebas.py: fixed indentation and line length
style: src/: organized imports with isort
```

---

### ♻️ `refactor` - Refactorización

Para reestructuración de código sin cambiar funcionalidad.

**Formato:**
```
refactor: <módulo>: <descripción de la refactorización>
```

**Ejemplos:**
```
refactor: terraf_pr.py: extracted band loading to separate method
refactor: visualization: modularized plotting functions
refactor: utils: split file into multiple modules
```

---

### 🧪 `test` - Pruebas

Para agregar o modificar pruebas.

**Formato:**
```
test: <archivo/módulo>: <descripción de las pruebas>
```

**Ejemplos:**
```
test: pruebas.py: added tests for all indices
test: magnetometry: created unit tests for filtering
test: integration: added end-to-end workflow test
```

---

### 🔧 `config` - Configuración

Para cambios en archivos de configuración, entorno, dependencias.

**Formato:**
```
config: <archivo>: <descripción del cambio>
```

**Ejemplos:**
```
config: environment.yml: updated numpy to version 1.24
config: .gitignore: added .ipynb_checkpoints
config: setup.py: added project metadata
```

---

### 🚀 `deploy` - Despliegue

Para cambios relacionados con despliegue o CI/CD.

**Formato:**
```
deploy: <sistema>: <descripción del cambio>
```

**Ejemplos:**
```
deploy: github-actions: added automated testing workflow
deploy: docker: created Dockerfile for project
deploy: release: version 1.0.0 ready for production
```

---

### 🗑️ `remove` - Eliminación

Para eliminar archivos, funciones o código obsoleto.

**Formato:**
```
remove: <archivo/función>: <razón de eliminación>
```

**Ejemplos:**
```
remove: old_analysis.py: deprecated in favor of terraf_pr
remove: terraf_pr.py: removed unused import statements
remove: datos/temp/: cleaned temporary files
```

---

### 🔀 `merge` - Fusión

Para commits de merge entre ramas.

**Formato:**
```
merge: <rama origen> -> <rama destino>: <descripción>
```

**Ejemplos:**
```
merge: feature/magnetometry -> main: integrated magnetic analysis
merge: bugfix/gossan-calculation -> develop: fixed gossan index
```

---

## 📏 Reglas Generales

### ✅ Buenos Commits

1. **Descriptivos y concisos:** Explican QUÉ se hizo y POR QUÉ
2. **En inglés:** Mantener consistencia en el proyecto
3. **Tiempo presente:** "add" no "added", "fix" no "fixed"
4. **Específicos:** Mencionar el archivo o módulo afectado
5. **Atómicos:** Un commit = un cambio lógico

### ❌ Malos Commits

```
❌ update stuff
❌ fixing things
❌ WIP
❌ asdfgh
❌ minor changes
```

### ✅ Buenos Ejemplos Completos

```
✅ bugfix: terraf_pr.py: fixed band loading error when B7 missing

The calcular_gossan method was failing when B7 band was not present
in the dataset. Added validation check before calculation.

✅ feature: terraf_pr.py: added NDVI vegetation index calculation

Implemented NDVI calculation to filter vegetated areas from mineral
analysis. Includes automatic classification into 4 vegetation density
levels.

✅ docs: README.md: updated installation section with conda environment

Added detailed instructions for installing the complete environment
using the conda/environment.yml file.
```

---

## 🔄 Flujo de Trabajo con Git

### 1. Antes de hacer commit

```bash
# Ver cambios
git status
git diff

# Agregar archivos específicos
git add src/terraf_pr.py
git add docs/README.md
```

### 2. Hacer commit siguiendo la convención

```bash
git commit -m "bugfix: terraf_pr.py: fixed division by zero in gossan index"
```

### 3. Para commits más detallados

```bash
git commit
# Se abrirá el editor para escribir mensaje completo
```

Formato en el editor:
```
bugfix: terraf_pr.py: fixed division by zero in gossan index

The calculation was failing when B6 band had zero values.
Added np.divide with where parameter to handle zeros safely.

Fixes #15
```

---

## 🏷️ Referencias a Issues

Cuando el commit resuelve un issue de GitHub:

```
bugfix: terraf_pr.py: fixed band loading for Level-2 products

Closes #23
Fixes #24
Resolves #25
```

---

## 🌳 Estructura de Ramas

- `main` - Código de producción estable
- `develop` - Rama de desarrollo principal
- `feature/<nombre>` - Nuevas características
- `bugfix/<nombre>` - Corrección de bugs
- `hotfix/<nombre>` - Correcciones urgentes en producción

---

## 📊 Ejemplos por Módulo

### Percepción Remota (terraf_pr)
```
feature: terraf_pr: added propilitica alteration detection
bugfix: terraf_pr: fixed RGB composition band ordering
refactor: terraf_pr: extracted visualization to separate class
test: pruebas.py: added tests for all spectral indices
```

### Magnetometría (futuro)
```
feature: magnetometry: implemented magnetic field reduction
bugfix: magnetometry: corrected IGRF model calculation
docs: magnetometry: added processing workflow documentation
```

### Gravimetría (futuro)
```
feature: gravity: added terrain correction algorithm
refactor: gravity: modularized anomaly calculation
test: gravity: created unit tests for Bouguer correction
```

---

## 🎓 Recursos Adicionales

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Git Best Practices](https://git-scm.com/book/en/v2/Git-Basics-Git-Branching)

---

**Nota:** Estas convenciones ayudan a mantener un historial de Git limpio, profesional y fácil de seguir. Facilitan la generación automática de changelogs y la comprensión de los cambios del proyecto.

---

*Última actualización: Noviembre 2025*
