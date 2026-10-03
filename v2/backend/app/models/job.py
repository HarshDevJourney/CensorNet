"""
Job = one processing run of a video (1 video <-> 1 job, job_id == video_id).   Table: jobs
"""
import datetime as dt
import enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class JobStatus(str, enum.Enum):
    preparing = "preparing"          # probing the file / building the chunk list
    downloading = "downloading"      # YouTube download in progress
    processing = "processing"        # chunks are being censored
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


ACTIVE_STATUSES = (JobStatus.preparing, JobStatus.downloading, JobStatus.processing)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), unique=True)
    status: Mapped[str] = mapped_column(String(16), default=JobStatus.preparing.value, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    total: Mapped[int] = mapped_column(Integer, default=0)            # number of chunks
    completed: Mapped[int] = mapped_column(Integer, default=0)        # chunks finished
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    def __init__(self, **kw):
        kw.setdefault("video_id", kw.get("id"))
        super().__init__(**kw)
