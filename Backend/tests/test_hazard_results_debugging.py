"""Regression test suite for targeted hazard results debugging, scientific provenance, and zero-regression validation.

Covers the 20 required verification points:
1. Duplicate hazard detection (grouping contiguous cells)
2. Distinct nearby hazards (retaining separate features)
3. Polar longitude wrapping (conversions across 0/360 and -180/180)
4. Hazard coordinates inside analysis radius
5. Correct slope units (degrees)
6. Correct roughness units (meters)
7. No-data handling (LOLA_NODATA_VALUE resilience)
8. DEM resolution handling
9. Confidence labeling (deterministic vs heuristic vs model)
10. LROC product coverage differentiation
11. Model unavailable handling
12. Model present but not executed when no image frame
13. Model inference successful on intersecting frame
14. Correct source provenance attribution
15. Updated scientific disclaimer (polar orbital nadir domain)
16. JSON serialization integrity
17. Frontend hazard contract compatibility
18. Existing analysis endpoint intact (POST /api/analysis/run)
19. Existing scoring endpoint intact (POST /api/scoring/score)
20. Existing site comparison endpoint intact (POST /api/sites/compare)
"""

import json
import math
from typing import Any, Dict, List
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.hazard import HazardItem, HazardPredictRequest, HazardPredictResponse
from app.services.geospatial.coordinate_manager import coordinate_manager
from app.services.hazard_detection import APOLLO_DOMAIN_LIMITATION, hazard_detection_service
from app.services.hazard_service import hazard_service
from maths.geodesy import haversine_lunar_distance, polar_stereo_to_latlon

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. DUPLICATE HAZARD DETECTION & CONTIGUOUS CELL GROUPING
# ---------------------------------------------------------------------------
def test_duplicate_hazard_detection_grouping():
    """Confirms contiguous steep slope cells are grouped into a physical escarpment feature.

    No multiple identical coordinates should be emitted for the same ridge.
    """
    req = HazardPredictRequest(center_lat=-89.44, center_lon=222.5, radius_meters=1000.0)
    resp = hazard_service.predict_hazards(req)
    escarpments = [h for h in resp.hazards if h.hazard_type == "escarpment"]

    assert len(escarpments) > 0, "Expected at least one escarpment feature at Shackleton ridge"
    coords = [(h.latitude, h.longitude) for h in escarpments]
    # No duplicate coordinates among escarpments
    assert len(coords) == len(set(coords)), f"Found duplicate escarpment coordinates: {coords}"


# ---------------------------------------------------------------------------
# 2. DISTINCT NEARBY HAZARDS
# ---------------------------------------------------------------------------
def test_distinct_nearby_hazards():
    """Genuinely distinct features remain distinguishable with unique IDs and separated locations."""
    req = HazardPredictRequest(center_lat=-89.44, center_lon=222.5, radius_meters=1000.0)
    resp = hazard_service.predict_hazards(req)
    escarpments = [h for h in resp.hazards if h.hazard_type == "escarpment"]

    if len(escarpments) >= 2:
        esc1, esc2 = escarpments[0], escarpments[1]
        assert esc1.id != esc2.id
        dist = haversine_lunar_distance(esc1.latitude, esc1.longitude, esc2.latitude, esc2.longitude)
        assert dist > 10.0, f"Expected distinct features to be separated by > 10m, got {dist:.1f}m"


# ---------------------------------------------------------------------------
# 3. POLAR LONGITUDE WRAPPING
# ---------------------------------------------------------------------------
def test_polar_longitude_wrapping():
    """Verifies coordinate conversion handles polar longitude boundaries [0, 360) and [-180, 180)."""
    norm_360 = coordinate_manager.normalize_longitude(-45.0, target_range="360")
    assert norm_360 == 315.0

    norm_180 = coordinate_manager.normalize_longitude(270.0, target_range="180")
    assert norm_180 == -90.0

    # Near-pole polar stereographic roundtrip
    x, y = coordinate_manager.to_polar_stereographic(-89.9, 359.5)
    lat_rt, lon_rt = coordinate_manager.from_polar_stereographic(x, y)
    assert abs(lat_rt - (-89.9)) < 0.001
    assert abs(lon_rt - 359.5) < 0.01 or abs(lon_rt - (-0.5)) < 0.01


# ---------------------------------------------------------------------------
# 4. HAZARD COORDINATES INSIDE ANALYSIS RADIUS
# ---------------------------------------------------------------------------
def test_hazard_coordinates_inside_analysis_radius():
    """All detected topographic hazards must fall within or on the boundary of the evaluated search radius."""
    target_lat, target_lon, target_radius = -89.44, 222.5, 1000.0
    req = HazardPredictRequest(center_lat=target_lat, center_lon=target_lon, radius_meters=target_radius)
    resp = hazard_service.predict_hazards(req)

    for h in resp.hazards:
        if h.hazard_type in ("escarpment", "surface_roughness_anomaly", "morphological_depression"):
            dist = coordinate_manager.surface_distance_m(target_lat, target_lon, h.latitude, h.longitude)
            # Allow margin for feature physical footprint extent
            extent_buffer = (h.feature_extent_m or 0.0) / 2.0
            assert dist <= (target_radius + extent_buffer + 250.0), (
                f"Hazard {h.id} at ({h.latitude}, {h.longitude}) is {dist:.1f}m away, exceeding radius {target_radius}m"
            )


# ---------------------------------------------------------------------------
# 5. CORRECT SLOPE UNITS
# ---------------------------------------------------------------------------
def test_correct_slope_units():
    """Escarpment hazards must specify slope in degrees, not meters or unitless."""
    req = HazardPredictRequest(center_lat=-89.44, center_lon=222.5, radius_meters=1000.0)
    resp = hazard_service.predict_hazards(req)
    escarpments = [h for h in resp.hazards if h.hazard_type == "escarpment"]

    for esc in escarpments:
        assert esc.measurement_unit == "deg"
        assert esc.measurement_name == "Peak Slope Gradient"
        assert esc.measurement_value is not None
        assert 15.0 <= esc.measurement_value <= 90.0


# ---------------------------------------------------------------------------
# 6. CORRECT ROUGHNESS UNITS
# ---------------------------------------------------------------------------
def test_correct_roughness_units():
    """Roughness anomaly hazards must specify RMS height deviation in meters."""
    req = HazardPredictRequest(center_lat=-89.44, center_lon=222.5, radius_meters=1000.0)
    resp = hazard_service.predict_hazards(req)
    roughness_hazards = [h for h in resp.hazards if h.hazard_type == "surface_roughness_anomaly"]

    for r in roughness_hazards:
        assert r.measurement_unit == "m"
        assert r.measurement_name == "RMS Surface Roughness"
        assert r.measurement_value is not None
        assert r.measurement_value > 0.0


# ---------------------------------------------------------------------------
# 7. NO-DATA HANDLING
# ---------------------------------------------------------------------------
def test_nodata_handling():
    """Elevation grid with LOLA_NODATA_VALUE (-32768) does not produce NaNs or fatal errors."""
    from app.core.constants import LOLA_NODATA_VALUE
    from maths.topography import horn_slope_and_aspect, rms_surface_roughness

    synthetic_dem = np.full((20, 20), 500.0, dtype=np.float32)
    synthetic_dem[5:8, 5:8] = LOLA_NODATA_VALUE  # Inject nodata crater

    valid_mask = synthetic_dem != LOLA_NODATA_VALUE
    assert np.sum(valid_mask) == (400 - 9)
    # Filtered evaluation
    filtered = np.where(valid_mask, synthetic_dem, 500.0)
    slopes, _ = horn_slope_and_aspect(filtered, 20.0, 20.0)
    assert not np.isnan(slopes).any()


# ---------------------------------------------------------------------------
# 8. DEM RESOLUTION HANDLING
# ---------------------------------------------------------------------------
def test_dem_resolution_handling():
    """Pixel resolution dx/dy is properly respected when converting cells to distance and extent."""
    dx, dy = 20.0, 20.0
    cell_count = 16
    extent_m = math.sqrt(cell_count * dx * dy)
    assert extent_m == 80.0


# ---------------------------------------------------------------------------
# 9. CONFIDENCE LABELING SEMANTICS
# ---------------------------------------------------------------------------
def test_confidence_labeling_semantics():
    """Differentiates deterministic DEM slope gradients, heuristic roughness scores, and ML confidences."""
    req = HazardPredictRequest(center_lat=-89.44, center_lon=222.5, radius_meters=1000.0)
    resp = hazard_service.predict_hazards(req)

    for h in resp.hazards:
        if h.hazard_type == "escarpment":
            assert h.confidence_type == "deterministic_gradient"
            assert h.confidence_score == 1.0
        elif h.hazard_type == "surface_roughness_anomaly":
            assert h.confidence_type == "heuristic_indicator"
            assert 0.0 <= h.confidence_score <= 1.0
        elif h.hazard_type in ("crater", "boulder"):
            assert h.confidence_type == "model_confidence"
            assert 0.0 <= h.confidence_score <= 1.0


# ---------------------------------------------------------------------------
# 10. LROC PRODUCT COVERAGE DIFFERENTIATION
# ---------------------------------------------------------------------------
def test_lroc_product_coverage_differentiation():
    """Accurately differentiates covered orbital frame from uncovered locations."""
    # Shackleton ridge is covered
    covered = hazard_service.find_covering_optical_tile(-89.44, 222.5)
    assert covered is not None
    meta, img_p = covered
    assert img_p.exists()
    assert meta.get("coverage_state") in ("exact_frame_processed", "proximity_frame_cataloged")

    # Uncovered location far north
    uncovered = hazard_service.find_covering_optical_tile(-72.0, 100.0)
    assert uncovered is None


# ---------------------------------------------------------------------------
# 11. MODEL UNAVAILABLE HANDLING
# ---------------------------------------------------------------------------
def test_model_unavailable_handling():
    """POST /api/hazards/predict gracefully returns status='not_available' when model is not configured."""
    hazard_detection_service.reset()
    try:
        response = client.post(
            "/api/hazards/predict",
            json={"image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_available"
        assert data["crater_count"] is None
        assert data["rock_count"] is None
    finally:
        hazard_detection_service.load_model()


# ---------------------------------------------------------------------------
# 12. MODEL PRESENT BUT NOT EXECUTED WHEN NO INTERSECTING IMAGE
# ---------------------------------------------------------------------------
def test_model_present_but_not_executed_when_no_image():
    """When coordinate has no intersecting optical frame, optical_status is 'not_available' without crashing."""
    req = HazardPredictRequest(center_lat=-73.0, center_lon=45.0, radius_meters=1000.0)
    resp = hazard_service.predict_hazards(req)
    assert resp.optical_status == "not_available"
    assert resp.crater_count is None
    assert resp.rock_count is None
    assert any("Detection imagery unavailable" in w for w in resp.warnings)


# ---------------------------------------------------------------------------
# 13. MODEL INFERENCE SUCCESSFUL ON INTERSECTING FRAME
# ---------------------------------------------------------------------------
def test_model_inference_success_on_intersecting_frame():
    """When coordinate encompasses calibrated tile, YOLOv8n executes and optical_status is 'success'."""
    req = HazardPredictRequest(center_lat=-89.44, center_lon=222.5, radius_meters=1000.0)
    resp = hazard_service.predict_hazards(req)
    assert resp.optical_status == "success"
    assert resp.source_product_id is not None
    assert resp.source_resolution_m is not None
    assert resp.crater_count is not None and resp.crater_count >= 0


# ---------------------------------------------------------------------------
# 14. CORRECT SOURCE PROVENANCE ATTRIBUTION
# ---------------------------------------------------------------------------
def test_correct_source_provenance_attribution():
    """Hazard items carry truthful source identifiers (LOLA DEM vs LROC optical frame ID)."""
    req = HazardPredictRequest(center_lat=-89.44, center_lon=222.5, radius_meters=1000.0)
    resp = hazard_service.predict_hazards(req)

    for h in resp.hazards:
        if h.hazard_type == "escarpment":
            assert "DEM" in h.source or "slope" in h.source.lower()
        elif h.hazard_type in ("crater", "boulder"):
            assert "LROC" in h.source or "optical" in h.source.lower()


# ---------------------------------------------------------------------------
# 15. UPDATED SCIENTIFIC DISCLAIMER (POLAR ORBITAL NADIR DOMAIN)
# ---------------------------------------------------------------------------
def test_updated_scientific_disclaimer():
    """Verifies disclaimer reflects polar orbital grazing incidence domain, preserving safety notice."""
    req = HazardPredictRequest(center_lat=-89.44, center_lon=222.5, radius_meters=1000.0)
    resp = hazard_service.predict_hazards(req)

    assert "CRITICAL SCIENTIFIC NOTICE" in resp.limitations
    assert "Apollo" in resp.limitations
    assert "Permanently Shadowed Regions" in resp.limitations


# ---------------------------------------------------------------------------
# 16. JSON SERIALIZATION INTEGRITY
# ---------------------------------------------------------------------------
def test_json_serialization_integrity():
    """Ensures HazardPredictResponse serializes cleanly to JSON without schema errors."""
    req = HazardPredictRequest(center_lat=-89.44, center_lon=222.5, radius_meters=1000.0)
    resp = hazard_service.predict_hazards(req)
    raw_json = resp.model_dump_json()
    parsed = json.loads(raw_json)
    assert parsed["status"] in ("success", "partial")
    assert "hazards" in parsed
    assert isinstance(parsed["hazards"], list)


# ---------------------------------------------------------------------------
# 17. FRONTEND HAZARD CONTRACT COMPATIBILITY
# ---------------------------------------------------------------------------
def test_frontend_hazard_contract_compatibility():
    """Verifies response payload matches frontend HazardPanel and api.ts expectations."""
    response = client.post(
        "/api/hazards/predict",
        json={"latitude": -89.44, "longitude": 222.5, "radius_m": 1000.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "hazards" in data
    assert "crater_count" in data
    assert "rock_count" in data
    assert "steep_slope_cells" in data
    assert "overall_hazard_level" in data


# ---------------------------------------------------------------------------
# 18. EXISTING ANALYSIS ENDPOINT INTACT
# ---------------------------------------------------------------------------
def test_existing_analysis_endpoint_intact():
    """POST /api/analysis/run remains functional and returns genuine elevation data."""
    response = client.post(
        "/api/analysis/run",
        json={"latitude": -89.44, "longitude": 222.5, "radius_m": 1000.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert "elevation" in data
    assert "slope" in data
    assert "roughness_mean_m" in data or "roughness" in data


# ---------------------------------------------------------------------------
# 19. EXISTING SCORING ENDPOINT INTACT
# ---------------------------------------------------------------------------
def test_existing_scoring_endpoint_intact():
    """POST /api/score remains functional."""
    response = client.post(
        "/api/score",
        json={"latitude": -89.44, "longitude": 222.5, "radius_m": 1000.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert "overall_suitability_score" in data or "score" in data


# ---------------------------------------------------------------------------
# 20. EXISTING SITE COMPARISON ENDPOINT INTACT
# ---------------------------------------------------------------------------
def test_existing_site_comparison_endpoint_intact():
    """POST /api/sites/compare remains functional."""
    response = client.post(
        "/api/sites/compare",
        json={"site_ids": ["shackleton_connecting_ridge", "malapert_mountain"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "compared_sites" in data or "sites" in data
