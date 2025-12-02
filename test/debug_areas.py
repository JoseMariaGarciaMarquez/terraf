"""
Script de debugging para investigar el problema de áreas negativas
"""

import sys
from pathlib import Path

# Agregar src al path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from terraf_pr import TerrafPR
import numpy as np

# Cargar datos
datos_path = Path(__file__).parent.parent / 'datos' / 'landsat9' / 'coleccion-1' / 'LC09_L1TP_031040_20251108_20251108_02_T1'

print("🔍 Investigando problema de áreas negativas\n")
print("=" * 70)

pr = TerrafPR(str(datos_path), nombre="Hercules_Debug")
pr.cargar_bandas(reducir=True, factor=4)

print(f"\n✅ Bandas cargadas: {list(pr.bandas.keys())}")
print(f"📐 Resolución: {pr.metadatos.get('resolution', 30)} m")
print(f"📏 Dimensiones: {pr.bandas['B2'].shape}")

# Calcular gossan
print("\n🔍 Calculando índice gossan...")
pr.calcular_gossan()

if 'gossan' in pr.indices:
    gossan = pr.indices['gossan']
    print(f"\n📊 Estadísticas del índice gossan:")
    print(f"   Shape: {gossan.shape}")
    print(f"   Min: {np.nanmin(gossan):.3f}")
    print(f"   Max: {np.nanmax(gossan):.3f}")
    print(f"   Mean: {np.nanmean(gossan):.3f}")
    print(f"   P90: {np.nanpercentile(gossan, 90):.3f}")

# Revisar zona
print(f"\n🔍 Analizando zona_gossan...")
if 'zona_gossan' in pr.zonas:
    zona = pr.zonas['zona_gossan']
    print(f"   Tipo de dato: {type(zona)}")
    print(f"   Dtype: {zona.dtype}")
    print(f"   Shape: {zona.shape}")
    print(f"   Valores únicos: {np.unique(zona)}")
    print(f"   Número de True: {np.sum(zona)}")
    print(f"   Número de False: {np.sum(~zona)}")
    
    # Calcular área manualmente
    n_pixeles = np.sum(zona)
    resolucion = pr.metadatos.get('resolution', 30)
    area_km2 = n_pixeles * (resolucion ** 2) / 1e6
    
    print(f"\n📐 Cálculo manual de área:")
    print(f"   Píxeles positivos: {n_pixeles}")
    print(f"   Resolución: {resolucion} m")
    print(f"   Resolución²: {resolucion ** 2} m²")
    print(f"   Área total: {n_pixeles * (resolucion ** 2)} m²")
    print(f"   Área en km²: {area_km2:.2f} km²")
    
    # Verificar si el área es negativa
    if area_km2 < 0:
        print(f"\n❌ ¡ÁREA NEGATIVA DETECTADA!")
        print(f"   Investigando causa...")
        print(f"   np.sum(zona) = {np.sum(zona)}")
        print(f"   type(np.sum(zona)) = {type(np.sum(zona))}")
    else:
        print(f"\n✅ Área positiva: {area_km2:.2f} km²")
else:
    print("   ❌ zona_gossan no encontrada")

# Calcular ratio_oxidos
print(f"\n🔍 Calculando ratio_oxidos...")
pr.calcular_ratio_oxidos()

if 'zona_oxidos' in pr.zonas:
    zona_oxidos = pr.zonas['zona_oxidos']
    n_pix_oxidos = np.sum(zona_oxidos)
    area_oxidos = n_pix_oxidos * (pr.metadatos.get('resolution', 30) ** 2) / 1e6
    
    print(f"   Píxeles positivos: {n_pix_oxidos}")
    print(f"   Área óxidos: {area_oxidos:.2f} km²")

print("\n" + "=" * 70)
print("\n✨ Debug completado")
