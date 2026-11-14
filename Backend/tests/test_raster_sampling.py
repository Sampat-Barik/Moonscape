"""Tests for memory-bounded raster sampling and cache manager."""

from pathlib import Path
import numpy as np
import pytest

from Backend.app.services.data_management.cache_manager import cache_manager
from Backend.app.services.geospatial.raster_sampler import raster_sampler


def test_sample_point_missing_file():
    """Verify raster sampler returns None for nonexistent files without crashing."""
    fake_path = Path("D:/nonexistent_dataset.tif")
    val, is_valid, is_nodata = raster_sampler.sample_point_value(fake_path, -89.5, 0.0)
    assert val is None
    assert is_valid is False
    assert is_nodata is False


def test_sample_window_missing_file():
    """Verify raster sampler window returns None for nonexistent files."""
    fake_path = Path("D:/nonexistent_dataset.tif")
    arr, transform, res = raster_sampler.sample_raster_window(fake_path, -89.5, 0.0, radius_m=500.0)
    assert arr is None
    assert transform is None
    assert res == (0.0, 0.0)


def test_cache_manager_point_queries():
    """Verify LRU cache for single-point queries."""
    cache_manager.clear_all()
    cache_manager.put_point_query("test_key_1", {"val": 123.4, "valid": True, "nodata": False})

    cached = cache_manager.get_point_query("test_key_1")
    assert cached is not None
    assert cached["val"] == 123.4

    # Miss
    assert cache_manager.get_point_query("test_key_2") is None


def test_cache_manager_window_queries():
    """Verify LRU cache for raster sub-windows."""
    cache_manager.clear_all()
    dummy_arr = np.zeros((10, 10), dtype=np.float32)
    cache_manager.put_raster_window("win_key_1", dummy_arr, None, (80.0, 80.0))

    arr, transform, res = cache_manager.get_raster_window("win_key_1")
    assert arr is not None
    assert arr.shape == (10, 10)
    assert res == (80.0, 80.0)
