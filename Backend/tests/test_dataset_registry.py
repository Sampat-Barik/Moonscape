"""Tests for NASA dataset registry, manifest parsing, and lifecycle state tracking."""

import pytest
from app.config.dataset_settings import DatasetStatus, dataset_settings
from app.services.data_management.dataset_registry import dataset_registry


def test_manifest_datasets_loaded():
    """Verify that all required NASA datasets are loaded from the manifest."""
    assert len(dataset_settings.datasets) >= 6
    assert "pgda90_ldem" in dataset_settings.datasets
    assert "pgda90_ldsm" in dataset_settings.datasets
    assert "pgda90_ldec" in dataset_settings.datasets
    assert "pgda78_site01_surf" in dataset_settings.datasets


def test_dataset_definition_attributes():
    """Verify definition fields including resolution, URL, and bounds."""
    dem = dataset_settings.datasets["pgda90_ldem"]
    assert dem.spatial_resolution_m == 80.0
    assert dem.units == "meters"
    assert dem.bounds.min_lat == -90.0
    assert dem.bounds.max_lat == -80.0
    assert "pgda.gsfc.nasa.gov" in dem.url
    assert dem.byte_range_supported is True


def test_manifest_profiles():
    """Verify preset download profiles (profile_a, profile_b, profile_c)."""
    profiles = dataset_settings.get_profiles()
    assert "profile_a" in profiles
    assert "profile_b" in profiles
    assert "profile_c" in profiles
    assert "pgda90_ldem" in profiles["profile_b"]["datasets"]
    assert "pgda78_site01_surf" in profiles["profile_c"]["datasets"]


def test_dataset_registry_status_evaluation():
    """Verify status query returns valid DatasetStatus enum."""
    status = dataset_registry.get_status("pgda90_ldem")
    assert isinstance(status, DatasetStatus)
    assert status in [
        DatasetStatus.NOT_INSTALLED,
        DatasetStatus.REMOTE_AVAILABLE,
        DatasetStatus.AVAILABLE,
        DatasetStatus.DOWNLOADING,
    ]
