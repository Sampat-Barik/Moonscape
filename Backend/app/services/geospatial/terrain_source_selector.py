"""Hierarchical Terrain Source Selector prioritizing highest-resolution verified authentic NASA data."""

from typing import Any, Dict, Optional, Tuple
import numpy as np

from Backend.app.core.constants import (
    LOLA_DATASET_NAME,
    LOLA_NODATA_VALUE,
    LOLA_PRODUCT_ID,
    LOLA_SPATIAL_RESOLUTION_M,
    LOLA_VERTICAL_ACCURACY_M,
    SLOPE_CRITICAL_MAX_DEG,
    SLOPE_NOMINAL_MAX_DEG,
)
from Backend.app.schemas.terrain import TerrainDatasetInfo, TerrainResponse
from Backend.app.services.data_sources.pgda_product78 import pgda_product78
from Backend.app.services.data_sources.pgda_product90 import pgda_product90
from Backend.app.services.dem_service import dem_service
from Backend.app.services.geospatial.coordinate_manager import coordinate_manager
from maths.topography import horn_slope_and_aspect, rms_surface_roughness


class TerrainSourceSelector:
    """Selects highest-resolution available NASA lunar raster data for any coordinate."""

    @classmethod
    def select_source(cls, lat_deg: float, lon_deg: float) -> str:
        """Determines best available source ID for requested point."""
        if pgda_product78.is_available() and pgda_product78.covers_point(lat_deg, lon_deg):
            return "pgda_product78"
        if pgda_product90.is_available() and pgda_product90.covers_point(lat_deg, lon_deg):
            return "pgda_product90"
        return "dem_sample_fallback"

    @classmethod
    def get_point_terrain(cls, lat: float, lon: float) -> TerrainResponse:
        """Acquires scientific terrain measurements using the highest-fidelity available layer."""
        is_valid_coord, val_msg = coordinate_manager.validate_coordinates(lat, lon)
        if not is_valid_coord or not coordinate_manager.is_in_south_pole_zone(lat):
            return TerrainResponse(
                latitude=lat,
                longitude=lon,
                is_valid_point=False,
                is_nodata=False,
                elevation_m=None,
                slope_deg=None,
                roughness_m=None,
                aspect_deg=None,
                solar_illumination_pct=None,
                landing_hazard_classification="nodata",
                dataset_info=TerrainDatasetInfo(
                    dataset_name=LOLA_DATASET_NAME,
                    product_id=LOLA_PRODUCT_ID,
                    spatial_resolution_m=LOLA_SPATIAL_RESOLUTION_M,
                    vertical_uncertainty_m=LOLA_VERTICAL_ACCURACY_M,
                    slope_method="Horn (1981) 8-neighbor gradient operator",
                    roughness_baseline_m=LOLA_SPATIAL_RESOLUTION_M * 3.0,
                ),
                notes=f"Coordinates outside lunar South Pole coverage area (-90.0° to -80.0°). {val_msg}",
            )

        source_id = cls.select_source(lat, lon)

        # -------------------------------------------------------------
        # 1. Product 78: 5m/pixel high-resolution candidate site DEM
        # -------------------------------------------------------------
        if source_id == "pgda_product78":
            sample = pgda_product78.sample_point(lat, lon)
            if sample and not sample.get("is_nodata", False):
                slope_val = sample.get("slope_deg")
                win_data, _, _ = pgda_product78.sample_window(lat, lon, radius_m=25.0)
                rough_val = 0.2
                aspect_val = 0.0
                if win_data is not None and win_data.size >= 9:
                    r_arr = rms_surface_roughness(win_data, kernel_size=3)
                    rough_val = float(r_arr[r_arr.shape[0] // 2, r_arr.shape[1] // 2])
                    s_arr, a_arr = horn_slope_and_aspect(win_data, 5.0, 5.0)
                    aspect_val = float(a_arr[a_arr.shape[0] // 2, a_arr.shape[1] // 2])
                    if slope_val is None:
                        slope_val = round(float(s_arr[s_arr.shape[0] // 2, s_arr.shape[1] // 2]), 2)
                hazard_class = cls._classify_hazard(slope_val, rough_val)
                illum = cls._estimate_illumination(lat, sample["elevation_m"])

                dataset_info = TerrainDatasetInfo(
                    dataset_name=sample["source_name"],
                    product_id="Site01_5mpp_LOLA_adj",
                    spatial_resolution_m=5.0,
                    vertical_uncertainty_m=sample.get("elevation_uncertainty_m") or 1.5,
                    slope_method="NASA GSFC Precomputed 5m Topographic Gradient + Horn Local Aspect",
                    roughness_baseline_m=15.0,
                    citation="Barker et al. (2021) Planetary and Space Science 203, 105119",
                    observation_count=sample.get("observation_count"),
                    slope_uncertainty_deg=sample.get("slope_uncertainty_deg"),
                    effective_resolution_m=sample.get("effective_resolution_m"),
                    is_measured_data=True,
                )

                return TerrainResponse(
                    latitude=lat,
                    longitude=lon,
                    is_valid_point=True,
                    is_nodata=False,
                    elevation_m=sample["elevation_m"],
                    slope_deg=slope_val,
                    roughness_m=round(rough_val, 2),
                    aspect_deg=round(aspect_val, 1),
                    solar_illumination_pct=illum,
                    landing_hazard_classification=hazard_class,
                    dataset_info=dataset_info,
                    source_tier="Tier 2 (High-Resolution 5m Candidate Region)",
                    uncertainty_elevation_m=sample.get("elevation_uncertainty_m"),
                    uncertainty_slope_deg=sample.get("slope_uncertainty_deg"),
                    notes="Authentic NASA LOLA 5m/pixel high-resolution candidate landing site model (Site 01 Connecting Ridge).",
                )

        # -------------------------------------------------------------
        # 2. Product 90: LOLA South Pole 80m regional foundation DEM
        # -------------------------------------------------------------
        if source_id == "pgda_product90":
            sample = pgda_product90.sample_point(lat, lon)
            if sample and not sample.get("is_nodata", False):
                slope_val = sample.get("slope_deg")
                win_data, _, _ = pgda_product90.sample_window(lat, lon, radius_m=300.0)
                rough_val = 0.5
                aspect_val = 0.0
                if win_data is not None and win_data.size >= 9:
                    r_arr = rms_surface_roughness(win_data, kernel_size=3)
                    rough_val = float(r_arr[r_arr.shape[0] // 2, r_arr.shape[1] // 2])
                    s_arr, a_arr = horn_slope_and_aspect(win_data, 80.0, 80.0)
                    aspect_val = float(a_arr[a_arr.shape[0] // 2, a_arr.shape[1] // 2])
                    if slope_val is None:
                        slope_val = round(float(s_arr[s_arr.shape[0] // 2, s_arr.shape[1] // 2]), 2)
                hazard_class = cls._classify_hazard(slope_val, rough_val)
                illum = cls._estimate_illumination(lat, sample["elevation_m"])

                dataset_info = TerrainDatasetInfo(
                    dataset_name=sample["source_name"],
                    product_id="LDEM_80S_80MPP_ADJ",
                    spatial_resolution_m=80.0,
                    vertical_uncertainty_m=sample.get("elevation_uncertainty_m") or 1.0,
                    slope_method="NASA GSFC Precomputed 80m Slope + Horn Local Aspect",
                    roughness_baseline_m=240.0,
                    citation="Barker et al. (2016) PDS Geosciences Node / NASA GSFC",
                    observation_count=sample.get("observation_count"),
                    slope_uncertainty_deg=sample.get("slope_uncertainty_deg"),
                    effective_resolution_m=sample.get("effective_resolution_m"),
                    is_measured_data=True,
                )

                return TerrainResponse(
                    latitude=lat,
                    longitude=lon,
                    is_valid_point=True,
                    is_nodata=False,
                    elevation_m=sample["elevation_m"],
                    slope_deg=slope_val,
                    roughness_m=round(rough_val, 2),
                    aspect_deg=round(aspect_val, 1),
                    solar_illumination_pct=illum,
                    landing_hazard_classification=hazard_class,
                    dataset_info=dataset_info,
                    source_tier="Tier 1 (LOLA 80m Regional Foundation)",
                    uncertainty_elevation_m=sample.get("elevation_uncertainty_m"),
                    uncertainty_slope_deg=sample.get("slope_uncertainty_deg"),
                    notes="Authentic NASA LOLA 80m/pixel regional foundation terrain raster.",
                )

        # -------------------------------------------------------------
        # 3. Fallback: Calibrated baseline sample DEM
        # -------------------------------------------------------------
        return cls._fallback_sample_dem(lat, lon)

    @classmethod
    def _fallback_sample_dem(cls, lat: float, lon: float) -> TerrainResponse:
        """Calibrated fallback reading from sample DEM with explicit missing-real-raster notice."""
        elev_data, transform, res = dem_service.read_window_around_point(lat, lon, radius_m=1500.0)

        dataset_info = TerrainDatasetInfo(
            dataset_name=LOLA_DATASET_NAME,
            product_id="SAMPLE_SOUTH_POLE_CALIBRATED",
            spatial_resolution_m=LOLA_SPATIAL_RESOLUTION_M,
            vertical_uncertainty_m=LOLA_VERTICAL_ACCURACY_M,
            slope_method="Horn (1981) 8-neighbor gradient operator",
            roughness_baseline_m=LOLA_SPATIAL_RESOLUTION_M * 3.0,
            citation="Moonscape Baseline Sample DEM (Download Profile B for real 80m NASA GeoTIFF rasters)",
            is_measured_data=False,
        )

        if elev_data is None or elev_data.size == 0:
            return TerrainResponse(
                latitude=lat,
                longitude=lon,
                is_valid_point=False,
                is_nodata=False,
                elevation_m=None,
                slope_deg=None,
                roughness_m=None,
                aspect_deg=None,
                solar_illumination_pct=None,
                landing_hazard_classification="nodata",
                dataset_info=dataset_info,
                notes="DEM raster window could not be loaded for requested coordinate.",
            )

        center_row = elev_data.shape[0] // 2
        center_col = elev_data.shape[1] // 2
        point_elev = float(elev_data[center_row, center_col])

        if point_elev == LOLA_NODATA_VALUE or point_elev <= -30000 or np.isnan(point_elev):
            return TerrainResponse(
                latitude=lat,
                longitude=lon,
                is_valid_point=True,
                is_nodata=True,
                elevation_m=None,
                slope_deg=None,
                roughness_m=None,
                aspect_deg=None,
                solar_illumination_pct=None,
                landing_hazard_classification="nodata",
                dataset_info=dataset_info,
                notes="Target point is classified as LOLA nodata/shadow void.",
            )

        dx = res[0] if res[0] > 0 else 620.0
        dy = res[1] if res[1] > 0 else 620.0

        slopes, aspects = horn_slope_and_aspect(elev_data, dx, dy)
        roughness = rms_surface_roughness(elev_data)

        point_slope = float(slopes[center_row, center_col])
        point_aspect = float(aspects[center_row, center_col])
        point_roughness = float(roughness[center_row, center_col])

        illum = cls._estimate_illumination(lat, point_elev)
        hazard_class = cls._classify_hazard(point_slope, point_roughness)

        return TerrainResponse(
            latitude=lat,
            longitude=lon,
            is_valid_point=True,
            is_nodata=False,
            elevation_m=round(point_elev, 2),
            slope_deg=round(point_slope, 2),
            roughness_m=round(point_roughness, 2),
            aspect_deg=round(point_aspect, 1),
            solar_illumination_pct=illum,
            landing_hazard_classification=hazard_class,
            dataset_info=dataset_info,
            source_tier="Tier 0 (Calibrated Sample Baseline)",
            notes="NOTICE: Operating on calibrated sample DEM baseline. Download Phase 2 Profile B to enable authentic NASA 80m and 5m rasters.",
        )

    @staticmethod
    def _classify_hazard(slope_deg: Optional[float], roughness_m: Optional[float]) -> str:
        """Classifies landing safety based on slope and roughness."""
        if slope_deg is None:
            return "nodata"
        r = roughness_m or 0.0
        if slope_deg <= SLOPE_NOMINAL_MAX_DEG and r <= 0.5:
            return "safe"
        elif slope_deg <= SLOPE_CRITICAL_MAX_DEG and r <= 1.5:
            return "marginal"
        return "hazardous"

    @staticmethod
    def _estimate_illumination(lat: float, elevation_m: Optional[float]) -> float:
        """Estimates polar solar illumination percentage based on latitude and elevation."""
        elev = elevation_m or 0.0
        lat_factor = (lat - (-80.0)) / (-10.0)
        elev_factor = max(0.0, min(1.0, (elev + 2000.0) / 4000.0))
        return round(min(92.0, max(15.0, 50.0 + (lat_factor * 20.0) + (elev_factor * 22.0))), 1)


terrain_source_selector = TerrainSourceSelector()
