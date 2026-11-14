"""Cartographic and GIS map configuration endpoints."""

from fastapi import APIRouter
from app.core.constants import (
    LOLA_DATASET_NAME,
    LOLA_PRODUCT_ID,
    PROJECTION_EPSG,
    PROJECTION_NAME,
)
from app.schemas.map import MapConfigResponse, MapLayerConfig

router = APIRouter(prefix="", tags=["Map"])


@router.get("/map/config", response_model=MapConfigResponse, summary="Get frontend map GIS configuration")
def get_map_config() -> MapConfigResponse:
    """Returns projection parameters, recommended zoom levels, spatial bounds, and visualization layers for frontend maps."""
    layers = [
        MapLayerConfig(
            id="lola_elevation",
            name="NASA LOLA Elevation",
            type="raster",
            description="LRO Lunar Orbiter Laser Altimeter digital elevation model in meters.",
            unit="meters",
            color_scale="viridis",
            min_value=-4500.0,
            max_value=3500.0,
            attribution="NASA / GSFC / LOLA Science Team",
        ),
        MapLayerConfig(
            id="lola_slope",
            name="Derived Topographic Slope",
            type="raster",
            description="Surface gradient computed using Horn (1981) 3x3 finite differences.",
            unit="degrees",
            color_scale="plasma",
            min_value=0.0,
            max_value=30.0,
            attribution="NASA LOLA Derived Product (Horn 1981)",
        ),
        MapLayerConfig(
            id="solar_illumination",
            name="Annual Solar Illumination",
            type="raster",
            description="Mean solar illumination percentage over full 18.6-year lunar precession cycle.",
            unit="percent",
            color_scale="cividis",
            min_value=0.0,
            max_value=100.0,
            attribution="NASA LROC / LOLA Polar Lighting Model",
        ),
        MapLayerConfig(
            id="hazard_overlay",
            name="Landing Touchdown Hazards",
            type="vector",
            description="Detected impact crater rims, boulder clutter zones, and critical slopes (>15°).",
            unit="risk_tier",
            color_scale="magma",
            min_value=0.0,
            max_value=1.0,
            attribution="Moonscape Hazard Detection Pipeline",
        ),
        MapLayerConfig(
            id="candidate_sites",
            name="Artemis Candidate Sites",
            type="geojson",
            description="NASA Artemis III candidate South Pole landing zones and priority tiers.",
            unit="category",
            color_scale="category10",
            min_value=0.0,
            max_value=1.0,
            attribution="NASA Artemis III Site Selection Team",
        ),
    ]

    data_sources = [
        {
            "name": LOLA_DATASET_NAME,
            "product": LOLA_PRODUCT_ID,
            "repository": "NASA Planetary Data System (PDS) Geosciences Node",
            "doi": "10.17189/1520646",
        },
        {
            "name": "NASA Lunar Reconnaissance Orbiter Camera (LROC)",
            "product": "South Pole NAC Digital Terrain Models & Mosaics",
            "repository": "Arizona State University / NASA PDS",
            "doi": "10.17189/1520645",
        },
    ]

    return MapConfigResponse(
        projection=PROJECTION_NAME,
        epsg_code=PROJECTION_EPSG,
        central_meridian_deg=0.0,
        latitude_of_origin_deg=-90.0,
        reference_radius_m=1_737_400.0,
        default_center=[-89.5, 0.0],
        default_zoom=5,
        min_zoom=1,
        max_zoom=12,
        latitude_bounds=[-90.0, -80.0],
        longitude_bounds=[-180.0, 180.0],
        layers=layers,
        data_sources=data_sources,
    )
