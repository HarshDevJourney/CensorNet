"""Scheduler / seek behaviour against a real Redis (DB 15)."""
import pytest

from app import models
from app.db import r
from app.services import queue_service

try:
    r.ping()
except Exception:  # noqa: BLE001
    pytest.skip("Redis not running", allow_module_level=True)


@pytest.fixture(autouse=True)
def clean():
    r.flushdb()
    yield
    r.flushdb()


def _video(total=20):
    vid = models.new_video_id()
    models.create_video(vid, source_type="upload", source_path="x.mp4")
    models.set_video(vid, duration=total * 4.0, chunk_seconds=4.0, status=models.JobStatus.processing)
    models.init_chunks(vid, total)
    queue_service.enqueue_chunks(vid, list(range(total)), playhead=0)
    return vid


def _drain(n):
    out = []
    for _ in range(n):
        t = queue_service.pop_task()
        if t:
            out.append(t[2])
    return out


def test_default_order_is_playback_order():
    _video(10)
    assert _drain(10) == list(range(10))


def test_seek_pulls_target_and_following_chunks_to_the_front():
    vid = _video(40)
    queue_service.reprioritize(vid, 30, stalled=30)
    first = _drain(5)
    assert first[0] == 30                      # the chunk the player is blocked on
    assert first[1:3] == [31, 32]              # then the next ones (urgent window)
    assert first[3:5] == [33, 34]              # then ahead of the playhead, nearest first


def test_chunks_behind_playhead_go_last():
    vid = _video(10)
    queue_service.reprioritize(vid, 6, stalled=6)
    assert _drain(10) == [6, 7, 8, 9, 5, 4, 3, 2, 1, 0]


def test_reprioritize_never_resurrects_a_chunk_a_worker_already_took():
    vid = _video(5)
    taken = queue_service.pop_task()               # worker takes chunk 0
    queue_service.reprioritize(vid, 3, stalled=3)
    assert queue_service.queue_length() == 4 and all(t[2] != taken[2] for t in
                                                 [queue_service.pop_task() for _ in range(4)])


def test_two_workers_never_get_the_same_chunk():
    _video(30)
    got = _drain(30)
    assert sorted(got) == list(range(30)) and len(set(got)) == 30


def test_claim_is_exclusive():
    vid = _video(3)
    assert models.cas_chunk(vid, 0, models.PENDING, models.PROCESSING) is True
    assert models.cas_chunk(vid, 0, models.PENDING, models.PROCESSING) is False


def test_reaper_requeues_dead_workers_chunk_and_lost_tasks():
    vid = _video(4)
    t = queue_service.pop_task()                                  # worker pops chunk 0 ...
    models.cas_chunk(vid, t[2], models.PENDING, models.PROCESSING)  # ... starts it ...
    r.zadd(queue_service.INFLIGHT, {queue_service.chunk_member(vid, t[2]): 1})   # ... and dies; lease expired
    r.zrem(queue_service.QUEUE, queue_service.chunk_member(vid, 3))                # a task also got lost
    stats = queue_service.reap()
    assert stats["expired"] == 1 and stats["requeued"] >= 2
    assert sorted(_drain(4)) == [0, 1, 2, 3]                  # everything is queued again


def test_prepare_runs_before_chunks():
    _video(3)
    queue_service.enqueue_prepare(99)
    assert queue_service.pop_task()[0] == "prepare"
