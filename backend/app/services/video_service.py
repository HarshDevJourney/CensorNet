import logging
import math
import shutil
import subprocess
from datetime import datetime, timedelta, timezone

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import session_scope
from app.models import Chunk, ChunkStatus, Job, JobStatus, SourceType, Video
from app.services import ffmpeg_service as ff
from app.services import queue_service as q
from app.services import storage

log = logging.getLogger("video_service")


# ------------------------------------------------------------------ API side (fast, no heavy work)

def create_from_upload(db: Session, file: UploadFile) -> Video:
    video = Video(source_type=SourceType.upload)
    video.job = Job(status=JobStatus.queued)
    db.add(video)
    db.commit()
    db.refresh(video)

    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ".mp4"
    dest = storage.source_path(video.id, ext)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f, length=1024 * 1024)   # streamed, never fully in RAM
    video.source_path = str(dest)
    db.commit()

    q.enqueue_prepare(video.id)
    return video


def create_from_youtube(db: Session, url: str) -> Video:
    video = Video(source_type=SourceType.youtube, source_url=url)
    video.job = Job(status=JobStatus.queued)
    db.add(video)
    db.commit()
    db.refresh(video)
    q.enqueue_prepare(video.id)
    return video


def get_progress(db: Session, video: Video) -> dict:
    total = db.scalar(select(func.count()).select_from(Chunk).where(Chunk.video_id == video.id)) or 0
    done = db.scalar(select(func.count()).select_from(Chunk).where(
        Chunk.video_id == video.id, Chunk.status == ChunkStatus.completed)) or 0
    return {"video_id": video.id, "status": video.job.status.value if video.job else "unknown",
            "total_chunks": total, "completed_chunks": done,
            "progress": round(done / total, 4) if total else 0.0}


def cancel_job(db: Session, job: Job) -> Job:
    if job.status not in (JobStatus.completed, JobStatus.failed):
        job.status = JobStatus.cancelled
        db.commit()   # workers check this in _claim(); queued tasks drain harmlessly
    return job


def retry_chunk(db: Session, chunk: Chunk) -> Chunk:
    chunk.status, chunk.attempts, chunk.error = ChunkStatus.pending, 0, None
    chunk.priority = q.URGENT_BASE
    job = chunk.video.job
    if job.status in (JobStatus.failed, JobStatus.completed):
        job.status, job.error = JobStatus.processing, None
    db.commit()
    q.enqueue_chunks([(chunk.id, chunk.priority)])
    return chunk


# ------------------------------------------------------------------ worker side (heavy)

def _set_job(video_id: int, status: JobStatus, error: str | None = None) -> None:
    with session_scope() as db:
        job = db.get(Video, video_id).job
        if job.status == JobStatus.cancelled:
            return
        job.status, job.error = status, error


def _download_youtube(video: Video) -> str:
    dest = storage.source_path(video.id, ".mp4")
    cmd = [settings.YTDLP_BIN, "-f", "bv*[height<=720]+ba/b[height<=720]",
           "--merge-output-format", "mp4", "--no-playlist", "-o", str(dest), video.source_url]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {p.stderr[-500:]}")
    return str(dest)


def prepare_video(video_id: int) -> None:
    """download (if youtube) -> ffprobe -> split into chunk rows -> push all chunks to Redis."""
    try:
        with session_scope() as db:
            video = db.get(Video, video_id)
            src_type, url, path = video.source_type, video.source_url, video.source_path

        if src_type == SourceType.youtube:
            _set_job(video_id, JobStatus.downloading)
            with session_scope() as db:
                v = db.get(Video, video_id)
                v.source_path = path = _download_youtube(v)

        _set_job(video_id, JobStatus.preparing)
        info = ff.probe(path)
        duration = info["duration"]
        n = max(1, math.ceil(duration / settings.CHUNK_SECONDS))

        with session_scope() as db:
            v = db.get(Video, video_id)
            v.duration, v.width, v.height = duration, info["width"], info["height"]
            db.add_all([
                Chunk(video_id=video_id, index=i,
                      start_time=i * settings.CHUNK_SECONDS,
                      end_time=min(duration, (i + 1) * settings.CHUNK_SECONDS),
                      priority=float(i))            # default order = playback order
                for i in range(n)
            ])
            db.flush()
            ids = [(c.id, c.priority) for c in db.scalars(select(Chunk).where(Chunk.video_id == video_id))]

        _set_job(video_id, JobStatus.processing)
        q.enqueue_chunks(ids)
        q.publish(video_id, {"type": "ready", "total": n, "duration": duration})
    except Exception as e:  # noqa: BLE001
        log.exception("prepare failed for video %s", video_id)
        _set_job(video_id, JobStatus.failed, str(e)[-500:])


# ------------------------------------------------------------------ self-healing

def reap() -> None:
    """Run periodically (one worker at a time, Redis lock). Fixes two crash cases:
       1. worker died mid-chunk      -> chunk stuck in 'processing'  -> back to pending
       2. task lost between pop/claim or Redis flushed -> chunk 'pending' but not queued -> re-enqueue"""
    if not q.try_lock("reaper", ttl=25):
        return
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.STALE_PROCESSING_SECONDS)
    with session_scope() as db:
        for c in db.scalars(select(Chunk).where(Chunk.status == ChunkStatus.processing, Chunk.started_at < cutoff)):
            log.warning("reaping stale chunk %s", c.id)
            c.status = ChunkStatus.pending if c.attempts < settings.MAX_ATTEMPTS else ChunkStatus.failed
            c.error = "worker timeout"
        db.flush()   # autoflush is off: make the next query see the status changes

        pending = db.execute(
            select(Chunk.id, Chunk.priority).join(Video).join(Job, Job.video_id == Video.id)
            .where(Chunk.status == ChunkStatus.pending, Job.status == JobStatus.processing).limit(500)
        ).all()
    q.enqueue_chunks([(cid, p) for cid, p in pending if not q.is_queued(cid)])
