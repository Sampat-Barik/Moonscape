"""Terrain analysis router endpoint."""

from fastapi import APIRouter, Query
from Backend.app.schemas.terrain import TerrainResponse
from Backend.app.services.terrain_service import terrain_service

router = APIRouter(prefix="", tags=["Terrain"])


@router.get("/terrain", response_model=TerrainResponse, summary="Query terrain parameters at a specific lunar coordinate and radius")
def get_terrain_at_point(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude in degrees (-90 to 90)"),
    lon: float = Query(..., ge=-180.0, le=360.0, description="Longitude in degrees (-180 to 360)"),
    radius_m: float = Query(50.0, ge=10.0, le=25000.0, description="Physical analysis radius in meters (default 50m)"),
) -> TerrainResponse:
    """Extracts elevation, slope, roughness, and relief summaries over requested physical radius."""
    return terrain_service.get_point_terrain(lat=lat, lon=lon, radius_m=radius_m)
