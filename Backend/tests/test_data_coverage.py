"""Tests for spatial data coverage evaluation and data management API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_management.coverage_manager import coverage_manager

client = TestClient(app)


def test_coverage_south_pole_point():
    """Verify spatial coverage report for a point in Shackleton Connecting Ridge."""
    report = coverage_manager.get_coverage_report(lat_deg=-89.5, lon_deg=220.0)
    assert report["valid_coordinate"] is True
    assert report["in_south_pole_zone"] is True
    assert len(report["layers"]) >= 5

    # Check Product 90
    p90 = next(l for l in report["layers"] if l["source_id"] == "pgda_product90")
    assert p90["covers"] is True

    # Check Product 78 Site 01
    p78 = next(l for l in report["layers"] if l["source_id"] == "pgda_product78")
    assert p78["covers"] is True


def test_coverage_outside_south_pole():
    """Verify coverage report correctly identifies points outside polar disk."""
    report = coverage_manager.get_coverage_report(lat_deg=-50.0, lon_deg=0.0)
    assert report["in_south_pole_zone"] is False


def test_api_data_catalog():
    """Verify GET /api/data/catalog returns complete dataset catalog."""
    resp = client.get("/api/data/catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_datasets"] >= 6
    assert "profiles" in data
    assert "profile_b" in data["profiles"]
    assert len(data["datasets"]) >= 6


def test_api_data_status():
    """Verify GET /api/data/status returns status for all datasets."""
    resp = client.get("/api/data/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "pgda90_ldem" in data
    assert "status" in data["pgda90_ldem"]
    assert "size_mb" in data["pgda90_ldem"]


def test_api_data_coverage_endpoint():
    """Verify GET /api/data/coverage endpoint returns structured response."""
    resp = client.get("/api/data/coverage?lat=-89.5&lon=220.0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid_coordinate"] is True
    assert data["in_south_pole_zone"] is True
    assert len(data["layers"]) >= 5
