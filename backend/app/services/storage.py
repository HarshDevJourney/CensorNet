"""All filesystem paths in one place. Everything is relative to STORAGE_ROOT."""
from pathlib import Path

from app.config import settings

ROOT = Path(settings.STORAGE_ROOT).resolve()


def video_dir(video_id: int) -> Path:
    p = ROOT / "videos" / str(video_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def source_path(video_id: int, ext: str = ".mp4") -> Path:
    return video_dir(video_id) / f"source{ext}"


def segment_rel(video_id: int, index: int) -> str:
    return f"videos/{video_id}/hls/seg_{index:05d}.ts"


def segment_abs(video_id: int, index: int) -> Path:
    p = ROOT / segment_rel(video_id, index)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def final_path(video_id: int) -> Path:
    return video_dir(video_id) / "final.mp4"
