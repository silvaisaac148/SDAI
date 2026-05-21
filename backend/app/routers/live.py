import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/live", tags=["live"])

# Active SSE listener queues
_listeners: list = []


async def broadcast_packet(pkt_dict: dict):
    """Broadcast captured packet and alerts to all active live streams."""
    for q in list(_listeners):
        try:
            await q.put(pkt_dict)
        except Exception:
            pass


@router.get("/stream")
async def live_stream():
    """Server-Sent Events endpoint to stream packets and alerts in real-time."""
    q = asyncio.Queue()
    _listeners.append(q)
    
    async def event_generator():
        try:
            while True:
                pkt = await q.get()
                # SSE protocol format: "data: <message>\n\n"
                yield f"data: {json.dumps(pkt, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if q in _listeners:
                _listeners.remove(q)
                
    return StreamingResponse(event_generator(), media_type="text/event-stream")
