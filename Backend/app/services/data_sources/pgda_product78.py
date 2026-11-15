"""Adapter for NASA PGDA Product 78: High-Resolution 5m/pixel Candidate Landing Site DEMs (Site 01 Connecting Ridge)."""

from typing import Any, Dict, Optional, Tuple
import numpy as np
from affine import Affine

from app.config.dataset_settings import dataset_settings
from app.services.data_sources.base import BaseDataSource
from app.services.geospatial.coordinate_manager import coordinate_manager
from app.services.geospatial.raster_sampler import raster_sampler


class PGDAProduct78Source(BaseDataSource):
    """Scientific adapter for NASA PGDA Product 78 (5m/pixel LOLA Candidate Region DEMs)."""

    SITE_01_BOUNDS = {
        "min_lat": -89.75,
        "max_lat": -89.20,
        "min_lon": 210.0,
        "max_lon": 235.0,
    }

    @property
    def source_id(self) -> str:
        return "pgda_product78"

    @property
    def source_name(self) -> str:
        return "NASA PGDA Product 78 (LOLA 5m/pixel High-Resolution Candidate Site DEM)"

    def is_available(self) -> bool:
        """Returns True if the 5m elevation DEM for Site 01 is installed on disk."""
        surf_def = dataset_settings.datasets.get("pgda78_site01_surf")
        if not surf_def:
            return False
        return surf_def.absolute_local_path.exists()

    def covers_point(self, lat_deg: float, lon_deg: float) -> bool:
        """Checks if coordinate falls inside the Site 01 bounding box (Shackleton connecting ridge)."""
        norm_lon = coordinate_manager.normalize_longitude(lon_deg, target_range="360")
        b = self.SITE_01_BOUNDS
        return (b["min_lat"] <= lat_deg <= b["max_lat"]) and (b["min_lon"] <= norm_lon <= b["max_lon"])

    def sample_point(self, lat_deg: float, lon_deg: float) -> Optional[Dict[str, Any]]:
        """Samples high-resolution 5m elevation, slope, count density, and total uncertainty."""
        if not self.covers_point(lat_deg, lon_deg):
            return None

        surf_def = dataset_settings.datasets.get("pgda78_site01_surf")
        if not surf_def or not surf_def.absolute_local_path.exists():
            return None

        elev_val, is_valid_pt, is_nodata = raster_sampler.sample_point_value(
            surf_def.absolute_local_path, lat_deg, lon_deg, nodata_val=surf_def.nodata
        )
        if not is_valid_pt:
            return None

        # Sample 5m slope
        slope_val = None
        slp_def = dataset_settings.datasets.get("pgda78_site01_slp")
        if slp_def and slp_def.absolute_local_path.exists():
            s_val, _, _ = raster_sampler.sample_point_value(
                slp_def.absolute_local_path, lat_deg, lon_deg, nodata_val=slp_def.nodata
            )
            slope_val = s_val

        # Sample 5m observation count
        count_val = None
        dec_def = dataset_settings.datasets.get("pgda78_site01_ldec")
        if dec_def and dec_def.absolute_local_path.exists():
            c_val, _, _ = raster_sampler.sample_point_value(
                dec_def.absolute_local_path, lat_deg, lon_deg, nodata_val=dec_def.nodata
            )
            count_val = int(c_val) if c_val is not None else None

        # Sample 5m total uncertainty
        toterr_val = None
        toterr_def = dataset_settings.datasets.get("pgda78_site01_toterr")
        if toterr_def and toterr_def.absolute_local_path.exists():
            err_val, _, _ = raster_sampler.sample_point_value(
                toterr_def.absolute_local_path, lat_deg, lon_deg, nodata_val=toterr_def.nodata
            )
            toterr_val = err_val

        # Sample 5m slope error
        slperr_val = None
        slperr_def = dataset_settings.datasets.get("pgda78_site01_slperr")
        if slperr_def and slperr_def.absolute_local_path.exists():
            se_val, _, _ = raster_sampler.sample_point_value(
                slperr_def.absolute_local_path, lat_deg, lon_deg, nodata_val=slperr_def.nodata
            )
            slperr_val = se_val

        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "site_id": "site_01_connecting_ridge",
            "is_nodata": is_nodata,
            "elevation_m": elev_val if not is_nodata else None,
            "slope_deg": slope_val if not is_nodata else None,
            "observation_count": count_val,
            "elevation_uncertainty_m": toterr_val,
            "slope_uncertainty_deg": slperr_val,
            "effective_resolution_m": 5.0,
            "nominal_resolution_m": 5.0,
            "spatial_units": "meters",
            "angular_units": "degrees",
            "crs": "ESRI:104903 (Lunar South Polar Stereographic)",
            "reference_sphere_radius_m": coordinate_manager.RADIUS_METERS,
            "provenance": self.get_provenance(),
        }

    def sample_window(
        self,
        lat_deg: float,
        lon_deg: float,
        radius_m: float,
    ) -> Tuple[Optional[np.ndarray], Optional[Affine], Tuple[float, float]]:
        """Extracts spatial sub-window from 5m candidate region DEM."""
        surf_def = dataset_settings.datasets.get("pgda78_site01_surf")
        if not surf_def or not surf_def.absolute_local_path.exists():
            return None, None, (0.0, 0.0)

        return raster_sampler.sample_raster_window(
            surf_def.absolute_local_path, lat_deg, lon_deg, radius_m
        )

    def get_provenance(self) -> Dict[str, Any]:
        """Returns provenance for Product 78 high-resolution DEMs."""
        return {
            "mission": "Lunar Reconnaissance Orbiter (LRO)",
            "instrument": "Lunar Orbiter Laser Altimeter (LOLA)",
            "archive": "NASA Planetary Geodynamics Laboratory / PDS Geosciences Node",
            "product_url": "https://pgda.gsfc.nasa.gov/products/78",
            "citation": "Barker, M. K., Mazarico, E., Neumann, G. A., et al. (2021). High-resolution lunar south pole digital elevation models from LOLA and LROC. Planetary and Space Science, 203, 105119.",
            "reference_frame": "MOON_ME (Mean Earth / Polar Axis) DE421",
            "datum_radius_m": 1737400.0,
        }


pgda_product78 = PGDAProduct78Source()
