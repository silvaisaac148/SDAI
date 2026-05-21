import os
import sys
import ipaddress
import hashlib
from pathlib import Path
from typing import Dict, Optional, Any

# Add workspace root to sys.path to allow imports from db
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "db" / "GeoLite2-City.mmdb"

# Lazy-loaded geoip2 module to prevent import errors if not installed
_geoip2_installed = False
try:
    import geoip2.database
    _geoip2_installed = True
except ImportError:
    pass


class GeoIPResolver:
    """Resolves IP addresses to geographical details (country, city, lat, lon)

    Supports local MaxMind GeoLite2 database, private IP identification, and robust mock fallback.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._reader = None
        self._tried_init = False
        
        # Known public IPs for mock resolution (development/testing)
        self.mock_ips = {
            "8.8.8.8": {
                "country": "Estados Unidos",
                "city": "Mountain View",
                "latitude": 37.4223,
                "longitude": -122.0847
            },
            "1.1.1.1": {
                "country": "Australia",
                "city": "Research",
                "latitude": -37.7000,
                "longitude": 145.1833
            },
            "9.9.9.9": {
                "country": "Suiza",
                "city": "Ginebra",
                "latitude": 46.2000,
                "longitude": 6.1500
            }
        }
        
        # Deterministic pool of mock locations for generic public IPs
        self.mock_countries = ["Alemania", "Canadá", "Reino Unido", "Japón", "Brasil", "España", "Países Bajos", "Singapur"]
        self.mock_cities = ["Fráncfort", "Toronto", "Londres", "Tokio", "São Paulo", "Madrid", "Ámsterdam", "Singapur"]
        self.mock_coords = [
            (50.1109, 8.6821),    # Frankfurt
            (43.6532, -79.3832),  # Toronto
            (51.5074, -0.1278),   # London
            (35.6762, 139.6503),  # Tokyo
            (-23.5505, -46.6333), # Sao Paulo
            (40.4168, -3.7038),   # Madrid
            (52.3676, 4.9041),    # Amsterdam
            (1.3521, 103.8198)    # Singapore
        ]

    def _init_reader(self) -> bool:
        """Initialize the GeoLite2 database reader if available."""
        if self._tried_init:
            return self._reader is not None
            
        self._tried_init = True
        
        if not _geoip2_installed:
            print("[GeoIP] Warning: 'geoip2' package is not installed. Falling back to Mock resolution.", file=sys.stderr)
            return False
            
        if not self.db_path.exists():
            print(f"[GeoIP] Warning: Database not found at '{self.db_path}'. Falling back to Mock resolution.", file=sys.stderr)
            return False
            
        try:
            self._reader = geoip2.database.Reader(str(self.db_path))
            print(f"[GeoIP] Successfully loaded local database: {self.db_path}", file=sys.stderr)
            return True
        except Exception as e:
            print(f"[GeoIP] Error loading local database: {e}. Falling back to Mock resolution.", file=sys.stderr)
            return False

    def is_private_ip(self, ip_str: str) -> bool:
        """Check if an IP address belongs to a private/local subnet."""
        try:
            ip = ipaddress.ip_address(ip_str)
            return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
        except ValueError:
            # If it's not a valid IP (e.g. malformed or a name), treat as private/local to be safe
            return True

    def resolve_ip(self, ip_str: str) -> Dict[str, Any]:
        """Resolve IP address to country, city, latitude, and longitude."""
        # 1. Private/Local IP Address check
        if self.is_private_ip(ip_str):
            return {
                "country": "Red Local",
                "city": "Red de Área Local",
                "latitude": None,
                "longitude": None
            }
            
        # 2. Database resolution (Real MaxMind MMDB)
        if self._init_reader():
            try:
                response = self._reader.city(ip_str)
                # Fallback to Spanish or English names
                country = (
                    response.country.names.get("es") or 
                    response.country.name or 
                    "Desconocido"
                )
                city = (
                    response.city.names.get("es") or 
                    response.city.name or 
                    "Desconocido"
                )
                return {
                    "country": country,
                    "city": city,
                    "latitude": response.location.latitude,
                    "longitude": response.location.longitude
                }
            except Exception as e:
                # If database lookup fails for a valid public IP, fall through to Mock Fallback
                pass

        # 3. Mock Fallback resolution (Known IPs)
        if ip_str in self.mock_ips:
            return self.mock_ips[ip_str]
            
        # 4. Deterministic Mock Fallback for any other public IP
        # Compute MD5 hash of IP address to get stable/deterministic values
        h = int(hashlib.md5(ip_str.encode("utf-8")).hexdigest(), 16)
        idx = h % len(self.mock_countries)
        
        lat, lon = self.mock_coords[idx]
        return {
            "country": self.mock_countries[idx],
            "city": self.mock_cities[idx],
            "latitude": lat,
            "longitude": lon
        }

    def close(self):
        """Close the reader connection if active."""
        if self._reader:
            try:
                self._reader.close()
            except Exception:
                pass
            self._reader = None
            self._tried_init = False
            
    def __del__(self):
        self.close()
