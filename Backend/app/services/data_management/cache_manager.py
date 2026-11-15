"""Bounded in-memory LRU cache manager protecting 16GB system RAM."""

import sys
import threading
from collections import OrderedDict
from typing import Any, Optional, Tuple
import numpy as np

from app.config.resource_settings import resource_settings
from app.core.logging import logger


class BoundedCacheManager:
    """Thread-safe LRU cache with strict size limits preventing RAM exhaustion."""

    def __init__(self, max_raster_windows: int = resource_settings.MAX_LRU_RASTER_WINDOWS):
        self.max_windows = max_raster_windows
        self._lock = threading.Lock()
        self._window_cache: OrderedDict[str, Tuple[np.ndarray, Any, Any]] = OrderedDict()
        self._coord_query_cache: OrderedDict[str, dict] = OrderedDict()
        self.max_coord_entries = 512

    def get_raster_window(self, key: str) -> Optional[Tuple[np.ndarray, Any, Any]]:
        """Retrieves cached raster window array and transform."""
        with self._lock:
            if key in self._window_cache:
                self._window_cache.move_to_end(key)
                return self._window_cache[key]
            return None

    def put_raster_window(self, key: str, data: np.ndarray, transform: Any, res: Any) -> None:
        """Stores a raster window in LRU cache, evicting oldest if capacity reached."""
        with self._lock:
            if key in self._window_cache:
                self._window_cache.move_to_end(key)
                self._window_cache[key] = (data, transform, res)
                return

            # Evict if full
            while len(self._window_cache) >= self.max_windows:
                evicted_key, (evicted_data, _, _) = self._window_cache.popitem(last=False)
                del evicted_data

            self._window_cache[key] = (data, transform, res)

    def get_point_query(self, key: str) -> Optional[dict]:
        """Retrieves cached single-point query result."""
        with self._lock:
            if key in self._coord_query_cache:
                self._coord_query_cache.move_to_end(key)
                return self._coord_query_cache[key]
            return None

    def put_point_query(self, key: str, result: dict) -> None:
        """Stores single-point query result in LRU cache."""
        with self._lock:
            if key in self._coord_query_cache:
                self._coord_query_cache.move_to_end(key)
                self._coord_query_cache[key] = result
                return

            while len(self._coord_query_cache) >= self.max_coord_entries:
                self._coord_query_cache.popitem(last=False)

            self._coord_query_cache[key] = result

    def clear(self) -> None:
        """Clears all in-memory cached entries."""
        with self._lock:
            self._window_cache.clear()
            self._coord_query_cache.clear()

    def clear_all(self) -> None:
        """Alias for clearing all caches."""
        self.clear()


cache_manager = BoundedCacheManager()
