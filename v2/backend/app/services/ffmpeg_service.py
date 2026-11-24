"""ffmpeg / ffprobe helpers. Everything here works on ONE chunk (a time window), never the whole file."""
import json
import logging
import subprocess
from pathlib import Path

import numpy as np

from app.config import settings

log = logging.getLogger("ffmpeg")
_caps: dict | None = None


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


def media_caps() -> dict:
    """Whether this ffmpeg can decode on the 5080 (NVDEC) and encode with NVENC. Cached."""
    global _caps
    if _caps is not None:
        return _caps
    hw_text, enc_text = "", ""
    try:
        hw_text = run([settings.FFMPEG_BIN, "-hide_banner", "-hwaccels"]).decode(errors="ignore").lower()
    except Exception:  # noqa: BLE001
        hw_text = ""
    try:
        enc_text = run([settings.FFMPEG_BIN, "-hide_banner", "-encoders"]).decode(errors="ignore").lower()
    except Exception:  # noqa: BLE001
        enc_text = ""
    cuda = "cuda" in hw_text.split()
    nvenc_built = "h264_nvenc" in enc_text
    mode_hw = settings.HWACCEL.lower()
    mode_enc = settings.VIDEO_ENCODER.lower()
    use_hw = mode_hw == "cuda" or (mode_hw == "auto" and cuda)
    use_nvenc = mode_enc == "nvenc" or (mode_enc == "auto" and nvenc_built)
    if mode_hw == "none":
        use_hw = False
    if mode_enc == "libx264":
        use_nvenc = False
    if mode_hw == "cuda" and not cuda:
        log.warning("HWACCEL=cuda but this ffmpeg has no CUDA decoder; decoding on CPU")
        use_hw = False
    if mode_enc == "nvenc" and not nvenc_built:
        log.warning("VIDEO_ENCODER=nvenc but h264_nvenc is missing; encoding with libx264")
        use_nvenc = False
    _caps = {"hwaccel": use_hw, "nvenc": use_nvenc}
    log.info("ffmpeg hwaccel=%s nvenc=%s", use_hw, use_nvenc)
    return _caps


def decode_flags() -> list[str]:
    """NVDEC flags. Placed before -i so the chunk is decoded on the GPU."""
    if not media_caps()["hwaccel"]:
        return []
    return ["-hwaccel", "cuda", "-hwaccel_device", str(settings.CUDA_DEVICE)]


def disable_hwaccel() -> None:
    media_caps()["hwaccel"] = False
    log.warning("NVDEC failed; later chunks will decode on CPU")


def analysis_size(width: int, height: int) -> tuple[int, int]:
    aw = min(settings.ANALYSIS_WIDTH, width)
    ah = max(2, int(round(height * aw / width)))
    return aw // 2 * 2, ah // 2 * 2


def _input(src: str, start: float, dur: float, *, hw: bool) -> list[str]:
    flags = ["-hwaccel", "cuda", "-hwaccel_device", str(settings.CUDA_DEVICE)] if hw else []
    return [settings.FFMPEG_BIN, "-v", "error", *flags, "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src]


def extract_frames(src: str, start: float, dur: float, width: int, height: int) -> np.ndarray:
    """Decode ONE chunk, downscaled, at ANALYSIS_FPS -> (n, h, w, 3) uint8 RGB. Raw pipe, no temp files."""
    aw, ah = analysis_size(width, height)
    tail = ["-an", "-vf", f"fps={settings.ANALYSIS_FPS},scale={aw}:{ah}",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
    try:
        raw = run(_input(src, start, dur, hw=media_caps()["hwaccel"]) + tail)
    except FFmpegError:
        if not media_caps()["hwaccel"]:
            raise
        disable_hwaccel()
        raw = run(_input(src, start, dur, hw=False) + tail)
    frame_bytes = aw * ah * 3
    n = len(raw) // frame_bytes
    return np.frombuffer(raw, dtype=np.uint8, count=n * frame_bytes).reshape(n, ah, aw, 3)


def extract_audio(src: str, start: float, dur: float) -> np.ndarray:
    """16 kHz mono float32 samples of a window [start, start+dur) - what Whisper wants. No temp files."""
    # Audio decode does not use the GPU. -vn still demuxes; keep it on the CPU decoder.
    raw = run(_input(src, start, dur, hw=False) + ["-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "pipe:1"])
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
