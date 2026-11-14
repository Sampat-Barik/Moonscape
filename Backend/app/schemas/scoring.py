"""Schemas for transparent multi-criteria landing site suitability scoring."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class ScoringWeights(BaseModel):
    """Normalized weighting coefficients across multi-criteria landing factors."""

    slope_weight: float = Field(0.30, ge=0.0, le=1.0, description="Weight for topographic slope penalty")
    roughness_weight: float = Field(0.20, ge=0.0, le=1.0, description="Weight for terrain roughness penalty")
    illumination_weight: float = Field(0.20, ge=0.0, le=1.0, description="Weight for solar illumination bonus")
    crater_hazard_weight: float = Field(0.10, ge=0.0, le=1.0, description="Weight for crater hazard penalty")
    rock_hazard_weight: float = Field(0.10, ge=0.0, le=1.0, description="Weight for rock/boulder hazard penalty")
    elevation_weight: float = Field(0.10, ge=0.0, le=1.0, description="Weight for surface elevation preference")

    # Backward-compatible operational weights
    communication_weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="Optional weight for Earth visibility")
    science_weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="Optional weight for scientific value")

    @model_validator(mode="after")
    def validate_weights(self) -> "ScoringWeights":
        total = (
            self.slope_weight
            + self.roughness_weight
            + self.illumination_weight
            + self.crater_hazard_weight
            + self.rock_hazard_weight
            + self.elevation_weight
            + (self.communication_weight or 0.0)
            + (self.science_weight or 0.0)
        )
        if total <= 0:
            raise ValueError("Sum of scoring weights must be greater than zero.")
        return self


class ScoreRequest(BaseModel):
    """Input payload to evaluate site suitability score."""

    site_id: Optional[str] = Field(None, description="Catalog site identifier (if scoring an existing site)")
    slope_deg: Optional[float] = Field(None, ge=0.0, le=90.0, description="Topographic slope in degrees")
    roughness_m: Optional[float] = Field(None, ge=0.0, le=10.0, description="Surface roughness in meters")
    elevation_m: Optional[float] = Field(None, ge=-10000.0, le=10000.0, description="Surface elevation in meters relative to 1737.4 km sphere")
    crater_count: Optional[int] = Field(None, ge=0, le=1000, description="Detected hazardous craters in landing area")
    rock_count: Optional[int] = Field(None, ge=0, le=5000, description="Detected hazardous rocks/boulders in landing area")
    illumination_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Solar illumination percentage")
    earth_visibility_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Earth line-of-sight visibility percentage")
    science_value_rating: Optional[float] = Field(None, ge=0.0, le=100.0, description="Science prioritization rating (0-100)")
    weights: Optional[ScoringWeights] = Field(default_factory=ScoringWeights, description="Custom criteria weights")


class FactorSubscore(BaseModel):
    """Transparent calculation breakdown for a single criterion."""

    criterion: str
    raw_measurement: Optional[float]
    unit: str
    normalized_subscore: Optional[float] = Field(None, ge=0.0, le=100.0, description="Subscore from 0 (worst) to 100 (best)")
    weight: float
    weighted_contribution: Optional[float] = Field(None, description="Score contribution (normalized_subscore * weight)")
    status: str = Field("available", description="'available' or 'missing'")
    preference_direction: str = Field("lower_is_better", description="'lower_is_better' or 'higher_is_better'")
    description: str


class ScoreResponse(BaseModel):
    """Transparent multi-criteria suitability scoring response."""

    site_id: Optional[str] = None
    overall_suitability_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Composite score (0-100) or null if insufficient data")
    suitability_category: str = Field(
        ...,
        description="'Higher preliminary suitability', 'Moderate preliminary suitability', 'Lower preliminary suitability', or 'Insufficient data'",
    )
    score_coverage_pct: float = Field(..., ge=0.0, le=100.0, description="Percentage of factor weight covered by actual measurements")
    missing_factors: List[str] = Field(default_factory=list, description="List of criteria with unmeasured or missing data")
    evaluated_factors_count: int = Field(..., description="Count of evaluated factors")
    total_factors_count: int = Field(..., description="Total factors in criteria specification")
    subscores: List[FactorSubscore]
    scoring_methodology: str
    key_advantages: List[str]
    critical_concerns: List[str]
    warnings: List[str] = Field(default_factory=list, description="Caveats, coverage warnings, and threshold notices")
    criteria_version: str = Field("2.0-phase6", description="Scoring criteria and threshold version")
    disclaimer: str
