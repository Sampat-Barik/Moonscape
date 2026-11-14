"""Tests for landing zone spatial analysis endpoint."""

from fastapi.testclient import TestClient


def test_analysis_run_success(client: TestClient) -> None:
    """Tests POST /api/analysis/run executes windowed spatial analysis over candidate landing zone."""
    payload = {
        "center_lat": -89.44,
        "center_lon": 222.50,
        "radius_meters": 2000.0,
        "max_acceptable_slope_deg": 10.0,
        "max_acceptable_roughness_m": 0.5,
    }
    response = client.post("/api/analysis/run", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["analysis_id"].startswith("ANL-")
    assert data["total_samples"] > 0
    assert data["valid_samples"] > 0
    assert data["elevation"]["mean_value"] is not None
    assert data["slope"]["mean_value"] is not None
    assert data["slope_distribution"]["ideal_pct"] >= 0.0
    assert 0.0 <= data["safe_touchdown_fraction_pct"] <= 100.0
    assert data["preliminary_feasibility"] in ["favorable", "marginal", "unfavorable", "insufficient_data"]
    assert "DISCLAIMER" in data["disclaimer"]


def test_analysis_run_invalid_radius(client: TestClient) -> None:
    """Tests POST /api/analysis/run with invalid radius (> 25km limit) fails with 422."""
    payload = {
        "center_lat": -89.44,
        "center_lon": 222.50,
        "radius_meters": 50000.0,
    }
    response = client.post("/api/analysis/run", json=payload)
    assert response.status_code == 422
