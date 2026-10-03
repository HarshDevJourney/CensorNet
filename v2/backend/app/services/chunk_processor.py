"""
Process ONE chunk: analyse (video + audio in parallel) -> censor -> write its HLS segment.

SAFETY RULE: a chunk that fails is never served uncensored. It stays 'failed' (HTTP 502 for that segment)
until it is retried.
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from app import models
from app.config import settings
from app.models import JobStatus
from app.services import audio_service, ffmpeg_service, queue_service, storage
from app.services.analyzer import Analyzer
from app.services.render import render_segment

log = logging.getLogger("chunk_processor")


def _analyze_video(info: dict, start: float, dur: float, analyzer: Analyzer):
    frames = ffmpeg_service.extract_frames(info["source_path"], start, dur, info["width"], info["height"])
    if len(frames) == 0:
        return []
    return analyzer.analyze(frames, settings.ANALYSIS_FPS, dur)


def process_chunk(vid: int, idx: int, analyzer: Analyzer, worker: str) -> None:
    info = models.video_info(vid)
    if not info or info["status"] != JobStatus.processing:
        return                                              # cancelled / failed / gone
    if not models.cas_chunk(vid, idx, models.PENDING, models.PROCESSING):
        return                                              # another worker (or the reaper) owns it
    attempts = models.mark_started(vid, idx, worker)
    start, end = models.chunk_bounds(info, idx)
    dur = end - start
    t0 = time.time()
    try:
        out = storage.segment_abs(vid, idx)
        with ThreadPoolExecutor(max_workers=1) as pool:
            # speech runs in a thread while this thread does the frame analysis
            audio_future = None
            if settings.AUDIO_ENABLED and info["has_audio"]:
                audio_future = pool.submit(audio_service.events_for_chunk, info["source_path"], start, dur,
                                           info["duration"])
            detections = _analyze_video(info, start, dur, analyzer)
            events = audio_future.result() if audio_future else []

        render_segment(info["source_path"], start, dur, out, width=info["width"], height=info["height"],
                       fps=info["fps"], has_audio=info["has_audio"], detections=detections, events=events)

        ms = int((time.time() - t0) * 1000)
        ok = models.mark_completed(vid, idx, [d.to_dict(start) for d in detections],
                                   [{**e, "start": round(e["start"] + start, 3), "end": round(e["end"] + start, 3)}
                                    for e in events], ms)
        log.info("[%s] video %s chunk %s done in %d ms (%d visual, %d beeps)%s", worker, vid, idx, ms,
                 len(detections), len(events), "" if ok else "  (result discarded: chunk no longer ours)")
    except Exception as e:  # noqa: BLE001
        log.exception("chunk %s/%s failed (attempt %d)", vid, idx, attempts)
        give_up = attempts >= settings.MAX_ATTEMPTS
        models.mark_error(vid, idx, str(e), give_up=give_up)
        if not give_up:
            fresh = models.video_info(vid)
            queue_service.enqueue_chunks(vid, [idx], fresh["playhead"] if fresh else 0)
