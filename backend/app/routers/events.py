import csv
import io
import sys
from typing import List, Optional
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.db.supabase_client import get_client, execute_with_retry
from app.services import state_manager
from app.routers.live import broadcast_packet

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/ingest", status_code=201)
async def ingest_event(pkt: dict):
    """Receive packet from sniffer, save to Supabase, run detectors, and broadcast live."""
    client = get_client()
    event_id = None

    if client is not None:
        try:
            row = {
                "timestamp": pkt.get("timestamp"),
                "src_ip": pkt.get("src_ip"),
                "dst_ip": pkt.get("dst_ip"),
                "protocol": pkt.get("protocol"),
                "src_port": pkt.get("src_port"),
                "dst_port": pkt.get("dst_port"),
                "flags": pkt.get("flags"),
                "length": pkt.get("length"),
                "raw_data": pkt,
            }
            res = execute_with_retry(lambda c: c.table("events").insert(row))
            if res.data:
                event_id = res.data[0]["id"]
        except Exception as e:
            print(f"[events] Error saving event to Supabase: {e}", file=sys.stderr)

    # Run detection engine — auto-persists triggered alerts to Supabase
    triggered_alerts = state_manager.process_packet(pkt, event_id=event_id)

    # Always broadcast the original packet dict, just enriched with the persisted id.
    event_payload = {**pkt, "id": event_id}
    live_msg = {"event": event_payload, "alerts": triggered_alerts}

    await broadcast_packet(live_msg)

    return {"status": "ok", "event_id": event_id, "alerts_triggered": len(triggered_alerts)}


def _events_query(limit, offset, protocol, src_ip, since):
    def build(c):
        q = c.table("events").select("*")
        if protocol:
            q = q.eq("protocol", protocol.upper())
        if src_ip:
            q = q.eq("src_ip", src_ip)
        if since:
            q = q.gte("timestamp", since)
        return q.order("timestamp", desc=True).range(offset, offset + limit - 1)
    return build


@router.get("/export")
async def export_events_csv(
    limit: int = Query(1000, ge=1, le=10000),
    src_ip: Optional[str] = None,
    protocol: Optional[str] = None,
    since: Optional[str] = None,
):
    """Stream a CSV of events for the dashboard 'Exportar reporte' button."""
    client = get_client()
    rows = []
    if client is not None:
        try:
            res = execute_with_retry(_events_query(limit, 0, protocol, src_ip, since))
            rows = res.data or []
        except Exception as e:
            print(f"[events] export error: {e}", file=sys.stderr)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "timestamp", "src_ip", "dst_ip", "protocol", "src_port", "dst_port", "flags", "length"])
    for r in rows:
        writer.writerow([
            r.get("id"), r.get("timestamp"), r.get("src_ip"), r.get("dst_ip"),
            r.get("protocol"), r.get("src_port"), r.get("dst_port"),
            r.get("flags") or "", r.get("length") or 0,
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sdai_events.csv"},
    )


@router.get("/investigate/{src_ip}", response_model=dict)
async def investigate_ip(src_ip: str, limit_events: int = Query(50, ge=1, le=500)):
    """Aggregate everything we know about a source IP for the 'Investigar' modal."""
    client = get_client()
    if client is None:
        return {"src_ip": src_ip, "events": [], "alerts": [], "ports": {}, "geo": None, "summary": {"events_count": 0, "alerts_count": 0}}

    events_data = []
    alerts_data = []
    try:
        ev_res = execute_with_retry(_events_query(limit_events, 0, None, src_ip, None))
        events_data = ev_res.data or []
    except Exception as e:
        print(f"[events] investigate events error: {e}", file=sys.stderr)

    try:
        al_res = execute_with_retry(
            lambda c: c.table("alerts").select("*, events!inner(src_ip)").eq("events.src_ip", src_ip).order("created_at", desc=True).limit(20)
        )
        alerts_data = al_res.data or []
    except Exception:
        # Older Supabase / RLS path: fall back to alerts referencing events with src_ip
        try:
            ev_ids = [e["id"] for e in events_data if e.get("id")]
            if ev_ids:
                al_res = execute_with_retry(
                    lambda c: c.table("alerts").select("*").in_("event_id", ev_ids).order("created_at", desc=True).limit(20)
                )
                alerts_data = al_res.data or []
        except Exception as e2:
            print(f"[events] investigate alerts fallback error: {e2}", file=sys.stderr)

    # Aggregate per-port and per-protocol
    port_count: dict = {}
    proto_count: dict = {}
    for e in events_data:
        p = e.get("dst_port")
        if p is not None:
            port_count[p] = port_count.get(p, 0) + 1
        pr = e.get("protocol")
        if pr:
            proto_count[pr] = proto_count.get(pr, 0) + 1

    geo = state_manager.geoip.resolve_ip(src_ip)

    return {
        "src_ip": src_ip,
        "geo": geo,
        "events": events_data,
        "alerts": alerts_data,
        "ports": dict(sorted(port_count.items(), key=lambda kv: -kv[1])[:10]),
        "protocols": proto_count,
        "summary": {
            "events_count": len(events_data),
            "alerts_count": len(alerts_data),
            "high_severity_count": sum(1 for a in alerts_data if a.get("severity") == "alta"),
            "is_blacklisted": src_ip in (state_manager.configs.get("blacklist_ips") or []),
        },
    }


@router.get("", response_model=List[dict])
async def list_events(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    protocol: Optional[str] = None,
    src_ip: Optional[str] = None,
    since: Optional[str] = None
):
    """Get event history from Supabase with pagination and filters."""
    client = get_client()
    if client is None:
        return []

    try:
        res = execute_with_retry(_events_query(limit, offset, protocol, src_ip, since))
        return res.data or []
    except Exception as e:
        print(f"[events] Error fetching events: {e}", file=sys.stderr)
        return []

