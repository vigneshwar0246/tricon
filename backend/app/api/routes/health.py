"""Read-only health and local model availability checks."""

import ctypes
import sys

from fastapi import APIRouter, Request

from app.core.config import get_settings
from app.schemas.chat import HealthResponse, HealthService
from app.services.llm import OllamaResponseError, OllamaUnavailableError

router = APIRouter(tags=["health"])


@router.get("/diagnostics")
async def diagnostics(request: Request) -> dict[str, object]:
    """Report configured devices and observed runtime facts, not assumed GPU acceleration."""
    import ctranslate2

    stt = request.app.state.stt
    try:
        cuda_devices = ctranslate2.get_cuda_device_count()
    except RuntimeError:
        cuda_devices = 0
    cublas_found = False
    if sys.platform == "win32":
        try:
            ctypes.WinDLL("cublas64_12.dll")
            cublas_found = True
        except OSError:
            pass
    try:
        loaded_models = await request.app.state.ollama.loaded_models()
    except OllamaUnavailableError:
        loaded_models = []
    return {
        "stt": {
            "configured_device": stt.settings.stt_device,
            "compute_type": stt.settings.stt_compute_type,
            "last_successful_device": stt.last_successful_device,
        },
        "cuda": {
            "device_count": cuda_devices,
            "cublas12_found": cublas_found,
            "inference_verified": stt.last_successful_device == "cuda",
            "detail": "CUDA inference has not been verified; cublas64_12.dll is missing. STT remains on CPU."
            if sys.platform == "win32" and not cublas_found else "CUDA inference is verified only after a successful STT request using the CUDA device.",
        },
        "ollama_loaded_models": loaded_models,
    }


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = get_settings()
    llm = request.app.state.ollama
    stt = request.app.state.stt
    tts = request.app.state.tts

    try:
        models = await llm.list_models(timeout_seconds=3.0)
        ollama_reachable = True
        normalized_models = {name if ":" in name else f"{name}:latest" for name in models}
        configured_model = settings.ollama_model if ":" in settings.ollama_model else f"{settings.ollama_model}:latest"
        model_installed = configured_model in normalized_models
        ollama_detail = "Configured model is installed." if model_installed else f"Model '{settings.ollama_model}' is not installed."
    except OllamaUnavailableError:
        ollama_reachable = False
        model_installed = False
        ollama_detail = "Ollama is not reachable at the configured local URL."
    except OllamaResponseError as exc:
        ollama_reachable = True
        model_installed = False
        ollama_detail = str(exc)

    return HealthResponse(
        status="ok" if ollama_reachable and model_installed else "degraded",
        backend=HealthService(available=True, status="ready", detail="FastAPI is responding."),
        ollama=HealthService(
            available=ollama_reachable,
            status="ready" if ollama_reachable else "unavailable",
            model=settings.ollama_model,
            detail=ollama_detail,
        ),
        services={
            "api": True,
            "llm": model_installed if ollama_reachable else False,
            "stt": stt.available,
            "tts": tts.available,
        },
        models={
            "stt": settings.stt_model_path.name,
            "llm": settings.ollama_model,
            "tts": settings.tts_model_path.stem,
            "language": settings.stt_language or "auto",
        },
    )
