"""
TERRAF - Utilidades Landsat
============================

Script unificado para:
1. Descarga Landsat 9 (earthaccess)
2. Procesamiento de bandas
3. Índices espectrales (NDVI, NDWI)
4. Análisis mineral (ratios, gossan, alteración)
5. Visualización y exportación

Autor: TERRAF
Fecha: 5 de diciembre de 2025
"""

import numpy as np
import matplotlib.pyplot as plt
import rasterio
from pathlib import Path
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import earthaccess

# =============================================================================
# DESCARGA
# =============================================================================

def descargar_landsat(bbox, fecha_inicio, fecha_fin, num_escenas=2, output_dir='datos/landsat9'):
    """
    Descarga escenas Landsat 9 usando earthaccess.
    
    Args:
        bbox: (lon_min, lat_min, lon_max, lat_max)
        fecha_inicio: 'YYYY-MM-DD'
        fecha_fin: 'YYYY-MM-DD'
        num_escenas: número de escenas a descargar
        output_dir: carpeta de salida
    """
    print("🛰️ Descargando Landsat 9 (HLS)...")
    
    earthaccess.login(persist=True)
    
    granules = earthaccess.search_data(
        short_name='HLSL30',
        bounding_box=bbox,
        temporal=(fecha_inicio, fecha_fin),
        cloud_cover=(0, 20)
    )
    
    print(f"📊 Encontradas {len(granules)} escenas")
    
    if granules:
        earthaccess.download(granules[:num_escenas], output_dir)
        print(f"✅ Descarga completa: {num_escenas} escenas")
    else:
        print("❌ No se encontraron escenas")


# =============================================================================
# LECTURA Y PROCESAMIENTO
# =============================================================================

def listar_escenas(landsat_dir='datos/landsat9'):
    """Lista escenas disponibles agrupadas por tile."""
    archivos = list(Path(landsat_dir).glob('*.tif'))
    
    escenas = {}
    for archivo in archivos:
        parts = archivo.stem.split('.')
        if len(parts) >= 4:
            escena_id = f"{parts[0]}.{parts[1]}.{parts[2]}.{parts[3]}"
            if escena_id not in escenas:
                escenas[escena_id] = {'bandas': {}, 'tile': parts[2], 'fecha': parts[3]}
            
            banda = parts[-1]
            if banda in ['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07']:
                escenas[escena_id]['bandas'][banda] = archivo
    
    return escenas


def leer_banda(archivo):
    """Lee banda Landsat y filtra valores inválidos."""
    with rasterio.open(archivo) as src:
        banda = src.read(1).astype(float)
        banda[banda < 0] = np.nan
        banda[banda > 10000] = np.nan
        return banda, src.transform, src.crs, src.bounds


# =============================================================================
# ÍNDICES ESPECTRALES
# =============================================================================

def calcular_ndvi(b05, b04):
    """NDVI = (NIR - Red) / (NIR + Red)"""
    return (b05 - b04) / (b05 + b04 + 1e-10)


def calcular_ndwi(b03, b05):
    """NDWI = (Green - NIR) / (Green + NIR)"""
    return (b03 - b05) / (b03 + b05 + 1e-10)


def calcular_ndbi(b06, b05):
    """NDBI = (SWIR - NIR) / (SWIR + NIR)"""
    return (b06 - b05) / (b06 + b05 + 1e-10)


# =============================================================================
# RATIOS MINERALES
# =============================================================================

def ratio_oxidos_hierro(b04, b02):
    """B04/B02 - Óxidos de hierro (hematita, goethita)"""
    ratio = b04 / (b02 + 1e-10)
    return np.clip(ratio, 0.5, 2.5)


def ratio_hidrotermal(b06, b07):
    """B06/B07 - Alteración hidrotermal (arcillas, alunita)"""
    ratio = b06 / (b07 + 1e-10)
    return np.clip(ratio, 0.8, 1.5)


def ratio_arcillas(b05, b06, b07):
    """(B05/B06) * (B06/B07) - Minerales arcillosos"""
    ratio = (b05 / (b06 + 1e-10)) * (b06 / (b07 + 1e-10))
    return np.clip(ratio, 0.5, 2.0)


def ratio_carbonatos(b07, b05):
    """B07/B05 - Carbonatos (calcita, dolomita)"""
    ratio = b07 / (b05 + 1e-10)
    return np.clip(ratio, 0.8, 1.5)


def ratio_gossan(b04, b05, b03):
    """(B04+B05)/B03 - Kaufmann ratio para gossan (caps oxidados de sulfuros)"""
    ratio = (b04 + b05) / (b03 + 1e-10)
    return np.clip(ratio, 1.0, 3.0)


def pca_mineral(bandas_dict):
    """PCA con bandas B03-B07 para detectar anomalías espectrales."""
    bandas = ['B03', 'B04', 'B05', 'B06', 'B07']
    
    # Leer y apilar bandas
    stack = []
    for banda in bandas:
        b, _, _, _ = leer_banda(bandas_dict[banda])
        stack.append(b)
    
    stack = np.array(stack)
    shape_original = stack.shape[1:]
    
    # Reshape para PCA
    stack_flat = stack.reshape(len(bandas), -1).T
    mask = ~np.isnan(stack_flat).any(axis=1)
    stack_clean = stack_flat[mask]
    
    # Normalizar y aplicar PCA
    scaler = StandardScaler()
    stack_scaled = scaler.fit_transform(stack_clean)
    
    pca = PCA(n_components=3)
    pca_result = pca.fit_transform(stack_scaled)
    
    # Reconstruir imágenes
    pcs = [np.full(shape_original.prod(), np.nan) for _ in range(3)]
    for i in range(3):
        pcs[i][mask] = pca_result[:, i]
        pcs[i] = pcs[i].reshape(shape_original)
    
    print(f"  📊 Varianza explicada: {pca.explained_variance_ratio_}")
    
    return pcs[0], pcs[1], pcs[2]


# =============================================================================
# VISUALIZACIÓN
# =============================================================================

def crear_rgb(red, green, blue):
    """Crea composición RGB normalizada."""
    rgb = np.dstack([red, green, blue]) / 10000.0
    rgb = np.clip(rgb, 0, 1)
    
    # Stretch contraste
    for i in range(3):
        canal = rgb[:, :, i]
        p2, p98 = np.nanpercentile(canal[~np.isnan(canal)], [2, 98])
        rgb[:, :, i] = np.clip((canal - p2) / (p98 - p2), 0, 1)
    
    return rgb


def visualizar_analisis_completo(escena_id, bandas_dict, output_dir='resultados/landsat'):
    """Genera visualización completa: RGB, índices y ratios minerales."""
    
    print(f"\n🎨 Visualizando: {escena_id}")
    
    # Leer bandas
    bandas = {}
    for b in ['B02', 'B03', 'B04', 'B05', 'B06', 'B07']:
        bandas[b], transform, crs, bounds = leer_banda(bandas_dict[b])
    
    # Calcular todo
    rgb_natural = crear_rgb(bandas['B04'], bandas['B03'], bandas['B02'])
    rgb_falso = crear_rgb(bandas['B05'], bandas['B04'], bandas['B03'])
    
    ndvi = calcular_ndvi(bandas['B05'], bandas['B04'])
    ndwi = calcular_ndwi(bandas['B03'], bandas['B05'])
    
    fe_oxidos = ratio_oxidos_hierro(bandas['B04'], bandas['B02'])
    gossan = ratio_gossan(bandas['B04'], bandas['B05'], bandas['B03'])
    hidrotermal = ratio_hidrotermal(bandas['B06'], bandas['B07'])
    arcillas = ratio_arcillas(bandas['B05'], bandas['B06'], bandas['B07'])
    
    pc1, pc2, pc3 = pca_mineral(bandas_dict)
    
    # Visualización 3x3
    fig, axes = plt.subplots(3, 3, figsize=(18, 18))
    
    axes[0, 0].imshow(rgb_natural)
    axes[0, 0].set_title('RGB Natural', fontweight='bold', fontsize=12)
    axes[0, 0].axis('off')
    
    axes[0, 1].imshow(rgb_falso)
    axes[0, 1].set_title('Falso Color (vegetación en rojo)', fontweight='bold', fontsize=12)
    axes[0, 1].axis('off')
    
    im = axes[0, 2].imshow(ndvi, cmap='RdYlGn', vmin=-0.5, vmax=0.8)
    axes[0, 2].set_title('NDVI', fontweight='bold', fontsize=12)
    axes[0, 2].axis('off')
    plt.colorbar(im, ax=axes[0, 2], fraction=0.046)
    
    im = axes[1, 0].imshow(fe_oxidos, cmap='YlOrRd')
    axes[1, 0].set_title('🔴 Óxidos de Hierro', fontweight='bold', fontsize=12)
    axes[1, 0].axis('off')
    plt.colorbar(im, ax=axes[1, 0], fraction=0.046)
    
    im = axes[1, 1].imshow(gossan, cmap='hot')
    axes[1, 1].set_title('🟠 Gossan (Sulfuros)', fontweight='bold', fontsize=12)
    axes[1, 1].axis('off')
    plt.colorbar(im, ax=axes[1, 1], fraction=0.046)
    
    im = axes[1, 2].imshow(hidrotermal, cmap='RdPu')
    axes[1, 2].set_title('💎 Alteración Hidrotermal', fontweight='bold', fontsize=12)
    axes[1, 2].axis('off')
    plt.colorbar(im, ax=axes[1, 2], fraction=0.046)
    
    im = axes[2, 0].imshow(arcillas, cmap='YlGnBu')
    axes[2, 0].set_title('🟤 Arcillas', fontweight='bold', fontsize=12)
    axes[2, 0].axis('off')
    plt.colorbar(im, ax=axes[2, 0], fraction=0.046)
    
    im = axes[2, 1].imshow(pc1, cmap='viridis')
    axes[2, 1].set_title('📊 PCA - Componente 1', fontweight='bold', fontsize=12)
    axes[2, 1].axis('off')
    plt.colorbar(im, ax=axes[2, 1], fraction=0.046)
    
    im = axes[2, 2].imshow(ndwi, cmap='Blues', vmin=-0.5, vmax=0.5)
    axes[2, 2].set_title('💧 NDWI (Agua)', fontweight='bold', fontsize=12)
    axes[2, 2].axis('off')
    plt.colorbar(im, ax=axes[2, 2], fraction=0.046)
    
    plt.tight_layout()
    
    # Guardar
    Path(output_dir).mkdir(exist_ok=True, parents=True)
    output_file = Path(output_dir) / f"analisis_{escena_id.split('.')[2]}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  ✅ Guardado: {output_file}")
    plt.show()


def exportar_geotiff(data, archivo_referencia, output_file):
    """Exporta array como GeoTIFF con CRS y transform de referencia."""
    with rasterio.open(archivo_referencia) as src:
        profile = src.profile.copy()
        profile.update(dtype=rasterio.float32, count=1, compress='lzw')
        
        with rasterio.open(output_file, 'w', **profile) as dst:
            dst.write(data.astype(np.float32), 1)


# =============================================================================
# MAIN - EJEMPLO DE USO
# =============================================================================

if __name__ == "__main__":
    print("="*70)
    print("🛰️ TERRAF - Análisis Landsat")
    print("="*70)
    
    # Listar escenas disponibles
    escenas = listar_escenas()
    
    print(f"\n📊 Escenas disponibles: {len(escenas)}")
    for i, (escena_id, info) in enumerate(escenas.items(), 1):
        print(f"  {i}. {info['tile']} - {info['fecha']} ({len(info['bandas'])} bandas)")
    
    # Procesar escena 1 (T13RDN)
    escena_t13rdn = [e for e in escenas.items() if 'T13RDN' in e[0]]
    
    if escena_t13rdn:
        escena_id, info = escena_t13rdn[0]
        visualizar_analisis_completo(escena_id, info['bandas'])
        
        # Exportar ratios como GeoTIFF
        print("\n💾 Exportando GeoTIFFs...")
        bandas = {}
        ref_file = None
        for b in ['B02', 'B03', 'B04', 'B05', 'B06', 'B07']:
            bandas[b], _, _, _ = leer_banda(info['bandas'][b])
            if not ref_file:
                ref_file = info['bandas'][b]
        
        gossan = ratio_gossan(bandas['B04'], bandas['B05'], bandas['B03'])
        exportar_geotiff(gossan, ref_file, 'resultados/landsat/gossan.tif')
        print("  ✅ resultados/landsat/gossan.tif")
