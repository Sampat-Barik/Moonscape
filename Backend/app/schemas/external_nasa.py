"""Schemas for external NASA integrations: JPL Horizons, Moon Trek, and LROC QuickMap."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExternalSourceStatus(BaseModel):
    """Operational status and provenance for an external scientific service."""

    source_id: str
    name: str
    status: str  # "operational", "degraded", "offline"
    endpoint_url: str
    description: str
    documentation_url: str
    is_live_accessible: bool
    cached_entries_count: int = 0
    notes: str


class ExternalSourcesStatusResponse(BaseModel):
    """Combined operational status across all external NASA services."""

    horizons: ExternalSourceStatus
    moon_trek: ExternalSourceStatus
    lroc_quickmap: ExternalSourceStatus
    timestamp: str


class HorizonsQueryRequest(BaseModel):
    """Payload to query NASA JPL Horizons astronomical ephemerides."""

    latitude: float = Field(..., ge=-90.0, le=90.0, description="Observer latitude on Moon (-90 to +90)")
    longitude: float = Field(..., ge=-180.0, le=360.0, description="Observer longitude on Moon (-180 to 360)")
    altitude_km: float = Field(0.0, ge=-10.0, le=10.0, description="Altitude above 1737.4 km lunar sphere (km)")
    target: str = Field("Sun", description="Target celestial body: 'Sun' (10) or 'Earth' (399) or 'both'")
    start_epoch_iso: str = Field(..., description="Start UTC timestamp (ISO-8601, e.g. '2026-10-15T00:00:00Z')")
    stop_epoch_iso: Optional[str] = Field(None, description="Stop UTC timestamp (defaults to start + 3 days)")
    duration_days: Optional[float] = Field(3.0, ge=0.1, le=60.0, description="Duration in days if stop_epoch_iso omitted")
    step_hours: float = Field(2.0, ge=0.25, le=24.0, description="Time step in hours (default 2h)")


class HorizonsQueryResponse(BaseModel):
    """JPL Horizons ephemeris query output with validation residuals."""

    success: bool
    target: str
    observer: Dict[str, float]
    temporal_window: Dict[str, Any]
    points_count: int
    points: List[Dict[str, Any]]
    source_attribution: str
    is_cached: bool
    query_duration_ms: float
    error_message: Optional[str] = None


class MoonTrekLayersResponse(BaseModel):
    """List of verified NASA Moon Trek OGC WMTS layers."""

    layers_count: int
    layers: List[Dict[str, Any]]
    supported_projections: List[str]
    documentation_url: str


class LROCCoverageResponse(BaseModel):
    """LROC NAC stereo DTM discovery and QuickMap deep link response."""

    latitude: float
    longitude: float
    is_covered: bool
    covering_dtms_count: int
    covering_dtms: List[Dict[str, Any]]
    nearest_dtm: Optional[Dict[str, Any]]
    distance_to_nearest_dtm_km: float
    best_resolution_m: Optional[float]
    quickmap_url: str
    lroc_archive_url: str
    optical_hazard_validation_supported: bool
    status_note: str
