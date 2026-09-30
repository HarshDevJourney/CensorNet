# Video Censorship Pipeline

Upload a video or paste a YouTube URL. The pipeline:
1. Downloads (if YouTube) and probes the video.
2. Transcribes audio once; flags profanity.
3. Splits into 6s chunks stored in Postgres as a priority queue.
4. Processes only `MAX_CONCURRENT_CHUNKS` at a time.
5. Each chunk: blur nudity + beep profanity + encode to HLS with absolute PTS.
6. Browser plays a single growing HLS playlist — scrubbing reprioritizes
   pending chunks with one UPDATE.

## Run

Terminal 0:  docker compose up -d
Terminal A:  cd backend && source .venv/bin/activate && ./run_api.sh
Terminal B:  cd backend && source .venv/bin/activate && ./run_worker.sh
Terminal C:  cd frontend && npm install && npm run dev

Open http://localhost:3000
