"""Detector wiring tests. YOLO / ViT weights are replaced by stand-ins, so these run anywhere in <1 s."""
import sys
import types

import numpy as np

from app.services import analyzer as analyzer_mod
from app.services.detection import FrameBatch


class _T:                                   # tiny tensor stand-in
    def __init__(self, v): self.v = v
    def __getitem__(self, i): return _T(self.v[i]) if isinstance(self.v, (list, tuple)) else self.v
    def tolist(self): return list(self.v)
    def __int__(self): return int(self.v)
    def __float__(self): return float(self.v)


class _Box:
    def __init__(self, cls, conf, xyxyn): self.cls, self.conf, self.xyxyn = _T([cls]), _T([conf]), _T([xyxyn])


class _Res:
    def __init__(self, boxes): self.boxes = boxes


class _FakeYOLO:
    names = {0: "Explosive", 1: "Gun", 2: "Grenade", 3: "Knife", 4: "person"}

    def __init__(self, path): self.path = path

    def predict(self, frames, **kw):
        out = []
        for i, _ in enumerate(frames):
            boxes = [_Box(4, 0.99, (0, 0, 1, 1))]                       # a person: must be ignored
            if i == 1:
                boxes.append(_Box(1, 0.88, (0.2, 0.3, 0.6, 0.7)))       # a gun on frame 1
            out.append(_Res(boxes))
        return out


def test_weapon_detector_keeps_only_weapon_classes_and_converts_boxes(monkeypatch):
    monkeypatch.setitem(sys.modules, "ultralytics", types.SimpleNamespace(YOLO=_FakeYOLO))
    from app.config import settings
    monkeypatch.setattr(settings, "WEAPON_MODEL_PATH", "fake.pt")
    from app.services.detectors.weapon_detector import WeaponDetector
    d = WeaponDetector(); d.load()
    hits = d.detect(FrameBatch(np.zeros((3, 90, 160, 3), np.uint8), 3.0))
    assert [(h.frame_idx, h.label) for h in hits] == [(1, "weapon")]
    x, y, w, h = hits[0].box
    assert (round(x, 2), round(y, 2), round(w, 2), round(h, 2)) == (0.2, 0.3, 0.4, 0.4)


def test_ensemble_turns_weapon_hits_into_a_blur_instruction(monkeypatch):
    monkeypatch.setitem(sys.modules, "ultralytics", types.SimpleNamespace(YOLO=_FakeYOLO))
    from app.config import settings
    monkeypatch.setattr(settings, "WEAPON_MODEL_PATH", "fake.pt")
    monkeypatch.setattr(settings, "ANALYZER", "weapon")
    a = analyzer_mod.get_analyzer(); a.load()
    (det,) = a.analyze(np.zeros((12, 90, 160, 3), np.uint8), 3.0, 4.0)
    assert det.category == "weapon" and det.action == "blur" and det.box is not None


def test_blood_detector_without_classifier_needs_a_big_blob(monkeypatch):
    from app.config import settings
    from app.services.detectors import blood_detector as bd
    monkeypatch.setattr(bd.ViolenceClassifier, "get", classmethod(lambda cls: None))
    monkeypatch.setattr(settings, "BLOOD_USE_CLASSIFIER", True)
    det = bd.BloodDetector(); det.load()
    assert det.use_classifier is False                     # degraded gracefully, no crash
    frames = np.full((4, 180, 320, 3), 40, np.uint8)
    frames[:, 40:120, 80:240] = (130, 10, 10)              # big, bright-enough red blob on every frame
    hits = det.detect(FrameBatch(frames, 3.0))
    assert len(hits) == 4 and all(h.label == "blood" for h in hits)
    small = np.full((4, 180, 320, 3), 40, np.uint8)
    small[:, 100:110, 100:110] = (130, 10, 10)             # tiny red dot (e.g. a lip, a bulb)
    assert det.detect(FrameBatch(small, 3.0)) == []


def test_blood_is_gated_by_the_classifier(monkeypatch):
    from app.config import settings
    from app.services.detectors import blood_detector as bd
    scores = {0: 0.9, 1: 0.1, 2: 0.9, 3: 0.1}
    monkeypatch.setattr(bd.ViolenceClassifier, "get", classmethod(lambda cls: object()))
    monkeypatch.setattr(bd, "violence_scores", lambda batch, idx: {i: scores[i] for i in idx})
    monkeypatch.setattr(settings, "BLOOD_USE_CLASSIFIER", True)
    det = bd.BloodDetector(); det.load()
    frames = np.full((4, 180, 320, 3), 40, np.uint8)
    frames[:, 40:120, 80:240] = (130, 10, 10)
    assert sorted(h.frame_idx for h in det.detect(FrameBatch(frames, 3.0))) == [0, 2]   # red shirt on 1, 3 ignored


def test_unknown_detector_name_is_a_clear_error(monkeypatch):
    import pytest
    from app.config import settings
    monkeypatch.setattr(settings, "ANALYZER", "nudenet,lasers")
    with pytest.raises(ValueError, match="lasers"):
        analyzer_mod.get_analyzer()
