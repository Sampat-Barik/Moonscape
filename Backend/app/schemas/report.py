"""Schemas for mission landing-site evaluation report generation (Phase 8)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from app.core.constants import SCIENTIFIC_SAFETY_DISCLAIMER


class ReportGenerateRequest(BaseModel):
    """Input payload to compile a comprehensive lunar landing evaluation report."""

    analysis_id: Optional[str] = Field(None, description="Identifier of completed analysis (e.g. 'analysis_001')")
    site_id: Optional[str] = Field(None, description="Target site slug identifier from catalog")
    site_ids: Optional[List[str]] = Field(None, description="List of site IDs for multi-site comparative report (min 2)")
    custom_weights: Optional[Dict[str, float]] = Field(None, description="Custom criteria weight overrides for comparison")
    weights: Optional[Dict[str, float]] = Field(None, description="Alias for custom_weights")
    mission_profile: Optional[str] = Field("crewed_artemis_class", description="Mission profile preset for scoring weights")
    mission_title: Optional[str] = Field("Moonscape Lunar Landing Site Scientific Assessment", description="Mission or report title")
    include_ai_narrative: bool = Field(True, description="Whether to include synthesized AI scientific explanation")
    format: Optional[str] = Field(None, description="Desired report format: 'json', 'pdf', 'markdown', or 'html'")
    output_format: Optional[str] = Field(None, description="Alias for 'format'")
    summary_only: bool = Field(False, description="Whether to compile a concise 2-page executive summary PDF instead of full dossier")

    @model_validator(mode="before")
    @classmethod
    def reconcile_format(cls, data: Any) -> Any:
        if isinstance(data, dict):
            fmt = (data.get("format") or data.get("output_format") or "json").lower()
            allowed = {"json", "pdf", "markdown", "html"}
            if fmt not in allowed:
                raise ValueError(f"Unsupported report format '{fmt}'. Allowed formats are: {sorted(allowed)}.")
            data["format"] = fmt
            data["output_format"] = fmt
            if "weights" in data and "custom_weights" not in data:
                data["custom_weights"] = data["weights"]
        return data

    @model_validator(mode="after")
    def validate_target(self) -> "ReportGenerateRequest":
        if self.site_ids is not None:
            if len(self.site_ids) < 2:
                raise ValueError("Comparison report requires at least two distinct landing sites.")
            if len(self.site_ids) != len(set(self.site_ids)):
                raise ValueError("Duplicate site IDs found in comparison request. All site IDs must be unique.")
            return self
        if not self.analysis_id and not self.site_id:
            raise ValueError("Either 'analysis_id', 'site_id', or 'site_ids' must be specified to generate a report.")
        return self


class ComparisonReportRequest(BaseModel):
    """Payload to generate a comprehensive multi-site comparative assessment report."""

    site_ids: List[str] = Field(..., min_length=2, description="List of candidate site IDs to compare (minimum 2)")
    mission_profile: Optional[str] = Field("crewed_artemis_class", description="Mission profile preset for scoring weights")
    custom_weights: Optional[Dict[str, float]] = Field(None, description="Custom criteria weight overrides")
    weights: Optional[Dict[str, float]] = Field(None, description="Alias for custom_weights")
    mission_title: Optional[str] = Field(
        "MoonScape Lunar South Pole Comparative Landing Site Assessment",
        description="Title printed on cover and header",
    )
    format: Optional[str] = Field("pdf", description="Report format: 'pdf', 'json', 'markdown', or 'html'")
    output_format: Optional[str] = Field(None, description="Alias for 'format'")
    summary_only: bool = Field(False, description="Whether to compile a concise 2-page executive summary PDF instead of full dossier")

    @field_validator("site_ids")
    @classmethod
    def validate_site_ids(cls, v: List[str]) -> List[str]:
        if not v or len(v) < 2:
            raise ValueError("Comparison report requires at least two distinct landing sites.")
        if len(v) != len(set(v)):
            raise ValueError("Duplicate site IDs found in comparison request. All site IDs must be unique.")
        return v

    @model_validator(mode="before")
    @classmethod
    def reconcile_format(cls, data: Any) -> Any:
        if isinstance(data, dict):
            fmt = (data.get("format") or data.get("output_format") or "pdf").lower()
            allowed = {"json", "pdf", "markdown", "html"}
            if fmt not in allowed:
                raise ValueError(f"Unsupported report format '{fmt}'. Allowed formats are: {sorted(allowed)}.")
            data["format"] = fmt
            data["output_format"] = fmt
            if "weights" in data and "custom_weights" not in data:
                data["custom_weights"] = data["weights"]
        return data


class ComparisonReportResponse(BaseModel):
    """Metadata response for comparative evaluation report."""

    report_id: str
    generated_at: str
    site_count: int
    site_ids: List[str]
    mission_profile: str
    highest_ranked_site: Optional[str] = None
    rankings: List[Dict[str, Any]] = Field(default_factory=list)
    format: str = "pdf"
    disclaimer: str = SCIENTIFIC_SAFETY_DISCLAIMER


# ---------------------------------------------------------------------------
# Structured Report Content Elements (19 Mandated Scientific Elements)
# ---------------------------------------------------------------------------

class CoordinatesModel(BaseModel):
    latitude: float
    longitude: float
    formatted: str


class ElevationReportSection(BaseModel):
    min_m: Optional[float]
    max_m: Optional[float]
    mean_m: Optional[float]
    relief_variation_m: Optional[float]
    std_dev_m: Optional[float]
    datum: str = "Lunar reference sphere (R = 1737.4 km)"
    units: str = "meters"


class SlopeReportSection(BaseModel):
    min_deg: Optional[float]
    max_deg: Optional[float]
    mean_deg: Optional[float]
    median_deg: Optional[float]
    std_dev_deg: Optional[float]
    operator: str = "Horn (1981) 3x3 Finite-Difference Operator"
    ideal_pct: float
    acceptable_pct: float
    marginal_pct: float
    critical_hazardous_pct: float
    units: str = "degrees"


class RoughnessReportSection(BaseModel):
    mean_rms_m: Optional[float]
    max_rms_m: Optional[float]
    baseline_meters: float = 15.0
    method: str = "Root-Mean-Square (RMS) Residual Height Deviation"
    safe_touchdown_fraction_pct: float


class IlluminationReportSection(BaseModel):
    status: str
    cumulative_illumination_pct: Optional[float]
    instantaneous_sunlit_fraction_pct: Optional[float]
    is_permanently_shadowed_region: bool
    estimated_surface_temp_k: Optional[float]
    time_period_evaluated: str
    thermal_caveat: str


class HazardReportSection(BaseModel):
    craters_detected: Optional[int]
    rocks_detected: Optional[int]
    hazard_status: str
    severity_assessment: str
    calibration_notice: str


class SuitabilityReportSection(BaseModel):
    overall_score: Optional[float]
    category: str
    score_coverage_pct: float
    evaluated_factors_count: int
    total_factors_count: int
    criteria_version: str


class MethodologyReportSection(BaseModel):
    topographic_slope: str
    surface_roughness: str
    solar_illumination: str
    multi_criteria_scoring: str


class UncertaintyReportSection(BaseModel):
    vertical_accuracy_m: float = 1.0
    horizontal_resolution_m: float = 5.0
    interpolation_uncertainty: str
    hazard_scale_uncertainty: str


class ScientificReportData(BaseModel):
    """Complete 19-element structured scientific report."""

    # 1. Report title and generation date
    title: str
    generated_at_utc: str
    generated_at_human: str

    # 2. Analysis ID
    analysis_id: str
    site_id: Optional[str] = None
    site_name: Optional[str] = None

    # 3. Selected lunar coordinates
    coordinates: CoordinatesModel

    # 4. Analysis radius
    analysis_radius_meters: float

    # 5. Elevation measurements
    elevation: ElevationReportSection

    # 6. Slope measurements
    slope: SlopeReportSection

    # 7. Roughness measurements
    roughness: RoughnessReportSection

    # 8. Illumination information
    illumination: IlluminationReportSection

    # 9. Crater and rock detection results
    hazards: HazardReportSection

    # 10. Preliminary suitability score
    suitability: SuitabilityReportSection

    # 11. Factor breakdown
    factor_breakdown: List[Dict[str, Any]]

    # 12. Positive factors
    positive_factors: List[str]

    # 13. Risk factors
    risk_factors: List[str]

    # 14. Data sources
    data_sources: Dict[str, Any]

    # 15. Methodology
    methodology: MethodologyReportSection

    # 16. Missing data
    missing_data: List[str]

    # 17. Uncertainty
    uncertainty: UncertaintyReportSection

    # 18. Limitations
    limitations: List[str]

    # 19. Final preliminary conclusion
    conclusion: str

    disclaimer: str = SCIENTIFIC_SAFETY_DISCLAIMER


class ReportGenerateResponse(BaseModel):
    """Unified report generation API response."""

    report_id: str
    generated_at: str
    mission_title: str
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    analysis_id: Optional[str] = None
    output_format: str
    content: Optional[str] = Field(None, description="Formatted content or JSON string")
    structured_summary: Optional[Dict[str, Any]] = Field(None, description="Key metrics and decision matrices")
    report_data: Optional[ScientificReportData] = Field(None, description="19-element structured scientific data object")
    disclaimer: str = SCIENTIFIC_SAFETY_DISCLAIMER
