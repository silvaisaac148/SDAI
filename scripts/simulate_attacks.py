"""Send fake packets to /events/ingest to exercise every detector without Npcap.

Useful for demos, validation, and dashboard testing on machines without packet
capture privileges.

Usage:
    python scripts/simulate_attacks.py                    # full demo (all 4 attacks)
    python scripts/simulate_attacks.py --only port_scan   # single scenario
    python scripts/simulate_attacks.py --only baseline    # just normal traffic
    python scripts/simulate_attacks.py --host http://127.0.0.1:8000 --rate 80
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

SCENARIOS = ("baseline", "port_scan", "brute_force", "dos", "malicious_ip", "all")

# Real public IPs with known GeoLite2 entries so they appear at real coordinates
# on the dashboard world map.
PUBLIC_IPS = [
    ("8.8.8.8",          "TCP", 443),   # Google US
    ("1.1.1.1",          "UDP", 53),    # Cloudflare AU
    ("142.250.190.78",   "TCP", 443),   # Google US
    ("167.99.7.55",      "TCP", 443),   # DigitalOcean NY
    ("89.38.97.196",     "TCP", 443),   # NL Naaldwijk
    ("185.130.44.108",   "UDP", 443),   # SE Stockholm
    ("193.107.216.31",   "TCP", 443),   # HK
]
LOCAL_HOSTS = ["192.168.1.10", "192.168.1.45", "10.0.0.12", "10.0.0.55"]

# Public IPs treated as attackers — chosen for geographic diversity so the world
# map shows hits across continents. NOT actual confirmed malicious hosts.
MALICIOUS_IPS = ["45.155.205.231", "185.220.101.5", "5.252.176.36"]

ATTACKER_PORT_SCAN   = "185.220.101.5"    # DE Brandenburg
ATTACKER_BRUTE_FORCE = "45.155.205.231"   # RU St Petersburg
ATTACKER_DOS         = "5.252.176.36"     # RU Moscow


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_pkt(
    src_ip: str,
    dst_ip: str,
    protocol: str = "TCP",
    src_port: Optional[int] = None,
    dst_port: Optional[int] = None,
    flags: Optional[str] = "A",
    length: int = 60,
) -> dict:
    return {
        "timestamp": now_iso(),
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "protocol": protocol,
        "src_port": src_port if src_port is not None else random.randint(1024, 65535),
        "dst_port": dst_port if dst_port is not None else 443,
        "flags": flags if protocol == "TCP" else None,
        "length": length,
    }


class Sender:
    def __init__(self, host: str, rate: int):
        self.host = host.rstrip("/")
        self.url = f"{self.host}/events/ingest"
        self.delay = 1.0 / max(1, rate)
        self.session = httpx.Client(timeout=2.0)
        self.sent = 0
        self.alerts = 0

    def send(self, pkt: dict) -> None:
        try:
            r = self.session.post(self.url, json=pkt)
            self.sent += 1
            if r.status_code == 201:
                triggered = r.json().get("alerts_triggered", 0)
                if triggered:
                    self.alerts += triggered
        except httpx.HTTPError as e:
            print(f"[!] request error: {e}", file=sys.stderr)
        time.sleep(self.delay)

    def close(self) -> None:
        self.session.close()


def scenario_baseline(s: Sender, packets: int = 60) -> None:
    print(f"[baseline] enviando {packets} paquetes legítimos...")
    for _ in range(packets):
        ext_ip, proto, dport = random.choice(PUBLIC_IPS)
        local = random.choice(LOCAL_HOSTS)
        outbound = random.random() < 0.6
        src, dst = (local, ext_ip) if outbound else (ext_ip, local)
        s.send(make_pkt(
            src_ip=src, dst_ip=dst, protocol=proto,
            dst_port=dport if outbound else random.randint(40000, 65000),
            flags=random.choice(["A", "PA", "SA"]) if proto == "TCP" else None,
            length=random.randint(60, 1400),
        ))


def scenario_port_scan(s: Sender, attacker: str = ATTACKER_PORT_SCAN, target: str = "192.168.1.45") -> None:
    print(f"[port_scan] {attacker} -> {target} (25 puertos distintos)")
    for port in (21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 161, 389, 443, 445, 587, 636, 873, 993, 995, 1080, 1433, 1521, 3306, 3389, 5432):
        s.send(make_pkt(src_ip=attacker, dst_ip=target, protocol="TCP", dst_port=port, flags="S", length=60))


def scenario_brute_force(s: Sender, attacker: str = ATTACKER_BRUTE_FORCE, target: str = "10.0.0.12") -> None:
    print(f"[brute_force] {attacker} -> {target}:22 (12 intentos SSH SYN)")
    for _ in range(12):
        s.send(make_pkt(src_ip=attacker, dst_ip=target, protocol="TCP", dst_port=22, flags="S", length=60))


def scenario_dos(s: Sender, attacker: str = ATTACKER_DOS, target: str = "10.0.0.55") -> None:
    print(f"[dos] {attacker} -> {target} (600 paquetes UDP en ráfaga)")
    original_delay = s.delay
    s.delay = 0  # flood as fast as possible
    try:
        for _ in range(600):
            s.send(make_pkt(src_ip=attacker, dst_ip=target, protocol="UDP", dst_port=80, length=64))
    finally:
        s.delay = original_delay


def scenario_malicious_ip(s: Sender) -> None:
    print(f"[malicious_ip] tráfico desde/hacia IPs en blacklist (asegura que blacklist incluye estas)")
    for ip in MALICIOUS_IPS:
        s.send(make_pkt(src_ip=ip, dst_ip="10.0.0.12", protocol="TCP", dst_port=443, flags="PA"))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SDAI attack simulator")
    p.add_argument("--host", default="http://127.0.0.1:8000", help="API base URL")
    p.add_argument("--only", choices=SCENARIOS, default="all", help="Run a single scenario (default: all)")
    p.add_argument("--rate", type=int, default=40, help="Packets per second (default 40)")
    p.add_argument("--baseline-packets", type=int, default=40, help="Number of baseline packets")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    s = Sender(args.host, args.rate)
    print(f"Target: {s.url}  | rate: {args.rate} pkt/s\n")

    try:
        if args.only in ("baseline", "all"):
            scenario_baseline(s, args.baseline_packets)
        if args.only in ("malicious_ip", "all"):
            scenario_malicious_ip(s)
        if args.only in ("port_scan", "all"):
            scenario_port_scan(s)
        if args.only in ("brute_force", "all"):
            scenario_brute_force(s)
        if args.only in ("dos", "all"):
            scenario_dos(s)
    finally:
        s.close()

    print(f"\nSent: {s.sent} packets  |  alerts triggered (reported by API): {s.alerts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
