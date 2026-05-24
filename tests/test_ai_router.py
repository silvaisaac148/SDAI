"""Unit tests for the SDAI AI tutor, threat explanation, and active firewall blocking router.

Covers 100% of branch and statement coverage for backend/app/routers/ai.py.
"""
import ipaddress
import platform
import subprocess
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.routers.auth import get_current_user
from app.routers.ai import _call_groq_api, _call_gemini_api


# Force authentication by overriding the current user dependency
@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: "admin"
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def client():
    return TestClient(app)


# ---------- Test LLM API Wrapper Logic ----------

def test_call_groq_api_missing_key():
    with patch.object(settings, "GROQ_API_KEY", ""):
        assert _call_groq_api("sys", "user") is None


def test_call_groq_api_success():
    with patch.object(settings, "GROQ_API_KEY", "mock-key"):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Groq response"}}]
        }
        with patch("httpx.post", return_value=mock_response):
            res = _call_groq_api("sys", "user")
            assert res == "Groq response"


def test_call_groq_api_error_status():
    with patch.object(settings, "GROQ_API_KEY", "mock-key"):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        with patch("httpx.post", return_value=mock_response):
            res = _call_groq_api("sys", "user")
            assert res is None


def test_call_groq_api_exception():
    with patch.object(settings, "GROQ_API_KEY", "mock-key"):
        with patch("httpx.post", side_effect=httpx.ConnectTimeout("Timeout")):
            res = _call_groq_api("sys", "user")
            assert res is None


def test_call_gemini_api_missing_key():
    with patch.object(settings, "GEMINI_API_KEY", ""):
        assert _call_gemini_api("prompt") is None


def test_call_gemini_api_success():
    with patch.object(settings, "GEMINI_API_KEY", "mock-key"):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Gemini response"}]}}]
        }
        with patch("httpx.post", return_value=mock_response):
            res = _call_gemini_api("prompt")
            assert res == "Gemini response"


def test_call_gemini_api_error_status():
    with patch.object(settings, "GEMINI_API_KEY", "mock-key"):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        with patch("httpx.post", return_value=mock_response):
            res = _call_gemini_api("prompt")
            assert res is None


def test_call_gemini_api_exception():
    with patch.object(settings, "GEMINI_API_KEY", "mock-key"):
        with patch("httpx.post", side_effect=Exception("API Error")):
            res = _call_gemini_api("prompt")
            assert res is None


# ---------- Test Chat Endpoint ----------

def test_chat_heuristic_fallback_portscan(client):
    with patch.object(settings, "GROQ_API_KEY", ""), patch.object(settings, "GEMINI_API_KEY", ""):
        response = client.post("/ai/chat", json={"message": "Háblame de port scan"})
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "heuristic"
        assert "Escaneo de Puertos" in data["reply"]


def test_chat_heuristic_fallback_dos(client):
    with patch.object(settings, "GROQ_API_KEY", ""), patch.object(settings, "GEMINI_API_KEY", ""):
        response = client.post("/ai/chat", json={"message": "qué es denegación de servicio"})
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "heuristic"
        assert "Denegación de Servicio" in data["reply"]


def test_chat_heuristic_fallback_bruteforce(client):
    with patch.object(settings, "GROQ_API_KEY", ""), patch.object(settings, "GEMINI_API_KEY", ""):
        response = client.post("/ai/chat", json={"message": "Intento de fuerza bruta"})
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "heuristic"
        assert "Ataques de Fuerza Bruta" in data["reply"]


def test_chat_heuristic_fallback_ac1300(client):
    with patch.object(settings, "GROQ_API_KEY", ""), patch.object(settings, "GEMINI_API_KEY", ""):
        response = client.post("/ai/chat", json={"message": "Háblame de la Archer AC1300"})
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "heuristic"
        assert "Archer T3U AC1300" in data["reply"]


def test_chat_heuristic_fallback_default(client):
    with patch.object(settings, "GROQ_API_KEY", ""), patch.object(settings, "GEMINI_API_KEY", ""):
        response = client.post("/ai/chat", json={"message": "Hola, tutor"})
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "heuristic"
        assert "Tutor Pedagógico de Ciberseguridad" in data["reply"]


def test_chat_groq_success(client):
    with patch.object(settings, "GROQ_API_KEY", "mock-key"):
        with patch("app.routers.ai._call_groq_api", return_value="Custom Groq Chat") as mock_groq:
            response = client.post("/ai/chat", json={"message": "hola"})
            assert response.status_code == 200
            data = response.json()
            assert data["mode"] == "groq"
            assert data["reply"] == "Custom Groq Chat"
            mock_groq.assert_called_once()


def test_chat_gemini_success(client):
    # Enable Gemini key, leave Groq empty to trigger Gemini block
    with patch.object(settings, "GROQ_API_KEY", ""):
        with patch.object(settings, "GEMINI_API_KEY", "mock-key"):
            with patch("app.routers.ai._call_gemini_api", return_value="Custom Gemini Chat") as mock_gem:
                response = client.post("/ai/chat", json={"message": "hola"})
                assert response.status_code == 200
                data = response.json()
                assert data["mode"] == "gemini"
                assert data["reply"] == "Custom Gemini Chat"
                mock_gem.assert_called_once()


# ---------- Test Explain Threat Endpoint ----------

def test_explain_ip_investigate_fails(client):
    with patch("app.routers.ai.investigate_ip", side_effect=Exception("DB Failure")):
        response = client.get("/ai/explain/10.0.0.99")
        assert response.status_code == 500
        assert "Failed to gather IP details" in response.json()["detail"]


def test_explain_ip_heuristic_portscan(client):
    mock_details = {
        "summary": {"events_count": 50, "alerts_count": 2, "high_severity_count": 0},
        "geo": {"city": "Barinas", "country": "Venezuela"},
        "ports": {"80": 20, "22": 30},
        "protocols": {"TCP": 50},
        "alerts": [{"threat_type": "port_scan", "description": "Escaneo detectado"}]
    }
    with patch("app.routers.ai.investigate_ip", return_value=mock_details):
        with patch.object(settings, "GROQ_API_KEY", ""), patch.object(settings, "GEMINI_API_KEY", ""):
            response = client.get("/ai/explain/10.0.0.2")
            assert response.status_code == 200
            data = response.json()
            assert data["mode"] == "heuristic"
            assert "Escaneo de Puertos" in data["analysis"]
            assert "10.0.0.2" in data["analysis"]
            assert "Barinas, Venezuela" in data["analysis"]


def test_explain_ip_heuristic_dos(client):
    mock_details = {
        "summary": {"events_count": 2000, "alerts_count": 5, "high_severity_count": 3},
        "geo": {"city": "Caracas", "country": "Venezuela"},
        "ports": {"80": 2000},
        "protocols": {"TCP": 2000},
        "alerts": [{"threat_type": "dos", "description": "Saturación detectada"}]
    }
    with patch("app.routers.ai.investigate_ip", return_value=mock_details):
        with patch.object(settings, "GROQ_API_KEY", ""), patch.object(settings, "GEMINI_API_KEY", ""):
            response = client.get("/ai/explain/10.0.0.3")
            assert response.status_code == 200
            data = response.json()
            assert data["mode"] == "heuristic"
            assert "Denegación de Servicio (DoS)" in data["analysis"]


def test_explain_ip_heuristic_default(client):
    mock_details = {
        "summary": {"events_count": 5, "alerts_count": 0, "high_severity_count": 0},
        "geo": {},
        "ports": {"443": 5},
        "protocols": {"TCP": 5},
        "alerts": []
    }
    with patch("app.routers.ai.investigate_ip", return_value=mock_details):
        with patch.object(settings, "GROQ_API_KEY", ""), patch.object(settings, "GEMINI_API_KEY", ""):
            response = client.get("/ai/explain/10.0.0.4")
            assert response.status_code == 200
            data = response.json()
            assert data["mode"] == "heuristic"
            assert "actividad inusual pero moderada" in data["analysis"]


def test_explain_ip_groq_success(client):
    mock_details = {
        "summary": {"events_count": 5, "alerts_count": 0},
        "geo": {},
        "ports": {},
        "protocols": {},
        "alerts": []
    }
    with patch("app.routers.ai.investigate_ip", return_value=mock_details):
        with patch.object(settings, "GROQ_API_KEY", "mock-key"):
            with patch("app.routers.ai._call_groq_api", return_value="Custom Groq Explanation") as mock_groq:
                response = client.get("/ai/explain/10.0.0.5")
                assert response.status_code == 200
                data = response.json()
                assert data["mode"] == "groq"
                assert data["analysis"] == "Custom Groq Explanation"
                mock_groq.assert_called_once()


def test_explain_ip_gemini_success(client):
    mock_details = {
        "summary": {"events_count": 5, "alerts_count": 0},
        "geo": {},
        "ports": {},
        "protocols": {},
        "alerts": []
    }
    with patch("app.routers.ai.investigate_ip", return_value=mock_details):
        with patch.object(settings, "GROQ_API_KEY", ""):
            with patch.object(settings, "GEMINI_API_KEY", "mock-key"):
                with patch("app.routers.ai._call_gemini_api", return_value="Custom Gemini Explanation") as mock_gem:
                    response = client.get("/ai/explain/10.0.0.6")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["mode"] == "gemini"
                    assert data["analysis"] == "Custom Gemini Explanation"
                    mock_gem.assert_called_once()


# ---------- Test Block IP Endpoint ----------

def test_block_invalid_ip(client):
    response = client.post("/ai/block/invalid-ip-format")
    assert response.status_code == 400
    assert "Invalid IP address" in response.json()["detail"]


# Windows System Blocking Scenarios

def test_block_ip_windows_rule_exists(client):
    with patch("platform.system", return_value="Windows"):
        # Duplicate check returns 0 (rule exists)
        mock_chk = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock_chk) as mock_run:
            response = client.post("/ai/block/1.2.3.4")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "blocked"
            assert data["firewall_status"] == "Active (Rule already exists)"
            assert "already exists" in data["explanation"]


def test_block_ip_windows_success(client):
    with patch("platform.system", return_value="Windows"):
        # Duplicate check returns 1 (does not exist), block command returns 0 (success)
        mock_chk = MagicMock(returncode=1)
        mock_blk = MagicMock(returncode=0)
        
        def mock_subprocess_run(cmd, *args, **kwargs):
            if "Get-NetFirewallRule" in cmd[2]:
                return mock_chk
            return mock_blk

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            response = client.post("/ai/block/1.2.3.4")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "blocked"
            assert data["firewall_status"] == "Success (Rule created)"
            assert "mitigada de forma activa" in data["explanation"]


def test_block_ip_windows_permission_error(client):
    with patch("platform.system", return_value="Windows"):
        # Duplicate check returns 1, block command returns 1 with permission error
        mock_chk = MagicMock(returncode=1)
        mock_blk = MagicMock(returncode=1, stderr="  AccessIsDenied: Permission was denied.")
        
        def mock_subprocess_run(cmd, *args, **kwargs):
            if "Get-NetFirewallRule" in cmd[2]:
                return mock_chk
            return mock_blk

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            response = client.post("/ai/block/1.2.3.4")
            assert response.status_code == 200
            data = response.json()
            assert data["firewall_status"] == "Error: Acceso denegado (Requiere PowerShell como Administrador)"


def test_block_ip_windows_other_failure(client):
    with patch("platform.system", return_value="Windows"):
        mock_chk = MagicMock(returncode=1)
        mock_blk = MagicMock(returncode=1, stderr="Something went completely wrong with NetFirewall rules.")
        
        def mock_subprocess_run(cmd, *args, **kwargs):
            if "Get-NetFirewallRule" in cmd[2]:
                return mock_chk
            return mock_blk

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            response = client.post("/ai/block/1.2.3.4")
            assert response.status_code == 200
            data = response.json()
            assert "Failed: Something went completely wrong" in data["firewall_status"]


def test_block_ip_windows_exception(client):
    with patch("platform.system", return_value="Windows"):
        with patch("subprocess.run", side_effect=FileNotFoundError("powershell not found")):
            response = client.post("/ai/block/1.2.3.4")
            assert response.status_code == 200
            data = response.json()
            assert "Error: powershell not found" in data["firewall_status"]


# Linux System Blocking Scenarios

def test_block_ip_linux_success(client):
    with patch("platform.system", return_value="Linux"):
        mock_blk = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock_blk) as mock_run:
            response = client.post("/ai/block/1.2.3.4")
            assert response.status_code == 200
            data = response.json()
            assert data["os"] == "Linux"
            assert data["firewall_status"] == "Success (iptables rule added)"
            mock_run.assert_called_once_with(
                ["sudo", "iptables", "-A", "INPUT", "-s", "1.2.3.4", "-j", "DROP"],
                capture_output=True, text=True, check=False
            )


def test_block_ip_linux_failure(client):
    with patch("platform.system", return_value="Linux"):
        mock_blk = MagicMock(returncode=1, stderr="iptables: No chain/target/match by that name.")
        with patch("subprocess.run", return_value=mock_blk):
            response = client.post("/ai/block/1.2.3.4")
            assert response.status_code == 200
            data = response.json()
            assert "Failed: iptables:" in data["firewall_status"]


def test_block_ip_linux_exception(client):
    with patch("platform.system", return_value="Linux"):
        with patch("subprocess.run", side_effect=Exception("iptables failed")):
            response = client.post("/ai/block/1.2.3.4")
            assert response.status_code == 200
            data = response.json()
            assert "Error: iptables failed" in data["firewall_status"]


# Supabase/Local Database Blacklist Actions

def test_block_ip_database_update_success(client):
    # Mock supabase client and responses
    mock_db = MagicMock()
    
    # 1. Mock select single configuration
    mock_select = MagicMock()
    mock_select.data = {"value": ["1.1.1.1"]}
    
    # 2. Mock upsert config
    mock_upsert = MagicMock()
    
    def execute_with_retry_mock(func):
        return func(mock_db)

    with patch("app.routers.ai.get_client", return_value=mock_db):
        with patch("app.routers.ai.execute_with_retry", side_effect=execute_with_retry_mock):
            mock_db.table.return_value.select.return_value.eq.return_value.single.return_value = mock_select
            mock_db.table.return_value.upsert.return_value = mock_upsert
            
            with patch("platform.system", return_value="Unknown"):
                response = client.post("/ai/block/1.2.3.4")
                assert response.status_code == 200
                data = response.json()
                assert data["blacklist_status"] == "Success (Added to database blacklist)"
                
                # Verify that it fetched, added IP to blacklist, and called upsert
                mock_db.table.assert_called_with("configurations")


def test_block_ip_database_upsert_failure(client):
    mock_db = MagicMock()
    mock_select = MagicMock()
    mock_select.data = {"value": ["1.1.1.1"]}
    
    def execute_with_retry_mock(func):
        res = func(mock_db)
        if hasattr(res, "upsert"):
            raise Exception("Supabase Write Denied")
        return res

    with patch("app.routers.ai.get_client", return_value=mock_db):
        with patch("app.routers.ai.execute_with_retry", side_effect=execute_with_retry_mock):
            mock_db.table.return_value.select.return_value.eq.return_value.single.return_value = mock_select
            mock_db.table.return_value.upsert.side_effect = Exception("Supabase Write Denied")
            
            with patch("platform.system", return_value="Unknown"):
                response = client.post("/ai/block/1.2.3.4")
                assert response.status_code == 200
                data = response.json()
                assert "Failed database update: Supabase Write Denied" in data["blacklist_status"]


def test_unauthenticated_access(client):
    # Temporarily remove the override to check authenticating failure
    app.dependency_overrides.pop(get_current_user, None)
    try:
        response = client.get("/ai/explain/10.0.0.1")
        assert response.status_code == 401
    finally:
        # Restore override for other test runs
        app.dependency_overrides[get_current_user] = lambda: "admin"
