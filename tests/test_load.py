"""Tests carga in-process Sprint 7-8.

Verifica que el batch_writer encola y procesa volumen alto sin perder paquetes
ni saturar el queue. Usa cliente FastAPI directo (sin red) y Supabase mockeado,
así corre en CI sin credenciales ni servidor externo.

Target Sprint 7-8: 10,000 paquetes/min = 167 pkt/s sostenido.
En tests usamos volumen reducido (500 paquetes) para mantener CI rápido,
pero el script `scripts/load_test.py` ejecuta el target completo contra
un backend real.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.batch_writer import EventBatchWriter


def _fake_packet(i: int) -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "src_ip": f"192.168.1.{(i % 250) + 2}",
        "dst_ip": "8.8.8.8",
        "protocol": "TCP",
        "src_port": 49152 + (i % 1000),
        "dst_port": 443,
        "flags": "PA",
        "length": 128,
    }


@pytest.mark.asyncio
async def test_batch_writer_high_volume_no_loss():
    """500 paquetes encolados → batch writer los procesa todos sin pérdidas."""
    writer = EventBatchWriter(batch_size=100, flush_interval=0.2)
    inserted_total = 0

    with patch("app.db.batch_writer.get_client", return_value=MagicMock()), \
         patch("app.db.batch_writer.execute_with_retry") as mock_exec:

        def capture_insert(builder):
            nonlocal inserted_total
            mock_c = MagicMock()
            builder(mock_c)
            batch = mock_c.table().insert.call_args[0][0]
            inserted_total += len(batch)
            return MagicMock(data=[{"id": i} for i in range(len(batch))])

        mock_exec.side_effect = capture_insert

        writer.start()
        for i in range(500):
            await writer.enqueue(_fake_packet(i))
        await writer.stop()

    assert inserted_total == 500, f"esperados 500 eventos insertados, recibidos {inserted_total}"


@pytest.mark.asyncio
async def test_batch_writer_respects_batch_size():
    """Steady-state worker agrupa hasta batch_size. Encola gradualmente
    para que el worker tenga oportunidad de drenar entre lotes (el shutdown
    flush legítimamente puede emitir un batch mayor con leftovers)."""
    writer = EventBatchWriter(batch_size=50, flush_interval=0.1)
    batch_sizes: list[int] = []

    with patch("app.db.batch_writer.get_client", return_value=MagicMock()), \
         patch("app.db.batch_writer.execute_with_retry") as mock_exec:

        def capture(builder):
            mock_c = MagicMock()
            builder(mock_c)
            batch_sizes.append(len(mock_c.table().insert.call_args[0][0]))
            return MagicMock(data=[])

        mock_exec.side_effect = capture

        writer.start()
        # Encolar 250 en grupos de 25 con pausas → worker drena en pasos
        for chunk_start in range(0, 250, 25):
            for i in range(chunk_start, chunk_start + 25):
                await writer.enqueue(_fake_packet(i))
            await asyncio.sleep(0.15)  # > flush_interval para forzar drenaje
        await writer.stop()

    assert sum(batch_sizes) == 250, f"total insertado: {sum(batch_sizes)}"
    # Worker batches no exceden batch_size; último batch (shutdown flush) puede ser parcial
    assert all(sz <= 50 for sz in batch_sizes), f"batch sobrepasó tamaño: {batch_sizes}"
    assert len(batch_sizes) >= 5, f"esperados ≥5 batches, hubo {len(batch_sizes)}: {batch_sizes}"


def test_ingest_endpoint_burst_no_supabase():
    """200 POST /events/ingest sin Supabase → 100% éxito vía in-memory queue."""
    with patch("app.routers.events.get_client", return_value=None):
        client = TestClient(app)
        start = time.perf_counter()
        ok = 0
        for i in range(200):
            r = client.post("/events/ingest", json=_fake_packet(i))
            if r.status_code == 201:
                ok += 1
        elapsed = time.perf_counter() - start

    assert ok == 200, f"esperados 200 OK, recibidos {ok}"
    pps = 200 / elapsed
    print(f"[load_test] in-process throughput: {pps:.0f} pkt/s ({pps*60:.0f} pkt/min)")
    assert pps > 50, f"throughput in-process demasiado bajo: {pps:.0f} pkt/s"
