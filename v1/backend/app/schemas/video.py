from pydantic import BaseModel, Field, HttpUrl

from app.schemas.chunk import ChunkInfo


class YouTubeRequest(BaseModel):
    url: HttpUrl


class SeekRequest(BaseModel):
    timestamp: float = Field(ge=0)


class VideoResponse(BaseModel):
    id: int
    source_type: str
    source_url: str | None = None
    duration: float = 0.0
    job_id: int
    playlist_url: str


class VideoStatusResponse(BaseModel):
    video_id: int
    status: str
    total_chunks: int
    completed_chunks: int
    progress: float


class VideoJobResponse(BaseModel):
    """Everything the player page polls once a second."""
    id: int
    video_id: int
    status: str
    error: str | None = None
    duration: float
    source_type: str
    playhead: int
    completed: int
    total: int
    workers: int                       # live worker processes
    queue_length: int
    chunks: list[ChunkInfo]
