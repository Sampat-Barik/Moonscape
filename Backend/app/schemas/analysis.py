"""Schemas for landing zone spatial analysis pipelines and lunar illumination modeling."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.scoring import ScoreResponse


class AnalysisRunRequest(BaseModel):
    """Input payload to trigger a landing zone raster analysis."""

    center_lat: float = Field(..., ge=-90.0, le=-80.0, description="Center latitude of candidate landing zone (-90 to -80)")
    center_lon: float = Field(..., ge=-180.0, le=360.0, description="Center longitude of candidate landing zone (-180 to 360)")
    radius_meters: float = Field(1000.0, ge=50.0, le=25000.0, description="Landing ellipse radius in meters (50m to 25km)")
    max_acceptable_slope_deg: float = Field(10.0, ge=1.0, le=30.0, description="Maximum slope constraint for lander stability (deg)")
    max_acceptable_roughness_m: float = Field(0.5, ge=0.1, le=5.0, description="Maximum surface roughness constraint (m)")
    roughness_kernel_size: int = Field(3, ge=3, le=15, description="Moving window kernel size for RMS roughness (default 3x3)")
    epoch_iso: Optional[str] = Field(None, description="Optional UTC ISO-8601 timestamp for instantaneous solar geometry (e.g. '2026-10-15T12:00:00Z')")
    time_period: Optional[str] = Field("annual_cycle", description="Target illumination evaluation period: 'instantaneous', 'annual_cycle', 'precession_18yr'")

    @field_validator("center_lat")
    @classmethod
    def validate_center_lat(cls, v: float) -> float:
        if v < -90.0 or v > -80.0:
            raise ValueError(
                f"Selected latitude ({v}°) is outside the supported lunar South Pole analysis region (80°S–90°S). "
                "Visual exploration is available, but terrain analysis requires coordinates within the polar coverage zone."
            )
        return v

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "latitude" in data and "center_lat" not in data:
                data["center_lat"] = data["latitude"]
            elif "lat" in data and "center_lat" not in data:
                data["center_lat"] = data["lat"]

            if "longitude" in data and "center_lon" not in data:
                data["center_lon"] = data["longitude"]
            elif "lon" in data and "center_lon" not in data:
                data["center_lon"] = data["lon"]

            if "radius_m" in data and "radius_meters" not in data:
                data["radius_meters"] = data["radius_m"]
            elif "radius" in data and "radius_meters" not in data:
                data["radius_meters"] = data["radius"]
        return data


class TopographicStats(BaseModel):
    """Aggregated topographic statistical metrics for an evaluated landing zone."""

    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    median_value: Optional[float] = None
    std_dev: Optional[float] = None
    variation: Optional[float] = None  # Relief (max - min)
    p95_value: Optional[float] = Field(None, description="95th percentile value")
    units: str


class SlopeDistribution(BaseModel):
    """Distribution of slopes within the evaluated zone."""

    ideal_pct: float = Field(..., description="Percentage of area with slope <= 5 deg")
    acceptable_pct: float = Field(..., description="Percentage of area with slope between 5 and 10 deg")
    marginal_pct: float = Field(..., description="Percentage of area with slope between 10 and 15 deg")
    critical_hazardous_pct: float = Field(..., description="Percentage of area with slope > 15 deg (tip-over risk)")


class IlluminationSummary(BaseModel):
    """Scientifically grounded lunar South Pole illumination and solar condition assessment."""

    status: str = Field(..., description="'available', 'degraded', or 'unavailable'")
    solar_elevation_deg: Optional[float] = Field(None, description="Solar elevation angle above local horizon (degrees)")
    solar_azimuth_deg: Optional[float] = Field(None, description="Azimuth angle of the Sun from true North (degrees clockwise)")
    instantaneous_sunlit_fraction_pct: Optional[float] = Field(None, description="Percentage of landing zone currently in direct line-of-sight sunlight")
    cumulative_illumination_pct: Optional[float] = Field(None, description="Average solar illumination percentage over defined time period")
    time_period_evaluated: str = Field(..., description="Documented epoch or temporal baseline (e.g. 'LOLA 18.6-year draconic precession cycle')")
    is_permanently_shadowed_region: bool = Field(False, description="Whether location is a candidate or verified Permanently Shadowed Region (PSR)")
    estimated_surface_temp_k: Optional[float] = Field(None, description="Estimated surface brightness temperature (Kelvin). Note: Thermal, not direct sunlight")
    sunlight_continuous_hours_max: Optional[float] = Field(None, description="Estimated peak continuous sunlight duration in hours")
    next_sunset_iso: Optional[str] = Field(None, description="UTC timestamp of the next sunset event")
    next_sunrise_iso: Optional[str] = Field(None, description="UTC timestamp of the next sunrise event")
    sunlight_duration_remaining_hours: Optional[float] = Field(None, description="Hours of continuous daylight remaining until next sunset")
    earth_visibility_pct: Optional[float] = Field(None, description="Direct Earth line-of-sight communication visibility percentage")
    earth_elevation_deg: Optional[float] = Field(None, description="Topocentric Earth elevation angle above local horizon (degrees)")
    earth_azimuth_deg: Optional[float] = Field(None, description="Topocentric Earth azimuth clockwise from true North (degrees)")
    earth_visibility_fraction: Optional[float] = Field(None, description="Visible fraction of the Earth's disc [0.0 to 1.0]")
    communication_link_status: Optional[str] = Field(None, description="'operational', 'marginal', or 'blackout'")
    communication_link_rationale: Optional[str] = Field(None, description="Physical and RF link justification")
    methodology: str = Field(..., description="Computational or observational derivation method")
    source_attribution: str = Field(..., description="NASA LRO instrument or ephemeris source")
    scientific_caveats: List[str] = Field(default_factory=list, description="Assumptions, limitations, and domain boundaries")


class AnalysisRunResponse(BaseModel):
    """Comprehensive analytical output for candidate landing zone."""

    analysis_id: str
    center_lat: float
    center_lon: float
    radius_meters: float
    total_samples: int
    valid_samples: int
    nodata_samples: int
    elevation: TopographicStats
    slope: TopographicStats
    slope_distribution: SlopeDistribution
    roughness_mean_m: Optional[float]
    roughness_max_m: Optional[float] = None
    roughness_baseline_m: Optional[float] = None
    roughness_method: Optional[str] = None
    roughness_multi_baseline: Optional[Dict[str, Any]] = Field(
        None, description="Multi-scale roughness breakdown across physical baseline lengths"
    )
    slope_method: Optional[str] = None
    safe_touchdown_fraction_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of zone meeting both slope and roughness safety constraints",
    )
    preliminary_feasibility: str = Field(
        ...,
        description="'favorable', 'marginal', 'unfavorable', or 'insufficient_data'",
    )
    dataset_metadata: Dict[str, Any]
    disclaimer: str
    illumination: Optional[IlluminationSummary] = Field(
        None, description="Solar illumination and shadow analysis for landing zone"
    )
    suitability: Optional[ScoreResponse] = Field(
        None, description="Preliminary multi-criteria landing suitability score evaluation"
    )
