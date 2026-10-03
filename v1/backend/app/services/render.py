"""
Turn ONE chunk of the source into ONE independent MPEG-TS (HLS) segment with the censoring applied.

  video:  no visual detections -> ffmpeg re-encodes directly
          visual detections    -> ffmpeg decode (full res, raw) -> OpenCV obscures ONLY the tracked boxes
                                  -> ffmpeg encode        (so the rest of the frame stays sharp)
  audio:  original audio, with each profane span replaced by a beep tone

Every segment gets  -output_ts_offset <chunk start>  so timestamps are continuous across chunks that were
encoded by different workers at different times; hls.js plays them back to back and can seek anywhere.
The file is written to *.part and atomically renamed: "file exists"  <=>  "segment is complete".
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

AUDIO_RATE = 48000
# AAC's encoder delay is 1024 samples. Without a shift, chunk 0 (which cannot start before t=0) would be pushed
# 21 ms later than every other chunk. Shifting ALL chunks by the same amount keeps the timeline uniform.
TS_SHIFT = 1024 / AUDIO_RATE


# ----------------------------------------------------------------------------- pixels

def obscure(frame: np.ndarray, box, action: str = "blur", shape: str = "rect") -> None:
    """In place. box = normalised (x, y, w, h) or None for the whole frame."""
    H, W = frame.shape[:2]
    if box is None:
        x0, y0, x1, y1 = 0, 0, W, H
    else:
        x0, y0 = int(round(box[0] * W)), int(round(box[1] * H))
        x1, y1 = int(round((box[0] + box[2]) * W)), int(round((box[1] + box[3]) * H))
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return

    f = max(3, min(x1 - x0, y1 - y0) // 10)                   # soft edge falls outside the box
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


# ----------------------------------------------------------------------------- audio graph

def _between(events: list[dict]) -> str:
    return "+".join(f"between(t,{e['start']:.3f},{e['end']:.3f})" for e in events)


def audio_graph(events: list[dict], dur: float, src_idx: int, beep_idx: int) -> str:
    """
    filter_complex that mutes the original audio inside each event and plays a beep there instead.
    The beep source is a continuous sine that is silenced everywhere EXCEPT inside the events.
    amix halves each input by default, so volume=2 puts the level back.
    """
    ev = _between(events)
    fmt = f"aformat=sample_fmts=fltp:sample_rates={AUDIO_RATE}:channel_layouts=stereo"
    return (
        f"[{src_idx}:a]{fmt},apad=whole_dur={dur:.3f},volume=0:enable='{ev}'[quiet];"
        f"[{beep_idx}:a]{fmt},volume={settings.BEEP_VOLUME * 8:.3f},volume=0:enable='not({ev})'[beep];"
        f"[quiet][beep]amix=inputs=2:duration=first:dropout_transition=0,volume=2[aout]"
    )


def _beep_input(dur: float) -> list[str]:
    return ["-f", "lavfi", "-t", f"{dur:.3f}", "-i",
            f"sine=frequency={settings.BEEP_FREQUENCY}:sample_rate={AUDIO_RATE}"]


def _encode_args(fps: float, start: float, dur: float, has_audio: bool, tmp: Path) -> list[str]:
    a = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
         "-r", f"{fps:.3f}", "-g", str(max(1, int(round(fps * 2)))), "-sc_threshold", "0",
         "-bf", "0",                     # no B-frames: DTS == PTS, so segments join without overlapping timestamps
         "-threads", "2"]
    if has_audio:
        a += ["-c:a", "aac", "-b:a", "128k", "-ar", str(AUDIO_RATE), "-ac", "2"]
    a += ["-t", f"{dur:.3f}", "-output_ts_offset", f"{start + TS_SHIFT:.6f}", "-muxdelay", "0", "-muxpreload", "0",
          "-f", "mpegts", str(tmp)]
    return a


# ----------------------------------------------------------------------------- the two paths

def _plain(src, start, dur, tmp, fps, has_audio, events) -> list[str]:
    """No visual detections: one ffmpeg command."""
    cmd = [settings.FFMPEG_BIN, "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src]
    vf = f"fps={fps:.3f},pad=ceil(iw/2)*2:ceil(ih/2)*2"
    if has_audio and events:
        cmd += _beep_input(dur)
        cmd += ["-filter_complex", f"[0:v]{vf}[vout];" + audio_graph(events, dur, 0, 1),
                "-map", "[vout]", "-map", "[aout]"]
    elif has_audio:
        cmd += ["-filter_complex", f"[0:v]{vf}[vout];[0:a]apad=whole_dur={dur:.3f}[aout]",
                "-map", "[vout]", "-map", "[aout]"]
    else:
        cmd += ["-vf", vf, "-map", "0:v:0"]
    return cmd + _encode_args(fps, start, dur, has_audio, tmp)


def _read_exact(stream, n: int) -> bytes | None:
    buf = bytearray()
    while len(buf) < n:
        chunk = stream.read(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return bytes(buf)


def _piped(src, start, dur, tmp, fps, has_audio, events, detections, width, height) -> None:
    """Visual detections: ffmpeg -> OpenCV -> ffmpeg."""
    frame_bytes = width * height * 3
    reader_cmd = [settings.FFMPEG_BIN, "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src,
                  "-an", "-vf", f"fps={fps:.3f}", "-f", "rawvideo", "-pix_fmt", "bgr24", "pipe:1"]
    writer_cmd = [settings.FFMPEG_BIN, "-v", "error", "-y",
                  "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{width}x{height}", "-framerate", f"{fps:.3f}",
                  "-i", "pipe:0"]
    vf = "pad=ceil(iw/2)*2:ceil(ih/2)*2"
    if has_audio:
        writer_cmd += ["-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src]       # input 1: original audio
        if events:
            writer_cmd += _beep_input(dur)                                          # input 2: beep tone
            writer_cmd += ["-filter_complex", f"[0:v]{vf}[vout];" + audio_graph(events, dur, 1, 2)]
        else:
            writer_cmd += ["-filter_complex", f"[0:v]{vf}[vout];[1:a]apad=whole_dur={dur:.3f}[aout]"]
        writer_cmd += ["-map", "[vout]", "-map", "[aout]"]
    else:
        writer_cmd += ["-vf", vf, "-map", "0:v:0"]
    writer_cmd += _encode_args(fps, start, dur, has_audio, tmp)

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
                        obscure(frame, d.box_at(t), d.action, d.shape)
                writer.stdin.write(frame.tobytes())
                i += 1
            writer.stdin.close()
        except BrokenPipeError:
            pass                      # writer died; its return code + stderr are reported below
        finally:
            reader.stdout.close()
            rc_r, rc_w = reader.wait(), writer.wait()
        if rc_r != 0 or rc_w != 0:
            rerr.seek(0); werr.seek(0)
            tmp.unlink(missing_ok=True)
            raise FFmpegError(f"render failed (reader={rc_r}, writer={rc_w}): "
                              f"{rerr.read().decode(errors='ignore')[-300:]} | "
                              f"{werr.read().decode(errors='ignore')[-500:]}")


def render_segment(src: str, start: float, dur: float, out_path: Path, *, width: int, height: int,
                   fps: float, has_audio: bool, detections: list[Detection], events: list[dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".part")
    if detections:
        _piped(src, start, dur, tmp, fps, has_audio, events, detections, width, height)
    else:
        cmd = _plain(src, start, dur, tmp, fps, has_audio, events)
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode != 0:
            tmp.unlink(missing_ok=True)
            raise FFmpegError(f"encode failed ({p.returncode}): {p.stderr.decode(errors='ignore')[-800:]}")
    os.replace(tmp, out_path)
