"""Abstract base class for all NASA lunar data source adapters."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
import numpy as np
from affine import Affine


class BaseDataSource(ABC):
    """Abstract interface for scientific lunar data source adapters."""

    @property
    @abstractmethod
    def source_id(self) -> str:
        """Unique identifier for the source adapter."""
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Official name of the NASA dataset/product."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the underlying dataset is verified and accessible on disk or verified remote."""
        pass

    @abstractmethod
    def covers_point(self, lat_deg: float, lon_deg: float) -> bool:
        """Determines whether given planetocentric coordinates fall within the spatial bounds."""
        pass

    @abstractmethod
    def sample_point(self, lat_deg: float, lon_deg: float) -> Optional[Dict[str, Any]]:
        """Samples the point and returns a dictionary with measurement, unit, uncertainty, and provenance."""
        pass

    @abstractmethod
    def sample_window(
        self,
        lat_deg: float,
        lon_deg: float,
        radius_m: float,
    ) -> Tuple[Optional[np.ndarray], Optional[Affine], Tuple[float, float]]:
        """Extracts a memory-efficient spatial sub-window of raster data centered around point."""
        pass

    @abstractmethod
    def get_provenance(self) -> Dict[str, Any]:
        """Returns complete scientific provenance, dataset DOI, and processing citations."""
        pass
