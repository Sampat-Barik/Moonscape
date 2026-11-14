"""Tests for system health endpoint."""

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    """Tests GET /api/health returns healthy operational status and metadata."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["version"] == "1.0.0"
    assert data["crs"] == "ESRI:104903"
    assert data["sites_loaded"] > 0
    assert data["dem_dataset_loaded"] is True
    assert "DISCLAIMER" in data["disclaimer"]


def test_root_endpoint(client: TestClient) -> None:
    """Tests GET / returns API base and documentation link."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Moonscape Backend"
    assert data["api_documentation"] == "/docs"
