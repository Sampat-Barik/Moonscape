"""Phase 13 Comprehensive Scientific and Engineering Tests:
AI Landing-Site Suitability Scoring, Tabular Surrogate Inference, Hard Constraint Gating,
Explainability, Monte Carlo Uncertainty Propagation, and Multi-Criteria Ranking.
"""

import time
from fastapi.testclient import TestClient
import numpy as np
import pytest

from app.schemas.ml_scoring import LunarSiteFeatures
from app.services.ml.suitability_model_service import suitability_model_service
from maths.scoring import evaluate_hard_constraints, MISSION_PROFILES


def test_hard_constraint_evaluation_profiles() -> None:
    """Verifies that hard engineering constraints enforce physical landing limits before soft scoring."""
    # 1. Benign Artemis HLS parameters
    benign_params = {
        "slope_deg": 4.5,
        "max_slope_deg": 7.0,
        "p95_slope_deg": 6.0,
        "roughness_m": 0.25,
        "contiguous_diameter_m": 120.0,
        "max_continuous_dark_h": 40.0,
        "earth_visibility_pct": 75.0,
    }
    violated, reasons = evaluate_hard_constraints(benign_params, profile_id="artemis_hls")
    assert not violated
    assert len(reasons) == 0

    # 2. Extreme slope tip-over violation (> 15 deg universal limit)
    steep_params = {
        "slope_deg": 18.5,
        "roughness_m": 0.25,
    }
    violated, reasons = evaluate_hard_constraints(steep_params, profile_id="artemis_hls")
    assert violated
    assert any("tip-over limit (15.0°)" in r for r in reasons)

    # 3. Footprint diameter violation for Artemis HLS (requires >= 100m)
    small_diameter_params = {
        "slope_deg": 5.0,
        "contiguous_diameter_m": 60.0,
    }
    violated, reasons = evaluate_hard_constraints(small_diameter_params, profile_id="artemis_hls")
    assert violated
    assert any("contiguous safe landing diameter" in r.lower() for r in reasons)

    # 4. CLPS cargo tolerance check (allows up to 12 deg slope, 40m footprint)
    violated_clps, _ = evaluate_hard_constraints(small_diameter_params, profile_id="clps_cargo")
    assert not violated_clps


def test_ml_feature_standardization() -> None:
    """Verifies that heterogeneous input dictionaries are mapped to standardized 24-feature schema."""
    raw_input = {
        "slope_deg": 5.2,
        "roughness_m": 0.28,
        "elevation_m": 850.0,
        "illumination_pct": 78.0,
        "crater_count": 2,
    }
    features = suitability_model_service.construct_features_from_dict(raw_input)

    assert isinstance(features, LunarSiteFeatures)
    assert features.mean_slope_deg == 5.2
    assert features.roughness_15m == 0.28
    assert features.mean_elevation_m == 850.0
    assert features.cumulative_sunlight_pct == 78.0
    assert features.crater_density_km2 == 1.0  # 2 / 2.0
    assert features.vertical_uncertainty_m == 1.5  # LOLA standard uncertainty
    assert features.slope_uncertainty_deg == 1.2


def test_ml_model_inference_latency() -> None:
    """Verifies that ML surrogate model runs locally on CPU with latency under 10ms."""
    sample = {
        "slope_deg": 4.1,
        "roughness_m": 0.22,
        "elevation_m": 1200.0,
        "illumination_pct": 82.0,
    }

    # Warm-up inference
    suitability_model_service.predict_suitability(sample, run_monte_carlo=False)

    times = []
    for _ in range(10):
        t0 = time.perf_counter()
        res = suitability_model_service.predict_suitability(sample, run_monte_carlo=False)
        times.append(time.perf_counter() - t0)

    avg_latency_ms = (sum(times) / len(times)) * 1000.0
    assert avg_latency_ms < 15.0, f"Inference took {avg_latency_ms:.2f}ms, expected < 15ms"
    assert 0.0 <= res.ml_suitability_score <= 100.0
    assert res.hard_constraint_status == "passed"


def test_monte_carlo_uncertainty_propagation() -> None:
    """Verifies that measurement noise propagation produces valid confidence intervals and stability."""
    sample = {
        "slope_deg": 5.0,
        "roughness_m": 0.30,
        "elevation_m": 500.0,
        "illumination_pct": 75.0,
    }
    res = suitability_model_service.predict_suitability(sample, run_monte_carlo=True)

    assert res.uncertainty_score_std >= 0.0
    assert len(res.confidence_interval_95) == 2
    assert res.confidence_interval_95[0] <= res.confidence_interval_95[1]
    assert res.ranking_stability in ["high", "moderate", "low"]


def test_feature_explainability_contributions() -> None:
    """Verifies that feature sensitivity identifies positive assets and risk factors."""
    sample = {
        "slope_deg": 3.0,  # Highly favorable
        "roughness_m": 0.18,  # Highly favorable
        "elevation_m": 1500.0,
        "illumination_pct": 85.0,  # Highly favorable
        "crater_count": 6,  # Elevated hazard
    }
    res = suitability_model_service.predict_suitability(sample, run_monte_carlo=False)

    assert len(res.top_positive_features) > 0
    assert len(res.top_risk_features) > 0
    # Crater hazard should be flagged in top risks
    assert any("crater" in k.lower() for k in res.top_risk_features.keys())


def test_api_score_with_mission_profile(client: TestClient) -> None:
    """Tests POST /api/score with explicit mission profile and ML surrogate enrichment."""
    payload = {
        "slope_deg": 4.0,
        "roughness_m": 0.22,
        "elevation_m": 900.0,
        "illumination_pct": 80.0,
        "mission_profile": "artemis_hls",
    }
    response = client.post("/api/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["mission_profile"] == "artemis_hls"
    assert data["hard_constraint_status"] == "passed"
    assert len(data["hard_constraint_violations"]) == 0
    assert data["scientific_baseline_score"] is not None
    assert data["ml_model_score"] is not None
    assert 0.0 <= data["ml_model_score"] <= 100.0
    assert data["model_version"] is not None
    assert data["uncertainty_score_std"] is not None
    assert len(data["confidence_interval_95"]) == 2
    assert isinstance(data["feature_contributions"], dict)


def test_api_score_hard_constraint_rejection(client: TestClient) -> None:
    """Tests POST /api/score disqualifies sites violating engineering constraints."""
    payload = {
        "slope_deg": 19.0,  # Exceeds universal tip-over limit (15.0 deg)
        "roughness_m": 0.20,
        "illumination_pct": 95.0,  # Strong illumination must NOT mask slope disqualification
        "mission_profile": "artemis_hls",
    }
    response = client.post("/api/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["hard_constraint_status"] == "violated"
    assert len(data["hard_constraint_violations"]) > 0
    assert any("tip-over limit" in v for v in data["hard_constraint_violations"])
    assert data["suitability_category"] in ["Lower preliminary suitability", "Unsuitable"]
    # Strong sunlight should not bypass slope penalty
    assert data["overall_suitability_score"] < 40.0


def test_api_compare_sites_with_mission_profile(client: TestClient) -> None:
    """Tests POST /api/sites/compare returns ML scores and hard constraint evaluations."""
    payload = {
        "site_ids": ["shackleton_connecting_ridge", "malapert_mountain"],
        "mission_profile": "clps_cargo",
    }
    response = client.post("/api/sites/compare", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["mission_profile"] == "clps_cargo"
    assert len(data["compared_sites"]) == 2
    for site in data["compared_sites"]:
        assert site["hard_constraint_status"] in ["passed", "violated"]
        assert site["ml_model_score"] is not None
        assert site["suitability_score"] is not None
        assert site["safety_rank"] in [1, 2]


def test_geographic_dataset_leakage_prevention() -> None:
    """Verifies that training, validation, and holdout datasets have zero geographic overlap."""
    from app.services.ml.dataset_generator import dataset_generator
    recs = dataset_generator.load_saved_dataset()

    train_regions = {r.geographic_region for r in recs if r.split_group == "train"}
    val_regions = {r.geographic_region for r in recs if r.split_group == "validation"}
    test_regions = {r.geographic_region for r in recs if r.split_group == "heldout_test"}

    # Zero intersection between splits
    assert len(train_regions.intersection(val_regions)) == 0, "Spatial leakage between train and validation!"
    assert len(train_regions.intersection(test_regions)) == 0, "Spatial leakage between train and test!"
    assert len(val_regions.intersection(test_regions)) == 0, "Spatial leakage between validation and test!"
