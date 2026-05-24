"""Unit tests for the advanced cryptographic session tokens and rate-limiting security mitigations.

Covers:
1. Dynamic signed session tokens with Unix timestamps.
2. Expiration of stolen/replay session tokens after 18 hours.
3. Denial of future/clock desync session tokens.
4. Tampering detection on session usernames, timestamps, and signatures.
5. Brute-force rate limiting on /auth/login (HTTP 429 after 5 requests/min).
6. Proxy IP header resolution (X-Forwarded-For / X-Real-IP) in the rate limiter.
"""
import hashlib
import hmac
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request, HTTPException, status
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.routers.auth import sign_session, verify_session, get_current_user
from app.utils.rate_limiter import RateLimiter, login_rate_limiter


@pytest.fixture
def client():
    # Make sure we don't have overrides active during auth logic testing
    app.dependency_overrides.pop(get_current_user, None)
    return TestClient(app)


# ---------- Cryptographic Session Verification Tests ----------

def test_auth_session_valid_dynamic_signature():
    """Verify that a freshly generated dynamic session token validates successfully."""
    token = sign_session("admin", settings.SESSION_SECRET_KEY)
    assert token is not None
    assert token.count(":") == 2
    
    username = verify_session(token, settings.SESSION_SECRET_KEY)
    assert username == "admin"


def test_auth_session_expired_timestamp():
    """Verify that a session token older than 18 hours is rejected cryptographically."""
    # Generate timestamp from 19 hours ago
    expired_time = str(int(time.time()) - 19 * 3600)
    payload = f"admin:{expired_time}"
    signature = hmac.new(
        settings.SESSION_SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    expired_token = f"{payload}:{signature}"
    assert verify_session(expired_token, settings.SESSION_SECRET_KEY) is None


def test_auth_session_future_timestamp():
    """Verify that a session token with a future timestamp is rejected."""
    # Generate timestamp from 2 hours in the future
    future_time = str(int(time.time()) + 7200)
    payload = f"admin:{future_time}"
    signature = hmac.new(
        settings.SESSION_SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    future_token = f"{payload}:{signature}"
    assert verify_session(future_token, settings.SESSION_SECRET_KEY) is None


def test_auth_session_tampered_signature():
    """Verify that tampering with username, timestamp, or signature rejects the session."""
    token = sign_session("admin", settings.SESSION_SECRET_KEY)
    username, timestamp_str, signature = token.split(":", 2)
    
    # 1. Tamper with username
    tampered_user = f"attacker:{timestamp_str}:{signature}"
    assert verify_session(tampered_user, settings.SESSION_SECRET_KEY) is None
    
    # 2. Tamper with timestamp
    tampered_ts = f"admin:{int(timestamp_str) - 1}:{signature}"
    assert verify_session(tampered_ts, settings.SESSION_SECRET_KEY) is None
    
    # 3. Tamper with signature
    tampered_sig = f"admin:{timestamp_str}:1234567890abcdef"
    assert verify_session(tampered_sig, settings.SESSION_SECRET_KEY) is None


# ---------- Login Brute-force Rate Limiting Tests ----------

def test_auth_login_rate_limiting(client):
    """Verify that making more than 5 attempts in 60s triggers HTTP 429."""
    # Clean rate limiter storage to guarantee fresh test run
    login_rate_limiter.history.clear()
    
    payload = {"username": "admin", "password": "wrong-password"}
    
    # Execute 5 failed login attempts
    for _ in range(5):
        response = client.post("/auth/login", json=payload)
        # Should return 401 Unauthorized since credentials are wrong
        assert response.status_code == 401
        
    # The 6th attempt must be blocked by the rate limiter with 429
    blocked_response = client.post("/auth/login", json=payload)
    assert blocked_response.status_code == 429
    assert "Demasiados intentos" in blocked_response.json()["detail"]
    
    # Clean up rate limiter history at end of test to avoid polluting other runs
    login_rate_limiter.history.clear()


# ---------- Proxy IP Headers Resolution Tests ----------

def test_rate_limiter_proxy_headers():
    """Verify that client IP is resolved correctly from proxy headers."""
    limiter = RateLimiter(limit=2, window_seconds=10)
    
    # Mock Request 1: Using X-Forwarded-For header
    req_xff = MagicMock(spec=Request)
    req_xff.headers = {"X-Forwarded-For": "203.0.113.195, 70.41.3.18, 150.172.238.178"}
    req_xff.client = MagicMock()
    req_xff.client.host = "127.0.0.1"
    
    # Mock Request 2: Using X-Real-IP header
    req_xri = MagicMock(spec=Request)
    req_xri.headers = {"X-Real-IP": "198.51.100.42"}
    req_xri.client = MagicMock()
    req_xri.client.host = "127.0.0.1"
    
    # Verify that the limiter processes requests and identifies client IPs correctly
    limiter(req_xff)
    limiter(req_xff)
    
    # Third request from 203.0.113.195 should be blocked (limit is 2)
    with pytest.raises(HTTPException) as exc_info:
        limiter(req_xff)
    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    
    # But a request from X-Real-IP client (198.51.100.42) should be allowed!
    limiter(req_xri)
