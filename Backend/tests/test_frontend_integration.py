"""End-to-End Frontend-Backend Integration Test Suite (Phase 9).

Validates the complete 12-step user workflow and error recovery contracts between
the Moonscape frontend application and the FastAPI backend.
"""

from fastapi.testclient import TestClient


def test_complete_frontend_backend_workflow(client: TestClient) -> None:
    """Executes the complete 12-step Moonscape frontend data flow from initial load to PDF report download."""

    # Step 1: Health check on page load
    health_res = client.get("/api/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["status"] == "healthy"
    assert health_data["sites_loaded"] >= 8
    assert "ESRI:104903" in health_data["crs"]

    # Step 2: Load candidate sites catalog
    sites_res = client.get("/api/sites")
    assert sites_res.status_code == 200
    sites = sites_res.json()
    assert len(sites) >= 8
    shackleton = next(s for s in sites if s["site_id"] == "shackleton_connecting_ridge")
    assert shackleton["latitude"] == -89.44
    assert shackleton["longitude"] == 222.50

    # Step 3: Load cartographic map configuration
    map_res = client.get("/api/map/config")
    assert map_res.status_code == 200
    map_config = map_res.json()
    assert "Polar Stereographic" in map_config["projection"]
    assert map_config["latitude_bounds"] == [-90.0, -80.0]
    assert map_config["longitude_bounds"] == [-180.0, 180.0]

    # Step 4: Sample point terrain at selected coordinates
    point_res = client.get(f"/api/terrain?lat={shackleton['latitude']}&lon={shackleton['longitude']}")
    assert point_res.status_code == 200
    point_data = point_res.json()
    assert point_data["elevation_m"] is not None
    assert point_data["slope_deg"] is not None

    # Step 5: Execute full landing zone spatial analysis
    analysis_req = {
        "center_lat": shackleton["latitude"],
        "center_lon": shackleton["longitude"],
        "radius_meters": 1000.0,
        "max_acceptable_slope_deg": 10.0,
        "max_acceptable_roughness_m": 0.5,
    }
    analysis_res = client.post("/api/analysis/run", json=analysis_req)
    assert analysis_res.status_code == 200
    analysis = analysis_res.json()
    analysis_id = analysis["analysis_id"]
    assert analysis_id.startswith("ANL-")

    # Step 6 & 7: Verify backend processed terrain results
    assert analysis["elevation"]["mean_value"] is not None
    assert analysis["slope"]["mean_value"] is not None
    assert analysis["slope_distribution"]["ideal_pct"] > 0
    assert analysis["safe_touchdown_fraction_pct"] > 0
    assert analysis["dataset_metadata"]["is_measured_data"] is True

    # Step 8: Verify illumination results
    assert analysis["illumination"]["status"] == "available"
    assert analysis["illumination"]["cumulative_illumination_pct"] > 70.0

    # Step 9: Verify suitability assessment
    suitability = analysis["suitability"]
    assert suitability is not None
    assert suitability["overall_suitability_score"] is not None
    assert suitability["score_coverage_pct"] >= 70.0

    # Step 10: Run hazard detection
    hazard_req = {
        "center_lat": shackleton["latitude"],
        "center_lon": shackleton["longitude"],
        "radius_meters": 1000.0,
    }
    hazard_res = client.post("/api/hazards/predict", json=hazard_req)
    assert hazard_res.status_code == 200
    hazard_data = hazard_res.json()
    assert "status" in hazard_data

    # Step 10b: Direct suitability score via frontend coordinate payload
    score_req = {
        "latitude": shackleton["latitude"],
        "longitude": shackleton["longitude"],
        "radius_m": 50.0,
    }
    score_res = client.post("/api/score", json=score_req)
    assert score_res.status_code == 200
    score_data = score_res.json()
    assert score_data["overall_suitability_score"] is not None
    assert score_data["score"] == score_data["overall_suitability_score"]
    assert score_data["label"] is not None
    assert score_data["breakdown"] is not None
    assert "slope" in score_data["breakdown"]

    # Step 11: Compare multiple candidate sites
    compare_req = {
        "site_ids": ["shackleton_connecting_ridge", "malapert_mountain"],
        "weights": {"slope": 0.40, "illumination": 0.30, "communication": 0.20, "science": 0.10},
    }
    compare_res = client.post("/api/sites/compare", json=compare_req)
    assert compare_res.status_code == 200
    compare_data = compare_res.json()
    assert len(compare_data["compared_sites"]) == 2
    assert compare_data["top_recommended_site_id"] in ["shackleton_connecting_ridge", "malapert_mountain"]

    # Step 12: Request AI Scientific Explanation for the analysis_id
    explain_req = {
        "analysis_id": analysis_id,
        "focus_topics": ["topography", "slope"],
    }
    explain_res = client.post("/api/ai/explain", json=explain_req)
    assert explain_res.status_code == 200
    explain_data = explain_res.json()
    assert explain_data["analysis_id"] == analysis_id
    assert len(explain_data["explanation"]) > 30
    assert len(explain_data["positive_factors"]) >= 1
    assert len(explain_data["risk_factors"]) >= 1

    # Step 13: Generate JSON Scientific Report
    report_json_req = {
        "analysis_id": analysis_id,
        "format": "json",
    }
    report_json_res = client.post("/api/reports/generate", json=report_json_req)
    assert report_json_res.status_code == 200
    report_json_data = report_json_res.json()
    assert report_json_data["report_data"]["analysis_id"] == analysis_id

    # Step 14: Download Binary PDF Scientific Report
    report_pdf_req = {
        "analysis_id": analysis_id,
        "format": "pdf",
    }
    report_pdf_res = client.post("/api/reports/generate", json=report_pdf_req)
    assert report_pdf_res.status_code == 200
    assert report_pdf_res.headers["content-type"] == "application/pdf"
    assert report_pdf_res.content.startswith(b"%PDF-")
    assert len(report_pdf_res.content) > 2000


def test_frontend_error_handling_contracts(client: TestClient) -> None:
    """Verifies that the backend returns structured, beginner-friendly error responses for all edge cases."""

    # 1. Coordinate outside physical latitude bounds (lat < -90.0) triggers 422
    res_bad_coord = client.get("/api/terrain?lat=-95.0&lon=0.0")
    assert res_bad_coord.status_code == 422  # Pydantic validation failure on lat range

    # 1b. Coordinate outside South Pole coverage region (-80 < lat <= 90) returns 200 with invalid point and nodata classification
    res_out_of_bounds = client.get("/api/terrain?lat=-75.0&lon=0.0")
    assert res_out_of_bounds.status_code == 200
    out_data = res_out_of_bounds.json()
    assert out_data["is_valid_point"] is False
    assert out_data["landing_hazard_classification"] == "nodata"
    assert out_data["dataset_info"]["is_measured_data"] is False

    # 2. Non-existent candidate site ID
    res_unknown_site = client.get("/api/sites/invalid_site_xyz")
    assert res_unknown_site.status_code == 404

    # 3. Duplicate site IDs in comparison request
    res_dup_compare = client.post("/api/sites/compare", json={"site_ids": ["site_a", "site_a"]})
    assert res_dup_compare.status_code == 422

    # 4. Unknown analysis ID in AI explainer
    res_unknown_ai = client.post("/api/ai/explain", json={"analysis_id": "ANL-FAKE-ID"})
    assert res_unknown_ai.status_code == 404

    # 5. Unknown analysis ID in Report generator
    res_unknown_report = client.post("/api/reports/generate", json={"analysis_id": "ANL-FAKE-ID", "format": "json"})
    assert res_unknown_report.status_code == 404

    # 6. Invalid radius (> 10000m) in spatial analysis
    res_huge_radius = client.post("/api/analysis/run", json={"center_lat": -89.44, "center_lon": 0.0, "radius_meters": 50000.0})
    assert res_huge_radius.status_code == 422
