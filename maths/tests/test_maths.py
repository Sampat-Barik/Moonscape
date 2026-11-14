"""Unit tests for pure mathematical functions in the maths package."""

import math
import numpy as np
import pytest

from maths.geodesy import (
    DEFAULT_MOON_RADIUS_M,
    haversine_lunar_distance,
    latlon_to_polar_stereo,
    polar_stereo_to_latlon,
)
from maths.topography import (
    horn_slope_and_aspect,
    rms_surface_roughness,
    slope_distribution_breakdown,
)
from maths.curvature import laplacian_curvature, detect_crater_basins
from maths.scoring import (
    evaluate_roughness_score,
    evaluate_slope_score,
    piecewise_linear_penalty,
    weighted_composite_score,
)


def test_south_pole_origin_geodesy() -> None:
    """The South Pole (-90° lat) must map exactly to (0, 0) projected meters."""
    x, y = latlon_to_polar_stereo(-90.0, 0.0)
    assert abs(x) < 1e-4
    assert abs(y) < 1e-4

    lat, lon = polar_stereo_to_latlon(0.0, 0.0)
    assert lat == -90.0


def test_roundtrip_polar_stereographic_geodesy() -> None:
    """Converting lat/lon to stereographic and back must preserve coordinates to high precision."""
    test_coords = [(-89.5, 45.0), (-85.0, 180.0), (-82.5, 270.0), (-87.2, 12.3)]
    for lat_in, lon_in in test_coords:
        x, y = latlon_to_polar_stereo(lat_in, lon_in)
        lat_out, lon_out = polar_stereo_to_latlon(x, y)
        assert abs(lat_out - lat_in) < 1e-4
        assert abs(lon_out - lon_in) < 1e-4


def test_haversine_lunar_distance() -> None:
    """Tests great circle distance between 1 degree of latitude on Moon."""
    # 1 deg latitude on Moon = (2 * pi * 1737.4 km) / 360 ≈ 30.323 km
    dist = haversine_lunar_distance(-89.0, 0.0, -90.0, 0.0)
    expected = (2.0 * math.pi * DEFAULT_MOON_RADIUS_M) / 360.0
    assert abs(dist - expected) < 10.0


def test_horn_slope_flat_plane() -> None:
    """A completely flat elevation surface must have zero slope."""
    flat_elevation = np.full((10, 10), 100.0, dtype=np.float32)
    slopes, aspects = horn_slope_and_aspect(flat_elevation, dx=100.0, dy=100.0)
    assert np.all(slopes == 0.0)


def test_horn_slope_uniform_gradient() -> None:
    """An inclined plane rising 100m over 100m distance must have a 45 degree slope."""
    xs = np.arange(10, dtype=np.float32) * 100.0  # rises 1m per meter in x
    elevation = np.tile(xs, (10, 1))
    slopes, _ = horn_slope_and_aspect(elevation, dx=100.0, dy=100.0)
    # Interior pixels (away from borders) should be 45 degrees
    assert abs(slopes[4, 4] - 45.0) < 0.1


def test_rms_surface_roughness() -> None:
    """Roughness of perfectly smooth terrain is zero; adding perturbation increases RMS."""
    smooth = np.full((10, 10), 50.0, dtype=np.float32)
    assert np.all(rms_surface_roughness(smooth) == 0.0)

    rough = smooth.copy()
    rough[5, 5] += 5.0  # Single point spike
    roughness = rms_surface_roughness(rough)
    assert roughness[5, 5] > 0.0


def test_slope_distribution_breakdown() -> None:
    """Verifies area percentages across slope categories."""
    slopes = np.array([3.0, 4.0, 7.0, 12.0, 20.0], dtype=np.float32)
    mask = np.ones_like(slopes, dtype=bool)
    dist = slope_distribution_breakdown(slopes, mask)
    assert dist["ideal_pct"] == 40.0  # 3 and 4 are <= 5
    assert dist["acceptable_pct"] == 20.0  # 7 is in (5, 10]
    assert dist["marginal_pct"] == 20.0  # 12 is in (10, 15]
    assert dist["critical_hazardous_pct"] == 20.0  # 20 is > 15


def test_scoring_slope_penalty() -> None:
    """Verifies Apollo/Artemis slope score step-downs."""
    assert evaluate_slope_score(2.0) == 100.0
    assert evaluate_slope_score(5.0) == 100.0
    assert evaluate_slope_score(10.0) == 70.0
    assert evaluate_slope_score(15.0) == 0.0
    assert evaluate_slope_score(25.0) == 0.0


def test_scoring_roughness_penalty() -> None:
    """Verifies roughness score step-downs."""
    assert evaluate_roughness_score(0.2) == 100.0
    assert evaluate_roughness_score(0.3) == 100.0
    assert evaluate_roughness_score(0.5) == 75.0
    assert evaluate_roughness_score(1.5) == 0.0


def test_weighted_composite_score() -> None:
    """Verifies weighted combination of multiple criteria."""
    subscores = {"slope": 100.0, "illum": 80.0}
    weights = {"slope": 0.5, "illum": 0.5}
    score = weighted_composite_score(subscores, weights)
    assert score == 90.0
