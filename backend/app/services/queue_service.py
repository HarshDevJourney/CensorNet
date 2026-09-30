"""
Redis priority queue shared by every worker.

One sorted set:  member = "prepare:<video_id>" | "chunk:<chunk_id>",  score = priority.
LOWER score is popped first.  BZPOPMIN is atomic, so N workers never get the same task.
(The DB claim in chunk_processor is a second safety net.)
Needs Redis >= 5 (BZPOPMIN) and >= 6.2 (ZADD LT).
"""
import json

import redis

from app.config import settings

QUEUE = "vc:queue"
PREPARE_SCORE = -1_000_000.0      # prepare jobs always jump the line
URGENT_BASE = -1_000.0            # player is waiting on this chunk right now

r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def enqueue_prepare(video_id: int) -> None:
    r.zadd(QUEUE, {f"prepare:{video_id}": PREPARE_SCORE})


def enqueue_chunks(items: list[tuple[int, float]]) -> None:
    """items = [(chunk_id, priority), ...]"""
    if items:
        r.zadd(QUEUE, {f"chunk:{cid}": prio for cid, prio in items})


def bump_chunk(chunk_id: int, priority: float) -> None:
    """Move a chunk forward (never backwards)."""
    r.zadd(QUEUE, {f"chunk:{chunk_id}": priority}, lt=True)


def is_queued(chunk_id: int) -> bool:
    return r.zscore(QUEUE, f"chunk:{chunk_id}") is not None


def pop_task(timeout: int = 2) -> tuple[str, int] | None:
    res = r.bzpopmin(QUEUE, timeout=timeout)
    if not res:
        return None
    _key, member, _score = res
    kind, _, ident = member.partition(":")
    return kind, int(ident)


def try_lock(name: str, ttl: int) -> bool:
    return bool(r.set(f"vc:lock:{name}", "1", nx=True, ex=ttl))


def publish(video_id: int, event: dict) -> None:
    r.publish(f"vc:events:{video_id}", json.dumps(event))
