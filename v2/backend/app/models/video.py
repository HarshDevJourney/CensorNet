"""
Video = the source file and its technical info.   Table: videos
(Processing state lives in Job, per-slice state in Chunk.)
"""
import datetime as dt

from sqlalchemy import Boolean, DateTime, Float, Integer, String, select, update
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.db import Base, session_scope
from app.models.job import Job, JobStatus

MIN_TAIL_SECONDS = 0.5


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(16), default="upload")      # upload | youtube
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    fps: Mapped[float] = mapped_column(Float, default=25.0)
    has_audio: Mapped[bool] = mapped_column(Boolean, default=False)
    chunk_seconds: Mapped[float] = mapped_column(Float, default=settings.CHUNK_SECONDS)
    playhead: Mapped[int] = mapped_column(Integer, default=0)                   # chunk the viewer is at
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc))

    job: Mapped[Job] = relationship(Job, uselist=False, lazy="joined", cascade="all, delete-orphan")


_VIDEO_COLS = {"source_type", "source_url", "source_path", "duration", "width", "height", "fps",
               "has_audio", "chunk_seconds", "playhead"}
_JOB_COLS = {"status": "status", "error": "error", "total": "total", "done": "completed"}


def new_video_id() -> int:
    """Reserve an id (so the upload can be saved under videos/<id>/ before the row exists)."""
    from sqlalchemy import text
    with session_scope() as s:
        return int(s.execute(text("SELECT nextval(pg_get_serial_sequence('videos', 'id'))")).scalar())


def create_video(vid: int, **fields) -> None:
    with session_scope() as s:
        video = Video(id=vid, **{k: v for k, v in fields.items() if k in _VIDEO_COLS})
        video.job = Job(id=vid, status=JobStatus.preparing.value)       # 1 video <-> 1 job, job_id == video_id
        s.add(video)


def set_video(vid: int, **fields) -> None:
    """Update video and/or job columns by name ('status', 'error', 'total', 'done' belong to the job)."""
    fields = {k: (v.value if hasattr(v, "value") else v) for k, v in fields.items()}
    v_vals = {}
    for k, v in fields.items():
        if k in _VIDEO_COLS:
            v_vals[k] = (v == "1") if k == "has_audio" and isinstance(v, str) else v
    j_vals = {_JOB_COLS[k]: v for k, v in fields.items() if k in _JOB_COLS}
    j_vals = {k: (None if v == "" else v) for k, v in j_vals.items()}
    with session_scope() as s:
        if v_vals:
            s.execute(update(Video).where(Video.id == vid).values(**v_vals))
        if j_vals:
            s.execute(update(Job).where(Job.id == vid).values(**j_vals))


def video_info(vid: int) -> dict | None:
    with session_scope() as s:
        v = s.execute(select(Video).where(Video.id == vid)).unique().scalar_one_or_none()
        if v is None:
            return None
        j = v.job
        return {
            "id": v.id, "status": j.status, "error": j.error,
            "source_type": v.source_type, "source_url": v.source_url, "source_path": v.source_path,
            "duration": float(v.duration or 0), "width": int(v.width or 0), "height": int(v.height or 0),
            "fps": float(v.fps or 25), "has_audio": bool(v.has_audio),
            "chunk_seconds": float(v.chunk_seconds or settings.CHUNK_SECONDS),
            "total": int(j.total or 0), "done": int(j.completed or 0), "playhead": int(v.playhead or 0),
        }


def chunk_count(duration: float, chunk_seconds: float) -> int:
    """ceil(duration / chunk_seconds), except that a tail shorter than MIN_TAIL_SECONDS is merged into the
    previous chunk (a 40 ms chunk would be a useless one-frame segment)."""
    full, tail = divmod(duration, chunk_seconds)
    return max(1, int(full) + (1 if tail >= MIN_TAIL_SECONDS or full == 0 else 0))


def chunk_bounds(info: dict, idx: int) -> tuple[float, float]:
    cs = info["chunk_seconds"]
    end = info["duration"] if idx >= info["total"] - 1 else (idx + 1) * cs     # last chunk absorbs the tail
    return idx * cs, end


def active_video_ids() -> list[int]:
    """Videos that still have work to do (the reaper scans these)."""
    with session_scope() as s:
        return list(s.scalars(select(Job.id).where(Job.status.in_(
            [JobStatus.preparing.value, JobStatus.downloading.value, JobStatus.processing.value]))))
