from datetime import datetime
from pydantic import BaseModel


class PageOut(BaseModel):
    page: int
    text: str


class DocumentOut(BaseModel):
    id: str
    task_id: str | None
    filename: str
    content_type: str
    extraction_status: str
    page_count: int
    char_count: int
    created_at: datetime


class DocumentDetail(DocumentOut):
    pages: list[PageOut]