"""
Playback side. We publish a full VOD playlist as soon as the chunk list exists (durations are known), and
make the SEGMENT endpoint smart:

    segment ready   -> serve the file
    not ready       -> mark it STALL priority in Redis (workers take it next), wait for the file

So the browser can start immediately and seek anywhere; workers always do what the viewer needs first.
"""
import asyncio
import math
import time
from pathlib import Path

from fastapi.concurrency import run_in_threadpool

from app import models
from app.config import settings
from app.services import queue_service, storage


def build_playlist(info: dict) -> str:
    total = info["total"]
    bounds = [models.chunk_bounds(info, i) for i in range(total)]
    longest = max(e - s for s, e in bounds)
    lines = ["#EXTM3U", "#EXT-X-VERSION:3", f"#EXT-X-TARGETDURATION:{math.ceil(longest)}",
             "#EXT-X-MEDIA-SEQUENCE:0", "#EXT-X-PLAYLIST-TYPE:VOD"]
    for i, (s, e) in enumerate(bounds):
        lines += [f"#EXTINF:{e - s:.3f},", f"segments/{i}.ts"]
    lines.append("#EXT-X-ENDLIST")
    return "\n".join(lines) + "\n"


def chunk_index_at(info: dict, t: float) -> int:
    return max(0, min(info["total"] - 1, int(t // info["chunk_seconds"])))


def _stall(vid: int, idx: int) -> None:
    """The player is blocked on `idx`. Make it the very next thing any worker picks up."""
    info = models.video_info(vid)
    if not info:
        return
    playhead = info["playhead"]
    # a normal "next segment" request is near the playhead; a far one means the viewer jumped
    if abs(idx - playhead) > settings.PLAYHEAD_JUMP_CHUNKS or idx < playhead:
        playhead = idx
    queue_service.reprioritize(vid, playhead, stalled=idx)


def _state(vid: int, idx: int) -> tuple[str | None, str | None]:
    info = models.video_info(vid)
    if not info:
        return None, "video not found"
    if info["status"] == models.JobStatus.cancelled:
        return None, "cancelled"
    if info["status"] == models.JobStatus.failed:
        return None, info["error"] or "failed"
    st = models.chunk_status(vid, idx)
    if st == models.FAILED:
        return st, models.chunk_detail(vid, idx)["error"] or "chunk failed"
    return st, None


async def wait_for_segment(vid: int, idx: int) -> Path | None:
    """Path when ready, None on timeout. Raises RuntimeError if the chunk can never be served."""
    path = storage.segment_abs(vid, idx)
    if path.exists():
        return path
    await run_in_threadpool(_stall, vid, idx)
    deadline = time.monotonic() + settings.SEGMENT_WAIT_SECONDS
    tick = 0
    while time.monotonic() < deadline:
        if path.exists():                       # atomic rename => the file is complete
            return path
        tick += 1
        if tick % 5 == 0:
            status, err = await run_in_threadpool(_state, vid, idx)
            if err:
                raise RuntimeError(err)
            if status == models.PENDING and tick % 25 == 0:   # still waiting after ~5 s: re-assert priority
                await run_in_threadpool(_stall, vid, idx)
        await asyncio.sleep(0.2)
    return None
