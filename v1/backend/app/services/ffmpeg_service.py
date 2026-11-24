"""ffmpeg / ffprobe helpers. Everything here works on ONE chunk (a time window), never the whole file."""
import json
import subprocess
from pathlib import Path

import numpy as np

from app.config import settings


class FFmpegError(RuntimeError):
    pass


def run(cmd: list[str]) -> bytes:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise FFmpegError(f"{cmd[0]} failed ({p.returncode}): {p.stderr.decode(errors='ignore')[-800:]}")
    return p.stdout


def _parse_rate(text: str) -> float:
    try:
        a, b = text.split("/")
        return float(a) / float(b) if float(b) else 0.0
    except Exception:  # noqa: BLE001
        return 0.0


def probe(path: str | Path) -> dict:
    out = run([settings.FFPROBE_BIN, "-v", "error", "-print_format", "json",
               "-show_format", "-show_streams", str(path)])
    info = json.loads(out)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    if not v:
        raise FFmpegError("no video stream found")
    duration = float(info["format"].get("duration") or v.get("duration") or 0)
    fps = _parse_rate(v.get("avg_frame_rate", "")) or _parse_rate(v.get("r_frame_rate", "")) or 25.0
    if not 5.0 <= fps <= 120.0:
        fps = 25.0
    return {
        "duration": duration, "width": int(v["width"]), "height": int(v["height"]),
        "fps": min(round(fps, 3), settings.OUTPUT_FPS_CAP),
        "has_audio": any(s.get("codec_type") == "audio" for s in info["streams"]),
    }


def analysis_size(width: int, height: int) -> tuple[int, int]:
    aw = min(settings.ANALYSIS_WIDTH, width)
    ah = max(2, int(round(height * aw / width)))
    return aw // 2 * 2, ah // 2 * 2


def extract_frames(src: str, start: float, dur: float, width: int, height: int) -> np.ndarray:
    """Decode ONE chunk, downscaled, at ANALYSIS_FPS -> (n, h, w, 3) uint8 RGB. Raw pipe, no temp files."""
    aw, ah = analysis_size(width, height)
    raw = run([
        settings.FFMPEG_BIN, "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src,
        "-an", "-vf", f"fps={settings.ANALYSIS_FPS},scale={aw}:{ah}",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
    ])
    frame_bytes = aw * ah * 3
    n = len(raw) // frame_bytes
    return np.frombuffer(raw, dtype=np.uint8, count=n * frame_bytes).reshape(n, ah, aw, 3)


def extract_audio(src: str, start: float, dur: float) -> np.ndarray:
    """16 kHz mono float32 samples of a window [start, start+dur) - what Whisper wants. No temp files."""
    raw = run([
        settings.FFMPEG_BIN, "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src,
        "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "pipe:1",
    ])
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
