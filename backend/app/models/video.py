import enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db import Base


class SourceType(str, enum.Enum):
    upload = "upload"
    youtube = "youtube"


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True)
    source_type = Column(SAEnum(SourceType, native_enum=False), default=SourceType.upload, nullable=False)
    source_url = Column(String, nullable=True)
    source_path = Column(String, nullable=True)
    duration = Column(Float, default=0.0)
    width = Column(Integer, nullable=True)     # filled by prepare step (ffprobe)
    height = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chunks = relationship("Chunk", back_populates="video", cascade="all, delete", order_by="Chunk.index")
    job = relationship("Job", back_populates="video", uselist=False, cascade="all, delete")
