"""Application settings and environment configuration."""

import sys
from pathlib import Path
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure the root workspace is always in Python's module search path
_current_dir = Path(__file__).resolve().parent
_possible_roots = [_current_dir.parent.parent, _current_dir.parent.parent.parent]
for r in _possible_roots:
    if (r / "maths").exists() and str(r) not in sys.path:
        sys.path.insert(0, str(r))
        break


class Settings(BaseSettings):
    """Central configuration for the Moonscape backend application."""

    # Project Information
    PROJECT_NAME: str = "Moonscape Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    DEBUG: bool = True

    # Server Bindings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:4173",
        "http://localhost:8080",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8000",
    ]

    # Data Directories and File Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DEM_DATA_PATH: Path = DATA_DIR / "sample_dem.tif"
    SITES_DATA_PATH: Path = DATA_DIR / "sites.json"

    @property
    def resolved_dem_path(self) -> Path:
        if self.DEM_DATA_PATH.exists():
            return self.DEM_DATA_PATH
        alt1 = self.BASE_DIR.parent / "data" / "sample_dem.tif"
        if alt1.exists():
            return alt1
        alt2 = self.BASE_DIR / "Backend" / "data" / "sample_dem.tif"
        if alt2.exists():
            return alt2
        alt3 = self.BASE_DIR.parent / "Backend" / "data" / "sample_dem.tif"
        if alt3.exists():
            return alt3
        return self.DEM_DATA_PATH

    @property
    def resolved_sites_path(self) -> Path:
        if self.SITES_DATA_PATH.exists():
            return self.SITES_DATA_PATH
        alt1 = self.BASE_DIR.parent / "data" / "sites.json"
        if alt1.exists():
            return alt1
        alt2 = self.BASE_DIR / "Backend" / "data" / "sites.json"
        if alt2.exists():
            return alt2
        alt3 = self.BASE_DIR.parent / "Backend" / "data" / "sites.json"
        if alt3.exists():
            return alt3
        return self.SITES_DATA_PATH

    # Scientific Configuration Defaults
    DATA_MODE: str = Field("live", description="'live' (verified NASA data priority) or 'demo' (synthetic fallback permitted)")
    ALLOW_SYNTHETIC_FALLBACK: bool = Field(True, description="Whether to allow synthetic sample_dem.tif when verified NASA rasters are uninstalled")
    LUNAR_RADIUS_METERS: float = 1_737_400.0
    MAX_SAFE_SLOPE_DEG: float = 10.0
    CRITICAL_SLOPE_DEG: float = 15.0
    MAX_SAFE_ROUGHNESS_M: float = 0.5

    # AI Explainer Service Configuration (Phase 7)
    MOONSCAPE_AI_PROVIDER: str = "auto"  # 'auto', 'gemini', 'openai', or 'mock'
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    MOONSCAPE_AI_MODEL: str = "gemini-1.5-flash"
    MOONSCAPE_AI_TIMEOUT_SECONDS: float = 15.0
    MOONSCAPE_AI_TEMPERATURE: float = 0.2

    model_config = SettingsConfigDict(
        env_file=(".env", "Backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()
