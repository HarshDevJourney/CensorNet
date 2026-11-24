"""
Weapons (guns, knives, grenades ...) with a YOLO detector.

Default weights: HuggingFace 'Subh775/Threat-Detection-YOLOv8n' (classes: Gun, Knife, Grenade, Explosive),
downloaded once on first start and cached. To use your own model set WEAPON_MODEL_PATH=/path/best.pt.
Any class whose NAME is listed in WEAPON_LABELS is treated as a weapon, so custom models just work.
"""
import logging

import numpy as np

from app.config import resolve_device, settings
from app.services.detection import FrameBatch, FrameHit

log = logging.getLogger("weapon")


class WeaponDetector:
    name = "weapon"

    def load(self) -> None:
        from ultralytics import YOLO               # heavy import: once per worker process
        path = settings.WEAPON_MODEL_PATH
        if not path:
            from huggingface_hub import hf_hub_download
            path = hf_hub_download(repo_id=settings.WEAPON_HF_REPO, filename=settings.WEAPON_HF_FILE)
        self.model = YOLO(path)
        self.device = resolve_device()
        wanted = {s.strip().lower() for s in settings.WEAPON_LABELS.split(",") if s.strip()}
        names = self.model.names                  # {class_id: name}
        self.keep = {i for i, n in names.items() if str(n).strip().lower() in wanted}
        if not self.keep:
            raise RuntimeError(f"model classes {list(names.values())} match none of WEAPON_LABELS={sorted(wanted)}")
        log.info("weapon classes: %s", [names[i] for i in sorted(self.keep)])

    def detect(self, batch: FrameBatch) -> list[FrameHit]:
        if len(batch) == 0:
            return []
        bgr = [np.ascontiguousarray(f[..., ::-1]) for f in batch.frames]      # ultralytics arrays are BGR
        results = self.model.predict(bgr, conf=min(settings.THRESH_WEAPON, 0.25), imgsz=settings.WEAPON_IMGSZ,
                                     device=self.device, verbose=False)
        hits: list[FrameHit] = []
        for i, res in enumerate(results):
            for b in res.boxes:
                if int(b.cls[0]) not in self.keep:
                    continue
                x1, y1, x2, y2 = (float(v) for v in b.xyxyn[0].tolist())
                hits.append(FrameHit(i, "weapon", float(b.conf[0]), (x1, y1, x2 - x1, y2 - y1)))
        return hits
