import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.routes import chunk_router, job_router, video_router
from app.services import queue_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

@asynccontextmanager
async def lifespan(_app):
    init_db()                      # creates the tables on first start
    yield


app = FastAPI(title="Real-time video censorship", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(video_router)
app.include_router(job_router)
app.include_router(chunk_router)


@app.get("/health")
def health():
    from sqlalchemy import text

    from app.db import engine, r
    try:
        r.ping()
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}
    workers = queue_service.alive_workers()
    return {"ok": True, "redis": True, "postgres": True, "workers": len(workers), "worker_ids": workers,
            "queue_length": queue_service.queue_length(), "inflight": queue_service.inflight_count(),
            "analyzers": settings.analyzers}


@app.get("/queue")
def queue():
    """Debug view: the next tasks the workers will pick, lowest score first."""
    return {"length": queue_service.queue_length(), "inflight": queue_service.inflight_count(),
            "head": queue_service.queue_head(12)}
