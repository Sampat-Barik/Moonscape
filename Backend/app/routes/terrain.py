"""Terrain analysis router endpoint."""

from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Query, HTTPException
from Backend.app.schemas.terrain import TerrainResponse
from Backend.app.services.terrain_service import terrain_service

router = APIRouter(prefix="", tags=["Terrain"])


class TerrainQueryRequest(BaseModel):
    """Input payload for POST /api/terrain query."""
    lat: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Latitude in degrees (-90 to 90)")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Alias for lat")
    lon: Optional[float] = Field(None, ge=-180.0, le=360.0, description="Longitude in degrees (-180 to 360)")
    longitude: Optional[float] = Field(None, ge=-180.0, le=360.0, description="Alias for lon")
    radius_m: Optional[float] = Field(50.0, ge=10.0, le=25000.0, description="Physical analysis radius in meters")
    radius_meters: Optional[float] = Field(None, ge=10.0, le=25000.0, description="Alias for radius_m")


@router.get("/terrain", response_model=TerrainResponse, summary="Query terrain parameters at a specific lunar coordinate and radius")
def get_terrain_at_point(
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Latitude in degrees (-90 to 90)"),
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Alias for lat"),
    lon: Optional[float] = Query(None, ge=-180.0, le=360.0, description="Longitude in degrees (-180 to 360)"),
    longitude: Optional[float] = Query(None, ge=-180.0, le=360.0, description="Alias for lon"),
    radius_m: Optional[float] = Query(50.0, ge=10.0, le=25000.0, description="Physical analysis radius in meters (default 50m)"),
    radius_meters: Optional[float] = Query(None, ge=10.0, le=25000.0, description="Alias for radius_m"),
) -> TerrainResponse:
    """Extracts elevation, slope, roughness, and relief summaries over requested physical radius."""
    effective_lat = lat if lat is not None else latitude
    effective_lon = lon if lon is not None else longitude
    effective_radius = radius_m if radius_m is not None else (radius_meters or 50.0)

    if effective_lat is None or effective_lon is None:
        raise HTTPException(
            status_code=422,
            detail="Field 'lat' (or 'latitude') and 'lon' (or 'longitude') are required."
        )
    return terrain_service.get_point_terrain(lat=effective_lat, lon=effective_lon, radius_m=effective_radius)


@router.post("/terrain", response_model=TerrainResponse, summary="Query terrain parameters at a specific lunar coordinate and radius (POST)")
def post_terrain_at_point(payload: TerrainQueryRequest) -> TerrainResponse:
    """Extracts elevation, slope, roughness, and relief summaries over requested physical radius via POST body."""
    lat = payload.lat if payload.lat is not None else payload.latitude
    lon = payload.lon if payload.lon is not None else payload.longitude
    radius = payload.radius_m if payload.radius_m is not None else (payload.radius_meters or 50.0)

    if lat is None or lon is None:
        raise HTTPException(
            status_code=400,
            detail="Both latitude and longitude are required in request body (e.g. {'lat': -89.44, 'lon': 222.50} or {'latitude': -89.44, 'longitude': 222.50})."
        )
    return terrain_service.get_point_terrain(lat=lat, lon=lon, radius_m=radius)
