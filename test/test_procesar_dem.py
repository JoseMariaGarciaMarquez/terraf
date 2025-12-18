"""
Procesamiento de DEM para región de magnetometría

Funciones:
- Lectura de GeoTIFF
- Cálculo de pendientes
- Cálculo de aspecto
- Hillshade
- Perfiles de elevación
- Exportación a formatos compatibles
"""

import rasterio
from rasterio.plot import show
import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage
from pathlib import Path

def procesar_dem(dem_path):
    """Procesa un archivo DEM"""
    print(f"📂 Procesando: {dem_path}")
    
    with rasterio.open(dem_path) as src:
        dem = src.read(1)
        meta = src.meta
        
        # Reemplazar nodata
        nodata = src.nodata
        if nodata is not None:
            dem = np.where(dem == nodata, np.nan, dem)
        
        print(f"   • Tamaño: {dem.shape}")
        print(f"   • Elevación: {np.nanmin(dem):.1f} - {np.nanmax(dem):.1f} m")
        print(f"   • Resolución: {src.res[0]:.1f} m")
        
        # Calcular pendiente
        dy, dx = np.gradient(dem)
        slope = np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))
        
        # Calcular aspecto
        aspect = np.degrees(np.arctan2(-dx, dy))
        aspect = (aspect + 360) % 360
        
        # Hillshade
        azimuth = 315  # Dirección de iluminación
        altitude = 45  # Ángulo de iluminación
        
        az_rad = np.radians(azimuth)
        alt_rad = np.radians(altitude)
        
        hillshade = (np.cos(alt_rad) * np.cos(np.radians(slope)) +
                    np.sin(alt_rad) * np.sin(np.radians(slope)) *
                    np.cos(az_rad - np.radians(aspect)))
        
        hillshade = (hillshade * 255).astype(np.uint8)
        
        # Visualizar
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # DEM
        im1 = axes[0, 0].imshow(dem, cmap='terrain')
        axes[0, 0].set_title('Elevación', fontsize=14, fontweight='bold')
        plt.colorbar(im1, ax=axes[0, 0], label='Metros')
        
        # Pendiente
        im2 = axes[0, 1].imshow(slope, cmap='YlOrRd', vmin=0, vmax=30)
        axes[0, 1].set_title('Pendiente', fontsize=14, fontweight='bold')
        plt.colorbar(im2, ax=axes[0, 1], label='Grados')
        
        # Aspecto
        im3 = axes[1, 0].imshow(aspect, cmap='hsv', vmin=0, vmax=360)
        axes[1, 0].set_title('Aspecto', fontsize=14, fontweight='bold')
        plt.colorbar(im3, ax=axes[1, 0], label='Grados')
        
        # Hillshade
        axes[1, 1].imshow(hillshade, cmap='gray')
        axes[1, 1].set_title('Hillshade', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        output_path = Path(dem_path).parent / f"{Path(dem_path).stem}_procesado.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"   ✅ Visualización guardada: {output_path}")
        
        return dem, slope, aspect, hillshade, meta

if __name__ == '__main__':
    # Buscar archivos DEM
    topo_dir = Path("datos/topografia")
    dem_files = list(topo_dir.glob("*.tif"))
    
    if not dem_files:
        print("⚠️ No hay archivos DEM en datos/topografia/")
        print("Descarga primero un DEM usando las instrucciones.")
    else:
        for dem_file in dem_files:
            procesar_dem(dem_file)
