"""Schemas for crater, boulder, and topographic hazard detection and ML inference."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class BoundingBox(BaseModel):
    """2D bounding region in normalized or pixel coordinates."""

    ymin: float = Field(..., description="Top boundary coordinate")
    xmin: float = Field(..., description="Left boundary coordinate")
    ymax: float = Field(..., description="Bottom boundary coordinate")
    xmax: float = Field(..., description="Right boundary coordinate")


class DetectionItem(BaseModel):
    """An individual ML-detected crater, rock, or surface feature."""

    label: str = Field(..., description="Hazard class: 'crater', 'rock', 'boulder', 'escarpment'")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    bounding_box: Optional[BoundingBox] = Field(None, description="Bounding region coordinates")
    center_pixel: Optional[List[int]] = Field(None, description="[y, x] center coordinate in pixel space")
    pixel_diameter: Optional[float] = Field(None, description="Feature diameter or span in pixels")
    estimated_size_m: Optional[float] = Field(
        None,
        description="Physical diameter/span in meters. Null if spatial scale (meters per pixel) is uncalibrated.",
    )
    severity: Optional[str] = Field("medium", description="'low', 'medium', 'high', 'critical'")
    mask_rle: Optional[str] = Field(None, description="Run-length encoded binary mask if segmentation model is used")


class HazardItem(BaseModel):
    """An individual identified or predicted topographic hazard feature (Phase 1 compatibility)."""

    hazard_type: str = Field(..., description="'crater', 'boulder', 'escarpment', or 'permanent_shadow'")
    latitude: float
    longitude: float
    estimated_size_m: float = Field(..., description="Estimated diameter or height in meters")
    severity: str = Field(..., description="'low', 'medium', 'high', 'critical'")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence metric from detector/model")
    source: str = Field(..., description="Detection origin: 'LOLA_DEM_curvature', 'LROC_optical', or 'heuristic_model'")


class HazardPredictRequest(BaseModel):
    """Input payload to predict lunar surface touchdown hazards via coordinates or ML imagery."""

    # Topographic coordinate inputs (optional for ML image queries)
    center_lat: Optional[float] = Field(
        None, ge=-90.0, le=-80.0, description="Center latitude of candidate landing zone (-90 to -80)"
    )
    center_lon: Optional[float] = Field(
        None, ge=-180.0, le=360.0, description="Center longitude of candidate landing zone (-180 to 360)"
    )
    radius_meters: Optional[float] = Field(
        1000.0, ge=100.0, le=10000.0, description="Hazard evaluation radius in meters"
    )
    min_crater_diameter_m: Optional[float] = Field(
        5.0, ge=2.0, le=100.0, description="Minimum crater diameter threshold for hazard tagging"
    )
    boulder_detection_sensitivity: Optional[float] = Field(
        0.7, ge=0.1, le=1.0, description="Model sensitivity threshold for boulder detection"
    )

    # ML optical / SAR image inputs
    image_base64: Optional[str] = Field(
        None, description="Base64 encoded optical image (PNG, JPEG, or TIFF), with or without data URI scheme"
    )
    image_path: Optional[str] = Field(
        None, description="Local or onboard file path to lunar optical/SAR image"
    )
    spatial_resolution_mpp: Optional[float] = Field(
        None, gt=0.0, le=1000.0, description="Spatial scale in meters per pixel for physical metric sizing"
    )
    confidence_threshold: Optional[float] = Field(
        0.50, ge=0.0, le=1.0, description="Minimum confidence threshold for hazard detection"
    )

    model_config = ConfigDict(extra="ignore")


class HazardPredictResponse(BaseModel):
    """Unified output results of hazard prediction and surface risk mapping."""

    status: str = Field("success", description="'success', 'not_available', or 'error'")
    detections: List[DetectionItem] = Field(default_factory=list, description="List of ML hazard detections")
    crater_count: Optional[int] = Field(None, description="Total detected craters")
    rock_count: Optional[int] = Field(None, description="Total detected rocks/boulders")
    warnings: List[str] = Field(default_factory=list, description="Operational warnings or validation caveats")
    model_name: Optional[str] = Field(None, description="ML model identifier")
    model_version: Optional[str] = Field(None, description="ML model version")
    limitations: Optional[str] = Field(None, description="Scientific limitations and validation domain caveats")

    # Phase 1 Topographic DEM compatibility fields
    hazard_assessment_id: Optional[str] = Field(None, description="Topographic assessment identifier")
    center_lat: Optional[float] = Field(None, description="Center latitude of assessment area")
    center_lon: Optional[float] = Field(None, description="Center longitude of assessment area")
    radius_meters: Optional[float] = Field(None, description="Assessment radius in meters")
    total_hazards_detected: Optional[int] = Field(None, description="Total count of hazards detected")
    craters_count: Optional[int] = Field(None, description="Crater count alias")
    boulders_count: Optional[int] = Field(None, description="Boulder count alias")
    steep_slope_cells: Optional[int] = Field(None, description="Count of steep slope cells (>15 deg)")
    shadow_coverage_pct: Optional[float] = Field(None, description="Permanent shadow coverage percentage")
    overall_hazard_level: Optional[str] = Field(None, description="'low', 'moderate', 'high', 'critical'")
    hazards: Optional[List[HazardItem]] = Field(default_factory=list, description="Topographic hazard items")
    model_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata dictionary")
    disclaimer: Optional[str] = Field(None, description="Scientific safety disclaimer")

    model_config = ConfigDict(extra="allow")
