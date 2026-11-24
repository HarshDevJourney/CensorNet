"""
Per-chunk speech censoring (no whole-video pre-pass, so playback can start immediately):

    audio window = chunk +/- AUDIO_CONTEXT_SECONDS  ->  faster-whisper (word timestamps)
                -> profane words -> padded, merged spans -> clipped to THIS chunk, relative to chunk start

The context lets a word that straddles a chunk border be heard whole by both neighbouring chunks, so each
chunk beeps its own half of it.
"""
import logging

import numpy as np

from app.services import ffmpeg_service
from app.config import resolve_device, settings
from app.services.profanity import is_profane

log = logging.getLogger("audio")
_model = None


def load_model():
    """Heavy: once per worker process."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        device = resolve_device(settings.WHISPER_DEVICE if settings.WHISPER_DEVICE != "auto" else None)
        compute = settings.WHISPER_COMPUTE
        if compute == "auto":
            compute = "float16" if device == "cuda" else "int8"
        log.info("loading whisper '%s' on %s (%s)", settings.WHISPER_MODEL, device, compute)
        _model = WhisperModel(settings.WHISPER_MODEL, device=device, compute_type=compute,
                              cpu_threads=settings.WHISPER_CPU_THREADS)
    return _model


def transcribe_words(samples: np.ndarray, offset: float) -> list[dict]:
    """-> [{"word", "start", "end"}] with ABSOLUTE video times (offset = where the window starts)."""
    segments, _info = load_model().transcribe(
        samples,
        language=settings.WHISPER_LANGUAGE or None,
        word_timestamps=True,
        beam_size=1,
        vad_filter=settings.WHISPER_VAD,
        condition_on_previous_text=False,        # avoids repetition/hallucination loops
        initial_prompt=settings.WHISPER_PROMPT or None,
    )
    words = []
    for seg in segments:
        for w in seg.words or []:
            words.append({"word": w.word.strip(), "start": offset + float(w.start), "end": offset + float(w.end)})
    return words


def find_events(words: list[dict]) -> list[dict]:
    """Flag profane words, pad them (Whisper timestamps are loose), merge neighbours. Absolute times."""
    pad, gap = settings.BEEP_PAD_SECONDS, settings.BEEP_MERGE_GAP
    events: list[dict] = []
    for w in words:
        if not is_profane(w["word"]):
            continue
        s, e = max(0.0, w["start"] - pad), w["end"] + pad
        if events and s <= events[-1]["end"] + gap:
            events[-1]["end"] = max(events[-1]["end"], e)
            events[-1]["words"].append(w["word"])
        else:
            events.append({"start": s, "end": e, "words": [w["word"]], "label": "profanity"})
    return events


def clip_to_chunk(events: list[dict], start: float, dur: float) -> list[dict]:
    """Absolute events -> events relative to the chunk, dropped if they do not overlap it."""
    out = []
    for ev in events:
        s, e = max(0.0, ev["start"] - start), min(dur, ev["end"] - start)
        if e - s > 0.02:
            out.append({**ev, "start": round(s, 3), "end": round(e, 3)})
    return out


def events_for_chunk(src: str, start: float, dur: float, video_duration: float) -> list[dict]:
    ctx = settings.AUDIO_CONTEXT_SECONDS
    w0 = max(0.0, start - ctx)
    w1 = min(video_duration, start + dur + ctx)
    samples = ffmpeg_service.extract_audio(src, w0, w1 - w0)
    if samples.size < 1600 or float(np.abs(samples).max()) < 0.004:      # < 0.1 s, or digital silence
        return []
    words = transcribe_words(samples, w0)
    return clip_to_chunk(find_events(words), start, dur)
