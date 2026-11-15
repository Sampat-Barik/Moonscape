"""Integration test for terrain endpoint with real NASA data hierarchy."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_terrain_site01_shackleton_connecting_ridge():
    """Verify that coordinates within Site 01 return authentic 5m NASA measurements."""
    # Connecting Ridge center coordinate
    resp = client.get("/api/terrain?lat=-89.46&lon=222.0")
    assert resp.status_code == 200
    data = resp.json()

    assert data["is_valid_point"] is True
    assert data["is_nodata"] is False
    assert data["elevation_m"] is not None
    # Shackleton ridge is roughly 1900m above 1737.4 km reference sphere
    assert 1800.0 < data["elevation_m"] < 2100.0
    assert data["slope_deg"] is not None
    assert 0.0 <= data["slope_deg"] <= 90.0
    assert data["source_tier"] == "Tier 2 (High-Resolution 5m Candidate Region)"
    assert data["dataset_info"]["spatial_resolution_m"] == 5.0
    assert "Barker" in data["dataset_info"]["citation"]
    assert data["landing_hazard_classification"] in ["safe", "marginal", "hazardous"]


def test_terrain_out_of_bounds():
    """Verify that points outside South Pole (-90 to -70) are rejected cleanly."""
    resp = client.get("/api/terrain?lat=-69.0&lon=0.0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid_point"] is False
    assert "outside" in data["notes"].lower()
