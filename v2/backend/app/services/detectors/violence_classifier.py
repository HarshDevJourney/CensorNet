"""
ViT violence classifier, ported from the offline project (BTP-HARSH-PROTOTYPE/visual_path.py).
Loaded once per worker process, shared by the 'blood' (confirmation) and 'violence' (whole-frame) detectors.
"""
import logging

import numpy as np

from app.config import resolve_device, settings

log = logging.getLogger("violence")


def _convert_timm_to_hf(model_id: str, device: str):
    """The hosamEl1 / jaranohaal checkpoints are timm-style; map their tensors onto a HF ViT."""
    from huggingface_hub import hf_hub_download
    from safetensors.torch import load_file
    from transformers import ViTConfig, ViTForImageClassification, ViTImageProcessor, pipeline

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
    processor = ViTImageProcessor.from_pretrained(model_id)
    return pipeline("image-classification", model=model, image_processor=processor,
                    device=0 if device == "cuda" else -1)


class ViolenceClassifier:
    _instance: "ViolenceClassifier | None" = None

    def __init__(self) -> None:
        device = resolve_device()
        self.pipe = None
        errors = []
        for model_id in (m.strip() for m in settings.VIOLENCE_MODELS.split(",") if m.strip()):
            try:
                self.pipe = _convert_timm_to_hf(model_id, device)
                log.info("violence classifier: %s on %s", model_id, device)
                break
            except Exception as e:  # noqa: BLE001
                errors.append(f"{model_id}: {e}")
        if self.pipe is None:
            raise RuntimeError("could not load any violence classifier: " + " | ".join(errors))

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

    def score(self, frames_rgb: list[np.ndarray]) -> list[float]:
        from PIL import Image
        if not frames_rgb:
            return []
        images = [Image.fromarray(f) for f in frames_rgb]
        out = self.pipe(images, batch_size=min(8, len(images)))
        scores = []
        for preds in out:
            vio = [p for p in preds if str(p["label"]).strip().lower() in {"violence", "violent"}]
            if not vio:
                vio = [p for p in preds if str(p["label"]).upper() == "LABEL_1"]
            scores.append(max((float(p["score"]) for p in vio), default=0.0))
        return scores


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
    return {i: cache[i] for i in indexes if i in cache}
