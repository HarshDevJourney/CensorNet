import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Setting(BaseSettings):
    
    DATABASE_URL: str
    REDIS_URL: str
    STORAGE_ROOT: str
    
    FFMPEG_BIN: str = "ffmpeg"
    FFPROBE_BIN: str = "ffprobe"
    YTDLP_BIN: str = "yt-dlp"

    # --- pipeline tuning ---
    CHUNK_SECONDS: float = 4.0        # unit of work AND hls segment length
    ANALYSIS_FPS: float = 2.0         # frames/sec sent to the model
    ANALYSIS_WIDTH: int = 320         # frames are downscaled to this width for the model
    ANALYZER: str = "noop"            # "noop" | "demo" | add your own in analyzer.py
    PREFETCH_CHUNKS: int = 3          # when player asks chunk N, also boost N+1..N+k
    SEGMENT_WAIT_SECONDS: float = 30  # how long /segments/N.ts waits for a chunk
    STALE_PROCESSING_SECONDS: int = 180
    MAX_ATTEMPTS: int = 3
    WORKER_COUNT: int = 4              # number of chunk processors (CPU-bound)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    
settings = Setting()