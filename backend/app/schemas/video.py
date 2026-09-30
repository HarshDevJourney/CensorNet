from pydantic import BaseModel, ConfigDict, HttpUrl

from app.models import SourceType


class YouTubeRequest(BaseModel):
    url: HttpUrl


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: SourceType
    source_url: str | None = None
    duration: float = 0.0
    job_id: int | None = None
    playlist_url: str | None = None


class VideoStatusResponse(BaseModel):
    video_id: int
    status: str
    total_chunks: int
    completed_chunks: int
    progress: float


class SeekRequest(BaseModel):
    timestamp: float


class VideoJobResponse(BaseModel):
    id: int
    video_id: int
    status: str
    duration: float
    source_type: SourceType
    chunks: list[dict]
