"""
Tests unitarios para validar el cálculo correcto de áreas
Relacionado con Issue #26: Validación y corrección de cálculo de áreas
"""

import unittest
import numpy as np
import sys
from pathlib import Path

# Agregar src al path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from terraf_pr import TerrafPR
from reporte_md import ReporteMarkdown


class TestCalculoAreas(unittest.TestCase):
    """Tests para verificar que los cálculos de área son correctos"""
    
    @classmethod
    def setUpClass(cls):
        """Cargar datos de prueba una vez para todos los tests"""
        datos_path = Path(__file__).parent.parent / 'datos' / 'landsat9' / 'coleccion-1' / 'LC09_L1TP_031040_20251108_20251108_02_T1'
        
        if not datos_path.exists():
            raise unittest.SkipTest("Datos de prueba no disponibles")
        
        cls.pr = TerrafPR(str(datos_path), nombre="TestAreas")
        cls.pr.cargar_bandas(reducir=True, factor=4)
        cls.pr.calcular_gossan()
        cls.pr.calcular_ratio_oxidos()
        cls.pr.calcular_ratio_argilica()
        cls.pr.calcular_propilitica()
        
        cls.reporte = ReporteMarkdown(cls.pr, autor="Test", titulo_proyecto="Test")
    
    def test_formula_area_correcta(self):
        """Verifica que la fórmula de cálculo de área es correcta"""
        # Zona de prueba sintética
        zona_test = np.zeros((100, 100), dtype=bool)
        zona_test[25:75, 25:75] = True  # 2500 píxeles = 50x50
        
        n_pixeles = np.sum(zona_test)
        resolucion = 30  # metros
        area_esperada = n_pixeles * (resolucion ** 2) / 1e6  # km²
        
        # Verificar
        self.assertEqual(n_pixeles, 2500)
        self.assertAlmostEqual(area_esperada, 2.25, places=2)  # 2.25 km²
    
    def test_areas_siempre_positivas(self):
        """Verifica que todas las áreas calculadas son positivas"""
        zonas_a_probar = ['zona_gossan', 'zona_argilica', 'zona_oxidos', 'zona_propilitica']
        
        for zona_key in zonas_a_probar:
            if zona_key in self.pr.zonas:
                area = self.reporte._calcular_area(zona_key)
                self.assertGreaterEqual(
                    area, 0.0,
                    f"El área de {zona_key} debe ser positiva, pero es {area:.2f} km²"
                )
    
    def test_area_gossan_positiva(self):
        """Test específico para el bug reportado en Issue #26"""
        if 'zona_gossan' not in self.pr.zonas:
            self.skipTest("zona_gossan no calculada")
        
        area_gossan = self.reporte._calcular_area('zona_gossan')
        
        # El bug reportaba -559.12 km², debe ser positivo
        self.assertGreater(
            area_gossan, 0,
            f"Área gossan debe ser positiva, pero es {area_gossan:.2f} km²"
        )
        
        # Verificar que es un valor razonable (no infinito ni NaN)
        self.assertFalse(np.isnan(area_gossan))
        self.assertFalse(np.isinf(area_gossan))
    
    def test_area_oxidos_positiva(self):
        """Test específico para óxidos (también reportado en Issue #26)"""
        if 'zona_oxidos' not in self.pr.zonas:
            self.skipTest("zona_oxidos no calculada")
        
        area_oxidos = self.reporte._calcular_area('zona_oxidos')
        
        # El bug reportaba -1117.93 km², debe ser positivo
        self.assertGreater(
            area_oxidos, 0,
            f"Área óxidos debe ser positiva, pero es {area_oxidos:.2f} km²"
        )
    
    def test_consistencia_calculo_manual(self):
        """Verifica que el cálculo manual coincide con la función"""
        if 'zona_gossan' not in self.pr.zonas:
            self.skipTest("zona_gossan no calculada")
        
        zona = self.pr.zonas['zona_gossan']
        
        # Cálculo manual
        n_pixeles = np.sum(zona)
        resolucion = self.pr.metadatos.get('resolution', 30)
        area_manual = n_pixeles * (resolucion ** 2) / 1e6
        
        # Cálculo con función
        area_funcion = self.reporte._calcular_area('zona_gossan')
        
        # Deben ser iguales
        self.assertAlmostEqual(
            area_manual, area_funcion,
            places=2,
            msg=f"Cálculo manual ({area_manual:.2f}) != función ({area_funcion:.2f})"
        )
    
    def test_zona_vacia_retorna_cero(self):
        """Verifica que una zona vacía retorna 0 km²"""
        area = self.reporte._calcular_area('zona_inexistente')
        self.assertEqual(area, 0.0)
    
    def test_tipo_dato_zona_es_booleano(self):
        """Verifica que las zonas son arrays booleanos"""
        for zona_key, zona in self.pr.zonas.items():
            self.assertEqual(
                zona.dtype, np.bool_,
                f"{zona_key} debe ser bool, pero es {zona.dtype}"
            )
    
    def test_resolucion_es_positiva(self):
        """Verifica que la resolución es un valor positivo"""
        resolucion = self.pr.metadatos.get('resolution', 30)
        self.assertGreater(resolucion, 0)
        self.assertIsInstance(resolucion, (int, float))
    
    def test_zonas_tienen_misma_dimension(self):
        """Verifica que todas las zonas tienen las mismas dimensiones"""
        if len(self.pr.zonas) < 2:
            self.skipTest("No hay suficientes zonas para comparar")
        
        shapes = [zona.shape for zona in self.pr.zonas.values()]
        primera_shape = shapes[0]
        
        for shape in shapes[1:]:
            self.assertEqual(
                shape, primera_shape,
                "Todas las zonas deben tener las mismas dimensiones"
            )


if __name__ == '__main__':
    # Ejecutar tests con output verbose
    unittest.main(verbosity=2)
