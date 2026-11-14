"""Phase 11: Scientific Regression and Comprehensive System Audit Test Suite.

Verifies:
1. Earth visibility ephemeris, optical librations, and RF communication corridors.
2. Next sunset and sunrise event root solvers at lunar South Pole coordinates.
3. Automated contiguous landing-site detection from real NASA DEM rasters.
4. Time-based Sun/Earth visibility simulation across 14-day lunar diurnal intervals.
5. End-to-end API integration for new scientific endpoints (/api/sites/detect, /api/simulation/visibility).
"""

import math
from datetime import datetime, timezone
import numpy as np
import pytest
from fastapi.testclient import TestClient

from Backend.app.core.constants import MOON_RADIUS_METERS
from Backend.app.main import app
from Backend.app.schemas.simulation import VisibilitySimulationRequest
from Backend.app.schemas.site_detection import DetectLandingSitesRequest
from Backend.app.services.landing_site_detection import landing_site_detection_service
from Backend.app.services.visibility_simulation import visibility_simulation_service
from maths.earth_visibility import (
    calculate_earth_elevation_and_azimuth,
    calculate_earth_visibility_fraction,
    calculate_subearth_coordinates,
    evaluate_communication_link,
)
from maths.illumination_geometry import find_next_sunset_and_sunrise


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ==============================================================================
# 1. EARTH VISIBILITY & COMMUNICATION MATHEMATICS
# ==============================================================================

class TestEarthVisibilityScience:
    """Verifies lunar optical libration and Earth line-of-sight communication physics."""

    def test_subearth_coordinates_libration_bounds(self):
        """Verifies that sub-Earth optical/physical librations stay within physical limits (~±8°)."""
        for month in range(1, 13):
            dt = datetime(2026, month, 15, 0, 0, tzinfo=timezone.utc)
            sub_lat, sub_lon, dist_km = calculate_subearth_coordinates(dt)

            # Sub-Earth latitude oscillates within ~±6.7°
            assert abs(sub_lat) <= 8.0, f"Sub-Earth latitude {sub_lat}° exceeded physical libration envelope"
            # Sub-Earth longitude oscillates within ~±7.9°
            assert abs(sub_lon) <= 10.0, f"Sub-Earth longitude {sub_lon}° exceeded physical libration envelope"
            # Earth-Moon distance between perigee (~356,500 km) and apogee (~406,700 km)
            assert 350000.0 <= dist_km <= 415000.0, f"Earth-Moon distance {dist_km} km out of bounds"

    def test_earth_elevation_at_south_pole(self):
        """At South Pole (lat = -90°), Earth elevation equals -sub_earth_lat."""
        dt = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)
        sub_lat, sub_lon, _ = calculate_subearth_coordinates(dt)
        earth_elev, earth_az = calculate_earth_elevation_and_azimuth(
            lat_deg=-90.0, lon_deg=0.0, subearth_lat_deg=sub_lat, subearth_lon_deg=sub_lon
        )
        expected_elev = -sub_lat
        assert math.isclose(earth_elev, expected_elev, abs_tol=0.01), (
            f"Polar Earth elevation {earth_elev}° does not match expected {-sub_lat}°"
        )

    def test_communication_link_margins(self):
        """Operational communication requires elevation >= 2.0° and unocculted fraction >= 0.5."""
        # Case 1: High Earth, unocculted -> Operational
        is_op, _ = evaluate_communication_link(earth_elevation_deg=5.0, visibility_fraction=1.0)
        assert is_op is True

        # Case 2: Negative elevation (below horizon) -> Blackout
        is_op, rationale = evaluate_communication_link(earth_elevation_deg=-1.5, visibility_fraction=0.0)
        assert is_op is False
        assert "below" in rationale.lower()

        # Case 3: Low elevation (0.5°) -> Marginal/Rejected due to multipath
        is_op, rationale = evaluate_communication_link(earth_elevation_deg=0.5, visibility_fraction=1.0)
        assert is_op is False
        assert "multi-path" in rationale.lower()

        # Case 4: Severe terrain occultation (fraction = 0.2) -> Rejected
        is_op, rationale = evaluate_communication_link(earth_elevation_deg=4.0, visibility_fraction=0.2)
        assert is_op is False
        assert "margin" in rationale.lower()


# ==============================================================================
# 2. SUNSET AND SUNRISE TEMPORAL PREDICTION
# ==============================================================================

class TestSunsetSunrisePrediction:
    """Verifies polar sunrise and sunset event solvers."""

    def test_sunset_sunrise_solver_execution(self):
        """Tests that root-solver identifies polar horizon crossing events within 35 days."""
        # Test 1: At 82°S in March (transition season), sunset occurs within ~11 days
        dt_start = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)
        sunset_iso, sunrise_iso, duration_h = find_next_sunset_and_sunrise(
            lat_deg=-82.0,
            lon_deg=0.0,
            start_dt=dt_start,
            horizon_elevation_deg=0.0,
            max_search_days=35.0,
        )
        assert sunset_iso is not None
        assert sunrise_iso is not None
        assert duration_h is not None and duration_h > 0.0

        # Test 2: At Shackleton Ridge (-89.44°) in October (southern polar summer),
        # the sun remains above the horizon continuously ("peak of eternal light" / midnight sun)
        dt_summer = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
        sunset_sum, _, _ = find_next_sunset_and_sunrise(
            lat_deg=-89.44,
            lon_deg=222.50,
            start_dt=dt_summer,
            horizon_elevation_deg=0.0,
            max_search_days=35.0,
        )
        assert sunset_sum is None  # Continuous daylight; no sunset occurs within the 35-day window


# ==============================================================================
# 3. CONTIGUOUS LANDING SITE DETECTION
# ==============================================================================

class TestLandingSiteDetection:
    """Verifies automated contiguous safe landing zone delineation from real DEM rasters."""

    def test_detect_candidate_sites_service(self):
        """Runs landing site detection at Site 01 Shackleton Ridge using authentic 5m DEM."""
        req = DetectLandingSitesRequest(
            center_lat=-89.44,
            center_lon=222.50,
            search_radius_meters=1000.0,
            max_slope_deg=10.0,
            max_roughness_m=0.40,
            min_landing_diameter_meters=40.0,
        )
        res = landing_site_detection_service.detect_candidate_sites(req)
        assert res.status == "success"
        assert res.total_sites_detected >= 1

        top_zone = res.candidate_zones[0]
        assert top_zone.safety_rank == 1
        assert top_zone.effective_diameter_m >= 40.0
        assert top_zone.mean_slope_deg <= 10.0
        assert top_zone.suitability_score > 50.0
        assert -90.0 <= top_zone.centroid_lat <= -80.0

    def test_detect_candidate_sites_rejects_tiny_footprints(self):
        """Ensures that patches smaller than minimum landing diameter are strictly rejected."""
        req_strict = DetectLandingSitesRequest(
            center_lat=-89.44,
            center_lon=222.50,
            search_radius_meters=500.0,
            max_slope_deg=4.0,  # very strict slope
            min_landing_diameter_meters=500.0,  # unrealistically large contiguous circle
        )
        res = landing_site_detection_service.detect_candidate_sites(req_strict)
        # Should reject because no 500m flat contiguous patch exists on this ridge
        assert res.total_sites_detected == 0 or all(z.effective_diameter_m >= 500.0 for z in res.candidate_zones)

    def test_detect_candidate_sites_api_endpoint(self, client: TestClient):
        """Verifies POST /api/sites/detect HTTP contract."""
        payload = {
            "center_lat": -89.44,
            "center_lon": 222.50,
            "search_radius_meters": 800.0,
            "max_slope_deg": 10.0,
            "min_landing_diameter_meters": 30.0,
        }
        res = client.post("/api/sites/detect", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "candidate_zones" in data
        assert len(data["candidate_zones"]) >= 1


# ==============================================================================
# 4. TIME-BASED SUN/EARTH VISIBILITY SIMULATION
# ==============================================================================

class TestVisibilitySimulation:
    """Verifies temporal Sun/Earth visibility time series propagation."""

    def test_simulate_visibility_service(self):
        """Runs a 7-day visibility simulation at 6-hour intervals."""
        req = VisibilitySimulationRequest(
            lat=-89.44,
            lon=222.50,
            start_epoch_iso="2026-10-15T00:00:00Z",
            duration_days=7.0,
            step_hours=6.0,
        )
        res = visibility_simulation_service.simulate_visibility(req)
        assert res.total_steps == 29  # (7 * 24 / 6) + 1
        assert len(res.time_series) == 29
        assert 0.0 <= res.sunlight_percentage <= 100.0
        assert 0.0 <= res.earth_comm_percentage <= 100.0
        assert res.max_continuous_sunlight_hours >= 0.0

        first_step = res.time_series[0]
        assert first_step.elapsed_hours == 0.0
        assert -90.0 <= first_step.solar_elevation_deg <= 90.0
        assert first_step.communication_status in ["operational", "marginal", "blackout"]

    def test_simulate_visibility_api_endpoint(self, client: TestClient):
        """Verifies POST /api/simulation/visibility HTTP contract."""
        payload = {
            "lat": -89.44,
            "lon": 222.50,
            "duration_days": 3.0,
            "step_hours": 3.0,
        }
        res = client.post("/api/simulation/visibility", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["query_lat"] == -89.44
        assert len(data["time_series"]) == 25  # (3 * 24 / 3) + 1
        assert "total_sunlight_hours" in data
        assert "total_earth_comm_hours" in data
