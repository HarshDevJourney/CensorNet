"""
Chunk = one fixed-length slice of a video (the unit of work AND one HLS segment).   Table: chunks

Each row also keeps the audit trail: what was detected, which words were beeped, which worker did it,
how long it took, how many attempts.
"""
import datetime as dt
import enum

from sqlalchemy import (JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func,
                        select, update)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, session_scope
from app.models.job import Job, JobStatus


class ChunkStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


PENDING, PROCESSING, COMPLETED, FAILED = (
    ChunkStatus.pending, ChunkStatus.processing, ChunkStatus.completed, ChunkStatus.failed)


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (UniqueConstraint("video_id", "index", name="uq_chunk_video_index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    index: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default=PENDING.value, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    worker: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    process_ms: Mapped[int] = mapped_column(Integer, default=0)
    censored: Mapped[bool] = mapped_column(Boolean, default=False)
    detections: Mapped[list] = mapped_column(JSON, default=list)       # [{label, category, score, t_start, t_end, box}]
    audio_events: Mapped[list] = mapped_column(JSON, default=list)     # [{start, end, words}]
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def init_chunks(vid: int, total: int) -> None:
    with session_scope() as s:
        s.query(Chunk).filter(Chunk.video_id == vid).delete()
        s.add_all([Chunk(video_id=vid, index=i, status=PENDING.value, detections=[], audio_events=[])
                   for i in range(total)])
        s.execute(update(Job).where(Job.id == vid).values(total=total, completed=0))


def chunk_statuses(vid: int) -> dict[int, str]:
    with session_scope() as s:
        return {i: st for i, st in s.execute(select(Chunk.index, Chunk.status).where(Chunk.video_id == vid))}


def chunk_status(vid: int, idx: int) -> str | None:
    with session_scope() as s:
        return s.scalar(select(Chunk.status).where(Chunk.video_id == vid, Chunk.index == idx))


def cas_chunk(vid: int, idx: int, expected: ChunkStatus, new: ChunkStatus) -> bool:
    """
    Atomic 'change status only if it is still `expected`'. The WHERE clause makes the database the referee:
    when two workers race, exactly one UPDATE matches a row.
    """
    with session_scope() as s:
        res = s.execute(update(Chunk).where(Chunk.video_id == vid, Chunk.index == idx,
                                            Chunk.status == expected.value).values(status=new.value))
        return res.rowcount == 1


def chunk_detail(vid: int, idx: int) -> dict:
    with session_scope() as s:
        c = s.scalar(select(Chunk).where(Chunk.video_id == vid, Chunk.index == idx))
        if c is None:
            return {"id": None, "attempts": 0, "worker": None, "process_ms": 0, "censored": False,
                    "detections": [], "audio_events": [], "error": None}
        return {"id": c.id, "attempts": c.attempts, "worker": c.worker, "process_ms": c.process_ms or 0,
                "censored": bool(c.censored), "detections": c.detections or [],
                "audio_events": c.audio_events or [], "error": c.error}


def mark_started(vid: int, idx: int, worker: str) -> int:
    with session_scope() as s:
        s.execute(update(Chunk).where(Chunk.video_id == vid, Chunk.index == idx)
                  .values(attempts=Chunk.attempts + 1, worker=worker, started_at=_now()))
        return int(s.scalar(select(Chunk.attempts).where(Chunk.video_id == vid, Chunk.index == idx)))


def get_attempts(vid: int, idx: int) -> int:
    with session_scope() as s:
        return int(s.scalar(select(Chunk.attempts).where(Chunk.video_id == vid, Chunk.index == idx)) or 0)


def reset_attempts(vid: int, idx: int) -> None:
    with session_scope() as s:
        s.execute(update(Chunk).where(Chunk.video_id == vid, Chunk.index == idx).values(attempts=0, error=None))


def mark_completed(vid: int, idx: int, detections: list[dict], audio_events: list[dict], process_ms: int) -> bool:
    """processing -> completed. Returns False if we no longer own the chunk (reaped / cancelled)."""
    with session_scope() as s:
        res = s.execute(update(Chunk).where(Chunk.video_id == vid, Chunk.index == idx,
                                            Chunk.status == PROCESSING.value)
                        .values(status=COMPLETED.value, detections=detections, audio_events=audio_events,
                                censored=bool(detections or audio_events), finished_at=_now(),
                                process_ms=process_ms, error=None))
        if res.rowcount != 1:
            return False
        done = s.scalar(select(func.count()).select_from(Chunk)
                        .where(Chunk.video_id == vid, Chunk.status == COMPLETED.value))
        job = s.get(Job, vid)
        job.completed = int(done)
        if job.status == JobStatus.processing.value and job.total and done >= job.total:
            job.status = JobStatus.completed.value
        return True


def mark_error(vid: int, idx: int, message: str, give_up: bool) -> None:
    with session_scope() as s:
        s.execute(update(Chunk).where(Chunk.video_id == vid, Chunk.index == idx)
                  .values(error=message[-600:], status=(FAILED if give_up else PENDING).value))
