from typing import Protocol

from app.services.detection import FrameBatch, FrameHit


class Detector(Protocol):
    name: str

    def load(self) -> None:
        """Load model weights. Called once per worker process."""

    def detect(self, batch: FrameBatch) -> list[FrameHit]:
        """Return raw hits. frame_idx i is at t = i / batch.fps. Boxes are normalised (x, y, w, h)."""
