"""Schemas for time-based lunar Sun and Earth visibility simulation."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field, model_validator


class VisibilitySimulationRequest(BaseModel):
    """Input parameters for temporal Sun and Earth visibility propagation."""

    lat: float = Field(..., ge=-90.0, le=-80.0, description="Latitude in degrees (-90 to -80)")
    lon: float = Field(..., ge=-180.0, le=360.0, description="Longitude in degrees (-180 to 360)")
    start_epoch_iso: Optional[str] = Field(None, description="Start UTC timestamp (ISO-8601). Defaults to current time.")
    duration_days: float = Field(14.0, ge=1.0, le=60.0, description="Simulation duration in Earth days (1 to 60 days)")
    step_hours: float = Field(2.0, ge=0.5, le=24.0, description="Time step in hours (0.5 to 24h)")
    ephemeris_source: Optional[str] = Field("auto", description="Ephemeris provider: 'auto', 'horizons' (NASA JPL Horizons API), or 'analytical' (JPL DE421 / Meeus)")

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "latitude" in data and "lat" not in data:
                data["lat"] = data["latitude"]
            elif "center_lat" in data and "lat" not in data:
                data["lat"] = data["center_lat"]

            if "longitude" in data and "lon" not in data:
                data["lon"] = data["longitude"]
            elif "center_lon" in data and "lon" not in data:
                data["lon"] = data["center_lon"]

            if "start_epoch" in data and "start_epoch_iso" not in data:
                data["start_epoch_iso"] = data["start_epoch"]
            elif "start_time_iso" in data and "start_epoch_iso" not in data:
                data["start_epoch_iso"] = data["start_time_iso"]
            elif "start_time" in data and "start_epoch_iso" not in data:
                data["start_epoch_iso"] = data["start_time"]
            elif "epoch" in data and "start_epoch_iso" not in data:
                data["start_epoch_iso"] = data["epoch"]

            if "step" in data and "step_hours" not in data:
                data["step_hours"] = data["step"]
            elif "time_step_hours" in data and "step_hours" not in data:
                data["step_hours"] = data["time_step_hours"]

            if "duration" in data and "duration_days" not in data:
                data["duration_days"] = data["duration"]
        return data


class SimulationTimeStep(BaseModel):
    """Calculated ephemeris and visibility state at a specific simulation epoch."""

    timestamp_iso: str
    elapsed_hours: float
    solar_elevation_deg: float
    solar_azimuth_deg: float
    sunlit_fraction_pct: float
    is_sunlit: bool
    earth_elevation_deg: float
    earth_azimuth_deg: float
    earth_visibility_fraction: float
    is_earth_visible: bool
    communication_status: str = Field(..., description="'operational', 'marginal', or 'blackout'")
    surface_temp_k: float
    horizon_elevation_sun_deg: Optional[float] = Field(None, description="Terrain horizon angle at solar azimuth")
    horizon_elevation_earth_deg: Optional[float] = Field(None, description="Terrain horizon angle at Earth azimuth")
    is_combined_ops_available: Optional[bool] = Field(None, description="Both solar power and direct Earth comm active")


class VisibilitySimulationResponse(BaseModel):
    """Comprehensive time-series and aggregate statistics for Sun/Earth visibility."""

    query_lat: float
    query_lon: float
    start_epoch_iso: str
    end_epoch_iso: str
    duration_days: float
    total_steps: int
    total_sunlight_hours: float
    sunlight_percentage: float
    total_earth_comm_hours: float
    earth_comm_percentage: float
    max_continuous_sunlight_hours: float
    max_continuous_darkness_hours: float
    max_continuous_comm_blackout_hours: float
    combined_ops_hours: Optional[float] = Field(None, description="Hours with simultaneous sunlight and Earth comm")
    combined_ops_percentage: Optional[float] = Field(None, description="Percentage of time with simultaneous sunlight and Earth comm")
    horizon_min_deg: Optional[float] = Field(None, description="Minimum terrain horizon elevation around site")
    horizon_max_deg: Optional[float] = Field(None, description="Maximum terrain obstacle elevation around site")
    horizon_mean_deg: Optional[float] = Field(None, description="Average 360-degree horizon elevation")
    terrain_dataset: Optional[str] = Field(None, description="DEM dataset utilized for radial ray-tracing")
    ephemeris_provider: Optional[str] = Field("JPL DE421 / Meeus Analytical", description="Celestial ephemeris source utilized (JPL Horizons or DE421)")
    time_series: List[SimulationTimeStep]
    scientific_methodology: str
    caveats: List[str]
