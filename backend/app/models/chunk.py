import enum

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db import Base


class ChunkStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (UniqueConstraint("video_id", "index", name="uq_chunk_video_index"),)

    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, index=True)
    index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    status = Column(SAEnum(ChunkStatus, native_enum=False), default=ChunkStatus.pending, nullable=False, index=True)
    priority = Column(Float, default=0.0, nullable=False, index=True)   # LOWER = processed first
    attempts = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    segment_path = Column(String, nullable=True)      # relative to STORAGE_ROOT
    detections = Column(JSON, nullable=True)          # [{label, score, t_start, t_end, box}]
    censored = Column(Boolean, default=False, nullable=False)
    error = Column(Text, nullable=True)

    video = relationship("Video", back_populates="chunks")