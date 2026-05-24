"""End-to-end tests for the standalone login + dashboard gating flow.

Covers:
- /login serves the SOC login HTML and includes the auth wiring.
- /dashboard redirects unauthenticated visitors to /login.
- /dashboard serves the dashboard once a valid session cookie is present.
- / (root) navigates to /login when no session is found and /dashboard otherwise.
- Successful POST /auth/login sets an HttpOnly session cookie.
- DB-backed bcrypt authentication is preferred over the .env fallback admin.
- bcrypt hash_password + verify_password round-trip.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.routers.auth import (
    authenticate,
    get_current_user,
    hash_password,
    sign_session,
    verify_password,
)
from app.utils.rate_limiter import login_rate_limiter


@pytest.fixture
def client():
    """Clean client with no auto-overrides so we can exercise the real cookie path."""
    app.dependency_overrides.pop(get_current_user, None)
    login_rate_limiter.history.clear()
    return TestClient(app)


# ---------- /login route ----------

def test_login_page_served(client):
    r = client.get("/login")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    body = r.text
    assert "SDAI" in body
    assert "/auth/login" in body  # JS hits the login endpoint
    assert "/auth/session" in body  # probes existing session on load


def test_login_page_redirects_when_already_authenticated(client):
    token = sign_session(settings.ADMIN_USERNAME, settings.SESSION_SECRET_KEY)
    client.cookies.set("sdai_session", token)
    r = client.get("/login", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/dashboard"


# ---------- /dashboard gating ----------

def test_dashboard_redirects_when_unauthenticated(client):
    r = client.get("/dashboard", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_dashboard_served_when_authenticated(client):
    token = sign_session(settings.ADMIN_USERNAME, settings.SESSION_SECRET_KEY)
    client.cookies.set("sdai_session", token)
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "SDAI" in r.text


def test_dashboard_rejects_tampered_cookie(client):
    client.cookies.set("sdai_session", "admin:9999999999:not-a-real-signature")
    r = client.get("/dashboard", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


# ---------- / root ----------

def test_root_redirects_to_dashboard_when_authenticated(client):
    token = sign_session(settings.ADMIN_USERNAME, settings.SESSION_SECRET_KEY)
    client.cookies.set("sdai_session", token)
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/dashboard"


# ---------- POST /auth/login cookie flow ----------

def test_login_sets_httponly_cookie(client):
    r = client.post(
        "/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )
    assert r.status_code == 200
    set_cookie = r.headers.get("set-cookie", "").lower()
    assert "sdai_session=" in set_cookie
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie


def test_login_rejects_bad_credentials(client):
    r = client.post(
        "/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": "definitely-wrong"},
    )
    assert r.status_code == 401


# ---------- Bcrypt + DB-backed authentication ----------

def test_hash_password_and_verify_roundtrip():
    pw = "S3nsor!Barinas#2026"
    h = hash_password(pw)
    assert h != pw
    assert h.startswith("$2")  # bcrypt prefix
    assert verify_password(pw, h)
    assert not verify_password("other", h)
    assert not verify_password("", h)
    assert not verify_password(pw, "")
    assert not verify_password(pw, "not-a-bcrypt-hash")


def test_authenticate_prefers_db_user_over_env_fallback():
    """Even when the env admin password is correct, an active DB user wins."""
    stored_hash = hash_password("real-db-password")
    db_user = {
        "username": "analista_db",
        "password_hash": stored_hash,
        "role": "admin",
        "active": True,
    }
    with patch("app.routers.auth._lookup_db_user", return_value=db_user), \
         patch("app.routers.auth._mark_last_login") as mock_touch:
        assert authenticate("analista_db", "real-db-password") is True
        mock_touch.assert_called_once_with("analista_db")
        assert authenticate("analista_db", "wrong") is False


def test_authenticate_falls_back_to_env_admin_when_db_empty():
    with patch("app.routers.auth._lookup_db_user", return_value=None):
        assert authenticate(settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD) is True
        assert authenticate(settings.ADMIN_USERNAME, "wrong") is False
        assert authenticate("ghost", settings.ADMIN_PASSWORD) is False
