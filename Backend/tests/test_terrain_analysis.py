"""Scientific verification tests for the Phase 3 Lunar Terrain Analysis Engine.

Validates algorithms on controlled synthetic rasters and authentic NASA LOLA data:
1. Flat terrain test raster (slope == 0.0 deg, roughness == 0.0 m, variation == 0.0 m)
2. Inclined terrain test raster (known planar gradient with exact trigonometric verification)
3. Rough terrain test raster (controlled elevation variance and RMS roughness)
4. Missing / nodata pixels handling (-32768.0 and NaN exclusion)
5. Edge of raster boundary conditions (reflection padding without array bounds errors)
6. Varying physical analysis radii (quadratic area scaling)
7. Known authentic NASA raster sample points (Shackleton Connecting Ridge Site 01)
"""

import math
from affine import Affine
import numpy as np
import pytest

from app.services.terrain_analysis import terrain_analysis_engine


def test_flat_terrain_synthetic_raster():
    """Flat terrain (uniform elevation) must yield exactly 0.0 slope, 0.0 roughness, and 0.0 relief."""
    shape = (21, 21)
    flat_elevation = np.full(shape, 1500.0, dtype=np.float32)
    spatial_mask = np.ones(shape, dtype=bool)
    dx = 10.0
    dy = 10.0
    center_row, center_col = 10, 10

    # 1. Elevation metrics
    e_metrics = terrain_analysis_engine.compute_elevation_metrics(
        elev_data=flat_elevation,
        spatial_mask=spatial_mask,
        center_row=center_row,
        center_col=center_col,
    )
    assert e_metrics.point_elevation_m == 1500.0
    assert e_metrics.min_elevation_m == 1500.0
    assert e_metrics.max_elevation_m == 1500.0
    assert e_metrics.mean_elevation_m == 1500.0
    assert e_metrics.elevation_variation_m == 0.0
    assert e_metrics.std_dev_m == 0.0

    # 2. Slope metrics (DEM derived)
    s_metrics, aspect = terrain_analysis_engine.compute_slope_metrics(
        elev_data=flat_elevation,
        slope_data=None,
        spatial_mask=spatial_mask,
        dx_meters=dx,
        dy_meters=dy,
        center_row=center_row,
        center_col=center_col,
    )
    assert s_metrics.point_slope_deg == 0.0
    assert s_metrics.mean_slope_deg == 0.0
    assert s_metrics.max_slope_deg == 0.0
    assert s_metrics.min_slope_deg == 0.0
    assert s_metrics.ideal_pct == 100.0

    # 3. Roughness metrics
    r_metrics = terrain_analysis_engine.compute_roughness_metrics(
        elev_data=flat_elevation,
        spatial_mask=spatial_mask,
        dx_meters=dx,
        center_row=center_row,
        center_col=center_col,
        kernel_size=3,
    )
    assert r_metrics.point_roughness_m == 0.0
    assert r_metrics.mean_roughness_m == 0.0
    assert r_metrics.max_roughness_m == 0.0


def test_inclined_terrain_synthetic_raster():
    """Inclined planar terrain with known gradient dz/dx must yield exact trigonometric slope."""
    shape = (31, 31)
    dx = 10.0
    dy = 10.0
    gradient_x = 0.1  # dz/dx = 0.1 -> slope = arctan(0.1) rad = 5.7106 deg

    rows, cols = np.indices(shape)
    inclined_elevation = (cols * dx * gradient_x + 500.0).astype(np.float32)
    spatial_mask = np.ones(shape, dtype=bool)
    center_row, center_col = 15, 15

    expected_slope_deg = math.degrees(math.atan(gradient_x))  # ~5.7106 deg

    s_metrics, aspect = terrain_analysis_engine.compute_slope_metrics(
        elev_data=inclined_elevation,
        slope_data=None,
        spatial_mask=spatial_mask,
        dx_meters=dx,
        dy_meters=dy,
        center_row=center_row,
        center_col=center_col,
    )

    # In the interior of the incline, Horn slope should exactly equal expected slope
    assert abs(s_metrics.point_slope_deg - expected_slope_deg) < 0.01
    assert abs(s_metrics.mean_slope_deg - expected_slope_deg) < 0.25
    assert s_metrics.source_type == "horn_1981_dem_gradient"


def test_roughness_calculation_synthetic_raster():
    """Synthetic undulating terrain with known high-frequency perturbation must yield non-zero RMS roughness."""
    shape = (25, 25)
    dx = 5.0
    rows, cols = np.indices(shape)
    # Checkerboard alternating perturbation of +/- 2.0 meters around 1000m
    perturbation = np.where((rows + cols) % 2 == 0, 2.0, -2.0)
    rough_elevation = (1000.0 + perturbation).astype(np.float32)
    spatial_mask = np.ones(shape, dtype=bool)
    center_row, center_col = 12, 12

    r_metrics = terrain_analysis_engine.compute_roughness_metrics(
        elev_data=rough_elevation,
        spatial_mask=spatial_mask,
        dx_meters=dx,
        center_row=center_row,
        center_col=center_col,
        kernel_size=3,
    )

    assert r_metrics.point_roughness_m is not None
    assert r_metrics.point_roughness_m > 0.0
    assert r_metrics.mean_roughness_m > 0.0
    assert r_metrics.units == "meters"
    assert r_metrics.kernel_size == 3
    assert r_metrics.baseline_meters == 15.0  # 3 * 5.0m


def test_missing_and_nodata_pixels_handling():
    """Pixels matching LOLA nodata (-32768.0) or NaN must be masked out from all statistical metrics."""
    shape = (15, 15)
    elev_data = np.full(shape, 800.0, dtype=np.float32)
    # Inject missing and extreme nodata pixels
    elev_data[2, 2] = -32768.0
    elev_data[3, 3] = -99999.0
    elev_data[4, 4] = np.nan
    elev_data[7, 7] = 850.0  # single elevated peak

    spatial_mask = np.ones(shape, dtype=bool)
    center_row, center_col = 7, 7

    e_metrics = terrain_analysis_engine.compute_elevation_metrics(
        elev_data=elev_data,
        spatial_mask=spatial_mask,
        center_row=center_row,
        center_col=center_col,
        nodata_val=-32768.0,
    )

    assert e_metrics.point_elevation_m == 850.0
    assert e_metrics.min_elevation_m == 800.0  # nodata -32768 must NOT pull min down
    assert e_metrics.max_elevation_m == 850.0
    assert e_metrics.elevation_variation_m == 50.0


def test_edge_of_raster_boundary_conditions():
    """Queries at the exact corner / edge of a raster window must not trigger IndexError."""
    shape = (11, 11)
    elev_data = np.full(shape, 1200.0, dtype=np.float32)
    spatial_mask = np.ones(shape, dtype=bool)

    # Test top-left corner
    e_metrics = terrain_analysis_engine.compute_elevation_metrics(
        elev_data=elev_data,
        spatial_mask=spatial_mask,
        center_row=0,
        center_col=0,
    )
    assert e_metrics.point_elevation_m == 1200.0

    s_metrics, aspect = terrain_analysis_engine.compute_slope_metrics(
        elev_data=elev_data,
        slope_data=None,
        spatial_mask=spatial_mask,
        dx_meters=10.0,
        dy_meters=10.0,
        center_row=0,
        center_col=0,
    )
    assert s_metrics.point_slope_deg == 0.0


def test_different_analysis_radii_scaling():
    """The number of raster cells included inside spatial distance mask must scale quadratically with radius."""
    shape = (101, 101)
    transform = Affine(5.0, 0.0, -250.0, 0.0, -5.0, 250.0)
    center_x = 0.0
    center_y = 0.0

    mask_r50 = terrain_analysis_engine.create_spatial_distance_mask(shape, transform, center_x, center_y, radius_m=50.0)
    mask_r100 = terrain_analysis_engine.create_spatial_distance_mask(shape, transform, center_x, center_y, radius_m=100.0)

    count_50 = np.sum(mask_r50)
    count_100 = np.sum(mask_r100)

    # Doubling the radius should approximately quadruple the cell count (pi * r^2)
    ratio = count_100 / count_50
    assert 3.6 < ratio < 4.4, f"Quadratic area scaling failed: ratio was {ratio}"


def test_known_authentic_nasa_sample_point():
    """Evaluates authentic NASA LOLA 5m data at the Shackleton Connecting Ridge (-89.46, 222.0)."""
    res = terrain_analysis_engine.analyze_location(
        lat_deg=-89.46,
        lon_deg=222.0,
        radius_meters=100.0,
        roughness_kernel_size=3,
    )

    assert res is not None
    assert res.latitude == -89.46
    assert res.longitude == 222.0
    assert res.radius_meters == 100.0
    assert res.valid_pixels_in_disc > 0

    # Shackleton connecting ridge is roughly 1900-1950m
    assert 1850.0 < res.elevation.point_elevation_m < 2050.0
    assert res.elevation.elevation_variation_m is not None
    assert res.elevation.elevation_variation_m >= 0.0

    # Precomputed NASA 5m slope map verification
    assert res.slope.point_slope_deg is not None
    assert 0.0 <= res.slope.point_slope_deg <= 20.0
    assert res.slope.source_type == "nasa_precomputed_product"

    # Roughness metrics
    assert res.roughness.point_roughness_m is not None
    assert res.roughness.baseline_meters == 15.0  # 3 * 5m
    assert res.roughness.units == "meters"

    # Provenance
    assert "Barker" in res.metadata["citation"]
    assert res.metadata["spatial_resolution_m"] == 5.0
