"""Scientific computing service for terrain slope, roughness, and landing safety analysis."""

import uuid
from typing import Optional, Tuple
import numpy as np

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
from app.schemas.terrain import (
    ElevationSummary,
    RoughnessSummary,
    SlopeSummary,
    TerrainDatasetInfo,
    TerrainMeshResponse,
    TerrainResponse,
)
from app.services.geospatial.coordinate_manager import coordinate_manager
from app.services.illumination import illumination_service
from app.services.site_scoring import site_scoring_engine
from app.services.terrain_analysis import terrain_analysis_engine
from app.schemas.scoring import ScoreRequest
from app.services.analysis_store import analysis_store
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

    def get_point_terrain(self, lat: float, lon: float, radius_m: float = 50.0) -> TerrainResponse:
        """Extracts topographic attributes at coordinate using highest-resolution authentic NASA data."""
        is_valid_coord, val_msg = coordinate_manager.validate_coordinates(lat, lon)
        if not is_valid_coord or not coordinate_manager.is_in_analysis_region(lat):
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
                    source_url="https://pgda.gsfc.nasa.gov/products/90",
                    crs="ESRI:104903 (Lunar South Polar Stereographic)",
                    is_measured_data=False,
                ),
                notes=f"Coordinates outside lunar South Pole exploration region (-90.0° to -70.0°). {val_msg}",
            )

        res = terrain_analysis_engine.analyze_location(
            lat_deg=lat,
            lon_deg=lon,
            radius_meters=radius_m,
            roughness_kernel_size=3,
        )

        if res is None:
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
                notes="Terrain data could not be acquired for requested coordinates.",
            )

        # Build detailed sub-summaries
        elev_summary = ElevationSummary(
            point_m=res.elevation.point_elevation_m,
            min_m=res.elevation.min_elevation_m,
            max_m=res.elevation.max_elevation_m,
            mean_m=res.elevation.mean_elevation_m,
            variation_m=res.elevation.elevation_variation_m,
            std_dev_m=res.elevation.std_dev_m,
            units=res.elevation.units,
        )

        slope_summary = SlopeSummary(
            point_deg=res.slope.point_slope_deg,
            min_deg=res.slope.min_slope_deg,
            max_deg=res.slope.max_slope_deg,
            mean_deg=res.slope.mean_slope_deg,
            p95_deg=res.slope.p95_slope_deg,
            std_dev_deg=res.slope.std_dev_deg,
            method=res.slope.method,
            units=res.slope.units,
            ideal_pct=res.slope.ideal_pct,
            acceptable_pct=res.slope.acceptable_pct,
            marginal_pct=res.slope.marginal_pct,
            critical_hazardous_pct=res.slope.critical_hazardous_pct,
        )

        rough_summary = RoughnessSummary(
            point_m=res.roughness.point_roughness_m,
            min_m=res.roughness.min_roughness_m,
            max_m=res.roughness.max_roughness_m,
            mean_m=res.roughness.mean_roughness_m,
            std_dev_m=res.roughness.std_dev_m,
            method=res.roughness.method,
            kernel_size=res.roughness.kernel_size,
            baseline_m=res.roughness.baseline_meters,
            units=res.roughness.units,
            multi_baseline=res.roughness.multi_baseline,
        )

        dataset_info = TerrainDatasetInfo(
            dataset_name=res.metadata.get("dataset_name", LOLA_DATASET_NAME),
            product_id=res.metadata.get("product_id", LOLA_PRODUCT_ID),
            spatial_resolution_m=res.metadata.get("spatial_resolution_m", 80.0),
            vertical_uncertainty_m=res.metadata.get("vertical_uncertainty_m") or 1.0,
            slope_method=res.metadata.get("slope_method", "Horn (1981)"),
            roughness_baseline_m=res.metadata.get("roughness_baseline_m", 15.0),
            citation=res.metadata.get("citation"),
            observation_count=res.metadata.get("observation_count"),
            slope_uncertainty_deg=res.metadata.get("slope_uncertainty_deg"),
            effective_resolution_m=res.metadata.get("effective_resolution_m"),
            is_measured_data=res.metadata.get("is_measured_data", True),
            source_url=res.metadata.get("source_url"),
            crs=res.metadata.get("crs"),
            reference_frame=res.metadata.get("reference_frame"),
            quality_warnings=res.metadata.get("quality_warnings"),
        )

        return TerrainResponse(
            latitude=lat,
            longitude=lon,
            is_valid_point=True,
            is_nodata=(res.valid_pixels_in_disc == 0),
            elevation_m=res.elevation.point_elevation_m,
            slope_deg=res.slope.point_slope_deg,
            roughness_m=res.roughness.point_roughness_m,
            aspect_deg=res.aspect_deg,
            solar_illumination_pct=res.solar_illumination_pct,
            landing_hazard_classification=res.landing_hazard_classification,
            dataset_info=dataset_info,
            source_tier=res.metadata.get("source_tier"),
            uncertainty_elevation_m=res.metadata.get("vertical_uncertainty_m"),
            uncertainty_slope_deg=res.metadata.get("slope_uncertainty_deg"),
            notes=f"Analysis computed over physical disc of {radius_m:.1f}m radius.",
            analysis_radius_m=radius_m,
            elevation_summary=elev_summary,
            slope_summary=slope_summary,
            roughness_summary=rough_summary,
            total_pixels_in_disc=res.total_pixels_in_disc,
            valid_pixels_in_disc=res.valid_pixels_in_disc,
            nodata_pixels_in_disc=res.nodata_pixels_in_disc,
        )

    def analyze_landing_zone(self, req: AnalysisRunRequest) -> AnalysisRunResponse:
        """Executes full landing zone spatial analysis bounded by physical radius in meters."""
        analysis_id = f"ANL-{uuid.uuid4().hex[:8].upper()}"

        res = terrain_analysis_engine.analyze_location(
            lat_deg=req.center_lat,
            lon_deg=req.center_lon,
            radius_meters=req.radius_meters,
            roughness_kernel_size=req.roughness_kernel_size,
        )

        if res is None or res.valid_pixels_in_disc == 0:
            illum_summary = illumination_service.analyze_illumination(
                lat_deg=req.center_lat,
                lon_deg=req.center_lon,
                radius_m=req.radius_meters,
                epoch_iso=req.epoch_iso,
                time_period=req.time_period or "annual_cycle",
            )
            suitability_eval = site_scoring_engine.evaluate_suitability(
                ScoreRequest(
                    slope_deg=None,
                    roughness_m=None,
                    illumination_pct=illum_summary.cumulative_illumination_pct,
                )
            )
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
                dataset_metadata={"error": "Terrain data unavailable for requested coordinate."},
                disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
                illumination=illum_summary,
                suitability=suitability_eval,
            )

        elev_stats = TopographicStats(
            min_value=res.elevation.min_elevation_m,
            max_value=res.elevation.max_elevation_m,
            mean_value=res.elevation.mean_elevation_m,
            median_value=res.elevation.point_elevation_m,
            std_dev=res.elevation.std_dev_m,
            variation=res.elevation.elevation_variation_m,
            units=res.elevation.units,
        )

        slope_stats = TopographicStats(
            min_value=res.slope.min_slope_deg,
            max_value=res.slope.max_slope_deg,
            mean_value=res.slope.mean_slope_deg,
            median_value=res.slope.point_slope_deg,
            std_dev=res.slope.std_dev_deg,
            p95_value=res.slope.p95_slope_deg,
            units=res.slope.units,
        )

        slope_distribution = SlopeDistribution(
            ideal_pct=res.slope.ideal_pct,
            acceptable_pct=res.slope.acceptable_pct,
            marginal_pct=res.slope.marginal_pct,
            critical_hazardous_pct=res.slope.critical_hazardous_pct,
        )

        # Safe touchdown fraction: fraction of valid area meeting max slope & max roughness constraints
        # Approximate from distribution percentages and roughness mean
        slope_safe_pct = res.slope.ideal_pct + (res.slope.acceptable_pct if req.max_acceptable_slope_deg >= 10.0 else 0.0)
        rough_factor = 1.0 if (res.roughness.mean_roughness_m or 0.0) <= req.max_acceptable_roughness_m else 0.5
        safe_fraction_pct = round(float(slope_safe_pct * rough_factor), 1)

        # Preliminary feasibility determination
        mean_s = res.slope.mean_slope_deg or 99.0
        if safe_fraction_pct >= 75.0 and mean_s <= req.max_acceptable_slope_deg:
            feasibility = "favorable"
        elif safe_fraction_pct >= 45.0:
            feasibility = "marginal"
        else:
            feasibility = "unfavorable"

        metadata = dict(res.metadata)
        metadata["analysis_radius_meters"] = req.radius_meters
        metadata["max_acceptable_slope_deg"] = req.max_acceptable_slope_deg
        metadata["max_acceptable_roughness_m"] = req.max_acceptable_roughness_m

        illum_summary = illumination_service.analyze_illumination(
            lat_deg=req.center_lat,
            lon_deg=req.center_lon,
            radius_m=req.radius_meters,
            epoch_iso=req.epoch_iso,
            time_period=req.time_period or "annual_cycle",
        )

        suitability_eval = site_scoring_engine.evaluate_suitability(
            ScoreRequest(
                slope_deg=res.slope.mean_slope_deg,
                roughness_m=res.roughness.mean_roughness_m,
                elevation_m=res.elevation.mean_elevation_m,
                illumination_pct=illum_summary.cumulative_illumination_pct,
            )
        )

        run_result = AnalysisRunResponse(
            analysis_id=analysis_id,
            center_lat=req.center_lat,
            center_lon=req.center_lon,
            radius_meters=req.radius_meters,
            total_samples=res.total_pixels_in_disc,
            valid_samples=res.valid_pixels_in_disc,
            nodata_samples=res.nodata_pixels_in_disc,
            elevation=elev_stats,
            slope=slope_stats,
            slope_distribution=slope_distribution,
            roughness_mean_m=res.roughness.mean_roughness_m,
            roughness_max_m=res.roughness.max_roughness_m,
            roughness_baseline_m=res.roughness.baseline_meters,
            roughness_method=res.roughness.method,
            roughness_multi_baseline=res.roughness.multi_baseline,
            slope_method=res.slope.method,
            safe_touchdown_fraction_pct=safe_fraction_pct,
            preliminary_feasibility=feasibility,
            dataset_metadata=metadata,
            disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
            illumination=illum_summary,
            suitability=suitability_eval,
        )

        analysis_store.save(run_result)
        return run_result

    def get_terrain_mesh(
        self,
        lat: float,
        lon: float,
        radius_m: float = 500.0,
        grid_size: int = 64,
    ) -> TerrainMeshResponse:
        """Extracts downsampled elevation and slope grids for 3D terrain relief visualization."""
        from app.services.dem_service import dem_service
        from app.services.nasa_data import nasa_data_manager
        import scipy.ndimage

        # Validate coordinate
        is_valid, _ = coordinate_manager.validate_coordinates(lat, lon)
        if not is_valid or not coordinate_manager.is_in_analysis_region(lat):
            cx, cy = coordinate_manager.to_polar_stereographic(lat, lon)
            empty_grid = [[0.0] * grid_size for _ in range(grid_size)]
            return TerrainMeshResponse(
                status="outside_polar_zone",
                latitude=lat,
                longitude=lon,
                radius_m=radius_m,
                grid_size=grid_size,
                resolution_m=round((radius_m * 2.0) / grid_size, 2),
                center_x_polar_m=round(cx, 1),
                center_y_polar_m=round(cy, 1),
                min_elevation_m=0.0,
                max_elevation_m=0.0,
                mean_elevation_m=0.0,
                relief_m=0.0,
                elevation_grid=empty_grid,
                slope_grid=empty_grid,
                dataset_name=LOLA_DATASET_NAME,
                product_id=LOLA_PRODUCT_ID,
                crs="ESRI:104903 (Lunar South Polar Stereographic)",
                disclaimer="Coordinates outside supported lunar South Pole region (80°S-90°S).",
            )

        cx, cy = coordinate_manager.to_polar_stereographic(lat, lon)
        win = nasa_data_manager.get_spatial_window(lat, lon, radius_m)

        if win is None or win.elevation_data is None or win.elevation_data.size == 0:
            pt_elev, _, _ = dem_service.get_elevation_at_point(lat, lon)
            base_elev = float(pt_elev if pt_elev is not None else 0.0)
            flat_grid = [[round(base_elev, 2)] * grid_size for _ in range(grid_size)]
            zero_slope = [[0.0] * grid_size for _ in range(grid_size)]
            return TerrainMeshResponse(
                status="single_point_fallback",
                latitude=lat,
                longitude=lon,
                radius_m=radius_m,
                grid_size=grid_size,
                resolution_m=round((radius_m * 2.0) / grid_size, 2),
                center_x_polar_m=round(cx, 1),
                center_y_polar_m=round(cy, 1),
                min_elevation_m=round(base_elev, 2),
                max_elevation_m=round(base_elev, 2),
                mean_elevation_m=round(base_elev, 2),
                relief_m=0.0,
                elevation_grid=flat_grid,
                slope_grid=zero_slope,
                dataset_name=LOLA_DATASET_NAME,
                product_id=LOLA_PRODUCT_ID,
                crs="ESRI:104903",
                disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
            )

        elev = win.elevation_data.astype(np.float32).copy()
        nodata_mask = (elev <= -30000.0) | (elev == LOLA_NODATA_VALUE) | np.isnan(elev)

        if np.all(nodata_mask):
            base_elev = 0.0
            elev.fill(base_elev)
        elif np.any(nodata_mask):
            valid_mean = float(np.mean(elev[~nodata_mask]))
            elev[nodata_mask] = valid_mean

        # Calculate slope if not already present
        if win.slope_data is not None and win.slope_data.shape == elev.shape:
            slope = win.slope_data.astype(np.float32).copy()
            slope_nodata = (slope < 0) | np.isnan(slope)
            if np.any(slope_nodata):
                slope[slope_nodata] = 0.0
        else:
            slope, _ = horn_slope_and_aspect(elev, win.dx_meters, win.dy_meters)

        # Resample to grid_size x grid_size
        r_in, c_in = elev.shape
        zoom_r = float(grid_size) / max(r_in, 1)
        zoom_c = float(grid_size) / max(c_in, 1)

        resampled_elev = scipy.ndimage.zoom(elev, (zoom_r, zoom_c), order=1)
        resampled_slope = scipy.ndimage.zoom(slope, (zoom_r, zoom_c), order=1)

        # Ensure exact shape
        resampled_elev = resampled_elev[:grid_size, :grid_size]
        resampled_slope = resampled_slope[:grid_size, :grid_size]

        min_e = float(np.min(resampled_elev))
        max_e = float(np.max(resampled_elev))
        mean_e = float(np.mean(resampled_elev))
        relief = float(max_e - min_e)
        eff_res = (radius_m * 2.0) / grid_size

        return TerrainMeshResponse(
            status="ready",
            latitude=lat,
            longitude=lon,
            radius_m=radius_m,
            grid_size=grid_size,
            resolution_m=round(eff_res, 2),
            center_x_polar_m=round(cx, 1),
            center_y_polar_m=round(cy, 1),
            min_elevation_m=round(min_e, 2),
            max_elevation_m=round(max_e, 2),
            mean_elevation_m=round(mean_e, 2),
            relief_m=round(relief, 2),
            elevation_grid=[[round(float(v), 2) for v in row] for row in resampled_elev],
            slope_grid=[[round(float(v), 1) for v in row] for row in resampled_slope],
            dataset_name=win.dataset_name,
            product_id=win.product_id,
            crs=win.crs,
            disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
        )


terrain_service = TerrainService()
