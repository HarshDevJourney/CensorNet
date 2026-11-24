"""All filesystem paths in one place. Everything lives under STORAGE_ROOT (shared by API + all workers)."""
from pathlib import Path

from app.config import settings

ROOT = Path(settings.STORAGE_ROOT).resolve()


def video_dir(vid: int) -> Path:
    p = ROOT / "videos" / str(vid)
    p.mkdir(parents=True, exist_ok=True)
    return p


def source_path(vid: int, ext: str = ".mp4") -> Path:
    return video_dir(vid) / f"source{ext}"


def segment_abs(vid: int, idx: int) -> Path:
    p = video_dir(vid) / "hls" / f"seg_{idx:05d}.ts"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
