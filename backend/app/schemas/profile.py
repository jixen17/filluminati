from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_name(v: str | None) -> str | None:
    if v is None:
        return v
    v = v.strip()
    if not v:
        raise ValueError("Name cannot be blank")
    return v


class ProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    avatar: str | None = Field(default=None, max_length=200)

    _strip = field_validator("name")(_clean_name)


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    avatar: str | None = Field(default=None, max_length=200)

    _strip = field_validator("name")(_clean_name)


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    avatar: str | None = None
    created_at: datetime
    document_count: int = 0   # counts only; never document names
    task_count: int = 0