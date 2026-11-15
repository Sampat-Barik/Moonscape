"""Adapter for NASA LROC Wide Angle Camera (WAC) South Pole Visual Mosaics."""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import numpy as np
from affine import Affine

from app.core.config import settings
from app.services.data_sources.base import BaseDataSource
from app.services.geospatial.coordinate_manager import coordinate_manager
from app.services.geospatial.raster_sampler import raster_sampler


class LROCWACSource(BaseDataSource):
    """Scientific adapter for NASA LROC WAC South Polar visual imagery mosaics."""

    def __init__(self):
        self.raw_dir = settings.BASE_DIR / "data" / "lunar" / "raw" / "lroc_wac"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    @property
    def source_id(self) -> str:
        return "lroc_wac"

    @property
    def source_name(self) -> str:
        return "NASA LROC WAC South Pole Visual Mosaic (Morphologic & Illumination Context)"

    def is_available(self) -> bool:
        """Returns True if local LROC WAC polar mosaic is installed on disk."""
        if not self.raw_dir.exists():
            return False
        return any(self.raw_dir.glob("*.tif"))

    def covers_point(self, lat_deg: float, lon_deg: float) -> bool:
        """Covers all regions poleward of 80°S."""
        return coordinate_manager.is_in_south_pole_zone(lat_deg)

    def sample_point(self, lat_deg: float, lon_deg: float) -> Optional[Dict[str, Any]]:
        """Samples optical reflectance / illumination context if installed."""
        if not self.covers_point(lat_deg, lon_deg):
            return None

        tif_files = list(self.raw_dir.glob("*.tif"))
        if tif_files:
            val, is_valid_pt, is_nodata = raster_sampler.sample_point_value(
                tif_files[0], lat_deg, lon_deg, nodata_val=0.0
            )
            if is_valid_pt:
                return {
                    "source_id": self.source_id,
                    "source_name": self.source_name,
                    "is_nodata": is_nodata,
                    "albedo_dn": val if not is_nodata else None,
                    "visual_context": "Normalized optical reflectance",
                    "caveat": "Optical albedo does NOT measure terrain elevation. Grazing polar shadows must not be mistaken for craters.",
                    "provenance": self.get_provenance(),
                }

        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "is_nodata": True,
            "albedo_dn": None,
            "message": "LROC WAC polar mosaic not installed locally. Visual reference available via LROC PDS archive.",
            "caveat": "Optical albedo does NOT measure terrain elevation. Grazing polar shadows must not be mistaken for craters.",
            "provenance": self.get_provenance(),
        }

    def sample_window(
        self,
        lat_deg: float,
        lon_deg: float,
        radius_m: float,
    ) -> Tuple[Optional[np.ndarray], Optional[Affine], Tuple[float, float]]:
        """Extracts spatial sub-window from local LROC WAC mosaic if installed."""
        tif_files = list(self.raw_dir.glob("*.tif"))
        if tif_files:
            return raster_sampler.sample_raster_window(tif_files[0], lat_deg, lon_deg, radius_m)
        return None, None, (0.0, 0.0)

    def get_provenance(self) -> Dict[str, Any]:
        """Returns official LROC PDS citation."""
        return {
            "mission": "Lunar Reconnaissance Orbiter (LRO)",
            "instrument": "Lunar Reconnaissance Orbiter Camera (LROC) Wide Angle Camera",
            "archive": "NASA Planetary Data System (PDS) Cartography and Imaging Sciences Node / ASU",
            "product_url": "https://wms.lroc.asu.edu/lroc",
            "citation": "Robinson, M. S., et al. (2010). Lunar Reconnaissance Orbiter Camera (LROC) Instrument Overview. Space Science Reviews, 150(1-4), 81-124.",
        }


lroc_wac = LROCWACSource()
