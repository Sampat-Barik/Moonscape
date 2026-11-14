"""Hardware-aware operational resource configuration for Moonscape.

Optimized for:
- CPU: AMD Ryzen 9 8940HX
- RAM: 16 GB (In-memory cache budget: ~256 MB)
- GPU: NVIDIA GeForce RTX 5070 Laptop GPU (8GB VRAM reserved for ML/vision)
- Storage: Dynamic SSD detection on drive D:
"""

import os
import shutil
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class HardwareProfile(BaseModel):
    """Specification of the local execution host."""

    cpu_model: str = "AMD Ryzen 9 8940HX"
    cpu_cores_logical: int = os.cpu_count() or 16
    system_ram_gb: float = 16.0
    gpu_model: str = "NVIDIA GeForce RTX 5070 Laptop GPU"
    gpu_vram_gb: float = 8.0
    gpu_accelerated_sampling_enabled: bool = False  # Keep false: CPU rasterio is fast and avoids CUDA lockups


class ResourceSettings(BaseModel):
    """Operational limits and thresholds tuned for laptop stability."""

    hardware: HardwareProfile = Field(default_factory=HardwareProfile)

    # In-Memory Cache Limits (RAM protection)
    CACHE_BUDGET_MB: int = 256
    MAX_LRU_RASTER_WINDOWS: int = 64
    MAX_PER_REQUEST_WINDOW_PIXELS: int = 1024  # Max 1024x1024 window per single sample request

    # Concurrency Limits
    MAX_CONCURRENT_LARGE_DOWNLOADS: int = 1
    MAX_CONCURRENT_HEAVY_RASTER_JOBS: int = 2

    # Storage Thresholds
    AUTO_DOWNLOAD_APPROVAL_THRESHOLD_MB: float = 250.0  # Files > 250MB require approval unless pre-approved
    USER_PREAPPROVED_TOTAL_STORAGE_GB: float = 5.0  # User explicitly approved up to 5GB for terrain data
    MINIMUM_FREE_SSD_HEADROOM_GB: float = 10.0  # Never download if free disk space falls below 10GB

    # Network
    DOWNLOAD_CHUNK_SIZE_BYTES: int = 1024 * 512  # 512 KB chunks for smooth streaming and responsive cancellation
    DOWNLOAD_TIMEOUT_SECONDS: int = 60
    MAX_DOWNLOAD_RETRIES: int = 3

    @staticmethod
    def get_available_disk_space_gb(path: Optional[Path] = None) -> float:
        """Dynamically queries the free SSD capacity for the volume hosting the given path."""
        try:
            target = path or Path.cwd()
            while not target.exists() and target.parent != target:
                target = target.parent
            total, used, free = shutil.disk_usage(target)
            return round(free / (1024**3), 2)
        except Exception:
            return 50.0  # Fallback assumption if OS call fails


resource_settings = ResourceSettings()
