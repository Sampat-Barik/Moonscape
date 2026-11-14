"""Schemas for landing zone spatial analysis pipelines and lunar illumination modeling."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


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


class TopographicStats(BaseModel):
    """Aggregated topographic statistical metrics for an evaluated landing zone."""

    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    median_value: Optional[float] = None
    std_dev: Optional[float] = None
    variation: Optional[float] = None  # Relief (max - min)
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
