from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Chunk, ChunkStatus, Video
from app.schemas import SeekRequest, VideoJobResponse, VideoResponse, VideoStatusResponse, YouTubeRequest
from app.services import hls_services, video_service

router = APIRouter(
    prefix="/videos",
    tags=["Videos"]
)

def _get_video(db: Session, video_id: int) -> Video:
    v = db.get(Video, video_id)
    if not v:
        raise HTTPException(404, "video not found")
    return v

@router.post("/upload", response_model=VideoResponse)
def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    video = video_service.create_from_upload(db, file)
    return {
        "id": video.id,
        "source_type": video.source_type,
        "source_url": video.source_url,
        "duration": video.duration,
        "job_id": video.job.id,
        "playlist_url": f"/videos/{video.id}/index.m3u8",
    }


@router.post("/youtube", response_model=VideoResponse)
def youtube_video(request: YouTubeRequest, db: Session = Depends(get_db)):
    video = video_service.create_from_youtube(db, str(request.url))
    return {
        "id": video.id,
        "source_type": video.source_type,
        "source_url": video.source_url,
        "duration": video.duration,
        "job_id": video.job.id,
        "playlist_url": f"/videos/{video.id}/index.m3u8",
    }


@router.get("/{video_id}/download")
def download_video(video_id: int):
    return {"message": f"Downloading video with ID {video_id}"}


@router.get("/{video_id}/job", response_model=VideoJobResponse)
def job_status(video_id: int, db: Session = Depends(get_db)):
    video = _get_video(db, video_id)
    if not video.job:
        raise HTTPException(404, "job not found")
    return {
        "id": video.job.id,
        "video_id": video.id,
        "status": video.job.status.value,
        "duration": video.duration or 0.0,
        "source_type": video.source_type,
        "chunks": [
            {
                "index": c.index,
                "start_time": c.start_time,
                "end_time": c.end_time,
                "status": c.status.value,
                "priority": c.priority,
            }
            for c in video.chunks
        ],
    }


@router.post("/{video_id}/seek")
async def seek(video_id: int, body: SeekRequest, db: Session = Depends(get_db)):
    video = _get_video(db, video_id)
    chunk = db.scalar(select(Chunk).where(
        Chunk.video_id == video_id,
        Chunk.start_time <= body.timestamp,
        Chunk.end_time > body.timestamp,
    ))
    if chunk is None:
        raise HTTPException(400, "timestamp is outside the video")
    boosted = await run_in_threadpool(hls_services._boost, video.id, chunk.index)
    return {"reprioritized": boosted}


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
def video_status(video_id: int, db: Session = Depends(get_db)):
    video = _get_video(db, video_id)
    return video_service.get_progress(db, video)


@router.get("/{video_id}/index.m3u8")
def stream_video(video_id: int, db: Session = Depends(get_db)):
    _get_video(db, video_id)
    playlist = hls_services.build_playlist(db, video_id)
    if playlist is None:
        raise HTTPException(404, "playlist not ready")
    return PlainTextResponse(playlist, media_type="application/vnd.apple.mpegurl")


@router.get("/{video_id}/segments/{index}.ts")
async def stream_segment(video_id: int, index: int):
    if index < 0:
        raise HTTPException(400, "invalid segment index")
    try:
        path = await hls_services.wait_for_segment(video_id, index)
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc
    if path is None:
        raise HTTPException(504, "segment processing timed out")
    return FileResponse(path, media_type="video/mp2t")