"""
Pluggable analysis step. A worker builds the analyzer ONCE at startup (models are heavy), then
calls analyze() per chunk.

  detectors  -> raw FrameHits (per model)      app/services/detectors/*.py
  policy     -> which labels matter, thresholds, action     app/services/policy.py
  tracking   -> hits -> moving-region Detections            app/services/tracking.py
  render     -> apply Detections to pixels                  app/services/render.py

Add a model: write a detector class with load() and detect(frames, fps) -> list[FrameHit],
add its labels to POLICY, register it in _DETECTORS below.
"""
import numpy as np

from app.config import settings
from app.services.detection import Detection, FrameHit   # noqa: F401  (re-exported)
from app.services.tracking import build_detections


class Analyzer:
    def load(self) -> None:
        """Load model weights (called once per worker process)."""

    def analyze(self, frames: np.ndarray, fps: float) -> list[Detection]:
        """frames: (n, h, w, 3) uint8 RGB, frame i is at t = i / fps."""
        raise NotImplementedError


class NoopAnalyzer(Analyzer):
    def analyze(self, frames, fps):
        return []


class DemoAnalyzer(Analyzer):
    """Blurs a centre box for 1s..2s of EVERY chunk so you can see the pipeline working."""

    def analyze(self, frames, fps):
        return [Detection("demo", 1.0, 1.0, 2.0, (0.3, 0.3, 0.4, 0.4))]


class EnsembleAnalyzer(Analyzer):
    def __init__(self, detectors: list):
        self.detectors = detectors

    def load(self) -> None:
        for d in self.detectors:
            d.load()

    def analyze(self, frames, fps):
        hits: list[FrameHit] = []
        for d in self.detectors:
            hits += d.detect(frames, fps)
        return build_detections(hits, fps)


def _nudenet():
    from app.services.detectors.nudenet_detector import NudeNetDetector
    return NudeNetDetector()


_DETECTORS = {
    "nudenet": _nudenet,
    # "weapons": ..., "blood": ..., "violence": ...
}


def get_analyzer() -> Analyzer:
    names = [n.strip().lower() for n in settings.ANALYZER.split(",") if n.strip()]
    if names in (["noop"], []):
        return NoopAnalyzer()
    if names == ["demo"]:
        return DemoAnalyzer()
    unknown = [n for n in names if n not in _DETECTORS]
    if unknown:
        raise ValueError(f"unknown ANALYZER {unknown} (available: {sorted(_DETECTORS)}, demo, noop)")
    return EnsembleAnalyzer([_DETECTORS[n]() for n in names])
