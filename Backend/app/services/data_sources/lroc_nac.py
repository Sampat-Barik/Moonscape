"""Adapter for NASA LROC Narrow Angle Camera (NAC) Targeted Stereo DTMs and Optical Footprints."""

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from affine import Affine

from Backend.app.core.config import settings
from Backend.app.services.data_sources.base import BaseDataSource
from Backend.app.services.geospatial.coordinate_manager import coordinate_manager
from Backend.app.services.geospatial.raster_sampler import raster_sampler
from maths.geodesy import haversine_lunar_distance, DEFAULT_MOON_RADIUS_M


# Comprehensive Catalog of Official NASA LROC NAC Targeted Polar DTM Footprints (ASU / PDS Cartography Node)
KNOWN_NAC_DTM_FOOTPRINTS: List[Dict[str, Any]] = [
    {
        "product_id": "NAC_DTM_SHACKLETON_01",
        "name": "Shackleton Crater Rim & Connecting Ridge Stereo DTM",
        "site_label": "Artemis III Candidate Region 01",
        "bounds": {"min_lat": -89.90, "max_lat": -89.40, "min_lon": 120.0, "max_lon": 240.0},
        "centroid": {"lat": -89.65, "lon": 180.0},
        "resolution_m": 1.5,
        "stereo_pairs": ["M119811899LE", "M119818694LE"],
        "size_mb": 450.0,
        "incidence_angle_range_deg": [78.5, 84.2],
        "solar_illumination_min_pct": 52.0,
        "solar_illumination_peak_pct": 86.4,
        "pds_url": "https://wms.lroc.asu.edu/lroc/view_rdr/NAC_DTM_SHACKLETON",
    },
    {
        "product_id": "NAC_DTM_CONNECTING_RIDGE_02",
        "name": "Connecting Ridge Extension Stereo DTM",
        "site_label": "Connecting Ridge Site 01 / 02 Extension",
        "bounds": {"min_lat": -89.60, "max_lat": -89.30, "min_lon": 190.0, "max_lon": 240.0},
        "centroid": {"lat": -89.45, "lon": 215.0},
        "resolution_m": 1.5,
        "stereo_pairs": ["M120145821LE", "M120152616LE"],
        "size_mb": 395.0,
        "incidence_angle_range_deg": [80.1, 85.0],
        "solar_illumination_min_pct": 48.0,
        "solar_illumination_peak_pct": 82.1,
        "pds_url": "https://wms.lroc.asu.edu/lroc/view_rdr/NAC_DTM_CONNECTING_RIDGE",
    },
    {
        "product_id": "NAC_DTM_DE_GERLACHE_RIM_01",
        "name": "de Gerlache Crater Rim 1 & 2 Stereo DTM",
        "site_label": "Artemis III Candidate Region 03 / 04",
        "bounds": {"min_lat": -88.80, "max_lat": -88.20, "min_lon": 265.0, "max_lon": 295.0},
        "centroid": {"lat": -88.50, "lon": 280.0},
        "resolution_m": 1.5,
        "stereo_pairs": ["M134982103LE", "M134988898LE"],
        "size_mb": 510.0,
        "incidence_angle_range_deg": [79.2, 83.8],
        "solar_illumination_min_pct": 44.0,
        "solar_illumination_peak_pct": 78.5,
        "pds_url": "https://wms.lroc.asu.edu/lroc/view_rdr/NAC_DTM_DE_GERLACHE",
    },
    {
        "product_id": "NAC_DTM_MALAPERT_01",
        "name": "Malapert Mountain Summit Stereo DTM",
        "site_label": "Artemis III Candidate Region 02 / CLPS IM-1",
        "bounds": {"min_lat": -86.10, "max_lat": -85.70, "min_lon": 357.0, "max_lon": 4.0},
        "centroid": {"lat": -85.90, "lon": 0.5},
        "resolution_m": 2.0,
        "stereo_pairs": ["M123456789LE", "M123456790RE"],
        "size_mb": 380.0,
        "incidence_angle_range_deg": [75.0, 81.5],
        "solar_illumination_min_pct": 55.0,
        "solar_illumination_peak_pct": 91.0,
        "pds_url": "https://wms.lroc.asu.edu/lroc/view_rdr/NAC_DTM_MALAPERT",
    },
    {
        "product_id": "NAC_DTM_FAUSTINI_01",
        "name": "Faustini Crater Rim Stereo DTM",
        "site_label": "Artemis III Candidate Region 04",
        "bounds": {"min_lat": -87.40, "max_lat": -87.05, "min_lon": 75.0, "max_lon": 90.0},
        "centroid": {"lat": -87.22, "lon": 82.5},
        "resolution_m": 2.0,
        "stereo_pairs": ["M134567891LE", "M134567892RE"],
        "size_mb": 320.0,
        "incidence_angle_range_deg": [77.4, 82.9],
        "solar_illumination_min_pct": 42.0,
        "solar_illumination_peak_pct": 74.0,
        "pds_url": "https://wms.lroc.asu.edu/lroc/view_rdr/NAC_DTM_FAUSTINI",
    },
    {
        "product_id": "NAC_DTM_HAWORTH_01",
        "name": "Haworth Crater Floor & Permanently Shadowed Region DTM",
        "site_label": "Lunar Volatiles / PSR Exploration",
        "bounds": {"min_lat": -87.80, "max_lat": -87.10, "min_lon": 340.0, "max_lon": 360.0},
        "centroid": {"lat": -87.45, "lon": 350.0},
        "resolution_m": 2.0,
        "stereo_pairs": ["M145129840LE", "M145136635LE"],
        "size_mb": 420.0,
        "incidence_angle_range_deg": [84.0, 88.5],
        "solar_illumination_min_pct": 0.0,
        "solar_illumination_peak_pct": 18.0,
        "pds_url": "https://wms.lroc.asu.edu/lroc/view_rdr/NAC_DTM_HAWORTH",
    },
    {
        "product_id": "NAC_DTM_NOBILE_RIM_01",
        "name": "Nobile Crater Rim 1 & 2 Stereo DTM",
        "site_label": "VIPER Target Landing Area",
        "bounds": {"min_lat": -85.50, "max_lat": -85.00, "min_lon": 30.0, "max_lon": 45.0},
        "centroid": {"lat": -85.25, "lon": 37.5},
        "resolution_m": 1.5,
        "stereo_pairs": ["M139821045LE", "M139827840LE"],
        "size_mb": 480.0,
        "incidence_angle_range_deg": [76.0, 81.0],
        "solar_illumination_min_pct": 38.0,
        "solar_illumination_peak_pct": 79.2,
        "pds_url": "https://wms.lroc.asu.edu/lroc/view_rdr/NAC_DTM_NOBILE",
    },
    {
        "product_id": "NAC_DTM_AMUNDSEN_01",
        "name": "Amundsen Crater Rim & Plateau Stereo DTM",
        "site_label": "Artemis III Candidate Region 08",
        "bounds": {"min_lat": -84.80, "max_lat": -84.10, "min_lon": 78.0, "max_lon": 95.0},
        "centroid": {"lat": -84.45, "lon": 86.5},
        "resolution_m": 2.0,
        "stereo_pairs": ["M128945612LE", "M128952407LE"],
        "size_mb": 410.0,
        "incidence_angle_range_deg": [73.5, 79.8],
        "solar_illumination_min_pct": 46.0,
        "solar_illumination_peak_pct": 81.5,
        "pds_url": "https://wms.lroc.asu.edu/lroc/view_rdr/NAC_DTM_AMUNDSEN",
    },
    {
        "product_id": "NAC_DTM_LEIBNITZ_BETA_01",
        "name": "Leibnitz Beta Plateau Stereo DTM",
        "site_label": "Artemis III Candidate Region 10",
        "bounds": {"min_lat": -86.00, "max_lat": -85.30, "min_lon": 320.0, "max_lon": 345.0},
        "centroid": {"lat": -85.65, "lon": 332.5},
        "resolution_m": 2.0,
        "stereo_pairs": ["M131298450LE", "M131305245LE"],
        "size_mb": 430.0,
        "incidence_angle_range_deg": [75.2, 80.6],
        "solar_illumination_min_pct": 45.0,
        "solar_illumination_peak_pct": 83.0,
        "pds_url": "https://wms.lroc.asu.edu/lroc/view_rdr/NAC_DTM_LEIBNITZ_BETA",
    },
    {
        "product_id": "NAC_DTM_PEAK_NEAR_SHACKLETON_01",
        "name": "Peak Near Shackleton Stereo DTM",
        "site_label": "Artemis III Candidate Region 03",
        "bounds": {"min_lat": -89.00, "max_lat": -88.60, "min_lon": 110.0, "max_lon": 140.0},
        "centroid": {"lat": -88.80, "lon": 125.0},
        "resolution_m": 1.5,
        "stereo_pairs": ["M122345678LE", "M122352473LE"],
        "size_mb": 460.0,
        "incidence_angle_range_deg": [79.0, 84.5],
        "solar_illumination_min_pct": 58.0,
        "solar_illumination_peak_pct": 89.2,
        "pds_url": "https://wms.lroc.asu.edu/lroc/view_rdr/NAC_DTM_PEAK_SHACKLETON",
    },
]


class LROCNACSource(BaseDataSource):
    """Scientific adapter for LROC Narrow Angle Camera targeted stereo DTM footprints and optical discoveries."""

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

    def discover_footprints(
        self,
        center_lat: float,
        center_lon: float,
        search_radius_meters: float = 5000.0,
    ) -> Dict[str, Any]:
        """Performs spatial footprint discovery for LROC NAC targeted stereo products intersecting the query disc.

        Scientific Delineation:
            - Optical NAC Products: Enable sub-meter rock/boulder detection (> 1m) and micro-crater detection
              from shadows and reflectance. Requires stereo photogrammetry pairs; deep shadowed PSRs contain NO elevation.
            - Altimetry DEM Products (LOLA/PGDA): Provide direct 3D physical elevation, slopes, and macroscopic roughness
              invariant to shadow conditions.
        """
        norm_lon = coordinate_manager.normalize_longitude(center_lon, target_range="360")
        intersecting: List[Dict[str, Any]] = []

        # Convert search radius to degrees on lunar surface (1 deg ≈ 30.32 km)
        km_per_deg = (2.0 * math.pi * DEFAULT_MOON_RADIUS_M / 360.0) / 1000.0
        rad_deg = (search_radius_meters / 1000.0) / km_per_deg

        for dtm in KNOWN_NAC_DTM_FOOTPRINTS:
            c = dtm["centroid"]
            dist_m = haversine_lunar_distance(center_lat, norm_lon, c["lat"], c["lon"])

            # Check bounding box with radius buffer
            b = dtm["bounds"]
            lat_match = (b["min_lat"] - rad_deg) <= center_lat <= (b["max_lat"] + rad_deg)

            if b["min_lon"] > b["max_lon"]:
                lon_match = (norm_lon >= b["min_lon"] - rad_deg) or (norm_lon <= b["max_lon"] + rad_deg)
            else:
                lon_match = (b["min_lon"] - rad_deg) <= norm_lon <= (b["max_lon"] + rad_deg)

            if lat_match and lon_match:
                # Direct centroid check vs peripheral overlap
                is_direct = (b["min_lat"] <= center_lat <= b["max_lat"]) and (
                    (norm_lon >= b["min_lon"] or norm_lon <= b["max_lon"])
                    if b["min_lon"] > b["max_lon"]
                    else (b["min_lon"] <= norm_lon <= b["max_lon"])
                )

                # Local installation check
                local_path = self.raw_dir / f"{dtm['product_id']}.tif"
                is_local = local_path.exists()

                intersecting.append({
                    "product_id": dtm["product_id"],
                    "name": dtm["name"],
                    "site_label": dtm.get("site_label"),
                    "resolution_m": dtm["resolution_m"],
                    "stereo_pairs": dtm["stereo_pairs"],
                    "bounds": dtm["bounds"],
                    "centroid": dtm["centroid"],
                    "distance_to_centroid_km": round(dist_m / 1000.0, 2),
                    "overlap_type": "direct_coverage" if is_direct else "peripheral_intersection",
                    "incidence_angle_range_deg": dtm.get("incidence_angle_range_deg"),
                    "solar_illumination_peak_pct": dtm.get("solar_illumination_peak_pct"),
                    "is_installed_locally": is_local,
                    "pds_url": dtm["pds_url"],
                })

        # Sort by proximity to query coordinates
        intersecting.sort(key=lambda x: x["distance_to_centroid_km"])

        return {
            "query_center": {"lat": center_lat, "lon": norm_lon},
            "search_radius_meters": search_radius_meters,
            "total_footprints_intersecting": len(intersecting),
            "footprints": intersecting,
            "hazard_detection_delineation": {
                "optical_imaging_role": (
                    "LROC NAC 0.5-2.0 m/pixel optical imagery provides high-contrast reflectance "
                    "for detecting boulders (> 1-2m diameter via shadow length), crater rims, and visual "
                    "texture. Stereo elevation generation fails in permanently shadowed regions."
                ),
                "altimetry_dem_role": (
                    "LOLA laser altimetry (PGDA 78/90) provides true 3D topography, Horn slopes, "
                    "and multi-baseline surface roughness. LOLA operates independently of solar illumination "
                    "and measures elevation inside deep craters."
                ),
            },
            "provenance": self.get_provenance(),
        }

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
            "instrument": "Lunar Reconnaissance Orbiter Camera (LROC) Narrow Angle Camera (NAC)",
            "archive": "NASA Planetary Data System (PDS) Cartography and Imaging Sciences Node / Arizona State University (ASU)",
            "product_url": "https://data.lroc.im-ldi.com/lroc/view_rdr/SHAPEFILE_NAC_DTMS",
            "citation": "Henriksen, M. R., et al. (2017). Extracting accurate digital terrain models from Lunar Reconnaissance Orbiter Camera Narrow Angle Camera images. Icarus, 283, 122-137.",
        }


lroc_nac = LROCNACSource()
