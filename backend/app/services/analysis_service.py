import time
import uuid
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

from app.detectors.ppg_liveness import PPGLivenessDetector
from app.detectors.phoneme_viseme import PhonemeVisemeDetector
from app.detectors.financial_threat import FinancialThreatDetector
from app.detectors.deepfake_image import DeepfakeImageDetector
from app.detectors.ai_generated_image import AIGeneratedImageDetector
from app.services.llm_manager import llm_manager
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AnalysisJob:
    analysis_id: str
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AnalysisService:
    def __init__(self):
        self.jobs: Dict[str, AnalysisJob] = {}
        self.ppg_detector = PPGLivenessDetector()
        self.phoneme_viseme_detector = PhonemeVisemeDetector()
        self.financial_detector = FinancialThreatDetector()
        self.image_detector = DeepfakeImageDetector()
        self.ai_image_detector = AIGeneratedImageDetector()

    async def analyze_image(
        self,
        image_bytes: bytes,
        analysis_id: str,
        return_heatmap: bool = False,
        sensitivity: float = 0.5,
    ) -> Dict[str, Any]:
        start_time = time.time()
        job = self._create_job(analysis_id)

        try:
            # Full-image classification always runs, with or without faces.
            ai_result = await self.ai_image_detector.detect(image_bytes)
            result = await self.image_detector.detect(
                image_bytes=image_bytes,
                sensitivity=sensitivity,
                return_heatmap=return_heatmap,
            )

            processing_time = (time.time() - start_time) * 1000

            # Format response
            response = self._format_response(
                analysis_id=analysis_id,
                results={"ai_generated_image": ai_result, "image_deepfake": result},
                processing_time_ms=processing_time,
            )

            # Local Qwen LLM explains the result in plain language (VRAM is
            # loaded for the task and released afterwards)
            response = await self._attach_llm_summary(response)

            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.result = response
            return response

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            logger.error(f"Image analysis failed: {e}")
            raise

    async def analyze_video(
        self,
        video_bytes: bytes,
        analysis_id: str,
        enable_ppg: bool = True,
        enable_phoneme_viseme: bool = True,
        sample_rate: int = 5,
    ) -> Dict[str, Any]:
        start_time = time.time()
        job = self._create_job(analysis_id)

        try:
            results = {}
            all_explanations = []
            all_confidences = []

            # Run PPG Liveness Detection
            if enable_ppg:
                logger.info("Running PPG liveness detection...")
                ppg_result = await self.ppg_detector.detect(video_bytes, sample_rate)
                results["ppg_liveness"] = ppg_result
                all_explanations.extend(ppg_result.get("explanations", []))
                all_confidences.append(ppg_result.get("confidence", 0))

            # Run Phoneme-Viseme Synchronization
            if enable_phoneme_viseme:
                logger.info("Running phoneme-viseme synchronization...")
                pv_result = await self.phoneme_viseme_detector.detect(video_bytes)
                results["phoneme_viseme_sync"] = pv_result
                all_explanations.extend(pv_result.get("explanations", []))
                all_confidences.append(pv_result.get("confidence", 0))

            # Run frame-level deepfake detection
            logger.info("Running frame-level deepfake detection...")
            df_result = await self.image_detector.detect_video_frames(
                video_bytes, sample_rate=sample_rate
            )
            results["frame_deepfake"] = df_result
            all_explanations.extend(df_result.get("explanations", []))
            all_confidences.append(df_result.get("confidence", 0))

            processing_time = (time.time() - start_time) * 1000

            # Compute overall confidence (weighted average)
            overall_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0

            response = self._format_response(
                analysis_id=analysis_id,
                results=results,
                processing_time_ms=processing_time,
                overall_confidence=overall_confidence,
            )

            response = await self._attach_llm_summary(response)

            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.result = response
            return response

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            logger.error(f"Video analysis failed: {e}")
            raise

    async def analyze_text(
        self,
        text: str,
        analysis_id: str,
        language: Optional[str] = None,
        extract_entities: bool = True,
        check_threat_intel: bool = True,
    ) -> Dict[str, Any]:
        start_time = time.time()
        job = self._create_job(analysis_id)

        try:
            result = await self.financial_detector.detect(
                text=text,
                language=language,
                extract_entities=extract_entities,
                check_threat_intel=check_threat_intel,
            )

            processing_time = (time.time() - start_time) * 1000

            response = self._format_response(
                analysis_id=analysis_id,
                results={"financial_threat": result},
                processing_time_ms=processing_time,
            )

            response = await self._attach_llm_summary(response)

            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.result = response
            return response

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            logger.error(f"Text analysis failed: {e}")
            raise

    async def analyze_multimodal(
        self,
        analysis_id: str,
        image_bytes: Optional[bytes] = None,
        video_bytes: Optional[bytes] = None,
        audio_bytes: Optional[bytes] = None,
        text_content: Optional[str] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()
        job = self._create_job(analysis_id)

        try:
            results = {}
            all_explanations = []
            all_confidences = []

            # Analyze each modality
            tasks = []

            if image_bytes:
                tasks.append(("ai_generated_image", self.ai_image_detector.detect(image_bytes)))
                tasks.append(("image_deepfake", self.image_detector.detect(image_bytes)))

            if video_bytes:
                tasks.append(("video_ppg", self.ppg_detector.detect(video_bytes)))
                tasks.append(("video_phoneme_viseme", self.phoneme_viseme_detector.detect(video_bytes)))
                tasks.append(("video_deepfake", self.image_detector.detect_video_frames(video_bytes)))

            if text_content:
                tasks.append(("financial_threat", self.financial_detector.detect(text_content)))

            # Run all detections in parallel
            for name, coro in tasks:
                try:
                    result = await coro
                    results[name] = result
                    all_explanations.extend(result.get("explanations", []))
                    all_confidences.append(result.get("confidence", 0))
                except Exception as e:
                    logger.error(f"Detection {name} failed: {e}")
                    results[name] = {"error": str(e), "confidence": 0}

            processing_time = (time.time() - start_time) * 1000

            overall_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0

            response = self._format_response(
                analysis_id=analysis_id,
                results=results,
                processing_time_ms=processing_time,
                overall_confidence=overall_confidence,
            )

            response = await self._attach_llm_summary(response)

            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.result = response
            return response

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            logger.error(f"Multimodal analysis failed: {e}")
            raise

    def _create_job(self, analysis_id: str) -> AnalysisJob:
        job = AnalysisJob(analysis_id=analysis_id)
        self.jobs[analysis_id] = job
        return job

    def _format_response(
        self,
        analysis_id: str,
        results: Dict[str, Any],
        processing_time_ms: float,
        overall_confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        # Collect all explanations
        all_explanations = []
        for detector_name, result in results.items():
            if isinstance(result, dict) and "explanations" in result:
                for exp in result["explanations"]:
                    exp["detector"] = detector_name
                    all_explanations.append(exp)

        # Confidence in the REAL class is not evidence of a fake. Aggregate
        # explicit detector verdicts, preserving abstention and missing checks.
        verdicts = [self._detector_verdict(r) for r in results.values() if isinstance(r, dict)]
        active = [v for v in verdicts if v != 'not_applicable']
        status = ('suspicious' if 'suspicious' in active else
                  'clean' if active and all(v == 'clean' for v in active) else 'inconclusive')
        # Keep confidence for API compatibility, but only from detectors agreeing
        # with the verdict. Metadata has no fabricated numerical confidence.
        confidences = [r.get('confidence', 0) for r in results.values()
                       if isinstance(r, dict) and self._detector_verdict(r) == status
                       and not r.get('metadata_evidence')]
        overall_confidence = max(confidences, default=0) if status != 'inconclusive' else 0

        return {
            "analysis_id": analysis_id,
            "status": status,
            "confidence": round(overall_confidence, 4),
            "results": results,
            "explanations": all_explanations,
            "processing_time_ms": round(processing_time_ms, 2),
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _detector_verdict(result):
        explicit = result.get('status')
        if explicit in {'suspicious', 'clean', 'not_applicable'}:
            return explicit
        if explicit in {'error', 'unavailable', 'inconclusive'} or result.get('error'):
            return 'inconclusive'
        if not result.get('confidence'):
            return 'inconclusive'
        for flag in ('is_deepfake', 'is_threat'):
            if isinstance(result.get(flag), bool):
                return 'suspicious' if result[flag] else 'clean'
        for flag in ('is_synchronized', 'has_pulse'):
            if isinstance(result.get(flag), bool):
                return 'clean' if result[flag] else 'suspicious'
        return 'inconclusive'

    async def _attach_llm_summary(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ask the local Qwen LLM for a plain-language summary of the analysis.
        The model is loaded into VRAM for this task and unloaded again
        afterwards (VRAM is fully released).
        """
        if not settings.LLM_ENABLED:
            return response
        try:
            summary = await llm_manager.summarize(response)
            if summary:
                response["llm_summary"] = summary
                response["explanations"].append({
                    "type": "llm_summary",
                    "message": summary,
                    "severity": "info",
                    "detector": "qwen3_4b_llm",
                    "details": {
                        "model": "Qwen3-4B-Instruct-2507 (Q8_0)",
                        "backend": "llama.cpp",
                    },
                })
        except Exception as e:
            logger.warning(f"LLM summary failed (continuing without it): {e}")
        finally:
            # Task complete -> free VRAM
            await asyncio.to_thread(llm_manager.unload)
        return response

    async def get_status(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        job = self.jobs.get(analysis_id)
        if not job:
            return None
        return {
            "analysis_id": job.analysis_id,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error": job.error,
        }

    async def get_report(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        job = self.jobs.get(analysis_id)
        if not job or not job.result:
            return None
        return job.result


# Shared singleton used by the analyze + llm API routers
analysis_service = AnalysisService()
