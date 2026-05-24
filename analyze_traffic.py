"""Analyze traffic.jsonl and print stats."""

import json
import collections
from pathlib import Path
from collections import defaultdict

OUTPUT = Path(__file__).parent / "traffic.jsonl"

with open(OUTPUT, encoding="utf-8") as f:
    packets_data = [json.loads(l) for l in f if l.strip()]

total = len(packets_data)

def bar(n, total, width=20):
    filled = int(n / total * width) if total else 0
    return "#" * filled + "." * (width - filled)

protos    = collections.Counter(p["protocol"] for p in packets_data)
src_ips   = collections.Counter(p["src_ip"]   for p in packets_data)
dst_ips   = collections.Counter(p["dst_ip"]   for p in packets_data)
dst_ports = collections.Counter(
    p["dst_port"] for p in packets_data if p["dst_port"] is not None
)

PORT_NAMES = {
    80:"HTTP", 443:"HTTPS/QUIC", 53:"DNS", 22:"SSH",
    21:"FTP", 25:"SMTP", 110:"POP3", 143:"IMAP",
    3306:"MySQL", 5432:"PostgreSQL", 8080:"HTTP-alt",
    51820:"WireGuard", 123:"NTP", 88:"Kerberos/STUN",
}

print()
print("=" * 65)
print("  SDAI -- ANALISIS DE TRAFICO CAPTURADO  (%d paquetes)" % total)
print("=" * 65)

print("\n-- PROTOCOLOS --------------------------------------------------")
for proto, n in protos.most_common():
    pct = n / total * 100
    print("  %-8s  %s  %3d  (%5.1f%%)" % (proto, bar(n, total), n, pct))

print("\n-- TOP 8 IPs ORIGEN --------------------------------------------")
for ip, n in src_ips.most_common(8):
    print("  %-18s  %s  %3d pkts" % (ip, bar(n, total, 15), n))

print("\n-- TOP 8 IPs DESTINO -------------------------------------------")
for ip, n in dst_ips.most_common(8):
    print("  %-18s  %s  %3d pkts" % (ip, bar(n, total, 15), n))

print("\n-- TOP 10 PUERTOS DESTINO --------------------------------------")
for port, n in dst_ports.most_common(10):
    svc = PORT_NAMES.get(port, "?")
    print("  :%5d  %-18s  %3d pkts" % (port, svc, n))

# Pre-analisis amenazas
print("\n-- PRE-ANALISIS AMENAZAS (preview Sprint 3-4) ------------------")

src_port_variety = defaultdict(set)
for p in packets_data:
    if p["dst_port"]:
        src_port_variety[p["src_ip"]].add(p["dst_port"])

candidates = [(ip, ports) for ip, ports in src_port_variety.items() if len(ports) >= 5]
if candidates:
    print("  [!] Posible port scan (src con >=5 puertos dst distintos):")
    for ip, ports in sorted(candidates, key=lambda x: -len(x[1])):
        print("      %s -> %d puertos: %s" % (ip, len(ports), sorted(ports)))
else:
    print("  [OK] Sin indicios de port scan")

heavy = [(ip, n) for ip, n in src_ips.items() if n >= 15]
if heavy:
    print("  [!] Posible DoS/trafico intenso:")
    for ip, n in sorted(heavy, key=lambda x: -x[1]):
        print("      %s -> %d paquetes" % (ip, n))
else:
    print("  [OK] Sin src IP dominante (>=15 pkts)")

# Protocolo dominante
top_proto = protos.most_common(1)[0]
if top_proto[1] / total > 0.9:
    print("  [!] Protocolo %s domina (%.0f%%) -- trafico muy homogeneo" % (
        top_proto[0], top_proto[1] / total * 100))

print()
print("=" * 65)
print("  Capturador cerrado. Analisis completo.")
print("=" * 65)
print()
