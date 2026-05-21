from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, HTTPException

from app.db.supabase_client import get_client, execute_with_retry
from app.models.schemas import ConfigItem, ConfigResponse

router = APIRouter(prefix="/config", tags=["config"])

# In-memory fallback for Sprint 1 (when Supabase not configured yet)
_memory_store: Dict[str, ConfigResponse] = {}


@router.get("", response_model=List[ConfigResponse])
async def list_config() -> List[ConfigResponse]:
    client = get_client()
    if client is None:
        return list(_memory_store.values())
    res = execute_with_retry(lambda c: c.table("configurations").select("*"))
    return [
        ConfigResponse(key=r["key"], value=r["value"], updated_at=r.get("updated_at"))
        for r in res.data
    ]

@router.get("/{key}", response_model=ConfigResponse)
async def get_config(key: str) -> ConfigResponse:
    client = get_client()
    if client is None:
        if key not in _memory_store:
            raise HTTPException(status_code=404, detail=f"key '{key}' not found")
        return _memory_store[key]
    try:
        res = execute_with_retry(lambda c: c.table("configurations").select("*").eq("key", key).single())
        return ConfigResponse(**res.data)
    except Exception as e:
        if "PGRST116" in str(e) or "0 rows" in str(e):
            raise HTTPException(status_code=404, detail=f"key '{key}' not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=ConfigResponse, status_code=201)
async def upsert_config(item: ConfigItem) -> ConfigResponse:
    client = get_client()
    now = datetime.now(timezone.utc)
    if client is None:
        resp = ConfigResponse(key=item.key, value=item.value, updated_at=now)
        _memory_store[item.key] = resp
        return resp
    payload = {"key": item.key, "value": item.value, "updated_at": now.isoformat()}
    res = execute_with_retry(lambda c: c.table("configurations").upsert(payload))
    return ConfigResponse(**res.data[0])

