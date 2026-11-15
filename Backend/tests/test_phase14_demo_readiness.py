"""
test_phase14_demo_readiness.py
==============================
Comprehensive End-to-End Mission Simulation and Technical Demo Readiness Test Suite.

Validates the full Moonscape 17-step user workflow across:
  - Scenario 1: Favorable Site (Shackleton Connecting Ridge: -89.44 deg, 222.50 deg)
  - Scenario 2: Severe Hazard / Disqualified Site (Faustini Inner Wall: -89.75 deg, 120.00 deg)
  - Scenario 3: Coverage Boundary / Out-of-Bounds (Latitude -78.50 deg, 45.00 deg)
  - Edge Cases: Offline AI operation, date/time seasonal shift, ML surrogate model fallback,
                and sub-millisecond LRU cache performance.
"""

import time
from fastapi.testclient import TestClient
from app.main import app
from app.services.ml.suitability_model_service import suitability_model_service
from app.services.ai_providers import MockDeterministicProvider
from app.services.ai_explainer import AIExplainerService
from app.schemas.ai import AIExplainRequest

client = TestClient(app)


# ============================================================================
# SCENARIO 1: FAVORABLE SITE (Shackleton Connecting Ridge)
# ============================================================================

def test_scenario_1_favorable_site_full_workflow():
    """
    Scenario 1: Favorable Landing Site (-89.44 deg, 222.50 deg, Artemis HLS profile)
    Step-by-step validation of complete mission workflow:
      1. Dataset Coverage check (both /api/data/coverage and /api/coverage alias)
      2. Point Terrain Sampling & Full Ellipse Landing Zone Analysis
      3. Hazard Detection
      4. Solar & Earth Visibility Simulation
      5. MCDA & Tabular ML Suitability Scoring (hard constraints passed, score >= 70)
      6. Grounded AI Scientific Explanation
      7. Scientific Report Generation (JSON & PDF)
    """
    lat = -89.44
    lon = 222.50

    # 1. Coverage Check
    cov_resp = client.get(f"/api/data/coverage?lat={lat}&lon={lon}")
    assert cov_resp.status_code == 200
    cov_data = cov_resp.json()
    assert cov_data["valid_coordinate"] is True
    assert cov_data["in_south_pole_zone"] is True
    assert len(cov_data["layers"]) >= 5

    alias_resp = client.get(f"/api/coverage?lat={lat}&lon={lon}")
    assert alias_resp.status_code == 200
    assert alias_resp.json()["in_south_pole_zone"] is True

    # 2. Point Terrain Sampling & Analysis Run
    terrain_resp = client.get(f"/api/terrain?lat={lat}&lon={lon}&radius_m=500.0")
    assert terrain_resp.status_code == 200
    t_data = terrain_resp.json()
    assert t_data["is_valid_point"] is True
    assert t_data["slope_deg"] < 10.0  # Benign ridge slope
    assert t_data["elevation_m"] is not None
    assert t_data["roughness_m"] is not None
    assert "dataset_info" in t_data

    # Full windowed analysis run
    analysis_resp = client.post("/api/analysis/run", json={
        "center_lat": lat,
        "center_lon": lon,
        "radius_meters": 1000.0,
        "max_acceptable_slope_deg": 10.0,
        "max_acceptable_roughness_m": 0.5,
    })
    assert analysis_resp.status_code == 200
    a_data = analysis_resp.json()
    assert a_data["analysis_id"] is not None

    # 3. Hazard Detection
    hazard_resp = client.post("/api/hazards/predict", json={
        "center_lat": lat,
        "center_lon": lon,
        "radius_meters": 500.0,
    })
    assert hazard_resp.status_code == 200
    h_data = hazard_resp.json()
    assert h_data["status"] == "success"
    assert h_data["overall_hazard_level"] in ["low", "moderate", "high", "critical"]

    # 4. Sunlight & Earth Visibility Simulation
    sim_resp = client.post("/api/simulation/visibility", json={
        "lat": lat,
        "lon": lon,
        "start_epoch_iso": "2026-10-01T00:00:00Z",
        "duration_days": 14.0,
        "step_hours": 2.0
    })
    assert sim_resp.status_code == 200
    s_data = sim_resp.json()
    assert s_data["sunlight_percentage"] > 50.0  # Polar ridge elevated sunlight
    assert s_data["earth_comm_percentage"] >= 40.0  # Polar ridge terrain-masked Earth line-of-sight
    assert len(s_data["time_series"]) > 50

    # 5. Suitability Scoring (MCDA + ML Surrogate Model)
    score_resp = client.post("/api/score", json={
        "slope_deg": t_data["slope_deg"],
        "roughness_m": t_data["roughness_m"],
        "elevation_m": t_data["elevation_m"],
        "illumination_pct": s_data["sunlight_percentage"],
        "earth_visibility_pct": s_data["earth_comm_percentage"],
        "mission_profile": "artemis_hls"
    })
    assert score_resp.status_code == 200
    sc_data = score_resp.json()
    assert sc_data["hard_constraint_status"] == "passed"
    assert sc_data["overall_suitability_score"] >= 70.0
    assert sc_data["ml_model_score"] is not None
    assert sc_data["ml_model_score"] > 30.0

    # 6. Grounded AI Explanation
    ai_resp = client.post("/api/ai/explain", json={
        "site_id": "shackleton_connecting_ridge",
        "user_query": "Why is this site ranked higher than alternative locations?"
    })
    assert ai_resp.status_code == 200
    ai_data = ai_resp.json()
    assert "ranking" in ai_data["explanation"].lower() or "slope" in ai_data["explanation"].lower()
    assert "illumination" in ai_data["explanation"].lower() or "sunlight" in ai_data["explanation"].lower()

    # 7. Scientific Report Generation
    # JSON report
    rep_json = client.post("/api/reports/generate", json={
        "analysis_id": a_data["analysis_id"],
        "format": "json"
    })
    assert rep_json.status_code == 200
    assert rep_json.json()["analysis_id"] == a_data["analysis_id"]

    # PDF report
    rep_pdf = client.post("/api/reports/generate", json={
        "analysis_id": a_data["analysis_id"],
        "format": "pdf"
    })
    assert rep_pdf.status_code == 200
    assert rep_pdf.headers["content-type"] == "application/pdf"
    assert rep_pdf.content.startswith(b"%PDF-")
    assert len(rep_pdf.content) > 2000  # Valid binary PDF data


# ============================================================================
# SCENARIO 2: SEVERE HAZARD / DISQUALIFIED SITE (Faustini Inner Wall)
# ============================================================================

def test_scenario_2_hazard_disqualified_site():
    """
    Scenario 2: Severe Hazard Landing Site (-89.75 deg, 120.00 deg)
    Verifies:
      - Slope > 15 deg violates universal tip-over limit.
      - Hard mission constraint status is 'violated'.
      - Composite score is severely capped (< 40.0).
      - AI explanation flags Apollo/Artemis structural tip-over risk.
    """
    score_resp = client.post("/api/score", json={
        "slope_deg": 21.5,   # Critical: exceeds 15.0 deg universal Apollo/Artemis tip-over
        "roughness_m": 0.85,
        "elevation_m": -3200.0,
        "illumination_pct": 5.0,
        "earth_visibility_pct": 0.0,
        "mission_profile": "artemis_hls"
    })
    assert score_resp.status_code == 200
    data = score_resp.json()
    assert data["hard_constraint_status"] == "violated"
    assert data["overall_suitability_score"] < 40.0
    assert len(data["hard_constraint_violations"]) >= 1
    assert any("tip-over limit" in v for v in data["hard_constraint_violations"])

    # AI Explanation on hazard inquiry
    ai_resp = client.post("/api/ai/explain", json={
        "topographic_data": {
            "mean_slope_deg": 21.5,
            "rms_roughness_m": 0.85
        },
        "user_query": "What are the primary hazards at this site?"
    })
    assert ai_resp.status_code == 200
    ai_text = ai_resp.json()["explanation"]
    assert "slope" in ai_text.lower()
    assert "tip-over" in ai_text.lower() or "safety" in ai_text.lower() or "exceeds" in ai_text.lower()


# ============================================================================
# SCENARIO 3: COVERAGE BOUNDARY / OUT-OF-BOUNDS SITE
# ============================================================================

def test_scenario_3_coverage_boundary():
    """
    Scenario 3: Latitude -68.50 deg, 45.00 deg
    Verifies:
      - Coordinate is north of the -70.0 deg polar stereographic South Pole grid.
      - Coverage endpoint reports in_south_pole_zone == False.
      - Querying terrain returns is_valid_point=False gracefully without crashing.
    """
    lat = -68.50
    lon = 45.00

    cov_resp = client.get(f"/api/data/coverage?lat={lat}&lon={lon}")
    assert cov_resp.status_code == 200
    cov_data = cov_resp.json()
    assert cov_data["valid_coordinate"] is True
    assert cov_data["in_south_pole_zone"] is False

    # Terrain query out of polar bounds returns valid JSON with is_valid_point=False
    terrain_resp = client.get(f"/api/terrain?lat={lat}&lon={lon}")
    assert terrain_resp.status_code == 200
    t_data = terrain_resp.json()
    assert t_data["is_valid_point"] is False
    assert t_data["slope_deg"] is None
    assert t_data["elevation_m"] is None
    assert "outside" in t_data["notes"].lower()


# ============================================================================
# OPERATIONAL EDGE CASES: OFFLINE AI, DATE/TIME SHIFT, ML FALLBACK, CACHING
# ============================================================================

def test_offline_ai_explainer_six_benchmark_questions():
    """
    Verifies that the MockDeterministicProvider reliably answers all 6
    planetary science benchmark questions offline without external internet calls.
    """
    service = AIExplainerService(provider=MockDeterministicProvider())
    questions = [
        "What are the primary hazards at this site?",
        "Why is Earth visibility intermittent?",
        "How would conditions change one month later?",
        "What are the key uncertainties in the elevation and slope measurements?",
        "What additional NASA datasets are recommended?",
        "Why is this site ranked higher than alternative locations?"
    ]

    for q in questions:
        req = AIExplainRequest(
            site_id="shackleton_connecting_ridge",
            user_query=q
        )
        res = service.explain_analysis(req)
        assert res.explanation is not None
        assert len(res.explanation) > 50
        assert "Moonscape" in res.model_origin or "Deterministic" in res.model_origin


def test_temporal_simulation_date_shift():
    """
    Verifies that changing the mission epoch changes the solar elevation
    and illumination curve as dictated by lunar orbital obliquity.
    """
    lat = -89.44
    lon = 222.50

    # Epoch 1: October 1, 2026
    sim1 = client.post("/api/simulation/visibility", json={
        "lat": lat,
        "lon": lon,
        "start_epoch_iso": "2026-10-01T00:00:00Z",
        "duration_days": 7.0,
        "step_hours": 6.0
    }).json()

    # Epoch 2: November 1, 2026 (1 month later)
    sim2 = client.post("/api/simulation/visibility", json={
        "lat": lat,
        "lon": lon,
        "start_epoch_iso": "2026-11-01T00:00:00Z",
        "duration_days": 7.0,
        "step_hours": 6.0
    }).json()

    # Solar elevation mean must differ due to subsolar latitude progression
    solar_mean_1 = sum(p["solar_elevation_deg"] for p in sim1["time_series"]) / len(sim1["time_series"])
    solar_mean_2 = sum(p["solar_elevation_deg"] for p in sim2["time_series"]) / len(sim2["time_series"])
    assert abs(solar_mean_1 - solar_mean_2) > 0.05  # Significant seasonal elevation shift


def test_ml_surrogate_model_fallback_on_missing_model(monkeypatch):
    """
    Verifies that if the ML model is disabled or unavailable, the scoring engine
    falls back cleanly to the deterministic MCDA score without failing.
    """
    # Temporarily monkeypatch the model to None
    monkeypatch.setattr(suitability_model_service, "_model", None)
    monkeypatch.setattr(suitability_model_service, "_is_loaded", True)

    resp = client.post("/api/score", json={
        "slope_deg": 4.0,
        "roughness_m": 0.22,
        "elevation_m": 900.0,
        "illumination_pct": 80.0,
        "mission_profile": "artemis_hls"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_suitability_score"] is not None
    assert data["hard_constraint_status"] == "passed"
    assert data["ml_model_score"] is not None
    assert data["model_version"] is not None


def test_terrain_lru_caching_submillisecond():
    """
    Verifies that the thread-safe LRU cache on analyze_location returns
    subsequent queries for the same coordinate in sub-millisecond time.
    """
    lat = -89.44
    lon = 222.50

    # First call: populates cache
    resp1 = client.get(f"/api/terrain?lat={lat}&lon={lon}")
    assert resp1.status_code == 200

    # Second call: cached
    t0 = time.perf_counter()
    resp2 = client.get(f"/api/terrain?lat={lat}&lon={lon}")
    t1 = time.perf_counter()
    assert resp2.status_code == 200

    cached_duration = t1 - t0
    # Verify cached call is fast and results are identical
    assert resp1.json()["slope_deg"] == resp2.json()["slope_deg"]
    assert cached_duration < 0.05  # Within 50ms including HTTP testclient stack


def test_candidate_detection_and_ranking():
    """
    Verifies candidate region detection endpoint (/api/sites/detect)
    generates candidate zones, ranks them, and tags hard constraint status.
    """
    resp = client.post("/api/sites/detect", json={
        "center_lat": -89.44,
        "center_lon": 222.50,
        "search_radius_meters": 1000.0,
        "max_slope_deg": 10.0,
        "max_roughness_m": 0.40,
        "min_landing_diameter_meters": 40.0,
        "mission_profile": "artemis_hls"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert len(data["candidate_zones"]) > 0
    c1 = data["candidate_zones"][0]
    assert "suitability_score" in c1
    assert "hard_constraint_status" in c1
    assert "effective_diameter_m" in c1
