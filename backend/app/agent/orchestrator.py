from sqlalchemy.orm import Session
from app.agent.state import transition
from app.db.models import Task, TaskStatus
from app.services.event_service import emit


async def change_status(
    db: Session, task: Task, new_status: TaskStatus, message: str = "", error: str | None = None
) -> Task:
    """Validated transition + agent_status event (+ task_error on failure)."""
    transition(db, task, new_status, error=error)
    await emit(task.id, "agent_status", {"status": task.status, "message": message})
    if new_status == TaskStatus.FAILED:
        await emit(task.id, "task_error", {
            "code": "TASK_FAILED", "message": task.error_summary, "recoverable": False,
        })
    return task