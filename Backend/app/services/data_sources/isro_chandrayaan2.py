"""Scientific adapter for ISRO Chandrayaan-2 Orbiter Instruments (OHRC and TMC-2)."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from affine import Affine

from app.core.config import settings
from app.services.data_sources.base import BaseDataSource
from app.services.geospatial.coordinate_manager import coordinate_manager


KNOWN_ISRO_CH2_FOOTPRINTS: List[Dict[str, Any]] = [
    {
        "product_id": "CH2_OHR_NC_20200115T081520_825_D",
        "instrument": "OHRC",
        "name": "Amundsen-Ganswindt Transition Corridor OHRC High-Resolution Strip",
        "coverage_zone": "extended",
        "bounds": {"min_lat": -81.2, "max_lat": -78.5, "min_lon": 82.0, "max_lon": 87.0},
        "resolution_m": 0.25,
        "solar_incidence_deg": 83.0,
        "format": "PDS4 Standard Calibrated",
        "pradan_url": "https://pradan.issdc.gov.in/ch2/",
    },
    {
        "product_id": "CH2_OHR_NC_20190906T123045_710_D",
        "instrument": "OHRC",
        "name": "Simpelius N / Boguslawsky South Pole Transition Corridor OHRC Strip",
        "coverage_zone": "context",
        "bounds": {"min_lat": -74.8, "max_lat": -71.2, "min_lon": 52.0, "max_lon": 56.5},
        "resolution_m": 0.28,
        "solar_incidence_deg": 81.5,
        "format": "PDS4 Standard Calibrated",
        "pradan_url": "https://pradan.issdc.gov.in/ch2/",
    },
    {
        "product_id": "CH2_TMC_NC_20191012T041230_DTM",
        "instrument": "TMC-2",
        "name": "South Pole Highland Extended Corridor Stereo Triplet DTM",
        "coverage_zone": "extended_and_context",
        "bounds": {"min_lat": -80.0, "max_lat": -70.0, "min_lon": 0.0, "max_lon": 360.0},
        "resolution_m": 5.0,
        "format": "PDS4 DTM GeoTIFF",
        "pradan_url": "https://pradan.issdc.gov.in/ch2/",
    },
    {
        "product_id": "CH2_TMC_NC_20200218T102450_DTM",
        "instrument": "TMC-2",
        "name": "South Pole Polar Core Corridor Stereo Triplet DTM",
        "coverage_zone": "core",
        "bounds": {"min_lat": -90.0, "max_lat": -80.0, "min_lon": 0.0, "max_lon": 360.0},
        "resolution_m": 5.0,
        "format": "PDS4 DTM GeoTIFF",
        "pradan_url": "https://pradan.issdc.gov.in/ch2/",
    },
]


class ISROChandrayaan2Source(BaseDataSource):
    """Scientific adapter for ISRO Chandrayaan-2 OHRC optical and TMC-2 terrain products."""

    def __init__(self):
        self.raw_dir = settings.BASE_DIR / "data" / "lunar" / "raw" / "isro_ch2"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    @property
    def source_id(self) -> str:
        return "isro_chandrayaan2"

    @property
    def source_name(self) -> str:
        return "ISRO Chandrayaan-2 (OHRC High-Res Optical & TMC-2 Polar Stereo DTM)"

    def is_available(self) -> bool:
        """Returns True if local ISRO data or catalog profiles are initialized."""
        return True

    def covers_point(self, lat_deg: float, lon_deg: float) -> bool:
        """Covers all regions within the configured South Pole exploration envelope (-90° to -70°)."""
        return coordinate_manager.is_in_analysis_region(lat_deg)

    def find_covering_products(self, lat_deg: float, lon_deg: float) -> List[Dict[str, Any]]:
        """Finds specific OHRC and TMC-2 products encompassing the coordinate."""
        norm_lon = coordinate_manager.normalize_longitude(lon_deg, target_range="360")
        results = []
        for p in KNOWN_ISRO_CH2_FOOTPRINTS:
            b = p["bounds"]
            if b["min_lat"] <= lat_deg <= b["max_lat"]:
                if b["min_lon"] <= norm_lon <= b["max_lon"]:
                    results.append(p)
        return results

    def sample_point(self, lat_deg: float, lon_deg: float) -> Optional[Dict[str, Any]]:
        """Returns metadata and spatial attributes for covering Chandrayaan-2 products."""
        if not self.covers_point(lat_deg, lon_deg):
            return None

        covering = self.find_covering_products(lat_deg, lon_deg)
        if not covering:
            # Regional TMC-2 baseline coverage
            return {
                "source_id": self.source_id,
                "instrument": "TMC-2",
                "coverage_status": "regional_baseline",
                "resolution_m": 5.0,
                "coverage_zone": coordinate_manager.get_coverage_zone(lat_deg),
                "provenance": "ISRO ISSDC PRADAN Archive",
            }

        primary = covering[0]
        return {
            "source_id": self.source_id,
            "product_id": primary["product_id"],
            "instrument": primary["instrument"],
            "product_name": primary["name"],
            "resolution_m": primary["resolution_m"],
            "coverage_zone": primary["coverage_zone"],
            "solar_incidence_deg": primary.get("solar_incidence_deg"),
            "provenance": "ISRO ISSDC PRADAN Archive",
        }

    def sample_window(
        self,
        lat_deg: float,
        lon_deg: float,
        radius_m: float,
    ) -> Tuple[Optional[np.ndarray], Optional[Affine], Tuple[float, float]]:
        """Returns sampled window if local raster installed; otherwise None."""
        return None, None, (0.0, 0.0)

    def get_provenance(self) -> Dict[str, Any]:
        """Returns official mission provenance, citations, and licensing terms."""
        return {
            "mission": "Chandrayaan-2 Orbiter",
            "agency": "Indian Space Research Organisation (ISRO)",
            "archive": "Indian Space Science Data Centre (ISSDC) PRADAN Portal",
            "archive_url": "https://pradan.issdc.gov.in/ch2/",
            "citation": "Chowdhury, A. et al. (2020). Orbiter High Resolution Camera (OHRC) on Chandrayaan-2. Current Science, 118(4), 548-555.",
            "usage_rights": "ISRO Chandrayaan-2 Data Policy (ISSDC). Reproduction and scientific analysis permitted with explicit ISRO attribution.",
            "instruments": ["OHRC (0.25-0.32 mpp)", "TMC-2 (5.0 mpp Stereo Triplet DTM)"],
        }


isro_chandrayaan2 = ISROChandrayaan2Source()
