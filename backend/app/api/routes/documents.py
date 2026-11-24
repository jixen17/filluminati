import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.orchestrator import change_status
from app.core.config import settings
from app.db.database import get_db
from app.db.models import Document, Task, TaskStatus, new_id
from app.schemas.document import DocumentDetail, DocumentOut, PageOut
from app.services import document_service as ds
from app.services.event_service import emit

router = APIRouter(prefix="/tasks", tags=["documents"])

MAX_FILES_PER_TASK = 5
UPLOADABLE = {TaskStatus.CREATED.value, TaskStatus.UPLOADING.value}


def _get_task(db: Session, task_id: str) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _to_out(doc: Document) -> DocumentOut:
    pages = doc.extracted_pages or []
    return DocumentOut(
        id=doc.id, task_id=doc.task_id, filename=doc.filename,
        content_type=doc.content_type, extraction_status=doc.extraction_status,
        page_count=len(pages), char_count=sum(len(p["text"]) for p in pages),
        created_at=doc.created_at,
    )


def _get_task_document(db: Session, task: Task, doc_id: str) -> Document:
    doc = db.get(Document, doc_id)
    if not doc or doc.task_id != task.id or doc.profile_id != task.profile_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    buf = bytearray()
    while chunk := await file.read(64 * 1024):
        buf.extend(chunk)
        if len(buf) > limit:
            raise HTTPException(
                status_code=413,
                detail=f"'{file.filename}' exceeds the {limit // (1024 * 1024)} MB limit.",
            )
    return bytes(buf)


@router.post("/{task_id}/documents", response_model=list[DocumentOut], status_code=201)
async def upload_documents(
    task_id: str, files: list[UploadFile] = File(...), db: Session = Depends(get_db)
):
    task = _get_task(db, task_id)
    if task.status not in UPLOADABLE:
        raise HTTPException(status_code=409, detail="Documents can only be added before analysis starts.")

    existing = db.scalar(select(func.count()).select_from(Document).where(Document.task_id == task.id)) or 0
    if existing + len(files) > MAX_FILES_PER_TASK:
        raise HTTPException(status_code=400, detail=f"A task can have at most {MAX_FILES_PER_TASK} documents.")

    # 1) Validate + extract everything in memory first (all-or-nothing).
    prepared = []
    for f in files:
        data = await _read_limited(f, settings.max_upload_bytes)
        name = ds.clean_filename(f.filename or "document")
        try:
            ext, ctype, pages = await asyncio.to_thread(ds.validate_and_extract, name, f.content_type, data)
        except ds.DocumentError as e:
            raise HTTPException(status_code=422, detail=str(e))
        prepared.append((name, ext, ctype, pages, data))

    # 2) Write files + rows. The document inherits its profile from the task.
    written: list[Path] = []
    docs: list[Document] = []
    try:
        for name, ext, ctype, pages, data in prepared:
            doc_id = new_id("doc")
            stored = f"{doc_id}{ext}"
            path = settings.upload_dir / stored
            path.write_bytes(data)
            written.append(path)
            docs.append(Document(
                id=doc_id, profile_id=task.profile_id, task_id=task.id,
                filename=name, content_type=ctype, storage_path=stored,
                extracted_pages=pages, extraction_status="extracted",
            ))
        db.add_all(docs)
        db.commit()
    except Exception:
        db.rollback()
        for p in written:
            p.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Could not save the uploaded files.")

    # 3) State + event (counts only, no filenames in the event log).
    msg = f"Uploaded {len(docs)} document(s)"
    if task.status == TaskStatus.CREATED.value:
        await change_status(db, task, TaskStatus.UPLOADING, msg)
    else:
        await emit(task.id, "agent_status", {"status": task.status, "message": msg})

    return [_to_out(d) for d in docs]


@router.get("/{task_id}/documents", response_model=list[DocumentOut])
def list_task_documents(task_id: str, db: Session = Depends(get_db)):
    task = _get_task(db, task_id)
    stmt = select(Document).where(
        Document.task_id == task.id, Document.profile_id == task.profile_id
    ).order_by(Document.created_at)
    return [_to_out(d) for d in db.scalars(stmt).all()]


@router.get("/{task_id}/documents/{doc_id}", response_model=DocumentDetail)
def get_task_document(task_id: str, doc_id: str, db: Session = Depends(get_db)):
    task = _get_task(db, task_id)
    doc = _get_task_document(db, task, doc_id)
    return DocumentDetail(**_to_out(doc).model_dump(), pages=[PageOut(**p) for p in doc.extracted_pages or []])


@router.delete("/{task_id}/documents/{doc_id}", status_code=204)
def delete_task_document(task_id: str, doc_id: str, db: Session = Depends(get_db)):
    task = _get_task(db, task_id)
    if task.status not in UPLOADABLE:
        raise HTTPException(status_code=409, detail="Documents can only be removed before analysis starts.")
    doc = _get_task_document(db, task, doc_id)
    upload_root = settings.upload_dir.resolve()
    path = (upload_root / doc.storage_path).resolve()
    if upload_root in path.parents:
        path.unlink(missing_ok=True)
    db.delete(doc)
    db.commit()
    return Response(status_code=204)