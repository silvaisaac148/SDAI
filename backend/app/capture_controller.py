"""Remote-controlled Scapy sniffer.

Wraps `scapy.sendrecv.AsyncSniffer` so the dashboard / API can start, stop,
pause and resume packet capture without restarting the FastAPI process.

Each decoded packet is POSTed to the local `/events/ingest` endpoint — the same
path used by `capture/sniffer.py`, so the detection pipeline, SSE broadcast and
notification fan-out remain unchanged.

Requires Npcap on Windows + admin privileges. If Scapy raises at start time
the error is captured in `last_error` so the dashboard can surface it instead
of failing silently.
"""
from __future__ import annotations

import sys
import threading
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import settings


class CaptureController:
    def __init__(self) -> None:
        self._sniffer = None  # scapy.sendrecv.AsyncSniffer
        self._paused = False
        self._lock = threading.Lock()
        self._last_error: Optional[str] = None
        self._started_at: Optional[datetime] = None
        self._interface: Optional[str] = None
        self._bpf: Optional[str] = None
        self._http = httpx.Client(timeout=0.6)
        self._ingest_url = f"http://{settings.API_HOST}:{settings.API_PORT}/events/ingest"
        self._pkt_count = 0
        self._dropped_count = 0

    # ---------- public API ----------

    def status(self) -> dict:
        running = bool(self._sniffer and getattr(self._sniffer, "running", False))
        return {
            "running": running,
            "paused": self._paused,
            "interface": self._interface or settings.CAPTURE_INTERFACE,
            "bpf": self._bpf,
            "last_error": self._last_error,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "packets_captured": self._pkt_count,
            "packets_dropped": self._dropped_count,
        }

    def start(self, interface: Optional[str] = None, bpf: str = "ip") -> dict:
        with self._lock:
            if self._sniffer and getattr(self._sniffer, "running", False):
                return {"status": "already_running", **self.status()}

            iface = interface or settings.CAPTURE_INTERFACE
            self._interface = iface
            self._bpf = bpf
            self._pkt_count = 0
            self._dropped_count = 0
            self._last_error = None

            try:
                # Lazy import — Scapy can be slow to import and we don't want to
                # pay the cost at API startup when capture may never be used.
                from scapy.sendrecv import AsyncSniffer  # noqa: WPS433

                self._sniffer = AsyncSniffer(
                    iface=iface,
                    prn=self._on_packet,
                    filter=bpf,
                    store=False,
                )
                self._sniffer.start()
                self._paused = False
                self._started_at = datetime.now(timezone.utc)
                return {"status": "started", **self.status()}
            except Exception as e:  # pragma: no cover - depends on Npcap/admin
                self._last_error = str(e)
                self._sniffer = None
                print(f"[capture] start failed: {e}", file=sys.stderr)
                return {"status": "error", "error": str(e), **self.status()}

    def stop(self) -> dict:
        with self._lock:
            if self._sniffer and getattr(self._sniffer, "running", False):
                try:
                    self._sniffer.stop()
                except Exception as e:  # pragma: no cover
                    self._last_error = str(e)
                    print(f"[capture] stop error: {e}", file=sys.stderr)
            self._sniffer = None
            self._paused = False
            self._started_at = None
            return {"status": "stopped", **self.status()}

    def pause(self) -> dict:
        self._paused = True
        return {"status": "paused", **self.status()}

    def resume(self) -> dict:
        self._paused = False
        return {"status": "running", **self.status()}

    # ---------- internals ----------

    def _on_packet(self, pkt) -> None:
        if self._paused:
            return
        try:
            from capture.decoder import decode  # noqa: WPS433

            decoded = decode(pkt)
            if decoded is None:
                return
            self._pkt_count += 1
            try:
                self._http.post(self._ingest_url, json=decoded)
            except httpx.HTTPError:
                self._dropped_count += 1
        except Exception as e:  # never let a bad packet kill the sniffer thread
            print(f"[capture] packet handling error: {e}", file=sys.stderr)


# Singleton — imported by routers.capture and (optionally) main.py lifespan
controller = CaptureController()
