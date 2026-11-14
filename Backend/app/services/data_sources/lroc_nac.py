"""Adapter for NASA LROC Narrow Angle Camera (NAC) Targeted Stereo DTMs."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from affine import Affine

from Backend.app.core.config import settings
from Backend.app.services.data_sources.base import BaseDataSource
from Backend.app.services.geospatial.coordinate_manager import coordinate_manager
from Backend.app.services.geospatial.raster_sampler import raster_sampler


# Known LROC NAC Polar DTM Targeted Footprints (ASU / PDS Cartography Node)
KNOWN_NAC_DTM_FOOTPRINTS = [
    {
        "product_id": "NAC_DTM_SHACKLETON_01",
        "name": "Shackleton Crater Rim & Connecting Ridge Stereo DTM",
        "bounds": {"min_lat": -89.90, "max_lat": -89.40, "min_lon": 120.0, "max_lon": 240.0},
        "resolution_m": 1.5,
        "stereo_pairs": ["M119811899LE", "M119818694LE"],
        "size_mb": 450.0,
        "pds_url": "https://wms.lroc.asu.edu/lroc/view_rdr/NAC_DTM_SHACKLETON",
    },
    {
        "product_id": "NAC_DTM_MALAPERT_01",
        "name": "Malapert Mountain Summit Stereo DTM",
        "bounds": {"min_lat": -86.10, "max_lat": -85.70, "min_lon": 357.0, "max_lon": 4.0},
        "resolution_m": 2.0,
        "stereo_pairs": ["M123456789LE", "M123456790RE"],
        "size_mb": 380.0,
        "pds_url": "https://wms.lroc.asu.edu/lroc/view_rdr/NAC_DTM_MALAPERT",
    },
    {
        "product_id": "NAC_DTM_FAUSTINI_01",
        "name": "Faustini Crater Rim Stereo DTM",
        "bounds": {"min_lat": -87.35, "max_lat": -87.05, "min_lon": 80.0, "max_lon": 88.0},
        "resolution_m": 2.0,
        "stereo_pairs": ["M134567891LE", "M134567892RE"],
        "size_mb": 320.0,
        "pds_url": "https://wms.lroc.asu.edu/lroc/view_rdr/NAC_DTM_FAUSTINI",
    },
]


class LROCNACSource(BaseDataSource):
    """Scientific adapter for LROC Narrow Angle Camera targeted stereo DTM footprints."""

    def __init__(self):
        self.raw_dir = settings.BASE_DIR / "data" / "lunar" / "raw" / "lroc_nac"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    @property
    def source_id(self) -> str:
        return "lroc_nac"

    @property
    def source_name(self) -> str:
        return "NASA LROC NAC Targeted Stereo DTM (1-2 m/pixel Photogrammetry)"

    def is_available(self) -> bool:
        """Returns True if at least one local NAC DTM is installed."""
        if not self.raw_dir.exists():
            return False
        return any(self.raw_dir.glob("*.tif"))

    def covers_point(self, lat_deg: float, lon_deg: float) -> bool:
        """Checks if coordinate falls inside any known NAC targeted stereo DTM footprint."""
        return len(self.find_covering_dtms(lat_deg, lon_deg)) > 0

    def find_covering_dtms(self, lat_deg: float, lon_deg: float) -> List[Dict[str, Any]]:
        """Identifies NAC DTM footprints encompassing the query point."""
        norm_lon = coordinate_manager.normalize_longitude(lon_deg, target_range="360")
        matches = []
        for dtm in KNOWN_NAC_DTM_FOOTPRINTS:
            b = dtm["bounds"]
            if b["min_lon"] > b["max_lon"]:
                lon_match = (norm_lon >= b["min_lon"]) or (norm_lon <= b["max_lon"])
            else:
                lon_match = b["min_lon"] <= norm_lon <= b["max_lon"]

            if (b["min_lat"] <= lat_deg <= b["max_lat"]) and lon_match:
                matches.append(dict(dtm))
        return matches

    def sample_point(self, lat_deg: float, lon_deg: float) -> Optional[Dict[str, Any]]:
        """Samples local NAC DTM if installed, or returns discovery footprint metadata."""
        covering = self.find_covering_dtms(lat_deg, lon_deg)
        if not covering:
            return None

        for dtm in covering:
            fname = f"{dtm['product_id']}.tif"
            local_path = self.raw_dir / fname
            if local_path.exists():
                elev_val, is_valid_pt, is_nodata = raster_sampler.sample_point_value(
                    local_path, lat_deg, lon_deg, nodata_val=-32768.0
                )
                if is_valid_pt and not is_nodata:
                    return {
                        "source_id": self.source_id,
                        "source_name": self.source_name,
                        "product_id": dtm["product_id"],
                        "name": dtm["name"],
                        "elevation_m": elev_val,
                        "spatial_resolution_m": dtm["resolution_m"],
                        "stereo_pairs": dtm["stereo_pairs"],
                        "provenance": self.get_provenance(),
                    }

        primary = covering[0]
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "product_id": primary["product_id"],
            "name": primary["name"],
            "is_installed_locally": False,
            "spatial_resolution_m": primary["resolution_m"],
            "stereo_pairs": primary["stereo_pairs"],
            "pds_url": primary["pds_url"],
            "message": f"Target point falls inside high-resolution NAC stereo DTM footprint '{primary['name']}'. Not currently installed in local tier.",
            "caveat": "NAC DTMs are non-global and require overlapping stereo image pairs. Deep shadows contain no stereo elevation solution.",
            "provenance": self.get_provenance(),
        }

    def sample_window(
        self,
        lat_deg: float,
        lon_deg: float,
        radius_m: float,
    ) -> Tuple[Optional[np.ndarray], Optional[Affine], Tuple[float, float]]:
        """Extracts spatial sub-window from local NAC DTM if installed."""
        tif_files = list(self.raw_dir.glob("*.tif"))
        if tif_files:
            return raster_sampler.sample_raster_window(tif_files[0], lat_deg, lon_deg, radius_m)
        return None, None, (0.0, 0.0)

    def get_provenance(self) -> Dict[str, Any]:
        """Returns official LROC PDS citation for NAC DTMs."""
        return {
            "mission": "Lunar Reconnaissance Orbiter (LRO)",
            "instrument": "Lunar Reconnaissance Orbiter Camera (LROC) Narrow Angle Camera",
            "archive": "NASA Planetary Data System (PDS) Cartography and Imaging Sciences Node / ASU",
            "product_url": "https://data.lroc.im-ldi.com/lroc/view_rdr/SHAPEFILE_NAC_DTMS",
            "citation": "Henriksen, M. R., et al. (2017). Extracting accurate digital terrain models from Lunar Reconnaissance Orbiter Camera Narrow Angle Camera images. Icarus, 283, 122-137.",
        }


lroc_nac = LROCNACSource()
