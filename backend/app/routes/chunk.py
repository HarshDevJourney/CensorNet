from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Chunk
from app.schemas import ChunkResponse, ChunkStatusResponse
from app.services import video_service

router = APIRouter(prefix="/chunks", tags=["Chunks"])


def _get(db: Session, chunk_id: int) -> Chunk:
    c = db.get(Chunk, chunk_id)
    if not c:
        raise HTTPException(404, "chunk not found")
    return c


@router.get("/{chunk_id}", response_model=ChunkResponse)
def get_chunk(chunk_id: int, db: Session = Depends(get_db)):
    return _get(db, chunk_id)


@router.get("/{chunk_id}/status", response_model=ChunkStatusResponse)
def chunk_status(chunk_id: int, db: Session = Depends(get_db)):
    c = _get(db, chunk_id)
    return ChunkStatusResponse(chunk_id=c.id, status=c.status)


@router.post("/{chunk_id}/retry", response_model=ChunkResponse)
def retry_chunk(chunk_id: int, db: Session = Depends(get_db)):
    return video_service.retry_chunk(db, _get(db, chunk_id))
