from fastapi.testclient import TestClient
from scapy.layers.inet import ICMP, IP, TCP, UDP

from app.main import app
from capture.decoder import decode

client = TestClient(app)


# ---------- Backend health endpoint ----------

def test_health_returns_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
    assert "timestamp" in body


def test_root_redirects_to_login_when_unauthenticated():
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


# ---------- Config endpoint (in-memory mode, no Supabase) ----------

def test_config_upsert_and_get():
    payload = {"key": "test_threshold", "value": {"max": 42}}
    r = client.post("/config", json=payload)
    assert r.status_code == 201
    assert r.json()["key"] == "test_threshold"
    assert r.json()["value"] == {"max": 42}

    r = client.get("/config/test_threshold")
    assert r.status_code == 200
    assert r.json()["value"] == {"max": 42}


def test_config_404_on_missing():
    r = client.get("/config/does_not_exist_xyz")
    assert r.status_code == 404


# ---------- Decoder ----------

def test_decode_tcp_packet():
    pkt = IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=12345, dport=80, flags="S")
    out = decode(pkt)
    assert out is not None
    assert out["src_ip"] == "10.0.0.1"
    assert out["dst_ip"] == "10.0.0.2"
    assert out["protocol"] == "TCP"
    assert out["src_port"] == 12345
    assert out["dst_port"] == 80
    assert "S" in out["flags"]


def test_decode_udp_packet():
    pkt = IP(src="10.0.0.1", dst="8.8.8.8") / UDP(sport=53000, dport=53)
    out = decode(pkt)
    assert out["protocol"] == "UDP"
    assert out["dst_port"] == 53


def test_decode_icmp_packet():
    pkt = IP(src="10.0.0.1", dst="10.0.0.2") / ICMP(type=8, code=0)
    out = decode(pkt)
    assert out["protocol"] == "ICMP"
    assert "type=8" in out["flags"]


def test_decode_returns_none_for_non_ip():
    from scapy.layers.l2 import Ether
    pkt = Ether()
    assert decode(pkt) is None
