from pydantic import BaseModel


class ChunkInfo(BaseModel):
    index: int
    start_time: float
    end_time: float
    status: str
    priority: float | None = None      # queue score while pending (lower = sooner); None otherwise


class ChunkResponse(BaseModel):
    video_id: int
    index: int
    start_time: float
    end_time: float
    status: str
    priority: float | None = None
    attempts: int = 0
    worker: str | None = None
    process_ms: int = 0
    censored: bool = False
    detections: list[dict] = []
    audio_events: list[dict] = []
    error: str | None = None


class ChunkStatusResponse(BaseModel):
    video_id: int
    index: int
    status: str
