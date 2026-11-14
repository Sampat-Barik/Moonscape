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
        """Extracts topographic attributes at an exact lunar coordinate with 3x3 neighborhood gradient calculation."""
        dataset_info = TerrainDatasetInfo(
            dataset_name=LOLA_DATASET_NAME,
            product_id=LOLA_PRODUCT_ID,
            spatial_resolution_m=LOLA_SPATIAL_RESOLUTION_M,
            vertical_uncertainty_m=LOLA_VERTICAL_ACCURACY_M,
            slope_method="Horn (1981) 8-neighbor gradient operator",
            roughness_baseline_m=LOLA_SPATIAL_RESOLUTION_M * 3.0,
        )

        # Validate South Pole coverage
        if not (-90.0 <= lat <= -80.0):
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
                notes="Latitude outside lunar South Pole coverage area (-90.0° to -80.0°).",
            )

        # Read neighborhood around point (at least 2km radius to get clean 3x3 kernel)
        elev_data, transform, res = dem_service.read_window_around_point(lat, lon, radius_m=1500.0)

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

        # Center pixel indices
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

        # Mask nodata values before gradients
        valid_mask = (elev_data != LOLA_NODATA_VALUE) & (elev_data > -30000) & (~np.isnan(elev_data))
        if not valid_mask[center_row, center_col]:
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
                notes="Point is within nodata boundary mask.",
            )

        dx = res[0] if res[0] > 0 else 620.0
        dy = res[1] if res[1] > 0 else 620.0

        slopes, aspects = self.calculate_slope_and_aspect(elev_data, dx, dy)
        roughness = self.calculate_roughness_rms(elev_data)

        point_slope = float(slopes[center_row, center_col])
        point_aspect = float(aspects[center_row, center_col])
        point_roughness = float(roughness[center_row, center_col])

        # Estimate illumination based on elevation and latitude proximity to south pole
        # Higher elevated ridges closer to pole receive enhanced grazing solar incidence
        lat_factor = (lat - (-80.0)) / (-10.0)  # 0 at -80, 1 at -90
        elev_factor = max(0.0, min(1.0, (point_elev + 2000.0) / 4000.0))
        estimated_illumination = round(min(92.0, max(15.0, 50.0 + (lat_factor * 20.0) + (elev_factor * 22.0))), 1)

        # Landing hazard classification
        if point_slope <= SLOPE_NOMINAL_MAX_DEG and point_roughness <= 0.5:
            hazard_class = "safe"
        elif point_slope <= SLOPE_CRITICAL_MAX_DEG and point_roughness <= 1.5:
            hazard_class = "marginal"
        else:
            hazard_class = "hazardous"

        return TerrainResponse(
            latitude=lat,
            longitude=lon,
            is_valid_point=True,
            is_nodata=False,
            elevation_m=round(point_elev, 2),
            slope_deg=round(point_slope, 2),
            roughness_m=round(point_roughness, 2),
            aspect_deg=round(point_aspect, 1),
            solar_illumination_pct=estimated_illumination,
            landing_hazard_classification=hazard_class,
            dataset_info=dataset_info,
            notes="Measurement extracted from LOLA elevation grid with 3x3 spatial convolution.",
        )

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
