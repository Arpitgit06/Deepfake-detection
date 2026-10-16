from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import logging

from app.services.llm_manager import llm_manager
from app.services.analysis_service import analysis_service

router = APIRouter(tags=["llm"])
logger = logging.getLogger(__name__)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    analysis_id: Optional[str] = None


class AskResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    answer: Optional[str]
    model_used: str
    vram_freed_mb: Optional[float] = None


@router.get("/llm/status")
async def llm_status():
    """LLM availability, load state and VRAM usage."""
    return llm_manager.status()


@router.post("/llm/load")
async def llm_load():
    """Explicitly load the Qwen model into VRAM."""
    import asyncio

    ok = await asyncio.to_thread(llm_manager.load_model)
    status = llm_manager.status()
    if not ok:
        raise HTTPException(503, status.get("last_error") or "LLM could not be loaded")
    return status


@router.post("/llm/unload")
async def llm_unload():
    """Unload the model from VRAM and release GPU memory."""
    import asyncio

    return await asyncio.to_thread(llm_manager.unload)


@router.post("/llm/ask", response_model=AskResponse)
async def llm_ask(request: AskRequest):
    """
    Ask the local Qwen model a question. Optionally ground the answer in a
    previous analysis by passing its analysis_id. The model is loaded into
    VRAM for the task and unloaded (VRAM cleaned) afterwards.
    """
    analysis = None
    if request.analysis_id:
        analysis = await analysis_service.get_report(request.analysis_id)
        if not analysis:
            raise HTTPException(404, "Analysis not found")

    answer = await llm_manager.ask(request.question, analysis)
    if answer is None:
        raise HTTPException(
            503,
            llm_manager.status().get("last_error")
            or "LLM unavailable (disabled, not downloaded, or backend missing)",
        )

    return AskResponse(
        answer=answer,
        model_used="qwen3-4b-instruct-2507-q8_0",
        vram_freed_mb=llm_manager._last_unload_vram_mb,
    )
