from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routers import config, health, events, alerts, stats, live, capture
from app.capture_controller import controller as capture_controller

app = FastAPI(
    title="SDAI - Sistema Detección Alertas Intrusiones",
    description="API REST para detección de intrusiones en redes locales (PyMEs Barinas)",
    version="0.1.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(config.router)
app.include_router(events.router)
app.include_router(alerts.router)
app.include_router(stats.router)
app.include_router(live.router)
app.include_router(capture.router)


@app.on_event("shutdown")
def _stop_capture_on_shutdown() -> None:
    """Ensure Scapy's background sniffer thread is closed cleanly."""
    capture_controller.stop()

# Resolve path to the SDAI directory
ROOT = Path(__file__).resolve().parent.parent.parent
SDAI_DIR = ROOT / "SDAI"

if SDAI_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(SDAI_DIR)), name="static")

@app.get("/dashboard", include_in_schema=False)
async def get_dashboard():
    dashboard_path = SDAI_DIR / "SDAI Dashboard.html"
    if dashboard_path.exists():
        return FileResponse(str(dashboard_path))
    return {"error": "Dashboard file not found"}


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"name": "SDAI", "docs": "/docs", "health": "/health", "dashboard": "/dashboard"}

