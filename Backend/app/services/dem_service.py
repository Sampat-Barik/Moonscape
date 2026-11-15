"""Geospatial service for windowed access to NASA LOLA lunar elevation rasters."""

import math
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import rasterio
from rasterio.windows import Window, from_bounds
from affine import Affine

from app.core.config import settings
from app.core.constants import LOLA_NODATA_VALUE, MOON_RADIUS_METERS
from app.core.logging import logger
from maths.geodesy import (
    latlon_to_polar_stereo as _math_latlon_to_polar_stereo,
    polar_stereo_to_latlon as _math_polar_stereo_to_latlon,
)


class DEMService:
    """Manages windowed I/O, coordinate conversions, and raster sampling for NASA LOLA DEMs."""

    def __init__(self, dem_path: Optional[Path] = None):
        self.dem_path = dem_path or settings.resolved_dem_path

    def is_available(self) -> bool:
        """Returns True if the underlying DEM GeoTIFF file exists and can be opened."""
        return self.dem_path.exists()

    @staticmethod
    def latlon_to_polar_stereo(lat_deg: float, lon_deg: float) -> Tuple[float, float]:
        """Converts Moon planetocentric latitude and longitude to Lunar South Pole Stereographic coordinates (meters)."""
        return _math_latlon_to_polar_stereo(lat_deg, lon_deg, radius_m=MOON_RADIUS_METERS)

    @staticmethod
    def polar_stereo_to_latlon(x: float, y: float) -> Tuple[float, float]:
        """Converts Lunar South Pole Stereographic coordinates (meters) to planetocentric lat/lon (degrees)."""
        return _math_polar_stereo_to_latlon(x, y, radius_m=MOON_RADIUS_METERS)

    def get_elevation_at_point(self, lat_deg: float, lon_deg: float) -> Tuple[Optional[float], bool, bool]:
        """Extracts single-point elevation from the DEM without loading the entire raster.

        Returns:
            (elevation_m, is_valid_point, is_nodata)
        """
        # Must be in configured lunar South Pole exploration region (-90 to -70 deg)
        if not (-90.0 <= lat_deg <= -70.0):
            return None, False, False

        # Priority 1: Check if covered by verified high-res NASA Product 78 (Site 01)
        try:
            from app.config.dataset_settings import dataset_settings
            from app.services.data_sources.pgda_product78 import pgda_product78
            from app.services.geospatial.raster_sampler import raster_sampler

            if pgda_product78.is_available() and pgda_product78.covers_point(lat_deg, lon_deg):
                surf_def = dataset_settings.datasets.get("pgda78_site01_surf")
                if surf_def and surf_def.absolute_local_path.exists():
                    val, valid, nodata = raster_sampler.sample_point_value(
                        surf_def.absolute_local_path, lat_deg, lon_deg, nodata_val=surf_def.nodata
                    )
                    if valid:
                        return val, valid, nodata
        except Exception:
            pass

        if not self.is_available():
            logger.warning("DEM dataset file not available at %s", self.dem_path)
            return None, False, False

        x, y = self.latlon_to_polar_stereo(lat_deg, lon_deg)

        try:
            with rasterio.open(self.dem_path) as src:
                # Convert projected coordinates (x, y) to raster row, col
                row, col = src.index(x, y)

                # Bounds check
                if not (0 <= row < src.height and 0 <= col < src.width):
                    return None, False, False

                # Read a 1x1 window
                window = Window(col_off=col, row_off=row, width=1, height=1)
                data = src.read(1, window=window)

                val = float(data[0, 0])
                if val == LOLA_NODATA_VALUE or math.isnan(val) or val <= -30000:
                    return None, True, True

                return val, True, False
        except Exception as e:
            logger.error("Error reading elevation at point (%f, %f): %s", lat_deg, lon_deg, str(e))
            return None, False, False

    def read_window_around_point(
        self,
        lat_deg: float,
        lon_deg: float,
        radius_m: float,
    ) -> Tuple[Optional[np.ndarray], Optional[Affine], Tuple[float, float]]:
        """Reads a spatial window of raster pixels centered around coordinates.

        Memory-efficient: Only reads the requested bounding box into RAM.
        Prefers verified high-resolution NASA rasters (Product 78) when available.

        Returns:
            (elevation_array, window_affine_transform, (pixel_res_x, pixel_res_y))
        """
        # Priority 1: Check if covered by verified high-res NASA Product 78 (Site 01)
        try:
            from app.config.dataset_settings import dataset_settings
            from app.services.data_sources.pgda_product78 import pgda_product78
            from app.services.geospatial.raster_sampler import raster_sampler

            if pgda_product78.is_available() and pgda_product78.covers_point(lat_deg, lon_deg):
                surf_def = dataset_settings.datasets.get("pgda78_site01_surf")
                if surf_def and surf_def.absolute_local_path.exists():
                    data, win_transform, res = raster_sampler.sample_raster_window(
                        surf_def.absolute_local_path, lat_deg, lon_deg, radius_m=radius_m
                    )
                    if data is not None and data.size > 0:
                        return data, win_transform, res
        except Exception:
            pass

        if not self.is_available():
            return None, None, (0.0, 0.0)

        x, y = self.latlon_to_polar_stereo(lat_deg, lon_deg)
        left = x - radius_m
        right = x + radius_m
        bottom = y - radius_m
        top = y + radius_m

        try:
            with rasterio.open(self.dem_path) as src:
                # Window from spatial bounds
                window = from_bounds(left, bottom, right, top, transform=src.transform)

                # Clip window to raster extent to avoid out-of-bounds errors
                full_window = Window(0, 0, src.width, src.height)
                clipped_window = window.intersection(full_window)

                if clipped_window.width <= 0 or clipped_window.height <= 0:
                    return None, None, (0.0, 0.0)

                data = src.read(1, window=clipped_window)
                win_transform = src.window_transform(clipped_window)
                pixel_res = (src.res[0], src.res[1])

                return data, win_transform, pixel_res
        except Exception as e:
            logger.error("Error reading raster window around (%f, %f): %s", lat_deg, lon_deg, str(e))
            return None, None, (0.0, 0.0)


dem_service = DEMService()
