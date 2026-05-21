from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple


def check_port_scan(
    pkt_dict: dict,
    history: Dict[str, List[Tuple[int, datetime]]],  # src_ip -> list of (port, timestamp_dt)
    threshold: int,            # ports_per_minute (default 20)
    window: float = 60.0       # 60 seconds
) -> Optional[dict]:
    """Detect if a source IP has scanned N distinct destination ports within a time window.

    Args:
        pkt_dict: The normalized packet dictionary.
        history: The history state in memory.
        threshold: The port count threshold.
        window: The time window in seconds.
    """
    src_ip = pkt_dict.get("src_ip")
    dst_port = pkt_dict.get("dst_port")
    if not src_ip or dst_port is None:
        return None

    now = datetime.now(timezone.utc)
    
    # 1. Add current packet to history
    history[src_ip].append((dst_port, now))
    
    # 2. Clean old packets
    history[src_ip] = [
        (port, ts) for port, ts in history[src_ip]
        if (now - ts).total_seconds() <= window
    ]
    
    # 3. Calculate distinct ports
    distinct_ports = {port for port, ts in history[src_ip]}
    
    # 4. Check threshold
    if len(distinct_ports) >= threshold:
        severity = "alta" if len(distinct_ports) > 30 else "media"
        return {
            "threat_type": "port_scan",
            "severity": severity,
            "description": f"IP {src_ip} escaneó {len(distinct_ports)} puertos en {window}s. Umbral: {threshold}.",
            "details": {
                "ports_scanned": sorted(list(distinct_ports)),
                "window_seconds": window,
                "count": len(distinct_ports)
            }
        }
    return None
