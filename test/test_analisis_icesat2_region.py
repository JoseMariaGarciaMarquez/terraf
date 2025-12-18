"""
Análisis completo de datos ICESat-2 filtrados para región de magnetometría

Este script analiza los datos ICESat-2 que están SOLO dentro del área de estudio:
1. Carga datos filtrados
2. Análisis estadístico detallado
3. Visualizaciones espaciales
4. Perfiles de elevación
5. Comparación con magnetometría
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import geopandas as gpd

# Configurar estilo
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (16, 12)

def cargar_datos_filtrados():
    """Carga los datos filtrados"""
    print("=" * 70)
    print("📥 CARGANDO DATOS FILTRADOS")
    print("=" * 70)
    
    csv_path = Path("datos/icesat2/icesat2_region_magnetometria.csv")
    
    if not csv_path.exists():
        print("\n❌ No se encontró el archivo de datos filtrados")
        print("   Ejecuta primero: python test/test_icepyx_filtrar.py")
        return None
    
    print(f"\n📄 Cargando: {csv_path.name}")
    df = pd.read_csv(csv_path)
    
    print(f"\n✅ Datos cargados:")
    print(f"   • {len(df):,} puntos")
    print(f"   • {len(df.columns)} columnas")
    print(f"   • {df['archivo'].nunique()} archivos diferentes")
    print(f"   • {df['track'].nunique()} tracks")
    
    return df

def analisis_exploratorio(df):
    """Análisis exploratorio detallado"""
    print("\n" + "=" * 70)
    print("🔍 ANÁLISIS EXPLORATORIO")
    print("=" * 70)
    
    print("\n📋 Primeras filas:")
    print(df.head(10))
    
    print("\n📊 Información del DataFrame:")
    print(df.info())
    
    print("\n📈 Estadísticas descriptivas:")
    print(df.describe().round(2))
    
    print("\n🛰️ Distribución por track:")
    track_counts = df['track'].value_counts()
    for track, count in track_counts.items():
        print(f"   {track}: {count:,} puntos ({count/len(df)*100:.1f}%)")
    
    print("\n📦 Distribución por archivo:")
    archivo_counts = df['archivo'].value_counts()
    for archivo, count in archivo_counts.items():
        fecha = archivo.split('_')[1][:8]
        print(f"   {fecha}: {count:,} puntos ({count/len(df)*100:.1f}%)")
    
    print("\n⛰️ Estadísticas de elevación:")
    elev = df['elevacion_media'].dropna()
    print(f"   • N válidos: {len(elev):,}")
    print(f"   • Mínima: {elev.min():.1f} m")
    print(f"   • Máxima: {elev.max():.1f} m")
    print(f"   • Media: {elev.mean():.1f} m")
    print(f"   • Mediana: {elev.median():.1f} m")
    print(f"   • Desv. Est.: {elev.std():.1f} m")
    print(f"   • Rango: {elev.max() - elev.min():.1f} m")
    
    # Percentiles
    print(f"\n📊 Percentiles de elevación:")
    for p in [10, 25, 50, 75, 90, 95]:
        val = elev.quantile(p/100)
        print(f"   P{p}: {val:.1f} m")
    
    if 'altura_dosel' in df.columns:
        veg = df['altura_dosel'].dropna()
        if len(veg) > 0:
            print(f"\n🌲 Estadísticas de vegetación:")
            print(f"   • Puntos con vegetación: {len(veg):,} ({len(veg)/len(df)*100:.1f}%)")
            print(f"   • Altura mínima: {veg.min():.1f} m")
            print(f"   • Altura máxima: {veg.max():.1f} m")
            print(f"   • Altura media: {veg.mean():.1f} m")
            print(f"   • Altura mediana: {veg.median():.1f} m")

def crear_visualizaciones(df):
    """Crea visualizaciones completas"""
    print("\n" + "=" * 70)
    print("🎨 CREANDO VISUALIZACIONES")
    print("=" * 70)
    
    fig = plt.figure(figsize=(18, 14))
    
    # 1. Mapa de puntos coloreado por elevación
    ax1 = plt.subplot(3, 3, 1)
    scatter1 = ax1.scatter(df['longitud'], df['latitud'],
                          c=df['elevacion_media'], cmap='terrain',
                          s=3, alpha=0.6)
    ax1.set_xlabel('Longitud (°)')
    ax1.set_ylabel('Latitud (°)')
    ax1.set_title('Distribución Espacial - Elevación')
    ax1.grid(True, alpha=0.3)
    plt.colorbar(scatter1, ax=ax1, label='Elevación (m)')
    
    # 2. Mapa de tracks
    ax2 = plt.subplot(3, 3, 2)
    colors = ['red', 'blue', 'green', 'orange', 'purple', 'cyan']
    for i, track in enumerate(df['track'].unique()):
        track_data = df[df['track'] == track]
        ax2.scatter(track_data['longitud'], track_data['latitud'],
                   c=colors[i], s=2, alpha=0.6, label=track)
    ax2.set_xlabel('Longitud (°)')
    ax2.set_ylabel('Latitud (°)')
    ax2.set_title('Tracks ICESat-2')
    ax2.legend(markerscale=3, fontsize=8)
    ax2.grid(True, alpha=0.3)
    
    # 3. Histograma de elevación
    ax3 = plt.subplot(3, 3, 3)
    elev = df['elevacion_media'].dropna()
    ax3.hist(elev, bins=50, color='brown', alpha=0.7, edgecolor='black')
    ax3.axvline(elev.mean(), color='red', linestyle='--', linewidth=2, label=f'Media: {elev.mean():.0f}m')
    ax3.axvline(elev.median(), color='blue', linestyle='--', linewidth=2, label=f'Mediana: {elev.median():.0f}m')
    ax3.set_xlabel('Elevación (m)')
    ax3.set_ylabel('Frecuencia')
    ax3.set_title('Distribución de Elevación')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 4. Box plot por track
    ax4 = plt.subplot(3, 3, 4)
    tracks_data = []
    tracks_labels = []
    for track in sorted(df['track'].unique()):
        track_elev = df[df['track'] == track]['elevacion_media'].dropna()
        if len(track_elev) > 0:
            tracks_data.append(track_elev)
            tracks_labels.append(track)
    
    bp = ax4.boxplot(tracks_data, labels=tracks_labels, patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor('lightblue')
    ax4.set_xlabel('Track')
    ax4.set_ylabel('Elevación (m)')
    ax4.set_title('Distribución por Track')
    ax4.grid(True, alpha=0.3, axis='y')
    plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)
    
    # 5. Mapa de incertidumbre
    ax5 = plt.subplot(3, 3, 5)
    if 'incertidumbre' in df.columns:
        unc_valid = df[df['incertidumbre'] < 100]  # Filtrar outliers
        scatter5 = ax5.scatter(unc_valid['longitud'], unc_valid['latitud'],
                              c=unc_valid['incertidumbre'], cmap='YlOrRd',
                              s=3, alpha=0.6, vmin=0, vmax=50)
        plt.colorbar(scatter5, ax=ax5, label='Incertidumbre (m)')
        ax5.set_title('Incertidumbre de Medición')
    else:
        ax5.text(0.5, 0.5, 'No hay datos\nde incertidumbre', 
                ha='center', va='center', transform=ax5.transAxes)
        ax5.set_title('Incertidumbre')
    ax5.set_xlabel('Longitud (°)')
    ax5.set_ylabel('Latitud (°)')
    ax5.grid(True, alpha=0.3)
    
    # 6. Vegetación
    ax6 = plt.subplot(3, 3, 6)
    if 'altura_dosel' in df.columns:
        veg_data = df[df['altura_dosel'].notna()]
        if len(veg_data) > 0:
            scatter6 = ax6.scatter(veg_data['longitud'], veg_data['latitud'],
                                  c=veg_data['altura_dosel'], cmap='Greens',
                                  s=3, alpha=0.6, vmin=0, vmax=30)
            plt.colorbar(scatter6, ax=ax6, label='Altura (m)')
            ax6.set_title(f'Altura del Dosel ({len(veg_data)} puntos)')
        else:
            ax6.text(0.5, 0.5, 'No hay datos\nde vegetación', 
                    ha='center', va='center', transform=ax6.transAxes)
            ax6.set_title('Vegetación')
    ax6.set_xlabel('Longitud (°)')
    ax6.set_ylabel('Latitud (°)')
    ax6.grid(True, alpha=0.3)
    
    # 7. Perfil de elevación (latitud)
    ax7 = plt.subplot(3, 3, 7)
    df_sorted = df.sort_values('latitud')
    ax7.scatter(df_sorted['latitud'], df_sorted['elevacion_media'],
               c=df_sorted['elevacion_media'], cmap='terrain',
               s=1, alpha=0.3)
    ax7.set_xlabel('Latitud (°)')
    ax7.set_ylabel('Elevación (m)')
    ax7.set_title('Perfil S-N')
    ax7.grid(True, alpha=0.3)
    
    # 8. Perfil de elevación (longitud)
    ax8 = plt.subplot(3, 3, 8)
    df_sorted = df.sort_values('longitud')
    ax8.scatter(df_sorted['longitud'], df_sorted['elevacion_media'],
               c=df_sorted['elevacion_media'], cmap='terrain',
               s=1, alpha=0.3)
    ax8.set_xlabel('Longitud (°)')
    ax8.set_ylabel('Elevación (m)')
    ax8.set_title('Perfil W-E')
    ax8.grid(True, alpha=0.3)
    
    # 9. Distribución temporal
    ax9 = plt.subplot(3, 3, 9)
    archivo_counts = df['archivo'].value_counts()
    fechas = [a.split('_')[1][:8] for a in archivo_counts.index]
    
    bars = ax9.bar(range(len(fechas)), archivo_counts.values, 
                   color='steelblue', alpha=0.7, edgecolor='black')
    ax9.set_xticks(range(len(fechas)))
    ax9.set_xticklabels(fechas, rotation=45, ha='right')
    ax9.set_xlabel('Fecha')
    ax9.set_ylabel('Número de puntos')
    ax9.set_title('Distribución Temporal')
    ax9.grid(True, alpha=0.3, axis='y')
    
    # Agregar valores en las barras
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax9.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height):,}',
                ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    
    # Guardar
    output_path = Path("datos/icesat2/analisis_completo_region.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✅ Visualización guardada: {output_path.name}")
    
    return output_path

def crear_mapa_detallado(df):
    """Crea mapa detallado con límites de magnetometría"""
    print("\n" + "=" * 70)
    print("🗺️ CREANDO MAPA DETALLADO")
    print("=" * 70)
    
    # Cargar shapefile de magnetometría
    shp_path = Path("datos/magnetometria/Carta/D01122025163452P/CampoMagnetico_H13_11.shp")
    
    try:
        gdf_magne = gpd.read_file(shp_path)
        if gdf_magne.crs != 'EPSG:4326':
            gdf_magne = gdf_magne.to_crs('EPSG:4326')
        
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # Plotear límites de magnetometría
        gdf_magne.boundary.plot(ax=ax, color='red', linewidth=1.5, 
                               alpha=0.8, label='Límite magnetometría')
        
        # Plotear puntos ICESat-2
        scatter = ax.scatter(df['longitud'], df['latitud'],
                           c=df['elevacion_media'], cmap='terrain',
                           s=10, alpha=0.7, edgecolors='black', linewidth=0.2)
        
        # Configurar mapa
        ax.set_xlabel('Longitud (°)', fontsize=12)
        ax.set_ylabel('Latitud (°)', fontsize=12)
        ax.set_title('ICESat-2 en Región de Magnetometría', 
                    fontsize=14, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Colorbar
        cbar = plt.colorbar(scatter, ax=ax, label='Elevación (m)', pad=0.02)
        
        # Agregar estadísticas
        stats_text = f'Puntos: {len(df):,}\n'
        stats_text += f'Elev: {df["elevacion_media"].min():.0f}-{df["elevacion_media"].max():.0f} m\n'
        stats_text += f'Media: {df["elevacion_media"].mean():.0f} m'
        
        ax.text(0.02, 0.98, stats_text,
               transform=ax.transAxes,
               fontsize=10,
               verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        
        output_path = Path("datos/icesat2/mapa_detallado_region.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\n✅ Mapa detallado guardado: {output_path.name}")
        
        return output_path
        
    except Exception as e:
        print(f"\n⚠️ No se pudo crear mapa con límites: {e}")
        return None

def analizar_por_track(df):
    """Análisis detallado por track"""
    print("\n" + "=" * 70)
    print("📊 ANÁLISIS POR TRACK")
    print("=" * 70)
    
    resumen = []
    
    for track in sorted(df['track'].unique()):
        track_df = df[df['track'] == track]
        
        stats = {
            'track': track,
            'n_puntos': len(track_df),
            'elev_min': track_df['elevacion_media'].min(),
            'elev_max': track_df['elevacion_media'].max(),
            'elev_media': track_df['elevacion_media'].mean(),
            'elev_mediana': track_df['elevacion_media'].median(),
            'elev_std': track_df['elevacion_media'].std(),
            'lat_min': track_df['latitud'].min(),
            'lat_max': track_df['latitud'].max(),
            'lon_min': track_df['longitud'].min(),
            'lon_max': track_df['longitud'].max(),
        }
        
        if 'incertidumbre' in track_df.columns:
            stats['incert_media'] = track_df['incertidumbre'].mean()
            stats['incert_mediana'] = track_df['incertidumbre'].median()
        
        if 'altura_dosel' in track_df.columns:
            veg_count = track_df['altura_dosel'].notna().sum()
            stats['veg_puntos'] = veg_count
            stats['veg_pct'] = (veg_count / len(track_df)) * 100
            if veg_count > 0:
                stats['veg_media'] = track_df['altura_dosel'].mean()
        
        resumen.append(stats)
    
    resumen_df = pd.DataFrame(resumen)
    
    print("\n📋 Resumen por track:")
    print(resumen_df.round(2).to_string(index=False))
    
    # Guardar
    output_csv = Path("datos/icesat2/analisis_por_track.csv")
    resumen_df.to_csv(output_csv, index=False)
    print(f"\n✅ Guardado: {output_csv.name}")
    
    return resumen_df

def main():
    """Ejecuta análisis completo"""
    print("\n" + "=" * 70)
    print("🚀 TERRAF - Análisis ICESat-2 Región de Magnetometría")
    print("=" * 70)
    
    # 1. Cargar datos
    df = cargar_datos_filtrados()
    if df is None:
        return
    
    # 2. Análisis exploratorio
    analisis_exploratorio(df)
    
    # 3. Análisis por track
    resumen_tracks = analizar_por_track(df)
    
    # 4. Visualizaciones
    fig1_path = crear_visualizaciones(df)
    
    # 5. Mapa detallado
    fig2_path = crear_mapa_detallado(df)
    
    # 6. Abrir visualizaciones
    print("\n" + "=" * 70)
    print("🖼️ ABRIENDO VISUALIZACIONES")
    print("=" * 70)
    
    import os
    os.system(f'start {fig1_path}')
    if fig2_path:
        os.system(f'start {fig2_path}')
    
    print("\n" + "=" * 70)
    print("✅ ANÁLISIS COMPLETADO")
    print("=" * 70)
    print(f"\n📊 Resumen:")
    print(f"   • Total puntos: {len(df):,}")
    print(f"   • Tracks: {df['track'].nunique()}")
    print(f"   • Archivos: {df['archivo'].nunique()}")
    print(f"   • Elevación: {df['elevacion_media'].min():.0f} - {df['elevacion_media'].max():.0f} m")
    print(f"   • Área: {df['latitud'].min():.4f}° a {df['latitud'].max():.4f}° (lat)")
    print(f"   •       {df['longitud'].min():.4f}° a {df['longitud'].max():.4f}° (lon)")
    
    print(f"\n📂 Archivos generados:")
    print(f"   • analisis_completo_region.png - 9 paneles de visualización")
    print(f"   • mapa_detallado_region.png - Mapa con límites de magnetometría")
    print(f"   • analisis_por_track.csv - Estadísticas por track")
    print("=" * 70)

if __name__ == '__main__':
    main()
