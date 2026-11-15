"""Tests for ML Landing Suitability Model v2.0:
Scientific validation, strict zero-leakage geographic holdout, critical feature enforcement,
zero-preservation, and hard mission constraint gating.
"""

import pytest
from app.schemas.ml_scoring import LunarSiteFeatures
from app.services.ml.suitability_model_service import suitability_model_service


def test_v2_model_artifacts_loaded() -> None:
    """Verifies that the v2 model artifact and metadata load with correct attributes."""
    loaded = suitability_model_service._ensure_model_loaded()
    assert loaded is True
    meta = suitability_model_service._metadata
    assert meta is not None
    assert meta["version"] == "2.0.0"
    assert meta["model_file"] == "landing_suitability_rf_v2.joblib"
    assert meta["trained_features_count"] == 24
    assert meta["selection_criterion"] == "Highest Validation R2 (strict zero-leakage geographic holdout)"
    assert meta["spatial_leakage_audit"]["spatial_leakage_detected"] is False


def test_refusal_on_missing_slope() -> None:
    """Verifies that inference returns insufficient_data when slope is omitted."""
    raw = {
        "roughness_m": 0.25,
        "elevation_m": 500.0,
        "illumination_pct": 80.0,
    }
    result = suitability_model_service.predict_suitability(raw, strict=False)
    assert result.status == "insufficient_data"
    assert result.ml_suitability_score == 0.0
    assert result.predicted_class == "disqualified"
    assert "mean_slope_deg" in result.missing_critical_features


def test_strict_mode_raises_on_missing_critical() -> None:
    """Verifies that strict=True raises ValueError on missing critical parameters."""
    with pytest.raises(ValueError, match="Missing safety-critical landing parameters"):
        suitability_model_service.predict_suitability({"roughness_m": 0.25}, strict=True)


def test_preservation_of_valid_zeros() -> None:
    """Verifies that valid physical zero values (flat plain, PSR darkness, 0 boulders) are preserved."""
    raw = {
        "slope_deg": 0.0,  # Completely flat
        "elevation_m": 0.0,  # Reference lunar sphere radius 1737.4 km
        "roughness_m": 0.15,
        "boulder_density_km2": 0.0,  # Zero detected rocks
        "crater_density_km2": 0.0,
        "cumulative_sunlight_pct": 0.0,  # Deep PSR
        "is_psr": 1,
    }
    features = suitability_model_service.construct_features_from_dict(raw, allow_imputation=True)
    assert features.mean_slope_deg == 0.0
    assert features.mean_elevation_m == 0.0
    assert features.boulder_density_km2 == 0.0
    assert features.crater_density_km2 == 0.0
    assert features.cumulative_sunlight_pct == 0.0
    assert features.is_psr == 1


def test_hard_constraint_capping_at_35() -> None:
    """Verifies that hard constraint violations (slope > 15 deg) cap ML score at <= 35.0."""
    raw = {
        "slope_deg": 22.0,  # Far above 15 deg tip-over limit
        "roughness_m": 0.20,
        "elevation_m": 1200.0,
        "illumination_pct": 98.0,
    }
    result = suitability_model_service.predict_suitability(raw, mission_profile="artemis_hls")
    assert result.hard_constraint_status == "violated"
    assert result.predicted_class == "disqualified"
    assert result.ml_suitability_score <= 35.0
    assert any("tip-over limit" in v for v in result.hard_constraint_violations)


def test_data_completeness_calculation() -> None:
    """Verifies that data completeness percentage is calculated and returned."""
    raw = {
        "slope_deg": 4.5,
        "roughness_m": 0.22,
        "elevation_m": 800.0,
    }
    result = suitability_model_service.predict_suitability(raw)
    assert 10.0 <= result.data_completeness_pct <= 100.0
    assert result.status in ["success", "partial_data"]
