"""All settings in one place. Every value can be overridden from backend/.env or the environment."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    # ---- infrastructure -------------------------------------------------------------------------
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    STORAGE_ROOT: str = str(BACKEND_DIR / "storage")
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    FFMPEG_BIN: str = "ffmpeg"
    FFPROBE_BIN: str = "ffprobe"
    YTDLP_BIN: str = "yt-dlp"
    WORKER_COUNT: int = 2                 # used by run_workers.py
    DEVICE: str = "auto"                  # auto | cpu | cuda   (for torch / whisper / onnxruntime)

    # ---- chunking & scheduling ------------------------------------------------------------------
    CHUNK_SECONDS: float = 4.0            # unit of work AND hls segment length
    PREFETCH_CHUNKS: int = 3              # playhead chunk + next (N-1) are in the "urgent" tier
    SEGMENT_WAIT_SECONDS: float = 90.0    # how long GET /segments/N.ts waits for a chunk
    LEASE_SECONDS: int = 90               # a chunk "processing" longer than this is considered dead
    MAX_ATTEMPTS: int = 3
    PLAYHEAD_JUMP_CHUNKS: int = 6         # a stalled segment request this far from the playhead moves it
    OUTPUT_FPS_CAP: float = 30.0

    # ---- which detectors run (comma separated: nudenet, weapon, blood, violence) ----------------
    ANALYZER: str = "nudenet,weapon,blood"
    ANALYSIS_FPS: float = 3.0             # frames/sec sent to the models
    ANALYSIS_WIDTH: int = 640             # frames are downscaled to this width for the models
    TIME_PAD_SECONDS: float = 0.30        # extend every detection a little in time
    TRACK_MAX_GAP: int = 2                # missed analysis frames allowed inside one track

    # ---- thresholds -----------------------------------------------------------------------------
    THRESH_NUDITY: float = 0.45
    THRESH_NUDITY_GENITALIA: float = 0.35
    THRESH_WEAPON: float = 0.50
    THRESH_BLOOD: float = 0.50
    THRESH_VIOLENCE: float = 0.80
    BLOOD_MIN_HITS: int = 2               # blood must be seen on >=2 analysis frames (or touch a chunk edge)
    VIOLENCE_MIN_HITS: int = 2

    # ---- nudenet --------------------------------------------------------------------------------
    NUDENET_MODEL_PATH: str | None = None
    NUDENET_RESOLUTION: int = 320

    # ---- weapon (YOLO) --------------------------------------------------------------------------
    WEAPON_MODEL_PATH: str | None = None                  # local .pt wins if set
    WEAPON_HF_REPO: str = "Subh775/Threat-Detection-YOLOv8n"
    WEAPON_HF_FILE: str = "weights/best.pt"
    WEAPON_LABELS: str = "gun,pistol,rifle,shotgun,knife,grenade,explosive,sword,weapon"
    WEAPON_IMGSZ: int = 640

    # ---- blood / violence -----------------------------------------------------------------------
    BLOOD_USE_CLASSIFIER: bool = True     # confirm red regions with the ViT violence classifier
    BLOOD_VIOLENCE_GATE: float = 0.35
    BLOOD_MIN_AREA: float = 0.003         # min area of a red blob, as a fraction of the frame
    VIOLENCE_MODELS: str = "hosamEl1/vit-base-violence-detection,jaranohaal/vit-base-violence-detection"

    # ---- audio ----------------------------------------------------------------------------------
    AUDIO_ENABLED: bool = True
    WHISPER_MODEL: str = "base"           # tiny | base | small | medium ...  (small is better for Hindi)
    WHISPER_DEVICE: str = "auto"
    WHISPER_COMPUTE: str = "auto"         # auto -> float16 on cuda, int8 on cpu
    WHISPER_CPU_THREADS: int = 2
    WHISPER_LANGUAGE: str | None = None
    WHISPER_PROMPT: str | None = None
    WHISPER_VAD: bool = True
    AUDIO_CONTEXT_SECONDS: float = 1.0    # extra audio on both sides so words on chunk borders are heard whole
    PROFANITY_FILE: str | None = None     # extra word list, one word per line
    BEEP_PAD_SECONDS: float = 0.08
    BEEP_MERGE_GAP: float = 0.12
    BEEP_FREQUENCY: int = 1000
    BEEP_VOLUME: float = 0.35             # beep peak level, 0..1 (ffmpeg sine is 1/8 scale, handled in render.py)

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def analyzers(self) -> list[str]:
        return [n.strip().lower() for n in self.ANALYZER.split(",") if n.strip()]


settings = Settings()


def resolve_device(value: str | None = None) -> str:
    """'auto' -> 'cuda' if torch can see a GPU, else 'cpu'."""
    value = (value or settings.DEVICE).lower()
    if value != "auto":
        return value
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:  # noqa: BLE001  (torch not installed -> CPU)
        return "cpu"
