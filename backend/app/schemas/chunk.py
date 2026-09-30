from pydantic import BaseModel, ConfigDict

from app.models import ChunkStatus


class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    index: int
    start_time: float
    end_time: float
    status: ChunkStatus
    priority: float
    attempts: int = 0
    censored: bool = False
    detections: list[dict] | None = None
    segment_path: str | None = None
    error: str | None = None


class ChunkStatusResponse(BaseModel):
    chunk_id: int
    status: ChunkStatus
