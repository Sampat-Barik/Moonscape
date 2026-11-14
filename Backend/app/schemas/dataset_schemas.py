"""Schemas for NASA dataset catalog, download tracking, and spatial coverage queries."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DatasetItem(BaseModel):
    """Specification of a single registered NASA lunar dataset."""

    id: str
    name: str
    source_provider: str
    product_id: str
    filename: str
    size_mb: float
    spatial_resolution_m: float
    units: str
    tier: str
    byte_range_supported: bool
    status: str
    validation_detail: Optional[str] = None
    is_installed: bool
    bounds: Dict[str, float]


class DatasetProfile(BaseModel):
    """Preset download bundle."""

    name: str
    description: str
    total_size_mb: float
    datasets: List[str]


class DatasetCatalogResponse(BaseModel):
    """Full dataset inventory response including preset profiles."""

    total_datasets: int
    installed_count: int
    default_profile: str
    profiles: Dict[str, DatasetProfile]
    datasets: List[DatasetItem]


class CoverageLayer(BaseModel):
    """Layer coverage detail at a specific coordinate."""

    source_id: str
    name: str
    tier: str
    covers: bool
    is_installed: bool
    resolution_m: float
    status: Optional[str] = None
    detail: Optional[str] = None
    measurement_type: Optional[str] = None
    covering_candidate_sites: Optional[List[str]] = None
    covering_nac_dtms: Optional[List[str]] = None


class DataCoverageResponse(BaseModel):
    """Spatial coverage response at a given coordinate."""

    valid_coordinate: bool
    latitude: float
    longitude: float
    in_south_pole_zone: bool
    best_installed_resolution_m: Optional[float] = None
    total_covering_sources: int
    installed_covering_sources: int
    layers: List[CoverageLayer]


class DownloadTaskResponse(BaseModel):
    """Download task status and streaming progress."""

    task_id: str
    dataset_id: str
    filename: str
    status: str
    bytes_downloaded: int
    total_bytes: int
    progress_pct: float
    speed_mbps: float
    error_message: Optional[str] = None
