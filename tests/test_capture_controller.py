"""Tests for the remote sniffer controller (start/stop/pause/resume)."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.capture_controller import CaptureController
from app.main import app

client = TestClient(app)


def test_status_endpoint_initial_state():
    r = client.get("/capture/status")
    assert r.status_code == 200
    body = r.json()
    assert "running" in body and "paused" in body
    assert "interface" in body


def test_pause_endpoint_no_op_when_stopped():
    r = client.post("/capture/pause")
    assert r.status_code == 200
    body = r.json()
    assert body["paused"] is True
    # Cleanup
    client.post("/capture/resume")


def test_resume_endpoint():
    client.post("/capture/pause")
    r = client.post("/capture/resume")
    assert r.status_code == 200
    assert r.json()["paused"] is False


def test_stop_when_not_running_returns_stopped():
    r = client.post("/capture/stop")
    assert r.status_code == 200
    assert r.json()["running"] is False


def test_controller_start_failure_surfaces_error():
    ctrl = CaptureController()
    with patch("scapy.sendrecv.AsyncSniffer", side_effect=PermissionError("admin required")):
        result = ctrl.start(interface="bogus0")
    assert result["status"] == "error"
    assert "admin required" in result["error"]
    assert ctrl.status()["last_error"]


def test_controller_paused_callback_drops_packets():
    ctrl = CaptureController()
    ctrl._paused = True
    fake_pkt = object()
    with patch.object(ctrl._http, "post") as mock_post, \
         patch("capture.decoder.decode", return_value={"src_ip": "1.1.1.1"}):
        ctrl._on_packet(fake_pkt)
    mock_post.assert_not_called()


def test_controller_unpaused_callback_posts_to_ingest():
    ctrl = CaptureController()
    ctrl._paused = False
    fake_pkt = object()
    with patch.object(ctrl._http, "post") as mock_post, \
         patch("capture.decoder.decode", return_value={"src_ip": "1.1.1.1", "protocol": "TCP"}):
        ctrl._on_packet(fake_pkt)
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0].endswith("/events/ingest")
    assert kwargs["json"]["src_ip"] == "1.1.1.1"


def test_controller_decode_none_skips_post():
    ctrl = CaptureController()
    with patch.object(ctrl._http, "post") as mock_post, \
         patch("capture.decoder.decode", return_value=None):
        ctrl._on_packet(object())
    mock_post.assert_not_called()


def test_controller_counts_packets():
    ctrl = CaptureController()
    with patch.object(ctrl._http, "post"), \
         patch("capture.decoder.decode", return_value={"src_ip": "1.1.1.1"}):
        for _ in range(3):
            ctrl._on_packet(object())
    assert ctrl._pkt_count == 3
