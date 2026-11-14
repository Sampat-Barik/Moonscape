"""Configuration settings for lunar hazard detection and ML inference."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class HazardSettings(BaseSettings):
    """Settings governing lunar hazard ML inference, models, and limits."""

    # Base models directory
    MODEL_DIR: Path = Path(__file__).resolve().parent.parent.parent / "data" / "models"
    
    # Model file paths (configurable via environment variables)
    HAZARD_MODEL_PATH: str = os.getenv("HAZARD_MODEL_PATH", "")
    HAZARD_METADATA_PATH: str = os.getenv("HAZARD_METADATA_PATH", "")
    
    # Inference parameters
    DEFAULT_CONFIDENCE_THRESHOLD: float = 0.50
    MIN_CONFIDENCE_THRESHOLD: float = 0.10
    MAX_CONFIDENCE_THRESHOLD: float = 0.99
    
    # Image constraints (Hardware-optimized for 16 GB system RAM & 8 GB VRAM)
    MAX_IMAGE_WIDTH: int = 4096
    MAX_IMAGE_HEIGHT: int = 4096
    MAX_IMAGE_BYTES: int = 25 * 1024 * 1024  # 25 MB max raw image upload
    DEFAULT_TARGET_SIZE: tuple = (512, 512)
    
    # Device preference: auto-detect CUDA if PyTorch/ONNX runtime has it
    PREFERRED_DEVICE: str = os.getenv("HAZARD_DEVICE", "cuda")  # "cuda" or "cpu"

    model_config = {
        "env_prefix": "MOONSCAPE_HAZARD_",
        "extra": "ignore",
    }


hazard_settings = HazardSettings()
