from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=_utcnow)


class ConfigItem(BaseModel):
    key: str = Field(..., min_length=1, max_length=64)
    value: Any


class ConfigResponse(BaseModel):
    key: str
    value: Any
    updated_at: Optional[datetime] = None
