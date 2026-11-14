"""Scientific time-based Sun and Earth visibility simulation service for Moonscape.

Propagates planetary ephemerides (NASA NAIF SPICE / JPL DE421 / Meeus) over user-defined temporal windows,
evaluates 360-degree topographic horizon occultations with lunar spherical curvature correction,
and calculates power and communication margins with sub-millisecond per-step performance.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
import numpy as np

from Backend.app.core.logging import logger
from Backend.app.schemas.simulation import (
    SimulationTimeStep,
    VisibilitySimulationRequest,
    VisibilitySimulationResponse,
)
from Backend.app.services.geospatial.coordinate_manager import coordinate_manager
from Backend.app.services.spice_service import spice_service
from Backend.app.services.terrain_horizon import terrain_horizon_engine
from maths.earth_visibility import (
    calculate_earth_visibility_fraction,
    evaluate_communication_link,
    parse_utc_timestamp,
)
from maths.illumination_geometry import (
    SOLAR_SEMI_DIAMETER_DEG,
    calculate_sun_visibility_fraction,
    estimate_surface_temperature_kelvin,
)


class VisibilitySimulationService:
    """Propagates temporal planetary lighting and Earth direct line-of-sight communication with topographic horizon masking."""

    def simulate_visibility(self, req: VisibilitySimulationRequest) -> VisibilitySimulationResponse:
        """Executes time-series visibility simulation over requested time horizon using cached 360° radial horizon profile."""
        lat = req.lat
        lon = coordinate_manager.normalize_longitude(req.lon, target_range="360")

        start_dt = parse_utc_timestamp(req.start_epoch_iso)
        total_hours = req.duration_days * 24.0
        step_hours = req.step_hours
        steps_count = int(total_hours / step_hours) + 1

        # Retrieve or compute 360-degree radial horizon profile with lunar spherical curvature drop
        horizon_profile = terrain_horizon_engine.compute_horizon_profile(
            lat_deg=lat,
            lon_deg=lon,
            search_radius_m=10000.0,
            mast_height_m=2.0,
            num_azimuths=72,
        )

        time_series: List[SimulationTimeStep] = []
        sunlit_step_count = 0
        comm_step_count = 0
        combined_ops_step_count = 0

        curr_continuous_sun = 0.0
        max_continuous_sun = 0.0
        curr_continuous_dark = 0.0
        max_continuous_dark = 0.0

        curr_continuous_blackout = 0.0
        max_continuous_blackout = 0.0

        for i in range(steps_count):
            elapsed_h = i * step_hours
            step_dt = start_dt + timedelta(hours=elapsed_h)

            # Ephemeris State via Unified SPICE / Analytical DE421 Engine
            ephem = spice_service.get_ephemeris_state(lat, lon, step_dt)

            solar_elev = ephem.solar_elevation_deg
            solar_az = ephem.solar_azimuth_deg
            sun_dist = ephem.sun_distance_au

            earth_elev = ephem.earth_elevation_deg
            earth_az = ephem.earth_azimuth_deg

            # Query cached 360-degree radial terrain horizon mask in O(1) time
            h_sun = horizon_profile.get_horizon_elevation(solar_az)
            h_earth = horizon_profile.get_horizon_elevation(earth_az)

            # Solar visibility with topographic horizon mask
            sun_vis = calculate_sun_visibility_fraction(solar_elev, horizon_elevation_deg=h_sun)
            sunlit_pct = round(sun_vis * 100.0, 1)
            is_sunlit = sun_vis > 0.0

            # Earth visibility with topographic horizon mask
            earth_vis_frac = calculate_earth_visibility_fraction(earth_elev, horizon_elevation_deg=h_earth)
            is_earth_vis = earth_vis_frac > 0.0

            # Comm link margin: requires elevation above terrain horizon + 2.0 deg multipath clearance
            effective_earth_elev = earth_elev - h_earth
            is_comm_op, _ = evaluate_communication_link(effective_earth_elev, earth_vis_frac)
            comm_status = "operational" if is_comm_op else ("marginal" if is_earth_vis else "blackout")

            # Combined operations window (simultaneous power & direct comm)
            is_combined_ops = is_sunlit and is_comm_op
            if is_combined_ops:
                combined_ops_step_count += 1

            # Surface Thermal Temperature
            temp_k = estimate_surface_temperature_kelvin(
                solar_elevation_deg=solar_elev,
                sun_visibility_fraction=sun_vis,
                sun_distance_au=sun_dist,
                is_psr=False,
            )

            # Duration tracking
            if is_sunlit:
                sunlit_step_count += 1
                curr_continuous_sun += step_hours
                max_continuous_sun = max(max_continuous_sun, curr_continuous_sun)
                curr_continuous_dark = 0.0
            else:
                curr_continuous_dark += step_hours
                max_continuous_dark = max(max_continuous_dark, curr_continuous_dark)
                curr_continuous_sun = 0.0

            if is_comm_op:
                comm_step_count += 1
                curr_continuous_blackout = 0.0
            else:
                curr_continuous_blackout += step_hours
                max_continuous_blackout = max(max_continuous_blackout, curr_continuous_blackout)

            time_series.append(
                SimulationTimeStep(
                    timestamp_iso=step_dt.isoformat(),
                    elapsed_hours=round(elapsed_h, 1),
                    solar_elevation_deg=round(solar_elev, 2),
                    solar_azimuth_deg=round(solar_az, 1),
                    sunlit_fraction_pct=sunlit_pct,
                    is_sunlit=is_sunlit,
                    earth_elevation_deg=round(earth_elev, 2),
                    earth_azimuth_deg=round(earth_az, 1),
                    earth_visibility_fraction=round(earth_vis_frac, 3),
                    is_earth_visible=is_earth_vis,
                    communication_status=comm_status,
                    surface_temp_k=temp_k,
                    horizon_elevation_sun_deg=round(h_sun, 2),
                    horizon_elevation_earth_deg=round(h_earth, 2),
                    is_combined_ops_available=is_combined_ops,
                )
            )

        total_sim_hours = steps_count * step_hours
        tot_sun_hours = sunlit_step_count * step_hours
        sun_pct = round((tot_sun_hours / total_sim_hours) * 100.0, 1) if total_sim_hours > 0 else 0.0

        tot_comm_hours = comm_step_count * step_hours
        comm_pct = round((tot_comm_hours / total_sim_hours) * 100.0, 1) if total_sim_hours > 0 else 0.0

        tot_comb_hours = combined_ops_step_count * step_hours
        comb_pct = round((tot_comb_hours / total_sim_hours) * 100.0, 1) if total_sim_hours > 0 else 0.0

        end_dt = start_dt + timedelta(hours=total_sim_hours)

        methodology = (
            f"Temporal propagation using {spice_service.get_service_metadata()['active_mode']} ephemeris "
            f"integrated with 360-degree radial terrain horizon profiles ({horizon_profile.dataset_name}) "
            f"including spherical lunar curvature drop (d^2 / 2*R_moon) and multipath clearance (>2.0° above horizon)."
        )

        caveats = [
            f"Topographic horizon derived from {horizon_profile.dataset_name} with {horizon_profile.num_azimuths} radial azimuth rays.",
            "Lander observer elevation accounts for 2.0m solar array/antenna mast clearance above surface.",
            "Earth communication status accounts for optical/physical libration and 2.0° multipath obstacle clearance margin.",
        ]

        return VisibilitySimulationResponse(
            query_lat=lat,
            query_lon=lon,
            start_epoch_iso=start_dt.isoformat(),
            end_epoch_iso=end_dt.isoformat(),
            duration_days=req.duration_days,
            total_steps=len(time_series),
            total_sunlight_hours=round(tot_sun_hours, 1),
            sunlight_percentage=sun_pct,
            total_earth_comm_hours=round(tot_comm_hours, 1),
            earth_comm_percentage=comm_pct,
            max_continuous_sunlight_hours=round(max_continuous_sun, 1),
            max_continuous_darkness_hours=round(max_continuous_dark, 1),
            max_continuous_comm_blackout_hours=round(max_continuous_blackout, 1),
            combined_ops_hours=round(tot_comb_hours, 1),
            combined_ops_percentage=comb_pct,
            horizon_min_deg=horizon_profile.min_horizon_deg,
            horizon_max_deg=horizon_profile.max_horizon_deg,
            horizon_mean_deg=horizon_profile.mean_horizon_deg,
            terrain_dataset=horizon_profile.dataset_name,
            time_series=time_series,
            scientific_methodology=methodology,
            caveats=caveats,
        )


visibility_simulation_service = VisibilitySimulationService()
