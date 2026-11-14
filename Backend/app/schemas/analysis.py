"""Schemas for landing zone spatial analysis pipelines."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AnalysisRunRequest(BaseModel):
    """Input payload to trigger a landing zone raster analysis."""

    center_lat: float = Field(..., ge=-90.0, le=-80.0, description="Center latitude of candidate landing zone (-90 to -80)")
    center_lon: float = Field(..., ge=-180.0, le=360.0, description="Center longitude of candidate landing zone (-180 to 360)")
    radius_meters: float = Field(1000.0, ge=100.0, le=25000.0, description="Landing ellipse radius in meters (100m to 25km)")
    max_acceptable_slope_deg: float = Field(10.0, ge=1.0, le=30.0, description="Maximum slope constraint for lander stability (deg)")
    max_acceptable_roughness_m: float = Field(0.5, ge=0.1, le=5.0, description="Maximum surface roughness constraint (m)")


class TopographicStats(BaseModel):
    """Aggregated topographic statistical metrics for an evaluated landing zone."""

    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    median_value: Optional[float] = None
    std_dev: Optional[float] = None
    units: str


class SlopeDistribution(BaseModel):
    """Distribution of slopes within the evaluated zone."""

    ideal_pct: float = Field(..., description="Percentage of area with slope <= 5 deg")
    acceptable_pct: float = Field(..., description="Percentage of area with slope between 5 and 10 deg")
    marginal_pct: float = Field(..., description="Percentage of area with slope between 10 and 15 deg")
    critical_hazardous_pct: float = Field(..., description="Percentage of area with slope > 15 deg (tip-over risk)")


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
