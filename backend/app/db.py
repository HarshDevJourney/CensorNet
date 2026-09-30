from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

_kwargs = {"pool_pre_ping": True}
if settings.DATABASE_URL.startswith("sqlite"):
    _kwargs["connect_args"] = {"check_same_thread": False}
else:
    _kwargs.update(pool_size=10, max_overflow=20)

engine = create_engine(settings.DATABASE_URL, **_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    """FastAPI dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    """For workers: commit on success, rollback on error."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
