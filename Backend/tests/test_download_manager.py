"""Tests for background download task tracking and management."""

import pytest
from Backend.app.config.dataset_settings import dataset_settings
from Backend.app.services.data_management.download_manager import DownloadTask, download_manager


def test_download_task_serialization():
    """Verify DownloadTask converts to structured dictionary."""
    defn = dataset_settings.datasets["pgda90_ldem"]
    task = DownloadTask("DL-TEST1234", defn)

    d = task.to_dict()
    assert d["task_id"] == "DL-TEST1234"
    assert d["dataset_id"] == "pgda90_ldem"
    assert d["status"] == "queued"
    assert d["progress_pct"] == 0.0
    assert d["bytes_downloaded"] == 0
    assert d["total_bytes"] == defn.size_bytes


def test_cancel_nonexistent_task():
    """Verify cancelling nonexistent task returns False."""
    assert download_manager.cancel_task("DL-NONEXISTENT") is False


def test_get_nonexistent_task():
    """Verify getting nonexistent task returns None."""
    assert download_manager.get_task("DL-NONEXISTENT") is None


def test_task_cancellation_lifecycle():
    """Verify that an enqueued task can be cancelled cleanly."""
    defn = dataset_settings.datasets["pgda90_ldsm"]
    task = DownloadTask("DL-CANCELME", defn)
    download_manager._tasks["DL-CANCELME"] = task

    assert download_manager.cancel_task("DL-CANCELME") is True
    assert task.status == "cancelled"
    assert task.cancelled is True
