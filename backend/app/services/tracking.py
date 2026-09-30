"""Raw per-frame hits  ->  moving-region Detections (one per tracked object)."""
from collections import defaultdict

from app.config import settings
from app.services.detection import Box, Detection, FrameHit
from app.services.policy import POLICY


def _center(b: Box) -> tuple[float, float]:
    return b[0] + b[2] / 2, b[1] + b[3] / 2


def _same_object(a: Box | None, b: Box | None) -> bool:
    if a is None or b is None:
        return True
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    if ix * iy > 0:
        return True
    (ax, ay), (bx, by) = _center(a), _center(b)
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5 <= max(a[2], a[3], b[2], b[3])


def _dist(a: Box | None, b: Box | None) -> float:
    if a is None or b is None:
        return 0.0
    (ax, ay), (bx, by) = _center(a), _center(b)
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5


def _grow(b: Box, m: float) -> Box:
    x, y, w, h = b
    x0, y0 = max(0.0, x - w * m), max(0.0, y - h * m)
    x1, y1 = min(1.0, x + w * (1 + m)), min(1.0, y + h * (1 + m))
    return (x0, y0, x1 - x0, y1 - y0)


def build_detections(hits: list[FrameHit], fps: float) -> list[Detection]:
    step, pad, max_gap = 1.0 / fps, settings.TIME_PAD_SECONDS, settings.TRACK_MAX_GAP

    by_label: dict[str, list[FrameHit]] = defaultdict(list)
    for h in hits:
        rule = POLICY.get(h.label)
        if rule and h.score >= rule.threshold:
            by_label[h.label].append(h)

    out: list[Detection] = []
    for label, group in by_label.items():
        rule = POLICY[label]
        group.sort(key=lambda h: h.frame_idx)
        tracks: list[list[FrameHit]] = []
        for h in group:
            best, best_d = None, 1e9
            for tr in tracks:
                last = tr[-1]
                if 0 < h.frame_idx - last.frame_idx <= max_gap and _same_object(last.box, h.box):
                    d = _dist(last.box, h.box)
                    if d < best_d:
                        best, best_d = tr, d
            if best is None:
                tracks.append([h])
            else:
                best.append(h)

        for tr in tracks:
            t0, t1 = tr[0].frame_idx * step, tr[-1].frame_idx * step
            if any(h.box is None for h in tr):
                keys, union = [], None
            else:
                keys = [(h.frame_idx * step, _grow(h.box, rule.margin)) for h in tr]
                x0 = min(b[0] for _, b in keys); y0 = min(b[1] for _, b in keys)
                x1 = max(b[0] + b[2] for _, b in keys); y1 = max(b[1] + b[3] for _, b in keys)
                union = (x0, y0, x1 - x0, y1 - y0)
            out.append(Detection(label, max(h.score for h in tr),
                                 max(0.0, t0 - pad), t1 + step + pad, union,
                                 rule.action, rule.shape, keys))
    return sorted(out, key=lambda d: d.t_start)
