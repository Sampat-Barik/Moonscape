"""Schemas for AI-driven scientific landing explanation and trade-off synthesis."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AIExplainRequest(BaseModel):
    """Input payload to request scientific explanation and trade-off analysis."""

    site_id: Optional[str] = Field(None, description="Catalog site identifier")
    site_name: Optional[str] = Field(None, description="Human readable name of region")
    latitude: Optional[float] = Field(None, ge=-90.0, le=-80.0, description="Latitude of candidate zone")
    longitude: Optional[float] = Field(None, ge=-180.0, le=360.0, description="Longitude of candidate zone")
    topographic_data: Optional[Dict[str, Any]] = Field(None, description="Metrics dictionary containing slope, roughness, etc.")
    score_data: Optional[Dict[str, Any]] = Field(None, description="Output from scoring engine")
    focus_topics: Optional[List[str]] = Field(
        None,
        description="Optional specific topics: 'topography', 'illumination', 'thermal', 'traverse', 'sampling'",
    )
    user_query: Optional[str] = Field(None, description="Specific scientific inquiry or query from mission planner")


class AIExplainResponse(BaseModel):
    """Scientifically grounded, transparent narrative explanation response."""

    explanation_id: str
    target_site: str
    executive_summary: str
    geomorphology_assessment: str
    thermal_and_power_assessment: str
    communication_and_direct_line_of_sight: str
    traverse_and_sampling_potential: str
    key_engineering_tradeoffs: List[str]
    mitigation_strategies: List[str]
    model_origin: str
    disclaimer: str
