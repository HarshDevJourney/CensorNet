"""Redis connection (replaces the SQL database: Redis holds the queue AND all state)."""
import redis

from app.config import settings

r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_redis() -> redis.Redis:
    """FastAPI dependency / helper."""
    return r
