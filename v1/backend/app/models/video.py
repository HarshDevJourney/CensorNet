"""
Video = the source file + everything about it. Stored as a Redis hash:

  vc:seq:video       INCR counter for video ids
  vc:videos          SET  of video ids still being processed (the reaper scans these)
  vc:video:{vid}     HASH status (= job status), source_*, duration, width, height, fps, has_audio,
                          chunk_seconds, total, done, playhead, error
"""
import time

from app.config import settings
from app.db import r
from app.models.job import JobStatus

MIN_TAIL_SECONDS = 0.5


def k_video(vid: int) -> str: return f"vc:video:{vid}"


def new_video_id() -> int:
    return int(r.incr("vc:seq:video"))


def create_video(vid: int, **fields) -> None:
    fields = {k: ("" if v is None else v) for k, v in fields.items()}
    fields.update(status=JobStatus.preparing.value, created=time.time(), playhead=0, done=0, total=0)
    r.hset(k_video(vid), mapping=fields)
    r.sadd("vc:videos", vid)


def set_video(vid: int, **fields) -> None:
    r.hset(k_video(vid), mapping={k: ("" if v is None else (v.value if hasattr(v, "value") else v))
                                  for k, v in fields.items()})


def video_info(vid: int) -> dict | None:
    h = r.hgetall(k_video(vid))
    if not h:
        return None
    return {
        "id": vid,
        "status": h.get("status", JobStatus.preparing.value),
        "source_type": h.get("source_type", "upload"),
        "source_url": h.get("source_url") or None,
        "source_path": h.get("source_path") or None,
        "duration": float(h.get("duration") or 0),
        "width": int(h.get("width") or 0),
        "height": int(h.get("height") or 0),
        "fps": float(h.get("fps") or 25),
        "has_audio": h.get("has_audio") == "1",
        "chunk_seconds": float(h.get("chunk_seconds") or settings.CHUNK_SECONDS),
        "total": int(h.get("total") or 0),
        "done": int(h.get("done") or 0),
        "playhead": int(h.get("playhead") or 0),
        "error": h.get("error") or None,
    }


def finish_video_if_done(vid: int) -> None:
    info = video_info(vid)
    if info and info["status"] == JobStatus.processing and info["total"] and info["done"] >= info["total"]:
        set_video(vid, status=JobStatus.completed)
        r.srem("vc:videos", vid)


def chunk_count(duration: float, chunk_seconds: float) -> int:
    """ceil(duration / chunk_seconds), except that a tail shorter than MIN_TAIL_SECONDS is merged into the
    previous chunk (a 40 ms chunk would be a useless one-frame segment)."""
    full, tail = divmod(duration, chunk_seconds)
    return max(1, int(full) + (1 if tail >= MIN_TAIL_SECONDS or full == 0 else 0))


def chunk_bounds(info: dict, idx: int) -> tuple[float, float]:
    cs = info["chunk_seconds"]
    end = info["duration"] if idx >= info["total"] - 1 else (idx + 1) * cs     # last chunk absorbs the tail
    return idx * cs, end
