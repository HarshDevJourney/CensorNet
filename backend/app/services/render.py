"""
Pixel-level censoring for one chunk:

  ffmpeg (decode, full-res, raw BGR) -> OpenCV (obscure ONLY the tracked regions) -> ffmpeg (encode + mux audio)

Chunks with no detections never come through here (they use the plain ffmpeg path).
"""
import os
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

from app.config import settings
from app.services.detection import Detection
from app.services.ffmpeg_service import FFmpegError


def _obscure(frame: np.ndarray, box, action: str, shape: str) -> None:
    """In-place. box = normalised (x, y, w, h) or None for whole frame."""
    H, W = frame.shape[:2]
    if box is None:
        x0, y0, x1, y1 = 0, 0, W, H
    else:
        x0, y0 = int(round(box[0] * W)), int(round(box[1] * H))
        x1, y1 = int(round((box[0] + box[2]) * W)), int(round((box[1] + box[3]) * H))
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return

    # work on a slightly larger ROI so the soft edge falls outside the box, not inside it
    f = max(3, min(x1 - x0, y1 - y0) // 10)
    rx0, ry0, rx1, ry1 = max(0, x0 - f), max(0, y0 - f), min(W, x1 + f), min(H, y1 + f)
    roi = frame[ry0:ry1, rx0:rx1]
    ph, pw = roi.shape[:2]

    if action == "blackout":
        fx = np.zeros_like(roi)
    else:
        # strong pixelate first (irreversible), then smooth it so it looks like a blur, not a mosaic
        bs = max(4, min(ph, pw) // 8)
        small = cv2.resize(roi, (max(1, pw // bs), max(1, ph // bs)), interpolation=cv2.INTER_AREA)
        fx = cv2.resize(small, (pw, ph), interpolation=cv2.INTER_LINEAR)
        fx = cv2.GaussianBlur(fx, (0, 0), bs / 2)

    mask = np.zeros((ph, pw), np.float32)
    bx0, by0, bx1, by1 = x0 - rx0, y0 - ry0, x1 - rx0, y1 - ry0
    if shape == "ellipse":
        cv2.ellipse(mask, ((bx0 + bx1) // 2, (by0 + by1) // 2),
                    (int((bx1 - bx0) / 2 * 1.25), int((by1 - by0) / 2 * 1.25)), 0, 0, 360, 1.0, -1)
    else:
        mask[by0:by1, bx0:bx1] = 1.0
    if box is not None:
        mask = cv2.GaussianBlur(mask, (0, 0), f / 2)
    m = mask[..., None]
    roi[:] = (fx * m + roi * (1.0 - m)).astype(np.uint8)


def _read_exact(stream, n: int) -> bytes | None:
    buf = bytearray()
    while len(buf) < n:
        chunk = stream.read(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return bytes(buf)


def render_segment(src: str, start: float, dur: float, out_path: Path,
                   detections: list[Detection], width: int, height: int, fps: float,
                   audio_filter: str | None = None) -> None:
    tmp = out_path.with_suffix(".part")
    frame_bytes = width * height * 3

    reader_cmd = [settings.FFMPEG_BIN, "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src,
                  "-an", "-vf", f"fps={fps:.5f}", "-f", "rawvideo", "-pix_fmt", "bgr24", "pipe:1"]
    writer_cmd = [settings.FFMPEG_BIN, "-v", "error", "-y",
                  "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{width}x{height}", "-r", f"{fps:.5f}", "-i", "pipe:0",
                  "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src,
                  "-map", "0:v:0", "-map", "1:a:0?",
                  "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                  "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
                  "-sc_threshold", "0", "-g", "48",
                  "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2"]
    if audio_filter:
        writer_cmd += ["-af", audio_filter]
    writer_cmd += ["-t", f"{dur:.3f}", "-output_ts_offset", f"{start:.3f}", "-f", "mpegts", str(tmp)]

    # stderr goes to temp files (a full stderr pipe would deadlock ffmpeg)
    with tempfile.TemporaryFile() as rerr, tempfile.TemporaryFile() as werr:
        reader = subprocess.Popen(reader_cmd, stdout=subprocess.PIPE, stderr=rerr)
        writer = subprocess.Popen(writer_cmd, stdin=subprocess.PIPE, stderr=werr)
        try:
            i = 0
            while True:
                raw = _read_exact(reader.stdout, frame_bytes)
                if raw is None:
                    break
                frame = np.frombuffer(raw, np.uint8).reshape(height, width, 3).copy()
                t = i / fps
                for d in detections:
                    if d.t_start <= t <= d.t_end:
                        _obscure(frame, d.box_at(t), d.action, d.shape)
                writer.stdin.write(frame.tobytes())
                i += 1
            writer.stdin.close()
        except BrokenPipeError:
            pass          # writer died; its return code + stderr are reported below
        finally:
            reader.stdout.close()
            rc_r, rc_w = reader.wait(), writer.wait()
        if rc_r != 0 or rc_w != 0:
            rerr.seek(0); werr.seek(0)
            tmp.unlink(missing_ok=True)
            raise FFmpegError(f"render failed (reader={rc_r}, writer={rc_w}): "
                              f"{rerr.read().decode(errors='ignore')[-300:]} | {werr.read().decode(errors='ignore')[-500:]}")
    os.replace(tmp, out_path)
