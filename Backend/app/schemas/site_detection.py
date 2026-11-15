"""Schemas for automated contiguous landing-site detection from NASA lunar DEMs."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class DetectLandingSitesRequest(BaseModel):
    """Input payload to trigger automated contiguous safe landing zone search."""

    center_lat: float = Field(..., ge=-90.0, le=-70.0, description="Center latitude of search region (-90 to -70)")
    center_lon: float = Field(..., ge=-180.0, le=360.0, description="Center longitude of search region (-180 to 360)")
    search_radius_meters: float = Field(1500.0, ge=200.0, le=10000.0, description="Physical search radius in meters")
    max_slope_deg: float = Field(8.0, ge=2.0, le=15.0, description="Maximum allowable slope for touchdown (deg)")
    max_roughness_m: float = Field(0.35, ge=0.1, le=1.5, description="Maximum allowable RMS roughness (meters)")
    min_landing_diameter_meters: float = Field(50.0, ge=20.0, le=500.0, description="Minimum contiguous patch diameter required for lander gear clearance")
    mission_profile: Optional[str] = Field("artemis_hls", description="Mission profile ('artemis_hls', 'clps_cargo', 'polar_rover', 'base_camp')")

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

            if "radius_meters" in data and "search_radius_meters" not in data:
                data["search_radius_meters"] = data["radius_meters"]
            elif "radius_m" in data and "search_radius_meters" not in data:
                data["search_radius_meters"] = data["radius_m"]
            elif "radius" in data and "search_radius_meters" not in data:
                data["search_radius_meters"] = data["radius"]
        return data


class DetectedLandingZone(BaseModel):
    """An individual contiguous candidate landing zone detected from real raster elevation."""

    zone_id: str = Field(..., description="Unique generated identifier for detected zone")
    centroid_lat: float = Field(..., description="Planetocentric latitude of zone centroid (deg)")
    centroid_lon: float = Field(..., description="Planetocentric longitude of zone centroid (deg)")
    contiguous_area_m2: float = Field(..., description="Total contiguous safe surface area (m^2)")
    effective_diameter_m: float = Field(..., description="Equivalent circular diameter (meters)")
    pixel_count: int = Field(..., description="Number of contiguous valid raster cells")
    mean_slope_deg: float = Field(..., description="Mean slope across the contiguous patch (deg)")
    max_slope_deg: float = Field(..., description="Peak slope within the contiguous patch (deg)")
    mean_roughness_m: float = Field(..., description="Mean RMS surface roughness across the patch (m)")
    mean_elevation_m: float = Field(..., description="Mean surface elevation across the patch (m)")
    suitability_score: float = Field(..., ge=0.0, le=100.0, description="MCDA preliminary suitability score")
    ml_model_score: Optional[float] = Field(None, description="ML surrogate suitability score (0-100)")
    hard_constraint_status: str = Field("passed", description="'passed' or 'violated'")
    safety_rank: int = Field(..., description="Rank among detected candidate sites (1 = best)")
    feasibility_status: str = Field(..., description="'optimal', 'nominal', or 'marginal'")


class DetectLandingSitesResponse(BaseModel):
    """Results of contiguous landing zone detection pipeline."""

    status: str = Field("success", description="'success' or 'no_sites_found'")
    center_lat: float
    center_lon: float
    search_radius_meters: float
    total_sites_detected: int
    candidate_zones: List[DetectedLandingZone] = Field(default_factory=list)
    dataset_metadata: Dict[str, Any] = Field(default_factory=dict)
    summary: str
    mission_profile: Optional[str] = Field("artemis_hls", description="Active mission profile")
    warnings: List[str] = Field(default_factory=list)
