from datetime import datetime
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskCreate(BaseModel):
    profile_id: str
    goal: str = Field(min_length=1, max_length=500)
    target_url: str = Field(min_length=1, max_length=1000)

    @field_validator("goal")
    @classmethod
    def _goal(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Goal cannot be blank")
        return v

    @field_validator("target_url")
    @classmethod
    def _url(cls, v: str) -> str:
        v = v.strip()
        p = urlparse(v)
        # Basic check only. The full allowlist/SSRF check comes in Step 11.
        if p.scheme not in ("http", "https") or not p.netloc:
            raise ValueError("target_url must be a valid http(s) URL")
        return v


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    goal: str
    target_url: str
    status: str
    revision: int
    approved_revision: int | None = None
    error_summary: str | None = None
    created_at: datetime
    updated_at: datetime


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    data: dict | None = None
    created_at: datetime