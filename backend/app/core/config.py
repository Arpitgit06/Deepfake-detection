from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import List, Optional
from pathlib import Path
from pydantic import field_validator, Field, AliasChoices
import os

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=(BACKEND_DIR.parent / '.env', BACKEND_DIR / '.env'),
        case_sensitive=True, extra='ignore',
    )

    # App
    APP_NAME: str = "TruthLens AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Model Paths
    MODEL_DIR: str = os.getenv("MODEL_DIR", "./models")
    PPG_MODEL_PATH: str = os.getenv("PPG_MODEL_PATH", "./models/ppg_liveness.onnx")
    DEEPFAKE_MODEL_PATH: str = os.getenv("DEEPFAKE_MODEL_PATH", "./models/deepfake_detector.onnx")
    # Trained weights for the EfficientNet-B0 deepfake classifier (state dict).
    # When absent, the detector falls back to the heuristic algorithm ensemble.
    DEEPFAKE_MODEL_WEIGHTS: str = os.getenv(
        "DEEPFAKE_MODEL_WEIGHTS", "./models/deepfake_detector.pt"
    )
    AI_IMAGE_MODEL_PATH: str = './models/ai_image_detector'
    AI_IMAGE_MODEL_ID: str = 'dima806/ai_vs_real_image_detection'
    AI_IMAGE_MODEL_REVISION: str = '5d647683672ffd0080441f4e8b4345934c44cc61'
    AI_IMAGE_REQUIRE_GPU: bool = True
    # An abstention band: softmax scores are not calibrated certainty.
    AI_IMAGE_FAKE_THRESHOLD: float = Field(default=0.7, ge=0.5, le=1.0)
    AI_IMAGE_REAL_THRESHOLD: float = Field(default=0.3, ge=0.0, le=0.5)
    PHONEME_MODEL_PATH: str = os.getenv("PHONEME_MODEL_PATH", "./models/wav2vec2_phoneme")
    VISEME_MODEL_PATH: str = Field(default='./models/viseme_classifier.onnx',
                                  validation_alias=AliasChoices('VISEME_MODEL_PATH', 'VISME_MODEL_PATH'))

    # LLM (Qwen3-4B-Instruct-2507, Q8_0 GGUF via llama.cpp)
    # Downloaded into the project folder by setup.bat / download_llm.py
    LLM_ENABLED: bool = os.getenv("LLM_ENABLED", "true").lower() in ("1", "true", "yes")
    LLM_MODEL_PATH: str = os.getenv(
        "LLM_MODEL_PATH", "./models/llm/Qwen3-4B-Instruct-2507-Q8_0.gguf"
    )
    LLM_REPO_ID: str = os.getenv("LLM_REPO_ID", "unsloth/Qwen3-4B-Instruct-2507-GGUF")
    LLM_FILENAME: str = os.getenv("LLM_FILENAME", "Qwen3-4B-Instruct-2507-Q8_0.gguf")
    # -1 = offload all layers to GPU (VRAM); 0 = CPU only
    LLM_N_GPU_LAYERS: int = int(os.getenv("LLM_N_GPU_LAYERS", "-1"))
    LLM_REQUIRE_GPU: bool = True
    LLM_VERBOSE: bool = False
    LLM_N_CTX: int = int(os.getenv("LLM_N_CTX", "4096"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "512"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    # Seconds to keep the model in VRAM after a task (0 = unload immediately)
    LLM_IDLE_UNLOAD_SECONDS: int = int(os.getenv("LLM_IDLE_UNLOAD_SECONDS", "0"))

    # Detection Thresholds
    PPG_CONFIDENCE_THRESHOLD: float = 0.75
    PHONEME_VISEME_THRESHOLD: float = Field(default=0.70,
                                          validation_alias=AliasChoices('PHONEME_VISEME_THRESHOLD', 'PHONEME_VISME_THRESHOLD'))
    DEEPFAKE_THRESHOLD: float = 0.65
    FINANCIAL_THREAT_THRESHOLD: float = 0.60

    # External APIs
    THREAT_INTEL_API_KEY: Optional[str] = os.getenv("THREAT_INTEL_API_KEY")
    VIRUSTOTAL_API_KEY: Optional[str] = os.getenv("VIRUSTOTAL_API_KEY")
    ABUSEIPDB_API_KEY: Optional[str] = os.getenv("ABUSEIPDB_API_KEY")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # File Upload
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]
    ALLOWED_VIDEO_TYPES: List[str] = ["video/mp4", "video/webm", "video/quicktime"]
    ALLOWED_AUDIO_TYPES: List[str] = ["audio/wav", "audio/mp3", "audio/m4a"]

    # Logging
    LOG_LEVEL: str = "INFO"

    @field_validator('MODEL_DIR', 'PPG_MODEL_PATH', 'DEEPFAKE_MODEL_PATH',
                     'DEEPFAKE_MODEL_WEIGHTS', 'PHONEME_MODEL_PATH',
                     'VISEME_MODEL_PATH', 'LLM_MODEL_PATH', 'AI_IMAGE_MODEL_PATH')
    @classmethod
    def resolve_model_path(cls, value: str) -> str:
        path = Path(value).expanduser()
        return str(path if path.is_absolute() else (BACKEND_DIR / path).resolve())


settings = Settings()
