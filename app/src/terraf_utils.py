"""
TERRAF Utils - Utilidades Reutilizables
========================================
Funciones centralizadas para evitar código repetido
"""

import numpy as np
from typing import Tuple, Optional
import warnings

# ============================================================================
# CONVERSIÓN DE COORDENADAS
# ============================================================================

def extraer_coordenadas_geometrias(geometrias) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extrae coordenadas X, Y de geometrías de manera centralizada.
    
    Args:
        geometrias: GeoSeries con geometrías (Points, Polygons, etc.)
    
    Returns:
        tuple: (x_coords, y_coords) como arrays numpy
    """
    try:
        # Calcular centroides si son polígonos
        if hasattr(geometrias.iloc[0], 'centroid'):
            centroids = geometrias.centroid
            x = centroids.x.values
            y = centroids.y.values
        else:
            # Si son puntos directamente
            x = geometrias.x.values
            y = geometrias.y.values
        
        return x, y
    
    except Exception as e:
        raise ValueError(f"Error extrayendo coordenadas: {e}")


def transformar_coordenadas(x, y, crs_origen, crs_destino='EPSG:4326'):
    """
    Transforma coordenadas de un CRS a otro.
    
    Args:
        x: Array de coordenadas X
        y: Array de coordenadas Y
        crs_origen: CRS de origen (ej: 'EPSG:32613')
        crs_destino: CRS de destino (default: WGS84)
    
    Returns:
        tuple: (x_transformado, y_transformado)
    """
    try:
        from pyproj import Transformer
        
        transformer = Transformer.from_crs(crs_origen, crs_destino, always_xy=True)
        x_trans, y_trans = transformer.transform(x, y)
        
        return x_trans, y_trans
    
    except Exception as e:
        warnings.warn(f"Error transformando coordenadas: {e}. Retornando originales.")
        return x, y


def obtener_bounds_geometrias(geometrias, crs=None, target_crs='EPSG:4326'):
    """
    Obtiene bounds (bounding box) de geometrías en CRS especificado.
    
    Args:
        geometrias: GeoSeries con geometrías
        crs: CRS de las geometrías (si None, se asume que ya están en target_crs)
        target_crs: CRS objetivo para los bounds
    
    Returns:
        tuple: (min_lon, min_lat, max_lon, max_lat)
    """
    try:
        x, y = extraer_coordenadas_geometrias(geometrias)
        
        # Transformar si es necesario
        if crs is not None and str(crs) != target_crs:
            x, y = transformar_coordenadas(x, y, str(crs), target_crs)
        
        return np.min(x), np.min(y), np.max(x), np.max(y)
    
    except Exception as e:
        warnings.warn(f"Error obteniendo bounds: {e}")
        return None


# ============================================================================
# INTERPOLACIÓN Y GRIDS
# ============================================================================

def crear_grid_regular(x, y, resolution=100):
    """
    Crea grid regular para interpolación.
    
    Args:
        x: Coordenadas X
        y: Coordenadas Y
        resolution: Número de puntos en el grid
    
    Returns:
        tuple: (Xi, Yi) meshgrid
    """
    xi = np.linspace(np.nanmin(x), np.nanmax(x), resolution)
    yi = np.linspace(np.nanmin(y), np.nanmax(y), resolution)
    Xi, Yi = np.meshgrid(xi, yi)
    
    return Xi, Yi


def interpolar_a_grid(x, y, valores, resolution=100, method='cubic'):
    """
    Interpola valores irregulares a grid regular.
    
    Args:
        x: Coordenadas X
        y: Coordenadas Y
        valores: Valores a interpolar
        resolution: Resolución del grid
        method: Método de interpolación ('linear', 'cubic', 'nearest')
    
    Returns:
        tuple: (Xi, Yi, Zi) - Grid con valores interpolados
    """
    from scipy.interpolate import griddata
    
    # Crear grid
    Xi, Yi = crear_grid_regular(x, y, resolution)
    
    # Interpolar
    Zi = griddata((x, y), valores, (Xi, Yi), method=method, fill_value=np.nan)
    
    return Xi, Yi, Zi


def interpolar_desde_grid(Xi, Yi, Zi, x_target, y_target, method='linear'):
    """
    Interpola desde grid regular a puntos irregulares.
    
    Args:
        Xi, Yi: Meshgrid de coordenadas
        Zi: Valores en el grid
        x_target, y_target: Puntos objetivo
        method: Método de interpolación
    
    Returns:
        np.ndarray: Valores interpolados
    """
    from scipy.interpolate import griddata
    
    valores = griddata(
        (Xi.flatten(), Yi.flatten()),
        Zi.flatten(),
        (x_target, y_target),
        method=method,
        fill_value=np.nan
    )
    
    return valores


# ============================================================================
# MÁSCARAS Y FILTRADO
# ============================================================================

def crear_mascara_valida(*arrays):
    """
    Crea máscara de datos válidos para múltiples arrays.
    
    Args:
        *arrays: Arrays numpy a verificar
    
    Returns:
        np.ndarray: Máscara booleana (True = válido)
    """
    if len(arrays) == 0:
        raise ValueError("Se requiere al menos un array")
    
    mask = np.ones(arrays[0].shape, dtype=bool)
    
    for arr in arrays:
        mask &= ~np.isnan(arr)
        mask &= ~np.isinf(arr)
        if np.issubdtype(arr.dtype, np.number):
            mask &= (arr != 0)
    
    return mask


def aplicar_mascara(*arrays, mask=None, fill_value=np.nan):
    """
    Aplica máscara a múltiples arrays.
    
    Args:
        *arrays: Arrays a enmascarar
        mask: Máscara booleana (si None, se calcula automáticamente)
        fill_value: Valor para rellenar donde mask=False
    
    Returns:
        list: Arrays enmascarados
    """
    if mask is None:
        mask = crear_mascara_valida(*arrays)
    
    resultado = []
    for arr in arrays:
        arr_masked = arr.copy()
        arr_masked[~mask] = fill_value
        resultado.append(arr_masked)
    
    return resultado if len(resultado) > 1 else resultado[0]


# ============================================================================
# ESTADÍSTICAS RÁPIDAS
# ============================================================================

def calcular_estadisticas_basicas(datos, nombre="datos"):
    """
    Calcula estadísticas básicas de manera consistente.
    
    Args:
        datos: Array numpy
        nombre: Nombre descriptivo
    
    Returns:
        dict: Diccionario con estadísticas
    """
    datos_validos = datos[~np.isnan(datos) & ~np.isinf(datos)]
    
    if len(datos_validos) == 0:
        return {
            'nombre': nombre,
            'n_validos': 0,
            'n_total': len(datos)
        }
    
    return {
        'nombre': nombre,
        'n_total': len(datos),
        'n_validos': len(datos_validos),
        'n_nulos': len(datos) - len(datos_validos),
        'min': np.min(datos_validos),
        'max': np.max(datos_validos),
        'mean': np.mean(datos_validos),
        'median': np.median(datos_validos),
        'std': np.std(datos_validos),
        'percentil_25': np.percentile(datos_validos, 25),
        'percentil_75': np.percentile(datos_validos, 75),
        'rango': np.max(datos_validos) - np.min(datos_validos)
    }


# ============================================================================
# NORMALIZACIÓN
# ============================================================================

def normalizar_array(arr, metodo='minmax', percentiles=(2, 98)):
    """
    Normaliza array de manera centralizada.
    
    Args:
        arr: Array numpy
        metodo: 'minmax', 'zscore', 'percentile'
        percentiles: Percentiles para método 'percentile'
    
    Returns:
        np.ndarray: Array normalizado
    """
    arr_valido = arr[~np.isnan(arr) & ~np.isinf(arr)]
    
    if len(arr_valido) == 0:
        return arr
    
    if metodo == 'minmax':
        vmin, vmax = np.min(arr_valido), np.max(arr_valido)
        arr_norm = (arr - vmin) / (vmax - vmin) if vmax != vmin else arr * 0
    
    elif metodo == 'zscore':
        mean, std = np.mean(arr_valido), np.std(arr_valido)
        arr_norm = (arr - mean) / std if std != 0 else arr * 0
    
    elif metodo == 'percentile':
        p_low, p_high = np.percentile(arr_valido, percentiles)
        arr_norm = np.clip((arr - p_low) / (p_high - p_low), 0, 1)
    
    else:
        raise ValueError(f"Método '{metodo}' no soportado")
    
    return arr_norm
