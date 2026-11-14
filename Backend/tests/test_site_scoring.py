"""Unit and integration tests for Lunar Landing-Site Suitability Engine (Phase 6).

Tests:
1. Ideal synthetic terrain inputs (100% score, Higher preliminary suitability)
2. Poor synthetic terrain inputs (Critical slope penalty, Lower preliminary suitability)
3. Missing slope safety-gate (returns Insufficient data, does NOT score as zero)
4. Missing hazard factors (gracefully handled, explicit missing factors, coverage tracked)
5. All factors unavailable (returns null score, 0% coverage, Insufficient data)
6. Boundary threshold curves (slope, roughness, illumination mathematical steps)
7. Weight configuration customization and dynamic re-weighting
8. Repeatability (strictly deterministic scoring output)
9. Site comparison consistency and criteria versioning
10. Integration into POST /api/analysis/run
"""

import pytest
from fastapi.testclient import TestClient

from app.schemas.scoring import ScoreRequest, ScoringWeights
from app.services.site_scoring import CRITERIA_VERSION, site_scoring_engine
from maths.scoring import (
    compute_suitability_with_coverage,
    evaluate_crater_hazard_score,
    evaluate_elevation_score,
    evaluate_illumination_score,
    evaluate_rock_hazard_score,
    evaluate_roughness_score,
    evaluate_slope_score,
)


def test_scoring_ideal_synthetic_terrain(client: TestClient) -> None:
    """Tests ideal synthetic terrain inputs yield 100/100 score and Higher preliminary suitability."""
    payload = {
        "slope_deg": 2.0,  # <= 5.0 deg -> 100
        "roughness_m": 0.15,  # <= 0.25 m -> 100
        "illumination_pct": 92.0,  # >= 80% -> 100
        "crater_count": 0,  # 0 -> 100
        "rock_count": 0,  # 0 -> 100
        "elevation_m": 1200.0,  # >= 1000m -> 100
    }
    response = client.post("/api/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["overall_suitability_score"] == 100.0
    assert data["suitability_category"] == "Higher preliminary suitability"
    assert data["score_coverage_pct"] == 100.0
    assert data["missing_factors"] == []
    assert len(data["key_advantages"]) > 0
    assert len(data["critical_concerns"]) == 0
    assert data["criteria_version"] == CRITERIA_VERSION


def test_scoring_poor_synthetic_terrain(client: TestClient) -> None:
    """Tests adverse synthetic inputs yield low score and Lower preliminary suitability."""
    payload = {
        "slope_deg": 18.5,  # > 15 deg tip-over threshold -> 0.0
        "roughness_m": 1.6,  # > 1.2m -> 0.0
        "illumination_pct": 15.0,  # low
        "crater_count": 8,  # > 5
        "rock_count": 12,  # > 5
        "elevation_m": -3200.0,  # deep depression
    }
    response = client.post("/api/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["overall_suitability_score"] is not None
    assert data["overall_suitability_score"] < 25.0
    assert data["suitability_category"] == "Lower preliminary suitability"
    assert any("tip-over" in w.lower() for w in data["warnings"])
    assert len(data["critical_concerns"]) > 0


def test_scoring_missing_slope_safety_gate(client: TestClient) -> None:
    """SCIENTIFIC INTEGRITY: Missing slope must report Insufficient data, NEVER treat as zero."""
    payload = {
        "roughness_m": 0.20,
        "illumination_pct": 85.0,
        "elevation_m": 1500.0,
        # slope_deg is omitted
    }
    response = client.post("/api/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Overall score MUST be null because slope is safety-critical
    assert data["overall_suitability_score"] is None
    assert data["suitability_category"] == "Insufficient data"
    assert "slope" in data["missing_factors"]

    # Slope subscore must be null, not 0.0
    slope_sub = next(s for s in data["subscores"] if s["criterion"] == "Topographic Slope")
    assert slope_sub["status"] == "missing"
    assert slope_sub["normalized_subscore"] is None

    # Warning must explain why
    assert any("slope is a safety-critical" in w.lower() for w in data["warnings"])


def test_scoring_missing_hazards(client: TestClient) -> None:
    """Tests missing hazard factors are tracked with explicit coverage without silent weight redistribution."""
    payload = {
        "slope_deg": 3.5,
        "roughness_m": 0.30,
        "illumination_pct": 78.0,
        "elevation_m": 500.0,
        # crater_count and rock_count are omitted
    }
    response = client.post("/api/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Slope is present and coverage (0.80) >= 0.50 -> valid score computed
    assert data["overall_suitability_score"] is not None
    assert data["overall_suitability_score"] >= 75.0
    assert "crater_hazard" in data["missing_factors"]
    assert "rock_hazard" in data["missing_factors"]
    assert data["score_coverage_pct"] == 80.0  # 1.0 - 0.10 - 0.10 = 0.80

    crater_sub = next(s for s in data["subscores"] if s["criterion"] == "Crater Hazards")
    assert crater_sub["status"] == "missing"
    assert crater_sub["normalized_subscore"] is None
    assert crater_sub["weighted_contribution"] is None


def test_scoring_all_factors_unavailable(client: TestClient) -> None:
    """Tests empty payload returns null score, 0% coverage, and Insufficient data."""
    response = client.post("/api/score", json={})
    assert response.status_code == 200
    data = response.json()

    assert data["overall_suitability_score"] is None
    assert data["suitability_category"] == "Insufficient data"
    assert data["score_coverage_pct"] == 0.0
    assert data["evaluated_factors_count"] == 0
    assert data["total_factors_count"] == 6


def test_scoring_boundary_thresholds() -> None:
    """Verifies mathematical piece-wise boundary steps for key factor curves."""
    # 1. Topographic Slope
    assert evaluate_slope_score(0.0) == 100.0
    assert evaluate_slope_score(5.0) == 100.0
    assert evaluate_slope_score(10.0) == 70.0
    assert evaluate_slope_score(12.5) == 35.0
    assert evaluate_slope_score(15.0) == 0.0
    assert evaluate_slope_score(25.0) == 0.0

    # 2. Surface Roughness
    assert evaluate_roughness_score(0.10) == 100.0
    assert evaluate_roughness_score(0.25) == 100.0
    assert evaluate_roughness_score(0.50) == 70.0
    assert evaluate_roughness_score(1.20) == 0.0
    assert evaluate_roughness_score(2.00) == 0.0

    # 3. Solar Illumination
    assert evaluate_illumination_score(100.0) == 100.0
    assert evaluate_illumination_score(80.0) == 100.0
    assert evaluate_illumination_score(60.0) == 70.0
    assert evaluate_illumination_score(40.0) == 30.0
    assert evaluate_illumination_score(0.0) == 0.0

    # 4. Hazards
    assert evaluate_crater_hazard_score(0) == 100.0
    assert evaluate_crater_hazard_score(1) == 85.0
    assert evaluate_crater_hazard_score(2) == 70.0
    assert evaluate_crater_hazard_score(10) == 10.0

    assert evaluate_rock_hazard_score(0) == 100.0
    assert evaluate_rock_hazard_score(1) == 80.0
    assert evaluate_rock_hazard_score(2) == 65.0
    assert evaluate_rock_hazard_score(8) == 5.0


def test_scoring_custom_weight_configuration(client: TestClient) -> None:
    """Tests custom weights are strictly respected and normalized."""
    payload = {
        "slope_deg": 5.0,  # score = 100.0
        "roughness_m": 0.50,  # score = 70.0
        "illumination_pct": 40.0,  # score = 30.0
        "crater_count": 0,
        "rock_count": 0,
        "elevation_m": 0.0,
        "weights": {
            "slope_weight": 0.80,
            "illumination_weight": 0.20,
            "roughness_weight": 0.0,
            "crater_hazard_weight": 0.0,
            "rock_hazard_weight": 0.0,
            "elevation_weight": 0.0,
        },
    }
    response = client.post("/api/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Expected: 100.0 * 0.80 + 30.0 * 0.20 = 80.0 + 6.0 = 86.0
    assert data["overall_suitability_score"] == 86.0


def test_scoring_repeatability(client: TestClient) -> None:
    """Verifies that scoring engine is strictly deterministic across repeated evaluations."""
    payload = {
        "slope_deg": 4.5,
        "roughness_m": 0.35,
        "illumination_pct": 72.0,
        "crater_count": 1,
        "rock_count": 2,
        "elevation_m": 850.0,
    }
    first_response = client.post("/api/score", json=payload).json()

    for _ in range(4):
        subsequent = client.post("/api/score", json=payload).json()
        assert subsequent["overall_suitability_score"] == first_response["overall_suitability_score"]
        assert subsequent["suitability_category"] == first_response["suitability_category"]
        assert subsequent["score_coverage_pct"] == first_response["score_coverage_pct"]


def test_analysis_run_includes_suitability(client: TestClient) -> None:
    """Tests POST /api/analysis/run integrates preliminary suitability score."""
    payload = {
        "center_lat": -89.44,
        "center_lon": 222.50,
        "radius_meters": 1000.0,
    }
    response = client.post("/api/analysis/run", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "suitability" in data
    suit = data["suitability"]
    assert suit is not None
    assert suit["overall_suitability_score"] is not None
    assert suit["criteria_version"] == CRITERIA_VERSION
    assert suit["score_coverage_pct"] > 0.0
    assert len(suit["subscores"]) > 0
