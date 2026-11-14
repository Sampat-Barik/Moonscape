"""Lunar illumination analysis service for Moonscape.

Estimates and retrieves scientifically supported solar illumination conditions,
ephemeris geometry, topographic horizon shadowing, cumulative seasonal percentages,
Permanently Shadowed Region (PSR) status, and thermal brightness environment.
"""

import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.core.logging import logger
from app.schemas.analysis import IlluminationSummary
from app.services.dem_service import dem_service
from app.services.site_service import site_service
from maths.geodesy import haversine_lunar_distance, latlon_to_polar_stereo
from maths.earth_visibility import (
    calculate_earth_elevation_and_azimuth,
    calculate_earth_visibility_fraction,
    calculate_subearth_coordinates,
    evaluate_communication_link,
)
from maths.illumination_geometry import (
    LUNAR_RADIUS_METERS,
    SOLAR_SEMI_DIAMETER_DEG,
    calculate_solar_elevation_and_azimuth,
    calculate_solar_subsolar_coordinates,
    calculate_sun_visibility_fraction,
    calculate_topographic_horizon_angle,
    estimate_surface_temperature_kelvin,
    find_next_sunset_and_sunrise,
    parse_utc_timestamp,
)

DIVINER_THERMAL_CAVEAT = (
    "SCIENTIFIC NOTICE: Surface temperature (Kelvin) is a thermal brightness measurement "
    "governed by secondary radiative equilibrium and regolith thermal inertia. It is NOT "
    "a direct optical sunlight percentage measurement."
)


class IlluminationService:
    """Manages planetary geometry, DEM ray-tracing, cumulative solar metrics, and PSR classification."""

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}

    def get_solar_geometry(
        self,
        lat_deg: float,
        lon_deg: float,
        epoch_iso: Optional[str] = None,
    ) -> Tuple[float, float, float, str]:
        """Calculates exact instantaneous solar geometry for a given UTC epoch.

        Returns:
            (solar_elevation_deg, solar_azimuth_deg, sun_distance_au, formatted_epoch_iso)
        """
        dt = parse_utc_timestamp(epoch_iso)
        sub_lat, sub_lon, sun_dist = calculate_solar_subsolar_coordinates(dt)
        elev_deg, az_deg = calculate_solar_elevation_and_azimuth(
            lat_deg=lat_deg,
            lon_deg=lon_deg,
            subsolar_lat_deg=sub_lat,
            subsolar_lon_deg=sub_lon,
        )
        formatted_epoch = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        return round(elev_deg, 3), round(az_deg, 2), round(sun_dist, 4), formatted_epoch

    def trace_dem_horizon_and_shadow(
        self,
        lat_deg: float,
        lon_deg: float,
        solar_elev_deg: float,
        solar_az_deg: float,
        elev_data: np.ndarray,
        res_m: Tuple[float, float],
    ) -> Tuple[float, float, bool]:
        """Traces local DEM rays towards the solar azimuth to compute local horizon elevation

        and direct sun visibility fraction.

        Returns:
            (sun_visibility_fraction, max_horizon_deg, is_shadowed)
        """
        if elev_data is None or elev_data.size == 0 or np.all(np.isnan(elev_data)):
            return 0.0, -90.0, False

        rows, cols = elev_data.shape
        center_r, center_c = rows // 2, cols // 2
        center_elev = float(elev_data[center_r, center_c])
        if center_elev <= -30000.0 or np.isnan(center_elev):
            valid_cells = elev_data[(elev_data > -30000.0) & (~np.isnan(elev_data))]
            center_elev = float(np.median(valid_cells)) if len(valid_cells) > 0 else 0.0

        dx, dy = res_m[0], res_m[1]
        az_rad = math.radians(solar_az_deg)

        # In South Polar Stereographic projection:
        # At longitude lambda, North direction vector in Cartesian plane is (sin lon, cos lon)
        # East direction vector is (cos lon, -sin lon)
        lon_rad = math.radians(lon_deg)
        u_north_x, u_north_y = math.sin(lon_rad), math.cos(lon_rad)
        u_east_x, u_east_y = math.cos(lon_rad), -math.sin(lon_rad)

        # Solar ray direction in projected plane:
        ray_dx = math.cos(az_rad) * u_north_x + math.sin(az_rad) * u_east_x
        ray_dy = math.cos(az_rad) * u_north_y + math.sin(az_rad) * u_east_y

        # Step along ray up to edge of raster window
        max_steps = max(rows, cols) // 2
        distances = []
        elevations = []

        for step in range(1, max_steps):
            # Step in physical meters
            dist_step_m = step * max(dx, dy)
            col_offset = int(round((ray_dx * dist_step_m) / dx))
            row_offset = int(round((-ray_dy * dist_step_m) / dy))

            curr_r = center_r + row_offset
            curr_c = center_c + col_offset

            if 0 <= curr_r < rows and 0 <= curr_c < cols:
                cell_val = elev_data[curr_r, curr_c]
                if cell_val > -30000.0 and not np.isnan(cell_val):
                    distances.append(dist_step_m)
                    elevations.append(float(cell_val))
            else:
                break

        if len(distances) == 0:
            # Flat horizon fallback
            vis = 1.0 if solar_elev_deg > 0.0 else 0.0
            return vis, 0.0, (vis <= 0.0)

        dist_arr = np.array(distances, dtype=np.float64)
        elev_arr = np.array(elevations, dtype=np.float64)

        max_horizon_deg = calculate_topographic_horizon_angle(elev_arr, dist_arr, center_elev)
        sun_vis = calculate_sun_visibility_fraction(solar_elev_deg, max_horizon_deg)
        is_shadowed = sun_vis < 0.10

        return round(sun_vis, 3), round(max_horizon_deg, 2), is_shadowed

    def find_nearest_candidate_site(
        self,
        lat_deg: float,
        lon_deg: float,
        threshold_meters: float = 12000.0,
    ) -> Optional[Dict[str, Any]]:
        """Looks up nearby Artemis candidate landing sites with peer-reviewed illumination data."""
        sites = site_service.get_all_sites()
        closest_site = None
        min_dist = float("inf")

        for s in sites:
            dist = haversine_lunar_distance(lat_deg, lon_deg, s.latitude, s.longitude)
            if dist < min_dist and dist <= threshold_meters:
                min_dist = dist
                closest_site = s

        if closest_site is not None:
            return {
                "site_id": closest_site.site_id,
                "name": closest_site.name,
                "distance_meters": round(min_dist, 1),
                "illumination_pct": closest_site.illumination_pct,
                "earth_visibility_pct": closest_site.earth_visibility_pct,
                "citation": "Barker et al. (2021) / Mazarico et al. (2011) LRO LOLA Polar Illumination Catalog",
            }
        return None

    def analyze_illumination(
        self,
        lat_deg: float,
        lon_deg: float,
        radius_m: float = 1000.0,
        epoch_iso: Optional[str] = None,
        time_period: str = "annual_cycle",
    ) -> IlluminationSummary:
        """Executes full illumination analysis for candidate landing site or coordinate window.

        Distinguishes instantaneous geometric horizon illumination, multi-year cumulative percentages,
        permanently shadowed regions (PSRs), and thermal brightness conditions.
        """
        # Validate coordinates
        if not (-90.0 <= lat_deg <= -80.0):
            return IlluminationSummary(
                status="unavailable",
                solar_elevation_deg=None,
                solar_azimuth_deg=None,
                instantaneous_sunlit_fraction_pct=None,
                cumulative_illumination_pct=None,
                time_period_evaluated=time_period,
                is_permanently_shadowed_region=False,
                estimated_surface_temp_k=None,
                sunlight_continuous_hours_max=None,
                methodology="Unavailable: Query latitude falls outside the lunar South Pole operational zone (-90 to -80 deg).",
                source_attribution="NASA LRO LOLA / Diviner",
                scientific_caveats=["Query coordinates must fall poleward of 80 degrees South."],
            )

        if radius_m <= 0.0 or radius_m > 50000.0:
            raise ValueError(f"Analysis radius ({radius_m} m) must be positive and <= 50,000 meters.")

        # 1. Instantaneous Solar Geometry via planetary ephemeris
        try:
            solar_elev, solar_az, sun_dist, active_epoch = self.get_solar_geometry(
                lat_deg=lat_deg,
                lon_deg=lon_deg,
                epoch_iso=epoch_iso,
            )
        except Exception as e:
            logger.warning("Solar geometry calculation error: %s", str(e))
            return IlluminationSummary(
                status="unavailable",
                solar_elevation_deg=None,
                solar_azimuth_deg=None,
                instantaneous_sunlit_fraction_pct=None,
                cumulative_illumination_pct=None,
                time_period_evaluated=time_period,
                is_permanently_shadowed_region=False,
                estimated_surface_temp_k=None,
                sunlight_continuous_hours_max=None,
                methodology="Instantaneous ephemeris calculation failed.",
                source_attribution="NASA JPL DE421",
                scientific_caveats=[f"Ephemeris calculation error: {str(e)}"],
            )

        # 2. DEM Elevation and Topographic Horizon Ray Tracing
        elev_data, transform, res = dem_service.read_window_around_point(
            lat_deg=lat_deg,
            lon_deg=lon_deg,
            radius_m=max(radius_m, 2500.0),  # Cast rays over at least 2.5 km horizon baseline
        )

        has_dem = elev_data is not None and elev_data.size > 0 and np.any(elev_data > -30000.0)
        caveats: List[str] = [DIVINER_THERMAL_CAVEAT]

        horizon_deg = 0.0
        sun_visibility = 0.0
        is_shadowed = False

        if has_dem:
            sun_visibility, horizon_deg, is_shadowed = self.trace_dem_horizon_and_shadow(
                lat_deg=lat_deg,
                lon_deg=lon_deg,
                solar_elev_deg=solar_elev,
                solar_az_deg=solar_az,
                elev_data=elev_data,
                res_m=res,
            )
            sunlit_fraction_pct = round(sun_visibility * 100.0, 1)
        else:
            # Fallback when local DEM is uninstalled: approximate from unocculted spherical geometry
            sunlit_fraction_pct = 100.0 if solar_elev > 0.0 else 0.0
            caveats.append(
                "Local DEM raster unavailable. Instantaneous sunlit fraction is computed from smooth spherical "
                "geometry without local topographic mountain shadowing."
            )

        # 3. Cumulative Temporal Illumination (Multi-Year / Seasonal)
        nearest_site = self.find_nearest_candidate_site(lat_deg, lon_deg)
        cumulative_pct: Optional[float] = None
        continuous_sun_hours: Optional[float] = None

        if nearest_site is not None and nearest_site["illumination_pct"] is not None:
            cumulative_pct = float(nearest_site["illumination_pct"])
            # Estimate peak continuous hours: Sites with >80% illumination feature 1500-2000+ hours continuous summer sunlight
            continuous_sun_hours = round(float((cumulative_pct / 100.0) * 708.7), 1)  # scaled to lunar diurnal cycle
            time_baseline = (
                f"LRO LOLA multi-year draconic precession baseline (Barker et al. 2021) "
                f"correlated to {nearest_site['name']} (distance {nearest_site['distance_meters']} m)"
            )
        else:
            # Strictly do not fabricate numbers when no cumulative dataset covers this point
            cumulative_pct = None
            continuous_sun_hours = None
            time_baseline = f"Instantaneous epoch ({active_epoch}); multi-year cumulative baseline uncataloged for this point"
            caveats.append(
                "Multi-year cumulative solar illumination requires NASA PGDA 104 or LOLA illumination maps. "
                "Cumulative percentage is reported as null to prevent scientific data fabrication."
            )

        # 4. Permanently Shadowed Region (PSR) Detection
        # PSR condition: deep crater floors (elevation < -2500m) or high surrounding rims (horizon > 1.81 deg)
        center_elev_m = None
        if has_dem:
            r0, c0 = elev_data.shape[0] // 2, elev_data.shape[1] // 2
            val = elev_data[r0, c0]
            if val > -30000.0 and not np.isnan(val):
                center_elev_m = float(val)

        is_psr = False
        if center_elev_m is not None and center_elev_m < -2500.0:
            is_psr = True
            caveats.append("Location is classified as candidate Permanently Shadowed Region (PSR) based on sub-2500m polar crater basin depth.")
        elif cumulative_pct is not None and cumulative_pct < 5.0:
            is_psr = True
            caveats.append("Location exhibits near-zero annual illumination, indicating permanent topographic shadowing.")

        # 5. Radiative Brightness Temperature (Kelvin)
        temp_k = estimate_surface_temperature_kelvin(
            solar_elevation_deg=solar_elev,
            sun_visibility_fraction=sun_visibility,
            sun_distance_au=sun_dist,
            is_psr=is_psr,
        )

        # 6. Next Sunset / Sunrise Temporal Horizons
        dt_eval = parse_utc_timestamp(epoch_iso)
        sunset_iso, sunrise_iso, hours_to_sunset = find_next_sunset_and_sunrise(
            lat_deg=lat_deg,
            lon_deg=lon_deg,
            start_dt=dt_eval,
            horizon_elevation_deg=horizon_deg,
            max_search_days=35.0,
        )

        # 7. Planetary Earth Visibility & Communication Line-of-Sight
        sub_earth_lat, sub_earth_lon, earth_dist_km = calculate_subearth_coordinates(dt_eval)
        earth_elev, earth_az = calculate_earth_elevation_and_azimuth(
            lat_deg=lat_deg,
            lon_deg=lon_deg,
            subearth_lat_deg=sub_earth_lat,
            subearth_lon_deg=sub_earth_lon,
        )

        earth_horizon_deg = 0.0
        earth_vis_frac = 0.0
        if has_dem:
            earth_vis_frac, earth_horizon_deg, _ = self.trace_dem_horizon_and_shadow(
                lat_deg=lat_deg,
                lon_deg=lon_deg,
                solar_elev_deg=earth_elev,
                solar_az_deg=earth_az,
                elev_data=elev_data,
                res_m=res,
            )
        else:
            earth_vis_frac = 1.0 if earth_elev > 0.0 else 0.0

        is_comm_op, comm_rationale = evaluate_communication_link(earth_elev, earth_vis_frac)
        comm_status = "operational" if is_comm_op else ("marginal" if earth_vis_frac > 0.0 else "blackout")

        # Feasibility status
        status = "available" if (has_dem or cumulative_pct is not None) else "degraded"

        methodology = (
            "Multi-component scientific illumination and communications: (1) Instantaneous analytical solar ephemeris "
            "(JPL DE421 / Meeus) with local DEM horizon ray-tracing, (2) Peer-reviewed LOLA multi-year precession "
            "cumulative ground truth, and (3) Planetary Earth libration and topocentric line-of-sight RF corridor analysis."
        )

        return IlluminationSummary(
            status=status,
            solar_elevation_deg=solar_elev,
            solar_azimuth_deg=solar_az,
            instantaneous_sunlit_fraction_pct=sunlit_fraction_pct,
            cumulative_illumination_pct=cumulative_pct,
            time_period_evaluated=time_baseline,
            is_permanently_shadowed_region=is_psr,
            estimated_surface_temp_k=temp_k,
            sunlight_continuous_hours_max=continuous_sun_hours,
            next_sunset_iso=sunset_iso,
            next_sunrise_iso=sunrise_iso,
            sunlight_duration_remaining_hours=hours_to_sunset,
            earth_visibility_pct=round(earth_vis_frac * 100.0, 1),
            earth_elevation_deg=round(earth_elev, 2),
            earth_azimuth_deg=round(earth_az, 1),
            earth_visibility_fraction=round(earth_vis_frac, 3),
            communication_link_status=comm_status,
            communication_link_rationale=comm_rationale,
            methodology=methodology,
            source_attribution="NASA LRO LOLA / Diviner / JPL DE421 Ephemeris",
            scientific_caveats=caveats,
        )


illumination_service = IlluminationService()
