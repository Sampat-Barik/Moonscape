"""Schemas for AI-driven scientific landing explanation and trade-off synthesis."""

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from app.core.constants import SCIENTIFIC_SAFETY_DISCLAIMER


class AIExplainRequest(BaseModel):
    """Input payload to request scientific explanation and trade-off analysis."""

    analysis_id: Optional[str] = Field(None, description="Identifier of completed spatial analysis run (e.g. 'analysis_001')")
    site_id: Optional[str] = Field(None, description="Catalog site identifier (e.g. 'shackleton_connecting_ridge')")
    site_name: Optional[str] = Field(None, description="Human readable name of region")
    latitude: Optional[float] = Field(None, ge=-90.0, le=-70.0, description="Latitude of candidate zone")
    longitude: Optional[float] = Field(None, ge=-180.0, le=360.0, description="Longitude of candidate zone")
    topographic_data: Optional[Dict[str, Any]] = Field(None, description="Metrics dictionary containing slope, roughness, etc.")
    score_data: Optional[Dict[str, Any]] = Field(None, description="Output from scoring engine")
    focus_topics: Optional[List[str]] = Field(
        None,
        description="Optional specific topics: 'topography', 'illumination', 'thermal', 'traverse', 'sampling'",
    )
    user_query: Optional[str] = Field(None, description="Specific scientific inquiry or query from mission planner")

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "query" in data and "user_query" not in data:
                data["user_query"] = data["query"]
            elif "prompt" in data and "user_query" not in data:
                data["user_query"] = data["prompt"]
            elif "question" in data and "user_query" not in data:
                data["user_query"] = data["question"]

            if "lat" in data and "latitude" not in data:
                data["latitude"] = data["lat"]
            if "lon" in data and "longitude" not in data:
                data["longitude"] = data["lon"]
        return data


class AIExplainResponse(BaseModel):
    """Scientifically grounded, transparent narrative explanation response."""

    # Phase 7 Core API Contract
    analysis_id: Optional[str] = Field(None, description="Referenced spatial analysis run ID")
    explanation: Optional[str] = Field(None, description="Accessible scientific explanation grounded strictly in backend measurements")
    positive_factors: List[str] = Field(default_factory=list, description="Favourable landing terrain, power, and environmental conditions")
    risk_factors: List[str] = Field(default_factory=list, description="Identified operational, slope, clearance, or thermal hazards")
    limitations: List[str] = Field(default_factory=list, description="Uncertainties, missing data factors, and screening boundaries")
    conclusion: str = Field("Preliminary assessment only.", description="Concluding operational screening remark")

    # Backward Compatibility & Mission Planning Fields
    explanation_id: str = Field(default_factory=lambda: f"EXP-{uuid.uuid4().hex[:8].upper()}")
    target_site: str = Field("Candidate Lunar Zone", description="Target region or site name")
    executive_summary: Optional[str] = Field(None, description="High-level mission summary")
    geomorphology_assessment: Optional[str] = Field(None, description="Detailed slope and terrain geomorphology assessment")
    thermal_and_power_assessment: Optional[str] = Field(None, description="Illumination, temperature, and power conditions")
    communication_and_direct_line_of_sight: Optional[str] = Field(None, description="Earth line-of-sight and relay needs")
    traverse_and_sampling_potential: Optional[str] = Field(None, description="Surface trafficability and sampling value")
    key_engineering_tradeoffs: List[str] = Field(default_factory=list, description="Engineering trade-offs")
    mitigation_strategies: List[str] = Field(default_factory=list, description="Operational risk mitigation strategies")
    model_origin: str = Field("Moonscape Grounded Scientific Explainer", description="Originating LLM or deterministic rule engine")
    disclaimer: str = Field(SCIENTIFIC_SAFETY_DISCLAIMER, description="Scientific screening caveat")

    @model_validator(mode="after")
    def sync_backward_compatible_fields(self) -> "AIExplainResponse":
        if not self.explanation and self.executive_summary:
            self.explanation = self.executive_summary
        if not self.executive_summary and self.explanation:
            self.executive_summary = self.explanation
        if not self.explanation:
            self.explanation = "Scientific landing site evaluation."
        if not self.key_engineering_tradeoffs:
            tradeoffs = list(self.risk_factors)
            if len(tradeoffs) < 2:
                tradeoffs.extend([
                    "Solar Power vs. Slope Hazard: Peak elevations maximize illumination but narrow ridge crests reduce touchdown footprint clearance.",
                    "Direct Earth Contact vs. Topographic Shadowing: Direct Earth line-of-sight is vulnerable to lunar orbital libration dips.",
                ])
            self.key_engineering_tradeoffs = tradeoffs[:4]

        if not self.mitigation_strategies:
            mitigations = [f"Mitigate: {item}" for item in (self.risk_factors + self.limitations)]
            if len(mitigations) < 2:
                mitigations.extend([
                    "Implement active Hazard Detection and Avoidance (HDA) with flash lidar to detect sub-meter boulders during terminal descent.",
                    "Schedule landing touchdown during the peak southern lunar summer illumination window to maximize battery buffers.",
                ])
            self.mitigation_strategies = mitigations[:4]
        if not self.geomorphology_assessment:
            self.geomorphology_assessment = f"Geomorphological conditions: {self.explanation}"
        if not self.thermal_and_power_assessment:
            self.thermal_and_power_assessment = "Illumination and thermal conditions evaluated against lunar South Pole solar elevation models."
        if not self.communication_and_direct_line_of_sight:
            self.communication_and_direct_line_of_sight = "Direct-to-Earth communication depends on local massif relief and lunar libration cycles."
        if not self.traverse_and_sampling_potential:
            self.traverse_and_sampling_potential = "Surface mobility and sample accessibility depend on local rim slopes and terrain roughness."
        return self
