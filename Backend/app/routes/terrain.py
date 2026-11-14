"""Terrain analysis router endpoint."""

from fastapi import APIRouter, Query
from app.schemas.terrain import TerrainResponse
from app.services.terrain_service import terrain_service

router = APIRouter(prefix="", tags=["Terrain"])


@router.get("/terrain", response_model=TerrainResponse, summary="Query terrain parameters at a specific lunar coordinate")
def get_terrain_at_point(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude in degrees (-90 to 90)"),
    lon: float = Query(..., ge=-180.0, le=360.0, description="Longitude in degrees (-180 to 360)"),
) -> TerrainResponse:
    """Extracts elevation, Horn slope, roughness, and landing safety classification for coordinates."""
    return terrain_service.get_point_terrain(lat=lat, lon=lon)
