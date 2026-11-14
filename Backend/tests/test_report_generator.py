"""Automated test suite for Moonscape Scientific Report Generator (Phase 8)."""

from fastapi.testclient import TestClient

from app.schemas.analysis import (
    AnalysisRunResponse,
    SlopeDistribution,
    TopographicStats,
)
from app.schemas.report import ReportGenerateRequest
from app.services.analysis_store import analysis_store
from app.services.report_generator import report_generator


def test_generate_report_with_analysis_id_json(client: TestClient) -> None:
    """Tests POST /api/reports/generate returns a complete 19-element scientific report in JSON format."""
    payload = {
        "analysis_id": "analysis_001",
        "format": "json",
    }
    response = client.post("/api/reports/generate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["report_id"].startswith("RPT-")
    assert data["analysis_id"] == "analysis_001"
    assert data["output_format"] == "json"
    assert "DISCLAIMER" in data["disclaimer"]

    # Verify structured report data contains all 19 mandated elements
    report = data["report_data"]
    assert report is not None

    # 1. Report title and generation date
    assert "Moonscape" in report["title"]
    assert "UTC" in report["generated_at_human"]

    # 2. Analysis ID
    assert report["analysis_id"] == "analysis_001"

    # 3. Selected lunar coordinates
    coords = report["coordinates"]
    assert coords["latitude"] == -89.44
    assert coords["longitude"] == 222.5
    assert "89.4400° S" in coords["formatted"]

    # 4. Analysis radius
    assert report["analysis_radius_meters"] == 1000.0

    # 5. Elevation measurements
    elev = report["elevation"]
    assert elev["mean_m"] == -120.0
    assert elev["min_m"] == -210.0
    assert elev["max_m"] == 15.0
    assert elev["relief_variation_m"] == 225.0
    assert elev["units"] == "meters"

    # 6. Slope measurements
    slope = report["slope"]
    assert slope["mean_deg"] == 6.8
    assert slope["max_deg"] == 14.5
    assert "Horn" in slope["operator"]
    assert slope["ideal_pct"] == 62.5
    assert slope["critical_hazardous_pct"] == 1.8

    # 7. Roughness measurements
    rough = report["roughness"]
    assert rough["mean_rms_m"] == 0.12
    assert rough["max_rms_m"] == 0.38
    assert rough["baseline_meters"] == 15.0
    assert rough["safe_touchdown_fraction_pct"] == 91.0

    # 8. Illumination information
    illum = report["illumination"]
    assert illum["status"] == "available"
    assert illum["cumulative_illumination_pct"] == 86.4
    assert illum["is_permanently_shadowed_region"] is False
    assert illum["estimated_surface_temp_k"] == 185.0
    assert "thermal" in illum["thermal_caveat"].lower()

    # 9. Crater and rock detection results
    hazards = report["hazards"]
    assert "hazard_status" in hazards
    assert "calibration_notice" in hazards

    # 10. Preliminary suitability score
    suit = report["suitability"]
    assert suit["overall_score"] == 83.25
    assert suit["category"] == "Higher preliminary suitability"
    assert suit["score_coverage_pct"] == 80.0

    # 11. Factor breakdown
    breakdown = report["factor_breakdown"]
    assert isinstance(breakdown, list)
    assert len(breakdown) >= 4

    # 12. Positive factors
    assert len(report["positive_factors"]) >= 2

    # 13. Risk factors
    assert len(report["risk_factors"]) >= 2

    # 14. Data sources
    assert "dataset_name" in report["data_sources"]

    # 15. Methodology
    methodology = report["methodology"]
    assert "Horn" in methodology["topographic_slope"]
    assert "RMS" in methodology["surface_roughness"]
    assert "MCDA" in methodology["multi_criteria_scoring"]

    # 16. Missing data
    assert "missing_data" in report
    assert isinstance(report["missing_data"], list)

    # 17. Uncertainty
    assert report["uncertainty"]["vertical_accuracy_m"] == 1.0

    # 18. Limitations
    assert len(report["limitations"]) >= 2
    assert any("preliminary" in lim.lower() for lim in report["limitations"])

    # 19. Final preliminary conclusion
    assert len(report["conclusion"]) > 30


def test_generate_report_pdf_download(client: TestClient) -> None:
    """Tests POST /api/reports/generate with format='pdf' returns a downloadable PDF stream."""
    payload = {
        "analysis_id": "analysis_001",
        "format": "pdf",
    }
    response = client.post("/api/reports/generate", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert "moonscape_report_analysis_001.pdf" in response.headers["content-disposition"]

    # Validate authentic PDF magic bytes
    pdf_bytes = response.content
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 2000  # Multi-section document


def test_generate_report_missing_analysis_404(client: TestClient) -> None:
    """Tests querying a non-existent analysis ID returns a 404 status code."""
    payload = {
        "analysis_id": "ANL-DOES-NOT-EXIST",
        "format": "json",
    }
    response = client.post("/api/reports/generate", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_generate_report_empty_request_422_or_400(client: TestClient) -> None:
    """Tests empty payload returns validation error."""
    payload = {}
    response = client.post("/api/reports/generate", json=payload)
    assert response.status_code == 422  # Pydantic validation failure on missing required fields


def test_generate_report_partial_measurements(client: TestClient) -> None:
    """Tests generating a report when some scientific measurements (e.g. slope, illumination) are missing."""
    partial_analysis = AnalysisRunResponse(
        analysis_id="ANL-PARTIAL-001",
        center_lat=-89.80,
        center_lon=0.0,
        radius_meters=500.0,
        total_samples=1000,
        valid_samples=1000,
        nodata_samples=0,
        elevation=TopographicStats(
            min_value=-50.0,
            max_value=50.0,
            mean_value=0.0,
            units="meters",
        ),
        slope=TopographicStats(
            min_value=None,
            max_value=None,
            mean_value=None,
            units="degrees",
        ),
        slope_distribution=SlopeDistribution(
            ideal_pct=0.0,
            acceptable_pct=0.0,
            marginal_pct=0.0,
            critical_hazardous_pct=0.0,
        ),
        roughness_mean_m=0.18,
        safe_touchdown_fraction_pct=50.0,
        preliminary_feasibility="insufficient_data",
        dataset_metadata={"dataset_name": "Partial Sample DEM"},
        disclaimer="Preliminary",
        illumination=None,  # Missing illumination
        suitability=None,   # Missing suitability
    )
    analysis_store.save(partial_analysis)

    # Generate JSON
    res_json = client.post("/api/reports/generate", json={"analysis_id": "ANL-PARTIAL-001", "format": "json"})
    assert res_json.status_code == 200
    data = res_json.json()
    assert data["report_data"]["slope"]["mean_deg"] is None
    assert data["report_data"]["illumination"]["status"] == "unavailable"
    assert data["report_data"]["suitability"]["category"] == "Insufficient data"

    # Generate PDF with missing data
    res_pdf = client.post("/api/reports/generate", json={"analysis_id": "ANL-PARTIAL-001", "format": "pdf"})
    assert res_pdf.status_code == 200
    assert res_pdf.content.startswith(b"%PDF-")


def test_generate_report_dynamic_workflow(client: TestClient) -> None:
    """End-to-end integration: run POST /api/analysis/run then compile full report from generated ID."""
    analysis_req = {
        "center_lat": -89.46,
        "center_lon": 222.00,
        "radius_meters": 1000.0,
        "max_acceptable_slope_deg": 10.0,
        "max_acceptable_roughness_m": 0.5,
    }
    analysis_res = client.post("/api/analysis/run", json=analysis_req)
    assert analysis_res.status_code == 200
    generated_id = analysis_res.json()["analysis_id"]

    # 1. Compile JSON report
    rep_res = client.post("/api/reports/generate", json={"analysis_id": generated_id, "format": "json"})
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert rep_data["analysis_id"] == generated_id
    assert rep_data["report_data"]["elevation"]["mean_m"] is not None

    # 2. Compile PDF report
    rep_pdf = client.post("/api/reports/generate", json={"analysis_id": generated_id, "format": "pdf"})
    assert rep_pdf.status_code == 200
    assert rep_pdf.content.startswith(b"%PDF-")
    assert len(rep_pdf.content) > 2000
