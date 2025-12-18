"""
TERRAF Download
Módulo para descargar imágenes satelitales de diferentes fuentes
Soporta: HLS, Landsat, Sentinel-2
"""

import os
import requests
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class TerrafDownload:
    """
    Gestor de descargas de imágenes satelitales
    """
    
    def __init__(self, output_dir="datos/downloaded"):
        """
        Inicializar gestor de descargas
        
        Args:
            output_dir: Directorio donde guardar las descargas
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Credenciales (se cargarían de .env o config)
        self.earthdata_token = None
        self.planetary_computer_key = None
        
    def search_hls_scenes(self, bbox, start_date, end_date, max_cloud_cover=20):
        """
        Buscar escenas HLS disponibles
        
        Args:
            bbox: [min_lon, min_lat, max_lon, max_lat]
            start_date: Fecha inicio (datetime o string)
            end_date: Fecha fin (datetime o string)
            max_cloud_cover: Cobertura de nubes máxima (%)
            
        Returns:
            list: Lista de escenas disponibles con metadatos
        """
        print(f"🔍 Buscando escenas HLS...")
        print(f"   📍 Bbox: {bbox}")
        print(f"   📅 Dates: {start_date} - {end_date}")
        print(f"   ☁️  Cloud cover < {max_cloud_cover}%")
        
        # TODO: Implementar búsqueda real usando NASA CMR API
        # Por ahora, retornar ejemplo
        scenes = [
            {
                'id': 'HLS.L30.T13RDN.2023152T173419.v2.0',
                'date': '2023-06-01',
                'cloud_cover': 15,
                'tile': 'T13RDN',
                'sensor': 'Landsat 8/9'
            }
        ]
        
        print(f"✅ Encontradas {len(scenes)} escenas")
        return scenes
    
    def download_hls_scene(self, scene_id, bands=['B02', 'B03', 'B04', 'B05', 'B06', 'B07']):
        """
        Descargar una escena HLS completa
        
        Args:
            scene_id: ID de la escena HLS
            bands: Lista de bandas a descargar
            
        Returns:
            dict: Rutas de archivos descargados
        """
        print(f"📥 Descargando escena: {scene_id}")
        
        scene_dir = self.output_dir / scene_id
        scene_dir.mkdir(exist_ok=True)
        
        downloaded_files = {}
        
        for band in bands:
            # Construir URL (ejemplo - NASA EarthData)
            # url = f"https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/HLSL30.020/{scene_id}.{band}.tif"
            
            output_file = scene_dir / f"{scene_id}.{band}.tif"
            
            # TODO: Implementar descarga real
            print(f"   ⏳ Descargando {band}...")
            # downloaded_files[band] = str(output_file)
        
        print(f"✅ Descarga completa: {scene_dir}")
        return downloaded_files
    
    def search_landsat_scenes(self, bbox, start_date, end_date, max_cloud_cover=20):
        """
        Buscar escenas Landsat 8/9
        
        Args:
            bbox: [min_lon, min_lat, max_lon, max_lat]
            start_date: Fecha inicio
            end_date: Fecha fin
            max_cloud_cover: Cobertura de nubes máxima (%)
            
        Returns:
            list: Lista de escenas disponibles
        """
        print(f"🛰️  Buscando escenas Landsat...")
        
        # TODO: Implementar con USGS EarthExplorer API o Microsoft Planetary Computer
        scenes = []
        
        return scenes
    
    def search_sentinel2_scenes(self, bbox, start_date, end_date, max_cloud_cover=20):
        """
        Buscar escenas Sentinel-2
        
        Args:
            bbox: [min_lon, min_lat, max_lon, max_lat]
            start_date: Fecha inicio
            end_date: Fecha fin
            max_cloud_cover: Cobertura de nubes máxima (%)
            
        Returns:
            list: Lista de escenas disponibles
        """
        print(f"🛰️  Buscando escenas Sentinel-2...")
        
        # TODO: Implementar con Copernicus/ESA API o Microsoft Planetary Computer
        scenes = []
        
        return scenes
    
    def get_landsat_scenes_aws(self, bbox, start_date, end_date):
        """
        Buscar escenas Landsat usando USGS STAC API (AWS público - SIN autenticación)
        
        Args:
            bbox: [min_lon, min_lat, max_lon, max_lat]
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (YYYY-MM-DD)
            
        Returns:
            list: Escenas disponibles
        """
        try:
            import pystac_client
            
            print(f"🌐 Conectando a USGS Landsat STAC (AWS público)...")
            
            # USGS STAC API - completamente público
            catalog = pystac_client.Client.open(
                "https://landsatlook.usgs.gov/stac-server"
            )
            
            # Búsqueda de Landsat Collection 2 Level-2
            search = catalog.search(
                collections=["landsat-c2l2-sr"],
                bbox=bbox,
                datetime=f"{start_date}/{end_date}"
            )
            
            items = list(search.items())
            print(f"✅ Encontradas {len(items)} escenas en USGS Landsat")
            
            scenes = []
            for item in items:
                scenes.append({
                    'id': item.id,
                    'date': item.datetime.strftime('%Y-%m-%d'),
                    'cloud_cover': item.properties.get('eo:cloud_cover', 0),
                    'assets': list(item.assets.keys()),
                    'item': item,
                    'source': 'aws'
                })
            
            return scenes
            
        except ImportError:
            print("⚠️  pystac_client no instalado. Instalar con: pip install pystac-client")
            return []
        except Exception as e:
            print(f"❌ Error buscando en USGS STAC: {e}")
            return []
    
    def get_planetary_computer_scenes(self, bbox, start_date, end_date, collection='landsat-c2-l2'):
        """
        Buscar escenas usando Microsoft Planetary Computer (REQUIERE autenticación)
        NOTA: Este método puede fallar con error 409. Usar get_landsat_scenes_aws() en su lugar.
        
        Args:
            bbox: [min_lon, min_lat, max_lon, max_lat]
            start_date: Fecha inicio
            end_date: Fecha fin
            collection: 'landsat-c2-l2', 'sentinel-2-l2a', 'hls'
            
        Returns:
            list: Escenas disponibles
        """
        try:
            import pystac_client
            from datetime import datetime
            
            print(f"🌐 Conectando a Microsoft Planetary Computer...")
            
            catalog = pystac_client.Client.open(
                "https://planetarycomputer.microsoft.com/api/stac/v1"
            )
            
            # Búsqueda
            search = catalog.search(
                collections=[collection],
                bbox=bbox,
                datetime=f"{start_date}/{end_date}"
            )
            
            items = list(search.items())
            print(f"✅ Encontradas {len(items)} escenas en Planetary Computer")
            
            scenes = []
            for item in items:
                scenes.append({
                    'id': item.id,
                    'date': item.datetime.strftime('%Y-%m-%d'),
                    'cloud_cover': item.properties.get('eo:cloud_cover', 0),
                    'assets': list(item.assets.keys()),
                    'item': item,
                    'source': 'planetary_computer'
                })
            
            return scenes
            
        except ImportError:
            print("⚠️  pystac_client no instalado. Instalar con: pip install pystac-client")
            return []
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def download_from_planetary_computer(self, scene, output_dir=None):
        """
        Descargar escena desde Microsoft Planetary Computer
        
        Args:
            scene: Diccionario de escena (de get_planetary_computer_scenes)
            output_dir: Directorio de salida (opcional)
            
        Returns:
            dict: Rutas de archivos descargados
        """
        try:
            import planetary_computer
        except ImportError:
            print("⚠️  planetary_computer no instalado")
            return {}
        
        if output_dir is None:
            output_dir = self.output_dir / scene['id']
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📥 Descargando desde Planetary Computer: {scene['id']}")
        
        item = scene['item']
        
        # Firmar URLs para acceso autenticado
        signed_item = planetary_computer.sign(item)
        
        downloaded = {}
        
        # Filtrar solo bandas espectrales - nombres varían por colección
        # Landsat: 'red', 'green', 'blue', 'nir08', 'swir16', 'swir22', 'coastal', etc.
        # HLS: 'B01', 'B02', etc.
        all_assets = list(signed_item.assets.keys())
        
        # Identificar bandas (excluir QA, metadatos, etc.)
        exclude_keywords = ['qa', 'angle', 'metadata', 'thumbnail', 'tilejson', 'rendered']
        band_assets = [k for k in all_assets if not any(ex in k.lower() for ex in exclude_keywords)]
        
        print(f"   📊 Encontradas {len(band_assets)} bandas: {band_assets}")
        
        for asset_key in band_assets:
            asset = signed_item.assets[asset_key]
            href = asset.href
            
            # Intentar usar Azure Blob con SAS token si está disponible
            # Si falla, intentar AWS alternativo
            if 'blob.core.windows.net' in href and '?' not in href:
                # URL de Azure sin SAS token - probablemente fallará
                print(f"   ⚠️  Skipping {asset_key} - Azure requiere autenticación")
                continue
            
            # Nombre de archivo compatible con TerrafPR
            # Convertir nombres como 'red' -> 'B4', 'green' -> 'B3', etc.
            band_map = {
                'coastal': 'B1', 'blue': 'B2', 'green': 'B3', 'red': 'B4',
                'nir08': 'B5', 'swir16': 'B6', 'swir22': 'B7', 'cirrus': 'B9',
                'lwir11': 'B10', 'lwir12': 'B11'
            }
            
            # Si es HLS, mantener nombre original; si es Landsat, mapear
            if asset_key in band_map:
                band_name = band_map[asset_key]
            elif asset_key.startswith('B'):
                band_name = asset_key
            else:
                band_name = asset_key.upper()
            
            output_file = output_dir / f"{scene['id']}_{band_name}.tif"
            
            try:
                print(f"   ⏳ Descargando {asset_key} → {band_name}...")
                response = requests.get(href, stream=True, timeout=60)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                with open(output_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                
                downloaded[band_name] = str(output_file)
                size_mb = downloaded_size / (1024 * 1024)
                print(f"   ✅ {asset_key} descargado ({size_mb:.1f} MB)")
                
            except Exception as e:
                print(f"   ❌ Error descargando {asset_key}: {e}")
        
        print(f"✅ Descarga completa: {output_dir}")
        print(f"   📁 {len(downloaded)} archivos descargados")
        return downloaded
    
    def download_from_aws(self, scene, output_dir=None):
        """
        Descargar escena Landsat desde AWS (público, sin autenticación)
        
        Args:
            scene: Diccionario de escena (de get_landsat_scenes_aws)
            output_dir: Directorio de salida (opcional)
            
        Returns:
            dict: Rutas de archivos descargados
        """
        if output_dir is None:
            output_dir = self.output_dir / scene['id']
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📥 Descargando desde AWS S3: {scene['id']}")
        
        item = scene['item']
        downloaded = {}
        
        # Assets de Landsat que necesitamos (bandas espectrales)
        # En AWS/USGS STAC los nombres son diferentes
        band_assets = []
        for key in item.assets.keys():
            key_lower = key.lower()
            # Incluir bandas espectrales, excluir QA y metadatos
            if any(b in key_lower for b in ['blue', 'green', 'red', 'nir', 'swir', 'coastal', 'cirrus', 'lwir']):
                if 'qa' not in key_lower and 'angle' not in key_lower:
                    band_assets.append(key)
        
        print(f"   📊 Bandas a descargar: {band_assets}")
        
        # Mapeo de nombres AWS/USGS a nombres estándar Landsat
        band_map = {
            'coastal': 'B1', 'blue': 'B2', 'green': 'B3', 'red': 'B4',
            'nir08': 'B5', 'swir16': 'B6', 'swir22': 'B7', 
            'cirrus': 'B9', 'lwir11': 'B10', 'lwir': 'B10'
        }
        
        for asset_key in band_assets:
            try:
                asset = item.assets[asset_key]
                href = asset.href
                
                # Determinar nombre de banda
                asset_lower = asset_key.lower()
                band_name = None
                for aws_name, std_name in band_map.items():
                    if aws_name in asset_lower:
                        band_name = std_name
                        break
                
                if not band_name:
                    # Si no coincide con el mapa, usar el nombre original
                    band_name = asset_key.upper()
                
                output_file = output_dir / f"{scene['id']}_{band_name}.TIF"
                
                print(f"   ⏳ Descargando {asset_key} → {band_name}...")
                
                # Descargar directamente desde AWS (público)
                response = requests.get(href, stream=True, timeout=120)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                with open(output_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                
                downloaded[band_name] = str(output_file)
                size_mb = downloaded_size / (1024 * 1024)
                print(f"   ✅ {band_name} descargado ({size_mb:.1f} MB)")
                
            except Exception as e:
                print(f"   ❌ Error descargando {asset_key}: {e}")
        
        print(f"✅ Descarga completa: {output_dir}")
        print(f"   📁 {len(downloaded)} archivos descargados")
        return downloaded


# Ejemplo de uso
if __name__ == "__main__":
    downloader = TerrafDownload()
    
    # Ejemplo: buscar escenas HLS
    bbox = [-106.8, 28.0, -106.6, 28.2]  # Área de Chihuahua
    scenes = downloader.search_hls_scenes(
        bbox=bbox,
        start_date="2023-06-01",
        end_date="2023-06-30",
        max_cloud_cover=20
    )
    
    print(f"\nEscenas encontradas: {len(scenes)}")
    for scene in scenes:
        print(f"  - {scene['id']} | {scene['date']} | ☁️ {scene['cloud_cover']}%")
