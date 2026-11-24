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
 Browser (hls.js) ──GET index.m3u8 / segments/N.ts──►  FastAPI  ──┐
        │  POST /seek, /playhead                                   │  reads/writes
        └──────────────────────────────────────────────────────────▼
                                                          ┌────────────── Redis ──────────────┐
                                                          │ vc:queue   (sorted set, priority) │
                                                          │ vc:inflight(leases, crash safety) │
                                                          │ vc:video:* / vc:chunk:* (state)   │
                                                          └───────▲───────────▲───────────▲───┘
                                                                  │ pop lowest│score       │
                                                          Worker 1      Worker 2   …  Worker N
                                  (each: NudeNet + YOLO + blood + Whisper loaded once, own process)
                                                                  │
                                                  storage/videos/<id>/hls/seg_00000.ts …
```

**Chunk lifecycle:** `pending → processing → completed` (or `failed`). Per chunk a worker
1. decodes the chunk at 3 fps, runs the detectors, tracks boxes over time (`app/services/tracking.py`),
2. **in parallel** transcribes the chunk's audio (±1 s of context so words on a border are heard whole),
3. renders the segment: blur only the boxes, beep only the bad words, encode to MPEG-TS with absolute timestamps,
4. writes `seg_N.ts` atomically (`.part` → rename), so *file exists ⇔ segment complete*.

**Priorities (lower score = processed first)** — `app/services/queue_service.py`

| Tier | Score | Meaning |
|---|---|---|
| STALL | −2 000 000 + d | the player is waiting for this very segment |
| URGENT | −1 000 000 + d | playhead chunk + next `PREFETCH_CHUNKS−1` |
| AHEAD | d | everything after the playhead, nearest first |
| BEHIND | 100 000 + \|d\| | already watched; only matters if the viewer scrubs back |

`d = chunk − playhead`. A seek is **one `ZADD XX`** that re-scores the pending chunks of that video; workers
never need to know about it. A segment request that arrives before the segment exists does the same and then
waits. Workers pop with a Lua script (`ZPOPMIN` + lease) so two workers can never take the same chunk, and a
**reaper** re-queues chunks of workers that died.

**Safety rule:** a chunk that fails 3 times is *never* served un-censored; its segment returns HTTP 502 until retried.

## Project structure

```
real-time-censorship/
├─ docker-compose.yml            Redis (the only service you need)
├─ backend/
│  ├─ .env  /  .env.example      settings (REDIS_URL, WORKER_COUNT, ANALYZER, ...)
│  ├─ requirements.txt
│  ├─ run_workers.ps1            start N worker windows (Windows)
│  ├─ tests/
│  └─ app/
│     ├─ main.py                 FastAPI app, /health, /queue
│     ├─ config.py               all settings
│     ├─ db.py                   Redis connection
│     ├─ data/profanity.txt      bad-word list (English + Hindi/Hinglish)
│     ├─ models/                 Redis-backed entities: video.py, job.py (status), chunk.py (status, claim)
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

Needs: **Python 3.10+**, **Node 18+**, **ffmpeg + ffprobe on PATH**, **Docker** (for Redis; or any Redis ≥ 6.2 / Memurai / WSL).

```powershell
# 1. Redis
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
docker compose up -d                                   # 0. Redis (project root)
cd backend; uvicorn app.main:app --port 8000           # A. API
cd backend; .\run_workers.ps1 -Count 3                 # B. 3 worker windows  (WORKER_COUNT in .env is the default)
cd frontend; npm run dev                               # C. UI
```
Open **http://localhost:3000** → *Upload a file* → the player starts as soon as the first chunk is ready.
One worker only: `python -m app.workers.worker`.

**How many workers?** On CPU each worker uses ~1–2 GB RAM and 2–3 cores. Start with 2–4. With one GPU use
1–2 workers per GPU. Add more workers any time, even while a video is processing; remove them with Ctrl+C.

## Try it / check that it works

* `http://localhost:8000/health` → `workers` must be ≥ 1 and `redis: true`.
* In the UI scrub to the end: the chunk grid shows the playhead (white ring) jump and the blue-ringed "urgent"
  chunks get processed first. `http://localhost:8000/queue` shows the next tasks, lowest score first.
* `http://localhost:8000/chunks/<video_id>/<n>` shows what was censored in that chunk (labels, times, boxes, beeps).
* Kill a worker (Ctrl+C is graceful; `taskkill /F` is not): within `LEASE_SECONDS` another worker takes over.
* Tests (no models needed): `cd backend; pytest -q`  (the scheduler tests need Redis running).

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

## Known limits (be aware)

* **Blood** has no dedicated public detector. It is colour analysis + the violence classifier, so a bloody scene
  the classifier does not consider violent is not blurred, and very graphic non-red gore is not recognised.
  Tune `BLOOD_VIOLENCE_GATE`, or train a YOLO "blood/wound" model and plug it in (`app/services/detectors/`).
* **Weapons**: the default weights know *gun, knife, grenade, explosive*. Check its licence before commercial use.
* **Speech**: a word Whisper mis-hears is not beeped. Heavy background music lowers accuracy.
* Everything shares `STORAGE_ROOT`; running workers on **several machines** needs that folder on shared storage.
* Not included: ingesting a *live* RTMP/camera feed. The chunk/priority/worker design is the same one you would
  use for it (chunks would arrive over time instead of being known up front).
