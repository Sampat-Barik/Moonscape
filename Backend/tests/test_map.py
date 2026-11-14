"""Tests for map configuration endpoint."""

from fastapi.testclient import TestClient


def test_map_config(client: TestClient) -> None:
    """Tests GET /api/map/config provides valid projection and layer definitions."""
    response = client.get("/api/map/config")
    assert response.status_code == 200
    data = response.json()

    assert data["projection"] == "Lunar Polar Stereographic"
    assert data["epsg_code"] == "ESRI:104903"
    assert data["central_meridian_deg"] == 0.0
    assert data["latitude_of_origin_deg"] == -90.0
    assert len(data["layers"]) >= 4

    # Verify key layer IDs
    layer_ids = [layer["id"] for layer in data["layers"]]
    assert "lola_elevation" in layer_ids
    assert "lola_slope" in layer_ids
    assert "solar_illumination" in layer_ids
    assert "hazard_overlay" in layer_ids
