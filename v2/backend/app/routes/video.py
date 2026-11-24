from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, PlainTextResponse

from app import models
from app.models import JobStatus
from app.schemas import (ChunkInfo, SeekRequest, VideoJobResponse, VideoResponse, VideoStatusResponse,
                         YouTubeRequest)
from app.services import hls_services, queue_service, video_service

router = APIRouter(prefix="/videos", tags=["Videos"])


def _get_video(video_id: int) -> dict:
    info = models.video_info(video_id)
    if not info:
        raise HTTPException(404, "video not found")
    return info


def _created(vid: int) -> dict:
    info = _get_video(vid)
    return {"id": vid, "source_type": info["source_type"], "source_url": info["source_url"],
            "duration": info["duration"], "job_id": vid, "playlist_url": f"/videos/{vid}/index.m3u8"}


# ----------------------------------------------------------------------------- ingest

@router.post("/upload", response_model=VideoResponse)
def upload_video(file: UploadFile = File(...)):
    return _created(video_service.create_from_upload(file))


@router.post("/youtube", response_model=VideoResponse)
def youtube_video(request: YouTubeRequest):
    return _created(video_service.create_from_youtube(str(request.url)))


# ----------------------------------------------------------------------------- status

@router.get("/{video_id}/job", response_model=VideoJobResponse)
def video_job(video_id: int):
    info = _get_video(video_id)
    statuses = models.chunk_statuses(video_id)
    pending = [i for i, s in statuses.items() if s == models.PENDING]
    prios = queue_service.priorities(video_id, pending)
    chunks = []
    for i in sorted(statuses):
        s, e = models.chunk_bounds(info, i)
        chunks.append(ChunkInfo(index=i, start_time=s, end_time=e, status=statuses[i], priority=prios.get(i)))
    return VideoJobResponse(
        id=video_id, video_id=video_id, status=info["status"], error=info["error"], duration=info["duration"],
        source_type=info["source_type"], playhead=info["playhead"], completed=info["done"], total=info["total"],
        workers=len(queue_service.alive_workers()), queue_length=queue_service.queue_length(), chunks=chunks)


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
def video_status(video_id: int):
    return video_service.get_progress(_get_video(video_id))


# ----------------------------------------------------------------------------- seek / priorities

@router.post("/{video_id}/seek")
def seek(video_id: int, body: SeekRequest):
    """User jumped to `timestamp`: that chunk (and the next ones) go to the front of the queue."""
    _get_video(video_id)
    return video_service.seek(video_id, body.timestamp, stalled=True)


@router.post("/{video_id}/playhead")
def playhead(video_id: int, body: SeekRequest):
    """Periodic 'I am watching here' ping while playing: keeps 'what comes next' in order, no stall boost."""
    _get_video(video_id)
    return video_service.seek(video_id, body.timestamp, stalled=False)


# ----------------------------------------------------------------------------- HLS

@router.get("/{video_id}/index.m3u8")
def stream_video(video_id: int):
    info = _get_video(video_id)
    if info["status"] == JobStatus.failed:
        raise HTTPException(500, info["error"] or "processing failed")
    if not info["total"]:
        raise HTTPException(404, "playlist not ready yet")
    return PlainTextResponse(hls_services.build_playlist(info), media_type="application/vnd.apple.mpegurl",
                             headers={"Cache-Control": "no-store"})


@router.get("/{video_id}/segments/{index}.ts")
async def stream_segment(video_id: int, index: int):
    info = await run_in_threadpool(_get_video, video_id)
    if index < 0 or index >= max(info["total"], 1):
        raise HTTPException(404, "no such segment")
    try:
        path = await hls_services.wait_for_segment(video_id, index)
    except RuntimeError as exc:
        # never fall back to the raw source: an un-censored segment must not be served
        raise HTTPException(502, str(exc)) from exc
    if path is None:
        raise HTTPException(504, "segment is still being processed, try again")
    return FileResponse(path, media_type="video/mp2t", headers={"Cache-Control": "public, max-age=300"})
