"""
Chunk = one fixed-length slice of a video (the unit of work AND one HLS segment).

  vc:video:{vid}:chunks   HASH  chunk index -> status        (one HGETALL gives the whole timeline)
  vc:chunk:{vid}:{idx}    HASH  attempts, worker, started_at, finished_at, process_ms, censored,
                                detections (json), audio_events (json), error
"""
import enum
import json
import time

from app.db import r
from app.models.video import k_video, set_video, finish_video_if_done


class ChunkStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


PENDING, PROCESSING, COMPLETED, FAILED = (
    ChunkStatus.pending, ChunkStatus.processing, ChunkStatus.completed, ChunkStatus.failed)


def k_chunks(vid: int) -> str: return f"vc:video:{vid}:chunks"
def k_chunk(vid: int, idx: int) -> str: return f"vc:chunk:{vid}:{idx}"


# Atomic "set field to NEW only if it currently equals EXPECTED". This is what stops two workers
# (or a worker and the reaper) from both owning the same chunk.
_CAS = r.register_script("""
if redis.call('HGET', KEYS[1], ARGV[1]) == ARGV[2] then
  redis.call('HSET', KEYS[1], ARGV[1], ARGV[3])
  return 1
end
return 0
""")


def init_chunks(vid: int, total: int) -> None:
    r.delete(k_chunks(vid))
    r.hset(k_chunks(vid), mapping={str(i): PENDING.value for i in range(total)})
    set_video(vid, total=total, done=0)


def chunk_statuses(vid: int) -> dict[int, str]:
    return {int(i): s for i, s in r.hgetall(k_chunks(vid)).items()}


def chunk_status(vid: int, idx: int) -> str | None:
    return r.hget(k_chunks(vid), str(idx))


def cas_chunk(vid: int, idx: int, expected: ChunkStatus, new: ChunkStatus) -> bool:
    return bool(_CAS(keys=[k_chunks(vid)], args=[str(idx), expected.value, new.value]))


def chunk_detail(vid: int, idx: int) -> dict:
    h = r.hgetall(k_chunk(vid, idx))
    return {
        "attempts": int(h.get("attempts") or 0),
        "worker": h.get("worker") or None,
        "process_ms": int(h.get("process_ms") or 0),
        "censored": h.get("censored") == "1",
        "detections": json.loads(h.get("detections") or "[]"),
        "audio_events": json.loads(h.get("audio_events") or "[]"),
        "error": h.get("error") or None,
    }


def mark_started(vid: int, idx: int, worker: str) -> int:
    pipe = r.pipeline()
    pipe.hincrby(k_chunk(vid, idx), "attempts", 1)
    pipe.hset(k_chunk(vid, idx), mapping={"worker": worker, "started_at": time.time()})
    return int(pipe.execute()[0])


def mark_completed(vid: int, idx: int, detections: list[dict], audio_events: list[dict], process_ms: int) -> bool:
    """processing -> completed. Returns False if we no longer own the chunk (reaped / cancelled)."""
    if not cas_chunk(vid, idx, PROCESSING, COMPLETED):
        return False
    pipe = r.pipeline()
    pipe.hset(k_chunk(vid, idx), mapping={
        "detections": json.dumps(detections), "audio_events": json.dumps(audio_events),
        "censored": "1" if (detections or audio_events) else "0",
        "finished_at": time.time(), "process_ms": process_ms, "error": ""})
    pipe.hincrby(k_video(vid), "done", 1)
    pipe.execute()
    finish_video_if_done(vid)
    return True


def mark_error(vid: int, idx: int, message: str, give_up: bool) -> None:
    r.hset(k_chunk(vid, idx), "error", message[-600:])
    r.hset(k_chunks(vid), str(idx), (FAILED if give_up else PENDING).value)
