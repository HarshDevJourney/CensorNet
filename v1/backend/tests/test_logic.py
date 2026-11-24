"""Pure-logic tests (no models, no ffmpeg)."""
import numpy as np

from app.services import audio_service as audio
from app.services.detection import FrameHit
from app.services.detectors.blood_detector import blood_regions
from app.services.profanity import is_profane
from app.services.tracking import build_detections


# ---------------------------------------------------------------- tracking
def test_track_moves_and_is_padded_and_clamped():
    hits = [FrameHit(i, "weapon", 0.9, (0.1 + 0.05 * i, 0.2, 0.2, 0.2)) for i in range(2, 6)]
    (d,) = build_detections(hits, fps=3.0, n_frames=12, chunk_dur=4.0)
    assert d.category == "weapon" and d.action == "blur"
    assert 0.0 <= d.t_start < 2 / 3 and d.t_end <= 4.0
    b0, b1 = d.box_at(2 / 3), d.box_at(5 / 3)
    assert b1[0] > b0[0]                      # box follows the object


def test_below_threshold_ignored():
    assert build_detections([FrameHit(1, "weapon", 0.2, (0.1, 0.1, 0.2, 0.2))], 3.0, 12, 4.0) == []


def test_blood_needs_two_frames_unless_at_chunk_edge():
    one = [FrameHit(5, "blood", 0.9, (0.1, 0.1, 0.2, 0.2))]
    assert build_detections(one, 3.0, 12, 4.0) == []                     # flicker in the middle: dropped
    edge = [FrameHit(0, "blood", 0.9, (0.1, 0.1, 0.2, 0.2))]
    assert len(build_detections(edge, 3.0, 12, 4.0)) == 1                # touches the chunk start: kept
    two = [FrameHit(5, "blood", 0.9, (0.1, 0.1, 0.2, 0.2)), FrameHit(6, "blood", 0.9, (0.1, 0.1, 0.2, 0.2))]
    assert len(build_detections(two, 3.0, 12, 4.0)) == 1


def test_whole_frame_violence_has_no_box():
    hits = [FrameHit(3, "violence", 0.95), FrameHit(4, "violence", 0.95)]
    (d,) = build_detections(hits, 3.0, 12, 4.0)
    assert d.box is None and d.box_at(1.5) is None


# ---------------------------------------------------------------- profanity / beep windows
def test_profanity_matching():
    assert is_profane("Fuck!") and is_profane("fuuuuck")      # case, punctuation, stretched letters
    assert is_profane("f***")                                 # whisper masks some words itself
    assert not is_profane("class") and not is_profane("hello")


def test_events_merge_and_clip_to_chunk():
    words = [{"word": "hello", "start": 3.0, "end": 3.4},
             {"word": "fuck", "start": 4.5, "end": 4.8},
             {"word": "shit", "start": 4.85, "end": 5.1},       # close neighbour -> merged
             {"word": "world", "start": 6.0, "end": 6.3}]
    ev = audio.find_events(words)
    assert len(ev) == 1 and ev[0]["words"] == ["fuck", "shit"]
    assert audio.clip_to_chunk(ev, start=4.0, dur=4.0)[0]["start"] < 0.6   # relative to chunk 1 (4..8)
    assert audio.clip_to_chunk(ev, start=8.0, dur=4.0) == []               # other chunks: nothing


def test_word_on_chunk_border_is_beeped_by_both_chunks():
    ev = audio.find_events([{"word": "fuck", "start": 3.8, "end": 4.2}])
    left, right = audio.clip_to_chunk(ev, 0.0, 4.0), audio.clip_to_chunk(ev, 4.0, 4.0)
    assert left and right and left[0]["end"] == 4.0 and right[0]["start"] == 0.0


# ---------------------------------------------------------------- blood colour stage
def _frame(color=(40, 40, 40)):
    f = np.zeros((360, 640, 3), np.uint8)
    f[:] = color
    return f


def test_dark_red_blob_is_found_and_boxed():
    f = _frame()
    f[100:200, 300:420] = (120, 10, 10)            # RGB dark red
    regions = blood_regions(f)
    assert len(regions) == 1
    (x, y, w, h), frac = regions[0]
    assert 0.40 < x < 0.50 and 0.25 < y < 0.30 and frac > 0.03


def test_plain_and_red_lighting_frames_are_ignored():
    assert blood_regions(_frame()) == []
    assert blood_regions(_frame((130, 12, 12))) == []     # whole frame red = lighting, not blood


def test_blood_ignores_murky_dark_red_but_keeps_bright_blood():
    f = _frame()
    f[100:200, 300:420] = (45, 8, 8)               # very dark red (fire / shadow)
    assert blood_regions(f) == []


# ---------------------------------------------------------------- chunk count
def test_tail_shorter_than_half_second_is_merged():
    from app import models as store
    assert store.chunk_count(24.04, 4.0) == 6      # 6 chunks, last one is 4.04 s
    assert store.chunk_count(24.6, 4.0) == 7
    assert store.chunk_count(3.0, 4.0) == 1 and store.chunk_count(0.2, 4.0) == 1
    info = {"chunk_seconds": 4.0, "duration": 24.04, "total": 6}
    assert store.chunk_bounds(info, 5) == (20.0, 24.04)
