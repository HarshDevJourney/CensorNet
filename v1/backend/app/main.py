import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import chunk_router, job_router, video_router
from app.services import queue_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(title="Real-time video censorship")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(video_router)
app.include_router(job_router)
app.include_router(chunk_router)


@app.get("/health")
def health():
    from app.db import r
    try:
        r.ping()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "redis": False, "error": str(e)}
    workers = queue_service.alive_workers()
    return {"ok": True, "redis": True, "workers": len(workers), "worker_ids": workers,
            "queue_length": queue_service.queue_length(), "inflight": queue_service.inflight_count(),
            "analyzers": settings.analyzers}


@app.get("/queue")
def queue():
    """Debug view: the next tasks the workers will pick, lowest score first."""
    return {"length": queue_service.queue_length(), "inflight": queue_service.inflight_count(),
            "head": queue_service.queue_head(12)}
