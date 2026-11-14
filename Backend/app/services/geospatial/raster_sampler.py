"""Memory-efficient windowed raster sampler using Rasterio and Lunar Polar Stereographic geodetics."""

import math
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import rasterio
from affine import Affine
from rasterio.windows import Window, from_bounds

from Backend.app.config.resource_settings import resource_settings
from Backend.app.core.constants import LOLA_NODATA_VALUE
from Backend.app.core.logging import logger
from Backend.app.services.data_management.cache_manager import cache_manager
from Backend.app.services.geospatial.coordinate_manager import coordinate_manager


class RasterSampler:
    """Provides memory-bounded windowed reads and single-pixel extraction from NASA GeoTIFFs."""

    @staticmethod
    def sample_point_value(
        raster_path: Path,
        lat_deg: float,
        lon_deg: float,
        nodata_val: float = LOLA_NODATA_VALUE,
    ) -> Tuple[Optional[float], bool, bool]:
        """Extracts a single pixel from a GeoTIFF without loading the entire raster array.

        Returns:
            (value, is_valid_point, is_nodata)
        """
        if not raster_path.exists():
            return None, False, False

        cache_key = f"pt:{raster_path.name}:{lat_deg:.6f}:{lon_deg:.6f}"
        cached = cache_manager.get_point_query(cache_key)
        if cached is not None:
            return cached["val"], cached["valid"], cached["nodata"]

        try:
            x, y = coordinate_manager.to_polar_stereographic(lat_deg, lon_deg)
        except Exception:
            return None, False, False

        try:
            with rasterio.open(raster_path) as src:
                row, col = src.index(x, y)
                if not (0 <= row < src.height and 0 <= col < src.width):
                    res = (None, False, False)
                    cache_manager.put_point_query(cache_key, {"val": None, "valid": False, "nodata": False})
                    return res

                # Read a single pixel window (1x1)
                win = Window(col_off=col, row_off=row, width=1, height=1)
                data = src.read(1, window=win)
                val = float(data[0, 0])

                if val == nodata_val or val <= -30000.0 or math.isnan(val):
                    res = (None, True, True)
                    cache_manager.put_point_query(cache_key, {"val": None, "valid": True, "nodata": True})
                    return res

                res = (round(val, 2), True, False)
                cache_manager.put_point_query(cache_key, {"val": res[0], "valid": True, "nodata": False})
                return res
        except Exception as e:
            logger.error("Raster sampler error on %s: %s", raster_path.name, str(e))
            return None, False, False

    @staticmethod
    def sample_raster_window(
        raster_path: Path,
        lat_deg: float,
        lon_deg: float,
        radius_m: float,
    ) -> Tuple[Optional[np.ndarray], Optional[Affine], Tuple[float, float]]:
        """Reads a small bounding box sub-window into memory, bounded by MAX_PER_REQUEST_WINDOW_PIXELS.

        Returns:
            (2D numpy array, window Affine transform, (res_x, res_y))
        """
        if not raster_path.exists():
            return None, None, (0.0, 0.0)

        cache_key = f"win:{raster_path.name}:{lat_deg:.4f}:{lon_deg:.4f}:{int(radius_m)}"
        cached = cache_manager.get_raster_window(cache_key)
        if cached is not None:
            return cached

        try:
            x, y = coordinate_manager.to_polar_stereographic(lat_deg, lon_deg)
        except Exception:
            return None, None, (0.0, 0.0)

        left = x - radius_m
        right = x + radius_m
        bottom = y - radius_m
        top = y + radius_m

        try:
            with rasterio.open(raster_path) as src:
                window = from_bounds(left, bottom, right, top, transform=src.transform)
                full_extent = Window(0, 0, src.width, src.height)
                clipped = window.intersection(full_extent)

                if clipped.width <= 0 or clipped.height <= 0:
                    return None, None, (0.0, 0.0)

                # Cap max window to protect RAM limit
                max_dim = resource_settings.MAX_PER_REQUEST_WINDOW_PIXELS
                if clipped.width > max_dim or clipped.height > max_dim:
                    logger.warning("Requested window (%d x %d) exceeds limit (%d). Clamping.", clipped.width, clipped.height, max_dim)
                    col_off = clipped.col_off + (clipped.width - min(clipped.width, max_dim)) // 2
                    row_off = clipped.row_off + (clipped.height - min(clipped.height, max_dim)) // 2
                    clipped = Window(col_off, row_off, min(clipped.width, max_dim), min(clipped.height, max_dim))

                data = src.read(1, window=clipped)
                win_transform = src.window_transform(clipped)
                res = (src.res[0], src.res[1])

                cache_manager.put_raster_window(cache_key, data, win_transform, res)
                return data, win_transform, res
        except Exception as e:
            logger.error("Error reading window on %s: %s", raster_path.name, str(e))
            return None, None, (0.0, 0.0)


raster_sampler = RasterSampler()
