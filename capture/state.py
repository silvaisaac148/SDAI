import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add backend directory to sys.path to enable easy importing of app.db
ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from app.db.supabase_client import get_client, execute_with_retry
from app.utils.logger import logger
from capture.detectors import check_port_scan, check_brute_force, check_malicious_ip, check_dos
from capture.geoip_resolver import GeoIPResolver


try:
    from app.notifications import notify_alert as _notify_alert
except Exception:  # pragma: no cover - notifications optional in dev
    def _notify_alert(alert):
        return None

DEFAULT_CONFIGS = {
    "port_scan_threshold": {"ports_per_minute": 20},
    "brute_force_threshold": {"failed_attempts": 5, "window_seconds": 60},
    "dos_threshold": {"packets_per_second": 500},
    "blacklist_ips": []
}


class DetectionStateManager:
    """Manages sliding window histories in memory and orchestrates threat detectors."""

    def __init__(self):
        self.port_scan_history = defaultdict(list)
        self.brute_force_history = defaultdict(list)
        self.dos_history = defaultdict(list)

        self.alert_cooldowns: Dict[tuple, datetime] = {}  # (src_ip, threat_type) -> last_alert_time

        # Global packet timestamps for system-wide pps KPI (sliding window 60s)
        self.global_packet_timestamps: List[datetime] = []
        self.pps_window_seconds = 60.0

        # Sensor boot timestamp (uptime KPI)
        self.started_at = datetime.now(timezone.utc)

        # Initialize GeoIP resolver
        self.geoip = GeoIPResolver()

        # Config cache
        self.configs = DEFAULT_CONFIGS.copy()
        self.last_config_refresh = datetime.min.replace(tzinfo=timezone.utc)
        self.config_refresh_interval = timedelta(seconds=10)  # Refresh config every 10s

    def _refresh_configs_if_needed(self) -> None:
        """Fetch latest configs from Supabase and cache them, with interval throttling."""
        now = datetime.now(timezone.utc)
        if now - self.last_config_refresh < self.config_refresh_interval:
            return
            
        self.last_config_refresh = now
        client = get_client()
        if client is None:
            return
            
        try:
            res = execute_with_retry(lambda c: c.table("configurations").select("*"))
            if res.data:
                for r in res.data:
                    key = r["key"]
                    val = r["value"]
                    self.configs[key] = val
        except Exception as e:
            logger.warning(f"Failed to refresh configs from Supabase: {e}")


    def process_packet(self, pkt_dict: dict, event_id: Optional[int] = None, db_insert: bool = True) -> List[dict]:
        """Process a decoded packet dictionary, run all detectors, and return triggered alerts.

        Args:
            pkt_dict: The normalized packet dictionary.
            event_id: The ID of the saved event in the events table.
            db_insert: If True, immediately inserts alerts to the database and notifies.
        """
        self._refresh_configs_if_needed()

        # Track packet timestamp for global pps KPI
        now_ts = datetime.now(timezone.utc)
        self.global_packet_timestamps.append(now_ts)
        cutoff = now_ts - timedelta(seconds=self.pps_window_seconds)
        # Prune in place (cheap when window is small)
        self.global_packet_timestamps = [t for t in self.global_packet_timestamps if t >= cutoff]

        triggered_alerts = []
        src_ip = pkt_dict.get("src_ip")
        if not src_ip:
            return triggered_alerts
            
        # Get threshold values
        port_scan_thresh = self.configs.get("port_scan_threshold", {}).get("ports_per_minute", 20)
        
        bf_config = self.configs.get("brute_force_threshold", {})
        bf_attempts = bf_config.get("failed_attempts", 5)
        bf_window = bf_config.get("window_seconds", 60)
        
        dos_thresh = self.configs.get("dos_threshold", {}).get("packets_per_second", 500)
        
        blacklist = self.configs.get("blacklist_ips", [])
        
        # 1. Check Malicious IP
        alert = check_malicious_ip(pkt_dict, blacklist)
        if alert:
            triggered_alerts.append(alert)
            
        # 2. Check Port Scan
        alert = check_port_scan(pkt_dict, self.port_scan_history, port_scan_thresh)
        if alert:
            triggered_alerts.append(alert)
            
        # 3. Check Brute Force
        alert = check_brute_force(pkt_dict, self.brute_force_history, bf_attempts, bf_window)
        if alert:
            triggered_alerts.append(alert)
            
        # 4. Check DoS
        alert = check_dos(pkt_dict, self.dos_history, dos_thresh)
        if alert:
            triggered_alerts.append(alert)
            
        # Deduplicate and save alerts
        saved_alerts = []
        for alert_dict in triggered_alerts:
            threat_type = alert_dict["threat_type"]
            cooldown_key = (src_ip, threat_type)
            now = datetime.now(timezone.utc)
            
            # Check if this alert type is in cooldown for this IP
            if cooldown_key in self.alert_cooldowns:
                last_alert_time = self.alert_cooldowns[cooldown_key]
                if (now - last_alert_time).total_seconds() < 30.0:
                    continue  # Skip to avoid spamming
                    
            # Update cooldown timestamp
            self.alert_cooldowns[cooldown_key] = now
            
            # Decorate alert with event_id + src_ip (for dashboard rendering)
            alert_dict["event_id"] = event_id
            alert_dict["src_ip"] = src_ip
            alert_dict["created_at"] = now.isoformat()

            # Resolve GeoIP location details
            geo_info = self.geoip.resolve_ip(src_ip)
            alert_dict.update(geo_info)

            if db_insert:
                # Insert alert to database — capture returned row to get real id
                client = get_client()
                if client is not None:
                    try:
                        payload = {
                            "event_id": event_id,
                            "threat_type": threat_type,
                            "severity": alert_dict["severity"],
                            "description": alert_dict["description"],
                            "notified": False,
                            "country": geo_info["country"],
                            "city": geo_info["city"],
                            "latitude": geo_info["latitude"],
                            "longitude": geo_info["longitude"],
                        }
                        res = execute_with_retry(lambda c: c.table("alerts").insert(payload))
                        if res.data:
                            alert_dict["id"] = res.data[0].get("id")
                            alert_dict["created_at"] = res.data[0].get("created_at", alert_dict["created_at"])
                    except Exception as e:
                        logger.error(f"Error inserting alert to Supabase: {e}", exc_info=True)

                saved_alerts.append(alert_dict)
                logger.info(
                    f"🚨 [ALERTA] {threat_type.upper()} | {alert_dict['description']} | Ubicación: {geo_info['city']}, {geo_info['country']}",
                    extra={"threat_type": threat_type, "severity": alert_dict["severity"], "city": geo_info["city"], "country": geo_info["country"]}
                )

                # Fan-out async notifications (Telegram/Email) per severity policy
                _notify_alert(alert_dict)

            else:
                saved_alerts.append(alert_dict)

        return saved_alerts


    def current_pps(self, window_seconds: float = 1.0) -> int:
        """Return packets observed in the most recent N seconds (system-wide PPS)."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=window_seconds)
        return sum(1 for t in self.global_packet_timestamps if t >= cutoff)

    def pps_history(self, buckets: int = 30, bucket_seconds: float = 2.0) -> List[int]:
        """Bucket recent packet timestamps into a list of counts (oldest first)."""
        if not self.global_packet_timestamps:
            return [0] * buckets
        now = datetime.now(timezone.utc)
        result = []
        for i in range(buckets - 1, -1, -1):
            end = now - timedelta(seconds=i * bucket_seconds)
            start = end - timedelta(seconds=bucket_seconds)
            count = sum(1 for t in self.global_packet_timestamps if start <= t < end)
            result.append(count)
        return result

    def uptime_seconds(self) -> int:
        return int((datetime.now(timezone.utc) - self.started_at).total_seconds())

