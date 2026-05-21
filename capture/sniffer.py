"""Scapy sniffer entrypoint. Requires Npcap on Windows + admin privileges."""

import argparse
import json
import sys
from typing import Optional

from scapy.sendrecv import sniff

from capture.decoder import decode


import httpx
from pathlib import Path

# Add backend to path to load settings
ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

try:
    from app.config import settings
    API_URL = f"http://{settings.API_HOST}:{settings.API_PORT}/events/ingest"
except Exception:
    API_URL = "http://127.0.0.1:8000/events/ingest"


def packet_handler(pkt) -> None:
    """Callback invoked by Scapy for each captured packet."""
    decoded = decode(pkt)
    if decoded is None:
        return
    
    # 1. Print packet JSON to stdout
    print(json.dumps(decoded, ensure_ascii=False))
    
    # 2. Ingest to API for threat detection and Live Stream
    try:
        httpx.post(API_URL, json=decoded, timeout=0.5)
    except Exception as e:
        print(f"[sniffer] API ingest warning: {e}", file=sys.stderr)


def start_capture(iface: Optional[str], count: int, bpf_filter: Optional[str] = None) -> None:
    """Start packet capture loop.

    Args:
        iface: NIC name (e.g. "Wi-Fi", "Ethernet"). None = default.
        count: Stop after N packets. 0 = infinite.
        bpf_filter: BPF expression (e.g. "tcp or udp"). None = capture all.
    """
    print(f"[sniffer] iface={iface!r} count={count} filter={bpf_filter!r}", file=sys.stderr)
    sniff(iface=iface, prn=packet_handler, count=count, filter=bpf_filter, store=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="SDAI packet sniffer")
    parser.add_argument("-i", "--iface", default=None, help="Network interface name")
    parser.add_argument("-c", "--count", type=int, default=100, help="Packet count (0=infinite)")
    parser.add_argument("-f", "--filter", default="ip", help="BPF filter (default: ip)")
    args = parser.parse_args()
    start_capture(args.iface, args.count, args.filter)


if __name__ == "__main__":
    main()
