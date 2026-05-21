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
