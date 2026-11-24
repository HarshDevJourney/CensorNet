"""
Pluggable visual analysis. A worker builds the analyzer ONCE at startup (models are heavy) and calls
analyze() for every chunk.

   detectors  -> raw FrameHits (per model)             app/detectors/*.py
   policy     -> which labels matter, thresholds       app/policy.py
   tracking   -> hits -> moving-region Detections      app/tracking.py
   render     -> apply Detections to pixels            app/render.py

Add a model: write a class with load() and detect(batch) -> list[FrameHit], put its label in POLICY,
register it in _DETECTORS below, and add its name to ANALYZER in .env.
"""
import numpy as np

from app.config import settings
from app.services.detection import Detection, FrameBatch, FrameHit
from app.services.tracking import build_detections


class Analyzer:
    def load(self) -> None:
        """Load model weights (called once per worker process)."""

    def analyze(self, frames: np.ndarray, fps: float, chunk_dur: float) -> list[Detection]:
        """frames: (n, h, w, 3) uint8 RGB, frame i is at t = i / fps (relative to chunk start)."""
        raise NotImplementedError


class NoopAnalyzer(Analyzer):
    def analyze(self, frames, fps, chunk_dur):
        return []


class DemoAnalyzer(Analyzer):
    """Blurs a centre box for 1s..2s of EVERY chunk so you can see the pipeline working."""

    def analyze(self, frames, fps, chunk_dur):
        if chunk_dur < 2.0:
            return []
        return [Detection("demo", 1.0, 1.0, 2.0, (0.3, 0.3, 0.4, 0.4), category="demo")]


class EnsembleAnalyzer(Analyzer):
    def __init__(self, detectors: list):
        self.detectors = detectors

    def load(self) -> None:
        for d in self.detectors:
            d.load()

    def analyze(self, frames, fps, chunk_dur):
        batch = FrameBatch(frames, fps)
        hits: list[FrameHit] = []
        for d in self.detectors:
            hits += d.detect(batch)
        return build_detections(hits, fps, len(frames), chunk_dur)


def _nudenet():
    from app.services.detectors.nudenet_detector import NudeNetDetector
    return NudeNetDetector()


def _weapon():
    from app.services.detectors.weapon_detector import WeaponDetector
    return WeaponDetector()


def _blood():
    from app.services.detectors.blood_detector import BloodDetector
    return BloodDetector()


def _violence():
    from app.services.detectors.violence_detector import ViolenceDetector
    return ViolenceDetector()


_DETECTORS = {"nudenet": _nudenet, "weapon": _weapon, "blood": _blood, "violence": _violence}


def get_analyzer() -> Analyzer:
    names = settings.analyzers
    if names in (["noop"], []):
        return NoopAnalyzer()
    if names == ["demo"]:
        return DemoAnalyzer()
    unknown = [n for n in names if n not in _DETECTORS]
    if unknown:
        raise ValueError(f"unknown ANALYZER {unknown} (available: {sorted(_DETECTORS)}, demo, noop)")
    return EnsembleAnalyzer([_DETECTORS[n]() for n in names])
