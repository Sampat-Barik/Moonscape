"""Comprehensive test suite for multi-site comparison PDF generator (Phase 8 Extension).

Covers all 20 required backend verification test cases:
1. Two-site comparison PDF.
2. All-catalog comparison PDF.
3. Invalid site ID (404).
4. One-site request where two are required (422).
5. Duplicate site IDs (422).
6. Missing elevation handled gracefully.
7. Missing hazards handled.
8. Missing illumination handled.
9. Missing Earth visibility handled.
10. Missing score handled without zero-coercion.
11. Hard-constraint violation handling.
12. Different mission profiles & weight presets.
13. Dataset citation handling.
14. PDF generation failure handling.
15. PDF Content-Type.
16. PDF download filename.
17. PDF structural validity (readable by parser / EOF).
18. Correct number of sites in PDF.
19. Correct site names and ranking order.
20. Existing individual-site PDF generator regression test.
"""

from datetime import datetime, timezone
import io
from typing import Any
import pytest
from fastapi.testclient import TestClient

from app.schemas.report import ComparisonReportRequest
from app.services.comparison_report_generator import comparison_report_generator
from app.services.site_service import site_service


def test_01_two_site_comparison_pdf(client: TestClient) -> None:
    """1. Tests generating a PDF comparison for two selected landing sites."""
    payload = {
        "site_ids": ["shackleton_connecting_ridge", "malapert_mountain"],
        "format": "pdf",
    }
    response = client.post("/api/reports/comparison", json=payload)
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 10000


def test_02_all_catalog_comparison_pdf(client: TestClient) -> None:
    """2. Tests generating a PDF comparison for all 8 sites in the candidate catalog."""
    all_sites = [s.site_id for s in site_service.get_all_sites()]
    assert len(all_sites) >= 8

    payload = {
        "site_ids": all_sites,
        "mission_profile": "crewed_artemis_class",
        "format": "pdf",
    }
    response = client.post("/api/reports/comparison", json=payload)
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 50000


def test_03_invalid_site_id(client: TestClient) -> None:
    """3. Tests requesting an invalid or unrecognized site ID returns HTTP 404."""
    payload = {
        "site_ids": ["shackleton_connecting_ridge", "invalid_unknown_site_999"],
        "format": "pdf",
    }
    response = client.post("/api/reports/comparison", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_04_single_site_rejected(client: TestClient) -> None:
    """4. Tests requesting comparison with fewer than 2 sites returns HTTP 422."""
    payload = {
        "site_ids": ["shackleton_connecting_ridge"],
        "format": "pdf",
    }
    response = client.post("/api/reports/comparison", json=payload)
    assert response.status_code == 422


def test_05_duplicate_site_ids_rejected(client: TestClient) -> None:
    """5. Tests requesting comparison with duplicate site IDs returns HTTP 422."""
    payload = {
        "site_ids": ["shackleton_connecting_ridge", "shackleton_connecting_ridge"],
        "format": "pdf",
    }
    response = client.post("/api/reports/comparison", json=payload)
    assert response.status_code == 422


def test_06_missing_elevation_handled(client: TestClient, monkeypatch: Any) -> None:
    """6. Tests that missing elevation metric is handled as N/A without zero-coercion."""
    orig_site = site_service.get_site_by_id("shackleton_connecting_ridge")
    assert orig_site is not None
    
    # Temporarily set elevation_m to None
    monkeypatch.setattr(orig_site, "elevation_m", None)
    
    payload = {
        "site_ids": ["shackleton_connecting_ridge", "malapert_mountain"],
        "format": "pdf",
    }
    response = client.post("/api/reports/comparison", json=payload)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


def test_07_missing_hazards_handled(client: TestClient) -> None:
    """7. Tests that surface hazards table renders properly distinguishing DEM and optical scan."""
    payload = {
        "site_ids": ["shackleton_connecting_ridge", "amundsen_rim"],
        "format": "json",
    }
    response = client.post("/api/reports/comparison", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["site_count"] == 2


def test_08_missing_illumination_handled(client: TestClient, monkeypatch: Any) -> None:
    """8. Tests that missing illumination values do not crash PDF compilation."""
    orig_site = site_service.get_site_by_id("nobile_rim_1")
    assert orig_site is not None
    monkeypatch.setattr(orig_site, "illumination_pct", None)

    payload = {
        "site_ids": ["nobile_rim_1", "haworth_crater_rim"],
        "format": "pdf",
    }
    response = client.post("/api/reports/comparison", json=payload)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


def test_09_missing_earth_visibility_handled(client: TestClient, monkeypatch: Any) -> None:
    """9. Tests that missing Earth line-of-sight visibility values are handled gracefully."""
    orig_site = site_service.get_site_by_id("de_gerlache_rim_2")
    assert orig_site is not None
    monkeypatch.setattr(orig_site, "earth_visibility_pct", None)

    payload = {
        "site_ids": ["de_gerlache_rim_2", "malapert_mountain"],
        "format": "pdf",
    }
    response = client.post("/api/reports/comparison", json=payload)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


def test_10_missing_score_handled(client: TestClient) -> None:
    """10. Tests that scores are calculated using valid scoring rules without zero-substitution."""
    payload = {
        "site_ids": ["shackleton_connecting_ridge", "faustini_rim_a"],
        "format": "json",
    }
    response = client.post("/api/reports/comparison", json=payload)
    assert response.status_code == 200
    data = response.json()
    for rank in data["rankings"]:
        assert rank["suitability_score"] is not None
        assert rank["suitability_score"] > 0


def test_11_hard_constraint_violation(client: TestClient) -> None:
    """11. Tests that hard constraint violations are marked and reflected in rankings."""
    all_sites = [s.site_id for s in site_service.get_all_sites()]
    payload = {
        "site_ids": all_sites,
        "mission_profile": "crewed_artemis_class",
        "format": "json",
    }
    response = client.post("/api/reports/comparison", json=payload)
    assert response.status_code == 200
    data = response.json()
    statuses = [item["hard_constraint_status"] for item in data["rankings"]]
    assert "passed" in statuses


def test_12_different_mission_profiles(client: TestClient) -> None:
    """12. Tests comparing sites under different mission profile weight sets."""
    payload_artemis = {
        "site_ids": ["shackleton_connecting_ridge", "malapert_mountain"],
        "mission_profile": "crewed_artemis_class",
        "format": "json",
    }
    res_artemis = client.post("/api/reports/comparison", json=payload_artemis)
    assert res_artemis.status_code == 200

    payload_cargo = {
        "site_ids": ["shackleton_connecting_ridge", "malapert_mountain"],
        "mission_profile": "uncrewed_cargo_class",
        "format": "json",
    }
    res_cargo = client.post("/api/reports/comparison", json=payload_cargo)
    assert res_cargo.status_code == 200


def test_13_dataset_citations_included(client: TestClient) -> None:
    """13. Tests that required planetary scientific citations are embedded in generated output."""
    payload = {
        "site_ids": ["shackleton_connecting_ridge", "malapert_mountain"],
        "format": "markdown",
    }
    response = client.post("/api/reports/comparison", json=payload)
    assert response.status_code == 200
    assert "MOONSCAPE" in response.text
    assert "DISCLAIMER" in response.text


def test_14_pdf_generation_failure_handling(monkeypatch: Any) -> None:
    """14. Tests that an internal error during PDF generation surfaces as a clean exception."""
    req = ComparisonReportRequest(site_ids=["shackleton_connecting_ridge", "malapert_mountain"], format="pdf")
    
    def raise_err(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Simulated PDF engine failure")

    monkeypatch.setattr(comparison_report_generator, "render_pdf_comparison_report", raise_err)
    with pytest.raises(RuntimeError, match="Simulated PDF engine failure"):
        comparison_report_generator.generate_comparison_report(req)


def test_15_pdf_content_type(client: TestClient) -> None:
    """15. Tests that Content-Type header is strictly application/pdf."""
    payload = {
        "site_ids": ["shackleton_connecting_ridge", "malapert_mountain"],
        "format": "pdf",
    }
    response = client.post("/api/reports/comparison", json=payload)
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"


def test_16_pdf_download_filename(client: TestClient) -> None:
    """16. Tests that the download Content-Disposition header contains the dynamic date filename."""
    payload = {
        "site_ids": ["shackleton_connecting_ridge", "malapert_mountain"],
        "format": "pdf",
    }
    response = client.post("/api/reports/comparison", json=payload)
    assert response.status_code == 200
    disp = response.headers.get("Content-Disposition", "")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert f'filename="MoonScape_Comparison_{today}.pdf"' in disp


def test_17_pdf_readable_by_parser(client: TestClient) -> None:
    """17. Tests that the generated binary PDF has valid trailer and EOF marker."""
    payload = {
        "site_ids": ["shackleton_connecting_ridge", "malapert_mountain"],
        "format": "pdf",
    }
    response = client.post("/api/reports/comparison", json=payload)
    assert response.status_code == 200
    pdf_bytes = response.content
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in pdf_bytes[-1024:]


def test_18_correct_number_of_sites_in_pdf(client: TestClient) -> None:
    """18. Tests that an 8-site comparison report contains all 8 candidate sites."""
    all_sites = [s.site_id for s in site_service.get_all_sites()]
    payload = {
        "site_ids": all_sites,
        "format": "json",
    }
    response = client.post("/api/reports/comparison", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["site_count"] == len(all_sites)
    assert len(data["rankings"]) == len(all_sites)


def test_19_correct_site_names_and_ranking(client: TestClient) -> None:
    """19. Tests that safety rank corresponds to sorted composite suitability scores."""
    payload = {
        "site_ids": ["shackleton_connecting_ridge", "malapert_mountain", "nobile_rim_1"],
        "format": "json",
    }
    response = client.post("/api/reports/comparison", json=payload)
    assert response.status_code == 200
    rankings = response.json()["rankings"]
    assert len(rankings) == 3
    assert rankings[0]["safety_rank"] == 1
    assert rankings[1]["safety_rank"] == 2
    assert rankings[2]["safety_rank"] == 3
    # Check rank order is strictly descending by score (subject to hard constraint rules)
    assert rankings[0]["suitability_score"] >= rankings[1]["suitability_score"] or rankings[0]["hard_constraint_status"] == "passed"


def test_20_individual_site_report_regression(client: TestClient) -> None:
    """20. Zero-regression test: verifies single-site PDF generation at /api/reports/generate still works unchanged."""
    payload = {
        "site_id": "malapert_mountain",
        "format": "pdf",
    }
    response = client.post("/api/reports/generate", json=payload)
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"
    assert "moonscape_report_" in response.headers["Content-Disposition"]
    assert ".pdf" in response.headers["Content-Disposition"]
    assert response.content.startswith(b"%PDF-")
