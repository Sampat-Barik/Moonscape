"""Adapter for NASA LRO Diviner Lunar Radiometer Experiment Polar Cumulative Products (PCP)."""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import numpy as np
from affine import Affine

from app.core.config import settings
from app.services.data_sources.base import BaseDataSource
from app.services.geospatial.coordinate_manager import coordinate_manager
from app.services.geospatial.raster_sampler import raster_sampler


class DivinerThermalSource(BaseDataSource):
    """Scientific adapter for NASA LRO Diviner Lunar Radiometer Experiment."""

    NODATA_VAL: float = -9999.0

    def __init__(self):
        self.raw_dir = settings.BASE_DIR / "data" / "lunar" / "raw" / "diviner"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    @property
    def source_id(self) -> str:
        return "diviner_pcp"

    @property
    def source_name(self) -> str:
        return "NASA LRO Diviner Lunar Radiometer Polar Cumulative Products (PCP)"

    def is_available(self) -> bool:
        """Returns True if local Diviner polar thermal rasters are present on disk."""
        if not self.raw_dir.exists():
            return False
        return any(self.raw_dir.glob("*.tif"))

    def covers_point(self, lat_deg: float, lon_deg: float) -> bool:
        """Diviner Polar Cumulative Products cover all regions poleward of 80°S."""
        return coordinate_manager.is_in_south_pole_zone(lat_deg)

    def sample_point(self, lat_deg: float, lon_deg: float) -> Optional[Dict[str, Any]]:
        """Samples cumulative surface brightness temperature and thermal environment metrics."""
        if not self.covers_point(lat_deg, lon_deg):
            return None

        # Look for local Diviner GeoTIFFs (e.g., T_bol max, T_bol min, average)
        tif_files = list(self.raw_dir.glob("*.tif"))
        if tif_files:
            primary_tif = tif_files[0]
            val, is_valid_pt, is_nodata = raster_sampler.sample_point_value(
                primary_tif, lat_deg, lon_deg, nodata_val=self.NODATA_VAL
            )
            if is_valid_pt:
                return {
                    "source_id": self.source_id,
                    "source_name": self.source_name,
                    "is_nodata": is_nodata,
                    "temperature_k": val if not is_nodata else None,
                    "temperature_unit": "Kelvin",
                    "caveat": "Historical multi-year cumulative brightness temperature. Not a real-time measurement.",
                    "reference_frame": "MOON_ME (Mean Earth / Polar Axis) DE421",
                    "provenance": self.get_provenance(),
                }

        # If raster not installed, report authentic catalog metadata without fabricating numbers
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "is_nodata": True,
            "temperature_k": None,
            "temperature_unit": "Kelvin",
            "message": "Diviner Polar Cumulative Product not installed in local tier. Available from PDS Geosciences Node / UCLA Diviner archive.",
            "caveat": "Temperatures represent multi-year binned surface brightness, not real-time conditions. Permanently shadowed regions require cryogenic hardware tolerances (< 110 K).",
            "provenance": self.get_provenance(),
        }

    def sample_window(
        self,
        lat_deg: float,
        lon_deg: float,
        radius_m: float,
    ) -> Tuple[Optional[np.ndarray], Optional[Affine], Tuple[float, float]]:
        """Extracts spatial sub-window from local Diviner raster if installed."""
        tif_files = list(self.raw_dir.glob("*.tif"))
        if tif_files:
            return raster_sampler.sample_raster_window(tif_files[0], lat_deg, lon_deg, radius_m)
        return None, None, (0.0, 0.0)

    def get_provenance(self) -> Dict[str, Any]:
        """Returns official PDS and UCLA citations for Diviner."""
        return {
            "mission": "Lunar Reconnaissance Orbiter (LRO)",
            "instrument": "Diviner Lunar Radiometer Experiment (DLRE)",
            "archive": "PDS Geosciences Node / UCLA Diviner Science Team",
            "product_url": "https://www.diviner.ucla.edu/data",
            "citation": "Paige, D. A., et al. (2010). The Diviner Lunar Radiometer Experiment. Space Science Reviews, 150(1-4), 125-160.",
            "missing_value_sentinel": self.NODATA_VAL,
        }


diviner_thermal = DivinerThermalSource()
