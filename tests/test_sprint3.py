"""Tests Sprint 3-4: detectores, GeoIP, state manager, endpoints nuevos.

Estos tests no requieren Supabase configurado (degradan en modo dev cuando aplica).
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.services import state_manager as global_state_manager
from capture.detectors import (
    check_port_scan,
    check_brute_force,
    check_dos,
    check_malicious_ip,
)
from capture.state import DetectionStateManager

# Disable hot-reload of configs during the suite (no Supabase round-trips)
global_state_manager._refresh_configs_if_needed = lambda: None

client = TestClient(app)


def _pkt(src="1.2.3.4", dst="10.0.0.5", proto="TCP", flags="S", dport=22, sport=44444):
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "src_ip": src,
        "dst_ip": dst,
        "protocol": proto,
        "src_port": sport,
        "dst_port": dport,
        "flags": flags,
        "length": 60,
    }


# =====================  DETECTORES (puros) ====================================

def test_port_scan_triggers_on_threshold():
    history = defaultdict(list)
    alert = None
    for port in range(1, 22):
        alert = check_port_scan(_pkt(src="10.10.10.10", dport=port), history, threshold=20)
    assert alert is not None
    assert alert["threat_type"] == "port_scan"
    assert len(alert["details"]["ports_scanned"]) >= 20


def test_port_scan_below_threshold_no_alert():
    history = defaultdict(list)
    for port in range(1, 10):
        alert = check_port_scan(_pkt(src="9.9.9.9", dport=port), history, threshold=20)
        assert alert is None


def test_port_scan_repeated_port_does_not_inflate_count():
    history = defaultdict(list)
    alert = None
    for _ in range(50):
        alert = check_port_scan(_pkt(src="5.5.5.5", dport=443), history, threshold=20)
    assert alert is None


def test_brute_force_ssh_triggers():
    history = defaultdict(list)
    alert = None
    for _ in range(6):
        alert = check_brute_force(
            _pkt(src="6.6.6.6", proto="TCP", flags="S", dport=22),
            history,
            attempts_threshold=5,
            window=60.0,
        )
    assert alert is not None
    assert alert["details"]["service"] == "SSH"


def test_brute_force_ignores_non_critical_port():
    history = defaultdict(list)
    for _ in range(20):
        alert = check_brute_force(
            _pkt(src="7.7.7.7", proto="TCP", flags="S", dport=12345),
            history,
            attempts_threshold=5,
        )
    assert alert is None


def test_brute_force_ignores_tcp_non_syn():
    history = defaultdict(list)
    for _ in range(10):
        alert = check_brute_force(
            _pkt(src="8.8.8.8", proto="TCP", flags="A", dport=22),
            history,
            attempts_threshold=5,
        )
    assert alert is None


def test_dos_triggers_above_pps():
    history = defaultdict(list)
    alert = None
    for _ in range(60):
        alert = check_dos(_pkt(src="11.11.11.11"), history, pps_threshold=50)
    assert alert is not None
    assert alert["threat_type"] == "dos"


def test_malicious_ip_src_match():
    alert = check_malicious_ip(_pkt(src="203.0.113.42"), ["203.0.113.42"])
    assert alert is not None
    assert alert["details"]["direction"] == "entrada"


def test_malicious_ip_dst_match():
    alert = check_malicious_ip(
        _pkt(src="10.0.0.5", dst="45.155.205.231"),
        ["45.155.205.231"],
    )
    assert alert["details"]["direction"] == "salida"


def test_malicious_ip_no_match():
    assert check_malicious_ip(_pkt(src="10.0.0.5"), ["1.2.3.4"]) is None


# =====================  DetectionStateManager =================================

def _fresh_manager():
    mgr = DetectionStateManager()
    mgr._refresh_configs_if_needed = lambda: None
    return mgr


def test_state_manager_cooldown_prevents_spam():
    mgr = _fresh_manager()
    mgr.configs["blacklist_ips"] = ["203.0.113.42"]
    pkt = _pkt(src="203.0.113.42")
    first = mgr.process_packet(pkt)
    second = mgr.process_packet(pkt)
    assert len(first) == 1
    assert second == []


def test_state_manager_pps_tracking():
    mgr = _fresh_manager()
    for _ in range(10):
        mgr.process_packet(_pkt(src="1.1.1.1"))
    assert mgr.current_pps(window_seconds=60.0) == 10


def test_state_manager_pps_history_buckets():
    mgr = _fresh_manager()
    for _ in range(5):
        mgr.process_packet(_pkt(src="1.1.1.1"))
    hist = mgr.pps_history(buckets=10, bucket_seconds=1.0)
    assert len(hist) == 10
    assert sum(hist) >= 1


def test_state_manager_uptime():
    mgr = _fresh_manager()
    mgr.started_at = datetime.now(timezone.utc) - timedelta(seconds=42)
    assert mgr.uptime_seconds() >= 42


def test_state_manager_port_scan_full_flow():
    mgr = _fresh_manager()
    mgr.configs["port_scan_threshold"] = {"ports_per_minute": 5}
    alerts = []
    for port in range(10, 16):
        alerts.extend(mgr.process_packet(_pkt(src="192.168.50.50", dport=port)))
    assert any(a["threat_type"] == "port_scan" for a in alerts)


def test_state_manager_brute_force_full_flow():
    mgr = _fresh_manager()
    mgr.configs["brute_force_threshold"] = {"failed_attempts": 3, "window_seconds": 60}
    alerts = []
    for _ in range(4):
        alerts.extend(mgr.process_packet(_pkt(src="192.168.50.51", dport=22, flags="S")))
    assert any(a["threat_type"] == "brute_force" for a in alerts)


# =====================  Endpoints nuevos ======================================

def test_endpoint_pps_shape():
    r = client.get("/stats/pps")
    assert r.status_code == 200
    body = r.json()
    assert {"current", "history", "bucket_seconds", "avg_60s"} <= set(body.keys())
    assert isinstance(body["history"], list)


def test_endpoint_uptime_shape():
    r = client.get("/stats/uptime")
    assert r.status_code == 200
    body = r.json()
    assert body["uptime_seconds"] >= 0
    assert "started_at" in body


def test_endpoint_trend_shape():
    r = client.get("/stats/trend?minutes=15&buckets=10")
    assert r.status_code == 200
    body = r.json()
    assert body["buckets"] == 10
    assert set(body["series"].keys()) == {"alta", "media", "baja"}
    assert all(len(v) == 10 for v in body["series"].values())


def test_endpoint_summary_includes_new_kpis():
    r = client.get("/stats/summary")
    assert r.status_code == 200
    body = r.json()
    assert "current_pps" in body
    assert "uptime_seconds" in body


def test_events_ingest_smoke():
    pkt = _pkt(src="172.16.99.99", dport=80)
    r = client.post("/events/ingest", json=pkt)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "ok"
    assert "alerts_triggered" in body


def test_list_events_smoke():
    r = client.get("/events?limit=5")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_alerts_smoke():
    r = client.get("/alerts?limit=5")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_export_events_csv():
    r = client.get("/events/export?limit=10")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers.get("content-disposition", "")
    # First line is the header row
    first_line = r.text.split("\n", 1)[0]
    assert "src_ip" in first_line and "protocol" in first_line


def test_export_alerts_csv():
    r = client.get("/alerts/export?limit=10")
    assert r.status_code == 200
    assert "threat_type" in r.text.split("\n", 1)[0]


def test_sensor_info():
    r = client.get("/stats/sensor")
    assert r.status_code == 200
    body = r.json()
    assert {"version", "interface", "uptime_seconds", "notifications", "thresholds"} <= set(body.keys())
    assert {"telegram", "email"} <= set(body["notifications"].keys())


def test_sensor_reset():
    # Seed some state
    for _ in range(5):
        client.post("/events/ingest", json=_pkt(src="123.123.123.123"))
    r = client.post("/stats/reset")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    # After reset, PPS history should drain on the next read window
    r2 = client.get("/stats/pps")
    assert r2.status_code == 200


def test_investigate_ip():
    # Seed an event for a known IP
    client.post("/events/ingest", json=_pkt(src="55.55.55.55", dport=22, flags="S"))
    r = client.get("/events/investigate/55.55.55.55")
    assert r.status_code == 200
    body = r.json()
    assert body["src_ip"] == "55.55.55.55"
    assert "geo" in body and "summary" in body
    assert "ports" in body
