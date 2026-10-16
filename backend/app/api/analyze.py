from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
import logging

from app.services.analysis_service import AnalysisService, analysis_service
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class AnalysisResult(BaseModel):
    analysis_id: str
    status: str
    results: Dict[str, Any]
    confidence: float
    explanations: List[Dict[str, Any]]
    processing_time_ms: float
    timestamp: str
    llm_summary: Optional[str] = None


class ImageAnalysisRequest(BaseModel):
    analysis_id: Optional[str] = None
    return_heatmap: bool = False
    sensitivity: float = Field(default=0.5, ge=0.0, le=1.0)


class VideoAnalysisRequest(BaseModel):
    analysis_id: Optional[str] = None
    enable_ppg: bool = True
    enable_phoneme_viseme: bool = True
    sample_rate: int = Field(default=5, ge=1, le=30)  # frames per second to analyze


class TextAnalysisRequest(BaseModel):
    text: str
    analysis_id: Optional[str] = None
    language: Optional[str] = None
    extract_entities: bool = True
    check_threat_intel: bool = True


class MultimodalAnalysisRequest(BaseModel):
    analysis_id: Optional[str] = None
    text_content: Optional[str] = None


@router.post("/analyze/image", response_model=AnalysisResult)
async def analyze_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    return_heatmap: bool = Form(False),
    sensitivity: float = Form(0.5),
):
    """Analyze an image for deepfake/manipulation indicators."""
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    analysis_id = str(uuid.uuid4())
    logger.info(f"Starting image analysis: {analysis_id}")

    try:
        contents = await file.read()
        result = await analysis_service.analyze_image(
            image_bytes=contents,
            analysis_id=analysis_id,
            return_heatmap=return_heatmap,
            sensitivity=sensitivity,
        )
        return result
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@router.post("/analyze/video", response_model=AnalysisResult)
async def analyze_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    enable_ppg: bool = Form(True),
    enable_phoneme_viseme: bool = Form(True),
    sample_rate: int = Form(5),
):
    """Analyze a video with PPG liveness and phoneme-viseme synchronization."""
    if file.content_type not in settings.ALLOWED_VIDEO_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    analysis_id = str(uuid.uuid4())
    logger.info(f"Starting video analysis: {analysis_id}")

    try:
        contents = await file.read()
        result = await analysis_service.analyze_video(
            video_bytes=contents,
            analysis_id=analysis_id,
            enable_ppg=enable_ppg,
            enable_phoneme_viseme=enable_phoneme_viseme,
            sample_rate=sample_rate,
        )
        return result
    except Exception as e:
        logger.error(f"Video analysis failed: {e}")
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@router.post("/analyze/text", response_model=AnalysisResult)
async def analyze_text(request: TextAnalysisRequest):
    """Analyze text for financial scam indicators and social engineering tactics."""
    analysis_id = request.analysis_id or str(uuid.uuid4())
    logger.info(f"Starting text analysis: {analysis_id}")

    try:
        result = await analysis_service.analyze_text(
            text=request.text,
            analysis_id=analysis_id,
            language=request.language,
            extract_entities=request.extract_entities,
            check_threat_intel=request.check_threat_intel,
        )
        return result
    except Exception as e:
        logger.error(f"Text analysis failed: {e}")
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@router.post("/analyze/multimodal", response_model=AnalysisResult)
async def analyze_multimodal(
    background_tasks: BackgroundTasks,
    image: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    text_content: Optional[str] = Form(None),
    analysis_id: Optional[str] = Form(None),
):
    """Combined multimodal analysis."""
    analysis_id = analysis_id or str(uuid.uuid4())
    logger.info(f"Starting multimodal analysis: {analysis_id}")

    try:
        image_bytes = await image.read() if image else None
        video_bytes = await video.read() if video else None
        audio_bytes = await audio.read() if audio else None

        result = await analysis_service.analyze_multimodal(
            analysis_id=analysis_id,
            image_bytes=image_bytes,
            video_bytes=video_bytes,
            audio_bytes=audio_bytes,
            text_content=text_content,
        )
        return result
    except Exception as e:
        logger.error(f"Multimodal analysis failed: {e}")
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@router.get("/analyze/{analysis_id}/status")
async def get_analysis_status(analysis_id: str):
    """Get the status of an analysis job."""
    status = await analysis_service.get_status(analysis_id)
    if not status:
        raise HTTPException(404, "Analysis not found")
    return status


@router.get("/analyze/{analysis_id}/report")
async def get_analysis_report(analysis_id: str):
    """Get detailed analysis report."""
    report = await analysis_service.get_report(analysis_id)
    if not report:
        raise HTTPException(404, "Report not found")
    return report
