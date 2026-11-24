"""
Blood = red-ish regions CONFIRMED by the violence classifier.

Colour alone cannot tell blood from a red shirt, lips or a sunset, so:
  1. find saturated red blobs (HSV + red-dominant RGB) and merge neighbours into boxes
  2. a smooth red wash is lighting, not gore; a blotchy red field can still be blood
  3. a calm scene keeps only obvious blobs; a violent scene also keeps small and dark wounds
Only the red boxes are blurred (not the whole frame), and a box must persist for BLOOD_MIN_HITS frames.
If the classifier cannot be loaded (or BLOOD_USE_CLASSIFIER=false) only big blobs are accepted.
"""
import cv2
import numpy as np

from app.config import settings
from app.services.detection import FrameBatch, FrameHit
from app.services.detectors.violence_classifier import ViolenceClassifier, violence_scores

# OpenCV HSV: H 0..179. Strict range is bright saturated blood. The wide range also
# catches dark, dried, and compression-shifted blood once the scene is known to be violent.
_LO1, _HI1 = (0, 110, 35), (10, 255, 200)
_LO2, _HI2 = (168, 110, 35), (179, 255, 200)
_LO1_WIDE, _HI1_WIDE = (0, 60, 18), (16, 255, 235)
_LO2_WIDE, _HI2_WIDE = (158, 60, 18), (179, 255, 235)
_STANDALONE_MIN_AREA = 0.02       # without the classifier a blob must cover >= 2% of the frame
_LIGHTING_COVERAGE = 0.35         # >= 35% of the frame red -> maybe red lighting, not blood
_LIGHTING_SAT_STD = 22.0          # a flat red wash (sunset, gel light) has almost no saturation variation
_MIN_MEAN_VALUE = 60              # strict blobs darker than this are shadow, not blood (HSV V, 0..255)
_RELAXED_MIN_VALUE = 28           # dark blood is allowed only when the violence score is high
_RELAXED_MIN_AREA = 0.0012        # a small wound, still larger than a lip or an indicator LED
_STRONG_VIOLENCE = 0.55           # at/above this, a small confirmed wound is kept


def red_mask(frame_rgb: np.ndarray, *, wide: bool = False) -> np.ndarray:
    hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)
    if wide:
        mask = cv2.inRange(hsv, _LO1_WIDE, _HI1_WIDE) | cv2.inRange(hsv, _LO2_WIDE, _HI2_WIDE)
        r, g, b = frame_rgb[..., 0].astype(np.int16), frame_rgb[..., 1].astype(np.int16), frame_rgb[..., 2].astype(np.int16)
        dominant = (r > 55) & (r > (g * 1.35).astype(np.int16) + 12) & (r > (b * 1.25).astype(np.int16) + 8)
        return mask | dominant.astype(np.uint8) * 255
    return cv2.inRange(hsv, _LO1, _HI1) | cv2.inRange(hsv, _LO2, _HI2)


def is_red_lighting(frame_rgb: np.ndarray, mask: np.ndarray) -> bool:
    """True when red covers the frame as a smooth wash rather than blotches of blood."""
    coverage = cv2.countNonZero(mask) / float(mask.size)
    if coverage < _LIGHTING_COVERAGE:
        return False
    sat = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)[..., 1]
    return float(sat[mask > 0].std()) < _LIGHTING_SAT_STD


def _skin_tone(h: float, s: float, v: float) -> bool:
    """Lips and skin sit at a higher hue and lower saturation than fresh blood."""
    return 6.0 <= h <= 28.0 and s < 150.0 and v > 125.0


def _regions(frame_rgb: np.ndarray, mask: np.ndarray, min_area: float, min_value: float,
             reject_skin: bool) -> list[tuple[tuple[float, float, float, float], float]]:
    h, w = frame_rgb.shape[:2]
    hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)
    value, hue, sat = hsv[..., 2], hsv[..., 0], hsv[..., 1]
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    k = max(5, int(min(h, w) * 0.04)) | 1                       # merge neighbouring splatters
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    regions = []
    for i in range(1, n):
        x, y, bw, bh, area = (int(v) for v in stats[i])
        frac = area / float(h * w)
        if frac < min_area:
            continue
        pixels = labels == i
        if float(value[pixels].mean()) < min_value:
            continue
        if reject_skin and _skin_tone(float(hue[pixels].mean()), float(sat[pixels].mean()), float(value[pixels].mean())):
            continue
        regions.append(((x / w, y / h, bw / w, bh / h), frac))
    return regions


def blood_regions(frame_rgb: np.ndarray) -> list[tuple[tuple[float, float, float, float], float]]:
    """Strict blobs. A frame that is red overall is treated as lighting and returns nothing."""
    mask = red_mask(frame_rgb)
    if is_red_lighting(frame_rgb, mask):
        return []
    return _regions(frame_rgb, mask, settings.BLOOD_MIN_AREA, _MIN_MEAN_VALUE, reject_skin=False)


def relaxed_blood_regions(frame_rgb: np.ndarray, violence: float) -> list[tuple[tuple[float, float, float, float], float]]:
    """Smaller and darker blood, used only after the classifier says the scene is violent."""
    mask = red_mask(frame_rgb, wide=True)
    if is_red_lighting(frame_rgb, mask) and violence < 0.92:
        return []
    min_area = _RELAXED_MIN_AREA if violence >= _STRONG_VIOLENCE else settings.BLOOD_MIN_AREA
    return _regions(frame_rgb, mask, min_area, _RELAXED_MIN_VALUE, reject_skin=True)


class BloodDetector:
    name = "blood"

    def load(self) -> None:
        self.use_classifier = settings.BLOOD_USE_CLASSIFIER
        if self.use_classifier and ViolenceClassifier.get() is None:
            self.use_classifier = False        # already logged a warning

    def detect(self, batch: FrameBatch) -> list[FrameHit]:
        scores = violence_scores(batch, list(range(len(batch)))) if self.use_classifier else {}
        hits: list[FrameHit] = []
        for i, frame in enumerate(batch.frames):
            vio = scores.get(i)
            if self.use_classifier:
                # A red shirt in a calm scene is not blood, however large it is.
                if vio is None or vio < settings.BLOOD_VIOLENCE_GATE:
                    continue
                regions = relaxed_blood_regions(frame, vio)
            else:
                regions = blood_regions(frame)
            for box, frac in regions:
                region_score = min(1.0, frac / 0.04)
                if self.use_classifier:
                    score = 0.35 * region_score + 0.65 * vio
                    # A clearly violent scene should not lose a small wound to the size term.
                    if vio >= _STRONG_VIOLENCE:
                        score = max(score, settings.THRESH_BLOOD)
                    elif score < settings.THRESH_BLOOD:
                        continue
                else:
                    if frac < _STANDALONE_MIN_AREA:
                        continue
                    score = 0.9 * region_score
                hits.append(FrameHit(i, "blood", score, box))
        return hits
