"""
Archivo de pruebas para TerrafPR
Prueba de nuevos índices minerales 
para terraf
"""

import sys
from pathlib import Path

# Agregar el directorio src al path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from terraf_pr import TerrafPR

print("="*80)
print("🧪 PRUEBAS DE ÍNDICES AVANZADOS ")
print("="*80)

# Definir carpetas
datos_path = Path(__file__).parent.parent / 'datos' / 'landsat9' / 'coleccion-1' / 'LC09_L1TP_031040_20251108_20251108_02_T1'
resultados_path = Path(__file__).parent.parent / 'resultados'

# Crear carpeta de resultados si no existe
resultados_path.mkdir(exist_ok=True)

# Crear instancia
pr = TerrafPR(str(datos_path), nombre="Hercules")

# Cargar bandas
pr.cargar_bandas(reducir=True, factor=4)

# 1. GOSSAN - Alta prioridad para sulfuros
print("\n🎯 PRUEBA 1: Índice GOSSAN (Alta Prioridad)")
print("-"*80)
pr.calcular_gossan()
pr.show('gossan', guardar=True, nombre_archivo=str(resultados_path / '01_gossan.png'))

# 2. Alteración propilítica
print("\n🌿 PRUEBA 2: Alteración Propilítica")
print("-"*80)
pr.calcular_propilitica()
pr.show('propilitica', guardar=True, nombre_archivo=str(resultados_path / '02_propilitica.png'))

# 3. NDVI para filtrar vegetación
print("\n🌱 PRUEBA 3: Índice de Vegetación NDVI")
print("-"*80)
pr.calcular_ndvi()
pr.show('ndvi', guardar=True, nombre_archivo=str(resultados_path / '03_ndvi.png'))

# 4. Carbonatos
print("\n🪨 PRUEBA 4: Índice de Carbonatos")
print("-"*80)
pr.calcular_carbonatos()
pr.show('carbonatos', guardar=True, nombre_archivo=str(resultados_path / '04_carbonatos.png'))

# 5. Arcillas mejorado
print("\n🟤 PRUEBA 5: Índice de Arcillas Mejorado")
print("-"*80)
pr.calcular_clay_index()
pr.show('clay_index', guardar=True, nombre_archivo=str(resultados_path / '05_clay_index.png'))

# Resumen final
print("\n" + "="*80)
pr.resumen()
print(f"\n✅ Resultados guardados en: {resultados_path}")
