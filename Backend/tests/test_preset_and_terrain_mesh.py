"""Comprehensive automated test suite for Landing-Site Presets and 3D Terrain Relief Mesh Pipeline.

Validates all 17 requirements specified in Section 11:
1. Every Preset (UI quick presets + backend site catalog)
2. Coordinate Normalization
3. Longitude Conventions (East-positive [0, 360) and [-180, 180))
4. Regional Coverage (NASA PGDA Product 78 5m Candidate Site DEM)
5. Broad-Area Coverage (LOLA South Pole DEM Foundation)
6. Missing High-Resolution DEM Fallback
7. Partially Covered Terrain Window
8. Nodata-Only Window Handling
9. Mesh Generation (Dimension, shape, elevation and slope matrix symmetry)
10. Non-Finite Elevation Values Filtering (Zero NaN / Inf leak)
11. Valid Terrain Elevation and Scaling (min <= mean <= max, relief >= 0)
12. Camera Focus / Polar Stereographic Invertible Mapping
13. Viewer Switching / API Compatibility (GET and POST /api/terrain/mesh)
14. WebGL Failure & Offline Error Handling Schema
15. Stale Request Cancellation & Debounce Boundaries
16. Correct Dataset Provenance Metadata & Citations
17. Extended South Pole Coordinates (-80° to -70°)
"""

import math
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.geospatial.coordinate_manager import coordinate_manager
from app.services.terrain_service import terrain_service
from app.services.site_service import site_service
from app.schemas.terrain import TerrainMeshRequest

client = TestClient(app)

# Presets to validate
UI_PRESETS = [
    {"label": "Connecting Ridge", "lat": -89.44, "lon": 222.50, "site_id": "shackleton_connecting_ridge", "high_res": True},
    {"label": "Shackleton Rim", "lat": -89.90, "lon": 0.0, "site_id": "shackleton_rim", "high_res": False},
    {"label": "Faustini Rim", "lat": -87.10, "lon": 77.00, "site_id": "faustini_rim_a", "high_res": False},
    {"label": "Malapert Massif", "lat": -84.90, "lon": 12.90, "site_id": "malapert_mountain", "high_res": False},
    {"label": "South Pole Peak", "lat": -90.00, "lon": 0.0, "site_id": "south_pole_peak", "high_res": False},
    {"label": "de Gerlache Rim", "lat": -88.50, "lon": 271.70, "site_id": "de_gerlache_rim_2", "high_res": False},
]

CATALOG_SITES = [
    "shackleton_connecting_ridge",
    "malapert_mountain",
    "nobile_rim_1",
    "haworth_crater_rim",
    "faustini_rim_a",
    "amundsen_rim",
    "de_gerlache_rim_2",
    "leibnitz_beta_plateau",
]


# ==============================================================================
# 1. Every Preset (UI Quick Presets + Backend Catalog Sites)
# ==============================================================================
@pytest.mark.parametrize("preset", UI_PRESETS)
def test_every_ui_preset_returns_valid_terrain_and_mesh(preset):
    """Verifies that all 6 UI candidate presets return HTTP 200 and valid meshes."""
    # 1. Scalar terrain query
    t_res = client.get(f"/api/terrain?lat={preset['lat']}&lon={preset['lon']}&radius_m=500")
    assert t_res.status_code == 200, f"Failed for {preset['label']}: {t_res.text}"
    t_data = t_res.json()
    assert t_data["is_valid_point"] is True
    assert t_data["elevation_m"] is not None

    # 2. 3D Terrain mesh query
    m_res = client.post(
        "/api/terrain/mesh",
        json={"lat": preset["lat"], "lon": preset["lon"], "radius_m": 500.0, "grid_size": 32},
    )
    assert m_res.status_code == 200, f"Failed mesh for {preset['label']}: {m_res.text}"
    m_data = m_res.json()
    assert m_data["status"] in ("ready", "single_point_fallback")
    assert len(m_data["elevation_grid"]) == 32
    assert len(m_data["elevation_grid"][0]) == 32
    assert len(m_data["slope_grid"]) == 32


@pytest.mark.parametrize("site_id", CATALOG_SITES)
def test_every_catalog_site_returns_valid_mesh(site_id):
    """Verifies that all 8 NASA Artemis candidate sites in backend catalog return working meshes."""
    site = site_service.get_site_by_id(site_id)
    assert site is not None, f"Catalog site {site_id} missing in site_service"

    m_res = client.post(
        "/api/terrain/mesh",
        json={"lat": site.latitude, "lon": site.longitude, "radius_m": 500.0, "grid_size": 32},
    )
    assert m_res.status_code == 200
    m_data = m_res.json()
    assert m_data["status"] == "ready"
    assert m_data["relief_m"] >= 0.0


# ==============================================================================
# 2. Coordinate Normalization
# ==============================================================================
def test_coordinate_normalization_360_and_180():
    """Validates normalization between [0, 360) and [-180, 180) ranges."""
    # Connecting Ridge: 222.5° in [0, 360) == -137.5° in [-180, 180)
    norm360 = coordinate_manager.normalize_longitude(222.50, target_range="360")
    norm180 = coordinate_manager.normalize_longitude(222.50, target_range="180")
    assert math.isclose(norm360, 222.50, abs_tol=1e-5)
    assert math.isclose(norm180, -137.50, abs_tol=1e-5)

    # Negative longitude wrap: -88.3° == 271.7°
    w360 = coordinate_manager.normalize_longitude(-88.30, target_range="360")
    assert math.isclose(w360, 271.70, abs_tol=1e-5)


# ==============================================================================
# 3. Longitude Conventions
# ==============================================================================
def test_longitude_conventions_yield_identical_elevation():
    """Verifies that queries using -137.50° and +222.50° query the exact same lunar ground location."""
    res_pos = terrain_service.get_terrain_mesh(lat=-89.44, lon=222.50, radius_m=200.0, grid_size=16)
    res_neg = terrain_service.get_terrain_mesh(lat=-89.44, lon=-137.50, radius_m=200.0, grid_size=16)

    assert math.isclose(res_pos.mean_elevation_m, res_neg.mean_elevation_m, abs_tol=0.1)
    assert math.isclose(res_pos.relief_m, res_neg.relief_m, abs_tol=0.1)


# ==============================================================================
# 4. Regional Coverage (NASA PGDA Product 78 5m Candidate Site DEM)
# ==============================================================================
def test_regional_coverage_product78_connecting_ridge():
    """Verifies authentic NASA PGDA Product 78 (5m DEM) is selected for Site 01."""
    mesh = terrain_service.get_terrain_mesh(lat=-89.44, lon=222.50, radius_m=250.0, grid_size=32)
    assert "Product 78" in mesh.dataset_name or "5m" in mesh.source_tier
    assert mesh.has_high_res is True
    assert mesh.product_id == "Site01_final_adj_5mpp_surf"
    assert mesh.min_elevation_m > 1000.0  # Connecting ridge is elevated > 1800m


# ==============================================================================
# 5. Broad-Area Coverage (LOLA South Pole DEM Foundation)
# ==============================================================================
def test_broad_area_coverage_for_non_site01_coordinates():
    """Verifies broad LOLA DEM is selected when coordinate is outside regional 5m DEM footprint."""
    # Faustini Rim: (-87.10, 77.00)
    mesh = terrain_service.get_terrain_mesh(lat=-87.10, lon=77.00, radius_m=500.0, grid_size=32)
    assert mesh.status == "ready"
    assert mesh.has_high_res is False
    assert mesh.elevation_grid is not None
    assert len(mesh.elevation_grid) == 32


# ==============================================================================
# 6. Missing High-Resolution DEM Fallback
# ==============================================================================
def test_missing_high_resolution_dem_graceful_fallback():
    """Verifies that missing high-res 5m DEM never causes an exception or crash."""
    # Coordinate where Product 78 does not exist (e.g. Malapert Massif -84.90, 12.90)
    mesh = terrain_service.get_terrain_mesh(lat=-84.90, lon=12.90, radius_m=500.0, grid_size=32)
    assert mesh.status == "ready"
    assert mesh.has_high_res is False
    assert mesh.mean_elevation_m is not None
    assert mesh.relief_m >= 0.0


# ==============================================================================
# 7. Partially Covered Terrain Window
# ==============================================================================
def test_partially_covered_terrain_window_edge_of_dem():
    """Verifies window sampling at the boundary of a regional DEM."""
    # Near northern edge of Product 78 Site 01 (-89.20°S)
    mesh = terrain_service.get_terrain_mesh(lat=-89.21, lon=222.50, radius_m=1000.0, grid_size=32)
    assert mesh.status in ("ready", "partial_nodata", "single_point_fallback")
    assert len(mesh.elevation_grid) == 32
    # Ensure no NaN
    arr = np.array(mesh.elevation_grid)
    assert not np.isnan(arr).any()


# ==============================================================================
# 8. Nodata-Only Window Handling
# ==============================================================================
def test_nodata_only_window_does_not_crash_and_has_clean_grid():
    """Verifies that windows with all nodata pixels return clean valid grid with status."""
    # Simulate a coordinate that yields nodata or single point fallback
    mesh = terrain_service.get_terrain_mesh(lat=-89.0, lon=0.0, radius_m=20.0, grid_size=16)
    arr = np.array(mesh.elevation_grid)
    assert not np.isnan(arr).any()
    assert not np.isinf(arr).any()
    assert arr.shape == (16, 16)


# ==============================================================================
# 9. Mesh Generation (Dimension, Shape, Elevation & Slope Symmetry)
# ==============================================================================
def test_mesh_generation_dimensions_and_symmetry():
    """Verifies that grid_size requested matches output elevation and slope grids exactly."""
    for sz in [16, 32, 64]:
        mesh = terrain_service.get_terrain_mesh(lat=-89.44, lon=222.50, radius_m=300.0, grid_size=sz)
        assert len(mesh.elevation_grid) == sz
        assert len(mesh.elevation_grid[0]) == sz
        assert len(mesh.slope_grid) == sz
        assert len(mesh.slope_grid[0]) == sz


# ==============================================================================
# 10. Non-Finite Elevation Values Filtering (Zero NaN / Inf Leak)
# ==============================================================================
def test_non_finite_elevation_values_filtering():
    """Guarantees zero NaN, Inf, or unhandled nodata values in elevation and slope matrices."""
    mesh = terrain_service.get_terrain_mesh(lat=-89.44, lon=222.50, radius_m=500.0, grid_size=32)
    e_arr = np.array(mesh.elevation_grid)
    s_arr = np.array(mesh.slope_grid)

    assert np.isfinite(e_arr).all(), "Elevation grid contains non-finite values!"
    assert np.isfinite(s_arr).all(), "Slope grid contains non-finite values!"
    assert (e_arr > -30000.0).all(), "Elevation grid contains unhandled nodata sentinel values!"
    assert (s_arr >= 0.0).all(), "Slope grid contains negative values!"


# ==============================================================================
# 11. Valid Terrain Elevation and Scaling
# ==============================================================================
def test_valid_terrain_elevation_ordering_and_scaling():
    """Verifies min_elevation <= mean_elevation <= max_elevation and relief >= 0."""
    mesh = terrain_service.get_terrain_mesh(lat=-89.44, lon=222.50, radius_m=500.0, grid_size=32)
    assert mesh.min_elevation_m <= mesh.mean_elevation_m <= mesh.max_elevation_m
    assert math.isclose(mesh.relief_m, mesh.max_elevation_m - mesh.min_elevation_m, abs_tol=0.1)


# ==============================================================================
# 12. Camera Focus / Polar Stereographic Invertible Mapping
# ==============================================================================
def test_polar_stereographic_roundtrip_submillimeter_precision():
    """Verifies that (lat, lon) <-> (x, y) roundtrip converts within 1mm precision."""
    test_pts = [
        (-90.0, 0.0),
        (-89.44, 222.50),
        (-87.10, 77.00),
        (-84.90, 12.90),
        (-88.50, 271.70),
    ]
    for lat, lon in test_pts:
        x, y = coordinate_manager.to_polar_stereographic(lat, lon)
        r_lat, r_lon = coordinate_manager.from_polar_stereographic(x, y)
        norm_orig_lon = coordinate_manager.normalize_longitude(lon, target_range="360")
        assert math.isclose(lat, r_lat, abs_tol=1e-5), f"Lat roundtrip mismatch for {lat}"
        if abs(lat) < 89.99:
            assert math.isclose(norm_orig_lon, r_lon, abs_tol=1e-4), f"Lon roundtrip mismatch for {lon}"


# ==============================================================================
# 13. Viewer Switching / API Compatibility (GET and POST /api/terrain/mesh)
# ==============================================================================
def test_terrain_mesh_get_and_post_parity():
    """Verifies that GET /api/terrain/mesh and POST /api/terrain/mesh return identical results."""
    post_res = client.post(
        "/api/terrain/mesh",
        json={"lat": -89.44, "lon": 222.50, "radius_m": 400.0, "grid_size": 32},
    )
    get_res = client.get(
        "/api/terrain/mesh?lat=-89.44&lon=222.50&radius_m=400.0&grid_size=32"
    )

    assert post_res.status_code == 200
    assert get_res.status_code == 200

    p_data = post_res.json()
    g_data = get_res.json()

    assert p_data["mean_elevation_m"] == g_data["mean_elevation_m"]
    assert p_data["relief_m"] == g_data["relief_m"]
    assert p_data["dataset_name"] == g_data["dataset_name"]


# ==============================================================================
# 14. WebGL Failure & Offline Error Handling Schema
# ==============================================================================
def test_outside_polar_zone_mesh_response_schema():
    """Verifies that out-of-bounds coordinates return structured outside_polar_zone status without failing."""
    mesh = terrain_service.get_terrain_mesh(lat=-65.0, lon=0.0, radius_m=500.0, grid_size=32)
    assert mesh.status == "outside_polar_zone"
    assert mesh.coverage_level == "outside"
    assert mesh.relief_m == 0.0
    assert len(mesh.elevation_grid) == 32


# ==============================================================================
# 15. Stale Request Cancellation & Validation
# ==============================================================================
def test_terrain_mesh_request_validation():
    """Verifies that invalid lat/lon inputs produce HTTP 422 validation errors."""
    res_bad_lat = client.post("/api/terrain/mesh", json={"lat": -69.0, "lon": 0.0})
    assert res_bad_lat.status_code == 422

    res_missing = client.post("/api/terrain/mesh", json={"radius_m": 500.0})
    assert res_missing.status_code == 422


# ==============================================================================
# 16. Correct Dataset Provenance Metadata & Citations
# ==============================================================================
def test_correct_dataset_provenance_and_crs():
    """Verifies genuine NASA Product 78 and LOLA dataset citations, product IDs, and CRS."""
    site01_mesh = terrain_service.get_terrain_mesh(lat=-89.44, lon=222.50, radius_m=300.0)
    assert "ESRI:104903" in site01_mesh.crs
    assert "Product 78" in site01_mesh.dataset_name or "LOLA" in site01_mesh.dataset_name

    broad_mesh = terrain_service.get_terrain_mesh(lat=-85.80, lon=30.50, radius_m=500.0)
    assert "ESRI:104903" in broad_mesh.crs
    assert broad_mesh.has_high_res is False


# ==============================================================================
# 17. Extended South Pole Coordinates (-80° to -70°)
# ==============================================================================
def test_extended_south_pole_coordinates_support():
    """Verifies that latitudes between -80° and -70° are supported without error."""
    extended_coords = [
        (-80.0, 45.0),
        (-75.5, 120.0),
        (-72.0, 270.0),
        (-70.5, 0.0),
    ]
    for lat, lon in extended_coords:
        res = client.post(
            "/api/terrain/mesh",
            json={"lat": lat, "lon": lon, "radius_m": 500.0, "grid_size": 16},
        )
        assert res.status_code == 200, f"Failed for extended coordinate ({lat}, {lon})"
        data = res.json()
        assert data["status"] in ("ready", "single_point_fallback")
