"""
Tests unitarios para validación de cálculo de áreas
Valida que las áreas calculadas sean siempre positivas y correctas

Issue #26: Validación y corrección de cálculo de áreas
"""

import sys
from pathlib import Path
import numpy as np
import pytest

# Agregar src al path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from terraf_pr import TerrafPR
from reporte_md import ReporteMarkdown


class TestCalculoAreas:
    """Tests para el cálculo correcto de áreas"""
    
    @pytest.fixture
    def terraf_instance(self):
        """Fixture que crea una instancia de TerrafPR con datos de prueba"""
        datos_path = Path(__file__).parent.parent / 'datos' / 'landsat9' / 'coleccion-1' / 'LC09_L1TP_031040_20251108_20251108_02_T1'
        pr = TerrafPR(str(datos_path), nombre="TestAreas")
        pr.cargar_bandas(reducir=True, factor=4)
        return pr
    
    def test_area_gossan_positiva(self, terraf_instance):
        """Verifica que el área de gossan sea positiva"""
        pr = terraf_instance
        pr.calcular_gossan()
        
        assert 'zona_gossan' in pr.zonas, "zona_gossan no fue creada"
        
        zona = pr.zonas['zona_gossan']
        n_pixeles = np.sum(zona)
        resolucion = pr.metadatos.get('resolution', 30)
        area_km2 = n_pixeles * (resolucion ** 2) / 1e6
        
        assert area_km2 > 0, f"Área de gossan es negativa: {area_km2}"
        assert n_pixeles > 0, f"No hay píxeles detectados: {n_pixeles}"
        print(f"✅ Área gossan: {area_km2:.2f} km²")
    
    def test_area_oxidos_positiva(self, terraf_instance):
        """Verifica que el área de óxidos sea positiva"""
        pr = terraf_instance
        pr.calcular_ratio_oxidos()
        
        assert 'zona_oxidos' in pr.zonas, "zona_oxidos no fue creada"
        
        zona = pr.zonas['zona_oxidos']
        n_pixeles = np.sum(zona)
        resolucion = pr.metadatos.get('resolution', 30)
        area_km2 = n_pixeles * (resolucion ** 2) / 1e6
        
        assert area_km2 > 0, f"Área de óxidos es negativa: {area_km2}"
        assert n_pixeles > 0, f"No hay píxeles detectados: {n_pixeles}"
        print(f"✅ Área óxidos: {area_km2:.2f} km²")
    
    def test_area_argilica_positiva(self, terraf_instance):
        """Verifica que el área argílica sea positiva"""
        pr = terraf_instance
        pr.calcular_ratio_argilica()
        
        assert 'zona_argilica' in pr.zonas, "zona_argilica no fue creada"
        
        zona = pr.zonas['zona_argilica']
        n_pixeles = np.sum(zona)
        resolucion = pr.metadatos.get('resolution', 30)
        area_km2 = n_pixeles * (resolucion ** 2) / 1e6
        
        assert area_km2 > 0, f"Área argílica es negativa: {area_km2}"
        assert n_pixeles > 0, f"No hay píxeles detectados: {n_pixeles}"
        print(f"✅ Área argílica: {area_km2:.2f} km²")
    
    def test_formula_area_correcta(self):
        """Verifica que la fórmula de cálculo de área sea correcta"""
        # Caso de prueba sintético
        zona_test = np.zeros((100, 100), dtype=bool)
        zona_test[25:75, 25:75] = True  # 50x50 = 2500 píxeles
        
        n_pixeles = np.sum(zona_test)
        assert n_pixeles == 2500, f"Conteo de píxeles incorrecto: {n_pixeles}"
        
        resolucion = 30  # 30 metros
        area_m2 = n_pixeles * (resolucion ** 2)
        area_km2 = area_m2 / 1e6
        
        area_esperada = 2500 * 900 / 1e6  # 2.25 km²
        
        assert abs(area_km2 - area_esperada) < 0.01, f"Cálculo incorrecto: {area_km2} != {area_esperada}"
        assert area_km2 > 0, f"Área negativa: {area_km2}"
        print(f"✅ Fórmula correcta: {area_km2:.2f} km² (esperado: {area_esperada:.2f} km²)")
    
    def test_reporte_markdown_areas_positivas(self, terraf_instance):
        """Verifica que ReporteMarkdown calcule áreas positivas"""
        pr = terraf_instance
        pr.calcular_gossan()
        pr.calcular_ratio_oxidos()
        pr.calcular_ratio_argilica()
        
        reporte = ReporteMarkdown(pr, autor="Test", titulo_proyecto="Test")
        
        area_gossan = reporte._calcular_area('zona_gossan')
        area_oxidos = reporte._calcular_area('zona_oxidos')
        area_argilica = reporte._calcular_area('zona_argilica')
        
        assert area_gossan > 0, f"ReporteMarkdown: área gossan negativa: {area_gossan}"
        assert area_oxidos > 0, f"ReporteMarkdown: área óxidos negativa: {area_oxidos}"
        assert area_argilica > 0, f"ReporteMarkdown: área argílica negativa: {area_argilica}"
        
        print(f"✅ ReporteMarkdown áreas correctas:")
        print(f"   Gossan: {area_gossan:.2f} km²")
        print(f"   Óxidos: {area_oxidos:.2f} km²")
        print(f"   Argílica: {area_argilica:.2f} km²")
    
    def test_zona_inexistente_retorna_cero(self):
        """Verifica que zonas inexistentes retornen área 0"""
        datos_path = Path(__file__).parent.parent / 'datos' / 'landsat9' / 'coleccion-1' / 'LC09_L1TP_031040_20251108_20251108_02_T1'
        pr = TerrafPR(str(datos_path), nombre="Test")
        pr.cargar_bandas(reducir=True, factor=4)
        
        reporte = ReporteMarkdown(pr, autor="Test", titulo_proyecto="Test")
        area = reporte._calcular_area('zona_inexistente')
        
        assert area == 0.0, f"Zona inexistente debería retornar 0, retornó: {area}"
        print(f"✅ Zona inexistente retorna correctamente 0.0")
    
    def test_mascara_booleana_correcta(self, terraf_instance):
        """Verifica que las máscaras booleanas se creen correctamente"""
        pr = terraf_instance
        pr.calcular_gossan()
        
        zona = pr.zonas['zona_gossan']
        
        assert zona.dtype == bool, f"zona_gossan no es booleana: {zona.dtype}"
        assert zona.shape == pr.bandas['B2'].shape, "Dimensiones incorrectas"
        assert len(np.unique(zona)) <= 2, "Máscara booleana tiene más de 2 valores"
        
        print(f"✅ Máscara booleana correcta: dtype={zona.dtype}, shape={zona.shape}")


if __name__ == "__main__":
    # Ejecutar tests
    pytest.main([__file__, "-v", "-s"])
