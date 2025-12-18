"""
TERRAF - Utilidades ICESat-2
==============================

Script unificado para:
1. Descarga de datos ICESat-2 (ATL08)
2. Filtrado por región
3. Análisis de vegetación
4. Visualización

Autor: TERRAF
Fecha: 5 de diciembre de 2025
"""

import h5py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import icepyx as ipx

sns.set_style("whitegrid")

# =============================================================================
# DESCARGA
# =============================================================================

def descargar_icesat2(bbox, fecha_inicio, fecha_fin, producto='ATL08', output_dir='datos/icesat2'):
    """
    Descarga datos ICESat-2.
    
    Args:
        bbox: (lon_min, lat_min, lon_max, lat_max)
        fecha_inicio: 'YYYY-MM-DD'
        fecha_fin: 'YYYY-MM-DD'
        producto: 'ATL08' (vegetación), 'ATL06' (elevación)
        output_dir: carpeta de salida
    """
    print(f"🛰️ Descargando {producto} de ICESat-2...")
    print(f"   Región: {bbox}")
    print(f"   Periodo: {fecha_inicio} a {fecha_fin}")
    
    region = ipx.Query(producto, bbox, [fecha_inicio, fecha_fin])
    region.earthdata_login(persist=True)
    region.download_granules(output_dir)
    
    print(f"✅ Descarga completa en {output_dir}")


# =============================================================================
# FILTRADO Y EXTRACCIÓN
# =============================================================================

def extraer_vegetacion_h5(archivo, bounds):
    """
    Extrae datos de vegetación de ATL08.
    
    Returns:
        DataFrame con: lat, lon, canopy_height, canopy_openness, terrain_elevation
    """
    min_lon, min_lat, max_lon, max_lat = bounds
    tracks = ['gt1l', 'gt1r', 'gt2l', 'gt2r', 'gt3l', 'gt3r']
    datos = []
    
    with h5py.File(archivo, 'r') as f:
        for track in tracks:
            try:
                base = f[track]['land_segments']
                lat = base['latitude'][:]
                lon = base['longitude'][:]
                
                mask = ((lat >= min_lat) & (lat <= max_lat) & 
                       (lon >= min_lon) & (lon <= max_lon) &
                       (lat < 1e10) & (lon < 1e10))
                
                if not np.any(mask):
                    continue
                
                h_canopy = base['canopy']['h_canopy'][:]
                canopy_openness = base['canopy']['canopy_openness'][:]
                terrain_h = base['terrain']['h_te_median'][:]
                
                lat_f = lat[mask]
                lon_f = lon[mask]
                h_canopy_f = h_canopy[mask]
                openness_f = canopy_openness[mask]
                terrain_f = terrain_h[mask]
                
                valid = (h_canopy_f < 1e10) & (h_canopy_f >= 0)
                
                for i in range(len(lat_f)):
                    if valid[i]:
                        datos.append({
                            'latitude': lat_f[i],
                            'longitude': lon_f[i],
                            'canopy_height': h_canopy_f[i],
                            'canopy_openness': openness_f[i] if openness_f[i] < 1e10 else np.nan,
                            'terrain_elevation': terrain_f[i] if terrain_f[i] < 1e10 else np.nan,
                            'track': track
                        })
                        
            except Exception as e:
                continue
    
    return pd.DataFrame(datos)


def filtrar_region(h5_dir='datos/icesat2', bounds=None, shapefile=None):
    """
    Filtra todos los archivos H5 por región.
    
    Args:
        h5_dir: directorio con archivos .h5
        bounds: (lon_min, lat_min, lon_max, lat_max)
        shapefile: ruta a shapefile (alternativa a bounds)
    """
    if shapefile:
        import geopandas as gpd
        gdf = gpd.read_file(shapefile).to_crs(epsg=4326)
        bounds = gdf.total_bounds  # (minx, miny, maxx, maxy)
    
    archivos = list(Path(h5_dir).glob('*.h5'))
    print(f"📂 Procesando {len(archivos)} archivos...")
    
    todos_datos = []
    for archivo in archivos:
        df = extraer_vegetacion_h5(archivo, bounds)
        if not df.empty:
            todos_datos.append(df)
            print(f"  ✓ {archivo.name}: {len(df)} puntos")
    
    if todos_datos:
        df_total = pd.concat(todos_datos, ignore_index=True)
        print(f"\n✅ Total: {len(df_total):,} puntos")
        return df_total
    else:
        print("❌ No se encontraron datos")
        return None


# =============================================================================
# ANÁLISIS Y VISUALIZACIÓN
# =============================================================================

def analizar_vegetacion(df, output_file='resultados/icesat2_vegetacion.png'):
    """Análisis estadístico y visualización de vegetación."""
    
    # Clasificar vegetación
    df['clase_veg'] = pd.cut(
        df['canopy_height'],
        bins=[0, 2, 5, 10, 20, 100],
        labels=['<2m', '2-5m', '5-10m', '10-20m', '>20m']
    )
    
    # Estadísticas
    print("\n📊 ESTADÍSTICAS DE VEGETACIÓN")
    print("="*70)
    print(f"Altura media: {df['canopy_height'].mean():.2f} m")
    print(f"Altura máxima: {df['canopy_height'].max():.2f} m")
    print(f"Elevación promedio: {df['terrain_elevation'].mean():.2f} m")
    
    print("\nDistribución por clase:")
    print(df['clase_veg'].value_counts().sort_index())
    
    # Visualización
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    
    # 1. Mapa de altura
    ax = axes[0, 0]
    scatter = ax.scatter(df['longitude'], df['latitude'], 
                        c=df['canopy_height'], cmap='YlGn', 
                        s=5, alpha=0.6, vmin=0, vmax=df['canopy_height'].quantile(0.95))
    plt.colorbar(scatter, ax=ax, label='Altura (m)')
    ax.set_title('Altura del Dosel', fontweight='bold')
    ax.set_xlabel('Longitud')
    ax.set_ylabel('Latitud')
    
    # 2. Mapa de apertura
    ax = axes[0, 1]
    mask = ~df['canopy_openness'].isna()
    scatter = ax.scatter(df.loc[mask, 'longitude'], df.loc[mask, 'latitude'],
                        c=df.loc[mask, 'canopy_openness'], cmap='RdYlGn',
                        s=5, alpha=0.6, vmin=0, vmax=1)
    plt.colorbar(scatter, ax=ax, label='Apertura (0-1)')
    ax.set_title('Apertura del Dosel', fontweight='bold')
    ax.set_xlabel('Longitud')
    ax.set_ylabel('Latitud')
    
    # 3. Histograma altura
    ax = axes[0, 2]
    ax.hist(df['canopy_height'], bins=50, color='forestgreen', alpha=0.7)
    ax.axvline(df['canopy_height'].mean(), color='red', linestyle='--', 
               label=f"Media: {df['canopy_height'].mean():.2f} m")
    ax.set_xlabel('Altura (m)')
    ax.set_ylabel('Frecuencia')
    ax.set_title('Distribución de Altura', fontweight='bold')
    ax.legend()
    
    # 4. Boxplot por clase
    ax = axes[1, 0]
    df.boxplot(column='canopy_height', by='clase_veg', ax=ax)
    ax.set_xlabel('Clase')
    ax.set_ylabel('Altura (m)')
    ax.set_title('Altura por Clase', fontweight='bold')
    plt.sca(ax)
    plt.xticks(rotation=45)
    
    # 5. Elevación vs altura
    ax = axes[1, 1]
    ax.scatter(df['terrain_elevation'], df['canopy_height'], 
               alpha=0.3, s=5, c='darkgreen')
    ax.set_xlabel('Elevación del Terreno (m)')
    ax.set_ylabel('Altura del Dosel (m)')
    ax.set_title('Elevación vs Altura', fontweight='bold')
    
    # 6. Mapa clasificación
    ax = axes[1, 2]
    colores = {'<2m': '#ffffcc', '2-5m': '#c7e9b4', '5-10m': '#7fcdbb', 
               '10-20m': '#41b6c4', '>20m': '#1d91c0'}
    for clase, color in colores.items():
        mask = df['clase_veg'] == clase
        if mask.sum() > 0:
            ax.scatter(df.loc[mask, 'longitude'], df.loc[mask, 'latitude'],
                      c=color, label=clase, s=5, alpha=0.6)
    ax.set_xlabel('Longitud')
    ax.set_ylabel('Latitud')
    ax.set_title('Clasificación', fontweight='bold')
    ax.legend(fontsize=8)
    
    plt.tight_layout()
    Path(output_file).parent.mkdir(exist_ok=True, parents=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✅ Visualización guardada: {output_file}")
    plt.show()


# =============================================================================
# MAIN - EJEMPLO DE USO
# =============================================================================

if __name__ == "__main__":
    print("="*70)
    print("🌳 TERRAF - Análisis ICESat-2")
    print("="*70)
    
    # Opción 1: Usar shapefile para definir región
    shapefile = Path('datos/magnetometria/Carta/D01122025163452P/CampoMagnetico_H13_11.shp')
    
    if shapefile.exists():
        df = filtrar_region(shapefile=shapefile)
    else:
        # Opción 2: Definir bounds manualmente
        bounds = (-106.0, 28.0, -104.0, 29.0)
        df = filtrar_region(bounds=bounds)
    
    if df is not None:
        # Guardar datos
        df.to_csv('datos/icesat2/vegetacion_filtrada.csv', index=False)
        print(f"💾 Datos guardados: datos/icesat2/vegetacion_filtrada.csv")
        
        # Análisis
        analizar_vegetacion(df)
