"""Remote control of the live Scapy sniffer."""
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.capture_controller import controller

router = APIRouter(prefix="/capture", tags=["capture"])


class StartRequest(BaseModel):
    interface: Optional[str] = None
    bpf: str = "ip"


@router.get("/status", response_model=dict)
async def get_status():
    return controller.status()


@router.get("/interfaces", response_model=list)
async def get_interfaces():
    """List all available network interfaces in Scapy."""
    interfaces = []
    try:
        from scapy.all import conf
        seen_names = set()
        for iface in conf.ifaces.values():
            name = iface.name
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            interfaces.append({
                "name": name,
                "description": iface.description or name,
                "ip": iface.ip or None
            })
        # If list is empty, add a default fallback
        if not interfaces:
            interfaces.append({"name": "Wi-Fi", "description": "Interfaz Wi-Fi estándar", "ip": None})
    except Exception as e:
        interfaces = [
            {"name": "Wi-Fi", "description": f"Error cargando Scapy: {e}", "ip": None}
        ]
    return interfaces


@router.post("/start", response_model=dict)
async def start_capture(body: Optional[StartRequest] = None):
    body = body or StartRequest()
    return controller.start(interface=body.interface, bpf=body.bpf)


@router.post("/stop", response_model=dict)
async def stop_capture():
    return controller.stop()


@router.post("/pause", response_model=dict)
async def pause_capture():
    return controller.pause()


@router.post("/resume", response_model=dict)
async def resume_capture():
    return controller.resume()

