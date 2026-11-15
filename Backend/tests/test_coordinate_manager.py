"""Tests for lunar coordinate management, normalizations, and south pole validations."""

import pytest
from app.services.geospatial.coordinate_manager import coordinate_manager


def test_normalize_longitude_360():
    """Verify longitude normalization into [0, 360) range."""
    assert coordinate_manager.normalize_longitude(0.0, "360") == 0.0
    assert coordinate_manager.normalize_longitude(360.0, "360") == 0.0
    assert coordinate_manager.normalize_longitude(-90.0, "360") == 270.0
    assert coordinate_manager.normalize_longitude(-180.0, "360") == 180.0
    assert coordinate_manager.normalize_longitude(450.0, "360") == 90.0


def test_normalize_longitude_180():
    """Verify longitude normalization into [-180, 180) range."""
    assert coordinate_manager.normalize_longitude(0.0, "180") == 0.0
    assert coordinate_manager.normalize_longitude(180.0, "180") == 180.0
    assert coordinate_manager.normalize_longitude(270.0, "180") == -90.0
    assert coordinate_manager.normalize_longitude(-200.0, "180") == 160.0


def test_south_pole_zone_check():
    """Verify polar stereographic disk inclusion (-90 to -80 deg)."""
    assert coordinate_manager.is_in_south_pole_zone(-90.0) is True
    assert coordinate_manager.is_in_south_pole_zone(-89.9) is True
    assert coordinate_manager.is_in_south_pole_zone(-80.0) is True
    assert coordinate_manager.is_in_south_pole_zone(-79.9) is False
    assert coordinate_manager.is_in_south_pole_zone(0.0) is False
    assert coordinate_manager.is_in_south_pole_zone(85.0) is False


def test_polar_stereographic_projection_roundtrip():
    """Verify exact spherical projection round-trip accuracy within millimeters."""
    lat_in, lon_in = -89.5, 120.0
    x, y = coordinate_manager.to_polar_stereographic(lat_in, lon_in)
    lat_out, lon_out = coordinate_manager.from_polar_stereographic(x, y)

    assert abs(lat_out - lat_in) < 1e-6
    assert abs(lon_out - lon_in) < 1e-6


def test_surface_distance_meters():
    """Verify lunar great-circle distance calculation."""
    # 1 degree of lunar latitude is approx pi * 1737.4 km / 180 = ~30.323 km
    dist = coordinate_manager.surface_distance_m(-90.0, 0.0, -89.0, 0.0)
    assert 30_000.0 < dist < 30_500.0
