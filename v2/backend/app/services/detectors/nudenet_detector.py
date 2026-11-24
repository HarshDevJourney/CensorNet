import logging

from app.config import resolve_device, settings
from app.services.detection import FrameBatch, FrameHit
from app.services.policy import POLICY

log = logging.getLogger("nudenet")


class NudeNetDetector:
    name = "nudenet"

    def load(self) -> None:
        import os

        from app.services.gpu import enable_cuda_dlls
        enable_cuda_dlls()

        import nudenet
        import onnxruntime as ort
        from nudenet import NudeDetector          # heavy import: once per worker process

        # This NudeNet build comments out `providers=` inside InferenceSession, so the
        # argument is ignored. Rebuild the session ourselves and pin it to the 5080.
        model_path = settings.NUDENET_MODEL_PATH or os.path.join(
            os.path.dirname(nudenet.__file__), "320n.onnx")
        wanted: list = ["CPUExecutionProvider"]
        if resolve_device() == "cuda":
            wanted.insert(0, ("CUDAExecutionProvider", {
                "device_id": settings.CUDA_DEVICE,
                "arena_extend_strategy": "kSameAsRequested",
                "cudnn_conv_algo_search": "HEURISTIC",
            }))
        options = ort.SessionOptions()
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        real_session = ort.InferenceSession

        def _session(path, sess_options=None, providers=None, **kwargs):  # noqa: ANN001
            # NudeNet's constructor drops the providers argument. Force the GPU session here.
            return real_session(path, sess_options=options, providers=wanted, **kwargs)

        ort.InferenceSession = _session
        try:
            self.model = NudeDetector(model_path=model_path, inference_resolution=settings.NUDENET_RESOLUTION)
        finally:
            ort.InferenceSession = real_session
        active = self.model.onnx_session.get_providers()
        log.info("nudenet providers: %s", active)
        if resolve_device() == "cuda" and "CUDAExecutionProvider" not in active:
            raise RuntimeError(
                "NudeNet is on CPU. Install the GPU runtime: "
                "pip uninstall -y onnxruntime && pip install onnxruntime-gpu"
            )

    def detect(self, batch: FrameBatch) -> list[FrameHit]:
        n, h, w, _ = batch.frames.shape
        if n == 0:
            return []
        # NudeNet takes arrays in cv2.imread order (BGR); our frames are RGB.
        bgr = batch.bgr()
        frames = [bgr[i] for i in range(n)]
        hits: list[FrameHit] = []
        for i, dets in enumerate(self.model.detect_batch(frames, batch_size=settings.DETECT_BATCH)):
            for d in dets:
                if d["class"] not in POLICY:
                    continue
                x, y, bw, bh = d["box"]                      # pixels of the analysis frame
                hits.append(FrameHit(i, d["class"], float(d["score"]), (x / w, y / h, bw / w, bh / h)))
        return hits
