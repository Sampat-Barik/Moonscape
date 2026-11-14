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
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Target latitude in degrees")
    longitude: Optional[float] = Field(None, ge=-180.0, le=360.0, description="Target longitude in degrees")
    radius_m: Optional[float] = Field(50.0, ge=10.0, le=25000.0, description="Evaluation radius in meters")
    slope_deg: Optional[float] = Field(None, ge=0.0, le=90.0, description="Topographic slope in degrees")
    max_slope_deg: Optional[float] = Field(None, ge=0.0, le=90.0, description="Peak localized slope in degrees")
    p95_slope_deg: Optional[float] = Field(None, ge=0.0, le=90.0, description="95th percentile slope in degrees")
    roughness_m: Optional[float] = Field(None, ge=0.0, le=10.0, description="Surface roughness in meters")
    elevation_m: Optional[float] = Field(None, ge=-10000.0, le=10000.0, description="Surface elevation in meters relative to 1737.4 km sphere")
    crater_count: Optional[int] = Field(None, ge=0, le=1000, description="Detected hazardous craters in landing area")
    rock_count: Optional[int] = Field(None, ge=0, le=5000, description="Detected hazardous rocks/boulders in landing area")
    illumination_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Solar illumination percentage")
    earth_visibility_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Earth line-of-sight visibility percentage")
    contiguous_diameter_m: Optional[float] = Field(None, ge=0.0, le=5000.0, description="Safe contiguous touchdown diameter (m)")
    max_continuous_dark_h: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Maximum continuous night duration (h)")
    science_value_rating: Optional[float] = Field(None, ge=0.0, le=100.0, description="Science prioritization rating (0-100)")
    mission_profile: Optional[str] = Field(None, description="Mission profile ('artemis_hls', 'clps_cargo', 'polar_rover', 'base_camp')")
    weights: Optional[ScoringWeights] = Field(default_factory=ScoringWeights, description="Custom criteria weights")

    @model_validator(mode="before")
    @classmethod
    def normalize_measurements_payload(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Coordinate aliases
            if "lat" in data and "latitude" not in data:
                data["latitude"] = data["lat"]
            if "lon" in data and "longitude" not in data:
                data["longitude"] = data["lon"]
            if "radius_meters" in data and "radius_m" not in data:
                data["radius_m"] = data["radius_meters"]

            # If incoming data wraps measurements in a nested "measurements" dict, flatten them
            meas = data.get("measurements")
            if isinstance(meas, dict):
                key_mapping = {
                    "slope_mean": "slope_deg",
                    "slope_deg": "slope_deg",
                    "slope_max": "max_slope_deg",
                    "max_slope_deg": "max_slope_deg",
                    "roughness_rms": "roughness_m",
                    "roughness_m": "roughness_m",
                    "elevation_mean": "elevation_m",
                    "elevation_m": "elevation_m",
                    "sunlight_percentage": "illumination_pct",
                    "illumination_fraction_pct": "illumination_pct",
                    "illumination_pct": "illumination_pct",
                    "earth_comm_percentage": "earth_visibility_pct",
                    "earth_visibility_fraction_pct": "earth_visibility_pct",
                    "earth_visibility_pct": "earth_visibility_pct",
                    "crater_count": "crater_count",
                    "boulder_count": "rock_count",
                    "rock_count": "rock_count",
                }
                for src_key, dst_key in key_mapping.items():
                    if src_key in meas and (dst_key not in data or data[dst_key] is None):
                        data[dst_key] = meas[src_key]
        return data


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
    scientific_baseline_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Deterministic MCDA score")
    ml_model_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Machine learning surrogate suitability score")
    model_version: Optional[str] = Field(None, description="Active ML surrogate model version")
    mission_profile: str = Field("artemis_hls", description="Active mission profile")
    hard_constraint_status: str = Field("passed", description="'passed' or 'violated'")
    hard_constraint_violations: List[str] = Field(default_factory=list, description="Specific hard engineering constraints violated")
    uncertainty_score_std: Optional[float] = Field(None, description="Score uncertainty standard error under measurement perturbation")
    confidence_interval_95: Optional[List[float]] = Field(None, description="[min, max] 95% confidence interval")
    feature_contributions: Optional[Dict[str, float]] = Field(None, description="Feature contribution deviations from baseline mean")
    suitability_category: str = Field(
        ...,
        description="'Higher preliminary suitability', 'Moderate preliminary suitability', 'Lower preliminary suitability', 'Disqualified (Hard Constraint Violation)', or 'Insufficient data'",
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

    # Convenience frontend-aligned aliases
    score: Optional[float] = None
    grade: Optional[str] = None
    label: Optional[str] = None
    breakdown: Optional[Dict[str, Optional[float]]] = None

    @model_validator(mode="after")
    def sync_frontend_aliases(self) -> "ScoreResponse":
        if self.score is None:
            self.score = self.overall_suitability_score
        if self.label is None:
            self.label = self.suitability_category
        if self.grade is None and self.suitability_category:
            cat = self.suitability_category
            if "Higher" in cat or cat == "favorable":
                self.grade = "A"
            elif "Moderate" in cat or cat == "marginal":
                self.grade = "B"
            elif "Lower" in cat or cat == "unfavorable":
                self.grade = "C"
            elif "Disqualified" in cat:
                self.grade = "F"
            else:
                self.grade = "N/A"
        if self.breakdown is None:
            bd: Dict[str, Optional[float]] = {}
            for s in self.subscores:
                bd[s.criterion] = s.normalized_subscore
                # Add simplified / lowercase keys for robust frontend lookups
                norm_key = s.criterion.lower().replace(" ", "_")
                bd[norm_key] = s.normalized_subscore
                if "slope" in norm_key and "slope" not in bd:
                    bd["slope"] = s.normalized_subscore
                elif "roughness" in norm_key and "roughness" not in bd:
                    bd["roughness"] = s.normalized_subscore
                elif "illumination" in norm_key and "illumination" not in bd:
                    bd["illumination"] = s.normalized_subscore
            self.breakdown = bd
        return self
