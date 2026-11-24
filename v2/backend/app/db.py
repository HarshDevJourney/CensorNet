"""
Two stores, two jobs:

  PostgreSQL (SQLAlchemy)  permanent records: videos, jobs, chunks and what was censored in each chunk
  Redis                    the fast part: chunk priority queue, worker leases, worker heartbeats
"""
import importlib
from contextlib import contextmanager

import redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# ------------------------------------------------------------------ Redis
r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_redis() -> redis.Redis:
    return r


# ------------------------------------------------------------------ PostgreSQL
class Base(DeclarativeBase):
    pass


engine = create_engine(settings.DATABASE_URL, pool_size=10, max_overflow=10, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope():
    """One short transaction: commit on success, roll back on error."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    """FastAPI dependency (for routes that want a session of their own)."""
    with session_scope() as session:
        yield session


def init_db() -> None:
    """Create the tables if they do not exist. Safe to call from the API and every worker at the same time."""
    importlib.import_module("app.models")      # importing registers the tables on Base
    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(727272)"))      # one process creates, the rest wait
        Base.metadata.create_all(conn)
