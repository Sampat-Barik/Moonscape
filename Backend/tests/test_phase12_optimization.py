"""Phase 12 Verification Suite — NASA Dataset Optimization and Time-Dependent Lunar Analysis.

Validates:
1. Multi-baseline surface roughness scaling and Nyquist resolution bounds (Barker et al. 2016).
2. 360-degree radial terrain horizon profiles with lunar spherical curvature drop (d^2 / 2*R_moon).
3. SPICE and planetary ephemeris frame coordination (MOON_ME vs ESRI:104903) and fallback reliability.
4. Footprint-based NASA LROC NAC discovery and optical vs altimetry hazard delineation.
5. Time-series Sun and Earth visibility simulation with real topographic horizon masking.
"""

from datetime import datetime, timezone
import math
import numpy as np
import pytest
from fastapi.testclient import TestClient

from Backend.app.main import app
from Backend.app.schemas.simulation import VisibilitySimulationRequest
from Backend.app.services.data_sources.lroc_nac import lroc_nac
from Backend.app.services.spice_service import spice_service
from Backend.app.services.terrain_horizon import terrain_horizon_engine
from Backend.app.services.visibility_simulation import visibility_simulation_service
from Backend.app.services.terrain_analysis import terrain_analysis_engine
from maths.topography import calculate_multi_baseline_roughness
from maths.illumination_geometry import LUNAR_RADIUS_METERS

client = TestClient(app)


# ==============================================================================
# 1. MULTI-BASELINE ROUGHNESS SCALING (Barker et al. 2016 / PGDA 90)
# ==============================================================================

class TestMultiBaselineRoughness:
    """Verifies that surface roughness is evaluated as a function of physical baseline."""

    def test_multi_baseline_roughness_on_synthetic_terrain(self):
        """Verifies multi-scale roughness calculations across distinct physical baselines."""
        # 100x100 synthetic raster at 5m resolution (500m x 500m extent)
        dx = 5.0
        x = np.linspace(0, 10, 100)
        y = np.linspace(0, 10, 100)
        xx, yy = np.meshgrid(x, y)
        # Multi-scale sinusoidal surface: micro-ripples + large undulations
        elev = np.sin(xx * 2.0) * 0.2 + np.cos(yy * 0.5) * 2.5

        results = calculate_multi_baseline_roughness(
            elevation=elev,
            dx_meters=dx,
            candidate_baselines_m=(15.0, 60.0, 100.0, 240.0, 1600.0),
        )

        # 15m baseline (3x3 kernel on 5m DEM): resolvable
        assert "15m" in results
        assert results["15m"]["resolvable"] is True
        assert results["15m"]["kernel_size"] == 3
        assert results["15m"]["actual_baseline_m"] == 15.0
        assert results["15m"]["mean_m"] is not None and results["15m"]["mean_m"] > 0.0

        # 60m baseline (12x12 -> odd 13x13 kernel): resolvable
        assert "60m" in results
        assert results["60m"]["resolvable"] is True
        assert results["60m"]["kernel_size"] == 13
        assert results["60m"]["actual_baseline_m"] == 65.0

        # 1600m baseline requires 320x320 kernel, exceeding 100x100 array bounds
        assert "1600m" in results
        assert results["1600m"]["resolvable"] is False
        assert "exceeds window bounds" in results["1600m"]["status"]

    def test_nyquist_resolution_limit_enforcement(self):
        """Verifies that coarse DEMs (e.g. 80m resolution) reject unresolvable micro-baselines (15m)."""
        # 80m resolution grid
        dx = 80.0
        elev = np.zeros((50, 50), dtype=float)

        results = calculate_multi_baseline_roughness(
            elevation=elev,
            dx_meters=dx,
            candidate_baselines_m=(15.0, 60.0, 240.0, 480.0),
        )

        # 15m and 60m are below the Nyquist limit for an 80m raster (kernel < 3)
        assert results["15m"]["resolvable"] is False
        assert "Nyquist limit" in results["15m"]["status"]
        assert results["60m"]["resolvable"] is False

        # 240m baseline: 3x3 kernel on 80m DEM is resolvable
        assert results["240m"]["resolvable"] is True
        assert results["240m"]["kernel_size"] == 3
        assert results["240m"]["actual_baseline_m"] == 240.0


# ==============================================================================
# 2. 360-DEGREE RADIAL TERRAIN HORIZON ENGINE & LUNAR CURVATURE
# ==============================================================================

class TestTerrainHorizonEngine:
    """Verifies radial ray-tracing and lunar spherical curvature corrections."""

    def test_spherical_curvature_drop_formula(self):
        """Validates physical curvature drop formula: d^2 / (2 * R_moon)."""
        r_5km = 5000.0
        drop_5km = (r_5km**2) / (2.0 * LUNAR_RADIUS_METERS)
        assert pytest.approx(drop_5km, abs=0.1) == 7.19

        r_10km = 10000.0
        drop_10km = (r_10km**2) / (2.0 * LUNAR_RADIUS_METERS)
        assert pytest.approx(drop_10km, abs=0.1) == 28.78

        r_20km = 20000.0
        drop_20km = (r_20km**2) / (2.0 * LUNAR_RADIUS_METERS)
        assert pytest.approx(drop_20km, abs=0.1) == 115.11

    def test_compute_horizon_profile_at_site01(self):
        """Computes 360-degree radial horizon profile for Shackleton Ridge using authentic 5m DEM."""
        profile = terrain_horizon_engine.compute_horizon_profile(
            lat_deg=-89.44,
            lon_deg=222.50,
            search_radius_m=5000.0,
            mast_height_m=2.0,
            num_azimuths=72,
        )

        assert profile.num_azimuths == 72
        assert len(profile.azimuths_deg) == 72
        assert len(profile.horizon_elevations_deg) == 72
        assert profile.curvature_corrected is True
        assert profile.crs == "ESRI:104903"
        assert profile.sky_view_factor > 0.0 and profile.sky_view_factor <= 1.0

        # Circular interpolation test
        h_0 = profile.get_horizon_elevation(0.0)
        h_360 = profile.get_horizon_elevation(360.0)
        assert pytest.approx(h_0, abs=0.001) == h_360

        # Fractional azimuth interpolation
        h_frac = profile.get_horizon_elevation(2.5)
        assert isinstance(h_frac, float)

    def test_horizon_profile_lru_caching(self):
        """Verifies that repeated profile calls are served instantly from cache."""
        lat, lon = -89.44, 222.50
        p1 = terrain_horizon_engine.compute_horizon_profile(lat, lon, search_radius_m=5000.0)
        p2 = terrain_horizon_engine.compute_horizon_profile(lat, lon, search_radius_m=5000.0)
        assert p1 is p2  # Same object reference from memory cache


# ==============================================================================
# 3. SPICE AND PLANETARY EPHEMERIS FRAME COORDINATION
# ==============================================================================

class TestSPICEEphemerisCoordination:
    """Verifies MOON_ME to ESRI:104903 frame harmonization and ephemeris calculations."""

    def test_ephemeris_state_generation(self):
        """Tests that unified ephemeris service returns verified solar and Earth geometry."""
        dt = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
        state = spice_service.get_ephemeris_state(
            lat_deg=-89.44,
            lon_deg=222.50,
            dt_or_iso=dt,
        )

        assert state.lunar_body_fixed_frame == "MOON_ME (IAU Mean Earth/Polar Axis)"
        assert state.dem_projected_crs == "ESRI:104903 (Lunar South Polar Stereographic)"
        assert -1.6 <= state.subsolar_latitude_deg <= 1.6  # Cassini obliquity bound
        assert -7.0 <= state.subearth_latitude_deg <= 7.0  # Libration bound
        assert -8.5 <= state.subearth_longitude_deg <= 8.5
        assert state.sun_distance_au > 0.98 and state.sun_distance_au < 1.02
        assert state.earth_distance_km > 350000.0 and state.earth_distance_km < 410000.0
        assert "ESRI:104903 is a conformal stereographic projection" in state.frame_relationship_summary

    def test_spice_service_metadata_endpoint(self):
        """Tests engine metadata introspection and documentation."""
        meta = spice_service.get_service_metadata()
        assert "active_mode" in meta
        assert meta["body_fixed_frame"] == "MOON_ME (IAU Mean Earth/Polar Axis)"
        assert meta["reference_sphere_radius_m"] == 1737400.0


# ==============================================================================
# 4. FOOTPRINT-BASED LROC NAC DISCOVERY & HAZARD DELINEATION
# ==============================================================================

class TestLROCNACDiscovery:
    """Verifies spatial footprint intersection for targeted high-resolution LROC NAC stereo products."""

    def test_discover_footprints_at_shackleton(self):
        """Discovers intersecting targeted NAC DTMs near Shackleton Connecting Ridge."""
        res = lroc_nac.discover_footprints(
            center_lat=-89.44,
            center_lon=222.50,
            search_radius_meters=5000.0,
        )

        assert res["total_footprints_intersecting"] > 0
        footprint_ids = [f["product_id"] for f in res["footprints"]]
        assert "NAC_DTM_SHACKLETON_01" in footprint_ids or "NAC_DTM_CONNECTING_RIDGE_02" in footprint_ids

        # Verify separation of optical and altimetry hazards
        delineation = res["hazard_detection_delineation"]
        assert "optical_imaging_role" in delineation
        assert "altimetry_dem_role" in delineation
        assert "boulder" in delineation["optical_imaging_role"].lower()
        assert "slopes" in delineation["altimetry_dem_role"].lower()

    def test_lroc_nac_api_endpoint(self):
        """Tests the GET /api/data/lroc/footprints HTTP endpoint."""
        resp = client.get("/api/data/lroc/footprints?lat=-89.44&lon=222.50&radius=10000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_footprints_intersecting"] >= 1
        assert "footprints" in data
        assert "hazard_detection_delineation" in data


# ==============================================================================
# 5. TIME-SERIES VISIBILITY SIMULATION WITH TERRAIN HORIZON MASKING
# ==============================================================================

class TestVisibilitySimulationOptimization:
    """Verifies time-dependent Sun/Earth visibility simulation with cached radial horizon profile."""

    def test_simulate_visibility_with_horizon_profile(self):
        """Executes 7-day visibility simulation at Shackleton Ridge with real horizon masking."""
        req = VisibilitySimulationRequest(
            lat=-89.44,
            lon=222.50,
            start_epoch_iso="2026-10-01T00:00:00Z",
            duration_days=7.0,
            step_hours=2.0,
        )

        res = visibility_simulation_service.simulate_visibility(req)

        assert res.total_steps == int(7.0 * 24.0 / 2.0) + 1
        assert res.horizon_min_deg is not None
        assert res.horizon_max_deg is not None
        assert res.horizon_mean_deg is not None
        assert res.terrain_dataset is not None
        assert res.combined_ops_hours is not None

        # Verify per-step horizon elevation outputs
        step0 = res.time_series[0]
        assert step0.horizon_elevation_sun_deg is not None
        assert step0.horizon_elevation_earth_deg is not None
        assert isinstance(step0.is_combined_ops_available, bool)
