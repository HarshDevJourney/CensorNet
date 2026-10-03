"""PostgreSQL records: claiming, completion bookkeeping, durability. Needs Postgres (censor_test) + Redis."""
import threading

import pytest

from app import models
from app.db import Base, engine, init_db, r

try:
    r.ping()
    init_db()
except Exception as e:  # noqa: BLE001
    pytest.skip(f"Redis/Postgres not running: {e}", allow_module_level=True)


@pytest.fixture(autouse=True)
def clean():
    r.flushdb()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


def _video(total=3):
    vid = models.new_video_id()
    models.create_video(vid, source_type="upload", source_path="x.mp4")
    models.set_video(vid, duration=total * 4.0, chunk_seconds=4.0, fps=25.0, has_audio="1",
                     status=models.JobStatus.processing)
    models.init_chunks(vid, total)
    return vid


def test_video_and_job_round_trip():
    vid = _video(3)
    info = models.video_info(vid)
    assert info["status"] == "processing" and info["total"] == 3 and info["done"] == 0
    assert info["has_audio"] is True and info["fps"] == 25.0 and info["source_type"] == "upload"
    assert models.video_info(99999) is None


def test_exactly_one_of_many_racing_workers_claims_a_chunk():
    vid = _video(1)
    wins = []

    def claim():
        wins.append(models.cas_chunk(vid, 0, models.PENDING, models.PROCESSING))

    threads = [threading.Thread(target=claim) for _ in range(12)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert wins.count(True) == 1 and wins.count(False) == 11


def test_completion_updates_job_and_finishes_it_and_keeps_the_audit_trail():
    vid = _video(2)
    for idx in (0, 1):
        assert models.cas_chunk(vid, idx, models.PENDING, models.PROCESSING)
        models.mark_started(vid, idx, "worker-1")
        assert models.mark_completed(vid, idx, [{"label": "weapon", "t_start": 1.0, "t_end": 2.0}],
                                     [{"start": 0.5, "end": 0.9, "words": ["x"]}], 1234)
    info = models.video_info(vid)
    assert info["done"] == 2 and info["status"] == "completed"
    d = models.chunk_detail(vid, 1)
    assert d["censored"] and d["worker"] == "worker-1" and d["process_ms"] == 1234 and d["attempts"] == 1
    assert d["detections"][0]["label"] == "weapon" and d["audio_events"][0]["words"] == ["x"]


def test_a_chunk_we_no_longer_own_cannot_be_completed():
    vid = _video(1)                                    # still 'pending': nobody claimed it
    assert models.mark_completed(vid, 0, [], [], 10) is False
    assert models.video_info(vid)["done"] == 0


def test_error_handling_retry_then_give_up():
    vid = _video(1)
    models.cas_chunk(vid, 0, models.PENDING, models.PROCESSING)
    models.mark_error(vid, 0, "boom", give_up=False)
    assert models.chunk_status(vid, 0) == "pending"
    models.cas_chunk(vid, 0, models.PENDING, models.PROCESSING)
    models.mark_error(vid, 0, "boom again", give_up=True)
    assert models.chunk_status(vid, 0) == "failed" and models.chunk_detail(vid, 0)["error"] == "boom again"


def test_history_survives_a_redis_wipe_and_active_ids_come_from_postgres():
    vid = _video(2)
    models.cas_chunk(vid, 0, models.PENDING, models.PROCESSING)
    models.mark_completed(vid, 0, [{"label": "blood"}], [], 5)
    r.flushall()                                       # Redis restarted / emptied
    assert models.video_info(vid)["done"] == 1
    assert models.chunk_detail(vid, 0)["detections"] == [{"label": "blood"}]
    assert vid in models.active_video_ids()
