"""Schemas for Lunar South Pole map configuration and layer metadata."""

from typing import Any, Dict, List
from pydantic import BaseModel, Field


class MapLayerConfig(BaseModel):
    """Configuration for an individual raster or vector map layer."""

    id: str = Field(..., description="Unique layer identifier")
    name: str = Field(..., description="Human-readable layer name")
    type: str = Field(..., description="Layer type: 'raster', 'vector', 'tile', or 'geojson'")
    description: str = Field(..., description="Scientific description of dataset")
    unit: str = Field(..., description="Measurement unit (e.g., 'meters', 'degrees', '%')")
    color_scale: str = Field(..., description="Recommended color palette for rendering (e.g., 'viridis', 'plasma')")
    min_value: float = Field(..., description="Minimum valid value for colormap scaling")
    max_value: float = Field(..., description="Maximum valid value for colormap scaling")
    attribution: str = Field(..., description="NASA dataset attribution citation")


class MapConfigResponse(BaseModel):
    """Overall map viewport and GIS configuration response for frontend display."""

    projection: str = Field("Lunar Polar Stereographic", description="Active cartographic projection")
    epsg_code: str = Field("ESRI:104903", description="Spatial reference system identifier")
    central_meridian_deg: float = Field(0.0, description="Central meridian in degrees")
    latitude_of_origin_deg: float = Field(-90.0, description="Latitude of true scale / origin in degrees")
    reference_radius_m: float = Field(1_737_400.0, description="Lunar reference sphere radius in meters")
    default_center: List[float] = Field([-89.5, 0.0], description="Default center coordinates [lat, lon]")
    default_zoom: int = Field(5, description="Initial recommended zoom level")
    min_zoom: int = Field(1, description="Minimum allowable zoom level")
    max_zoom: int = Field(12, description="Maximum allowable zoom level")
    latitude_bounds: List[float] = Field([-90.0, -80.0], description="Geographic latitude range [min, max]")
    longitude_bounds: List[float] = Field([-180.0, 180.0], description="Geographic longitude range [min, max]")
    layers: List[MapLayerConfig] = Field(..., description="Available visualization layers")
    data_sources: List[Dict[str, Any]] = Field(..., description="Citation and PDS metadata for loaded datasets")
