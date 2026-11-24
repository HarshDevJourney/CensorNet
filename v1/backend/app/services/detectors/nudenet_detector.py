import numpy as np

from app.config import resolve_device, settings
from app.services.detection import FrameBatch, FrameHit
from app.services.policy import POLICY


class NudeNetDetector:
    name = "nudenet"

    def load(self) -> None:
        from nudenet import NudeDetector          # heavy import: once per worker process
        providers = ["CPUExecutionProvider"]
        if resolve_device() == "cuda":
            providers.insert(0, "CUDAExecutionProvider")   # needs onnxruntime-gpu; falls back to CPU otherwise
        self.model = NudeDetector(model_path=settings.NUDENET_MODEL_PATH or None, providers=providers,
                                  inference_resolution=settings.NUDENET_RESOLUTION)

    def detect(self, batch: FrameBatch) -> list[FrameHit]:
        n, h, w, _ = batch.frames.shape
        if n == 0:
            return []
        # NudeNet takes arrays in cv2.imread order (BGR); our frames are RGB.
        bgr = [np.ascontiguousarray(f[..., ::-1]) for f in batch.frames]
        hits: list[FrameHit] = []
        for i, dets in enumerate(self.model.detect_batch(bgr, batch_size=8)):
            for d in dets:
                if d["class"] not in POLICY:
                    continue
                x, y, bw, bh = d["box"]                      # pixels of the analysis frame
                hits.append(FrameHit(i, d["class"], float(d["score"]), (x / w, y / h, bw / w, bh / h)))
        return hits
