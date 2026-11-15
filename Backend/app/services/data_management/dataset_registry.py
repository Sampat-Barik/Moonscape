"""Central Dataset Registry tracking installation, validation states, and provenance."""

from typing import Dict, List, Optional
from app.config.dataset_settings import (
    DatasetDefinition,
    DatasetStatus,
    dataset_settings,
)
from app.services.data_management.local_storage import local_storage


class DatasetRegistry:
    """Maintains authoritative state, validation results, and access methods for all lunar datasets."""

    def __init__(self):
        self._dataset_states: Dict[str, DatasetStatus] = {}
        self._validation_details: Dict[str, str] = {}
        self.refresh_all_statuses()

    def refresh_all_statuses(self) -> None:
        """Inspects disk files and updates the status of every registered dataset."""
        for d_id, defn in dataset_settings.datasets.items():
            self.refresh_dataset_status(d_id)

    def refresh_dataset_status(self, dataset_id: str) -> DatasetStatus:
        """Evaluates whether a dataset file is installed, valid, or missing."""
        defn = dataset_settings.datasets.get(dataset_id)
        if not defn:
            self._dataset_states[dataset_id] = DatasetStatus.UNAVAILABLE
            return DatasetStatus.UNAVAILABLE

        dest_path = defn.absolute_local_path
        if not dest_path.exists():
            status = DatasetStatus.REMOTE_AVAILABLE if defn.byte_range_supported else DatasetStatus.NOT_INSTALLED
            self._dataset_states[dataset_id] = status
            self._validation_details[dataset_id] = "File not present on local SSD."
            return status

        # Check .part in progress
        part_path = local_storage.get_temp_part_path(defn.filename)
        if part_path.exists() and not dest_path.exists():
            self._dataset_states[dataset_id] = DatasetStatus.PARTIAL
            self._validation_details[dataset_id] = "Download in progress (.part file present)."
            return DatasetStatus.PARTIAL

        # Validate GeoTIFF
        is_valid, reason = local_storage.validate_geotiff(dest_path)
        if is_valid:
            self._dataset_states[dataset_id] = DatasetStatus.AVAILABLE
            self._validation_details[dataset_id] = "Verified authentic GeoTIFF."
            return DatasetStatus.AVAILABLE
        else:
            self._dataset_states[dataset_id] = DatasetStatus.INVALID
            self._validation_details[dataset_id] = f"Validation failed: {reason}"
            return DatasetStatus.INVALID

    def get_status(self, dataset_id: str) -> DatasetStatus:
        """Returns current cached status of a dataset."""
        if dataset_id not in self._dataset_states:
            return self.refresh_dataset_status(dataset_id)
        return self._dataset_states[dataset_id]

    def set_status(self, dataset_id: str, status: DatasetStatus, detail: str = "") -> None:
        """Explicitly updates the status of a dataset (e.g. during active download)."""
        self._dataset_states[dataset_id] = status
        if detail:
            self._validation_details[dataset_id] = detail

    def get_dataset(self, dataset_id: str) -> Optional[DatasetDefinition]:
        """Retrieves dataset definition by ID."""
        return dataset_settings.datasets.get(dataset_id)

    def get_all_datasets(self) -> List[DatasetDefinition]:
        """Returns all registered dataset definitions."""
        return list(dataset_settings.datasets.values())

    def get_installed_datasets(self) -> List[DatasetDefinition]:
        """Returns all datasets whose status is AVAILABLE on local disk."""
        self.refresh_all_statuses()
        return [
            d for d_id, d in dataset_settings.datasets.items()
            if self._dataset_states.get(d_id) == DatasetStatus.AVAILABLE
        ]

    def get_validation_detail(self, dataset_id: str) -> str:
        """Returns diagnostic validation message."""
        return self._validation_details.get(dataset_id, "")


dataset_registry = DatasetRegistry()
