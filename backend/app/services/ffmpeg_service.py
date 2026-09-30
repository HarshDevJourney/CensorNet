import json
import os
import subprocess
from pathlib import Path

import numpy as np

from app.config import settings


class FFmpegError(RuntimeError):
    pass


def _run(cmd: list[str], capture_stdout: bool = False) -> bytes:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise FFmpegError(f"{cmd[0]} failed ({p.returncode}): {p.stderr.decode(errors='ignore')[-800:]}")
    return p.stdout


def probe(path: str | Path) -> dict:
    out = _run([settings.FFPROBE_BIN, "-v", "error", "-print_format", "json",
                "-show_format", "-show_streams", str(path)])
    info = json.loads(out)
    vstream = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    if not vstream:
        raise FFmpegError("no video stream found")
    duration = float(info["format"].get("duration") or vstream.get("duration") or 0)
    return {"duration": duration, "width": int(vstream["width"]), "height": int(vstream["height"])}


def analysis_size(width: int, height: int) -> tuple[int, int]:
    aw = settings.ANALYSIS_WIDTH
    ah = max(2, int(round(height * aw / width)))
    return aw, ah


def extract_frames(src: str, start: float, dur: float, width: int, height: int) -> np.ndarray:
    """Decode ONE chunk into a (n, h, w, 3) uint8 array at ANALYSIS_FPS. No temp files, raw pipe."""
    aw, ah = analysis_size(width, height)
    raw = _run([
        settings.FFMPEG_BIN, "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src,
        "-an", "-vf", f"fps={settings.ANALYSIS_FPS},scale={aw}:{ah}",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
    ])
    frame_bytes = aw * ah * 3
    n = len(raw) // frame_bytes
    return np.frombuffer(raw, dtype=np.uint8, count=n * frame_bytes).reshape(n, ah, aw, 3)


def build_blur_filter(detections: list, width: int, height: int) -> str | None:
    """
    detections: objects with t_start/t_end (seconds, RELATIVE to chunk start) and
    box=(x,y,w,h) normalised 0..1 or None (= blur whole frame).
    Returns a -filter_complex graph ending in [vout], or None if nothing to censor.
    """
    if not detections:
        return None
    parts, cur = [], "0:v"
    for i, d in enumerate(detections):
        en = f"between(t\\,{d.t_start:.3f}\\,{d.t_end:.3f})"
        nxt = f"v{i}"
        if d.box is None:
            parts.append(f"[{cur}]boxblur=luma_radius=min(w\\,h)/12:luma_power=3:enable='{en}'[{nxt}]")
        else:
            x, y, w, h = d.box
            px = max(0, min(width - 16, int(x * width))) // 2 * 2
            py = max(0, min(height - 16, int(y * height))) // 2 * 2
            pw = max(16, min(width - px, int(w * width))) // 2 * 2
            ph = max(16, min(height - py, int(h * height))) // 2 * 2
            rad = max(2, min(pw, ph) // 6)
            parts.append(
                f"[{cur}]split[a{i}][b{i}];"
                f"[b{i}]crop={pw}:{ph}:{px}:{py},boxblur={rad}:3[c{i}];"
                f"[a{i}][c{i}]overlay={px}:{py}:enable='{en}'[{nxt}]"
            )
        cur = nxt
    parts.append(f"[{cur}]null[vout]")
    return ";".join(parts)


def encode_segment(src: str, start: float, dur: float, out_path: Path,
                   detections: list, width: int, height: int) -> None:
    """
    Encode one chunk to an independent MPEG-TS HLS segment with censoring applied.
    -output_ts_offset keeps timestamps continuous across separately-encoded segments,
    so hls.js can play them back to back (and seek anywhere).
    Written to *.part then atomically renamed => file exists  <=>  segment is complete.
    """
    graph = build_blur_filter(detections, width, height)
    tmp = out_path.with_suffix(".part")
    cmd = [settings.FFMPEG_BIN, "-v", "error", "-y",
           "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src]
    if graph:
        cmd += ["-filter_complex", graph, "-map", "[vout]"]
    else:
        cmd += ["-map", "0:v:0"]
    cmd += ["-map", "0:a:0?",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-sc_threshold", "0", "-g", "48",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
            "-output_ts_offset", f"{start:.3f}", "-f", "mpegts", str(tmp)]
    _run(cmd)
    os.replace(tmp, out_path)


def concat_segments(segment_files: list[Path], out_path: Path) -> None:
    list_file = out_path.with_suffix(".txt")
    list_file.write_text("".join(f"file '{p}'\n" for p in segment_files))
    tmp = out_path.with_suffix(".part.mp4")
    _run([settings.FFMPEG_BIN, "-v", "error", "-y", "-f", "concat", "-safe", "0",
          "-i", str(list_file), "-c", "copy", "-bsf:a", "aac_adtstoasc", str(tmp)])
    os.replace(tmp, out_path)
    list_file.unlink(missing_ok=True)
