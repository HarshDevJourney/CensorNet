# Real-time video censorship (stream while it is being censored)

Upload a video (or paste a YouTube link) and **start watching immediately**. The video is cut into 4-second
chunks; workers censor the chunks in the order the viewer needs them, and the browser plays them as an HLS
stream. Jump anywhere in the timeline and that part is processed next.

| Censored | How |
|---|---|
| **Nudity** | NudeNet detects exposed body parts → only that region is blurred |
| **Weapons** | YOLO detector (guns, knives, grenades…) → only the weapon is blurred |
| **Blood** | red-region analysis **confirmed** by the ViT violence classifier from the offline project → only the blood is blurred |
| **Bad words** | faster-Whisper word timestamps → the word is replaced by a **beep** (English + Hindi/Hinglish list) |
| *(optional)* Violent scenes | `ANALYZER=...,violence` blurs the whole frame, like the offline project |

## Architecture

```
 Browser (hls.js) ──GET index.m3u8 / segments/N.ts──►  FastAPI
        │  POST /seek, /playhead                          │
        └─────────────────────────────────────────────────┤
                                                          │ reads / writes
                       ┌──────────────────────────────────┴───────────────────────────┐
                       │                                                              │
          ┌────────────▼─────────────┐                              ┌─────────────────▼──────────────┐
          │ PostgreSQL (permanent)   │                              │ Redis (fast, disposable)       │
          │ videos · jobs · chunks   │                              │ vc:queue    priority queue     │
          │ status, attempts, worker │                              │ vc:inflight worker leases      │
          │ detections, beeps, times │                              │ vc:workers  heartbeats         │
          └────────────▲─────────────┘                              └────────▲───────────▲───────────┘
                       │  claim chunk (atomic UPDATE), save result           │ pop lowest score
                       └──────────────────  Worker 1 … Worker N  ────────────┘
                (each: NudeNet + YOLO + blood + Whisper loaded once, own process)
                                           │
                           storage/videos/<id>/hls/seg_00000.ts …
```

**Who stores what**

| Store | Holds | If it is lost |
|---|---|---|
| **PostgreSQL** | every video, job and chunk: status, attempts, which worker, how long, **what was detected** (labels, times, boxes) and **which words were beeped** | you lose the history |
| **Redis** | only "which chunk next" (the priority queue), worker leases and heartbeats | nothing is lost: the reaper rebuilds the queue from the pending chunks in PostgreSQL |

**Chunk lifecycle:** `pending → processing → completed` (or `failed`). Per chunk a worker
1. decodes the chunk at 3 fps, runs the detectors, tracks boxes over time (`app/services/tracking.py`),
2. **in parallel** transcribes the chunk's audio (±1 s of context so words on a border are heard whole),
3. renders the segment: blur only the boxes, beep only the bad words, encode to MPEG-TS with absolute timestamps,
4. writes `seg_N.ts` atomically (`.part` → rename), so *file exists ⇔ segment complete*,
5. records the result in PostgreSQL (`chunks` row: detections, beeps, worker, time taken).

**Priorities (lower score = processed first)** — `app/services/queue_service.py`

| Tier | Score | Meaning |
|---|---|---|
| STALL | −2 000 000 + d | the player is waiting for this very segment |
| URGENT | −1 000 000 + d | playhead chunk + next `PREFETCH_CHUNKS−1` |
| AHEAD | d | everything after the playhead, nearest first |
| BEHIND | 100 000 + \|d\| | already watched; only matters if the viewer scrubs back |

`d = chunk − playhead`. A seek is **one `ZADD XX`** that re-scores the pending chunks of that video (the list of pending chunks comes from PostgreSQL); workers
never need to know about it. A segment request that arrives before the segment exists does the same and then
waits. Workers pop with a Lua script (`ZPOPMIN` + lease), and then *claim* the chunk with an atomic
`UPDATE chunks SET status='processing' WHERE status='pending'`, so two workers can never process the same chunk.
A **reaper** re-queues chunks of workers that died and rebuilds the queue if Redis was wiped.

**Safety rule:** a chunk that fails 3 times is *never* served un-censored; its segment returns HTTP 502 until retried.

## Project structure

```
real-time-censorship/
├─ docker-compose.yml            PostgreSQL + Redis
├─ backend/
│  ├─ .env  /  .env.example      settings (DATABASE_URL, REDIS_URL, WORKER_COUNT, ANALYZER, ...)
│  ├─ requirements.txt
│  ├─ run_workers.ps1            start N workers (Windows): checks the setup first, one window each or -SingleWindow
│  ├─ run_workers.py             same, all workers in one terminal (any OS)
│  ├─ check_setup.py             "is everything installed and running?" (packages, ffmpeg, Redis, PostgreSQL)
│  ├─ tests/
│  └─ app/
│     ├─ main.py                 FastAPI app, /health, /queue
│     ├─ config.py               all settings
│     ├─ db.py                   PostgreSQL engine/session + Redis connection, init_db() creates the tables
│     ├─ data/profanity.txt      bad-word list (English + Hindi/Hinglish)
│     ├─ models/                 SQLAlchemy tables: video.py (videos), job.py (jobs), chunk.py (chunks)
│     ├─ schemas/                API request/response shapes: video.py, job.py, chunk.py
│     ├─ routes/                 video.py (upload, youtube, seek, playlist, segments)
│     │                          job.py (status, cancel)   chunk.py (inspect, retry)
│     ├─ services/
│     │  ├─ queue_service.py     Redis priority queue, seek re-scoring, reaper, worker heartbeats
│     │  ├─ video_service.py     upload/YouTube ingest, prepare_video (chunk list), cancel, retry
│     │  ├─ chunk_processor.py   process ONE chunk (video + audio in parallel)
│     │  ├─ hls_services.py      playlist + "wait for segment, boost its priority"
│     │  ├─ ffmpeg_service.py    probe, frame/audio extraction for a chunk
│     │  ├─ audio_service.py     Whisper per chunk -> bad-word spans -> beep events
│     │  ├─ profanity.py         word matching
│     │  ├─ analyzer.py          runs the detectors, builds Detections
│     │  ├─ policy.py            what to censor + thresholds
│     │  ├─ tracking.py          per-frame hits -> moving boxes
│     │  ├─ detection.py         shared data types
│     │  ├─ render.py            blur only the boxes, beep only the words, encode the HLS segment
│     │  ├─ storage.py           file paths
│     │  └─ detectors/           nudenet_detector.py, weapon_detector.py, blood_detector.py,
│     │                          violence_classifier.py, violence_detector.py
│     └─ workers/worker.py       one worker process (loads models once, loops on the queue)
└─ frontend/                     Next.js: upload page, player (hls.js), chunk grid
```

## Setup (once)

Needs: **Python 3.10+**, **Node 18+**, **ffmpeg + ffprobe on PATH**, **Docker** (for PostgreSQL and Redis; or install both yourself: PostgreSQL ≥ 13, Redis ≥ 6.2).

```powershell
# 1. PostgreSQL + Redis
docker compose up -d

# 2. Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                  # Linux/macOS:  cp .env.example .env

# 3. Frontend
cd ..\frontend
npm install
```

NVIDIA GPU? Install the CUDA build of PyTorch from pytorch.org, run `pip install onnxruntime-gpu`, and set
`DEVICE=cuda` in `backend/.env`. (Whisper then uses float16 automatically.)

The **first** worker start downloads the models (Whisper, the YOLO weapon weights, the ViT violence model) from
HuggingFace; later starts are instant.

## Run

Four terminals (activate the venv in the backend ones):
```powershell
docker compose up -d                                   # 0. PostgreSQL + Redis (project root)
cd backend; uvicorn app.main:app --port 8000           # A. API
cd backend; .\run_workers.ps1 -Count 3                 # B. 3 workers, one window each  (add -SingleWindow for one terminal)
cd frontend; npm run dev                               # C. UI
```
Open **http://localhost:3000** → *Upload a file* → the player starts as soon as the first chunk is ready.
One worker only: `python -m app.workers.worker`. All workers in the current terminal: `python run_workers.py -n 3`.
Before starting, `python check_setup.py` tells you what is missing.

**How many workers?** On CPU each worker uses ~1–2 GB RAM and 2–3 cores. Start with 2–4. With one GPU use
1–2 workers per GPU. Add more workers any time, even while a video is processing; remove them with Ctrl+C.

## Try it / check that it works

* `http://localhost:8000/health` → `postgres` and `redis` must be `true` and `workers` ≥ 1. The tables (`videos`, `jobs`, `chunks`) are created automatically on first start.
* In the UI scrub to the end: the chunk grid shows the playhead (white ring) jump and the blue-ringed "urgent"
  chunks get processed first. `http://localhost:8000/queue` shows the next tasks, lowest score first.
* `http://localhost:8000/chunks/<video_id>/<n>` shows what was censored in that chunk (labels, times, boxes, beeps).
* Kill a worker (Ctrl+C is graceful; `taskkill /F` is not): within `LEASE_SECONDS` another worker takes over.
* See what was censored, straight from the database:
  ```sql
  -- docker exec -it censor_postgres psql -U censor -d censor
  SELECT index, status, worker, process_ms, jsonb_array_length(detections::jsonb) AS visual, jsonb_array_length(audio_events::jsonb) AS beeps
  FROM chunks WHERE video_id = 1 ORDER BY index;
  ```
* Wipe Redis while a video is processing (`docker exec censor_redis redis-cli flushall`): within seconds a reaper rebuilds the queue from PostgreSQL and the video still finishes.
* Tests: `cd backend; pytest -q`. They need PostgreSQL and Redis running and use a separate database `censor_test`
  (create it once: `docker exec censor_postgres createdb -U censor censor_test`); Redis DB 15 is used and emptied.

## Tuning (`backend/.env`)

| Setting | Default | Notes |
|---|---|---|
| `ANALYZER` | `nudenet,weapon,blood` | add `violence` for whole-frame blur; `demo` blurs a box in every chunk to test the pipeline; `noop` = audio only |
| `CHUNK_SECONDS` | 4 | smaller = faster first frame & finer seeks, more overhead |
| `ANALYSIS_FPS` | 3 | detections per second of video. Higher = fewer misses, slower |
| `THRESH_NUDITY / WEAPON / BLOOD / VIOLENCE` | .45 / .5 / .5 / .8 | raise to reduce false blurs |
| `BLOOD_VIOLENCE_GATE` | .35 | min classifier score needed to accept a red region as blood |
| `WHISPER_MODEL` | base | `small` is noticeably better for Hindi/Hinglish; set `WHISPER_LANGUAGE=hi` if the video is Hindi |
| `PROFANITY_FILE` | – | your own extra words, one per line (see `app/data/profanity.txt`) |
| `WEAPON_MODEL_PATH` | – | your own YOLO `.pt`; any class named in `WEAPON_LABELS` counts as a weapon |
| `PREFETCH_CHUNKS` | 3 | how many chunks after the playhead are treated as urgent |

## Troubleshooting

| What you see | Cause and fix |
|---|---|
| Worker window shows `ModuleNotFoundError: No module named 'pydantic_settings'` (or any other module) | The venv does not have this project's packages (e.g. it is an old venv). In `backend` with the venv active: `pip install -r requirements.txt`, then `python check_setup.py` until it says READY. |
| UI says *No worker is running* / *Preparing video…* forever | The workers crashed or never started. Look at the worker windows (or run `python -m app.workers.worker` once to see the error). `http://localhost:8000/health` shows `workers: 0`. |
| `.\run_workers.ps1` says *Workers NOT started* | `check_setup.py` found a problem and printed it above the message with X. Fix it and run again. |
| `PostgreSQL not reachable` / `Redis not reachable` | `docker compose up -d` from the project root. If Docker complains that a container name is already in use: `docker rm censor_redis censor_postgres` and run it again. |
| 3 windows open | That is by design (one worker per window). For one terminal use `.\run_workers.ps1 -SingleWindow` or `python run_workers.py -n 3`. |
| First start is very slow | The workers are downloading the models once (Whisper, weapon YOLO, violence ViT). Wait for `worker ... ready`. |

## Known limits (be aware)

* **Blood** has no dedicated public detector. It is colour analysis + the violence classifier, so a bloody scene
  the classifier does not consider violent is not blurred, and very graphic non-red gore is not recognised.
  Tune `BLOOD_VIOLENCE_GATE`, or train a YOLO "blood/wound" model and plug it in (`app/services/detectors/`).
* **Weapons**: the default weights know *gun, knife, grenade, explosive*. Check its licence before commercial use.
* **Speech**: a word Whisper mis-hears is not beeped. Heavy background music lowers accuracy.
* Tables are created with `create_all` on startup (no migrations). If you change a model later, add Alembic or drop the table.
* Everything shares `STORAGE_ROOT`; running workers on **several machines** needs that folder on shared storage.
* Not included: ingesting a *live* RTMP/camera feed. The chunk/priority/worker design is the same one you would
  use for it (chunks would arrive over time instead of being known up front).
