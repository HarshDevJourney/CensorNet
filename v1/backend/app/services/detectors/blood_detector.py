"""
Blood = red-ish regions (cheap colour analysis) CONFIRMED by the violence classifier.

Colour alone cannot tell blood from a red shirt, lips or a sunset, so:
  1. find dark/saturated red blobs (HSV) and merge neighbours into boxes
  2. ignore frames that are red overall (red lighting) - same idea as the offline project
  3. only on frames that HAVE candidate blobs, ask the classifier; accept if its violence score >= gate
Only the red boxes are blurred (not the whole frame), and a box must persist for BLOOD_MIN_HITS frames.
If the classifier cannot be loaded (or BLOOD_USE_CLASSIFIER=false) only big blobs are accepted.
"""
import cv2
import numpy as np

from app.config import settings
from app.services.detection import FrameBatch, FrameHit
from app.services.detectors.violence_classifier import ViolenceClassifier, violence_scores

# OpenCV HSV: H 0..179. Blood is deep red: low/high hue, strong saturation, not too bright.
_LO1, _HI1 = (0, 110, 35), (10, 255, 200)
_LO2, _HI2 = (168, 110, 35), (179, 255, 200)
_STANDALONE_MIN_AREA = 0.02       # without the classifier a blob must cover >= 2% of the frame
_LIGHTING_COVERAGE = 0.35         # >= 35% of the frame red -> red lighting, not blood
_MIN_MEAN_VALUE = 60              # blobs darker than this are murky fire / shadow, not blood (HSV V, 0..255)


def red_mask(frame_rgb: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)
    return cv2.inRange(hsv, _LO1, _HI1) | cv2.inRange(hsv, _LO2, _HI2)


def blood_regions(frame_rgb: np.ndarray) -> list[tuple[tuple[float, float, float, float], float]]:
    """-> [(normalised box (x, y, w, h), area_fraction), ...] of blood-coloured blobs in one frame."""
    h, w = frame_rgb.shape[:2]
    mask = red_mask(frame_rgb)
    if cv2.countNonZero(mask) / mask.size >= _LIGHTING_COVERAGE:
        return []
    value = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)[..., 2]
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    k = max(5, int(min(h, w) * 0.04)) | 1                       # merge neighbouring splatters
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    regions = []
    for i in range(1, n):
        x, y, bw, bh, area = (int(v) for v in stats[i])
        frac = area / float(h * w)
        if frac < settings.BLOOD_MIN_AREA:
            continue
        if float(value[labels == i].mean()) < _MIN_MEAN_VALUE:
            continue
        regions.append(((x / w, y / h, bw / w, bh / h), frac))
    return regions


class BloodDetector:
    name = "blood"

    def load(self) -> None:
        self.use_classifier = settings.BLOOD_USE_CLASSIFIER
        if self.use_classifier and ViolenceClassifier.get() is None:
            self.use_classifier = False        # already logged a warning

    def detect(self, batch: FrameBatch) -> list[FrameHit]:
        candidates = {i: blood_regions(f) for i, f in enumerate(batch.frames)}
        candidates = {i: r for i, r in candidates.items() if r}
        if not candidates:
            return []
        scores = violence_scores(batch, sorted(candidates)) if self.use_classifier else {}
        hits: list[FrameHit] = []
        for i, regions in candidates.items():
            for box, frac in regions:
                region_score = min(1.0, frac / 0.04)
                if self.use_classifier and i in scores:
                    if scores[i] < settings.BLOOD_VIOLENCE_GATE:
                        continue
                    score = 0.4 * region_score + 0.6 * scores[i]
                else:
                    if frac < _STANDALONE_MIN_AREA:
                        continue
                    score = 0.9 * region_score
                hits.append(FrameHit(i, "blood", score, box))
        return hits
