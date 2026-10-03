"""
Checks that everything the workers need is in place BEFORE you start them.

    python check_setup.py

Prints what is missing and the exact command to fix it. Exit code 0 = ready, 1 = something is missing.
(Nothing heavy is imported, so it takes about a second.)
"""
import importlib.util
import shutil
import sys

# import name -> pip name
BASE = {
    "fastapi": "fastapi", "uvicorn": "uvicorn[standard]", "redis": "redis", "sqlalchemy": "sqlalchemy",
    "psycopg2": "psycopg2-binary", "pydantic_settings": "pydantic-settings", "multipart": "python-multipart",
    "numpy": "numpy", "cv2": "opencv-python-headless",
}
NUDENET = {"nudenet": "nudenet"}
WEAPON = {"ultralytics": "ultralytics", "huggingface_hub": "huggingface-hub>=0.23.0,<1.0"}
CLASSIFIER = {"torch": "torch", "transformers": "transformers==4.41.0", "huggingface_hub": "huggingface-hub>=0.23.0,<1.0",
              "safetensors": "safetensors", "PIL": "pillow"}
AUDIO = {"faster_whisper": "faster-whisper"}


SUPPORTED = ((3, 10), (3, 12))           # tested on 3.12; torch/tokenizers/transformers wheels exist for 3.10-3.12
PY_VERSION = sys.version_info[:2]


def have(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


def main() -> int:
    problems: list[str] = []
    pip: dict[str, str] = {}
    print(f"Python {sys.version.split()[0]}  ({sys.executable})")
    wrong_python = not (SUPPORTED[0] <= PY_VERSION <= SUPPORTED[1])
    if not (sys.prefix != sys.base_prefix):
        print("  ! you are NOT inside a virtual environment (activate .venv first)")

    need = dict(BASE)
    if not have("pydantic_settings"):
        analyzers, audio = ["nudenet", "weapon", "blood"], True          # cannot read .env yet: assume defaults
    else:
        from app.config import settings
        analyzers, audio = settings.analyzers, settings.AUDIO_ENABLED
    if "nudenet" in analyzers:
        need.update(NUDENET)
    if "weapon" in analyzers:
        need.update(WEAPON)
    if "blood" in analyzers or "violence" in analyzers:
        need.update(CLASSIFIER)
    if audio:
        need.update(AUDIO)

    for mod, pkg in need.items():
        if not have(mod):
            pip[mod] = pkg
    if pip:
        problems.append("missing Python packages: " + ", ".join(pip))
        print("  X missing packages:", ", ".join(sorted(pip.values())))
        print("    fix:  pip install -r requirements.txt")
        if wrong_python:
            problems.append("python version")
            print(f"  X Python {PY_VERSION[0]}.{PY_VERSION[1]} is the likely reason: PyTorch/tokenizers/transformers have no"
                  " wheels for it, so pip install fails.\n"
                  "    Use Python 3.11 (3.10-3.12):   py -3.11 -m venv .venv   then   .\\.venv\\Scripts\\Activate.ps1"
                  "   then   pip install -r requirements.txt")
    else:
        print("  OK Python packages")
        if wrong_python:
            print(f"  ! Python {PY_VERSION[0]}.{PY_VERSION[1]} is outside 3.10-3.12 (untested); it works only because the packages happen to be installed")

    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool):
            print(f"  OK {tool} found")
        else:
            problems.append(tool)
            print(f"  X {tool} not found on PATH (install ffmpeg and reopen the terminal)")

    if not pip:                                      # connections need the packages above
        from sqlalchemy import text

        from app.db import engine, r
        try:
            r.ping()
            print("  OK Redis reachable")
        except Exception as e:  # noqa: BLE001
            problems.append("redis")
            print(f"  X Redis not reachable ({type(e).__name__}). Start it:  docker compose up -d")
        try:
            with engine.connect() as c:
                c.execute(text("SELECT 1"))
            print("  OK PostgreSQL reachable")
        except Exception as e:  # noqa: BLE001
            problems.append("postgres")
            msg = str(e).strip().splitlines()[0][:120] if str(e).strip() else type(e).__name__
            print(f"  X PostgreSQL not reachable: {msg}\n    Start it:  docker compose up -d   (check DATABASE_URL in .env)")

    print("\nREADY: you can start the workers." if not problems else f"\nNOT READY: {len(problems)} problem(s) above.")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
