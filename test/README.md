# TERRAF - Scripts de Test

Scripts consolidados y organizados por tema.

## 📁 Estructura

```
test/
├── icesat2_utils.py          # Todo ICESat-2 (descarga, filtrado, vegetación)
├── landsat_utils.py           # Todo Landsat (descarga, índices, ratios minerales)
├── magnetometria_utils.py     # Magnetometría (análisis, anomalías)
├── mapas_interactivos.py      # Mapas web interactivos con Folium
└── old_scripts/               # Scripts antiguos (respaldo)
```

## 🚀 Uso Rápido

### ICESat-2
```python
from icesat2_utils import filtrar_region, analizar_vegetacion

# Filtrar datos por shapefile
df = filtrar_region(shapefile='datos/magnetometria/Carta/.../shapefile.shp')

# Análisis
analizar_vegetacion(df)
```

### Landsat
```python
from landsat_utils import listar_escenas, visualizar_analisis_completo

# Listar escenas disponibles
escenas = listar_escenas()

# Análisis completo (RGB, índices, ratios minerales)
escena_id, info = list(escenas.items())[0]
visualizar_analisis_completo(escena_id, info['bandas'])
```

### Magnetometría
```python
from magnetometria_utils import cargar_magnetometria, detectar_anomalias

# Cargar y analizar
df = cargar_magnetometria('datos/magnetometria/.../shapefile.shp')
anomalias = detectar_anomalias(df, umbral_codigo=10)
```

### Mapas Interactivos
```python
from mapas_interactivos import crear_mapa_landsat_mineral

# Crear mapa con todo integrado
mapa = crear_mapa_landsat_mineral()
```

## 🎯 Ventajas

- ✅ **1 archivo por tema** en lugar de 20+ scripts dispersos
- ✅ **Funciones reutilizables** en lugar de código duplicado
- ✅ **Documentación integrada** con docstrings
- ✅ **Ejecutables standalone** (cada script funciona por sí solo)
- ✅ **Importables como módulos** para scripts más complejos

## 📝 Notas

Los scripts antiguos están en `old_scripts/` por si necesitas consultar algo específico.
Todos los nuevos scripts son compatibles con los datos existentes.
