"""Tests for terrain elevation, slope, and coordinate query endpoints."""

from fastapi.testclient import TestClient


def test_terrain_valid_south_pole_point(client: TestClient) -> None:
    """Tests GET /api/terrain with valid Shackleton Crater coordinates (-89.9°, 0.0°)."""
    response = client.get("/api/terrain?lat=-89.9&lon=0.0")
    assert response.status_code == 200
    data = response.json()

    assert data["is_valid_point"] is True
    assert data["elevation_m"] is not None
    assert data["slope_deg"] is not None
    assert data["slope_deg"] >= 0.0
    assert data["aspect_deg"] is not None
    assert data["roughness_m"] is not None
    assert data["landing_hazard_classification"] in ["safe", "marginal", "hazardous"]
    assert data["dataset_info"]["dataset_name"] == "NASA LRO LOLA (Lunar Orbiter Laser Altimeter)"


def test_terrain_out_of_polar_coverage(client: TestClient) -> None:
    """Tests GET /api/terrain with non-polar latitude returns is_valid_point=False without 500 error."""
    response = client.get("/api/terrain?lat=10.0&lon=0.0")
    assert response.status_code == 200
    data = response.json()

    assert data["is_valid_point"] is False
    assert data["elevation_m"] is None
    assert data["slope_deg"] is None
    assert "outside" in data["notes"].lower()


def test_terrain_invalid_latitude_validation(client: TestClient) -> None:
    """Tests GET /api/terrain with invalid latitude (> 90.0) fails Pydantic validation with 422."""
    response = client.get("/api/terrain?lat=105.0&lon=0.0")
    assert response.status_code == 422


def test_terrain_invalid_longitude_validation(client: TestClient) -> None:
    """Tests GET /api/terrain with invalid longitude (> 360.0) fails Pydantic validation with 422."""
    response = client.get("/api/terrain?lat=-85.0&lon=400.0")
    assert response.status_code == 422
