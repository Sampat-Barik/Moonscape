"""Schemas for transparent multi-criteria landing site suitability scoring."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class ScoringWeights(BaseModel):
    """Normalized weighting coefficients across multi-criteria landing factors."""

    slope_weight: float = Field(0.35, ge=0.0, le=1.0, description="Weight for topographic slope penalty")
    roughness_weight: float = Field(0.20, ge=0.0, le=1.0, description="Weight for terrain roughness penalty")
    illumination_weight: float = Field(0.20, ge=0.0, le=1.0, description="Weight for solar illumination bonus")
    communication_weight: float = Field(0.15, ge=0.0, le=1.0, description="Weight for Earth line-of-sight communication")
    science_weight: float = Field(0.10, ge=0.0, le=1.0, description="Weight for scientific accessibility and value")

    @model_validator(mode="after")
    def normalize_weights(self) -> "ScoringWeights":
        total = (
            self.slope_weight
            + self.roughness_weight
            + self.illumination_weight
            + self.communication_weight
            + self.science_weight
        )
        if total <= 0:
            raise ValueError("Sum of scoring weights must be greater than zero.")
        return self


class ScoreRequest(BaseModel):
    """Input payload to evaluate site suitability score."""

    site_id: Optional[str] = Field(None, description="Catalog site identifier (if scoring an existing site)")
    slope_deg: Optional[float] = Field(None, ge=0.0, le=90.0, description="Topographic slope in degrees")
    roughness_m: Optional[float] = Field(None, ge=0.0, le=10.0, description="Surface roughness in meters")
    illumination_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Solar illumination percentage")
    earth_visibility_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Earth line-of-sight visibility percentage")
    science_value_rating: Optional[float] = Field(None, ge=0.0, le=100.0, description="Science prioritization rating (0-100)")
    weights: Optional[ScoringWeights] = Field(default_factory=ScoringWeights, description="Custom criteria weights")


class FactorSubscore(BaseModel):
    """Transparent calculation breakdown for a single criterion."""

    criterion: str
    raw_measurement: Optional[float]
    unit: str
    normalized_subscore: float = Field(..., ge=0.0, le=100.0, description="Subscore from 0 (worst) to 100 (best)")
    weight: float
    weighted_contribution: float
    description: str


class ScoreResponse(BaseModel):
    """Transparent multi-criteria suitability scoring response."""

    site_id: Optional[str]
    overall_suitability_score: float = Field(..., ge=0.0, le=100.0, description="Composite score (0-100)")
    suitability_category: str = Field(..., description="'Optimal', 'Nominal', 'Marginal', 'High Risk', or 'Unsuitable'")
    subscores: List[FactorSubscore]
    scoring_methodology: str
    key_advantages: List[str]
    critical_concerns: List[str]
    disclaimer: str
