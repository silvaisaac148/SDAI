"""Tests del CRUD de usuarios (admin-only) expuestos en /auth/users.

Cubre:
- Listar / crear / actualizar / eliminar usuarios desde la API
- Enforcement role admin
- Validaciones (username, password, role)
- Protecciones (no auto-eliminarse, no eliminar bootstrap admin, no auto-desactivar)
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.routers.auth import get_current_user


@pytest.fixture
def admin_client():
    """Cliente autenticado como admin (rol resuelto a 'admin')."""
    app.dependency_overrides[get_current_user] = lambda: "isaac_admin"
    with patch("app.routers.auth._resolve_role", return_value="admin"):
        yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def viewer_client():
    """Cliente autenticado pero rol 'viewer' — debe ser rechazado en endpoints admin."""
    app.dependency_overrides[get_current_user] = lambda: "viewer_user"
    with patch("app.routers.auth._resolve_role", return_value="viewer"):
        yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


# ---------- GET /auth/users ----------

def test_list_users_admin_ok(admin_client):
    fake_rows = [
        {"username": "isaac_admin", "role": "admin", "active": True, "last_login_at": None, "created_at": None},
        {"username": "carlos", "role": "viewer", "active": True, "last_login_at": None, "created_at": None},
    ]
    mock_res = MagicMock(data=fake_rows)
    with patch("app.routers.auth.get_client", return_value=MagicMock()), \
         patch("app.routers.auth.execute_with_retry", return_value=mock_res):
        r = admin_client.get("/auth/users")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert all("password_hash" not in u for u in data)


def test_list_users_viewer_forbidden(viewer_client):
    r = viewer_client.get("/auth/users")
    assert r.status_code == 403


# ---------- POST /auth/users ----------

def test_create_user_admin_ok(admin_client):
    with patch("app.routers.auth.get_client", return_value=MagicMock()), \
         patch("app.routers.auth._lookup_db_user", return_value=None), \
         patch("app.routers.auth.execute_with_retry") as mock_exec:
        r = admin_client.post("/auth/users", json={
            "username": "nuevo_user",
            "password": "PasswordSegura1!",
            "role": "viewer",
        })
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "nuevo_user"
    assert body["role"] == "viewer"
    assert body["active"] is True


def test_create_user_rejects_short_password(admin_client):
    with patch("app.routers.auth.get_client", return_value=MagicMock()), \
         patch("app.routers.auth._lookup_db_user", return_value=None):
        r = admin_client.post("/auth/users", json={
            "username": "u", "password": "abc", "role": "viewer",
        })
    assert r.status_code == 400


def test_create_user_rejects_invalid_role(admin_client):
    with patch("app.routers.auth.get_client", return_value=MagicMock()), \
         patch("app.routers.auth._lookup_db_user", return_value=None):
        r = admin_client.post("/auth/users", json={
            "username": "valido_user",
            "password": "PasswordSegura1!",
            "role": "superuser",
        })
    assert r.status_code == 400


def test_create_user_rejects_invalid_username(admin_client):
    with patch("app.routers.auth.get_client", return_value=MagicMock()):
        r = admin_client.post("/auth/users", json={
            "username": "ab",  # too short
            "password": "PasswordSegura1!",
            "role": "viewer",
        })
    assert r.status_code == 400


def test_create_user_rejects_duplicate(admin_client):
    existing = {"username": "ya_existe", "role": "viewer", "active": True}
    with patch("app.routers.auth.get_client", return_value=MagicMock()), \
         patch("app.routers.auth._lookup_db_user", return_value=existing):
        r = admin_client.post("/auth/users", json={
            "username": "ya_existe",
            "password": "PasswordSegura1!",
            "role": "viewer",
        })
    assert r.status_code == 409


def test_create_user_viewer_forbidden(viewer_client):
    r = viewer_client.post("/auth/users", json={
        "username": "intento", "password": "PasswordSegura1!", "role": "viewer",
    })
    assert r.status_code == 403


# ---------- PATCH /auth/users/{username} ----------

def test_update_user_password(admin_client):
    existing = {"username": "target", "role": "viewer", "active": True}
    with patch("app.routers.auth.get_client", return_value=MagicMock()), \
         patch("app.routers.auth._lookup_db_user", return_value=existing), \
         patch("app.routers.auth.execute_with_retry") as mock_exec:
        r = admin_client.patch("/auth/users/target", json={
            "password": "NuevaPasswordSegura1!",
        })
    assert r.status_code == 200


def test_update_user_role_to_admin(admin_client):
    existing = {"username": "target", "role": "viewer", "active": True}
    with patch("app.routers.auth.get_client", return_value=MagicMock()), \
         patch("app.routers.auth._lookup_db_user", return_value=existing), \
         patch("app.routers.auth.execute_with_retry") as mock_exec:
        r = admin_client.patch("/auth/users/target", json={"role": "admin"})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_update_user_cannot_deactivate_self(admin_client):
    existing = {"username": "isaac_admin", "role": "admin", "active": True}
    with patch("app.routers.auth.get_client", return_value=MagicMock()), \
         patch("app.routers.auth._lookup_db_user", return_value=existing):
        r = admin_client.patch("/auth/users/isaac_admin", json={"active": False})
    assert r.status_code == 400


def test_update_user_404_when_missing(admin_client):
    with patch("app.routers.auth.get_client", return_value=MagicMock()), \
         patch("app.routers.auth._lookup_db_user", return_value=None):
        r = admin_client.patch("/auth/users/fantasma", json={"role": "admin"})
    assert r.status_code == 404


# ---------- DELETE /auth/users/{username} ----------

def test_delete_user_ok(admin_client):
    existing = {"username": "ex_empleado", "role": "viewer", "active": True}
    with patch("app.routers.auth.get_client", return_value=MagicMock()), \
         patch("app.routers.auth._lookup_db_user", return_value=existing), \
         patch("app.routers.auth.execute_with_retry") as mock_exec:
        r = admin_client.delete("/auth/users/ex_empleado")
    assert r.status_code == 204


def test_delete_user_cannot_delete_self(admin_client):
    r = admin_client.delete("/auth/users/isaac_admin")
    assert r.status_code == 400


def test_delete_user_cannot_delete_bootstrap_admin(admin_client):
    r = admin_client.delete(f"/auth/users/{settings.ADMIN_USERNAME}")
    assert r.status_code == 400


def test_delete_user_viewer_forbidden(viewer_client):
    r = viewer_client.delete("/auth/users/cualquiera")
    assert r.status_code == 403


# ---------- GET /auth/me ----------

def test_me_returns_username_and_role(admin_client):
    r = admin_client.get("/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "isaac_admin"
    assert body["role"] == "admin"
