"""Tests for candidate landing sites and site comparison endpoints."""

from fastapi.testclient import TestClient


def test_list_sites(client: TestClient) -> None:
    """Tests GET /api/sites returns complete catalog of Artemis candidate regions."""
    response = client.get("/api/sites")
    assert response.status_code == 200
    sites = response.json()
    assert isinstance(sites, list)
    assert len(sites) >= 5

    # Verify site structure
    shackleton = next((s for s in sites if s["site_id"] == "shackleton_connecting_ridge"), None)
    assert shackleton is not None
    assert shackleton["latitude"] <= -80.0
    assert shackleton["target_mission"] == "Artemis III"
    assert "Shackleton" in shackleton["name"]


def test_get_site_by_id(client: TestClient) -> None:
    """Tests GET /api/sites/{site_id} returns accurate site details."""
    response = client.get("/api/sites/malapert_mountain")
    assert response.status_code == 200
    site = response.json()
    assert site["site_id"] == "malapert_mountain"
    assert site["latitude"] == -84.90
    assert site["longitude"] == 12.90
    assert site["earth_visibility_pct"] > 80.0


def test_get_site_not_found(client: TestClient) -> None:
    """Tests GET /api/sites/{site_id} with invalid slug returns HTTP 404."""
    response = client.get("/api/sites/non_existent_site")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_compare_sites_success(client: TestClient) -> None:
    """Tests POST /api/sites/compare calculates comparative ranking."""
    payload = {
        "site_ids": ["shackleton_connecting_ridge", "malapert_mountain", "nobile_rim_1"],
        "weights": {
            "slope": 0.4,
            "illumination": 0.3,
            "communication": 0.2,
            "science": 0.1,
        },
    }
    response = client.post("/api/sites/compare", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert len(data["compared_sites"]) == 3
    assert data["top_recommended_site_id"] in payload["site_ids"]
    assert "tradeoff_summary" in data
    assert "DISCLAIMER" in data["disclaimer"]

    # Verify rankings are strictly ordered
    ranks = [s["safety_rank"] for s in data["compared_sites"]]
    assert ranks == [1, 2, 3]


def test_compare_sites_invalid_site_id(client: TestClient) -> None:
    """Tests POST /api/sites/compare with unknown site returns HTTP 404."""
    payload = {
        "site_ids": ["shackleton_connecting_ridge", "invalid_site_xyz"],
    }
    response = client.post("/api/sites/compare", json=payload)
    assert response.status_code == 404


def test_compare_sites_duplicate_id(client: TestClient) -> None:
    """Tests POST /api/sites/compare with duplicate site IDs triggers validation error."""
    payload = {
        "site_ids": ["shackleton_connecting_ridge", "shackleton_connecting_ridge"],
    }
    response = client.post("/api/sites/compare", json=payload)
    assert response.status_code == 422
