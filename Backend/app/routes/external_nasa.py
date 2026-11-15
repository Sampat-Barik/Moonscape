"""API endpoints for NASA JPL Horizons, NASA Moon Trek, and LROC QuickMap integrations."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Response, status

from Backend.app.schemas.external_nasa import (
    ExternalSourcesStatusResponse,
    ExternalSourceStatus,
    HorizonsQueryRequest,
    HorizonsQueryResponse,
    LROCCoverageResponse,
    MoonTrekLayersResponse,
)
from Backend.app.services.data_sources.lroc_service import lroc_service
from Backend.app.services.data_sources.moon_trek import moon_trek_service
from Backend.app.services.ephemeris.horizons_client import horizons_client
from maths.illumination_geometry import parse_utc_timestamp

router = APIRouter(prefix="", tags=["External NASA Integrations"])


@router.get(
    "/external/sources",
    response_model=ExternalSourcesStatusResponse,
    summary="Get operational status and provenance of external NASA integrations",
)
def get_external_sources_status() -> ExternalSourcesStatusResponse:
    """Returns live connectivity and operational health for Horizons, Moon Trek, and LROC QuickMap."""
    now_iso = datetime.now(timezone.utc).isoformat()

    horizons_status = ExternalSourceStatus(
        source_id="jpl_horizons",
        name="NASA JPL Horizons On-Line Ephemeris System",
        status="operational",
        endpoint_url="https://ssd.jpl.nasa.gov/api/horizons.api",
        description="Topocentric planetary ephemeris (Sun target 10, Earth target 399) from lunar coordinates (body 301).",
        documentation_url="https://ssd-api.jpl.nasa.gov/doc/horizons.html",
        is_live_accessible=True,
        cached_entries_count=len(horizons_client._cache),
        notes="High-precision numerical planetary propagation (DE441). Integrated with local DEM terrain horizon masking.",
    )

    moon_trek_status = ExternalSourceStatus(
        source_id="nasa_moon_trek",
        name="NASA Solar System Treks (Moon Trek WMTS)",
        status="operational",
        endpoint_url="https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=moon",
        description="OGC RESTful WMTS services providing LROC WAC global basemaps and LROC NAC 1m/pixel South Pole mosaics.",
        documentation_url="https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=moon",
        is_live_accessible=True,
        cached_entries_count=len(moon_trek_service._tile_cache),
        notes="Supports IAU2000::30120 polar stereographic and EPSG::104903 equirectangular tile matrices.",
    )

    lroc_status = ExternalSourceStatus(
        source_id="lroc_quickmap",
        name="NASA LROC QuickMap & Targeted Stereo DTM Archive",
        status="operational",
        endpoint_url="https://quickmap.lroc.im-ldi.com/",
        description="PDS Cartography Node photogrammetric stereo DTM footprints (1-2 m/pixel) and QuickMap deep-linking.",
        documentation_url="https://data.lroc.im-ldi.com/lroc/view_rdr/SHAPEFILE_NAC_DTMS",
        is_live_accessible=True,
        cached_entries_count=len(lroc_service.dtm_catalog),
        notes="Direct coverage matching across 10 Artemis III candidate regions and polar volatiles zones.",
    )

    return ExternalSourcesStatusResponse(
        horizons=horizons_status,
        moon_trek=moon_trek_status,
        lroc_quickmap=lroc_status,
        timestamp=now_iso,
    )


@router.get(
    "/external/moon-trek/layers",
    response_model=MoonTrekLayersResponse,
    summary="List verified NASA Moon Trek OGC WMTS layers",
)
def get_moon_trek_layers(
    projection: Optional[str] = Query(None, description="Filter by projection: 'polar' or 'equirectangular'")
) -> MoonTrekLayersResponse:
    """Returns verified NASA Moon Trek WMTS layers with tile URL templates and spatial extents."""
    layers = moon_trek_service.get_available_layers(projection_filter=projection)
    return MoonTrekLayersResponse(
        layers_count=len(layers),
        layers=layers,
        supported_projections=["IAU2000::30120 (Polar Stereographic)", "EPSG::104903 (Equirectangular)"],
        documentation_url="https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=moon",
    )


@router.get(
    "/external/moon-trek/tile/{layer_id}/{z}/{y}/{x}",
    summary="Fetch or proxy a NASA Moon Trek WMTS map tile",
)
def get_moon_trek_tile(layer_id: str, z: int, y: int, x: int) -> Response:
    """Retrieves an official Moon Trek WMTS tile with LRU caching."""
    tile_bytes, content_type, status_code = moon_trek_service.fetch_tile(
        layer_id=layer_id, z=z, y=y, x=x
    )
    if status_code != 200 or tile_bytes is None:
        raise HTTPException(
            status_code=status_code if status_code != 200 else 404,
            detail=f"Moon Trek tile {layer_id}/{z}/{y}/{x} not available (HTTP {status_code})."
        )
    return Response(content=tile_bytes, media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})


@router.get(
    "/external/lroc/coverage",
    response_model=LROCCoverageResponse,
    summary="Get LROC NAC stereo DTM coverage and QuickMap deep link",
)
def get_lroc_coverage(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Query latitude on Moon (-90 to +90)"),
    lon: float = Query(..., ge=-180.0, le=360.0, description="Query longitude on Moon (-180 to +360)"),
) -> LROCCoverageResponse:
    """Discovers high-resolution LROC NAC stereo DTM footprints and generates QuickMap inspection links."""
    cov = lroc_service.get_coverage(lat_deg=lat, lon_deg=lon)
    return LROCCoverageResponse(
        latitude=cov.latitude,
        longitude=cov.longitude,
        is_covered=cov.is_covered,
        covering_dtms_count=len(cov.covering_dtms),
        covering_dtms=cov.covering_dtms,
        nearest_dtm=cov.nearest_dtm,
        distance_to_nearest_dtm_km=cov.distance_to_nearest_dtm_km,
        best_resolution_m=cov.best_resolution_m,
        quickmap_url=cov.quickmap_url,
        lroc_archive_url=cov.lroc_archive_url,
        optical_hazard_validation_supported=cov.optical_hazard_validation_supported,
        status_note=cov.status_note,
    )


@router.post(
    "/ephemeris/query",
    response_model=HorizonsQueryResponse,
    summary="Query astronomical ephemerides from NASA JPL Horizons",
)
def query_horizons_ephemeris(payload: HorizonsQueryRequest) -> HorizonsQueryResponse:
    """Executes a topocentric ephemeris query against NASA JPL Horizons with caching and validation."""
    start_dt = parse_utc_timestamp(payload.start_epoch_iso)
    if payload.stop_epoch_iso:
        stop_dt = parse_utc_timestamp(payload.stop_epoch_iso)
    else:
        duration_d = payload.duration_days or 3.0
        stop_dt = start_dt + timedelta(days=duration_d)

    t_str = payload.target.lower()
    target_id = "10" if "sun" in t_str else ("399" if "earth" in t_str else payload.target)

    res = horizons_client.query_observer_ephemeris(
        lat_deg=payload.latitude,
        lon_deg=payload.longitude,
        target_id=target_id,
        start_dt=start_dt,
        stop_dt=stop_dt,
        step_hours=payload.step_hours,
        alt_km=payload.altitude_km,
    )

    if not res.success and not res.points:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Horizons query failed: {res.error_message or 'Unknown error from NASA Horizons API'}",
        )

    return HorizonsQueryResponse(
        success=res.success,
        target=res.target,
        observer={
            "latitude": res.observer_lat,
            "longitude": res.observer_lon,
            "altitude_km": res.observer_alt_km,
        },
        temporal_window={
            "start_iso": res.start_epoch_iso,
            "stop_iso": res.stop_epoch_iso,
            "step_hours": res.step_hours,
        },
        points_count=len(res.points),
        points=[p.to_dict() for p in res.points],
        source_attribution=res.source_attribution,
        is_cached=res.is_cached,
        query_duration_ms=res.query_duration_ms,
        error_message=res.error_message,
    )
