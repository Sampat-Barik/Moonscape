"""Schemas for Lunar South Pole candidate landing sites and site comparison."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class CandidateSite(BaseModel):
    """Candidate lunar landing site metadata and baseline parameters."""

    site_id: str = Field(..., description="Unique slug identifier (e.g., 'shackleton_connecting_ridge')")
    name: str = Field(..., description="Official designated name of candidate region")
    latitude: float = Field(..., ge=-90.0, le=-70.0, description="Planetocentric latitude in degrees (South Pole: -90 to -70)")
    longitude: float = Field(..., ge=-180.0, le=360.0, description="Planetocentric longitude in degrees (-180 to 360)")
    elevation_m: Optional[float] = Field(None, description="Average surface elevation in meters relative to 1737.4 km lunar sphere")
    mean_slope_deg: Optional[float] = Field(None, description="Average terrain slope in degrees")
    illumination_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Solar illumination percentage over lunar year")
    earth_visibility_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Direct Earth line-of-sight communication visibility percentage")
    description: str = Field(..., description="Geomorphological context and site description")
    scientific_value: str = Field(..., description="Primary scientific objectives (e.g., volatile sampling, PSR access)")
    target_mission: str = Field("Artemis III", description="Associated lunar mission architecture")
    priority: str = Field("high", description="Candidate priority tier: 'high', 'medium', 'low'")


class SiteListResponse(BaseModel):
    """Response containing list of candidate sites."""

    total: int = Field(..., description="Total number of sites available")
    sites: List[CandidateSite] = Field(..., description="List of candidate landing sites")


class SiteCompareRequest(BaseModel):
    """Request payload to compare multiple candidate sites."""

    site_ids: List[str] = Field(..., min_length=2, max_length=10, description="List of site IDs to compare (min 2, max 10)")
    weights: Optional[Dict[str, float]] = Field(
        None,
        description="Optional custom weights for scoring criteria (slope, illumination, communication, science)",
    )
    mission_profile: Optional[str] = Field("artemis_hls", description="Mission profile ('artemis_hls', 'clps_cargo', 'polar_rover', 'base_camp')")

    @field_validator("site_ids")
    @classmethod
    def validate_unique_site_ids(cls, v: List[str]) -> List[str]:
        if len(v) != len(set(v)):
            raise ValueError("site_ids must contain unique site identifiers without duplicates.")
        return v


class SiteComparisonItem(BaseModel):
    """Detailed comparative evaluation of a single candidate site."""

    site_id: str
    name: str
    latitude: float
    longitude: float
    elevation_m: Optional[float]
    mean_slope_deg: Optional[float]
    illumination_pct: Optional[float]
    earth_visibility_pct: Optional[float]
    suitability_score: float = Field(..., ge=0.0, le=100.0, description="Computed multi-criteria score (0-100)")
    safety_rank: int = Field(..., ge=1, description="Rank ordered by safety suitability")
    key_strengths: List[str]
    key_vulnerabilities: List[str]
    ml_model_score: Optional[float] = Field(None, description="ML surrogate model suitability score (0-100)")
    hard_constraint_status: str = Field("passed", description="'passed' or 'violated'")
    uncertainty_score_std: Optional[float] = Field(None, description="Score uncertainty standard error under perturbation")
    confidence_interval_95: Optional[List[float]] = Field(None, description="95% confidence interval [min, max]")


class SiteCompareResponse(BaseModel):
    """Comparative analysis response."""

    compared_sites: List[SiteComparisonItem]
    top_recommended_site_id: str
    tradeoff_summary: str
    criteria_weights: Dict[str, float]
    disclaimer: str
    mission_profile: Optional[str] = Field("artemis_hls", description="Active mission profile")
    criteria_version: Optional[str] = Field("2.0-phase6", description="Evaluation criteria and algorithm version")
    warnings: List[str] = Field(default_factory=list, description="Comparative warnings and data disparity notes")
