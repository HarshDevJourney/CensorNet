"""Shared data types for the analysis pipeline (no heavy imports here)."""
from bisect import bisect_right
from dataclasses import dataclass, field

Box = tuple[float, float, float, float]          # normalised (x, y, w, h), top-left origin


@dataclass
class FrameHit:
    """One raw model hit on one sampled frame. frame_idx i is at t = i / ANALYSIS_FPS."""
    frame_idx: int
    label: str
    score: float
    box: Box | None = None                       # None = whole frame


@dataclass
class Detection:
    """A censorship instruction: 'between t_start and t_end, obscure this (moving) region'."""
    label: str
    score: float
    t_start: float                               # seconds, relative to chunk start
    t_end: float
    box: Box | None                              # union box (for UI / logging); None = whole frame
    action: str = "blur"                         # blur | blackout
    shape: str = "rect"                          # rect | ellipse
    track: list[tuple[float, Box]] = field(default_factory=list)   # keyframes (t, box)

    def box_at(self, t: float) -> Box | None:
        """Box at time t: linear interpolation between keyframes, held outside them."""
        if not self.track:
            return self.box
        ts = [k[0] for k in self.track]
        if t <= ts[0]:
            return self.track[0][1]
        if t >= ts[-1]:
            return self.track[-1][1]
        i = bisect_right(ts, t)
        (t0, b0), (t1, b1) = self.track[i - 1], self.track[i]
        a = (t - t0) / (t1 - t0)
        return tuple(b0[j] + (b1[j] - b0[j]) * a for j in range(4))  # type: ignore[return-value]

    def to_dict(self, chunk_start: float = 0.0) -> dict:
        """JSON for the DB / events. Times are ABSOLUTE video time."""
        return {
            "label": self.label, "score": round(self.score, 4),
            "t_start": round(self.t_start + chunk_start, 3),
            "t_end": round(self.t_end + chunk_start, 3),
            "box": list(self.box) if self.box else None,
            "action": self.action, "shape": self.shape,
            "track": [[round(t + chunk_start, 3), [round(v, 4) for v in b]] for t, b in self.track],
        }
