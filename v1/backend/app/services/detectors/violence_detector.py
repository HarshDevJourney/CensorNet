"""Optional whole-frame 'violent scene' blur (enable with ANALYZER=nudenet,weapon,blood,violence)."""
import cv2

from app.services.detection import FrameBatch, FrameHit
from app.services.detectors.blood_detector import _LIGHTING_COVERAGE, red_mask
from app.services.detectors.violence_classifier import ViolenceClassifier, violence_scores


class ViolenceDetector:
    name = "violence"

    def load(self) -> None:
        if ViolenceClassifier.get() is None:
            raise RuntimeError("violence detector enabled but no classifier could be loaded")

    def detect(self, batch: FrameBatch) -> list[FrameHit]:
        scores = violence_scores(batch, list(range(len(batch))))
        hits = []
        for i, s in scores.items():
            m = red_mask(batch.frames[i])
            if cv2.countNonZero(m) / m.size >= _LIGHTING_COVERAGE:
                continue                        # red lighting is not violence (offline project's rule)
            hits.append(FrameHit(i, "violence", s, None))
        return hits
