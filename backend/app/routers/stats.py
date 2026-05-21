import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from fastapi import APIRouter, Query

from app.config import settings
from app.db.supabase_client import get_client, execute_with_retry
from app.notifications.dispatcher import dispatcher
from app.services import state_manager

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary", response_model=dict)
async def get_summary():
    """Retrieve summary dashboard stats and KPI metrics."""
    client = get_client()
    if client is None:
        return {
            "total_events": 0,
            "total_alerts": 0,
            "unresolved_alerts": 0,
            "alerts_by_severity": {"baja": 0, "media": 0, "alta": 0},
            "threat_distribution": {"port_scan": 0, "brute_force": 0, "malicious_ip": 0, "dos": 0},
            "top_sources": [],
            "current_pps": state_manager.current_pps(),
            "uptime_seconds": state_manager.uptime_seconds(),
        }

    try:
        # 1. Total events count (Supabase count select)
        events_res = execute_with_retry(lambda c: c.table("events").select("id", count="exact").limit(1))
        total_events = events_res.count if events_res.count is not None else 0

        # 2. Total alerts and breakdown
        alerts_res = execute_with_retry(lambda c: c.table("alerts").select("severity, threat_type, notified"))
        alerts_data = alerts_res.data or []

        total_alerts = len(alerts_data)
        unresolved_alerts = sum(1 for a in alerts_data if not a.get("notified", False))

        severity_counts = {"baja": 0, "media": 0, "alta": 0}
        for a in alerts_data:
            sev = a.get("severity")
            if sev in severity_counts:
                severity_counts[sev] += 1

        threat_counts = {"port_scan": 0, "brute_force": 0, "malicious_ip": 0, "dos": 0}
        for a in alerts_data:
            tt = a.get("threat_type")
            if tt in threat_counts:
                threat_counts[tt] += 1

        # 3. Top sources (recent 500 events grouped in Python)
        recent_events = execute_with_retry(lambda c: c.table("events").select("src_ip").limit(500))
        events_data = recent_events.data or []

        ip_counter = Counter(e["src_ip"] for e in events_data if e.get("src_ip"))
        top_sources = [{"ip": ip, "count": count} for ip, count in ip_counter.most_common(5)]

        return {
            "total_events": total_events,
            "total_alerts": total_alerts,
            "unresolved_alerts": unresolved_alerts,
            "alerts_by_severity": severity_counts,
            "threat_distribution": threat_counts,
            "top_sources": top_sources,
            "current_pps": state_manager.current_pps(),
            "uptime_seconds": state_manager.uptime_seconds(),
        }
    except Exception as e:
        print(f"[stats] Error generating statistics summary: {e}", file=sys.stderr)
        return {
            "error": str(e),
            "total_events": 0,
            "total_alerts": 0,
            "unresolved_alerts": 0,
            "alerts_by_severity": {"baja": 0, "media": 0, "alta": 0},
            "threat_distribution": {"port_scan": 0, "brute_force": 0, "malicious_ip": 0, "dos": 0},
            "top_sources": [],
            "current_pps": state_manager.current_pps(),
            "uptime_seconds": state_manager.uptime_seconds(),
        }


@router.get("/pps", response_model=dict)
async def get_pps(history_buckets: int = Query(30, ge=5, le=120), bucket_seconds: float = Query(2.0, gt=0)):
    """Real-time packets-per-second + history buckets for sparkline."""
    return {
        "current": state_manager.current_pps(window_seconds=1.0),
        "avg_60s": round(state_manager.current_pps(window_seconds=60.0) / 60.0, 2),
        "history": state_manager.pps_history(buckets=history_buckets, bucket_seconds=bucket_seconds),
        "bucket_seconds": bucket_seconds,
    }


@router.get("/uptime", response_model=dict)
async def get_uptime():
    return {
        "uptime_seconds": state_manager.uptime_seconds(),
        "started_at": state_manager.started_at.isoformat(),
    }


@router.get("/sensor", response_model=dict)
async def get_sensor_info():
    """Static sensor / tenant metadata + notification channel availability."""
    return {
        "version": "0.1.0",
        "interface": settings.CAPTURE_INTERFACE,
        "api_host": settings.API_HOST,
        "api_port": settings.API_PORT,
        "started_at": state_manager.started_at.isoformat(),
        "uptime_seconds": state_manager.uptime_seconds(),
        "supabase_connected": get_client() is not None,
        "notifications": {
            "telegram": dispatcher.telegram_enabled(),
            "email": dispatcher.email_enabled(),
        },
        "thresholds": state_manager.configs,
    }


@router.post("/reset", response_model=dict)
async def reset_sensor():
    """Wipe in-memory sliding windows + cooldowns. Useful after demo / config change."""
    state_manager.port_scan_history.clear()
    state_manager.brute_force_history.clear()
    state_manager.dos_history.clear()
    state_manager.alert_cooldowns.clear()
    state_manager.global_packet_timestamps.clear()
    state_manager.started_at = datetime.now(timezone.utc)
    return {"status": "ok", "reset_at": state_manager.started_at.isoformat()}


@router.get("/trend", response_model=dict)
async def get_trend(
    minutes: int = Query(30, ge=5, le=240),
    buckets: int = Query(30, ge=5, le=120),
):
    """Stacked severity counts over a sliding time window (oldest bucket first)."""
    client = get_client()
    empty = {sev: [0] * buckets for sev in ("alta", "media", "baja")}
    if client is None:
        return {"buckets": buckets, "minutes": minutes, "series": empty, "labels": []}

    try:
        now = datetime.now(timezone.utc)
        since = now - timedelta(minutes=minutes)
        res = execute_with_retry(
            lambda c: c.table("alerts").select("severity, created_at").gte("created_at", since.isoformat())
        )
        rows = res.data or []

        bucket_seconds = (minutes * 60) / buckets
        series: Dict[str, List[int]] = {"alta": [0] * buckets, "media": [0] * buckets, "baja": [0] * buckets}
        labels: List[str] = []

        # Pre-compute bucket boundaries to keep labeling deterministic
        for i in range(buckets):
            bucket_end = now - timedelta(seconds=(buckets - 1 - i) * bucket_seconds)
            labels.append(bucket_end.strftime("%H:%M:%S"))

        for r in rows:
            sev = r.get("severity")
            if sev not in series:
                continue
            try:
                ts = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            except (KeyError, ValueError, AttributeError):
                continue
            delta = (now - ts).total_seconds()
            if delta < 0:
                idx = buckets - 1
            else:
                idx = buckets - 1 - int(delta // bucket_seconds)
            if 0 <= idx < buckets:
                series[sev][idx] += 1

        return {"buckets": buckets, "minutes": minutes, "series": series, "labels": labels}
    except Exception as e:
        print(f"[stats] Error generating trend: {e}", file=sys.stderr)
        return {"buckets": buckets, "minutes": minutes, "series": empty, "labels": [], "error": str(e)}
