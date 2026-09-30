import logging
from datetime import datetime, timezone

from sqlalchemy import func, select, update

from app.config import settings
from app.db import session_scope
from app.models import Chunk, ChunkStatus, Job, JobStatus, Video
from app.services import ffmpeg_service as ff
from app.services import queue_service as q
from app.services import storage
from app.services.analyzer import Analyzer

log = logging.getLogger("worker")


def _now():
    return datetime.now(timezone.utc)


def _claim(chunk_id: int) -> dict | None:
    """pending -> processing, atomically. Returns None if someone else got it / job is dead."""
    with session_scope() as db:
        res = db.execute(
            update(Chunk)
            .where(Chunk.id == chunk_id, Chunk.status == ChunkStatus.pending)
            .values(status=ChunkStatus.processing, started_at=_now(), attempts=Chunk.attempts + 1)
        )
        
        if res.rowcount == 0:
            return None
        
        chunk = db.get(Chunk, chunk_id)
        video = db.get(Video, chunk.video_id)
        
        job = video.job
        
        if job.status == JobStatus.cancelled:
            chunk.status = ChunkStatus.failed
            chunk.error = f"job {job.status.value}"
            return None
        
        return dict(
            id=chunk.id, 
            video_id=video.id, 
            index=chunk.index, 
            start=chunk.start_time,
            dur=chunk.end_time - chunk.start_time, 
            src=video.source_path,
            w=video.width,
            h=video.height,
        )


def process_chunk(chunk_id: int, analyzer: Analyzer) -> None:
    c = _claim(chunk_id)
    
    if not c:
        return
    try:
        frames = ff.extract_frames(c["src"], c["start"], c["dur"], c["w"], c["h"])
        detections = analyzer.analyze(frames, settings.ANALYSIS_FPS)
        # clamp to chunk bounds
        for d in detections:
            d.t_start, d.t_end = max(0.0, d.t_start), min(c["dur"], d.t_end)

        out = storage.segment_abs(c["video_id"], c["index"])
        ff.encode_segment(c["src"], c["start"], c["dur"], out, detections, c["w"], c["h"])
        _finish_ok(c, detections)
    except Exception as e:  # noqa: BLE001
        log.exception("chunk %s failed", chunk_id)
        _finish_error(c, str(e))


def _finish_ok(c: dict, detections: list) -> None:
    with session_scope() as db:
        chunk = db.get(Chunk, c["id"])
        chunk.status = ChunkStatus.completed
        chunk.segment_path = storage.segment_rel(c["video_id"], c["index"])
        chunk.detections = [d.to_dict(c["start"]) for d in detections]
        chunk.censored = bool(detections)
        chunk.finished_at = _now()
        chunk.error = None
        db.flush()

        total = db.scalar(select(func.count()).select_from(Chunk).where(Chunk.video_id == c["video_id"]))
        done = db.scalar(select(func.count()).select_from(Chunk).where(
            Chunk.video_id == c["video_id"], Chunk.status == ChunkStatus.completed))
        if done == total:
            job = db.get(Video, c["video_id"]).job
            if job.status == JobStatus.processing:
                job.status = JobStatus.completed
    q.publish(c["video_id"], {"type": "chunk", "index": c["index"], "status": "completed",
                              "censored": bool(detections), "detections": [d.to_dict(c["start"]) for d in detections],
                              "completed": done, "total": total})


def _finish_error(c: dict, message: str) -> None:
    requeue = None
    with session_scope() as db:
        chunk = db.get(Chunk, c["id"])
        chunk.error = message[-1000:]
        if chunk.attempts < settings.MAX_ATTEMPTS:
            chunk.status = ChunkStatus.pending
            requeue = chunk.priority
        else:
            chunk.status = ChunkStatus.failed
            job = db.get(Video, c["video_id"]).job
            job.status = JobStatus.failed
            job.error = f"chunk {chunk.index} failed after {chunk.attempts} attempts: {message[-300:]}"
    if requeue is not None:
        q.enqueue_chunks([(c["id"], requeue)])
    else:
        q.publish(c["video_id"], {"type": "chunk", "index": c["index"], "status": "failed"})
