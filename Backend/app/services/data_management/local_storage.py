"""Local storage directory management, atomic file operations, and raster validation."""

import hashlib
import os
from pathlib import Path
from typing import Optional, Tuple
import rasterio

from app.core.config import settings
from app.core.logging import logger


class LocalStorageManager:
    """Manages the raw, processed, cache, and temporary data directories on local SSD."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or (settings.BASE_DIR / "data" / "lunar")
        self.raw_dir = self.base_dir / "raw"
        self.processed_dir = self.base_dir / "processed"
        self.cache_dir = self.base_dir / "cache"
        self.temp_dir = self.base_dir / "temporary"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Creates data directories if not present."""
        for d in [self.raw_dir, self.processed_dir, self.cache_dir, self.temp_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def get_temp_part_path(self, filename: str) -> Path:
        """Returns temporary .part path for streaming downloads."""
        return self.temp_dir / f"{filename}.part"

    def get_destination_path(self, subfolder: str, filename: str) -> Path:
        """Returns final verified destination path."""
        target_dir = self.raw_dir / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / filename

    @staticmethod
    def calculate_sha256(filepath: Path) -> str:
        """Calculates SHA256 hex digest of a local file in streaming blocks."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(1024 * 1024):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def validate_geotiff(filepath: Path, expected_min_bytes: int = 1024) -> Tuple[bool, str]:
        """Validates that a downloaded file is a genuine, uncorrupted GeoTIFF readable by Rasterio."""
        if not filepath.exists():
            return False, "File does not exist on disk."

        actual_size = filepath.stat().st_size
        if actual_size < expected_min_bytes:
            return False, f"File size too small ({actual_size} bytes). Likely an HTTP error page or truncated file."

        try:
            with rasterio.open(filepath) as src:
                # Verify header, CRS, count, and dimensions
                if src.width <= 0 or src.height <= 0 or src.count <= 0:
                    return False, "Invalid raster dimensions or zero bands."
                _ = src.crs
                _ = src.transform
                _ = src.nodata
            return True, "Valid GeoTIFF"
        except Exception as e:
            return False, f"Rasterio validation failed: {str(e)}"

    def finalize_atomic_download(self, part_path: Path, dest_path: Path) -> bool:
        """Atomically moves a verified .part file to its permanent destination path."""
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if dest_path.exists():
                dest_path.unlink()
            os.replace(str(part_path), str(dest_path))
            logger.info("Successfully finalized download: %s", dest_path.name)
            return True
        except Exception as e:
            logger.error("Failed to atomically finalize %s: %s", dest_path.name, str(e))
            return False


local_storage = LocalStorageManager()
