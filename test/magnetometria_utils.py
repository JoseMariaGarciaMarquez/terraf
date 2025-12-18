"""
TERRAF - Utilidades Magnetometría
==================================

Script unificado para:
1. Carga y visualización de datos magnéticos
2. Estadísticas por polígono
3. Detección de anomalías
4. Correlación con otros datos

Autor: TERRAF
Fecha: 5 de diciembre de 2025
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import fiona
from shapely.geometry import shape

sns.set_style("whitegrid")

# =============================================================================
# LECTURA Y CARGA
# =============================================================================

def cargar_magnetometria(shapefile_path):
    """
    Carga shapefile de magnetometría.
    
    Returns:
        DataFrame con geometría y atributos
    """
    print(f"🧲 Cargando magnetometría...")
    
    features = []
    with fiona.open(shapefile_path) as src:
        for feature in src:
            props = feature['properties'].copy()
            props['geometry'] = shape(feature['geometry'])
            features.append(props)
    
    df = pd.DataFrame(features)
    print(f"  ✅ {len(df)} polígonos cargados")
    
    # Mostrar campos disponibles
    print(f"  📊 Campos: {list(df.columns)}")
    
    return df


# =============================================================================
# ANÁLISIS
# =============================================================================

def analizar_codigos(df, campo_codigo='RANGO_CODE'):
    """Análisis estadístico por código magnético."""
    
    if campo_codigo not in df.columns:
        print(f"❌ Campo {campo_codigo} no encontrado")
        return
    
    print(f"\n📊 ANÁLISIS POR CÓDIGO")
    print("="*70)
    
    # Distribución de códigos
    distribucion = df[campo_codigo].value_counts().sort_index()
    print("\nDistribución de códigos:")
    for codigo, count in distribucion.items():
        porcentaje = (count / len(df)) * 100
        print(f"  Código {codigo}: {count} polígonos ({porcentaje:.1f}%)")
    
    # Áreas por código
    if 'Shape_Area' in df.columns:
        print("\nÁrea por código (m²):")
        area_por_codigo = df.groupby(campo_codigo)['Shape_Area'].agg(['sum', 'mean', 'count'])
        print(area_por_codigo)
    
    return distribucion


def detectar_anomalias(df, campo_codigo='RANGO_CODE', umbral_codigo=10):
    """Detecta anomalías magnéticas (códigos altos)."""
    
    anomalias = df[df[campo_codigo] >= umbral_codigo].copy()
    
    print(f"\n🎯 ANOMALÍAS MAGNÉTICAS (código >= {umbral_codigo})")
    print("="*70)
    print(f"Total anomalías: {len(anomalias)}")
    
    if len(anomalias) > 0:
        print(f"\nCódigos de anomalía:")
        print(anomalias[campo_codigo].value_counts().sort_index())
        
        if 'Shape_Area' in anomalias.columns:
            area_total = anomalias['Shape_Area'].sum() / 1e6  # km²
            print(f"\nÁrea total de anomalías: {area_total:.2f} km²")
    
    return anomalias


# =============================================================================
# VISUALIZACIÓN
# =============================================================================

def visualizar_magnetometria(df, campo_codigo='RANGO_CODE', output_file='resultados/magnetometria.png'):
    """Visualización de datos magnéticos."""
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Mapa de códigos
    ax = axes[0, 0]
    for codigo in sorted(df[campo_codigo].unique()):
        subset = df[df[campo_codigo] == codigo]
        for idx, row in subset.iterrows():
            geom = row['geometry']
            if geom.geom_type == 'Polygon':
                x, y = geom.exterior.xy
                ax.fill(x, y, alpha=0.6, label=f'Código {codigo}' if idx == subset.index[0] else '')
    
    ax.set_xlabel('X (UTM)')
    ax.set_ylabel('Y (UTM)')
    ax.set_title('Mapa de Códigos Magnéticos', fontweight='bold', fontsize=14)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # 2. Histograma de códigos
    ax = axes[0, 1]
    df[campo_codigo].value_counts().sort_index().plot(kind='bar', ax=ax, color='steelblue')
    ax.set_xlabel('Código Magnético')
    ax.set_ylabel('Frecuencia')
    ax.set_title('Distribución de Códigos', fontweight='bold', fontsize=14)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 3. Áreas por código
    if 'Shape_Area' in df.columns:
        ax = axes[1, 0]
        area_por_codigo = df.groupby(campo_codigo)['Shape_Area'].sum() / 1e6  # km²
        area_por_codigo.plot(kind='bar', ax=ax, color='coral')
        ax.set_xlabel('Código Magnético')
        ax.set_ylabel('Área (km²)')
        ax.set_title('Área por Código', fontweight='bold', fontsize=14)
        ax.grid(True, alpha=0.3, axis='y')
    
    # 4. Estadísticas
    ax = axes[1, 1]
    ax.axis('off')
    
    stats_text = f"""
    📊 ESTADÍSTICAS GENERALES
    
    Total de polígonos: {len(df):,}
    Códigos únicos: {df[campo_codigo].nunique()}
    
    Código más frecuente: {df[campo_codigo].mode()[0]}
    Código menos frecuente: {df[campo_codigo].value_counts().idxmin()}
    
    """
    
    if 'Shape_Area' in df.columns:
        area_total = df['Shape_Area'].sum() / 1e6
        stats_text += f"Área total: {area_total:.2f} km²\n"
        stats_text += f"Área promedio: {df['Shape_Area'].mean():.2f} m²\n"
    
    ax.text(0.1, 0.5, stats_text, fontsize=12, family='monospace',
            verticalalignment='center')
    
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
    print("🧲 TERRAF - Análisis Magnetometría")
    print("="*70)
    
    shapefile = Path('datos/magnetometria/Carta/D01122025163452P/CampoMagnetico_H13_11.shp')
    
    if shapefile.exists():
        # Cargar datos
        df = cargar_magnetometria(shapefile)
        
        # Análisis
        analizar_codigos(df)
        anomalias = detectar_anomalias(df, umbral_codigo=10)
        
        # Visualización
        visualizar_magnetometria(df)
        
        # Guardar anomalías
        if len(anomalias) > 0:
            anomalias.to_csv('resultados/anomalias_magneticas.csv', index=False)
            print("\n💾 Anomalías guardadas: resultados/anomalias_magneticas.csv")
    else:
        print(f"❌ No se encuentra: {shapefile}")
