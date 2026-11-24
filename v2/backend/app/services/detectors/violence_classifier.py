"""
ViT violence classifier, ported from the offline project (BTP-HARSH-PROTOTYPE/visual_path.py).
Loaded once per worker process, shared by the 'blood' (confirmation) and 'violence' (whole-frame) detectors.
"""
import logging

import numpy as np

from app.config import settings, torch_device

log = logging.getLogger("violence")


def _convert_timm_to_hf(model_id: str, device: str):
    """The hosamEl1 / jaranohaal checkpoints are timm-style; map their tensors onto a HF ViT."""
    from huggingface_hub import hf_hub_download
    from safetensors.torch import load_file
    from transformers import ViTConfig, ViTForImageClassification, ViTImageProcessor

    model = ViTForImageClassification(ViTConfig.from_pretrained(model_id))
    ckpt = load_file(hf_hub_download(model_id, "model.safetensors"))
    c = {
        "vit.embeddings.cls_token": ckpt["cls_token"],
        "vit.embeddings.position_embeddings": ckpt["pos_embed"],
        "vit.embeddings.patch_embeddings.projection.weight": ckpt["patch_embed.proj.weight"],
        "vit.embeddings.patch_embeddings.projection.bias": ckpt["patch_embed.proj.bias"],
        "vit.layernorm.weight": ckpt["norm.weight"], "vit.layernorm.bias": ckpt["norm.bias"],
        "classifier.weight": ckpt["head.weight"], "classifier.bias": ckpt["head.bias"],
    }
    for i in range(model.config.num_hidden_layers):
        s, t = f"blocks.{i}", f"vit.encoder.layer.{i}"
        c[f"{t}.layernorm_before.weight"], c[f"{t}.layernorm_before.bias"] = ckpt[f"{s}.norm1.weight"], ckpt[f"{s}.norm1.bias"]
        c[f"{t}.layernorm_after.weight"], c[f"{t}.layernorm_after.bias"] = ckpt[f"{s}.norm2.weight"], ckpt[f"{s}.norm2.bias"]
        q, k, v = ckpt[f"{s}.attn.qkv.weight"].chunk(3, dim=0)
        qb, kb, vb = ckpt[f"{s}.attn.qkv.bias"].chunk(3, dim=0)
        a = f"{t}.attention.attention"
        c[f"{a}.query.weight"], c[f"{a}.key.weight"], c[f"{a}.value.weight"] = q, k, v
        c[f"{a}.query.bias"], c[f"{a}.key.bias"], c[f"{a}.value.bias"] = qb, kb, vb
        c[f"{t}.attention.output.dense.weight"], c[f"{t}.attention.output.dense.bias"] = ckpt[f"{s}.attn.proj.weight"], ckpt[f"{s}.attn.proj.bias"]
        c[f"{t}.intermediate.dense.weight"], c[f"{t}.intermediate.dense.bias"] = ckpt[f"{s}.mlp.fc1.weight"], ckpt[f"{s}.mlp.fc1.bias"]
        c[f"{t}.output.dense.weight"], c[f"{t}.output.dense.bias"] = ckpt[f"{s}.mlp.fc2.weight"], ckpt[f"{s}.mlp.fc2.bias"]
    missing, unexpected = model.load_state_dict(c, strict=False)
    if missing or unexpected:
        raise RuntimeError(f"incomplete checkpoint conversion: missing={missing} unexpected={unexpected}")
    model.to(device)
    model.eval()
    processor = ViTImageProcessor.from_pretrained(model_id)
    return model, processor


class ViolenceClassifier:
    _instance: "ViolenceClassifier | None" = None

    def __init__(self) -> None:
        device = torch_device()
        self.device = device
        self.half = device.startswith("cuda") and settings.USE_FP16
        self.models: list[tuple] = []
        errors = []
        for model_id in (m.strip() for m in settings.VIOLENCE_MODELS.split(",") if m.strip()):
            try:
                model, processor = _convert_timm_to_hf(model_id, device)
                labels = {int(k): str(v).strip().lower() for k, v in model.config.id2label.items()}
                positive = [i for i, name in labels.items() if name in {"violence", "violent", "label_1"}]
                positive = positive or ([1] if 1 in labels else [max(labels)])
                self.models.append((model, processor, positive))
                log.info("violence classifier: %s on %s (fp16=%s)", model_id, device, self.half)
            except Exception as e:  # noqa: BLE001
                errors.append(f"{model_id}: {e}")
        if not self.models:
            raise RuntimeError("could not load any violence classifier: " + " | ".join(errors))
        if errors:
            log.warning("some violence classifiers failed: %s", " | ".join(errors))

    @classmethod
    def get(cls) -> "ViolenceClassifier | None":
        """Singleton; returns None (and logs) if the model cannot be loaded, callers then degrade gracefully."""
        if cls._instance is None:
            try:
                cls._instance = cls()
            except Exception as e:  # noqa: BLE001
                log.warning("%s", e)
                cls._instance = False      # type: ignore[assignment]  (do not retry every chunk)
        return cls._instance or None

    def _score_one(self, model, processor, positive: list[int], frames_rgb: list[np.ndarray]) -> list[float]:
        import torch
        scores: list[float] = []
        step = max(1, settings.DETECT_BATCH)
        for start in range(0, len(frames_rgb), step):
            chunk = frames_rgb[start:start + step]
            inputs = processor(images=chunk, return_tensors="pt")
            pixels = inputs["pixel_values"].to(self.device, non_blocking=self.device != "cpu")
            with torch.inference_mode():
                if self.half:
                    with torch.autocast(device_type="cuda", dtype=torch.float16):
                        logits = model(pixel_values=pixels).logits
                else:
                    logits = model(pixel_values=pixels).logits
                probs = torch.softmax(logits.float(), dim=-1)
            take = probs[:, positive].max(dim=1).values
            scores.extend(float(v) for v in take.tolist())
        return scores

    def score(self, frames_rgb: list[np.ndarray]) -> list[float]:
        """Batched forward pass. Several models vote by max, so one blind spot does not drop a gory frame."""
        if not frames_rgb or not self.models:
            return []
        combined: list[float] | None = None
        for model, processor, positive in self.models:
            part = self._score_one(model, processor, positive, frames_rgb)
            combined = part if combined is None else [max(a, b) for a, b in zip(combined, part)]
        return combined or []


def bridge_violence(scores: dict[int, float], floor: float) -> dict[int, float]:
    """Fill a one-frame dip inside a violent stretch so gore does not flash back for 1/5 s."""
    if len(scores) < 2:
        return scores
    out = dict(scores)
    for i, score in scores.items():
        peak = max(scores.get(i - 1, 0.0), scores.get(i + 1, 0.0))
        if peak >= floor and score >= 0.35:
            out[i] = max(score, peak)
    return out


def violence_scores(batch, indexes: list[int]) -> dict[int, float]:
    """Scores for the requested frames; each frame is classified at most once per chunk (batch.cache)."""
    cache: dict[int, float] = batch.cache.setdefault("violence", {})
    todo = [i for i in indexes if i not in cache]
    if todo:
        clf = ViolenceClassifier.get()
        if clf is None:
            return {}
        for i, s in zip(todo, clf.score([batch.frames[i] for i in todo])):
            cache[i] = s
        bridged = bridge_violence({i: cache[i] for i in cache if isinstance(i, int)}, settings.THRESH_VIOLENCE)
        cache.update(bridged)
    return {i: cache[i] for i in indexes if i in cache}
