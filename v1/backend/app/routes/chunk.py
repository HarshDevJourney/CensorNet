from fastapi import APIRouter, HTTPException

from app import models
from app.schemas import ChunkResponse, ChunkStatusResponse
from app.services import queue_service, video_service

router = APIRouter(prefix="/chunks", tags=["Chunks"])    # a chunk is addressed by (video_id, index)


def _get(video_id: int, index: int) -> tuple[dict, str]:
    info = models.video_info(video_id)
    status = models.chunk_status(video_id, index) if info else None
    if status is None:
        raise HTTPException(404, "chunk not found")
    return info, status


@router.get("/{video_id}/{index}", response_model=ChunkResponse)
def get_chunk(video_id: int, index: int):
    info, status = _get(video_id, index)
    start, end = models.chunk_bounds(info, index)
    prio = queue_service.priorities(video_id, [index]).get(index)
    return {"video_id": video_id, "index": index, "start_time": start, "end_time": end, "status": status,
            "priority": prio, **models.chunk_detail(video_id, index)}


@router.get("/{video_id}/{index}/status", response_model=ChunkStatusResponse)
def chunk_status(video_id: int, index: int):
    _, status = _get(video_id, index)
    return {"video_id": video_id, "index": index, "status": status}


@router.post("/{video_id}/{index}/retry")
def retry_chunk(video_id: int, index: int):
    _get(video_id, index)
    if not video_service.retry_chunk(video_id, index):
        raise HTTPException(409, "chunk is not in failed state")
    return {"ok": True}
