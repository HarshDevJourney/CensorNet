"""
Playback side.  We publish a full VOD playlist as soon as chunks exist (durations are known),
and make the *segment* endpoint smart:
    - segment ready  -> serve the file
    - not ready      -> bump that chunk (+ next few) to the front of the Redis queue, wait for it
So the player can start immediately AND seek anywhere; workers process what the viewer needs first.
"""
import asyncio
import math
import time
from pathlib import Path

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import Chunk, ChunkStatus
from app.services import queue_service as q
from app.services import storage


def build_playlist(db: Session, video_id: int) -> str | None:
    chunks = db.scalars(select(Chunk).where(Chunk.video_id == video_id).order_by(Chunk.index)).all()
    if not chunks:
        return None
    lines = ["#EXTM3U", "#EXT-X-VERSION:3",
             f"#EXT-X-TARGETDURATION:{math.ceil(max(c.end_time - c.start_time for c in chunks))}",
             "#EXT-X-MEDIA-SEQUENCE:0", "#EXT-X-PLAYLIST-TYPE:VOD"]
    for c in chunks:
        lines += [f"#EXTINF:{c.end_time - c.start_time:.3f},", f"segments/{c.index}.ts"]
    lines.append("#EXT-X-ENDLIST")
    return "\n".join(lines) + "\n"


def _boost(video_id: int, index: int) -> int:
    """Called when the player requests a segment that is not ready yet."""
    boosted = 0
    with SessionLocal() as db:
        rows = db.scalars(select(Chunk).where(
            Chunk.video_id == video_id, Chunk.status == ChunkStatus.pending,
            Chunk.index >= index, Chunk.index <= index + settings.PREFETCH_CHUNKS)).all()
        for c in rows:
            prio = q.URGENT_BASE + (c.index - index)      # requested chunk first, then N+1, N+2...
            if prio < c.priority:
                c.priority = prio
            q.bump_chunk(c.id, prio)
            boosted += 1
        db.commit()
    return boosted


def _failed(video_id: int, index: int) -> str | None:
    with SessionLocal() as db:
        c = db.scalar(select(Chunk).where(Chunk.video_id == video_id, Chunk.index == index))
        if c is None:
            return "no such chunk"
        return (c.error or "failed") if c.status == ChunkStatus.failed else None


async def wait_for_segment(video_id: int, index: int) -> Path | None:
    """Returns path when ready, None on timeout. Raises RuntimeError if the chunk failed."""
    path = storage.segment_abs(video_id, index)
    if path.exists():
        return path
    await run_in_threadpool(_boost, video_id, index)
    deadline = time.monotonic() + settings.SEGMENT_WAIT_SECONDS
    tick = 0
    while time.monotonic() < deadline:
        if path.exists():                     # atomic rename => complete file
            return path
        tick += 1
        if tick % 8 == 0:
            err = await run_in_threadpool(_failed, video_id, index)
            if err:
                raise RuntimeError(err)
        await asyncio.sleep(0.25)
    return None
