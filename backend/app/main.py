from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Cookie, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import auth, config, health, events, alerts, stats, live, capture, ai
from app.routers.auth import get_current_user, verify_session
from app.capture_controller import controller as capture_controller
from app.services import batch_writer
from app.utils.logger import logger


_DEFAULT_ADMIN_PW = "admin123"
_DEFAULT_SESSION_SECRET = "sdai_super_secret_session_key_99"


def _emit_security_warnings() -> None:
    """Loud, visible warnings when the system boots with insecure defaults."""
    if settings.ADMIN_PASSWORD == _DEFAULT_ADMIN_PW:
        logger.warning(
            "[SECURITY] ADMIN_PASSWORD still set to the public default. "
            "Set ADMIN_PASSWORD in .env before exposing SDAI."
        )
    if settings.SESSION_SECRET_KEY == _DEFAULT_SESSION_SECRET:
        logger.warning(
            "[SECURITY] SESSION_SECRET_KEY still set to the public default. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    if (settings.CORS_ALLOWED_ORIGINS or "").strip() == "*" and settings.SESSION_COOKIE_SECURE:
        logger.warning(
            "[SECURITY] CORS_ALLOWED_ORIGINS='*' with SESSION_COOKIE_SECURE=true. "
            "Wildcard CORS disables credentialed requests — restrict origins in production."
        )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _emit_security_warnings()
    batch_writer.start()
    try:
        yield
    finally:
        await batch_writer.stop()
        capture_controller.stop()


app = FastAPI(
    title="SDAI - Sistema Detección Alertas Intrusiones",
    description="API REST para detección de intrusiones en redes locales (PyMEs Barinas)",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — controlled by CORS_ALLOWED_ORIGINS (.env). "*" disables credentialed
# requests per spec; for production set explicit origins so cookies can flow.
_origins_raw = (settings.CORS_ALLOWED_ORIGINS or "").strip()
if _origins_raw == "*" or not _origins_raw:
    _allow_origins = ["*"]
    _allow_credentials = False
else:
    _allow_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]
    _allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(config.router, dependencies=[Depends(get_current_user)])
app.include_router(events.router)
app.include_router(alerts.router, dependencies=[Depends(get_current_user)])
app.include_router(stats.router, dependencies=[Depends(get_current_user)])
app.include_router(live.router)
app.include_router(capture.router, dependencies=[Depends(get_current_user)])
app.include_router(ai.router, dependencies=[Depends(get_current_user)])


# Resolve path to the SDAI directory
ROOT = Path(__file__).resolve().parent.parent.parent
SDAI_DIR = ROOT / "SDAI"

if SDAI_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(SDAI_DIR)), name="static")

def _has_valid_session(sdai_session: Optional[str]) -> bool:
    if not sdai_session:
        return False
    return verify_session(sdai_session, settings.SESSION_SECRET_KEY) is not None


@app.get("/login", include_in_schema=False)
async def get_login_page(sdai_session: Optional[str] = Cookie(None)):
    """Serve the SOC login page. If session is valid, jump straight to dashboard."""
    if _has_valid_session(sdai_session):
        return RedirectResponse(url="/dashboard", status_code=302)
    login_path = SDAI_DIR / "SDAI Login.html"
    if login_path.exists():
        return FileResponse(str(login_path))
    return {"error": "Login page not found"}


@app.get("/dashboard", include_in_schema=False)
async def get_dashboard(sdai_session: Optional[str] = Cookie(None)):
    """Serve the dashboard only when an authenticated session cookie is present."""
    if not _has_valid_session(sdai_session):
        return RedirectResponse(url="/login", status_code=302)
    dashboard_path = SDAI_DIR / "SDAI Dashboard.html"
    if dashboard_path.exists():
        return FileResponse(str(dashboard_path))
    return {"error": "Dashboard file not found"}


@app.get("/", include_in_schema=False)
async def root(sdai_session: Optional[str] = Cookie(None)):
    """Send authenticated users to dashboard, otherwise to the login screen."""
    if _has_valid_session(sdai_session):
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/login", status_code=302)

