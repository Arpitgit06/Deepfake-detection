"""
LLM Manager for TruthLens AI.

Manages the lifecycle of a local Qwen3-4B (Q8_0 GGUF) model via llama.cpp:

  * load_model()   -> loads the model into VRAM (all layers offloaded to GPU
                      when a CUDA build of llama-cpp-python is installed)
  * generate()     -> runs a chat completion (load is implied on first use)
  * ask()          -> question answering over an analysis result
  * summarize()    -> plain-language summary of detector outputs
  * unload()       -> destroys the llama.cpp context/model, runs gc and
                      (if available) torch.cuda.empty_cache() so VRAM is
                      fully released after the task completes

The manager is intentionally conservative: every method degrades gracefully
(no model file, no llama_cpp package, OOM) so the rest of the API keeps
working when the LLM is unavailable.
"""

import gc
import json
import logging
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMManager:
    """Singleton-style manager that owns the local LLM lifecycle."""

    _instance: Optional["LLMManager"] = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self._model = None  # llama_cpp.Llama instance
        self._lock = threading.RLock()  # serializes load/unload/generate
        self._loaded_at: Optional[float] = None
        self._last_used_at: Optional[float] = None
        self._last_unload_vram_mb: Optional[float] = None
        self._load_error: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Singleton access
    # ------------------------------------------------------------------ #
    @classmethod
    def get(cls) -> "LLMManager":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = LLMManager()
            return cls._instance

    # ------------------------------------------------------------------ #
    # Introspection helpers
    # ------------------------------------------------------------------ #
    def model_path(self) -> Optional[str]:
        path = Path(settings.LLM_MODEL_PATH)
        return str(path) if path.exists() else None

    def model_exists(self) -> bool:
        return Path(settings.LLM_MODEL_PATH).is_file()

    def is_loaded(self) -> bool:
        return self._model is not None

    @staticmethod
    def _gpu_vram_mb() -> Optional[Dict[str, Any]]:
        """Read total/used VRAM via nvidia-smi (works on Windows + Linux)."""
        smi = shutil.which("nvidia-smi")
        if not smi:
            return None
        try:
            out = subprocess.run(
                [smi, "--query-gpu=memory.used,memory.total,name", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if out.returncode == 0:
                used, total, name = out.stdout.strip().splitlines()[0].split(",", 2)
                return {"used_mb": int(used.strip()), "total_mb": int(total.strip()),
                        "free_mb": int(total.strip()) - int(used.strip()), "name": name.strip()}
        except Exception:
            pass
        return None

    def status(self) -> Dict[str, Any]:
        try:
            import llama_cpp  # noqa: F401
            backend_available = True
            backend = getattr(llama_cpp, "__version__", "unknown")
            gpu_offload = bool(llama_cpp.llama_supports_gpu_offload())
        except (ImportError, OSError):
            backend_available = False
            backend = None
            gpu_offload = False

        return {
            "enabled": settings.LLM_ENABLED,
            "backend": "llama.cpp",
            "backend_version": backend,
            "backend_available": backend_available,
            "gpu_offload_supported": gpu_offload,
            "gpu_required": settings.LLM_REQUIRE_GPU,
            "execution_device": ("gpu" if gpu_offload and settings.LLM_N_GPU_LAYERS == -1 else "cpu_or_mixed")
            if self.is_loaded() else None,
            "model_file": settings.LLM_FILENAME,
            "model_path": str(Path(settings.LLM_MODEL_PATH)),
            "model_downloaded": self.model_exists(),
            "model_size_mb": round(Path(settings.LLM_MODEL_PATH).stat().st_size / (1024 * 1024))
            if self.model_exists() else None,
            "loaded": self.is_loaded(),
            "loaded_at": self._loaded_at,
            "n_gpu_layers": settings.LLM_N_GPU_LAYERS,
            "vram": self._gpu_vram_mb(),
            "last_error": self._load_error,
        }

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def load_model(self) -> bool:
        """Load the GGUF model. All layers go to VRAM when n_gpu_layers=-1."""
        with self._lock:
            return self._load_model_locked()

    def _load_model_locked(self) -> bool:
        if self._model is not None:
            return True

        if not settings.LLM_ENABLED:
            self._load_error = "LLM disabled via LLM_ENABLED setting"
            return False

        if not self.model_exists():
            self._load_error = (
                f"Model file not found at '{settings.LLM_MODEL_PATH}'. "
                f"Run setup.bat (or backend/download_llm.py) to download "
                f"{settings.LLM_FILENAME} into the project folder."
            )
            logger.warning(self._load_error)
            return False

        try:
            import llama_cpp
        except (ImportError, OSError):
            self._load_error = (
                "llama-cpp-python is not installed. Install it with pip "
                "(setup.bat installs a CUDA build)."
            )
            logger.warning(self._load_error)
            return False

        if settings.LLM_REQUIRE_GPU:
            if not llama_cpp.llama_supports_gpu_offload():
                self._load_error = "Qwen requires a CUDA-enabled llama-cpp-python build; CPU fallback is disabled."
                return False
            if settings.LLM_N_GPU_LAYERS != -1:
                self._load_error = "Set LLM_N_GPU_LAYERS=-1 to offload every Qwen layer; CPU/mixed loading is disabled."
                return False
            vram = self._gpu_vram_mb()
            # Conservative allowance for Qwen3-4B F16 KV cache, compute buffers,
            # CUDA context and desktop usage, beyond the Q8 weight file.
            required_mb = Path(settings.LLM_MODEL_PATH).stat().st_size / (1024 ** 2) + 1024 + settings.LLM_N_CTX * 0.15
            if not vram:
                self._load_error = "Cannot verify NVIDIA VRAM availability. Check nvidia-smi and your GPU driver; CPU fallback is disabled."
                return False
            if vram['free_mb'] < required_mb:
                self._load_error = (
                    f"Insufficient free GPU VRAM: {vram['free_mb']} MiB available; "
                    f"about {required_mb:.0f} MiB required. Close GPU applications or reduce LLM_N_CTX. "
                    "CPU fallback is disabled."
                )
                return False

        try:
            t0 = time.time()
            logger.info(
                f"Loading LLM '{settings.LLM_FILENAME}' "
                f"(n_gpu_layers={settings.LLM_N_GPU_LAYERS}, ctx={settings.LLM_N_CTX})..."
            )
            self._model = llama_cpp.Llama(
                model_path=str(Path(settings.LLM_MODEL_PATH)),
                n_gpu_layers=settings.LLM_N_GPU_LAYERS,  # -1 = all layers in VRAM
                n_ctx=settings.LLM_N_CTX,
                main_gpu=0,
                split_mode=llama_cpp.LLAMA_SPLIT_MODE_NONE,
                offload_kqv=True,
                flash_attn=True,
                use_mmap=False,
                verbose=settings.LLM_VERBOSE,
            )
            self._loaded_at = time.time()
            self._last_used_at = time.time()
            self._load_error = None
            logger.info(f"LLM loaded in {time.time() - t0:.1f}s")
            return True
        except Exception as e:
            self._model = None
            self._load_error = f"Failed to load LLM: {e}"
            logger.error(self._load_error)
            return False

    def unload(self) -> Dict[str, Any]:
        """
        Unload the model and release VRAM. Destroys the llama.cpp context,
        drops references, forces a gc cycle and (with CUDA torch) empties
        the CUDA allocator cache.
        """
        with self._lock:
            if self._model is None:
                return {"unloaded": True, "was_loaded": False, "vram_freed_mb": 0}

            vram_before = self._gpu_vram_mb()
            t0 = time.time()
            try:
                self._model.close()
                self._model = None
                gc.collect()
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        torch.cuda.ipc_collect()
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Error while unloading LLM: {e}")

            vram_after = self._gpu_vram_mb()
            self._last_unload_vram_mb = (
                (vram_before["used_mb"] - vram_after["used_mb"]) if vram_before and vram_after else None
            )
            self._loaded_at = None
            self._last_used_at = None
            logger.info(
                f"LLM unloaded in {time.time() - t0:.1f}s "
                f"(VRAM released: {self._last_unload_vram_mb} MB)"
            )
            return {
                "unloaded": True,
                "was_loaded": True,
                "unload_time_ms": round((time.time() - t0) * 1000, 1),
                "vram_freed_mb": self._last_unload_vram_mb,
                "vram": vram_after,
            }

    def maybe_idle_unload(self) -> None:
        """Unload if the idle window has elapsed (0 = unload immediately)."""
        if self._model is None:
            return
        idle = settings.LLM_IDLE_UNLOAD_SECONDS
        if idle <= 0:
            self.unload()
            return
        if self._last_used_at and (time.time() - self._last_used_at) >= idle:
            self.unload()

    # ------------------------------------------------------------------ #
    # Generation
    # ------------------------------------------------------------------ #
    def _chat_sync(self, messages, max_tokens: int, temperature: float) -> str:
        """Blocking chat completion (call via asyncio.to_thread)."""
        with self._lock:
            if not self.load_model():
                raise RuntimeError(self._load_error or "LLM unavailable")
            self._last_used_at = time.time()
            response = self._model.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.8,
                repeat_penalty=1.05,
            )
            text = (response.get("choices") or [{}])[0].get("message", {}).get("content", "")
            return (text or "").strip()

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Optional[str]:
        """Chat completion with the Qwen model. Returns None on failure."""
        import asyncio

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            return await asyncio.to_thread(
                self._chat_sync,
                messages,
                max_tokens or settings.LLM_MAX_TOKENS,
                temperature if temperature is not None else settings.LLM_TEMPERATURE,
            )
        except Exception as e:
            self._load_error = str(e)
            logger.error(f"LLM generation failed: {e}")
            return None
        finally:
            # Task complete -> release VRAM (policy-driven)
            await asyncio.to_thread(self.maybe_idle_unload)

    # ------------------------------------------------------------------ #
    # High-level tasks
    # ------------------------------------------------------------------ #
    ANALYST_SYSTEM_PROMPT = (
        "You are the AI security analyst of TruthLens, a deepfake and scam "
        "detection platform. You are given the JSON output of automated "
        "detectors (image deepfake, video liveness, phoneme-viseme sync, "
        "financial threat analysis). Write a concise, plain-language "
        "assessment for a non-technical user. Rules: state the verdict "
        "first, then cite the strongest evidence from the data, then give "
        "one recommended action. Never invent facts that are not in the "
        "data. Use at most 5 short sentences. No markdown headers."
        " No face only means face-specific checks do not apply: use the whole-image "
        "ai_generated_image result for AI generation. Respect inconclusive/unavailable "
        "results and never call them real or clean. An unsigned metadata declaration "
        "is a claim, not verified provenance; AI editing does not imply the entire "
        "image was generated. Model scores are not proof or calibrated certainty."
    )

    ASK_SYSTEM_PROMPT = (
        "You are the AI assistant of TruthLens, a deepfake and scam "
        "detection platform. Answer the user's question about the given "
        "analysis result. Be concise (at most 6 sentences), factual, and "
        "base your answer strictly on the provided analysis data. "
        "No markdown headers."
        " Whole-image AI detection does not require a face. Do not convert missing "
        "or inconclusive results into authentic/clean claims. Metadata may declare "
        "AI editing without establishing complete AI generation."
    )

    @staticmethod
    def _compact_analysis(analysis: Dict[str, Any]) -> str:
        """Trim heavy fields (base64 heatmaps, long signals) before prompting."""
        try:
            slim = json.loads(json.dumps(analysis))
        except Exception:
            return str(analysis)[:4000]
        results = slim.get("results") or {}
        for value in results.values():
            if isinstance(value, dict):
                value.pop("heatmap_base64", None)
                value.pop("heatmap", None)
                value.pop("raw_signal", None)
                value.pop("frame_scores", None)
        slim.pop("results", None)
        slim["results"] = results
        return json.dumps(slim)[:6000]

    async def summarize(self, analysis: Dict[str, Any]) -> Optional[str]:
        """Plain-language summary of a completed analysis."""
        if not settings.LLM_ENABLED:
            return None
        prompt = (
            "Summarize this TruthLens analysis result for the user.\n\n"
            f"Analysis JSON:\n{self._compact_analysis(analysis)}"
        )
        return await self.generate(self.ANALYST_SYSTEM_PROMPT, prompt)

    async def ask(
        self, question: str, analysis: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Answer a user question, optionally grounded in an analysis result."""
        if not settings.LLM_ENABLED:
            return None
        context = self._compact_analysis(analysis) if analysis else "No analysis data provided."
        prompt = (
            f"Analysis JSON:\n{context}\n\nUser question: {question}"
        )
        return await self.generate(
            self.ASK_SYSTEM_PROMPT, prompt, max_tokens=384, temperature=0.4
        )


# Module-level convenience singleton
llm_manager = LLMManager.get()
