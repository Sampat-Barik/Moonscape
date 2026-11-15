"""Schemas for point-specific terrain elevation and gradient queries."""

from typing import Any, Dict, Optional
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
    source_url: Optional[str] = None
    crs: Optional[str] = None
    reference_frame: Optional[str] = None
    quality_warnings: Optional[str] = None


class ElevationSummary(BaseModel):
    """Elevation metrics and spatial distribution within analysis radius."""

    point_m: Optional[float] = Field(None, description="Elevation at query coordinate (m)")
    min_m: Optional[float] = Field(None, description="Minimum elevation within radius (m)")
    max_m: Optional[float] = Field(None, description="Maximum elevation within radius (m)")
    mean_m: Optional[float] = Field(None, description="Mean elevation within radius (m)")
    variation_m: Optional[float] = Field(None, description="Elevation relief (max - min) in meters")
    std_dev_m: Optional[float] = Field(None, description="Elevation standard deviation in meters")
    units: str = "meters"


class SlopeSummary(BaseModel):
    """Slope statistics within analysis radius."""

    point_deg: Optional[float] = Field(None, description="Slope at query coordinate (degrees)")
    min_deg: Optional[float] = Field(None, description="Minimum slope within radius (degrees)")
    max_deg: Optional[float] = Field(None, description="Maximum slope within radius (degrees)")
    mean_deg: Optional[float] = Field(None, description="Mean slope within radius (degrees)")
    p95_deg: Optional[float] = Field(None, description="95th percentile slope within radius (degrees)")
    std_dev_deg: Optional[float] = Field(None, description="Slope standard deviation (degrees)")
    method: str = Field(..., description="Method used (NASA precomputed raster or Horn 1981 gradient)")
    units: str = "degrees"
    ideal_pct: Optional[float] = Field(None, description="Percentage of area with slope <= 5 deg")
    acceptable_pct: Optional[float] = Field(None, description="Percentage of area with slope 5-10 deg")
    marginal_pct: Optional[float] = Field(None, description="Percentage of area with slope 10-15 deg")
    critical_hazardous_pct: Optional[float] = Field(None, description="Percentage of area with slope > 15 deg")


class RoughnessSummary(BaseModel):
    """Surface roughness metrics evaluated across moving neighborhood baseline."""

    point_m: Optional[float] = Field(None, description="RMS roughness at query coordinate (m)")
    min_m: Optional[float] = Field(None, description="Minimum roughness within radius (m)")
    max_m: Optional[float] = Field(None, description="Maximum roughness within radius (m)")
    mean_m: Optional[float] = Field(None, description="Mean roughness within radius (m)")
    std_dev_m: Optional[float] = Field(None, description="Roughness standard deviation (m)")
    method: str = Field(..., description="Method used (e.g. RMS residual height deviation)")
    kernel_size: int = Field(3, description="Moving window kernel dimension (e.g. 3x3)")
    baseline_m: float = Field(..., description="Physical spatial baseline in meters = kernel_size * dx")
    units: str = "meters"
    multi_baseline: Optional[Dict[str, Any]] = Field(
        None, description="Scale-dependent RMS roughness evaluated across multiple physical baselines (Barker et al. 2016)"
    )


class TerrainResponse(BaseModel):
    """Terrain query response for a specific lunar coordinate and physical radius."""

    latitude: float = Field(..., description="Query latitude in degrees (-90 to 90)")
    longitude: float = Field(..., description="Query longitude in degrees (-180 to 360)")
    is_valid_point: bool = Field(..., description="Whether coordinates fall within valid raster bounds")
    is_nodata: bool = Field(..., description="Whether query point corresponds to a nodata / shadow pixel")
    elevation_m: Optional[float] = Field(None, description="Elevation in meters relative to 1737.4 km lunar sphere")
    slope_deg: Optional[float] = Field(None, description="Calculated topographic slope in degrees (Horn 1981 or NASA product)")
    roughness_m: Optional[float] = Field(None, description="Surface roughness (RMS residual height deviation in meters)")
    aspect_deg: Optional[float] = Field(None, description="Azimuthal direction of steepest slope (0-360 deg clockwise from North)")
    solar_illumination_pct: Optional[float] = Field(None, description="Estimated annual solar illumination percentage")
    landing_hazard_classification: str = Field(..., description="Preliminary classification: 'safe', 'marginal', 'hazardous', or 'nodata'")
    dataset_info: TerrainDatasetInfo = Field(..., description="Provenance information of underlying measurements")
    source_tier: Optional[str] = Field(None, description="Active data tier (e.g. Tier 1 80m, Tier 2 5m)")
    uncertainty_elevation_m: Optional[float] = Field(None, description="Vertical elevation uncertainty standard error in meters")
    uncertainty_slope_deg: Optional[float] = Field(None, description="Slope uncertainty in degrees")
    notes: Optional[str] = Field(None, description="Additional scientific commentary or uncertainty caveat")

    # Phase 3 Physical Spatial Window Summaries
    analysis_radius_m: Optional[float] = Field(None, description="Physical analysis radius in meters")
    elevation_summary: Optional[ElevationSummary] = Field(None, description="Detailed elevation distribution in radius")
    slope_summary: Optional[SlopeSummary] = Field(None, description="Detailed slope statistics in radius")
    roughness_summary: Optional[RoughnessSummary] = Field(None, description="Detailed roughness statistics in radius")
    total_pixels_in_disc: Optional[int] = Field(None, description="Total raster cells within physical radius disc")
    valid_pixels_in_disc: Optional[int] = Field(None, description="Valid non-nodata cells within physical radius disc")
    nodata_pixels_in_disc: Optional[int] = Field(None, description="Nodata cells within physical radius disc")


class TerrainMeshRequest(BaseModel):
    """Input payload for extracting downsampled 3D elevation and slope meshes."""

    lat: Optional[float] = Field(None, ge=-90.0, le=-70.0, description="Latitude in degrees (-90 to -70)")
    latitude: Optional[float] = Field(None, ge=-90.0, le=-70.0, description="Alias for lat")
    lon: Optional[float] = Field(None, ge=-180.0, le=360.0, description="Longitude in degrees (-180 to 360)")
    longitude: Optional[float] = Field(None, ge=-180.0, le=360.0, description="Alias for lon")
    radius_m: Optional[float] = Field(500.0, ge=20.0, le=25000.0, description="Physical radius in meters")
    radius_meters: Optional[float] = Field(None, ge=20.0, le=25000.0, description="Alias for radius_m")
    grid_size: Optional[int] = Field(64, ge=16, le=128, description="Grid dimension (N x N elevation samples, default 64)")


class TerrainMeshResponse(BaseModel):
    """3D elevation grid, slope gradient, and relief metadata for client-side rendering."""

    status: str = "ready"
    latitude: float
    longitude: float
    radius_m: float
    grid_size: int
    resolution_m: float
    center_x_polar_m: float
    center_y_polar_m: float
    min_elevation_m: float
    max_elevation_m: float
    mean_elevation_m: float
    relief_m: float
    elevation_grid: list[list[float]]
    slope_grid: list[list[float]]
    dataset_name: str
    product_id: str
    crs: str
    disclaimer: str
    source_tier: Optional[str] = Field(None, description="Active DEM source tier (e.g. Tier 2 5m, Tier 1 80m, Tier 0 sample)")
    has_high_res: Optional[bool] = Field(False, description="Whether authentic 5m regional high-resolution DEM is active")
    coverage_level: Optional[str] = Field("core", description="Exploration coverage classification ('core', 'extended', 'context')")
