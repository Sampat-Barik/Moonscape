"""Schemas for point-specific terrain elevation and gradient queries."""

from typing import Optional
from pydantic import BaseModel, Field


class TerrainDatasetInfo(BaseModel):
    """Metadata describing the NASA dataset and scientific derivation methodology."""

    dataset_name: str
    product_id: str
    spatial_resolution_m: float
    vertical_uncertainty_m: float
    slope_method: str
    roughness_baseline_m: float
    citation: Optional[str] = None
    observation_count: Optional[int] = None
    slope_uncertainty_deg: Optional[float] = None
    effective_resolution_m: Optional[float] = None
    is_measured_data: bool = True


class TerrainResponse(BaseModel):
    """Terrain query response for a specific lunar coordinate."""

    latitude: float = Field(..., description="Query latitude in degrees (-90 to 90)")
    longitude: float = Field(..., description="Query longitude in degrees (-180 to 360)")
    is_valid_point: bool = Field(..., description="Whether coordinates fall within valid raster bounds")
    is_nodata: bool = Field(..., description="Whether query point corresponds to a nodata / shadow pixel")
    elevation_m: Optional[float] = Field(None, description="Elevation in meters relative to 1737.4 km lunar sphere")
    slope_deg: Optional[float] = Field(None, description="Calculated topographic slope in degrees (Horn 1981)")
    roughness_m: Optional[float] = Field(None, description="Surface roughness (RMS residual height deviation in meters)")
    aspect_deg: Optional[float] = Field(None, description="Azimuthal direction of steepest slope (0-360 deg clockwise from North)")
    solar_illumination_pct: Optional[float] = Field(None, description="Estimated annual solar illumination percentage")
    landing_hazard_classification: str = Field(..., description="Preliminary classification: 'safe', 'marginal', 'hazardous', or 'nodata'")
    dataset_info: TerrainDatasetInfo = Field(..., description="Provenance information of underlying measurements")
    source_tier: Optional[str] = Field(None, description="Active data tier (e.g. Tier 1 80m, Tier 2 5m)")
    uncertainty_elevation_m: Optional[float] = Field(None, description="Vertical elevation uncertainty standard error in meters")
    uncertainty_slope_deg: Optional[float] = Field(None, description="Slope uncertainty in degrees")
    notes: Optional[str] = Field(None, description="Additional scientific commentary or uncertainty caveat")
