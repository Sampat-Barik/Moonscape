"""Tests for mission landing-site report generation endpoint."""

from fastapi.testclient import TestClient


def test_generate_report_markdown(client: TestClient) -> None:
    """Tests POST /api/reports/generate compiles Markdown formatted report."""
    payload = {
        "site_id": "malapert_mountain",
        "mission_title": "Artemis III Base Camp Staging Assessment",
        "output_format": "markdown",
        "include_ai_narrative": True,
    }
    response = client.post("/api/reports/generate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["report_id"].startswith("RPT-")
    assert data["site_name"] == "Malapert Mountain (Alpha)"
    assert data["output_format"] == "markdown"
    assert "# Artemis III Base Camp Staging Assessment" in data["content"]
    assert "Suitability Scoring" in data["content"]
    assert "DISCLAIMER" in data["disclaimer"]


def test_generate_report_json(client: TestClient) -> None:
    """Tests POST /api/reports/generate compiles JSON format report."""
    payload = {
        "site_id": "nobile_rim_1",
        "output_format": "json",
    }
    response = client.post("/api/reports/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["output_format"] == "json"
    assert "site_metadata" in data["content"]


def test_generate_report_html(client: TestClient) -> None:
    """Tests POST /api/reports/generate compiles styled HTML report."""
    payload = {
        "site_id": "shackleton_connecting_ridge",
        "output_format": "html",
    }
    response = client.post("/api/reports/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "<!DOCTYPE html>" in data["content"]
    assert "Shackleton" in data["content"]


def test_generate_report_invalid_site(client: TestClient) -> None:
    """Tests POST /api/reports/generate with unknown site returns 404."""
    payload = {
        "site_id": "unknown_lunar_site_999",
    }
    response = client.post("/api/reports/generate", json=payload)
    assert response.status_code == 404
