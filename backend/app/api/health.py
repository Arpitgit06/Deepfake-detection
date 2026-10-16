from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any
import torch
import cv2

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    gpu_available: bool
    gpu_name: str | None = None
    models_loaded: Dict[str, bool]
    llm: Dict[str, Any] = {}
    ai_image: Dict[str, Any] = {}


@router.get("/health", response_model=HealthResponse)
async def health_check():
    gpu_available = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if gpu_available else None

    from app.services.llm_manager import llm_manager
    from app.services.analysis_service import analysis_service
    llm_status = llm_manager.status()
    llm_gpu = llm_status['gpu_offload_supported'] and bool(llm_status['vram'])
    if llm_gpu and not gpu_name:
        gpu_name = llm_status['vram']['name']

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        gpu_available=gpu_available or llm_gpu,
        gpu_name=gpu_name,
        models_loaded={
            "ppg_liveness": analysis_service.ppg_detector is not None,
            "deepfake_detector": analysis_service.image_detector.model is not None,
            "ai_image_detector": analysis_service.ai_image_detector.model is not None,
            "phoneme_viseme": analysis_service.phoneme_viseme_detector.asr_model is not None,
            "financial_threat": analysis_service.financial_detector is not None,
        },
        llm=llm_status,
        ai_image=analysis_service.ai_image_detector.status(),
    )


@router.get("/health/detailed")
async def detailed_health():
    import psutil
    import platform
    from app.services.llm_manager import llm_manager

    return {
        "system": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
        },
        "gpu": {
            "available": torch.cuda.is_available(),
            "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "current_device": torch.cuda.current_device() if torch.cuda.is_available() else None,
            "memory_allocated_mb": round(torch.cuda.memory_allocated() / (1024**2), 2) if torch.cuda.is_available() else 0,
            "memory_reserved_mb": round(torch.cuda.memory_reserved() / (1024**2), 2) if torch.cuda.is_available() else 0,
        },
        "opencv": cv2.__version__,
        "torch": torch.__version__,
        "llm": llm_manager.status(),
    }
