"""
Run one or many:   python -m app.workers.worker
Scale horizontally: start N processes (or N containers). They all pull from the same Redis queue.
Each process loads the analyzer once. GPU model => 1 process per GPU.
"""

import logging
import signal
import time

from app.services import queue_service as q
from app.services.analyzer import get_analyzer
from app.services.chunk_processor import process_chunk
from app.services.video_service import prepare_video, reap

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("worker")

running = True


def _stop(*_):
    global running
    running = False
    log.info("shutdown requested, finishing current task...")


def main() -> None:
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    analyzer = get_analyzer()
    analyzer.load()
    log.info("worker ready (%s)", type(analyzer).__name__)

    last_reap = float("-inf")   # run the reaper right at startup
    while running:
        if time.monotonic() - last_reap > 30:
            last_reap = time.monotonic()
            try:
                reap()
            except Exception:  # noqa: BLE001
                log.exception("reaper failed")

        task = q.pop_task(timeout=2)
        if task is None:
            continue
        kind, ident = task
        try:
            if kind == "prepare":
                prepare_video(ident)
            elif kind == "chunk":
                process_chunk(ident, analyzer)
        except Exception:  # noqa: BLE001
            log.exception("task %s:%s crashed", kind, ident)


if __name__ == "__main__":
    main()
