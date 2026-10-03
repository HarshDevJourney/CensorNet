"""
One worker process. Start as many as you like:   python -m app.workers.worker
(or many at once:  .\run_workers.ps1   /   python run_workers.py -n 4)

Every worker loads its own models once, then loops:  pop the lowest-score task from the shared Redis queue
-> process it -> repeat. Workers share nothing but Redis and the STORAGE_ROOT folder.
"""
import logging
import os
import signal
import socket
import threading
import time

from app.config import settings
from app.db import init_db
from app.services import audio_service, queue_service
from app.services.analyzer import get_analyzer
from app.services.chunk_processor import process_chunk
from app.services.video_service import prepare_video

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("worker")

running = True
WORKER_ID = f"{socket.gethostname()}-{os.getpid()}"


def _stop(*_):
    global running
    running = False
    log.info("shutdown requested, finishing the current task...")


def _heartbeat_loop() -> None:
    while running:
        try:
            queue_service.heartbeat(WORKER_ID)
        except Exception:  # noqa: BLE001
            pass
        time.sleep(5)


def main() -> None:
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    init_db()
    analyzer = get_analyzer()
    analyzer.load()
    if settings.AUDIO_ENABLED:
        audio_service.load_model()
    log.info("worker %s ready (analyzers=%s, audio=%s)", WORKER_ID, settings.analyzers, settings.AUDIO_ENABLED)

    threading.Thread(target=_heartbeat_loop, daemon=True).start()
    last_reap = float("-inf")
    while running:
        if time.monotonic() - last_reap > 5:
            last_reap = time.monotonic()
            try:
                stats = queue_service.reap()
                if stats and (stats["expired"] or stats["requeued"]):
                    log.warning("reaper: %s", stats)
            except Exception:  # noqa: BLE001
                log.exception("reaper failed")

        try:
            task = queue_service.pop_task()
        except Exception:  # noqa: BLE001
            log.exception("cannot reach Redis, retrying")
            time.sleep(2)
            continue
        if task is None:
            time.sleep(0.2)
            continue

        kind, vid, idx = task
        member = f"p:{vid}" if kind == "prepare" else queue_service.chunk_member(vid, idx)
        try:
            if kind == "prepare":
                prepare_video(vid)
            else:
                process_chunk(vid, idx, analyzer, WORKER_ID)
        except Exception:  # noqa: BLE001
            log.exception("task %s crashed", member)
        finally:
            queue_service.done(member)

    queue_service.forget_worker(WORKER_ID)


if __name__ == "__main__":
    main()
