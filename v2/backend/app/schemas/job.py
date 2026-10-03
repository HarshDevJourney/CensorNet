from pydantic import BaseModel


class JobResponse(BaseModel):
    id: int                            # job id == video id
    video_id: int
    status: str
    error: str | None = None
    completed: int = 0
    total: int = 0


class JobStatusResponse(BaseModel):
    id: int
    status: str
