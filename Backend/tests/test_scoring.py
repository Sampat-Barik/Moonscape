"""Tests for multi-criteria suitability scoring endpoint."""

from fastapi.testclient import TestClient


def test_score_catalog_site(client: TestClient) -> None:
    """Tests POST /api/score for an existing catalog site."""
    payload = {
        "site_id": "shackleton_connecting_ridge",
        "weights": {
            "slope_weight": 0.40,
            "roughness_weight": 0.20,
            "illumination_weight": 0.20,
            "communication_weight": 0.10,
            "science_weight": 0.10,
        },
    }
    response = client.post("/api/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["site_id"] == "shackleton_connecting_ridge"
    assert 0.0 <= data["overall_suitability_score"] <= 100.0
    assert data["suitability_category"] in ["Optimal", "Nominal", "Marginal", "High Risk", "Unsuitable"]
    assert len(data["subscores"]) == 5
    assert len(data["key_advantages"]) > 0
    assert "DISCLAIMER" in data["disclaimer"]


def test_score_custom_measurements(client: TestClient) -> None:
    """Tests POST /api/score with ad-hoc user-provided scientific measurements."""
    payload = {
        "slope_deg": 3.2,
        "roughness_m": 0.25,
        "illumination_pct": 82.0,
        "earth_visibility_pct": 90.0,
        "science_value_rating": 85.0,
    }
    response = client.post("/api/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    # With very low slope and roughness and high illumination, score should be high
    assert data["overall_suitability_score"] >= 80.0
    assert data["suitability_category"] in ["Optimal", "Nominal"]


def test_score_critical_slope_penalty(client: TestClient) -> None:
    """Tests that a critical slope (> 15 deg) receives a slope subscore of 0."""
    payload = {
        "slope_deg": 22.0,
        "roughness_m": 0.3,
    }
    response = client.post("/api/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    slope_sub = next(s for s in data["subscores"] if s["criterion"] == "Topographic Slope")
    assert slope_sub["normalized_subscore"] == 0.0
    assert any("tip-over" in c.lower() for c in data["critical_concerns"])
