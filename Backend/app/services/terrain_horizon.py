"""360-Degree Radial Terrain Horizon Engine with Lunar Spherical Curvature.

Calculates high-precision topocentric horizon profiles around any candidate lunar landing site
by casting radial elevation rays across digital elevation models (DEMs).

Physical Mathematics:
---------------------
1. Spherical Lunar Curvature:
   Because the Moon's mean radius is R_moon = 1,737,400 m (over 3.6x smaller than Earth),
   the geometric surface drop over horizontal distance r is:
       Delta_z_curvature = r^2 / (2 * R_moon)
   At 5 km, curvature drop is ~7.2 meters; at 10 km, ~28.8 meters; at 20 km, ~115.1 meters.

2. Topocentric Elevation Angle:
   From an observer at surface elevation z_0 with lander mast height h_mast (default 2.0m),
   the apparent angle to terrain elevation z(r) at radial distance r is:
       theta(r) = arctan( (z(r) - Delta_z_curvature - (z_0 + h_mast)) / r )

3. Horizon Profile Mask H(alpha):
   The maximum obstacle angle along azimuth ray alpha defines the horizon:
       H(alpha) = max_r theta(r)
   Once cached, H(alpha) enables O(1) instantaneous line-of-sight determination
   for solar illumination and Earth communication visibility at any simulation epoch.
"""

from collections import OrderedDict
from dataclasses import asdict, dataclass
import math
import threading
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.core.constants import LOLA_NODATA_VALUE, MOON_RADIUS_METERS
from app.core.logging import logger
from app.services.dem_service import dem_service
from app.services.geospatial.coordinate_manager import coordinate_manager
from app.services.geospatial.raster_sampler import raster_sampler
from app.services.geospatial.terrain_source_selector import terrain_source_selector
from app.config.dataset_settings import dataset_settings


@dataclass
class HorizonObstacle:
    """Attributes of the critical terrain feature forming the horizon at a given azimuth."""

    azimuth_deg: float
    horizon_elevation_deg: float
    distance_meters: float
    terrain_elevation_m: float
    curvature_drop_m: float


@dataclass
class RadialHorizonProfile:
    """360-degree topocentric radial horizon profile surrounding a lunar site."""

    center_lat: float
    center_lon: float
    observer_elevation_m: float
    mast_height_m: float
    search_radius_m: float
    num_azimuths: int
    azimuth_step_deg: float

    # Angular distribution
    azimuths_deg: List[float]
    horizon_elevations_deg: List[float]

    # Global summary statistics
    min_horizon_deg: float
    max_horizon_deg: float
    mean_horizon_deg: float
    max_obstacle_azimuth_deg: float
    max_obstacle_distance_m: float
    sky_view_factor: float  # Fraction of upper hemisphere unobstructed [0.0 to 1.0]

    dataset_name: str
    crs: str = "ESRI:104903"
    curvature_corrected: bool = True

    def get_horizon_elevation(self, azimuth_deg: float) -> float:
        """Returns circularly interpolated horizon elevation angle (degrees) for any target azimuth."""
        norm_az = azimuth_deg % 360.0
        n = len(self.azimuths_deg)
        if n == 0:
            return 0.0

        idx_float = norm_az / self.azimuth_step_deg
        idx_lower = int(math.floor(idx_float)) % n
        idx_upper = (idx_lower + 1) % n

        frac = idx_float - math.floor(idx_float)
        h_lower = self.horizon_elevations_deg[idx_lower]
        h_upper = self.horizon_elevations_deg[idx_upper]

        return round(float(h_lower + frac * (h_upper - h_lower)), 3)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TerrainHorizonEngine:
    """Thread-safe engine for calculating and caching 360-degree topocentric lunar horizon profiles."""

    def __init__(self, cache_capacity: int = 64):
        self._cache: OrderedDict[str, RadialHorizonProfile] = OrderedDict()
        self._cache_capacity = cache_capacity
        self._lock = threading.Lock()

    def _make_cache_key(self, lat: float, lon: float, radius_m: float, mast_h: float, num_az: int) -> str:
        return f"{lat:.4f}:{lon:.4f}:{int(radius_m)}:{mast_h:.1f}:{num_az}"

    def compute_horizon_profile(
        self,
        lat_deg: float,
        lon_deg: float,
        search_radius_m: float = 10000.0,
        mast_height_m: float = 2.0,
        num_azimuths: int = 72,
    ) -> RadialHorizonProfile:
        """Computes or retrieves from cache the 360-degree radial horizon profile with lunar curvature correction.

        Args:
            lat_deg: Site latitude (-90 to -80 deg).
            lon_deg: Site longitude (-180 to 360 deg).
            search_radius_m: Maximum radial ray trace distance in meters (e.g. 5000 to 25000 m).
            mast_height_m: Height of observer lander solar array or antenna above surface in meters.
            num_azimuths: Number of azimuth rays (default 72 rays = 5.0 degree spacing).
        """
        norm_lon = coordinate_manager.normalize_longitude(lon_deg, target_range="360")
        cache_key = self._make_cache_key(lat_deg, norm_lon, search_radius_m, mast_height_m, num_azimuths)

        with self._lock:
            if cache_key in self._cache:
                profile = self._cache[cache_key]
                self._cache.move_to_end(cache_key)
                return profile

        # Select best available DEM
        source_id = terrain_source_selector.select_source(lat_deg, norm_lon)
        dem_path = None
        dataset_label = "Sample Baseline DEM (500m)"

        if source_id == "pgda_product78":
            p78_def = dataset_settings.datasets.get("pgda78_site01_surf")
            if p78_def and p78_def.absolute_local_path.exists():
                dem_path = p78_def.absolute_local_path
                dataset_label = "NASA PGDA Product 78 (5m Site 01 DEM)"
        elif source_id == "pgda_product90":
            p90_def = dataset_settings.datasets.get("pgda90_ldem")
            if p90_def and p90_def.absolute_local_path.exists():
                dem_path = p90_def.absolute_local_path
                dataset_label = "NASA PGDA Product 90 (80m Regional DEM)"

        # Read DEM window
        if dem_path is not None:
            elev_arr, transform, res = raster_sampler.sample_raster_window(
                dem_path, lat_deg, norm_lon, radius_m=search_radius_m
            )
        else:
            elev_arr, transform, res = dem_service.read_window_around_point(
                lat_deg, norm_lon, radius_m=search_radius_m
            )

        if elev_arr is None or elev_arr.size == 0 or transform is None:
            logger.warning("DEM data unavailable for horizon ray-tracing at (%.4f, %.4f); using flat horizon.", lat_deg, norm_lon)
            return self._build_flat_fallback(lat_deg, norm_lon, search_radius_m, mast_height_m, num_azimuths)

        # Center pixel coordinates
        center_x, center_y = coordinate_manager.to_polar_stereographic(lat_deg, norm_lon)
        inv_transform = ~transform

        # Center surface elevation
        c_col = inv_transform.c + center_x * inv_transform.a + center_y * inv_transform.b
        c_row = inv_transform.f + center_x * inv_transform.d + center_y * inv_transform.e
        c_row_int = int(round(c_row))
        c_col_int = int(round(c_col))

        if 0 <= c_row_int < elev_arr.shape[0] and 0 <= c_col_int < elev_arr.shape[1]:
            center_elev = float(elev_arr[c_row_int, c_col_int])
            if center_elev <= -30000.0 or np.isnan(center_elev):
                valid_elevs = elev_arr[(elev_arr > -30000.0) & (~np.isnan(elev_arr))]
                center_elev = float(np.mean(valid_elevs)) if valid_elevs.size > 0 else 0.0
        else:
            center_elev = 0.0

        observer_z = center_elev + mast_height_m
        dx = res[0] if res[0] > 0 else 5.0

        # Step size along ray
        ray_step_m = max(dx, 10.0)
        num_radial_steps = max(5, int(search_radius_m / ray_step_m))
        radial_distances = np.linspace(ray_step_m, search_radius_m, num_radial_steps, endpoint=True)

        # Precompute curvature drops: r^2 / (2 * R_moon)
        curvature_drops = (radial_distances**2) / (2.0 * MOON_RADIUS_METERS)

        azimuth_step = 360.0 / num_azimuths
        azimuths: List[float] = []
        horizon_elevations: List[float] = []

        max_obstacle_angle = -90.0
        max_obstacle_az = 0.0
        max_obstacle_dist = 0.0

        rows, cols = elev_arr.shape

        for k in range(num_azimuths):
            az_deg = k * azimuth_step
            az_rad = math.radians(az_deg)

            # In South Polar Stereographic: North is toward -Y at 0° Lon,
            # az clockwise from North: dx = r*sin(az), dy = r*cos(az)
            sin_az = math.sin(az_rad)
            cos_az = math.cos(az_rad)

            # Projected ray sample positions
            ray_x = center_x + radial_distances * sin_az
            ray_y = center_y + radial_distances * cos_az

            # Convert to raster indices using affine inverse
            ray_cols = inv_transform.a * ray_x + inv_transform.b * ray_y + inv_transform.c
            ray_rows = inv_transform.d * ray_x + inv_transform.e * ray_y + inv_transform.f

            # Round to nearest pixel
            row_idx = np.round(ray_rows).astype(int)
            col_idx = np.round(ray_cols).astype(int)

            # Filter valid inside raster window
            in_bounds = (row_idx >= 0) & (row_idx < rows) & (col_idx >= 0) & (col_idx < cols)

            if not np.any(in_bounds):
                h_angle = 0.0
            else:
                valid_rows = row_idx[in_bounds]
                valid_cols = col_idx[in_bounds]
                valid_dists = radial_distances[in_bounds]
                valid_curv = curvature_drops[in_bounds]

                sampled_elevs = elev_arr[valid_rows, valid_cols].astype(float)
                non_nodata = (sampled_elevs > -30000.0) & (~np.isnan(sampled_elevs))

                if not np.any(non_nodata):
                    h_angle = 0.0
                else:
                    z_target = sampled_elevs[non_nodata]
                    d_target = valid_dists[non_nodata]
                    curv_target = valid_curv[non_nodata]

                    # Apparent vertical delta: z_target - curvature_drop - observer_z
                    delta_z = z_target - curv_target - observer_z
                    angles_rad = np.arctan2(delta_z, d_target)
                    angles_deg = np.degrees(angles_rad)

                    max_idx = int(np.argmax(angles_deg))
                    h_angle = float(angles_deg[max_idx])

                    if h_angle > max_obstacle_angle:
                        max_obstacle_angle = h_angle
                        max_obstacle_az = az_deg
                        max_obstacle_dist = float(d_target[max_idx])

            azimuths.append(round(az_deg, 2))
            horizon_elevations.append(round(h_angle, 3))

        min_h = float(np.min(horizon_elevations))
        max_h = float(np.max(horizon_elevations))
        mean_h = float(np.mean(horizon_elevations))

        # Sky view factor approximation: integral of cos^2(h(alpha)) over hemisphere
        rad_elevs = np.radians(np.maximum(0.0, horizon_elevations))
        sky_view = float(np.mean(np.cos(rad_elevs) ** 2))

        profile = RadialHorizonProfile(
            center_lat=lat_deg,
            center_lon=norm_lon,
            observer_elevation_m=round(center_elev, 2),
            mast_height_m=mast_height_m,
            search_radius_m=search_radius_m,
            num_azimuths=num_azimuths,
            azimuth_step_deg=azimuth_step,
            azimuths_deg=azimuths,
            horizon_elevations_deg=horizon_elevations,
            min_horizon_deg=round(min_h, 3),
            max_horizon_deg=round(max_h, 3),
            mean_horizon_deg=round(mean_h, 3),
            max_obstacle_azimuth_deg=round(max_obstacle_az, 2),
            max_obstacle_distance_m=round(max_obstacle_dist, 1),
            sky_view_factor=round(sky_view, 4),
            dataset_name=dataset_label,
            crs="ESRI:104903",
            curvature_corrected=True,
        )

        with self._lock:
            if len(self._cache) >= self._cache_capacity:
                self._cache.popitem(last=False)
            self._cache[cache_key] = profile

        return profile

    def _build_flat_fallback(
        self, lat: float, lon: float, radius_m: float, mast_h: float, num_az: int
    ) -> RadialHorizonProfile:
        step = 360.0 / num_az
        az = [round(i * step, 2) for i in range(num_az)]
        elev = [0.0] * num_az
        return RadialHorizonProfile(
            center_lat=lat,
            center_lon=lon,
            observer_elevation_m=0.0,
            mast_height_m=mast_h,
            search_radius_m=radius_m,
            num_azimuths=num_az,
            azimuth_step_deg=step,
            azimuths_deg=az,
            horizon_elevations_deg=elev,
            min_horizon_deg=0.0,
            max_horizon_deg=0.0,
            mean_horizon_deg=0.0,
            max_obstacle_azimuth_deg=0.0,
            max_obstacle_distance_m=0.0,
            sky_view_factor=1.0,
            dataset_name="Geometric Horizon (Zero Topography Baseline)",
        )

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()


terrain_horizon_engine = TerrainHorizonEngine()
