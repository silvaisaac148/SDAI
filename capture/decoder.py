"""Decode Scapy packets into normalized dicts for downstream analysis."""

from datetime import datetime, timezone
from typing import Optional

from scapy.layers.inet import ICMP, IP, TCP, UDP
from scapy.packet import Packet


def decode(pkt: Packet) -> Optional[dict]:
    """Extract IP/transport fields from a Scapy packet.

    Returns None if packet has no IP layer (we ignore link-level only frames in Sprint 1).
    """
    if IP not in pkt:
        return None

    ip = pkt[IP]
    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "src_ip": ip.src,
        "dst_ip": ip.dst,
        "protocol": _protocol_name(pkt),
        "src_port": None,
        "dst_port": None,
        "flags": None,
        "length": len(pkt),
    }

    if TCP in pkt:
        tcp = pkt[TCP]
        out["src_port"] = int(tcp.sport)
        out["dst_port"] = int(tcp.dport)
        out["flags"] = str(tcp.flags)
    elif UDP in pkt:
        udp = pkt[UDP]
        out["src_port"] = int(udp.sport)
        out["dst_port"] = int(udp.dport)
    elif ICMP in pkt:
        icmp = pkt[ICMP]
        out["flags"] = f"type={icmp.type},code={icmp.code}"

    return out


def _protocol_name(pkt: Packet) -> str:
    if TCP in pkt:
        return "TCP"
    if UDP in pkt:
        return "UDP"
    if ICMP in pkt:
        return "ICMP"
    return f"IP/{pkt[IP].proto}"
