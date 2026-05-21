from typing import Optional, List


def check_malicious_ip(
    pkt_dict: dict,
    blacklist: List[str]
) -> Optional[dict]:
    """Check if the source or destination IP belongs to a configured blacklist.

    Args:
        pkt_dict: The normalized packet dictionary.
        blacklist: The list of blacklisted IP strings.
    """
    src_ip = pkt_dict.get("src_ip")
    dst_ip = pkt_dict.get("dst_ip")
    
    if not src_ip or not blacklist:
        return None
        
    # Check if either src_ip or dst_ip is in the blacklist
    if src_ip in blacklist:
        return {
            "threat_type": "malicious_ip",
            "severity": "alta",
            "description": f"Tráfico de red originado por IP maliciosa en lista negra: {src_ip}.",
            "details": {
                "blocked_ip": src_ip,
                "direction": "entrada"
            }
        }
    elif dst_ip in blacklist:
        return {
            "threat_type": "malicious_ip",
            "severity": "alta",
            "description": f"Tráfico de red destinado a IP maliciosa en lista negra: {dst_ip}.",
            "details": {
                "blocked_ip": dst_ip,
                "direction": "salida"
            }
        }
    return None
