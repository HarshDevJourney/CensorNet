# CensorNet GPU Runbook

This guide explains how to run the **v2** CensorNet application with NVIDIA GPU
acceleration and how to scale workers without wasting GPU memory.

## Code changes required?

### Required: none for basic single-GPU execution

The current v2 backend already contains GPU device selection for the main
inference paths. You do **not** need to modify the frontend or detector source
files to run one NVIDIA GPU. Install the correct packages, set the environment
variables, and restart the workers.

The existing code already:

- Resolves `DEVICE=auto` to CUDA when PyTorch detects a GPU.
- Sends YOLO inference to the resolved device.
- Loads the ViT classifier on CUDA.
- Selects NudeNet's `CUDAExecutionProvider` when CUDA is selected.
- Uses CUDA and `float16` for faster-whisper when configured.
- Loads models once per worker instead of once per chunk.
- Processes video and audio work concurrently within a chunk.
- Uses Redis to distribute chunks between worker processes.

### Required configuration changes

These are configuration changes, not Python code changes:

```dotenv
DEVICE=cuda
WHISPER_DEVICE=cuda
WHISPER_COMPUTE=float16
WORKER_COUNT=1
```

Install a CUDA-enabled PyTorch wheel and `onnxruntime-gpu`. A CPU-only
PyTorch installation or the CPU ONNX Runtime package will prevent the
corresponding model from using the GPU.

### Recommended code improvements for production

These are not required to make the current application work, but they are
recommended if GPU deployment becomes a permanent production target:

1. **Add an explicit GPU index setting.** Add a setting such as
   `CUDA_DEVICE: int = 0` and pass it consistently to YOLO, the Hugging Face
   pipeline, and faster-whisper. Until then, use one worker group per GPU with
   `CUDA_VISIBLE_DEVICES`, as described in the multi-GPU section below.
2. **Validate CUDA at worker startup.** When `DEVICE=cuda`, fail immediately
   with a clear error if `torch.cuda.is_available()` is false or if
   `CUDAExecutionProvider` is unavailable. This avoids accidentally running
   part of the pipeline on CPU.
3. **Expose device and memory in health diagnostics.** Add the resolved device,
   GPU name, and worker GPU assignment to `/health` or a separate diagnostics
   endpoint.
4. **Add inference metrics.** Record per-detector latency, chunks per minute,
   queue wait time, peak VRAM, and CPU render time before changing worker
   counts or model sizes.
5. **Make model download/cache paths explicit.** Configure a shared,
   persistent Hugging Face/model cache so every worker or machine does not
   download duplicate files.
6. **Use a bounded worker policy.** Keep one process per GPU initially and
   increase only after measuring VRAM and throughput. Separate processes do not
   share model memory.

### Optional performance improvements

These require source changes and should be benchmarked before adoption:

- Keep model inference in evaluation/no-gradient mode (`eval()` and
  inference/no-grad contexts) for the ViT and YOLO paths.
- Increase detector batch sizes only when VRAM has headroom.
- Reuse decoded frames between detectors to avoid repeated conversion/copies.
- Move more decode/encode work to hardware-accelerated FFmpeg only after
  confirming that the installed FFmpeg build supports the required NVIDIA
  encoder/decoder.
- Add a dedicated per-GPU queue or scheduler if different GPUs have different
  VRAM capacities.

Do not implement these optimizations blindly. The current worker architecture
already has process-level parallelism, and adding workers or larger batches can
reduce throughput through VRAM pressure, CPU contention, or disk I/O.

The frontend does not perform model inference. GPU work happens in the backend
worker processes:

| Component | GPU path |
| --- | --- |
| NudeNet | ONNX Runtime `CUDAExecutionProvider` |
| Weapon detection | Ultralytics YOLO on CUDA |
| Blood/violence classification | Hugging Face ViT on CUDA |
| Speech censoring | faster-whisper with CUDA and `float16` |
| FFmpeg decode/render | CPU by default; this is separate from model inference |

## 1. Requirements

- Windows 10/11
- NVIDIA GPU with a current NVIDIA driver
- Python 3.10-3.12; Python 3.11 is recommended
- Node.js 18 or newer
- Docker Desktop
- FFmpeg and FFprobe available on `PATH`
- Enough disk space for downloaded model weights and generated HLS segments

The supported application is in [`v2`](./v2). The commands below assume that
the repository is located at `C:\Users\harsh\Desktop\CensorNet`.

## 2. Verify the NVIDIA driver before installing Python packages

Open PowerShell and run:

```powershell
nvidia-smi
```

This must show the GPU and driver information. If `nvidia-smi` is not found or
the GPU is not listed, install/update the NVIDIA driver before continuing.

The CUDA version shown by `nvidia-smi` is the driver capability. It does not
mean that a matching standalone CUDA Toolkit must be installed: the PyTorch
wheel normally supplies the CUDA runtime it needs.

## 3. Create the backend virtual environment

```powershell
cd C:\Users\harsh\Desktop\CensorNet\v2\backend

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If PowerShell blocks activation for the current user, use:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate the environment again.

## 4. Install CUDA-enabled dependencies

Install a CUDA-enabled PyTorch wheel using the command shown by the official
PyTorch selector at <https://pytorch.org/get-started/locally/>.

For example, the command may look like this, but the exact index should be
chosen for the installed PyTorch release:

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
```

Do not install the CPU-only PyTorch wheel afterward. Confirm the selected wheel
with:

```powershell
python -c "import torch; print(torch.__version__); print(torch.version.cuda)"
```

Install the remaining backend dependencies:

```powershell
pip install -r requirements.txt
```

Replace the CPU ONNX Runtime package with the GPU build. Only one of these
packages should be installed:

```powershell
pip uninstall -y onnxruntime
pip install onnxruntime-gpu
```

Confirm that the providers are available:

```powershell
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

The output should contain `CUDAExecutionProvider`.

## 5. Configure GPU execution

Create the environment file:

```powershell
Copy-Item .env.example .env
```

Edit `C:\Users\harsh\Desktop\CensorNet\v2\backend\.env`:

```dotenv
# Required for GPU execution
DEVICE=cuda
WHISPER_DEVICE=cuda
WHISPER_COMPUTE=float16

# Start conservatively. Every worker has its own model copies.
WORKER_COUNT=1

# Default detectors
ANALYZER=nudenet,weapon,blood
ANALYSIS_FPS=3
ANALYSIS_WIDTH=640

# Audio
AUDIO_ENABLED=true
WHISPER_MODEL=base
```

`DEVICE=auto` is also supported and selects CUDA when PyTorch reports that a
CUDA device is available. Use `DEVICE=cuda` during deployment so a broken CUDA
installation fails visibly instead of silently running the visual models on
CPU.

The database and Redis values must match the services started by Docker. Do not
commit `.env`; it can contain local credentials.

## 6. Start PostgreSQL and Redis

From the v2 directory:

```powershell
cd C:\Users\harsh\Desktop\CensorNet\v2
docker compose up -d
docker compose ps
```

Both PostgreSQL and Redis must be running before the worker starts.

## 7. Validate the environment

From the backend directory with `.venv` activated:

```powershell
cd C:\Users\harsh\Desktop\CensorNet\v2\backend
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
python -c "import onnxruntime as ort; print('ONNX providers:', ort.get_available_providers())"
python check_setup.py
```

Expected PyTorch output includes:

```text
CUDA available: True
GPU: NVIDIA ...
```

Expected ONNX output includes:

```text
CUDAExecutionProvider
```

`check_setup.py` also checks Python packages, FFmpeg, PostgreSQL, and Redis.
Fix every item marked `X` before starting workers.

## 8. Start the application

Use three PowerShell windows.

### Window A: API

```powershell
cd C:\Users\harsh\Desktop\CensorNet\v2\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Window B: GPU worker

```powershell
cd C:\Users\harsh\Desktop\CensorNet\v2\backend
.\.venv\Scripts\Activate.ps1
.\run_workers.ps1 -Count 1
```

The first start downloads the YOLO, ViT, NudeNet, and Whisper model files.
Wait for a log line containing `worker ... ready`.

### Window C: frontend

```powershell
cd C:\Users\harsh\Desktop\CensorNet\v2\frontend
npm install
npm run dev
```

Open <http://localhost:3000>.

The API health endpoint is <http://localhost:8000/health>. It should report
`redis: true`, `postgres: true`, and at least one worker.

## 9. Confirm that inference is using the GPU

Run this in a separate PowerShell window while processing a video:

```powershell
nvidia-smi -l 1
```

Look for Python processes using GPU memory and GPU utilization. Worker logs
should include messages similar to:

```text
loading whisper 'base' on cuda (float16)
violence classifier: ... on cuda
```

For a stronger check:

```powershell
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.memory_allocated() if torch.cuda.is_available() else 0)"
```

GPU utilization may briefly fall to zero between chunks. That is normal because
video decoding, audio extraction, database operations, and MPEG-TS rendering
also consume CPU time.

## 10. Worker parallelism and VRAM planning

The queue is shared through Redis. Each worker:

1. Loads one copy of the enabled models.
2. Claims one chunk at a time.
3. Runs video analysis and audio processing for that chunk.
4. Renders and stores the censored HLS segment.
5. Claims the next highest-priority chunk.

This means increasing workers increases throughput only when the GPU has enough
free VRAM and the queue has enough work. It also increases model memory because
**each worker is a separate process with separate model instances**.

Recommended starting points:

| GPU memory | Starting workers | Guidance |
| ---: | ---: | --- |
| 4-6 GB | 1 | Use `WHISPER_MODEL=tiny` or `base`; keep analysis width modest |
| 8-12 GB | 1-2 | Start with one, then test two while watching `nvidia-smi` |
| 16-24 GB | 2-3 | Increase only after checking peak VRAM and throughput |
| 24+ GB | 2-4 | Benchmark; more workers can become CPU/FFmpeg bound |

Start with one worker:

```powershell
.\run_workers.ps1 -Count 1
```

Then benchmark two workers:

```powershell
.\run_workers.ps1 -Count 2
```

Stop if processes hit out-of-memory errors, if Windows starts paging heavily,
or if throughput does not improve. More workers are not automatically faster.

The application already performs audio processing concurrently with the visual
analysis inside a chunk. Do not launch a large number of workers just to obtain
parallelism; first measure GPU memory and completed chunks per minute.

## 11. Using multiple GPUs on Windows

The current code selects CUDA device `0` inside each worker. To distribute work
across multiple physical GPUs, launch separate worker groups with a different
`CUDA_VISIBLE_DEVICES` value. Each process then sees its assigned GPU as device
`0`, while all workers continue using the same Redis queue.

Example for two GPUs, one worker per GPU:

### GPU 0

```powershell
cd C:\Users\harsh\Desktop\CensorNet\v2\backend
.\.venv\Scripts\Activate.ps1
$env:CUDA_VISIBLE_DEVICES="0"
python -m app.workers.worker
```

### GPU 1

```powershell
cd C:\Users\harsh\Desktop\CensorNet\v2\backend
.\.venv\Scripts\Activate.ps1
$env:CUDA_VISIBLE_DEVICES="1"
python -m app.workers.worker
```

Do not set `WORKER_COUNT=2` and then start both workers from a shell where
`CUDA_VISIBLE_DEVICES` is unset: both processes will normally target GPU 0.
Likewise, do not use `CUDA_VISIBLE_DEVICES="0,1"` expecting the application to
split one worker across both GPUs; the current worker implementation does not
do model sharding or automatic multi-GPU scheduling.

For persistent launches, use two separate PowerShell windows or create two
small scripts with the environment variable set before the Python command.
Each GPU should initially run one worker. Add a second worker to a GPU only if
that GPU has enough VRAM and the benchmark improves.

## 12. Throughput tuning

Tune one setting at a time and record processing time and peak VRAM.

### Reduce model input work

```dotenv
ANALYSIS_FPS=2
ANALYSIS_WIDTH=512
NUDENET_RESOLUTION=320
WEAPON_IMGSZ=640
```

Lower values improve throughput but can reduce detection accuracy, especially
for small or fast-moving objects.

### Choose a smaller Whisper model

```dotenv
WHISPER_MODEL=tiny
```

Use `base` as the normal quality/performance starting point. `small` or larger
models use more VRAM and may reduce total chunk throughput.

### Increase parallelism carefully

```dotenv
WORKER_COUNT=2
```

This setting affects the default worker launcher. For multiple GPUs, prefer
explicit per-GPU worker processes as described above instead of relying on a
single unscoped worker count.

### Increase chunk size only after benchmarking

Larger chunks reduce scheduling overhead but delay the first playable segment
and increase peak memory/work per task. The default `CHUNK_SECONDS=4` is a
reasonable streaming balance.

## 13. Troubleshooting

### `torch.cuda.is_available()` is `False`

Check, in order:

1. `nvidia-smi` lists the GPU.
2. The activated Python is the project venv:
   `python -c "import sys; print(sys.executable)"`.
3. PyTorch is a CUDA wheel, not a CPU-only wheel.
4. The NVIDIA driver supports the CUDA runtime used by the PyTorch wheel.
5. Reinstall PyTorch using the official selector command.

### `CUDAExecutionProvider` is missing

```powershell
pip uninstall -y onnxruntime onnxruntime-gpu
pip install onnxruntime-gpu
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

### CUDA out-of-memory errors

Reduce `WORKER_COUNT`, use one worker per GPU, choose a smaller Whisper model,
lower `ANALYSIS_WIDTH` or `WEAPON_IMGSZ`, and close other GPU applications.
Restart workers after an OOM so their model allocations are released.

### GPU usage is low

This can be expected when the workload is limited by FFmpeg, disk I/O,
PostgreSQL, Redis, or a small queue. Check CPU usage, storage throughput, and
the number of pending chunks before adding workers.

### Workers repeatedly restart

Run one worker directly to see the original exception:

```powershell
python -m app.workers.worker
```

Then run:

```powershell
python check_setup.py
```

Common causes are missing FFmpeg, unavailable PostgreSQL/Redis, incompatible
PyTorch/driver versions, missing model downloads, or insufficient VRAM.

### The application still runs on CPU

Check `.env` for `DEVICE=cuda`, verify the worker is using the same activated
venv where CUDA PyTorch was installed, and inspect the worker log. The frontend
cannot switch inference devices; restart the backend workers after changing
`.env`.

## 14. Safe production checklist

- [ ] `nvidia-smi` detects every GPU.
- [ ] PyTorch reports `CUDA available: True`.
- [ ] ONNX Runtime reports `CUDAExecutionProvider`.
- [ ] `.env` uses `DEVICE=cuda`.
- [ ] `WHISPER_DEVICE=cuda` and `WHISPER_COMPUTE=float16`.
- [ ] PostgreSQL and Redis are healthy.
- [ ] `python check_setup.py` finishes without `X` errors.
- [ ] Worker logs contain `worker ... ready`.
- [ ] `nvidia-smi` shows the expected worker processes.
- [ ] Worker count is sized for available VRAM.
- [ ] Multi-GPU workers have distinct `CUDA_VISIBLE_DEVICES` values.
- [ ] Model cache and `STORAGE_ROOT` have sufficient disk space.
- [ ] `.env`, model credentials, and local media are not committed to Git.

## 15. Useful commands

```powershell
# GPU status
nvidia-smi
nvidia-smi -l 1

# Backend health
curl http://localhost:8000/health

# Queue status
curl http://localhost:8000/queue

# Run one worker with detailed logs
python -m app.workers.worker

# Run multiple workers on one visible GPU
.\run_workers.ps1 -Count 2

# Stop Docker services when finished
cd C:\Users\harsh\Desktop\CensorNet\v2
docker compose down
```
