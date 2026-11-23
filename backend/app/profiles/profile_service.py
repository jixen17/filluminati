from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Profile, Task, Document, TaskStatus
from app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileOut

# A profile with a task in one of these states cannot be deleted.
BUSY_STATUSES = {
    TaskStatus.ANALYZING.value,
    TaskStatus.INSPECTING.value,
    TaskStatus.MAPPING.value,
    TaskStatus.FILLING.value,
    TaskStatus.VERIFYING.value,
}


# ---------- profile access ----------

def get_profile_or_404(db: Session, profile_id: str) -> Profile:
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


def _to_out(db: Session, p: Profile) -> ProfileOut:
    doc_count = db.scalar(
        select(func.count()).select_from(Document).where(Document.profile_id == p.id)
    )
    task_count = db.scalar(
        select(func.count()).select_from(Task).where(Task.profile_id == p.id)
    )
    return ProfileOut(
        id=p.id, name=p.name, avatar=p.avatar, created_at=p.created_at,
        document_count=doc_count or 0, task_count=task_count or 0,
    )


# ---------- CRUD ----------

def create_profile(db: Session, data: ProfileCreate) -> ProfileOut:
    profile = Profile(name=data.name, avatar=data.avatar)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _to_out(db, profile)


def list_profiles(db: Session) -> list[ProfileOut]:
    profiles = db.scalars(select(Profile).order_by(Profile.created_at)).all()
    return [_to_out(db, p) for p in profiles]


def get_profile(db: Session, profile_id: str) -> ProfileOut:
    return _to_out(db, get_profile_or_404(db, profile_id))


def update_profile(db: Session, profile_id: str, data: ProfileUpdate) -> ProfileOut:
    profile = get_profile_or_404(db, profile_id)
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is None:
        raise HTTPException(status_code=422, detail="Name cannot be null")
    for key, value in changes.items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return _to_out(db, profile)


def delete_profile(db: Session, profile_id: str) -> None:
    profile = get_profile_or_404(db, profile_id)

    busy = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.profile_id == profile_id, Task.status.in_(BUSY_STATUSES)
        )
    )
    if busy:
        raise HTTPException(
            status_code=409,
            detail="A task is currently running for this profile. Cancel it first.",
        )

    # Remove stored files from disk, then cascade-delete rows.
    upload_root = settings.upload_dir.resolve()
    for doc in profile.documents:
        path = (upload_root / doc.storage_path).resolve()
        if upload_root in path.parents:          # never delete outside uploads/
            path.unlink(missing_ok=True)

    db.delete(profile)   # cascades to tasks, documents, fields, events
    db.commit()


# ---------- ownership helpers (reused by every later route) ----------

def get_owned_task(db: Session, task_id: str, profile_id: str) -> Task:
    task = db.get(Task, task_id)
    if not task or task.profile_id != profile_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def get_owned_document(db: Session, doc_id: str, profile_id: str) -> Document:
    doc = db.get(Document, doc_id)
    if not doc or doc.profile_id != profile_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc