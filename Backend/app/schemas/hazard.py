"""Schemas for crater, boulder, and topographic hazard detection/prediction."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HazardPredictRequest(BaseModel):
    """Input payload to predict lunar surface touchdown hazards."""

    center_lat: float = Field(..., ge=-90.0, le=-80.0, description="Center latitude of candidate landing zone (-90 to -80)")
    center_lon: float = Field(..., ge=-180.0, le=360.0, description="Center longitude of candidate landing zone (-180 to 360)")
    radius_meters: float = Field(1000.0, ge=100.0, le=10000.0, description="Hazard evaluation radius in meters")
    min_crater_diameter_m: float = Field(5.0, ge=2.0, le=100.0, description="Minimum crater diameter threshold for hazard tagging")
    boulder_detection_sensitivity: float = Field(0.7, ge=0.1, le=1.0, description="Model sensitivity threshold for boulder detection")


class HazardItem(BaseModel):
    """An individual identified or predicted hazard feature."""

    hazard_type: str = Field(..., description="'crater', 'boulder', 'escarpment', or 'permanent_shadow'")
    latitude: float
    longitude: float
    estimated_size_m: float = Field(..., description="Estimated diameter or height in meters")
    severity: str = Field(..., description="'low', 'medium', 'high', 'critical'")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence metric from detector/model")
    source: str = Field(..., description="Detection origin: 'LOLA_DEM_curvature', 'LROC_optical', or 'heuristic_model'")


class HazardPredictResponse(BaseModel):
    """Output results of hazard prediction and surface risk mapping."""

    hazard_assessment_id: str
    center_lat: float
    center_lon: float
    radius_meters: float
    total_hazards_detected: int
    craters_count: int
    boulders_count: int
    steep_slope_cells: int
    shadow_coverage_pct: Optional[float]
    overall_hazard_level: str = Field(..., description="'low', 'moderate', 'high', or 'critical'")
    hazards: List[HazardItem]
    model_metadata: Dict[str, Any] = Field(..., description="Model description, training source, and evaluation metrics")
    disclaimer: str
