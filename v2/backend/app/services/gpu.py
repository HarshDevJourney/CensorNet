"""Pin inference to one NVIDIA GPU and turn on the fast CUDA math paths.

Called once when a worker starts, before models are loaded. The API can call
describe() for /health without allocating model weights.
"""
import logging

from app.config import resolve_device, settings, torch_device

log = logging.getLogger("gpu")

_INSTALL = (
    "pip install torch==2.15.0 torchvision==0.29.2 "
    "--index-url https://download.pytorch.org/whl/cu134"
)


def _register_dll_dir(lib: str) -> None:
    import os
    if not lib or not os.path.isdir(lib):
        return
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(lib)
        except OSError:
            pass
    path = os.environ.get("PATH", "")
    if lib.lower() not in path.lower():
        os.environ["PATH"] = lib + os.pathsep + path


def enable_cuda_dlls() -> None:
    """Put CUDA DLLs on the Windows loader path.

    PyTorch ships CUDA 13 (cublas64_13.dll). ONNX Runtime needs those.
    faster-whisper / CTranslate2 still loads CUDA 12 (cublas64_12.dll), which
    comes from the nvidia-cublas-cu12 wheel under site-packages/nvidia.
    """
    import os
    import sys
    try:
        import torch
        _register_dll_dir(os.path.join(os.path.dirname(torch.__file__), "lib"))
    except Exception:  # noqa: BLE001
        pass
    roots = [os.path.join(os.path.dirname(sys.executable), "..", "Lib", "site-packages", "nvidia")]
    try:
        import nvidia
        roots.append(os.path.dirname(nvidia.__file__))
    except Exception:  # noqa: BLE001
        pass
    for root in roots:
        root = os.path.abspath(root)
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, _filenames in os.walk(root):
            if os.path.basename(dirpath).lower() in {"bin", "lib"}:
                _register_dll_dir(dirpath)
                dirnames.clear()
    # ONNX Runtime warns once while it probes the CUDA plugin, then loads it. Keep worker logs readable.
    os.environ.setdefault("ORT_LOG_SEVERITY_LEVEL", "3")


def describe() -> dict:
    """What this process will run on. Safe to call from the API process."""
    info: dict = {
        "requested": settings.DEVICE,
        "resolved": resolve_device(),
        "index": settings.CUDA_DEVICE,
        "fp16": settings.USE_FP16,
        "available": False,
    }
    try:
        import torch
    except Exception as e:  # noqa: BLE001
        info["error"] = str(e)
        return info
    info["torch"] = torch.__version__
    info["torch_cuda"] = torch.version.cuda
    try:
        info["available"] = bool(torch.cuda.is_available())
    except Exception as e:  # noqa: BLE001
        info["error"] = str(e)
        return info
    if not info["available"]:
        return info
    index = settings.CUDA_DEVICE
    info["name"] = torch.cuda.get_device_name(index)
    props = torch.cuda.get_device_properties(index)
    info["vram_mb"] = int(props.total_memory / (1024 * 1024))
    major, minor = torch.cuda.get_device_capability(index)
    info["capability"] = f"{major}.{minor}"
    return info


def configure_runtime(*, require_cuda: bool = False) -> dict:
    """Enable TF32 / cudnn autotune and fail loudly when CUDA was requested but is missing."""
    enable_cuda_dlls()
    info = describe()
    if require_cuda and not info.get("available"):
        raise RuntimeError(
            "DEVICE=cuda but this PyTorch build cannot run on the GPU "
            f"(torch {info.get('torch')}, cuda {info.get('torch_cuda')}). "
            "An RTX 5080 (sm_120) needs the CUDA 13.4 wheel, not the CPU build: "
            + _INSTALL
        )
    if not info.get("available"):
        if info.get("torch_cuda") is None:
            log.warning("PyTorch is a CPU build, so visual models will not use the RTX 5080. %s", _INSTALL)
        else:
            log.warning("CUDA is not available (%s); visual models will run on CPU", info.get("error", "no device"))
        return info

    import torch

    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cudnn.benchmark = True
    try:
        torch.set_float32_matmul_precision("high")
    except Exception:  # noqa: BLE001
        pass
    torch.cuda.set_device(settings.CUDA_DEVICE)
    # Pay CUDA context startup once, not on the first viewer chunk.
    with torch.inference_mode():
        warm = torch.randn(512, 512, device=torch_device())
        warm = warm @ warm
        torch.cuda.synchronize()
        del warm
    log.info(
        "using %s (cuda:%s, %s MB, sm_%s, fp16=%s)",
        info.get("name"),
        settings.CUDA_DEVICE,
        info.get("vram_mb"),
        str(info.get("capability", "")).replace(".", ""),
        settings.USE_FP16,
    )
    return info
