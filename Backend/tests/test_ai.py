"""Tests for AI scientific explanation endpoint."""

from fastapi.testclient import TestClient


def test_ai_explain_catalog_site(client: TestClient) -> None:
    """Tests POST /api/ai/explain generates thorough scientific rationale for a candidate landing site."""
    payload = {
        "site_id": "shackleton_connecting_ridge",
        "focus_topics": ["topography", "thermal", "traverse"],
    }
    response = client.post("/api/ai/explain", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["explanation_id"].startswith("EXP-")
    assert "Shackleton" in data["target_site"]
    assert len(data["executive_summary"]) > 50
    assert len(data["geomorphology_assessment"]) > 50
    assert len(data["thermal_and_power_assessment"]) > 50
    assert len(data["key_engineering_tradeoffs"]) >= 2
    assert len(data["mitigation_strategies"]) >= 2
    assert "DISCLAIMER" in data["disclaimer"]
