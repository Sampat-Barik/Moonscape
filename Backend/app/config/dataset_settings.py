"""Dataset registry definitions, metadata structures, and manifest loading."""

import json
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.config import settings


class DatasetTier(str, Enum):
    """Classification of data access tier."""

    LOCAL_REQUIRED = "local_required"
    LOCAL_OPTIONAL = "local_optional"
    REMOTE_METADATA = "remote_metadata"
    REMOTE_WINDOW = "remote_window"
    REMOTE_FULL_FILE = "remote_full_file"
    NOT_SUPPORTED = "not_supported"


class DatasetStatus(str, Enum):
    """Lifecycle and operational state of a NASA dataset in Moonscape."""

    NOT_INSTALLED = "not_installed"
    REMOTE_AVAILABLE = "remote_available"
    DOWNLOAD_QUEUED = "download_queued"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    VALIDATING = "validating"
    AVAILABLE = "available"
    PARTIAL = "partial"
    FAILED = "failed"
    INVALID = "invalid"
    UNAVAILABLE = "unavailable"


class SpatialBounds(BaseModel):
    """Geographic planetocentric coordinate bounds."""

    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float


class DatasetDefinition(BaseModel):
    """Canonical specification of a scientific lunar dataset."""

    id: str
    name: str
    source_provider: str
    product_id: str
    filename: str
    url: str
    local_relative_path: str
    size_bytes: int
    size_mb: float
    spatial_resolution_m: float
    units: str
    nodata: float
    bounds: SpatialBounds
    tier: DatasetTier
    byte_range_supported: bool = True
    sha256_checksum: Optional[str] = None
    description: Optional[str] = None

    @property
    def absolute_local_path(self) -> Path:
        """Returns the resolved local filesystem path on disk."""
        return settings.BASE_DIR / self.local_relative_path


class DatasetSettings(BaseModel):
    """Registry settings loaded from verified NASA download manifest."""

    manifest_path: Path = settings.BASE_DIR.parent / "docs" / "download_manifest.json"
    datasets: Dict[str, DatasetDefinition] = {}
    profiles: Dict[str, dict] = {}

    def __init__(self, **data):
        super().__init__(**data)
        self.load_manifest()

    def get_profiles(self) -> Dict[str, dict]:
        """Returns preset download profiles."""
        return self.profiles

    def load_manifest(self) -> None:
        """Loads and parses the verified NASA dataset manifest JSON."""
        # Try relative paths based on runtime cwd
        candidates = [
            self.manifest_path,
            settings.BASE_DIR / "docs" / "download_manifest.json",
            Path("docs/download_manifest.json"),
            Path("../docs/download_manifest.json"),
        ]
        target = next((p for p in candidates if p.exists()), None)
        if not target:
            return

        try:
            with open(target, "r", encoding="utf-8") as f:
                raw = json.load(f)
                self.profiles = raw.get("profiles", {})
                dsets = raw.get("datasets", {})
                for k, v in dsets.items():
                    self.datasets[k] = DatasetDefinition(**v)
        except Exception as e:
            from app.core.logging import logger
            logger.error("Failed to parse NASA dataset manifest: %s", str(e))


dataset_settings = DatasetSettings()
