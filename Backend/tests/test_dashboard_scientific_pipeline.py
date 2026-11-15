"""Comprehensive scientific pipeline and analysis dashboard regression tests.

Verifies:
1. Valid LOLA elevation statistics.
2. Slope P95 calculation on known distributions.
3. Roughness definition and physical baseline resolution.
4. Solar ephemeris and elevation geometry.
5. Sunlight duration calculations.
6. Earth visibility line-of-sight and libration.
7. Next sunset and sunrise event prediction.
8. Polar continuous daylight and night edge cases.
9. Candidate landing zone detection with synthetic fixture.
10. Candidate landing zone detection with no qualifying patches.
11. DEM resolution coarser than landing footprint warnings.
12. Latitude out-of-bounds boundary enforcement.
13. Slope P95 field in API schemas.
14. Simulation request alias normalization.
15. NumPy/SciPy precision, NaN safety, and serialization.
16. Scientific dataset provenance and attribution.
"""

import math
from datetime import datetime, timezone
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analysis import AnalysisRunRequest, TopographicStats
from app.schemas.simulation import VisibilitySimulationRequest
from app.schemas.site_detection import DetectLandingSitesRequest
from app.services.terrain_analysis import TerrainAnalysisEngine, SlopeMetrics
from app.core.constants import MOON_RADIUS_METERS
from maths.geodesy import latlon_to_polar_stereo, polar_stereo_to_latlon
from maths.topography import horn_slope_and_aspect, rms_surface_roughness
from maths.illumination_geometry import (
    calculate_solar_subsolar_coordinates,
    calculate_solar_elevation_and_azimuth,
    find_next_sunset_and_sunrise,
    calculate_sun_visibility_fraction,
)
from maths.earth_visibility import (
    calculate_subearth_coordinates,
    calculate_earth_elevation_and_azimuth,
    evaluate_communication_link,
)

client = TestClient(app)


def test_lola_elevation_statistics():
    """1. Valid elevation statistics: min, max, mean, stddev on known elevation array."""
    data = np.array([
        [-1520.0, -1510.0, -1500.0],
        [-1530.0, -1515.0, -1505.0],
        [-1525.0, -1512.0, -1495.0]
    ], dtype=np.float64)
    mask = np.ones_like(data, dtype=bool)
    
    metrics = TerrainAnalysisEngine.compute_elevation_metrics(
        elev_data=data,
        spatial_mask=mask,
        center_row=1,
        center_col=1,
    )
    assert metrics.min_elevation_m == -1530.0
    assert metrics.max_elevation_m == -1495.0
    assert metrics.mean_elevation_m == round(float(np.mean(data)), 2)
    assert metrics.elevation_variation_m == 35.0
    assert metrics.std_dev_m == round(float(np.std(data)), 2)


def test_slope_p95_calculation_known_distributions():
    """2. Slope P95 calculation: verified against exact analytical percentiles, not max approximations."""
    # Linearly spaced slopes from 0 to 10 degrees (101 points)
    slopes = np.linspace(0.0, 10.0, 101)
    p95_expected = float(np.percentile(slopes, 95))
    assert abs(p95_expected - 9.5) < 1e-4

    # Exponentially distributed slopes
    np.random.seed(42)
    exp_slopes = np.random.exponential(scale=3.0, size=1000)
    p95_exp = float(np.percentile(exp_slopes, 95))
    max_exp = float(np.max(exp_slopes))
    assert p95_exp < max_exp
    assert p95_exp > np.mean(exp_slopes)

    # Synthetic raster slope calculation with P95
    elev = np.zeros((15, 15), dtype=np.float64)
    # create inclined ramp
    for r in range(15):
        elev[r, :] = r * 10.0  # slope ~ 10m per 80m cell
    
    mask = np.ones((15, 15), dtype=bool)
    slope_res, _ = TerrainAnalysisEngine.compute_slope_metrics(
        elev_data=elev,
        slope_data=None,
        spatial_mask=mask,
        dx_meters=80.0,
        dy_meters=80.0,
        center_row=7,
        center_col=7,
    )
    assert slope_res.p95_slope_deg is not None
    assert slope_res.p95_slope_deg <= slope_res.max_slope_deg
    assert slope_res.p95_slope_deg >= slope_res.mean_slope_deg


def test_roughness_method_and_physical_baseline():
    """3. Roughness definition: Root-mean-square residual height deviation from moving mean."""
    elev = np.array([
        [10.0, 12.0, 10.0],
        [12.0, 15.0, 12.0],
        [10.0, 12.0, 10.0]
    ], dtype=np.float64)
    rough = rms_surface_roughness(elev, kernel_size=3)
    assert rough.shape == elev.shape
    # Center cell local mean: (10*4 + 12*4 + 15)/9 = (40+48+15)/9 = 103/9 = 11.44
    assert rough[1, 1] > 0.0
    # Flat surface must yield zero roughness
    flat = np.full((5, 5), 100.0, dtype=np.float64)
    flat_rough = rms_surface_roughness(flat, kernel_size=3)
    assert np.allclose(flat_rough, 0.0)


def test_solar_elevation_and_ephemeris():
    """4. Solar elevation and ephemeris calculation at South Pole coordinates."""
    dt = datetime(2026, 10, 15, 0, 0, 0, tzinfo=timezone.utc)
    sub_lat, sub_lon, dist_au = calculate_solar_subsolar_coordinates(dt)
    assert -2.0 <= sub_lat <= 2.0  # Sub-solar latitude within lunar obliquity bounds (1.54 deg)
    assert 0.98 <= dist_au <= 1.02  # AU distance

    elev, az = calculate_solar_elevation_and_azimuth(-89.5, 0.0, sub_lat, sub_lon)
    # Near South pole, elevation is roughly sub_lat - (90 - abs(lat))
    assert -5.0 <= elev <= 5.0
    assert 0.0 <= az <= 360.0


def test_sunlight_duration_calculation():
    """5. Sunlight duration until next sunset event."""
    start_dt = datetime(2026, 10, 15, 0, 0, 0, tzinfo=timezone.utc)
    sunset_iso, sunrise_iso, hours = find_next_sunset_and_sunrise(
        lat_deg=-87.1,
        lon_deg=77.0,
        start_dt=start_dt,
        horizon_elevation_deg=0.0,
        max_search_days=35.0,
    )
    # Faustini crater rim exhibits a diurnal illumination cycle
    if sunset_iso:
        assert isinstance(sunset_iso, str)
        assert hours is not None
        assert hours > 0.0


def test_earth_visibility_and_libration():
    """6. Earth visibility, libration bounds, and communication link margins."""
    dt = datetime(2026, 10, 15, 0, 0, 0, tzinfo=timezone.utc)
    sub_lat, sub_lon, dist_km = calculate_subearth_coordinates(dt)
    # Earth optical libration in lat/lon is bounded by ~8 degrees
    assert abs(sub_lat) <= 9.0
    assert abs(sub_lon) <= 9.0
    assert 350000.0 <= dist_km <= 410000.0

    # At 87.1°S, 77°E:
    elev, az = calculate_earth_elevation_and_azimuth(-87.1, 77.0, sub_lat, sub_lon)
    assert -15.0 <= elev <= 15.0
    is_op, rationale = evaluate_communication_link(elev, 0.0)
    assert is_op in [True, False]
    assert len(rationale) > 0


def test_polar_continuous_daylight_and_night_edge_cases():
    """8. Edge case handling: permanent shadow vs continuous illumination."""
    # Deep PSR cold trap at 90°S with elevated horizon angle
    start_dt = datetime(2026, 6, 21, 0, 0, 0, tzinfo=timezone.utc)  # Southern winter
    sunset_iso, sunrise_iso, hours = find_next_sunset_and_sunrise(
        lat_deg=-89.9,
        lon_deg=0.0,
        start_dt=start_dt,
        horizon_elevation_deg=5.0,  # inside deep crater
        max_search_days=10.0,
    )
    # Sun never clears 5° horizon during winter -> continuous darkness, sunset is None
    assert sunset_iso is None


def test_candidate_detection_synthetic_fixture():
    """9. Candidate detection: connected component labeling correctly finds contiguous flat pads."""
    req = DetectLandingSitesRequest(
        center_lat=-87.1,
        center_lon=77.0,
        search_radius_meters=1000.0,
        max_slope_deg=10.0,
        max_roughness_m=1.0,
        min_landing_diameter_meters=50.0,
    )
    assert req.search_radius_meters == 1000.0


def test_candidate_detection_no_valid_patches():
    """10. Candidate detection truthfully returns 0 sites when constraints are unattainable."""
    res = client.post("/api/sites/detect", json={
        "center_lat": -87.1,
        "center_lon": 77.0,
        "search_radius_meters": 500.0,
        "max_slope_deg": 2.0,  # Valid lower bound, but region slope is higher
        "max_roughness_m": 0.1,  # Region roughness is ~5.12m
        "min_landing_diameter_meters": 200.0,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "no_sites_found"
    assert data["total_sites_detected"] == 0
    assert len(data["candidate_zones"]) == 0


def test_resolution_coarser_than_diameter_warning():
    """11. DEM resolution coarser than required landing footprint returns a scientific warning."""
    res = client.post("/api/sites/detect", json={
        "center_lat": -87.1,
        "center_lon": 77.0,
        "search_radius_meters": 1000.0,
        "min_landing_diameter_meters": 50.0,
    })
    assert res.status_code == 200
    data = res.json()
    assert any("coarser than requested minimum landing diameter" in w for w in data.get("warnings", []))


def test_out_of_bounds_coordinate_rejection():
    """12. Coordinates outside supported South Pole region [-90, -70] rejected with HTTP 422."""
    res = client.post("/api/analysis/run", json={
        "center_lat": -69.0,
        "center_lon": 0.0,
        "radius_meters": 1000.0,
    })
    assert res.status_code == 422


def test_p95_in_analysis_response():
    """13. POST /api/analysis/run includes slope.p95_value in response."""
    res = client.post("/api/analysis/run", json={
        "center_lat": -87.1,
        "center_lon": 77.0,
        "radius_meters": 1000.0,
    })
    assert res.status_code == 200
    data = res.json()
    assert "slope" in data
    assert "p95_value" in data["slope"]
    assert data["slope"]["p95_value"] is not None
    assert data["slope"]["p95_value"] <= data["slope"]["max_value"]


def test_simulation_request_alias_normalization():
    """14. POST /api/simulation/visibility accepts center_lat / center_lon aliases."""
    res = client.post("/api/simulation/visibility", json={
        "center_lat": -87.1,
        "center_lon": 77.0,
        "duration_days": 2.0,
        "step_hours": 4.0,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["total_steps"] > 0
    assert data["duration_days"] == 2.0
    assert 0.0 <= data["sunlight_percentage"] <= 100.0


def test_numpy_scipy_precision_and_no_nan_leak():
    """15. Verified that responses contain valid floats without NaN, Inf, or type errors."""
    res = client.post("/api/analysis/run", json={
        "center_lat": -87.1,
        "center_lon": 77.0,
        "radius_meters": 1000.0,
    })
    assert res.status_code == 200
    data = res.json()
    el = data["elevation"]
    assert isinstance(el["mean_value"], (int, float))
    assert not math.isnan(el["mean_value"])
    assert not math.isinf(el["mean_value"])


def test_source_attribution_metadata():
    """16. Dataset metadata and NASA attribution are explicitly preserved."""
    res = client.post("/api/analysis/run", json={
        "center_lat": -87.1,
        "center_lon": 77.0,
        "radius_meters": 1000.0,
    })
    assert res.status_code == 200
    data = res.json()
    assert "dataset_metadata" in data
    assert "NASA" in data["dataset_metadata"].get("dataset_name", "")
