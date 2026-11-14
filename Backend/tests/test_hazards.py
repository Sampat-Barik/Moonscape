"""Tests for hazard prediction and surface risk mapping endpoint."""

from fastapi.testclient import TestClient


def test_hazards_predict_success(client: TestClient) -> None:
    """Tests POST /api/hazards/predict returns crater, boulder, and slope hazards."""
    payload = {
        "center_lat": -89.90,
        "center_lon": 0.0,
        "radius_meters": 3000.0,
        "min_crater_diameter_m": 5.0,
        "boulder_detection_sensitivity": 0.8,
    }
    response = client.post("/api/hazards/predict", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["hazard_assessment_id"].startswith("HAZ-")
    assert data["overall_hazard_level"] in ["low", "moderate", "high", "critical"]
    assert "model_metadata" in data
    assert "evaluation_caveat" in data["model_metadata"]
    assert "DISCLAIMER" in data["disclaimer"]
    assert isinstance(data["hazards"], list)


def test_hazards_predict_invalid_coordinates(client: TestClient) -> None:
    """Tests POST /api/hazards/predict with non-south-pole latitude fails with 422."""
    payload = {
        "center_lat": -50.0,
        "center_lon": 0.0,
    }
    response = client.post("/api/hazards/predict", json=payload)
    assert response.status_code == 422
