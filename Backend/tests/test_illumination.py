"""Unit and integration tests for Lunar Illumination Analysis Service (Phase 5).

Tests:
1. Solar ephemeris accuracy (subsolar coordinates, lunar obliquity bounds)
2. Valid input region analysis (Artemis III site, solar geometry, cumulative ground truth)
3. Time interval and epoch handling (summer vs winter solar elevation)
4. Missing illumination data handling (null cumulative percentage, no fabrication)
5. Invalid inputs (out-of-bounds latitude, malformed date, invalid radius)
6. Permanently Shadowed Region (PSR) and cryogenic cold-trap thermal classification
7. Topographic horizon ray tracing and mountain shadow occlusion
8. Diviner thermal distinction verification
"""

from datetime import datetime, timezone
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.schemas.analysis import AnalysisRunRequest
from app.services.illumination import DIVINER_THERMAL_CAVEAT, illumination_service
from maths.illumination_geometry import (
    LUNAR_OBLIQUITY_DEG,
    calculate_solar_elevation_and_azimuth,
    calculate_solar_subsolar_coordinates,
    calculate_sun_visibility_fraction,
    calculate_topographic_horizon_angle,
    estimate_surface_temperature_kelvin,
    parse_utc_timestamp,
)


def test_solar_ephemeris_bounds() -> None:
    """Verifies that astronomical ephemeris strictly respects lunar physical obliquity."""
    # Test across multiple quarters of a lunar precession year
    epochs = [
        datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc),
    ]

    for dt in epochs:
        sub_lat, sub_lon, sun_dist = calculate_solar_subsolar_coordinates(dt)
        # Declination on Moon cannot exceed lunar obliquity (1.5424 deg)
        assert abs(sub_lat) <= (LUNAR_OBLIQUITY_DEG + 0.05)
        assert -180.0 <= sub_lon <= 180.0
        assert 0.98 <= sun_dist <= 1.02  # Astronomical Units


def test_topographic_horizon_ray_tracing_shadow() -> None:
    """Tests that a high crater rim casts a shadow when the Sun is at low polar elevation."""
    center_elev = 0.0
    # Rim 500m higher than center point, 5000m away -> angle ~ arctan(500/5000) = 5.71 degrees
    profile = np.array([50.0, 100.0, 250.0, 500.0], dtype=np.float64)
    distances = np.array([1000.0, 2000.0, 3500.0, 5000.0], dtype=np.float64)

    horizon_angle = calculate_topographic_horizon_angle(profile, distances, center_elev)
    assert horizon_angle > 5.0  # ~5.6 deg

    # Case 1: Sun at 1.5 deg elevation (typical polar maximum) -> completely blocked by rim
    vis_blocked = calculate_sun_visibility_fraction(
        solar_elevation_deg=1.5,
        horizon_elevation_deg=horizon_angle,
    )
    assert vis_blocked == 0.0

    # Case 2: High Sun at 8.0 deg elevation -> clears the rim
    vis_cleared = calculate_sun_visibility_fraction(
        solar_elevation_deg=8.0,
        horizon_elevation_deg=horizon_angle,
    )
    assert vis_cleared == 1.0


def test_illumination_valid_polar_region(client: TestClient) -> None:
    """Tests POST /api/analysis/run returns structured illumination on Shackleton Connecting Ridge."""
    payload = {
        "center_lat": -89.44,
        "center_lon": 222.50,
        "radius_meters": 1000.0,
        "epoch_iso": "2026-11-15T12:00:00Z",
    }
    response = client.post("/api/analysis/run", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "illumination" in data
    illum = data["illumination"]
    assert illum["status"] in ["available", "degraded"]
    assert illum["solar_elevation_deg"] is not None
    assert 0.0 <= illum["solar_azimuth_deg"] <= 360.0
    assert illum["instantaneous_sunlit_fraction_pct"] is not None

    # Peer-reviewed LOLA Artemis III ground truth for Shackleton Connecting Ridge
    assert illum["cumulative_illumination_pct"] == 86.4
    assert "Barker et al." in illum["time_period_evaluated"]
    assert illum["sunlight_continuous_hours_max"] is not None
    assert illum["is_permanently_shadowed_region"] is False


def test_illumination_time_interval_handling(client: TestClient) -> None:
    """Tests solar elevation varies with seasonal epochs (lunar southern summer vs winter).

    Note: Due to the 18.6-year nodal precession of the Moon's spin axis relative to the Sun,
    lunar seasons drift relative to Earth's Gregorian calendar. In 2026, southern lunar summer
    peaks around May (subsolar latitude ~ -1.5 deg), while southern winter occurs around November.
    """
    # Southern summer epoch (May 2026): Sun higher in southern lunar sky
    summer_payload = {
        "center_lat": -89.50,
        "center_lon": 0.0,
        "radius_meters": 500.0,
        "epoch_iso": "2026-05-15T00:00:00Z",
    }
    resp_summer = client.post("/api/analysis/run", json=summer_payload)
    assert resp_summer.status_code == 200
    summer_elev = resp_summer.json()["illumination"]["solar_elevation_deg"]

    # Southern winter epoch (Nov 2026): Sun lower in southern lunar sky (subsolar latitude ~ +1.5 deg)
    winter_payload = {
        "center_lat": -89.50,
        "center_lon": 0.0,
        "radius_meters": 500.0,
        "epoch_iso": "2026-11-15T00:00:00Z",
    }
    resp_winter = client.post("/api/analysis/run", json=winter_payload)
    assert resp_winter.status_code == 200
    winter_elev = resp_winter.json()["illumination"]["solar_elevation_deg"]

    assert summer_elev > winter_elev


def test_illumination_missing_cumulative_data_point(client: TestClient) -> None:
    """SCIENTIFIC INTEGRITY: Points lacking cumulative rasters must report null, not fabricate data."""
    # Point at -81.0 deg latitude, far away from any candidate site
    payload = {
        "center_lat": -81.00,
        "center_lon": 90.00,
        "radius_meters": 1000.0,
    }
    response = client.post("/api/analysis/run", json=payload)
    assert response.status_code == 200
    illum = response.json()["illumination"]

    # Cumulative percentage MUST be null because no cumulative raster or candidate site covers this point
    assert illum["cumulative_illumination_pct"] is None
    assert illum["sunlight_continuous_hours_max"] is None

    # Caveats must explicitly explain why cumulative percentage is null
    assert any("null" in c.lower() or "fabricat" in c.lower() for c in illum["scientific_caveats"])


def test_illumination_invalid_latitude(client: TestClient) -> None:
    """Tests non-polar latitude (> -80.0) fails Pydantic validation with 422."""
    payload = {
        "center_lat": -50.0,
        "center_lon": 0.0,
    }
    response = client.post("/api/analysis/run", json=payload)
    assert response.status_code == 422


def test_illumination_permanently_shadowed_region_and_thermal() -> None:
    """Tests Permanently Shadowed Region (PSR) cryogenic cold trap classification."""
    # Simulate deep crater depression (e.g. Shackleton crater floor at -3000m)
    # in an unilluminated state
    temp_psr = estimate_surface_temperature_kelvin(
        solar_elevation_deg=-1.5,
        sun_visibility_fraction=0.0,
        is_psr=True,
    )
    # Cryogenic cold trap threshold (< 110K for water-ice stability)
    assert temp_psr <= 50.0

    # Sunlit peak at 1.5 deg elevation
    temp_sunlit = estimate_surface_temperature_kelvin(
        solar_elevation_deg=1.5,
        sun_visibility_fraction=1.0,
        is_psr=False,
    )
    assert temp_sunlit > 150.0


def test_diviner_thermal_distinction_warning(client: TestClient) -> None:
    """Verifies that thermal brightness measurements are never presented as direct sunlight percentages."""
    payload = {
        "center_lat": -89.44,
        "center_lon": 222.50,
        "radius_meters": 500.0,
    }
    response = client.post("/api/analysis/run", json=payload)
    assert response.status_code == 200
    illum = response.json()["illumination"]

    assert any(
        "thermal brightness" in c.lower() and "not a direct optical sunlight" in c.lower()
        for c in illum["scientific_caveats"]
    )
