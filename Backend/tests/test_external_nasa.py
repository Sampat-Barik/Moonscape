"""Tests for NASA JPL Horizons, Moon Trek, and LROC QuickMap Integrations."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from Backend.app.services.ephemeris.horizons_client import HorizonsClient, HorizonsEphemerisPoint, HorizonsQueryResult
from Backend.app.services.data_sources.moon_trek import MoonTrekService
from Backend.app.services.data_sources.lroc_service import LROCService


def test_horizons_client_parsing():
    """Validates JPL Horizons ASCII response block parsing."""
    client = HorizonsClient()
    sample_block = """
 2026-Nov-15 00:00     m  251.9213   1.3824  0.989123456789  0.01234
 2026-Nov-15 02:00     m  254.5120   1.4110  0.989123556789  0.01235
"""
    points = client._parse_horizons_block(sample_block, target_name="Sun", target_id="10")
    assert len(points) == 2
    assert points[0].target == "Sun"
    assert points[0].target_id == "10"
    assert abs(points[0].azimuth_deg - 251.9213) < 1e-4
    assert abs(points[0].elevation_deg - 1.3824) < 1e-4
    assert points[0].distance_au is not None
    assert points[0].apparent_coordinates is True
    assert points[0].ref_body == "Moon (301)"


def test_horizons_client_caching():
    """Validates LRU caching and retrieval efficiency."""
    client = HorizonsClient()
    start_dt = datetime(2026, 11, 15, 0, 0, tzinfo=timezone.utc)
    stop_dt = datetime(2026, 11, 15, 4, 0, tzinfo=timezone.utc)
    cache_key = "10:-89.4400:222.5000:0.00:2026-11-15 00:00:2026-11-15 04:00:2 h"
    
    fake_point = HorizonsEphemerisPoint(
        epoch_iso="2026-11-15T00:00:00Z",
        target="Sun",
        target_id="10",
        azimuth_deg=251.9,
        elevation_deg=1.38,
        distance_au=0.989,
        distance_km=147950000.0,
        range_rate_km_s=0.01,
        apparent_coordinates=True,
        ref_body="Moon (301)",
    )
    fake_result = HorizonsQueryResult(
        success=True,
        target="Sun",
        target_id="10",
        observer_lat=-89.44,
        observer_lon=222.50,
        observer_alt_km=0.0,
        start_epoch_iso="2026-11-15T00:00:00Z",
        stop_epoch_iso="2026-11-15T04:00:00Z",
        step_hours=2.0,
        points=[fake_point],
        source_attribution="NASA JPL Solar System Dynamics (Horizons API DE441)",
        is_cached=False,
    )
    import time
    with client._lock:
        client._cache[cache_key] = (time.time(), fake_result)

    res = client.query_observer_ephemeris(
        lat_deg=-89.44,
        lon_deg=222.50,
        target_id="10",
        start_dt=start_dt,
        stop_dt=stop_dt,
        step_hours=2.0,
        alt_km=0.0,
    )
    assert res.is_cached is True
    assert res.success is True
    assert len(res.points) == 1
    assert abs(res.points[0].azimuth_deg - 251.9) < 0.1


def test_moon_trek_service_catalog():
    """Validates NASA Moon Trek layer metadata and WMTS URL synthesis."""
    service = MoonTrekService()
    layers = service.get_available_layers()
    assert len(layers) >= 3

    wac_layer = next((l for l in layers if l["id"] == "trek_wac_global_mosaic"), None)
    assert wac_layer is not None
    assert wac_layer["resolution_m"] == 100.0
    assert wac_layer["projection_type"] == "equirectangular"

    nac_layer = next((l for l in layers if l["id"] == "trek_nac_south_pole_mosaic"), None)
    assert nac_layer is not None
    assert nac_layer["resolution_m"] == 1.0
    assert nac_layer["projection_type"] == "polar"

    layer = service.get_layer_by_id("trek_wac_global_mosaic")
    assert layer is not None
    url = layer.tile_url_template.format(z=0, y=0, x=0)
    assert "default028mm/0/0/0.jpg" in url


def test_lroc_service_coverage_and_quickmap():
    """Validates LROC NAC stereo DTM coverage check and QuickMap URL generation."""
    service = LROCService()
    # Shackleton / Connecting Ridge region
    cov = service.get_coverage(lat_deg=-89.44, lon_deg=222.50)
    assert cov.is_covered is True
    assert len(cov.covering_dtms) >= 1
    assert "quickmap.lroc.im-ldi.com" in cov.quickmap_url
    assert "proj=southpole" in cov.quickmap_url
    assert cov.optical_hazard_validation_supported is True


def test_external_sources_status_endpoint(client: TestClient):
    """GET /api/external/sources validates operational status of all 3 integrations."""
    resp = client.get("/api/external/sources")
    assert resp.status_code == 200
    data = resp.json()
    assert "horizons" in data
    assert "moon_trek" in data
    assert "lroc_quickmap" in data
    assert data["horizons"]["status"] == "operational"
    assert data["moon_trek"]["status"] == "operational"
    assert data["lroc_quickmap"]["status"] == "operational"


def test_moon_trek_layers_endpoint(client: TestClient):
    """GET /api/external/moon-trek/layers returns verified NASA WMTS layers."""
    resp = client.get("/api/external/moon-trek/layers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["layers_count"] >= 3
    layer_ids = [l["id"] for l in data["layers"]]
    assert "trek_wac_global_mosaic" in layer_ids
    assert "trek_nac_south_pole_mosaic" in layer_ids


def test_lroc_coverage_endpoint(client: TestClient):
    """GET /api/external/lroc/coverage returns coverage and QuickMap deep link."""
    resp = client.get("/api/external/lroc/coverage?lat=-89.44&lon=222.50")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_covered"] is True
    assert "quickmap.lroc.im-ldi.com" in data["quickmap_url"]
    assert data["optical_hazard_validation_supported"] is True


def test_simulation_with_horizons_ephemeris(client: TestClient):
    """POST /api/simulation/visibility integrates Horizons ephemeris with DEM terrain masking."""
    payload = {
        "lat": -89.44,
        "lon": 222.50,
        "start_epoch_iso": "2026-11-15T00:00:00Z",
        "duration_days": 1.0,
        "step_hours": 2.0,
        "ephemeris_source": "horizons",
    }
    resp = client.post("/api/simulation/visibility", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_steps"] > 0
    assert "NASA JPL Horizons" in data["ephemeris_provider"]
    assert len(data["time_series"]) == data["total_steps"]
    step0 = data["time_series"][0]
    assert "solar_elevation_deg" in step0
    assert "earth_elevation_deg" in step0
    assert "horizon_elevation_sun_deg" in step0
