import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.extractor import extract_facts
from app.agent.orchestrator import change_status
from app.db.database import get_db
from app.db.models import Document, Task, TaskStatus
from app.schemas.extraction import DocFacts
from app.services.event_service import emit
from app.services.llm_service import LLMError, LLMNotConfigured, get_llm

router = APIRouter(prefix="/tasks", tags=["extraction"])

EXTRACTABLE = {TaskStatus.CREATED.value, TaskStatus.UPLOADING.value, TaskStatus.ANALYZING.value}


def _task_docs(db: Session, task: Task) -> list[Document]:
    stmt = select(Document).where(
        Document.task_id == task.id, Document.profile_id == task.profile_id
    ).order_by(Document.created_at)
    return list(db.scalars(stmt).all())


@router.post("/{task_id}/extract", response_model=list[DocFacts])
async def extract(task_id: str, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in EXTRACTABLE:
        raise HTTPException(status_code=409, detail=f"Cannot extract while task is {task.status}.")
    docs = _task_docs(db, task)
    if not docs:
        raise HTTPException(status_code=400, detail="Upload at least one document first.")
    try:
        llm = get_llm()
    except LLMNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e))

    if task.status != TaskStatus.ANALYZING.value:
        await change_status(db, task, TaskStatus.ANALYZING, "Reading your documents")

    results, total = [], 0
    for doc in docs:
        try:
            facts, dropped = await asyncio.to_thread(
                extract_facts, llm, doc.filename, doc.extracted_pages or []
            )
        except LLMError as e:
            await emit(task.id, "task_error", {"code": "LLM_ERROR", "message": str(e), "recoverable": True})
            raise HTTPException(status_code=502, detail=str(e))
        doc.extracted_data = facts
        doc.extraction_status = "facts_extracted"
        db.commit()
        total += len(facts)
        results.append(DocFacts(document_id=doc.id, filename=doc.filename, facts=facts, dropped=dropped))

    await emit(task.id, "agent_status", {
        "status": task.status,
        "message": f"Extracted {total} fact(s) from {len(docs)} document(s)",
    })
    return results


@router.get("/{task_id}/facts", response_model=list[DocFacts])
def get_facts(task_id: str, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return [
        DocFacts(document_id=d.id, filename=d.filename, facts=d.extracted_data or {})
        for d in _task_docs(db, task)
    ]