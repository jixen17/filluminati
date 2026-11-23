from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.db.database import SessionLocal
from app.db.models import Task
from app.services.event_service import manager

router = APIRouter()


@router.websocket("/ws/tasks/{task_id}")
async def task_socket(ws: WebSocket, task_id: str):
    with SessionLocal() as db:
        task = db.get(Task, task_id)
        status = task.status if task else None

    if status is None:
        await ws.close(code=4404)
        return

    await manager.connect(task_id, ws)
    try:
        # Snapshot on connect, so a page refresh restores the current state.
        await ws.send_json({
            "type": "agent_status",
            "task_id": task_id,
            "timestamp": None,
            "data": {"status": status, "message": "Connected"},
        })
        while True:
            await ws.receive_text()      # keep the connection open; client messages ignored
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(task_id, ws)