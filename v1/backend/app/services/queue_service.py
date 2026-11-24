"""
Chunk queue = ONE Redis sorted set shared by every worker.

    member = "c:<video>:<chunk>"  (one chunk)   |   "p:<video>"  (prepare a video)
    score  = priority, LOWER IS POPPED FIRST

Priority tiers for a chunk, given where the viewer is (the "playhead", a chunk index):

    STALL   -2_000_000 + d   the player asked for this segment and it is not ready  -> do it NOW
    URGENT  -1_000_000 + d   the playhead chunk and the next PREFETCH_CHUNKS-1      -> do it next
    AHEAD              d     everything after the playhead, nearest first
    BEHIND   100_000 + |d|   chunks the viewer already passed (only matters if they scrub back)

d = chunk_index - playhead_index.  Seeking = rewrite the scores of the video's pending chunks
(ZADD XX, one command).  Workers never need to know about seeks; they just pop the lowest score.

Pop is a Lua script: ZPOPMIN + lease in `vc:inflight` in one atomic step, so a worker crash can never
lose a chunk (the reaper re-queues expired leases).
"""
import time

from app import models
from app.config import settings
from app.db import r

QUEUE = "vc:queue"
INFLIGHT = "vc:inflight"

PREPARE_SCORE = -10_000_000.0
STALL_BASE = -2_000_000.0
URGENT_BASE = -1_000_000.0
BEHIND_BASE = 100_000.0

_POP = r.register_script("""
local res = redis.call('ZPOPMIN', KEYS[1], 1)
if #res == 0 then return nil end
redis.call('ZADD', KEYS[2], ARGV[1], res[1])
return res[1]
""")


def chunk_member(vid: int, idx: int) -> str:
    return f"c:{vid}:{idx}"


def priority_for(idx: int, playhead: int, stalled: int | None = None) -> float:
    d = idx - playhead
    if stalled is not None and idx == stalled:
        return STALL_BASE + max(d, 0)
    if 0 <= d < settings.PREFETCH_CHUNKS:
        return URGENT_BASE + d
    if d >= 0:
        return float(d)
    return BEHIND_BASE + (-d)


# ----------------------------------------------------------------------------- producing

def enqueue_prepare(vid: int) -> None:
    r.zadd(QUEUE, {f"p:{vid}": PREPARE_SCORE})


def enqueue_chunks(vid: int, indexes: list[int], playhead: int = 0, stalled: int | None = None) -> None:
    if indexes:
        r.zadd(QUEUE, {chunk_member(vid, i): priority_for(i, playhead, stalled) for i in indexes})


def reprioritize(vid: int, playhead: int, stalled: int | None = None) -> int:
    """
    Viewer moved (seek / playback / stall). Re-score every PENDING chunk of this video.
    XX = only update members that are still queued, so a chunk a worker already took is never re-added.
    """
    r.hset(models.k_video(vid), "playhead", playhead)
    pending = [i for i, s in models.chunk_statuses(vid).items() if s == models.PENDING]
    if not pending:
        return 0
    r.zadd(QUEUE, {chunk_member(vid, i): priority_for(i, playhead, stalled) for i in pending}, xx=True)
    return len(pending)


# ----------------------------------------------------------------------------- consuming

def pop_task() -> tuple[str, int, int | None] | None:
    """-> ('prepare', vid, None) | ('chunk', vid, idx) | None when the queue is empty."""
    member = _POP(keys=[QUEUE, INFLIGHT], args=[time.time() + settings.LEASE_SECONDS])
    if member is None:
        return None
    return parse_member(member)


def parse_member(member: str) -> tuple[str, int, int | None]:
    parts = member.split(":")
    if parts[0] == "p":
        return "prepare", int(parts[1]), None
    return "chunk", int(parts[1]), int(parts[2])


def done(member: str) -> None:
    r.zrem(INFLIGHT, member)


def extend_lease(member: str) -> None:
    r.zadd(INFLIGHT, {member: time.time() + settings.LEASE_SECONDS}, xx=True)


# ----------------------------------------------------------------------------- introspection

def queue_length() -> int:
    return int(r.zcard(QUEUE))


def inflight_count() -> int:
    return int(r.zcard(INFLIGHT))


def queue_head(n: int = 8) -> list[dict]:
    return [{"task": m, "priority": s} for m, s in r.zrange(QUEUE, 0, n - 1, withscores=True)]


def priorities(vid: int, indexes: list[int]) -> dict[int, float]:
    if not indexes:
        return {}
    pipe = r.pipeline()
    for i in indexes:
        pipe.zscore(QUEUE, chunk_member(vid, i))
    return {i: s for i, s in zip(indexes, pipe.execute()) if s is not None}


# ----------------------------------------------------------------------------- self-healing

def reap() -> dict:
    """
    Run by every worker every few seconds; a Redis lock makes only one of them do it. Fixes:
      1. a worker died mid-chunk  -> lease expired in INFLIGHT   -> chunk back to pending + re-queued
      2. a task vanished (Redis flushed, crash between steps) -> chunk 'pending' but nowhere in the queue
    """
    if not r.set("vc:lock:reaper", "1", nx=True, ex=10):
        return {}
    stats = {"expired": 0, "requeued": 0}
    now = time.time()

    for member in r.zrangebyscore(INFLIGHT, "-inf", now):
        r.zrem(INFLIGHT, member)
        kind, vid, idx = parse_member(member)
        if kind == "prepare":
            info = models.video_info(vid)
            if info and info["status"] in (models.JobStatus.preparing, models.JobStatus.downloading):
                enqueue_prepare(vid)
            continue
        if models.chunk_status(vid, idx) == models.PROCESSING:
            attempts = int(r.hget(models.k_chunk(vid, idx), "attempts") or 0)
            models.mark_error(vid, idx, "worker lease expired", give_up=attempts >= settings.MAX_ATTEMPTS)
            stats["expired"] += 1

    for vid in [int(v) for v in r.smembers("vc:videos")]:
        info = models.video_info(vid)
        if not info or info["status"] != models.JobStatus.processing:
            continue
        pending = [i for i, s in models.chunk_statuses(vid).items() if s == models.PENDING]
        if not pending:
            continue
        pipe = r.pipeline()
        for i in pending:
            pipe.zscore(QUEUE, chunk_member(vid, i))
            pipe.zscore(INFLIGHT, chunk_member(vid, i))
        res = pipe.execute()
        missing = [i for n, i in enumerate(pending) if res[2 * n] is None and res[2 * n + 1] is None]
        if missing:
            enqueue_chunks(vid, missing, info["playhead"])
            stats["requeued"] += len(missing)
    return stats


# ----------------------------------------------------------------------------- worker registry

def heartbeat(worker: str) -> None:
    r.hset("vc:workers", worker, time.time())


def alive_workers(max_age: float = 20.0) -> list[str]:
    now = time.time()
    return sorted(w for w, ts in r.hgetall("vc:workers").items() if now - float(ts) < max_age)


def forget_worker(worker: str) -> None:
    r.hdel("vc:workers", worker)
