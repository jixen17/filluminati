from app.api.routes import profiles
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.database import Base, engine
from app.api.routes import profiles, tasks
from app.api import websocket
from app.db import models  # noqa: F401  (registers tables)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FormPilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profiles.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(websocket.router)      # no /api prefix: /ws/tasks/{task_id}

@app.get("/api/health")
def health():
    return {"status": "ok"}