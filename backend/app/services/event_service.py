from datetime import datetime, timezone
from fastapi import WebSocket
from app.db.database import SessionLocal
from app.db.models import AgentEvent

# Event types the contract defines
EVENT_TYPES = {
    "agent_status", "field_detected", "field_mapped",
    "action", "screenshot", "task_completed", "task_error",
}


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[str, set[WebSocket]] = {}

    async def connect(self, task_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.active.setdefault(task_id, set()).add(ws)

    def disconnect(self, task_id: str, ws: WebSocket) -> None:
        conns = self.active.get(task_id)
        if conns:
            conns.discard(ws)
            if not conns:
                self.active.pop(task_id, None)

    async def broadcast(self, task_id: str, message: dict) -> None:
        for ws in list(self.active.get(task_id, ())):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(task_id, ws)


manager = ConnectionManager()


async def emit(task_id: str, event_type: str, data: dict | None = None, persist: bool = True) -> dict:
    """Persist (except screenshots) and broadcast one event in the standard envelope."""
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown event type: {event_type}")
    data = data or {}
    envelope = {
        "type": event_type,
        "task_id": task_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    # Screenshots are large base64 blobs and PII-heavy: broadcast only, never store.
    if persist and event_type != "screenshot":
        with SessionLocal() as db:
            db.add(AgentEvent(task_id=task_id, event_type=event_type, data=data))
            db.commit()
    await manager.broadcast(task_id, envelope)
    return envelope