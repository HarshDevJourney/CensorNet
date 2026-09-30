from pydantic import BaseModel, ConfigDict

from app.models import JobStatus


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    status: JobStatus
    error: str | None = None


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: JobStatus
