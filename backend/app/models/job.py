import enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db import Base


class JobStatus(str, enum.Enum):
    queued = "queued"
    downloading = "downloading"
    preparing = "preparing"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, unique=True)
    status = Column(SAEnum(JobStatus, native_enum=False), default=JobStatus.queued, nullable=False)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    video = relationship("Video", back_populates="job")
