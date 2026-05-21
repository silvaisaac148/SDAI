import csv
import io
import sys
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse

from app.db.supabase_client import get_client, execute_with_retry

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=List[dict])
async def list_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity: baja, media, alta"),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status (notified)"),
    since: Optional[str] = Query(None, description="ISO timestamp since filter"),
    limit: int = Query(50, ge=1, le=100)
):
    """Retrieve list of threat alerts from Supabase, including their matching event data."""
    client = get_client()
    if client is None:
        return []
        
    try:
        def build_query(c):
            q = c.table("alerts").select("*, events(*)")
            if severity:
                q = q.eq("severity", severity.lower())
            if resolved is not None:
                # RLS/Schema mapping: `notified` stands for resolved status in Sprint 3-4
                q = q.eq("notified", resolved)
            if since:
                q = q.gte("created_at", since)
            return q.order("created_at", desc=True).limit(limit)

        res = execute_with_retry(build_query)
        return res.data or []
    except Exception as e:
        print(f"[alerts] Error querying alerts from Supabase: {e}", file=sys.stderr)
        return []


@router.get("/export")
async def export_alerts_csv(
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    since: Optional[str] = None,
    limit: int = Query(2000, ge=1, le=10000),
):
    """Stream alerts as CSV — fields tuned for executive PyME report."""
    client = get_client()
    rows = []
    if client is not None:
        try:
            def build(c):
                q = c.table("alerts").select("*, events(src_ip, dst_ip, dst_port, protocol)")
                if severity:
                    q = q.eq("severity", severity.lower())
                if resolved is not None:
                    q = q.eq("notified", resolved)
                if since:
                    q = q.gte("created_at", since)
                return q.order("created_at", desc=True).limit(limit)
            res = execute_with_retry(build)
            rows = res.data or []
        except Exception as e:
            print(f"[alerts] export error: {e}", file=sys.stderr)

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "created_at", "threat_type", "severity", "src_ip", "dst_ip", "dst_port", "protocol", "country", "city", "description", "resolved"])
    for r in rows:
        ev = r.get("events") or {}
        w.writerow([
            r.get("id"), r.get("created_at"),
            r.get("threat_type"), r.get("severity"),
            ev.get("src_ip", ""), ev.get("dst_ip", ""),
            ev.get("dst_port", ""), ev.get("protocol", ""),
            r.get("country", ""), r.get("city", ""),
            (r.get("description") or "").replace("\n", " "),
            r.get("notified", False),
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sdai_alerts.csv"},
    )


@router.patch("/{alert_id}/resolve", response_model=dict)
async def resolve_alert(alert_id: int):
    """Acknowledge or resolve an alert by marking 'notified' as True."""
    client = get_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Supabase connection not available")
        
    try:
        res = execute_with_retry(lambda c: c.table("alerts").update({"notified": True}).eq("id", alert_id))
        if not res.data:
            raise HTTPException(status_code=404, detail=f"Alert with ID {alert_id} not found")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating alert: {e}")

