"""
Test para verificar que las áreas se calculan correctamente
"""

import sys
from pathlib import Path

# Agregar src al path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from terraf_pr import TerrafPR
from reporte_md import ReporteMarkdown

# Cargar datos
datos_path = Path(__file__).parent.parent / 'datos' / 'landsat9' / 'coleccion-1' / 'LC09_L1TP_031040_20251108_20251108_02_T1'
resultados_path = Path(__file__).parent.parent / 'resultados'

print("🧪 Test de corrección de áreas\n")
print("=" * 70)

# Análisis
pr = TerrafPR(str(datos_path), nombre="HerculesFixed")
pr.cargar_bandas(reducir=True, factor=4)
pr.calcular_gossan()
pr.calcular_ratio_oxidos()
pr.calcular_ratio_argilica()
pr.calcular_propilitica()

print("\n📊 Áreas calculadas directamente desde TerrafPR:")
print(f"   Gossan: {pr.metadatos.get('area_gossan', 'N/A')} km²")
print(f"   Óxidos: {pr.metadatos.get('area_oxidos', 'N/A')} km²")
print(f"   Argílica: {pr.metadatos.get('area_argilica', 'N/A')} km²")

# Generar reporte
print("\n📝 Generando reporte...")
reporte = ReporteMarkdown(pr, autor="Test Automatizado", titulo_proyecto="Verificación de Áreas")

# Calcular áreas manualmente desde el reporte
from reporte_md import np
area_gossan = reporte._calcular_area('zona_gossan')
area_oxidos = reporte._calcular_area('zona_oxidos')
area_argilica = reporte._calcular_area('zona_argilica')

print(f"\n📊 Áreas calculadas desde ReporteMarkdown:")
print(f"   Gossan: {area_gossan:.2f} km²")
print(f"   Óxidos: {area_oxidos:.2f} km²")
print(f"   Argílica: {area_argilica:.2f} km²")

# Verificar signos
if area_gossan < 0 or area_oxidos < 0 or area_argilica < 0:
    print(f"\n❌ ¡ERROR! Áreas negativas detectadas")
else:
    print(f"\n✅ Todas las áreas son positivas")

# Generar reporte completo
output_file = resultados_path / "test_areas_fixed.md"
reporte.generar_resultados(str(output_file))

print(f"\n📄 Reporte generado en: {output_file}")
print("\n" + "=" * 70)
print("✨ Test completado")
