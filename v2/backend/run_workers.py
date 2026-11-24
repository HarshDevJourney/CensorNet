"""
Start N worker processes in ONE terminal and keep them alive (Windows, Linux, macOS).

    python run_workers.py            # N = WORKER_COUNT from .env (default 2)
    python run_workers.py -n 4

Ctrl+C stops all of them. A worker that crashes is restarted after 3 seconds.
"""
import argparse
import signal
import subprocess
import sys
import time

from app.config import BACKEND_DIR, settings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--workers", type=int, default=settings.WORKER_COUNT)
    n = ap.parse_args().workers
    cmd = [sys.executable, "-m", "app.workers.worker"]
    procs: list[subprocess.Popen | None] = [subprocess.Popen(cmd, cwd=str(BACKEND_DIR)) for _ in range(n)]
    print(f"started {n} worker(s); Ctrl+C to stop", flush=True)

    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        while not stopping:
            for i, p in enumerate(procs):
                if p is not None and p.poll() is not None and not stopping:
                    print(f"worker {i} exited ({p.returncode}); restarting in 3s", flush=True)
                    time.sleep(3)
                    if not stopping:
                        procs[i] = subprocess.Popen(cmd, cwd=str(BACKEND_DIR))
            time.sleep(1)
    finally:
        for p in procs:
            if p and p.poll() is None:
                p.terminate()
        for p in procs:
            if p:
                try:
                    p.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    p.kill()


if __name__ == "__main__":
    main()
