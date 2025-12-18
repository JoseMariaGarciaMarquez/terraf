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
from reporte_md import ReporteMarkdown

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

# 6. Composiciones RGB
print("\n🎨 PRUEBA 6: Composiciones RGB")
print("-"*80)
print("  • Color Natural")
pr.show('natural_color', guardar=True, nombre_archivo=str(resultados_path / '06_natural_color.png'))
print("  • Falso Color")
pr.show('false_color', guardar=True, nombre_archivo=str(resultados_path / '07_false_color.png'))
print("  • Color Geológico")
pr.show('geology_color', guardar=True, nombre_archivo=str(resultados_path / '08_geology_color.png'))

# 7. Índice de Alteración Hidrotermal
print("\n🔬 PRUEBA 7: Índice de Alteración Hidrotermal (IAH)")
print("-"*80)
pr.calcular_iah()
pr.show('iah', guardar=True, nombre_archivo=str(resultados_path / '09_iah.png'))

# 8. Ratio OH (Hidróxilos)
print("\n💧 PRUEBA 8: Ratio OH (Minerales Hidróxilos)")
print("-"*80)
pr.calcular_ratio_oh()
pr.show('oh', guardar=True, nombre_archivo=str(resultados_path / '10_ratio_oh.png'))

# 9. Objetivos Prioritarios (Triple Coincidencia)
print("\n🎯 PRUEBA 9: Objetivos Prioritarios (Triple Coincidencia)")
print("-"*80)
pr.identificar_objetivos()
pr.show('objetivos', guardar=True, nombre_archivo=str(resultados_path / '11_objetivos_prioritarios.png'))

# Resumen final
print("\n" + "="*80)
pr.resumen()
print(f"\n✅ Resultados guardados en: {resultados_path}")

# Generar reporte Markdown
print("\n" + "="*80)
print("📄 GENERANDO REPORTE TÉCNICO")
print("="*80)

reporte = ReporteMarkdown(pr, autor="José García", titulo_proyecto="Análisis Espectral - Hércules")
reporte.generar_reporte_completo(str(resultados_path / "reporte_hercules_completo.md"))

# Generar también teoría y resultados por separado
print("\n📚 Generando documentos adicionales...")
reporte.generar_teoria(str(resultados_path / "teoria_gossan.md"))
reporte.generar_resultados(str(resultados_path / "resultados_hercules.md"))

print("\n" + "="*80)
print("📊 ESTADÍSTICAS FINALES")
print("="*80)
print(f"  📁 Total de archivos generados: 14")
print(f"  🖼️  Imágenes: 11")
print(f"  📄 Reportes: 3")
print(f"  📂 Ubicación: {resultados_path}")
print("\n✅ ¡Análisis completo! Revisa los archivos en la carpeta resultados/")
print("\n¡Gracias por usar TerrafPR para tus análisis geoespaciales!")