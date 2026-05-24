"""Authentication router for the SDAI dashboard.

Uses lightweight, dynamically signed session cookies (HMAC-SHA256) with Unix timestamps
instead of heavy JWT tokens, implementing a secure, replay-safe, and zero-dependency
administrator login panel.

Credentials are resolved in two layers:
  1. Supabase `users` table (bcrypt password_hash) — production source of truth.
  2. `.env` ADMIN_USERNAME / ADMIN_PASSWORD — bootstrap fallback when the table
     is empty or unreachable, so the system stays operable on first install.
"""
import hashlib
import hmac
import sys
import time
from datetime import datetime, timezone
from typing import Optional

import bcrypt
from fastapi import APIRouter, Cookie, HTTPException, Response, status, Depends
from pydantic import BaseModel

from app.config import settings
from app.db.supabase_client import get_client, execute_with_retry
from app.utils.rate_limiter import login_rate_limiter

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------- Password helpers ----------

def hash_password(plain: str) -> str:
    """Return bcrypt hash (UTF-8 string) for storage in `users.password_hash`."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time bcrypt verify. Returns False on any malformed input."""
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _lookup_db_user(username: str) -> Optional[dict]:
    """Fetch an active user row from Supabase. Returns None if missing or DB offline."""
    client = get_client()
    if client is None:
        return None
    try:
        res = execute_with_retry(
            lambda c: c.table("users")
            .select("username, password_hash, role, active")
            .eq("username", username)
            .eq("active", True)
            .limit(1)
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception as e:
        print(f"[auth] users lookup failed: {e}", file=sys.stderr)
        return None


def _mark_last_login(username: str) -> None:
    """Best-effort timestamp update. Never blocks login on failure."""
    client = get_client()
    if client is None:
        return
    try:
        execute_with_retry(
            lambda c: c.table("users")
            .update({"last_login_at": datetime.now(timezone.utc).isoformat()})
            .eq("username", username)
        )
    except Exception as e:
        print(f"[auth] last_login update failed: {e}", file=sys.stderr)


def authenticate(username: str, password: str) -> bool:
    """Validate credentials against Supabase users table, falling back to .env admin."""
    if not username or not password:
        return False
    db_user = _lookup_db_user(username)
    if db_user:
        if verify_password(password, db_user.get("password_hash", "")):
            _mark_last_login(username)
            return True
        return False
    # Bootstrap fallback — single admin from environment.
    if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
        return True
    return False


class LoginRequest(BaseModel):
    username: str
    password: str


class SessionResponse(BaseModel):
    authenticated: bool
    username: Optional[str] = None


# ---------- HMAC Helper Methods (Dynamic signed sessions with timestamps) ----------

def sign_session(username: str, secret_key: str) -> str:
    """Create a tamper-proof session string signed with the secret key and current timestamp.

    Format: username:timestamp:signature
    """
    timestamp = str(int(time.time()))
    payload = f"{username}:{timestamp}"
    signature = hmac.new(
        secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"{payload}:{signature}"


def verify_session(cookie_value: str, secret_key: str) -> Optional[str]:
    """Verify session signature and check timestamp freshness.

    Prevents replay attacks by enforcing a maximum age of 18 hours.
    """
    if not cookie_value or cookie_value.count(":") < 2:
        return None
    try:
        username, timestamp_str, signature = cookie_value.split(":", 2)
        timestamp = int(timestamp_str)
        
        # 1. Verify signature integrity
        payload = f"{username}:{timestamp_str}"
        expected = hmac.new(
            secret_key.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected):
            return None
            
        # 2. Verify time window (18 hours max duration, protect against minor clock desyncs)
        now = int(time.time())
        if now - timestamp > 18 * 3600 or now - timestamp < -60:
            return None
            
        return username
    except Exception:
        pass
    return None


# ---------- Dependency Injection for Protected Routes ----------

async def get_current_user(sdai_session: Optional[str] = Cookie(None)) -> str:
    """Dependency that checks for a valid, non-expired session cookie.

    Raises HTTP 401 if missing, tampered, or expired. The username in the cookie
    is trusted because the HMAC signature is server-side, so any analyst recorded
    in Supabase (or the env fallback admin) can hold a valid session.
    """
    if not sdai_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inactiva. Inicia sesión para acceder a esta función."
        )
    username = verify_session(sdai_session, settings.SESSION_SECRET_KEY)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o expirada. Por favor, reautentícate."
        )
    return username


# ---------- Endpoints ----------

@router.post("/login", response_model=dict, dependencies=[Depends(login_rate_limiter)])
async def login(body: LoginRequest, response: Response):
    """Authenticate analyst credentials (DB-backed bcrypt or .env fallback) and set
    a signed, timestamped session cookie."""
    if not authenticate(body.username, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )

    session_val = sign_session(body.username, settings.SESSION_SECRET_KEY)
    response.set_cookie(
        key="sdai_session",
        value=session_val,
        httponly=True,
        samesite="lax",
        secure=settings.SESSION_COOKIE_SECURE,
        max_age=18 * 3600  # 18 hours duration
    )
    return {"status": "ok", "message": "Autenticación exitosa"}


@router.post("/logout", response_model=dict)
async def logout(response: Response):
    """Clear the signed session cookie, logging out the administrator."""
    response.delete_cookie(key="sdai_session")
    return {"status": "ok", "message": "Sesión cerrada"}


@router.get("/session", response_model=SessionResponse)
async def get_session(sdai_session: Optional[str] = Cookie(None)):
    """Check if the current client has a valid session cookie."""
    username = verify_session(sdai_session, settings.SESSION_SECRET_KEY)
    if username:
        return SessionResponse(authenticated=True, username=username)
    return SessionResponse(authenticated=False)
