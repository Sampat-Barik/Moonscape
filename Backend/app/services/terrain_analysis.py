"""Scientific Terrain Analysis Engine for Moonscape.

Performs geodetically traceable calculations for:
1. Elevation: Point sampling, local min/max/mean, and relief variation.
2. Slope: NASA precomputed slope rasters or Horn (1981) 8-neighbor gradient with true pixel spacing.
3. Terrain Roughness: Local RMS residual height deviation with configurable neighborhood.
4. Physical Spatial Windowing: Strictly bounded by physical radius in meters on the lunar sphere.
"""

from collections import OrderedDict
from dataclasses import asdict, dataclass
import math
import threading
from typing import Any, Dict, Optional, Tuple
from affine import Affine
import numpy as np
from scipy.ndimage import uniform_filter

from Backend.app.core.constants import (
    LOLA_NODATA_VALUE,
    SCIENTIFIC_SAFETY_DISCLAIMER,
    SLOPE_CRITICAL_MAX_DEG,
    SLOPE_IDEAL_MAX_DEG,
    SLOPE_NOMINAL_MAX_DEG,
)
from Backend.app.services.nasa_data import NASASpatialWindow, nasa_data_manager
from maths.geodesy import DEFAULT_MOON_RADIUS_M
from maths.topography import (
    calculate_multi_baseline_roughness,
    horn_slope_and_aspect,
    slope_distribution_breakdown,
)


@dataclass
class ElevationMetrics:
    """Elevation measurements and statistical distribution within physical radius."""

    point_elevation_m: Optional[float]
    min_elevation_m: Optional[float]
    max_elevation_m: Optional[float]
    mean_elevation_m: Optional[float]
    elevation_variation_m: Optional[float]  # Relief: max - min
    std_dev_m: Optional[float]
    units: str = "meters"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SlopeMetrics:
    """Topographic slope metrics and hazard distribution within physical radius."""

    point_slope_deg: Optional[float]
    min_slope_deg: Optional[float]
    max_slope_deg: Optional[float]
    mean_slope_deg: Optional[float]
    std_dev_deg: Optional[float]
    source_type: str
    method: str
    units: str = "degrees"
    ideal_pct: float = 0.0
    acceptable_pct: float = 0.0
    marginal_pct: float = 0.0
    critical_hazardous_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RoughnessMetrics:
    """Surface roughness metrics evaluated across moving neighborhood baseline."""

    point_roughness_m: Optional[float]
    min_roughness_m: Optional[float]
    max_roughness_m: Optional[float]
    mean_roughness_m: Optional[float]
    std_dev_m: Optional[float]
    method: str
    kernel_size: int
    baseline_meters: float
    units: str = "meters"
    multi_baseline: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TerrainAnalysisResult:
    """Comprehensive scientific output for a spatial lunar terrain query."""

    latitude: float
    longitude: float
    radius_meters: float
    total_pixels_in_disc: int
    valid_pixels_in_disc: int
    nodata_pixels_in_disc: int
    elevation: ElevationMetrics
    slope: SlopeMetrics
    roughness: RoughnessMetrics
    aspect_deg: Optional[float]
    solar_illumination_pct: Optional[float]
    landing_hazard_classification: str
    metadata: Dict[str, Any]
    disclaimer: str = SCIENTIFIC_SAFETY_DISCLAIMER

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["elevation"] = self.elevation.to_dict()
        d["slope"] = self.slope.to_dict()
        d["roughness"] = self.roughness.to_dict()
        return d


class TerrainAnalysisEngine:
    """Scientific compute engine for lunar terrain elevation, slope, and roughness."""

    _analysis_cache: OrderedDict[str, "TerrainAnalysisResult"] = OrderedDict()
    _cache_capacity: int = 128
    _cache_lock = threading.Lock()

    # -------------------------------------------------------------------------
    # Pure Numerical & Algorithmic Methods (Testable on Synthetic Arrays)
    # -------------------------------------------------------------------------

    @staticmethod
    def create_spatial_distance_mask(
        shape: Tuple[int, int],
        transform: Affine,
        center_x: float,
        center_y: float,
        radius_m: float,
    ) -> np.ndarray:
        """Constructs a boolean 2D mask where True indicates pixels within physical radius in meters."""
        rows, cols = shape
        r_indices, c_indices = np.indices((rows, cols))

        # Affine coordinate mapping: x = c0 + c*dx + r*rot, y = f0 + c*rot + r*dy
        xs = transform.c + c_indices * transform.a + r_indices * transform.b
        ys = transform.f + c_indices * transform.d + r_indices * transform.e

        dist_sq = (xs - center_x) ** 2 + (ys - center_y) ** 2
        mask = dist_sq <= (radius_m**2)
        # If requested radius is smaller than cell resolution, ensure center cell is retained
        if not np.any(mask):
            min_idx = np.unravel_index(np.argmin(dist_sq), shape)
            mask[min_idx] = True
        return mask

    @staticmethod
    def compute_elevation_metrics(
        elev_data: np.ndarray,
        spatial_mask: np.ndarray,
        center_row: int,
        center_col: int,
        nodata_val: float = LOLA_NODATA_VALUE,
    ) -> ElevationMetrics:
        """Extracts point elevation and local disc elevation statistics."""
        valid_mask = spatial_mask & (elev_data != nodata_val) & (elev_data > -30000.0) & (~np.isnan(elev_data))
        valid_count = int(np.sum(valid_mask))

        # Center point measurement
        pt_elev = None
        if 0 <= center_row < elev_data.shape[0] and 0 <= center_col < elev_data.shape[1]:
            val = float(elev_data[center_row, center_col])
            if val != nodata_val and val > -30000.0 and not math.isnan(val):
                pt_elev = round(val, 2)

        if valid_count == 0:
            return ElevationMetrics(
                point_elevation_m=pt_elev,
                min_elevation_m=None,
                max_elevation_m=None,
                mean_elevation_m=None,
                elevation_variation_m=None,
                std_dev_m=None,
            )

        valid_vals = elev_data[valid_mask]
        min_e = float(np.min(valid_vals))
        max_e = float(np.max(valid_vals))
        mean_e = float(np.mean(valid_vals))
        std_e = float(np.std(valid_vals))

        return ElevationMetrics(
            point_elevation_m=pt_elev if pt_elev is not None else round(mean_e, 2),
            min_elevation_m=round(min_e, 2),
            max_elevation_m=round(max_e, 2),
            mean_elevation_m=round(mean_e, 2),
            elevation_variation_m=round(max_e - min_e, 2),
            std_dev_m=round(std_e, 2),
            units="meters",
        )

    @classmethod
    def compute_slope_metrics(
        cls,
        elev_data: np.ndarray,
        slope_data: Optional[np.ndarray],
        spatial_mask: np.ndarray,
        dx_meters: float,
        dy_meters: float,
        center_row: int,
        center_col: int,
        nodata_val: float = LOLA_NODATA_VALUE,
    ) -> Tuple[SlopeMetrics, Optional[float]]:
        """Extracts slope metrics from NASA precomputed slope map or Horn (1981) gradient.

        Returns:
            (SlopeMetrics, point_aspect_deg)
        """
        valid_mask = spatial_mask & (elev_data != nodata_val) & (elev_data > -30000.0) & (~np.isnan(elev_data))

        # 1. Prefer authentic NASA precomputed slope map if provided
        if slope_data is not None and slope_data.shape == elev_data.shape:
            slp_valid_mask = valid_mask & (slope_data != nodata_val) & (slope_data >= 0.0) & (~np.isnan(slope_data))
            if np.sum(slp_valid_mask) > 0:
                valid_slopes = slope_data[slp_valid_mask]
                pt_slope = None
                if 0 <= center_row < slope_data.shape[0] and 0 <= center_col < slope_data.shape[1]:
                    v = float(slope_data[center_row, center_col])
                    if v != nodata_val and v >= 0.0 and not math.isnan(v):
                        pt_slope = round(v, 2)

                dist = slope_distribution_breakdown(
                    slopes=slope_data,
                    valid_mask=slp_valid_mask,
                    ideal_max_deg=SLOPE_IDEAL_MAX_DEG,
                    nominal_max_deg=SLOPE_NOMINAL_MAX_DEG,
                    critical_max_deg=SLOPE_CRITICAL_MAX_DEG,
                )

                # Compute aspect from DEM elevation gradients
                _, aspects = horn_slope_and_aspect(elev_data, dx_meters, dy_meters)
                pt_aspect = float(aspects[center_row, center_col]) if 0 <= center_row < aspects.shape[0] else None

                return (
                    SlopeMetrics(
                        point_slope_deg=pt_slope if pt_slope is not None else round(float(np.mean(valid_slopes)), 2),
                        min_slope_deg=round(float(np.min(valid_slopes)), 2),
                        max_slope_deg=round(float(np.max(valid_slopes)), 2),
                        mean_slope_deg=round(float(np.mean(valid_slopes)), 2),
                        std_dev_deg=round(float(np.std(valid_slopes)), 2),
                        source_type="nasa_precomputed_product",
                        method="NASA GSFC Precomputed Topographic Slope Raster",
                        units="degrees",
                        ideal_pct=dist["ideal_pct"],
                        acceptable_pct=dist["acceptable_pct"],
                        marginal_pct=dist["marginal_pct"],
                        critical_hazardous_pct=dist["critical_hazardous_pct"],
                    ),
                    round(pt_aspect, 1) if pt_aspect is not None else None,
                )

        # 2. Derive slope from DEM using Horn (1981) 8-neighbor operator
        slopes, aspects = horn_slope_and_aspect(elev_data, dx_meters, dy_meters)
        valid_slopes = slopes[valid_mask]

        if valid_slopes.size == 0:
            return (
                SlopeMetrics(
                    point_slope_deg=None,
                    min_slope_deg=None,
                    max_slope_deg=None,
                    mean_slope_deg=None,
                    std_dev_deg=None,
                    source_type="horn_1981_dem_gradient",
                    method="Horn (1981) 8-Neighbor Gradient Operator on DEM",
                    units="degrees",
                ),
                None,
            )

        pt_slope = None
        pt_aspect = None
        if 0 <= center_row < slopes.shape[0] and 0 <= center_col < slopes.shape[1]:
            pt_slope = round(float(slopes[center_row, center_col]), 2)
            pt_aspect = round(float(aspects[center_row, center_col]), 1)

        dist = slope_distribution_breakdown(
            slopes=slopes,
            valid_mask=valid_mask,
            ideal_max_deg=SLOPE_IDEAL_MAX_DEG,
            nominal_max_deg=SLOPE_NOMINAL_MAX_DEG,
            critical_max_deg=SLOPE_CRITICAL_MAX_DEG,
        )

        return (
            SlopeMetrics(
                point_slope_deg=pt_slope if pt_slope is not None else round(float(np.mean(valid_slopes)), 2),
                min_slope_deg=round(float(np.min(valid_slopes)), 2),
                max_slope_deg=round(float(np.max(valid_slopes)), 2),
                mean_slope_deg=round(float(np.mean(valid_slopes)), 2),
                std_dev_deg=round(float(np.std(valid_slopes)), 2),
                source_type="horn_1981_dem_gradient",
                method="Horn (1981) 8-Neighbor Gradient Operator on DEM",
                units="degrees",
                ideal_pct=dist["ideal_pct"],
                acceptable_pct=dist["acceptable_pct"],
                marginal_pct=dist["marginal_pct"],
                critical_hazardous_pct=dist["critical_hazardous_pct"],
            ),
            pt_aspect,
        )

    @classmethod
    def compute_roughness_metrics(
        cls,
        elev_data: np.ndarray,
        spatial_mask: np.ndarray,
        dx_meters: float,
        center_row: int,
        center_col: int,
        kernel_size: int = 3,
        nodata_val: float = LOLA_NODATA_VALUE,
    ) -> RoughnessMetrics:
        """Calculates RMS surface roughness (residual height deviation from moving window neighborhood).

        Math:
            z_mean(r, c) = (1/K^2) * sum(z_neighborhood)
            residual(r, c) = z(r, c) - z_mean(r, c)
            RMS(r, c) = sqrt( (1/K^2) * sum(residual^2) )

        Args:
            kernel_size: Neighborhood window size (e.g. 3 for 3x3, 5 for 5x5).
            baseline_meters: Physical spatial baseline = kernel_size * dx_meters.
        """
        valid_mask = spatial_mask & (elev_data != nodata_val) & (elev_data > -30000.0) & (~np.isnan(elev_data))
        baseline_m = round(kernel_size * dx_meters, 1)

        # Protect against empty arrays
        if np.sum(valid_mask) == 0:
            return RoughnessMetrics(
                point_roughness_m=None,
                min_roughness_m=None,
                max_roughness_m=None,
                mean_roughness_m=None,
                std_dev_m=None,
                method="Root-Mean-Square (RMS) Residual Height Deviation from Local Neighborhood",
                kernel_size=kernel_size,
                baseline_meters=baseline_m,
                units="meters",
            )

        # Mask nodata values with regional mean before convolution to prevent edge bleeding
        cleaned_elev = elev_data.copy()
        regional_mean = float(np.mean(cleaned_elev[valid_mask]))
        cleaned_elev[~valid_mask] = regional_mean

        local_mean = uniform_filter(cleaned_elev, size=kernel_size, mode="reflect")
        residuals = cleaned_elev - local_mean
        variance_map = np.maximum(0.0, uniform_filter(residuals**2, size=kernel_size, mode="reflect"))
        roughness_map = np.sqrt(variance_map)

        valid_roughness = roughness_map[valid_mask]
        pt_roughness = None
        if 0 <= center_row < roughness_map.shape[0] and 0 <= center_col < roughness_map.shape[1]:
            pt_roughness = round(float(roughness_map[center_row, center_col]), 2)

        min_r = float(np.min(valid_roughness))
        max_r = float(np.max(valid_roughness))
        mean_r = float(np.mean(valid_roughness))
        std_r = float(np.std(valid_roughness))

        multi_base = calculate_multi_baseline_roughness(
            cleaned_elev,
            dx_meters=dx_meters,
            valid_mask=valid_mask,
        )

        return RoughnessMetrics(
            point_roughness_m=pt_roughness if pt_roughness is not None else round(mean_r, 2),
            min_roughness_m=round(min_r, 2),
            max_roughness_m=round(max_r, 2),
            mean_roughness_m=round(mean_r, 2),
            std_dev_m=round(std_r, 2),
            method="Root-Mean-Square (RMS) Residual Height Deviation from Local Neighborhood",
            kernel_size=kernel_size,
            baseline_meters=baseline_m,
            units="meters",
            multi_baseline=multi_base,
        )

    # -------------------------------------------------------------------------
    # Spatial End-to-End Analysis Method
    # -------------------------------------------------------------------------

    @classmethod
    def analyze_location(
        cls,
        lat_deg: float,
        lon_deg: float,
        radius_meters: float = 100.0,
        roughness_kernel_size: int = 3,
    ) -> Optional[TerrainAnalysisResult]:
        """Performs full scientific terrain analysis over physical distance radius."""
        cache_key = f"{lat_deg:.4f}:{lon_deg:.4f}:{int(radius_meters)}:{roughness_kernel_size}"
        with cls._cache_lock:
            if cache_key in cls._analysis_cache:
                cached_res = cls._analysis_cache[cache_key]
                cls._analysis_cache.move_to_end(cache_key)
                return cached_res

        window: Optional[NASASpatialWindow] = nasa_data_manager.get_spatial_window(
            lat_deg=lat_deg,
            lon_deg=lon_deg,
            radius_m=radius_meters,
        )
        if window is None or window.elevation_data is None or window.elevation_data.size == 0:
            return None

        elev_arr = window.elevation_data
        rows, cols = elev_arr.shape

        # Construct boolean mask corresponding to physical Euclidean disc of radius_meters
        disc_mask = cls.create_spatial_distance_mask(
            shape=(rows, cols),
            transform=window.transform,
            center_x=window.center_x_meters,
            center_y=window.center_y_meters,
            radius_m=radius_meters,
        )

        center_row = rows // 2
        center_col = cols // 2

        # Count disc pixel distribution
        total_in_disc = int(np.sum(disc_mask))
        valid_pixel_mask = disc_mask & (elev_arr != window.nodata_value) & (elev_arr > -30000.0) & (~np.isnan(elev_arr))
        valid_in_disc = int(np.sum(valid_pixel_mask))
        nodata_in_disc = total_in_disc - valid_in_disc

        # Compute Elevation Metrics
        elev_metrics = cls.compute_elevation_metrics(
            elev_data=elev_arr,
            spatial_mask=disc_mask,
            center_row=center_row,
            center_col=center_col,
            nodata_val=window.nodata_value,
        )

        # Compute Slope Metrics
        slope_metrics, aspect_deg = cls.compute_slope_metrics(
            elev_data=elev_arr,
            slope_data=window.slope_data,
            spatial_mask=disc_mask,
            dx_meters=window.dx_meters,
            dy_meters=window.dy_meters,
            center_row=center_row,
            center_col=center_col,
            nodata_val=window.nodata_value,
        )

        # Compute Roughness Metrics
        roughness_metrics = cls.compute_roughness_metrics(
            elev_data=elev_arr,
            spatial_mask=disc_mask,
            dx_meters=window.dx_meters,
            center_row=center_row,
            center_col=center_col,
            kernel_size=roughness_kernel_size,
            nodata_val=window.nodata_value,
        )

        # Illumination estimate
        elev_val = elev_metrics.point_elevation_m or 0.0
        lat_factor = (lat_deg - (-80.0)) / (-10.0)
        elev_factor = max(0.0, min(1.0, (elev_val + 2000.0) / 4000.0))
        estimated_illum = round(min(92.0, max(15.0, 50.0 + (lat_factor * 20.0) + (elev_factor * 22.0))), 1)

        # Landing hazard classification
        pt_slope = slope_metrics.point_slope_deg
        pt_rough = roughness_metrics.point_roughness_m
        if pt_slope is None:
            hazard_class = "nodata"
        elif pt_slope <= SLOPE_NOMINAL_MAX_DEG and (pt_rough is None or pt_rough <= 0.5):
            hazard_class = "safe"
        elif pt_slope <= SLOPE_CRITICAL_MAX_DEG and (pt_rough is None or pt_rough <= 1.5):
            hazard_class = "marginal"
        else:
            hazard_class = "hazardous"

        metadata = {
            "source_tier": window.source_tier,
            "source_id": window.source_id,
            "dataset_name": window.dataset_name,
            "product_id": window.product_id,
            "source_url": window.source_url,
            "citation": window.citation,
            "crs": window.crs,
            "reference_frame": window.reference_frame,
            "spatial_resolution_m": window.dx_meters,
            "is_measured_data": window.is_measured_data,
            "vertical_uncertainty_m": window.vertical_uncertainty_m,
            "slope_uncertainty_deg": window.slope_uncertainty_deg,
            "effective_resolution_m": window.effective_resolution_m,
            "observation_count": window.observation_count,
            "quality_warnings": window.quality_warnings,
            "slope_method": slope_metrics.method,
            "roughness_method": roughness_metrics.method,
            "roughness_baseline_m": roughness_metrics.baseline_meters,
            "roughness_multi_baseline": roughness_metrics.multi_baseline,
        }

        result = TerrainAnalysisResult(
            latitude=lat_deg,
            longitude=lon_deg,
            radius_meters=radius_meters,
            total_pixels_in_disc=total_in_disc,
            valid_pixels_in_disc=valid_in_disc,
            nodata_pixels_in_disc=nodata_in_disc,
            elevation=elev_metrics,
            slope=slope_metrics,
            roughness=roughness_metrics,
            aspect_deg=aspect_deg,
            solar_illumination_pct=estimated_illum,
            landing_hazard_classification=hazard_class,
            metadata=metadata,
            disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
        )

        with cls._cache_lock:
            if len(cls._analysis_cache) >= cls._cache_capacity:
                cls._analysis_cache.popitem(last=False)
            cls._analysis_cache[cache_key] = result

        return result


terrain_analysis_engine = TerrainAnalysisEngine()
