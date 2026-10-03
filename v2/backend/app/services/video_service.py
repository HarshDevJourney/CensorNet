"""
Video / job level operations (records live in PostgreSQL, the work queue in Redis).

  API side  (fast, no heavy work):  create_from_upload, create_from_youtube, progress, cancel_job, retry_chunk, seek
  worker side (heavy):              prepare_video  = download (YouTube) -> ffprobe -> chunk list in Redis -> queue chunks
"""
import logging
import re
import shutil
import subprocess

from fastapi import UploadFile

from app import models
from app.config import settings
from app.models import JobStatus
from app.services import ffmpeg_service, hls_services, queue_service, storage

log = logging.getLogger("video_service")


# ------------------------------------------------------------------ API side

def create_from_upload(file: UploadFile) -> int:
    vid = models.new_video_id()
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ".mp4"
    if not re.fullmatch(r"\.[a-z0-9]{1,5}", ext):
        ext = ".mp4"
    dest = storage.source_path(vid, ext)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f, length=1024 * 1024)        # streamed, never fully in RAM
    models.create_video(vid, source_type="upload", source_path=str(dest))
    queue_service.enqueue_prepare(vid)
    return vid


def create_from_youtube(url: str) -> int:
    vid = models.new_video_id()
    models.create_video(vid, source_type="youtube", source_url=url)
    queue_service.enqueue_prepare(vid)
    return vid


def get_progress(info: dict) -> dict:
    total, done = info["total"], info["done"]
    return {"video_id": info["id"], "status": info["status"], "total_chunks": total, "completed_chunks": done,
            "progress": round(done / total, 4) if total else 0.0}


def seek(vid: int, timestamp: float, stalled: bool) -> dict:
    """Move the playhead to `timestamp`; its chunk (and the next ones) go to the front of the queue."""
    info = models.video_info(vid)
    if not info["total"]:
        return {"chunk": 0, "reprioritized": 0, "ready": False}
    idx = hls_services.chunk_index_at(info, timestamp)
    n = queue_service.reprioritize(vid, idx, stalled=idx if stalled else None)
    return {"chunk": idx, "reprioritized": n, "ready": storage.segment_abs(vid, idx).exists()}


def cancel_job(vid: int) -> str:
    info = models.video_info(vid)
    if info["status"] not in (JobStatus.completed, JobStatus.failed):
        models.set_video(vid, status=JobStatus.cancelled)
    return models.video_info(vid)["status"]


def retry_chunk(vid: int, idx: int) -> bool:
    info = models.video_info(vid)
    if not models.cas_chunk(vid, idx, models.FAILED, models.PENDING):
        return False
    models.reset_attempts(vid, idx)
    if info["status"] == JobStatus.failed:
        models.set_video(vid, status=JobStatus.processing, error=None)
    queue_service.enqueue_chunks(vid, [idx], info["playhead"], stalled=idx)
    return True


# ------------------------------------------------------------------ worker side (heavy)

def _download_youtube(vid: int, url: str) -> str:
    dest = storage.source_path(vid, ".mp4")
    cmd = [settings.YTDLP_BIN, "-f", "bv*[height<=720]+ba/b[height<=720]", "--merge-output-format", "mp4",
           "--no-playlist", "-o", str(dest), url]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {p.stderr[-500:]}")
    return str(dest)


def prepare_video(vid: int) -> None:
    info = models.video_info(vid)
    if not info or info["status"] == JobStatus.cancelled:
        return
    try:
        path = info["source_path"]
        if info["source_type"] == "youtube":
            models.set_video(vid, status=JobStatus.downloading)
            path = _download_youtube(vid, info["source_url"])
            models.set_video(vid, source_path=path, status=JobStatus.preparing)

        meta = ffmpeg_service.probe(path)
        if meta["duration"] <= 0:
            raise RuntimeError("could not determine video duration")
        total = models.chunk_count(meta["duration"], settings.CHUNK_SECONDS)
        models.set_video(vid, duration=meta["duration"], width=meta["width"], height=meta["height"],
                         fps=meta["fps"], has_audio="1" if meta["has_audio"] else "0",
                         chunk_seconds=settings.CHUNK_SECONDS)
        models.init_chunks(vid, total)
        models.set_video(vid, status=JobStatus.processing)
        queue_service.enqueue_chunks(vid, list(range(total)), playhead=0)
        log.info("video %s ready: %.1fs -> %d chunks", vid, meta["duration"], total)
    except Exception as e:  # noqa: BLE001
        log.exception("prepare failed for video %s", vid)
        models.set_video(vid, status=JobStatus.failed, error=str(e)[-500:])
