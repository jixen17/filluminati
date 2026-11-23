from sqlalchemy.orm import Session
from app.db.models import Task, TaskStatus as S


class InvalidTransition(Exception):
    pass


TERMINAL = {S.COMPLETED, S.FAILED, S.CANCELLED}

ALLOWED: dict[S, set[S]] = {
    S.CREATED:           {S.UPLOADING, S.ANALYZING},
    S.UPLOADING:         {S.ANALYZING},
    S.ANALYZING:         {S.INSPECTING},
    S.INSPECTING:        {S.MAPPING},
    S.MAPPING:           {S.NEEDS_INPUT, S.AWAITING_APPROVAL},
    S.NEEDS_INPUT:       {S.AWAITING_APPROVAL},
    S.AWAITING_APPROVAL: {S.NEEDS_INPUT, S.FILLING},
    S.FILLING:           {S.VERIFYING},
    S.VERIFYING:         {S.READY_FOR_REVIEW},
    S.READY_FOR_REVIEW:  {S.COMPLETED},
    S.COMPLETED:         set(),
    S.FAILED:            set(),
    S.CANCELLED:         set(),
}
# Any non-terminal state may fail or be cancelled.
for _s in S:
    if _s not in TERMINAL:
        ALLOWED[_s] = ALLOWED[_s] | {S.FAILED, S.CANCELLED}


def transition(db: Session, task: Task, new_status: S | str, error: str | None = None) -> Task:
    new = S(new_status)
    current = S(task.status)
    if new not in ALLOWED[current]:
        raise InvalidTransition(f"Cannot move task from {current.value} to {new.value}")
    task.status = new.value
    if new == S.FAILED:
        task.error_summary = (error or "Task failed")[:1000]
    db.commit()
    db.refresh(task)
    return task