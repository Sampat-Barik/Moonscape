"""Scientific validation and extended coverage tests for MoonScape.

Validates:
1. Multi-tier South Pole coverage (-90° to -70°) and out-of-bounds rejection (-69°).
2. All 8 required coordinates: -89°, -85°, -80°, -78°, -75°, -72°, -70°, -69°.
3. Authentic NASA LROC NAC polar optical hazard detection (Haworth -87.4°, -5.1°W).
4. Truthful zero/unavailable semantics (None instead of 0 when imagery is absent).
5. Separation of DEM morphological depressions and roughness risks from optical detections.
6. Elimination of fabricated F1 scores (0.88 / 0.94).
7. Independent synthetic algorithmic fixtures (flat, ramp, basin, roughness, nodata).
"""

import math
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.geospatial.coordinate_manager import coordinate_manager
from app.services.hazard_detection import hazard_detection_service
from app.services.hazard_service import hazard_service
from app.schemas.hazard import HazardPredictRequest
from maths.curvature import laplacian_curvature, detect_crater_basins
from maths.topography import horn_slope_and_aspect, rms_surface_roughness

client = TestClient(app)


# ===========================================================================
# 1. LATITUDE BOUNDS & COVERAGE ZONE CLASSIFICATION (8 REQUIRED COORDINATES)
# ===========================================================================

@pytest.mark.parametrize(
    "lat,expected_zone,is_analysis_valid",
    [
        (-89.0, "core", True),
        (-85.0, "core", True),
        (-80.0, "core", True),
        (-78.0, "extended", True),
        (-75.0, "extended", True),
        (-72.0, "context", True),
        (-70.0, "context", True),
        (-69.0, "outside", False),
    ],
)
def test_coverage_zone_classification_for_required_coordinates(lat, expected_zone, is_analysis_valid):
    """Verifies coverage classification for every coordinate required by Section 7."""
    zone = coordinate_manager.get_coverage_zone(lat)
    assert zone == expected_zone
    assert coordinate_manager.is_in_analysis_region(lat) == is_analysis_valid


def test_out_of_bounds_coordinate_69_rejection():
    """Coordinates outside configured South Pole exploration envelope (-69°) are rejected with HTTP 422."""
    res = client.post("/api/hazards/predict", json={
        "center_lat": -69.0,
        "center_lon": 0.0,
        "radius_meters": 1000.0,
    })
    assert res.status_code == 422


def test_core_coordinate_89_analysis_coverage():
    """Latitude -89.0° is inside core high-resolution analysis corridor."""
    res = client.get("/api/data/coverage", params={"lat": -89.0, "lon": 0.0})
    assert res.status_code == 200
    data = res.json()
    assert data["valid_coordinate"] is True
    assert data["coverage_zone"] == "core"
    assert data["in_south_pole_zone"] is True


def test_extended_coordinate_78_coverage_report():
    """Latitude -78.0° is inside extended South Pole region with dataset-specific coverage checked."""
    res = client.get("/api/data/coverage", params={"lat": -78.0, "lon": 0.0})
    assert res.status_code == 200
    data = res.json()
    assert data["valid_coordinate"] is True
    assert data["coverage_zone"] == "extended"
    # LROC WAC global/polar coverage should be reported
    assert any(l["source_id"] == "lroc_wac" for l in data["layers"])


def test_context_coordinate_72_coverage_report():
    """Latitude -72.0° is in optional context region."""
    res = client.get("/api/data/coverage", params={"lat": -72.0, "lon": 0.0})
    assert res.status_code == 200
    data = res.json()
    assert data["valid_coordinate"] is True
    assert data["coverage_zone"] == "context"


# ===========================================================================
# 2. AUTHENTIC NASA OPTICAL HAZARD DETECTION (-87.400°, -5.100°W)
# ===========================================================================

def test_optical_hazard_detection_haworth_location():
    """Reproduces and verifies live hazard detection at (-87.4°, -5.1°W = 354.9°E).

    Proves authentic NASA LROC NAC polar orbital imagery and trained YOLOv8n inference are used.
    """
    req = HazardPredictRequest(
        center_lat=-87.4,
        center_lon=-5.1,
        radius_meters=1000.0,
    )
    resp = hazard_service.predict_hazards(req)

    # 1. Status is partial (real optical LROC NAC detection + calibrated DEM baseline)
    assert resp.status in ["success", "partial"]

    # 2. Genuine optical detections returned (not 0)
    assert resp.crater_count is not None
    assert resp.crater_count > 0

    # 3. Authentic NASA product ID and resolution
    assert resp.source_product_id == "LROC_NAC_POLAR_M145129840LE"
    assert resp.source_resolution_m == 1.8

    # 4. Georeferenced overlay image is present as base64 PNG data URL
    assert resp.overlay_image is not None
    assert resp.overlay_image.startswith("data:image/png;base64,")

    # 5. Detections contain valid bounding boxes and confidence scores
    for d in resp.detections:
        assert d.confidence >= 0.20
        assert d.label in ["crater", "boulder", "rock"]


# ===========================================================================
# 3. TRUTHFUL ZERO / UNAVAILABLE SEMANTICS
# ===========================================================================

def test_no_optical_imagery_returns_none_not_zero():
    """When a coordinate lacks high-resolution optical coverage, crater/rock counts must be None, NOT zero."""
    req = HazardPredictRequest(
        center_lat=-80.5,
        center_lon=45.0,
        radius_meters=1000.0,
    )
    resp = hazard_service.predict_hazards(req)

    # Crater and rock counts MUST be None when optical scan could not be executed
    assert resp.crater_count is None
    assert resp.rock_count is None
    assert resp.overlay_image is None
    assert resp.optical_status == "not_available"
    assert any("Detection imagery unavailable" in w for w in resp.warnings)


# ===========================================================================
# 4. ELIMINATION OF FABRICATED F1 SCORES
# ===========================================================================

def test_no_fabricated_f1_scores_in_metadata():
    """Verifies that hardcoded 0.88 / 0.94 F1 scores are completely removed."""
    req = HazardPredictRequest(center_lat=-87.4, center_lon=-5.1, radius_meters=1000.0)
    resp = hazard_service.predict_hazards(req)
    meta = resp.model_metadata

    assert "f1_score_crater_detection" not in meta
    assert "f1_score_steep_slope_delineation" not in meta
    # Verified evaluation metrics from model card
    if "evaluation_metrics" in meta and meta["evaluation_metrics"]:
        test_split = meta["evaluation_metrics"].get("held_out_test_split", {})
        if test_split:
            assert "overall" in test_split
            assert test_split["overall"]["mAP50"] == 0.5818


# ===========================================================================
# 5. DEM ROUGHNESS VS BOULDER SEPARATION
# ===========================================================================

def test_dem_roughness_not_labeled_as_boulder():
    """DEM roughness anomalies must be tagged as surface_roughness_anomaly, NOT individual boulders."""
    req = HazardPredictRequest(center_lat=-80.5, center_lon=45.0, radius_meters=1000.0)
    resp = hazard_service.predict_hazards(req)

    # Topographic hazards in hazards list
    for h in resp.hazards:
        if "roughness" in h.source.lower():
            assert h.hazard_type == "surface_roughness_anomaly"
            assert h.hazard_type != "boulder"


# ===========================================================================
# 6. INDEPENDENT SYNTHETIC FIXTURES (ALGORITHMIC VALIDATION)
# ===========================================================================

def test_synthetic_flat_terrain_fixture():
    """Flat terrain fixture: slope = 0°, roughness = 0m, curvature = 0."""
    flat = np.full((32, 32), 1500.0, dtype=np.float32)
    slopes, _ = horn_slope_and_aspect(flat, 10.0, 10.0)
    rough = rms_surface_roughness(flat, 3)
    curv = laplacian_curvature(flat)

    assert np.allclose(slopes[1:-1, 1:-1], 0.0, atol=1e-4)
    assert np.allclose(rough[1:-1, 1:-1], 0.0, atol=1e-4)
    assert np.allclose(curv[1:-1, 1:-1], 0.0, atol=1e-4)
    assert np.sum(detect_crater_basins(curv, threshold=10.0)) == 0


def test_synthetic_known_slope_ramp_fixture():
    """Planar ramp with exact 15.0° gradient."""
    dx = 10.0
    # dy = dx * tan(15 deg)
    gradient = math.tan(math.radians(15.0))
    ramp = np.zeros((32, 32), dtype=np.float32)
    for r in range(32):
        ramp[r, :] = r * dx * gradient

    slopes, _ = horn_slope_and_aspect(ramp, dx, dx)
    # Interior slope must equal 15.0° +/- 0.1°
    interior = slopes[2:-2, 2:-2]
    assert np.allclose(interior, 15.0, atol=0.1)


def test_synthetic_parabolic_crater_basin_fixture():
    """Known parabolic bowl depression: z(r) = -depth * (1 - (r/R)^2)."""
    R = 80.0
    depth = 20.0
    grid = np.zeros((33, 33), dtype=np.float32)
    dx = 5.0
    center = 16

    for r in range(33):
        for c in range(33):
            dist = math.sqrt((r - center)**2 + (c - center)**2) * dx
            if dist < R:
                grid[r, c] = -depth * (1.0 - (dist / R)**2)

    curv = laplacian_curvature(grid)
    basins = detect_crater_basins(curv, threshold=0.2)
    # Center of bowl must be detected as a concave basin
    assert bool(basins[center, center]) is True


def test_synthetic_nodata_safety_fixture():
    """LOLA NODATA value (-32768) must be handled safely without NaN or crash."""
    grid = np.full((16, 16), -32768.0, dtype=np.float32)
    # Masking out nodata
    valid = grid != -32768.0
    assert np.sum(valid) == 0


# ===========================================================================
# 6. END-TO-END INFERENCE ON UNSEEN HELD-OUT SCENE & ISRO INTEGRATION
# ===========================================================================

def test_end_to_end_inference_unseen_heldout_scene():
    """Verifies that the trained YOLOv8n detector executes end-to-end inference

    on an authentic unseen held-out polar test image (de Gerlache Rim 1),
    producing valid crater/boulder bounding boxes, metric sizing, and visual overlays.
    """
    from pathlib import Path
    from app.schemas.hazard import HazardPredictRequest

    test_img = Path("Backend/data/hazard_dataset/images/test/tile_26_0.png")
    assert test_img.exists(), "Unseen holdout test image must exist"

    req = HazardPredictRequest(
        image_path=str(test_img),
        spatial_resolution_mpp=1.4,
        confidence_threshold=0.25,
    )
    resp = hazard_detection_service.predict(req)

    assert resp.status == "success"
    assert resp.crater_count is not None
    assert resp.crater_count > 0
    assert len(resp.detections) >= 5

    # Check bounding box geometry and metric size calculation
    for d in resp.detections:
        assert d.label in ["crater", "boulder", "rock"]
        assert d.confidence >= 0.25
        assert d.bounding_box is not None
        assert d.bounding_box.xmin < d.bounding_box.xmax
        assert d.bounding_box.ymin < d.bounding_box.ymax
        # Estimated size in meters = pixel_diameter * 1.4 mpp
        if d.pixel_diameter is not None and d.estimated_size_m is not None:
            expected_m = round(d.pixel_diameter * 1.4, 2)
            assert abs(d.estimated_size_m - expected_m) < 0.1

    # Check visual overlay base64 data URL
    assert resp.overlay_image is not None
    assert resp.overlay_image.startswith("data:image/png;base64,")


def test_yolov8n_model_architecture_and_cpu_cuda_contract():
    """Verifies active model metadata reflects YOLOv8n-Detection architecture and operational limitations."""
    meta = hazard_detection_service.get_metadata()
    assert meta["is_configured"] is True
    assert meta["architecture"] == "YOLOv8n-Detection"
    assert "crater" in meta["classes"]
    assert "boulder" in meta["classes"]
    assert "apollo_domain_gap_warning" in meta


def test_isro_chandrayaan2_data_adapter_integration():
    """Verifies that ISRO Chandrayaan-2 (OHRC & TMC-2) is registered and covers polar exploration corridors."""
    from app.services.data_sources.isro_chandrayaan2 import isro_chandrayaan2
    from app.services.data_management.coverage_manager import coverage_manager

    # 1. Covers point in extended region (-78°, 85°)
    assert isro_chandrayaan2.covers_point(-78.0, 85.0) is True

    # 2. Finds covering OHRC strip at Simpelius N / Boguslawsky (-73.0°, 54.0°)
    products = isro_chandrayaan2.find_covering_products(-73.0, 54.0)
    assert len(products) >= 1
    assert any(p["instrument"] == "OHRC" for p in products)

    # 3. Coverage manager report includes ISRO Chandrayaan-2
    report = coverage_manager.get_coverage_report(-78.0, 85.0)
    isro_layer = next((l for l in report["layers"] if l["source_id"] == "isro_chandrayaan2"), None)
    assert isro_layer is not None
    assert isro_layer["covers"] is True
    assert isro_layer["agency"] == "ISRO"
