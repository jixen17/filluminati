from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.orchestrator import change_status
from app.agent.state import InvalidTransition
from app.core.config import settings
from app.db.database import get_db
from app.db.models import AgentEvent, Task, TaskStatus
from app.profiles.profile_service import get_profile_or_404
from app.schemas.task import EventOut, TaskCreate, TaskOut

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _get_task(db: Session, task_id: str) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(body: TaskCreate, db: Session = Depends(get_db)):
    get_profile_or_404(db, body.profile_id)          # profile must exist
    task = Task(profile_id=body.profile_id, goal=body.goal, target_url=body.target_url)
    db.add(task)
    db.commit()
    db.refresh(task)
    from app.services.event_service import emit
    await emit(task.id, "agent_status", {"status": task.status, "message": "Task created"})
    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(profile_id: str, db: Session = Depends(get_db)):
    get_profile_or_404(db, profile_id)
    stmt = select(Task).where(Task.profile_id == profile_id).order_by(Task.created_at.desc())
    return db.scalars(stmt).all()


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)):
    return _get_task(db, task_id)


@router.get("/{task_id}/events", response_model=list[EventOut])
def get_events(task_id: str, db: Session = Depends(get_db)):
    _get_task(db, task_id)
    stmt = select(AgentEvent).where(AgentEvent.task_id == task_id).order_by(AgentEvent.id)
    return db.scalars(stmt).all()


@router.post("/{task_id}/cancel", response_model=TaskOut)
async def cancel_task(task_id: str, db: Session = Depends(get_db)):
    task = _get_task(db, task_id)
    try:
        # Later steps will also stop the browser here.
        await change_status(db, task, TaskStatus.CANCELLED, "Task cancelled by user")
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    return task


# ---------- DEV ONLY: remove in Step 12 ----------
class DebugTransition(BaseModel):
    status: TaskStatus
    message: str = ""


if settings.debug_routes:
    @router.post("/{task_id}/debug/transition", response_model=TaskOut, include_in_schema=True)
    async def debug_transition(task_id: str, body: DebugTransition, db: Session = Depends(get_db)):
        task = _get_task(db, task_id)
        try:
            await change_status(
                db, task, body.status, body.message,
                error=body.message if body.status == TaskStatus.FAILED else None,
            )
        except InvalidTransition as e:
            raise HTTPException(status_code=409, detail=str(e))
        return task