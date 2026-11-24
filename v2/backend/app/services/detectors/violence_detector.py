"""Whole-frame violent-scene blur (on by default, with nudity, weapons and blood)."""
import cv2

from app.config import settings
from app.services.detection import FrameBatch, FrameHit
from app.services.detectors.blood_detector import is_red_lighting, red_mask
from app.services.detectors.violence_classifier import ViolenceClassifier, violence_scores

# A bloody frame does not need the full 0.80 scene score. Colour and the classifier agree.
_GORE_SCORE = 0.55
_GORE_RED_FRACTION = 0.006


class ViolenceDetector:
    name = "violence"

    def load(self) -> None:
        if ViolenceClassifier.get() is None:
            raise RuntimeError("violence detector enabled but no classifier could be loaded")

    def detect(self, batch: FrameBatch) -> list[FrameHit]:
        scores = violence_scores(batch, list(range(len(batch))))
        hits = []
        for i, s in scores.items():
            frame = batch.frames[i]
            strict = red_mask(frame)
            lighting = is_red_lighting(frame, strict)
            wide = red_mask(frame, wide=True)
            bloody = (not lighting) and cv2.countNonZero(wide) / float(wide.size) >= _GORE_RED_FRACTION
            if lighting and s < 0.92:
                continue
            if s < settings.THRESH_VIOLENCE and not (bloody and s >= _GORE_SCORE):
                continue
            hits.append(FrameHit(i, "violence", max(s, settings.THRESH_VIOLENCE if bloody else s), None))
        return hits
