import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class TaskStatus(str, enum.Enum):
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    ANALYZING = "ANALYZING"
    INSPECTING = "INSPECTING"
    MAPPING = "MAPPING"
    NEEDS_INPUT = "NEEDS_INPUT"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    FILLING = "FILLING"
    VERIFYING = "VERIFYING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class FieldStatus(str, enum.Enum):
    MATCHED = "matched"
    NEEDS_REVIEW = "needs_review"
    MISSING = "missing"
    CONFLICT = "conflict"
    USER_SUPPLIED = "user_supplied"
    APPROVED = "approved"
    FILLED = "filled"
    VERIFIED = "verified"
    FAILED = "failed"
    SKIPPED = "skipped"

class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("profile"))
    name: Mapped[str] = mapped_column(String(100))
    avatar: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    tasks = relationship("Task", back_populates="profile", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="profile", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("task"))
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), index=True)
    goal: Mapped[str] = mapped_column(String(500))
    target_url: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(30), default=TaskStatus.CREATED.value)
    revision: Mapped[int] = mapped_column(Integer, default=1)          # bumps on any field edit
    approved_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    profile = relationship("Profile", back_populates="tasks")
    fields = relationship("FormField", back_populates="task", cascade="all, delete-orphan")
    events = relationship("AgentEvent", back_populates="task", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("doc"))
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), index=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(300))          # original name, display only
    content_type: Mapped[str] = mapped_column(String(100))
    storage_path: Mapped[str] = mapped_column(String(500))      # safe generated name
    extracted_pages: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{page, text}]
    extracted_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)   # structured LLM output
    extraction_status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile = relationship("Profile", back_populates="documents")

class FormField(Base):
    __tablename__ = "form_fields"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: new_id("ff"))
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    field_key: Mapped[str] = mapped_column(String(50))          # e.g. field_07, per inspection
    label: Mapped[str] = mapped_column(String(300))
    type: Mapped[str] = mapped_column(String(30))
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    options: Mapped[list | None] = mapped_column(JSON, nullable=True)
    locator_hint: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # label/name/id for Playwright
    proposed_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=FieldStatus.MISSING.value)
    observed_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    task = relationship("Task", back_populates="fields")

class AgentEvent(Base):
    __tablename__ = "agent_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(30))
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    task = relationship("Task", back_populates="events")