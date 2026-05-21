import os
import sys
from pathlib import Path
import httpx

# Add workspace root to sys.path
ROOT = Path(__file__).resolve().parent.parent
DB_DIR = ROOT / "db"
DB_PATH = DB_DIR / "GeoLite2-City.mmdb"

MIRROR_URL = "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb"

def download_geoip():
    """Download GeoLite2-City.mmdb from the public mirror."""
    print("=== Descargador de Base de Datos GeoIP ===")
    
    # Ensure db directory exists
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    if DB_PATH.exists():
        print(f"La base de datos ya existe en: {DB_PATH}")
        overwrite = input("¿Deseas sobreescribirla? (s/n): ").strip().lower()
        if overwrite not in ('s', 'si', 'y', 'yes'):
            print("Cancelado.")
            return
            
    print(f"Descargando GeoLite2-City.mmdb desde:\n{MIRROR_URL}")
    print("Esto puede tardar unos momentos (aprox. 30MB)...")
    
    try:
        # Use httpx with a streaming request to show progress
        with httpx.stream("GET", MIRROR_URL, follow_redirects=True, timeout=60.0) as response:
            if response.status_code != 200:
                print(f"Error al descargar: Código de estado HTTP {response.status_code}", file=sys.stderr)
                return
                
            total_bytes = int(response.headers.get("content-length", 0))
            downloaded = 0
            
            with open(DB_PATH, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=1024 * 1024):  # 1MB chunks
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_bytes > 0:
                            percent = (downloaded / total_bytes) * 100
                            print(f"\rProgreso: {percent:.1f}% ({downloaded / (1024*1024):.1f}MB / {total_bytes / (1024*1024):.1f}MB)", end="", flush=True)
                        else:
                            print(f"\rDescargados: {downloaded / (1024*1024):.1f}MB", end="", flush=True)
                            
        print("\n\n✅ Descarga finalizada exitosamente.")
        print(f"Base de datos guardada en: {DB_PATH}")
        
    except Exception as e:
        print(f"\n❌ Error durante la descarga: {e}", file=sys.stderr)
        print("El sistema utilizará el modo Mock de fallback de manera automática.", file=sys.stderr)

if __name__ == "__main__":
    download_geoip()
