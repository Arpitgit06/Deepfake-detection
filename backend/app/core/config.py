from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=True)

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
    PHONEME_MODEL_PATH: str = os.getenv("PHONEME_MODEL_PATH", "./models/wav2vec2_phoneme")
    VISME_MODEL_PATH: str = os.getenv("VISME_MODEL_PATH", "./models/viseme_classifier.onnx")

    # Detection Thresholds
    PPG_CONFIDENCE_THRESHOLD: float = 0.75
    PHONEME_VISME_THRESHOLD: float = 0.70
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


settings = Settings()