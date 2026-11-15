"""Time-based Sun and Earth visibility simulation endpoints."""

from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter
from Backend.app.schemas.simulation import (
    VisibilitySimulationRequest,
    VisibilitySimulationResponse,
)
from Backend.app.services.terrain_horizon import terrain_horizon_engine
from Backend.app.services.visibility_simulation import visibility_simulation_service
from maths.illumination_geometry import find_next_sunset_and_sunrise, parse_utc_timestamp

router = APIRouter(prefix="", tags=["Simulation"])


class HorizonElevationRequest(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=360.0)
    azimuth_deg: float = Field(..., ge=0.0, le=360.0)
    mast_height_m: float = Field(2.0, ge=0.0, le=50.0)


class SunsetSunriseRequest(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=360.0)
    start_epoch_iso: Optional[str] = None
    max_search_days: float = Field(35.0, ge=1.0, le=60.0)


@router.post(
    "/simulation/visibility",
    response_model=VisibilitySimulationResponse,
    summary="Propagate time-based Sun and Earth visibility over user-defined duration",
)
def simulate_visibility(payload: VisibilitySimulationRequest) -> VisibilitySimulationResponse:
    """Propagates solar elevation, surface insolation, Earth elevation, and direct communication

    line-of-sight over a configurable time horizon (1 to 60 days).
    """
    return visibility_simulation_service.simulate_visibility(payload)


@router.post("/horizon/elevation", summary="Compute terrain obstacle horizon elevation along an azimuth")
def get_horizon_elevation(payload: HorizonElevationRequest) -> dict:
    """Computes the terrain horizon obstacle angle along a specific azimuth ray taking into account spherical curvature."""
    profile = terrain_horizon_engine.compute_horizon_profile(
        lat_deg=payload.lat,
        lon_deg=payload.lon,
        mast_height_m=payload.mast_height_m,
    )
    horizon_el = profile.get_horizon_elevation(payload.azimuth_deg)
    return {
        "lat": payload.lat,
        "lon": payload.lon,
        "azimuth_deg": payload.azimuth_deg,
        "horizon_elevation_deg": round(horizon_el, 3),
        "min_horizon_deg": round(profile.min_horizon_deg, 3),
        "max_horizon_deg": round(profile.max_horizon_deg, 3),
        "mean_horizon_deg": round(profile.mean_horizon_deg, 3),
    }


@router.post("/sunset-sunrise", summary="Calculate next polar sunset and sunrise events")
def get_next_sunset_sunrise(payload: SunsetSunriseRequest) -> dict:
    """Determines the exact timestamps of next polar horizon crossing events within search window."""
    start_dt = parse_utc_timestamp(payload.start_epoch_iso)
    profile = terrain_horizon_engine.compute_horizon_profile(
        lat_deg=payload.lat,
        lon_deg=payload.lon,
    )
    mean_horizon = profile.mean_horizon_deg
    sunset_iso, sunrise_iso, duration_h = find_next_sunset_and_sunrise(
        lat_deg=payload.lat,
        lon_deg=payload.lon,
        start_dt=start_dt,
        horizon_elevation_deg=mean_horizon,
        max_search_days=payload.max_search_days,
    )
    return {
        "lat": payload.lat,
        "lon": payload.lon,
        "start_epoch_iso": start_dt.isoformat(),
        "horizon_elevation_deg": round(mean_horizon, 3),
        "next_sunset_iso": sunset_iso,
        "next_sunrise_iso": sunrise_iso,
        "sunlight_duration_hours": round(duration_h, 1) if duration_h is not None else None,
        "status": "continuous_daylight" if sunset_iso is None else "diurnal_cycle",
    }
