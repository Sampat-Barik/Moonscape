"""Schemas for crater, boulder, and topographic hazard detection and ML inference."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


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

    id: Optional[str] = Field(None, description="Stable unique identifier for the hazard feature (e.g. 'ESC-01', 'ROUGH-01')")
    hazard_type: str = Field(..., description="'crater', 'boulder', 'escarpment', or 'permanent_shadow'")
    latitude: float
    longitude: float
    estimated_size_m: float = Field(..., description="Estimated diameter or height in meters")
    severity: str = Field(..., description="'low', 'medium', 'high', 'critical'")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence metric from detector/model")
    source: str = Field(..., description="Detection origin: 'LOLA_DEM_curvature', 'LROC_optical', or 'heuristic_model'")
    measurement_name: Optional[str] = Field(None, description="Physical metric name (e.g. 'Peak Slope Gradient', 'RMS Surface Roughness', 'Basin Diameter')")
    measurement_unit: Optional[str] = Field(None, description="Physical units (e.g. 'deg', 'm')")
    measurement_value: Optional[float] = Field(None, description="Numerical measurement in specified units")
    confidence_type: Optional[str] = Field(None, description="Confidence origin: 'model_confidence', 'deterministic_gradient', 'heuristic_indicator'")
    detection_method: Optional[str] = Field(None, description="Algorithmic or ML method used for detection")
    feature_extent_m: Optional[float] = Field(None, description="Spatial span or footprint of the feature in meters")
    cell_count: Optional[int] = Field(None, description="Raster cell count for contiguous terrain features")


class HazardPredictRequest(BaseModel):
    """Input payload to predict lunar surface touchdown hazards via coordinates or ML imagery."""

    # Topographic coordinate inputs (optional for ML image queries)
    center_lat: Optional[float] = Field(
        None, ge=-90.0, le=-70.0, description="Center latitude of candidate landing zone (-90 to -70)"
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

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "latitude" in data and "center_lat" not in data:
                data["center_lat"] = data["latitude"]
            elif "lat" in data and "center_lat" not in data:
                data["center_lat"] = data["lat"]

            if "longitude" in data and "center_lon" not in data:
                data["center_lon"] = data["longitude"]
            elif "lon" in data and "center_lon" not in data:
                data["center_lon"] = data["lon"]

            if "radius_m" in data and "radius_meters" not in data:
                data["radius_meters"] = data["radius_m"]
            elif "radius" in data and "radius_meters" not in data:
                data["radius_meters"] = data["radius"]
        return data

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
    craters: Optional[List[HazardItem]] = Field(None, description="Identified craters list")
    rocks: Optional[List[HazardItem]] = Field(None, description="Identified boulders list")
    overlay_image: Optional[str] = Field(None, description="Base64 PNG data URL of optical detection overlay image")
    source_product_id: Optional[str] = Field(None, description="NASA or ISRO source observation product ID")
    source_resolution_m: Optional[float] = Field(None, description="Resolution of evaluated source image in meters per pixel")
    optical_status: Optional[str] = Field(None, description="'success', 'not_available', 'outside_coverage', 'error'")
    optical_provenance_state: Optional[str] = Field(None, description="'exact_frame_processed', 'proximity_frame_cataloged', 'catalog_reference_only', 'unavailable'")
    dem_provenance_state: Optional[str] = Field(None, description="'measured_lola_dem', 'calibrated_sample_baseline', 'unavailable'")
    coverage_zone: Optional[str] = Field("core", description="'core', 'extended', 'context', 'outside', 'invalid'")
    model_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata dictionary")
    disclaimer: Optional[str] = Field(None, description="Scientific safety disclaimer")

    model_config = ConfigDict(extra="allow")
