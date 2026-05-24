"""Carga sostenida contra /events/ingest para validar throughput Sprint 7-8.

Mide capacidad del backend (batch writer + async queue) bajo presión sostenida.
Objetivo: 10,000 paquetes/min (167 pkt/s) sin pérdidas ni latencia descontrolada.

Uso:
    # Default: 10k pkt/min durante 60s
    python scripts/load_test.py

    # Personalizado
    python scripts/load_test.py --rate 200 --duration 30 --concurrency 50
    python scripts/load_test.py --host http://127.0.0.1:8000 --total 10000

Métricas:
    - throughput real (pkt/s)
    - latencia p50/p95/p99/max
    - tasa errores (4xx/5xx/timeout)
    - duración total
"""
from __future__ import annotations

import argparse
import asyncio
import random
import statistics
import sys
import time
from datetime import datetime, timezone
from typing import List, Tuple

import httpx

# Pool IPs para variedad realista
SRC_IPS = [f"192.168.1.{i}" for i in range(2, 254)]
DST_IPS = ["8.8.8.8", "1.1.1.1", "142.250.190.78", "10.0.0.1", "172.217.10.46"]
PROTOCOLS = ["TCP", "UDP", "ICMP"]
TCP_PORTS = [80, 443, 22, 3389, 8080, 25]
UDP_PORTS = [53, 123, 161, 500]


def random_packet() -> dict:
    """Genera packet sintético equivalente al output del decoder Scapy."""
    proto = random.choices(PROTOCOLS, weights=[70, 25, 5])[0]
    pkt = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "src_ip": random.choice(SRC_IPS),
        "dst_ip": random.choice(DST_IPS),
        "protocol": proto,
        "length": random.randint(64, 1500),
    }
    if proto == "TCP":
        pkt["src_port"] = random.randint(49152, 65535)
        pkt["dst_port"] = random.choice(TCP_PORTS)
        pkt["flags"] = random.choice(["S", "SA", "A", "FA", "PA"])
    elif proto == "UDP":
        pkt["src_port"] = random.randint(49152, 65535)
        pkt["dst_port"] = random.choice(UDP_PORTS)
    return pkt


async def send_one(client: httpx.AsyncClient, url: str) -> Tuple[float, int]:
    """Envía un packet, retorna (latencia_ms, status_code). status=0 en timeout/error."""
    pkt = random_packet()
    start = time.perf_counter()
    try:
        r = await client.post(url, json=pkt, timeout=10.0)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms, r.status_code
    except (httpx.TimeoutException, httpx.HTTPError):
        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms, 0


async def worker(
    name: int,
    client: httpx.AsyncClient,
    url: str,
    sem: asyncio.Semaphore,
    schedule: asyncio.Queue,
    results: List[Tuple[float, int]],
) -> None:
    """Consume del schedule queue, dispara request, almacena resultado."""
    while True:
        try:
            await schedule.get()
        except asyncio.CancelledError:
            break
        try:
            async with sem:
                lat, code = await send_one(client, url)
                results.append((lat, code))
        finally:
            schedule.task_done()


async def scheduler(schedule: asyncio.Queue, total: int, rate: float) -> None:
    """Emite N tokens en el queue a la tasa pedida (pkt/s)."""
    interval = 1.0 / rate if rate > 0 else 0.0
    for _ in range(total):
        await schedule.put(1)
        if interval > 0:
            await asyncio.sleep(interval)


async def run_load(host: str, total: int, rate: float, concurrency: int) -> dict:
    url = f"{host.rstrip('/')}/events/ingest"
    results: List[Tuple[float, int]] = []
    schedule: asyncio.Queue = asyncio.Queue()
    sem = asyncio.Semaphore(concurrency)

    limits = httpx.Limits(max_keepalive_connections=concurrency, max_connections=concurrency * 2)
    async with httpx.AsyncClient(limits=limits) as client:
        workers = [
            asyncio.create_task(worker(i, client, url, sem, schedule, results))
            for i in range(concurrency)
        ]

        wall_start = time.perf_counter()
        await scheduler(schedule, total, rate)
        await schedule.join()
        wall_elapsed = time.perf_counter() - wall_start

        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

    latencies = [lat for lat, _ in results]
    codes = [c for _, c in results]
    ok = sum(1 for c in codes if 200 <= c < 300)
    client_err = sum(1 for c in codes if 400 <= c < 500)
    server_err = sum(1 for c in codes if c >= 500)
    timeouts = sum(1 for c in codes if c == 0)

    latencies_sorted = sorted(latencies)
    def pct(p: float) -> float:
        if not latencies_sorted:
            return 0.0
        idx = min(int(len(latencies_sorted) * p / 100), len(latencies_sorted) - 1)
        return latencies_sorted[idx]

    return {
        "total_sent": len(results),
        "wall_seconds": wall_elapsed,
        "throughput_pps": len(results) / wall_elapsed if wall_elapsed > 0 else 0,
        "throughput_per_min": (len(results) / wall_elapsed * 60) if wall_elapsed > 0 else 0,
        "ok_2xx": ok,
        "client_err_4xx": client_err,
        "server_err_5xx": server_err,
        "timeouts": timeouts,
        "error_rate_pct": ((client_err + server_err + timeouts) / len(results) * 100) if results else 0,
        "latency_ms": {
            "min": min(latencies) if latencies else 0,
            "p50": pct(50),
            "p95": pct(95),
            "p99": pct(99),
            "max": max(latencies) if latencies else 0,
            "mean": statistics.mean(latencies) if latencies else 0,
        },
    }


def print_report(r: dict, target_rate: float) -> None:
    pad = 26
    print()
    print("=" * 60)
    print(" SDAI LOAD TEST — RESULTADO")
    print("=" * 60)
    print(f" {'Paquetes enviados':<{pad}} {r['total_sent']}")
    print(f" {'Duración total':<{pad}} {r['wall_seconds']:.2f} s")
    print(f" {'Throughput real':<{pad}} {r['throughput_pps']:.1f} pkt/s ({r['throughput_per_min']:.0f} pkt/min)")
    print(f" {'Throughput objetivo':<{pad}} {target_rate:.1f} pkt/s ({target_rate*60:.0f} pkt/min)")
    print()
    print(f" {'OK (2xx)':<{pad}} {r['ok_2xx']}")
    print(f" {'Errores cliente (4xx)':<{pad}} {r['client_err_4xx']}")
    print(f" {'Errores server (5xx)':<{pad}} {r['server_err_5xx']}")
    print(f" {'Timeouts':<{pad}} {r['timeouts']}")
    print(f" {'Tasa error':<{pad}} {r['error_rate_pct']:.2f} %")
    print()
    lat = r["latency_ms"]
    print(f" {'Latencia min':<{pad}} {lat['min']:.1f} ms")
    print(f" {'Latencia p50':<{pad}} {lat['p50']:.1f} ms")
    print(f" {'Latencia p95':<{pad}} {lat['p95']:.1f} ms")
    print(f" {'Latencia p99':<{pad}} {lat['p99']:.1f} ms")
    print(f" {'Latencia max':<{pad}} {lat['max']:.1f} ms")
    print(f" {'Latencia media':<{pad}} {lat['mean']:.1f} ms")
    print("=" * 60)

    # Veredicto
    target_min = target_rate * 60
    pass_throughput = r["throughput_per_min"] >= target_min * 0.95
    pass_errors = r["error_rate_pct"] < 1.0
    pass_latency = lat["p95"] < 500
    overall = pass_throughput and pass_errors and pass_latency
    verdict = "✅ PASS" if overall else "❌ FAIL"
    print(f" VEREDICTO: {verdict}")
    print(f"   throughput ≥ 95% objetivo: {'✅' if pass_throughput else '❌'}")
    print(f"   tasa error < 1%:           {'✅' if pass_errors else '❌'}")
    print(f"   p95 < 500ms:               {'✅' if pass_latency else '❌'}")
    print("=" * 60)


def main() -> int:
    p = argparse.ArgumentParser(description="Load test SDAI ingest endpoint")
    p.add_argument("--host", default="http://127.0.0.1:8000", help="Backend URL base")
    p.add_argument("--rate", type=float, default=167.0, help="Paquetes/segundo (default 167 = 10k/min)")
    p.add_argument("--duration", type=int, default=60, help="Segundos de carga (default 60)")
    p.add_argument("--total", type=int, default=0, help="Override: total paquetes (ignora duration)")
    p.add_argument("--concurrency", type=int, default=50, help="Workers concurrentes (default 50)")
    args = p.parse_args()

    total = args.total if args.total > 0 else int(args.rate * args.duration)
    print(f"[load_test] host={args.host} rate={args.rate} pkt/s total={total} concurrency={args.concurrency}")
    print(f"[load_test] enviando {total} packets a {args.host}/events/ingest ...")

    r = asyncio.run(run_load(args.host, total, args.rate, args.concurrency))
    print_report(r, args.rate)
    return 0


if __name__ == "__main__":
    sys.exit(main())
