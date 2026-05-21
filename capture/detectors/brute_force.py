from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple

# Auth-by-connection services where SYN-storms genuinely indicate brute force.
# HTTP/HTTPS excluded: login bruteforce there is per-request and requires DPI/L7
# detection, not L3/L4 SYN counts.
CRITICAL_PORTS = {21, 22, 23, 3389}
PORT_SERVICE = {21: "FTP", 22: "SSH", 23: "Telnet", 3389: "RDP"}


def check_brute_force(
    pkt_dict: dict,
    history: Dict[str, List[Tuple[int, datetime]]],  # src_ip -> list of (port, timestamp_dt)
    attempts_threshold: int,   # failed_attempts (default 5)
    window: float = 60.0       # window_seconds (default 60)
) -> Optional[dict]:
    """Detect brute-force attempts on auth-by-connection services (SSH/FTP/Telnet/RDP).

    Only TCP SYN packets count as attempts — a SYN flood without auth-port targeting
    is DoS, not brute force.
    """
    src_ip = pkt_dict.get("src_ip")
    dst_port = pkt_dict.get("dst_port")
    protocol = pkt_dict.get("protocol")
    flags = pkt_dict.get("flags") or ""

    if not src_ip or dst_port not in CRITICAL_PORTS:
        return None
    if protocol != "TCP" or "S" not in flags:
        return None

    now = datetime.now(timezone.utc)
    
    # 1. Add current packet to history
    history[src_ip].append((dst_port, now))
    
    # 2. Clean old packets
    history[src_ip] = [
        (port, ts) for port, ts in history[src_ip]
        if (now - ts).total_seconds() <= window
    ]
    
    # 3. Count attempts on the specific destination port
    attempts_on_port = [port for port, ts in history[src_ip] if port == dst_port]
    count = len(attempts_on_port)
    
    if count >= attempts_threshold:
        severity = "alta" if count > 15 else "media"
        service = PORT_SERVICE.get(dst_port, "auth")
        return {
            "threat_type": "brute_force",
            "severity": severity,
            "description": f"Posible brute force detectado desde {src_ip} al servicio {service} (puerto {dst_port}). {count} intentos en {window}s. Umbral: {attempts_threshold}.",
            "details": {
                "port": dst_port,
                "service": service,
                "window_seconds": window,
                "count": count,
            },
        }
    return None
