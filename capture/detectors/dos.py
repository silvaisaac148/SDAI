from datetime import datetime, timezone
from typing import Optional, Dict, List


def check_dos(
    pkt_dict: dict,
    history: Dict[str, List[datetime]],  # src_ip -> list of timestamps
    pps_threshold: int,        # packets_per_second (default 500)
    window: float = 1.0        # 1.0 seconds
) -> Optional[dict]:
    """Detect if a source IP is sending an excessively high rate of packets (DoS).

    Args:
        pkt_dict: The normalized packet dictionary.
        history: The history state in memory.
        pps_threshold: Packets per second threshold.
        window: The time window in seconds.
    """
    src_ip = pkt_dict.get("src_ip")
    if not src_ip:
        return None
        
    now = datetime.now(timezone.utc)
    
    # 1. Add current packet to history
    history[src_ip].append(now)
    
    # 2. Clean old packets
    history[src_ip] = [
        ts for ts in history[src_ip]
        if (now - ts).total_seconds() <= window
    ]
    
    # 3. Calculate packets per second
    pps = len(history[src_ip])
    
    # 4. Check threshold
    if pps >= pps_threshold:
        return {
            "threat_type": "dos",
            "severity": "alta",
            "description": f"Ataque DoS detectado desde {src_ip}. Tasa de tráfico: {pps} pps. Umbral: {pps_threshold} pps.",
            "details": {
                "pps": pps,
                "window_seconds": window
            }
        }
    return None
