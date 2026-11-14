"""Scientific computing service for terrain slope, roughness, and landing safety analysis."""

import uuid
from typing import Optional, Tuple
import numpy as np
from scipy.ndimage import convolve

from app.core.constants import (
    LOLA_DATASET_NAME,
    LOLA_NODATA_VALUE,
    LOLA_PRODUCT_ID,
    LOLA_SPATIAL_RESOLUTION_M,
    LOLA_VERTICAL_ACCURACY_M,
    SCIENTIFIC_SAFETY_DISCLAIMER,
    SLOPE_CRITICAL_MAX_DEG,
    SLOPE_IDEAL_MAX_DEG,
    SLOPE_NOMINAL_MAX_DEG,
)
from app.core.logging import logger
from app.schemas.analysis import (
    AnalysisRunRequest,
    AnalysisRunResponse,
    SlopeDistribution,
    TopographicStats,
)
from app.schemas.terrain import TerrainDatasetInfo, TerrainResponse
from app.services.dem_service import dem_service
from Backend.app.services.geospatial.terrain_source_selector import terrain_source_selector
from maths.topography import (
    horn_slope_and_aspect,
    rms_surface_roughness,
    slope_distribution_breakdown,
)


class TerrainService:
    """Computes geodetic slopes (Horn 1981 method), surface roughness, and touchdown feasibility."""

    @staticmethod
    def calculate_slope_and_aspect(
        elevation: np.ndarray,
        dx: float,
        dy: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Calculates topographic slope and aspect using Horn's (1981) operator from the maths package."""
        return horn_slope_and_aspect(elevation, dx, dy)

    @staticmethod
    def calculate_roughness_rms(elevation: np.ndarray, kernel_size: int = 3) -> np.ndarray:
        """Calculates surface roughness (RMS height deviation) using the maths package."""
        return rms_surface_roughness(elevation, kernel_size=kernel_size)

    def get_point_terrain(self, lat: float, lon: float) -> TerrainResponse:
        """Extracts topographic attributes at coordinate using highest-resolution authentic NASA data."""
        return terrain_source_selector.get_point_terrain(lat=lat, lon=lon)

    def analyze_landing_zone(self, req: AnalysisRunRequest) -> AnalysisRunResponse:
        """Executes a full landing ellipse spatial analysis within the specified radial footprint."""
        elev_data, transform, res = dem_service.read_window_around_point(
            lat_deg=req.center_lat,
            lon_deg=req.center_lon,
            radius_m=req.radius_meters,
        )

        analysis_id = f"ANL-{uuid.uuid4().hex[:8].upper()}"

        if elev_data is None or elev_data.size == 0:
            return AnalysisRunResponse(
                analysis_id=analysis_id,
                center_lat=req.center_lat,
                center_lon=req.center_lon,
                radius_meters=req.radius_meters,
                total_samples=0,
                valid_samples=0,
                nodata_samples=0,
                elevation=TopographicStats(units="meters"),
                slope=TopographicStats(units="degrees"),
                slope_distribution=SlopeDistribution(
                    ideal_pct=0.0,
                    acceptable_pct=0.0,
                    marginal_pct=0.0,
                    critical_hazardous_pct=0.0,
                ),
                roughness_mean_m=None,
                safe_touchdown_fraction_pct=0.0,
                preliminary_feasibility="insufficient_data",
                dataset_metadata={"error": "Raster window unavailable"},
                disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
            )

        total_samples = int(elev_data.size)
        valid_mask = (elev_data != LOLA_NODATA_VALUE) & (elev_data > -30000) & (~np.isnan(elev_data))
        valid_samples = int(np.sum(valid_mask))
        nodata_samples = total_samples - valid_samples

        if valid_samples < 4:
            return AnalysisRunResponse(
                analysis_id=analysis_id,
                center_lat=req.center_lat,
                center_lon=req.center_lon,
                radius_meters=req.radius_meters,
                total_samples=total_samples,
                valid_samples=valid_samples,
                nodata_samples=nodata_samples,
                elevation=TopographicStats(units="meters"),
                slope=TopographicStats(units="degrees"),
                slope_distribution=SlopeDistribution(
                    ideal_pct=0.0,
                    acceptable_pct=0.0,
                    marginal_pct=0.0,
                    critical_hazardous_pct=0.0,
                ),
                roughness_mean_m=None,
                safe_touchdown_fraction_pct=0.0,
                preliminary_feasibility="insufficient_data",
                dataset_metadata={"warning": "Too few valid samples in evaluated zone"},
                disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
            )

        valid_elev = elev_data[valid_mask]
        elev_stats = TopographicStats(
            min_value=round(float(np.min(valid_elev)), 2),
            max_value=round(float(np.max(valid_elev)), 2),
            mean_value=round(float(np.mean(valid_elev)), 2),
            median_value=round(float(np.median(valid_elev)), 2),
            std_dev=round(float(np.std(valid_elev)), 2),
            units="meters",
        )

        dx = res[0] if res[0] > 0 else 620.0
        dy = res[1] if res[1] > 0 else 620.0
        slopes, _ = self.calculate_slope_and_aspect(elev_data, dx, dy)
        valid_slopes = slopes[valid_mask]

        slope_stats = TopographicStats(
            min_value=round(float(np.min(valid_slopes)), 2),
            max_value=round(float(np.max(valid_slopes)), 2),
            mean_value=round(float(np.mean(valid_slopes)), 2),
            median_value=round(float(np.median(valid_slopes)), 2),
            std_dev=round(float(np.std(valid_slopes)), 2),
            units="degrees",
        )

        # Slope distribution percentages via maths package
        breakdown = slope_distribution_breakdown(
            slopes=slopes,
            valid_mask=valid_mask,
            ideal_max_deg=SLOPE_IDEAL_MAX_DEG,
            nominal_max_deg=SLOPE_NOMINAL_MAX_DEG,
            critical_max_deg=SLOPE_CRITICAL_MAX_DEG,
        )
        slope_distribution = SlopeDistribution(
            ideal_pct=breakdown["ideal_pct"],
            acceptable_pct=breakdown["acceptable_pct"],
            marginal_pct=breakdown["marginal_pct"],
            critical_hazardous_pct=breakdown["critical_hazardous_pct"],
        )

        roughness = self.calculate_roughness_rms(elev_data)
        valid_roughness = roughness[valid_mask]
        roughness_mean = round(float(np.mean(valid_roughness)), 2)

        # Safe touchdown fraction: slope <= max_acceptable AND roughness <= max_acceptable
        safe_mask = (valid_slopes <= req.max_acceptable_slope_deg) & (valid_roughness <= req.max_acceptable_roughness_m)
        safe_fraction_pct = round(float(np.sum(safe_mask) / valid_samples * 100.0), 1)

        # Feasibility determination
        if safe_fraction_pct >= 75.0 and slope_stats.mean_value <= req.max_acceptable_slope_deg:
            feasibility = "favorable"
        elif safe_fraction_pct >= 45.0:
            feasibility = "marginal"
        else:
            feasibility = "unfavorable"

        metadata = {
            "source_instrument": LOLA_DATASET_NAME,
            "product_id": LOLA_PRODUCT_ID,
            "spatial_resolution_meters": dx,
            "slope_operator": "Horn 1981",
            "eval_radius_meters": req.radius_meters,
        }

        return AnalysisRunResponse(
            analysis_id=analysis_id,
            center_lat=req.center_lat,
            center_lon=req.center_lon,
            radius_meters=req.radius_meters,
            total_samples=total_samples,
            valid_samples=valid_samples,
            nodata_samples=nodata_samples,
            elevation=elev_stats,
            slope=slope_stats,
            slope_distribution=slope_distribution,
            roughness_mean_m=roughness_mean,
            safe_touchdown_fraction_pct=safe_fraction_pct,
            preliminary_feasibility=feasibility,
            dataset_metadata=metadata,
            disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
        )


terrain_service = TerrainService()
