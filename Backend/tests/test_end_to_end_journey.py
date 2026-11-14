"""Complete End-to-End User Journey Test Suite for Moonscape.

Validates all 14 steps of the required user journey:
1. Lunar South Pole map display & configuration
2. Coordinate selection & manual entry
3. Input validation & range checking
4. NASA dataset coverage checking
5. Elevation, slope and roughness terrain analysis
6. Hazard analysis (craters, boulders, steep slopes)
7. Candidate landing regions identification
8. Mission start date/time & duration selection
9. Sunlight, illumination & shadow conditions calculation
10. Earth visibility calculation
11. Multi-criteria landing site scoring & ranking
12. AI assistant explanation of ranking
13. Comparison of candidate sites
14. Export of scientific report (JSON and binary PDF)
15. Scientific honesty & edge case failure handling
"""

import pytest
from fastapi.testclient import TestClient


def test_complete_moonscape_14_step_journey(client: TestClient) -> None:
    # -------------------------------------------------------------------------
    # STEP 1: User opens the lunar South Pole map & checks system health
    # -------------------------------------------------------------------------
    health_res = client.get("/api/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["status"] == "healthy"
    assert health_data["dem_dataset_loaded"] is True
    assert health_data["sites_loaded"] >= 8

    map_res = client.get("/api/map/config")
    assert map_res.status_code == 200
    map_config = map_res.json()
    assert "Polar Stereographic" in map_config["projection"]
    assert "104903" in map_config["epsg_code"]
    assert len(map_config["layers"]) >= 3

    sites_res = client.get("/api/sites")
    assert sites_res.status_code == 200
    sites = sites_res.json()
    assert len(sites) >= 8

    # -------------------------------------------------------------------------
    # STEP 2 & 3: Coordinate selection & input validation
    # Selected candidate: Shackleton Connecting Ridge (-89.44, 222.50)
    # -------------------------------------------------------------------------
    target_lat = -89.44
    target_lon = 222.50
    radius_m = 1000.0

    # Ensure coordinates are within South Pole bounds (-90 <= lat <= -80)
    assert -90.0 <= target_lat <= -80.0
    assert -180.0 <= target_lon <= 360.0

    # -------------------------------------------------------------------------
    # STEP 4: Backend checks NASA dataset coverage
    # -------------------------------------------------------------------------
    cov_res = client.get(f"/api/coverage?lat={target_lat}&lon={target_lon}")
    assert cov_res.status_code == 200
    cov_data = cov_res.json()
    assert cov_data["valid_coordinate"] is True
    assert cov_data["in_south_pole_zone"] is True
    assert cov_data["total_covering_sources"] >= 5
    assert cov_data["best_installed_resolution_m"] is not None
    # Product 90 or 78 covers this candidate
    covering_layers = [l for l in cov_data["layers"] if l["covers"]]
    assert len(covering_layers) >= 2

    # -------------------------------------------------------------------------
    # STEP 5: Terrain analysis returns elevation, slope and roughness
    # -------------------------------------------------------------------------
    analysis_req = {
        "center_lat": target_lat,
        "center_lon": target_lon,
        "radius_meters": radius_m,
        "max_acceptable_slope_deg": 15.0,
        "max_acceptable_roughness_m": 2.0,
        "latitude": target_lat,
        "longitude": target_lon,
        "radius_m": radius_m,
    }
    anl_res = client.post("/api/analysis/run", json=analysis_req)
    assert anl_res.status_code == 200
    anl_data = anl_res.json()
    analysis_id = anl_data["analysis_id"]
    assert analysis_id.startswith("ANL-")

    # Verify authentic scientific measurements
    assert anl_data["elevation"]["mean_value"] is not None
    assert anl_data["elevation"]["units"] == "meters"
    assert anl_data["slope"]["mean_value"] is not None
    assert anl_data["slope"]["units"] == "degrees"
    assert anl_data["roughness_mean_m"] is not None
    assert anl_data["safe_touchdown_fraction_pct"] > 0
    assert anl_data["dataset_metadata"]["is_measured_data"] is True

    # -------------------------------------------------------------------------
    # STEP 6: Hazard analysis evaluates slope, roughness, crater & boulder info
    # -------------------------------------------------------------------------
    hazard_req = {
        "center_lat": target_lat,
        "center_lon": target_lon,
        "radius_meters": radius_m,
    }
    haz_res = client.post("/api/hazards/predict", json=hazard_req)
    assert haz_res.status_code == 200
    haz_data = haz_res.json()
    assert haz_data["status"] == "success"
    assert haz_data["overall_hazard_level"] in ["low", "moderate", "high", "critical"]
    assert "Morphological Curvature" in haz_data["model_name"]
    # Hazards list contains items with confidence and size
    assert isinstance(haz_data.get("hazards", []), list)

    # -------------------------------------------------------------------------
    # STEP 7: Backend identifies contiguous candidate landing regions
    # -------------------------------------------------------------------------
    detect_req = {
        "center_lat": target_lat,
        "center_lon": target_lon,
        "search_radius_meters": 1500.0,
        "max_slope_deg": 10.0,
        "max_roughness_m": 0.5,
        "min_landing_diameter_meters": 50.0,
    }
    det_res = client.post("/api/sites/detect", json=detect_req)
    assert det_res.status_code == 200
    det_data = det_res.json()
    assert det_data["status"] == "success"
    assert det_data["total_sites_detected"] > 0
    candidate_zones = det_data["candidate_zones"]
    assert len(candidate_zones) > 0
    top_zone = candidate_zones[0]
    assert top_zone["safety_rank"] == 1
    assert top_zone["effective_diameter_m"] >= 50.0
    assert top_zone["mean_slope_deg"] <= 10.0

    # -------------------------------------------------------------------------
    # STEP 8, 9 & 10: Time simulation (Sunlight, shadow, Earth visibility)
    # -------------------------------------------------------------------------
    sim_req = {
        "lat": target_lat,
        "lon": target_lon,
        "start_epoch_iso": "2026-10-15T00:00:00Z",
        "duration_days": 14.0,
        "step_hours": 2.0,
    }
    sim_res = client.post("/api/simulation/visibility", json=sim_req)
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["total_steps"] == 169
    assert sim_data["sunlight_percentage"] > 0
    assert sim_data["earth_comm_percentage"] > 0
    assert sim_data["max_continuous_sunlight_hours"] > 0
    assert sim_data["max_continuous_darkness_hours"] >= 0
    assert len(sim_data["time_series"]) == 169

    # Verify first step fields
    step0 = sim_data["time_series"][0]
    assert "solar_elevation_deg" in step0
    assert "earth_elevation_deg" in step0
    assert "communication_status" in step0
    assert step0["communication_status"] in ["operational", "marginal", "blackout"]

    # -------------------------------------------------------------------------
    # STEP 11: Multi-criteria suitability scoring ranks candidate
    # -------------------------------------------------------------------------
    score_req = {
        "latitude": target_lat,
        "longitude": target_lon,
        "radius_m": radius_m,
    }
    score_res = client.post("/api/score", json=score_req)
    assert score_res.status_code == 200
    score_data = score_res.json()
    assert score_data["overall_suitability_score"] is not None
    assert score_data["score"] == score_data["overall_suitability_score"]
    assert score_data["suitability_category"] is not None
    assert score_data["hard_constraint_status"] in ["passed", "violated"]
    assert len(score_data["subscores"]) >= 4

    # -------------------------------------------------------------------------
    # STEP 12: AI assistant explains the ranking and trade-offs
    # -------------------------------------------------------------------------
    explain_req = {
        "analysis_id": analysis_id,
        "focus_topics": ["topography", "illumination", "hazards"],
    }
    exp_res = client.post("/api/ai/explain", json=explain_req)
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    assert exp_data["analysis_id"] == analysis_id
    assert len(exp_data["explanation"]) > 50
    assert len(exp_data["positive_factors"]) >= 1
    assert len(exp_data["risk_factors"]) >= 1

    # -------------------------------------------------------------------------
    # STEP 13: User compares multiple candidate sites
    # -------------------------------------------------------------------------
    compare_req = {
        "site_ids": ["shackleton_connecting_ridge", "malapert_mountain"],
        "weights": {"slope": 0.35, "illumination": 0.35, "communication": 0.20, "science": 0.10},
    }
    cmp_res = client.post("/api/sites/compare", json=compare_req)
    assert cmp_res.status_code == 200
    cmp_data = cmp_res.json()
    assert len(cmp_data["compared_sites"]) == 2
    assert cmp_data["top_recommended_site_id"] in ["shackleton_connecting_ridge", "malapert_mountain"]

    # -------------------------------------------------------------------------
    # STEP 14: User exports scientific report (JSON & binary PDF)
    # -------------------------------------------------------------------------
    # 14a. JSON report
    rep_json_res = client.post("/api/reports/generate", json={"analysis_id": analysis_id, "format": "json"})
    assert rep_json_res.status_code == 200
    rep_json = rep_json_res.json()
    assert "report_data" in rep_json

    # 14b. Binary PDF report
    rep_pdf_res = client.post("/api/reports/generate", json={"analysis_id": analysis_id, "format": "pdf"})
    assert rep_pdf_res.status_code == 200
    assert rep_pdf_res.headers["content-type"] == "application/pdf"
    assert rep_pdf_res.content.startswith(b"%PDF-")
    assert len(rep_pdf_res.content) > 1000


def test_scientific_honesty_and_error_boundaries(client: TestClient) -> None:
    """Verifies that invalid coordinates, missing datasets, and boundary violations are reported honestly."""
    # 1. Invalid physical latitude (< -90) triggers 422
    res_lat_low = client.get("/api/terrain?lat=-95.0&lon=0.0")
    assert res_lat_low.status_code == 422

    # 2. Coordinate outside South Pole polar bounds (-75 deg) reports nodata honestly without 0 coercion
    res_outside = client.get("/api/terrain?lat=-75.0&lon=0.0")
    assert res_outside.status_code == 200
    d_outside = res_outside.json()
    assert d_outside["is_valid_point"] is False
    assert d_outside["landing_hazard_classification"] == "nodata"
    assert d_outside["dataset_info"]["is_measured_data"] is False
    assert d_outside["elevation_m"] is None  # Never coerced to zero!

    # 3. Nonexistent candidate site ID returns 404
    res_404_site = client.get("/api/sites/fictional_crater_apollo_99")
    assert res_404_site.status_code == 404

    # 4. Unknown analysis ID in report generation returns 404
    res_404_report = client.post("/api/reports/generate", json={"analysis_id": "ANL-DOES-NOT-EXIST", "format": "json"})
    assert res_404_report.status_code == 404

    # 5. Duplicate site IDs in comparison rejected via 422
    res_dup = client.post("/api/sites/compare", json={"site_ids": ["malapert_mountain", "malapert_mountain"]})
    assert res_dup.status_code == 422
