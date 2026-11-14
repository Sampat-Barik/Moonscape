"""Adapter for NASA PGDA Product 90: LOLA South Pole 80m Regional Polar DEM & Topography."""

from typing import Any, Dict, Optional, Tuple
import numpy as np
from affine import Affine

from Backend.app.config.dataset_settings import dataset_settings
from Backend.app.core.constants import LOLA_NODATA_VALUE
from Backend.app.services.data_sources.base import BaseDataSource
from Backend.app.services.geospatial.coordinate_manager import coordinate_manager
from Backend.app.services.geospatial.raster_sampler import raster_sampler


class PGDAProduct90Source(BaseDataSource):
    """Scientific adapter for NASA PGDA Product 90 (LRO LOLA South Pole 80m rasters)."""

    @property
    def source_id(self) -> str:
        return "pgda_product90"

    @property
    def source_name(self) -> str:
        return "NASA PGDA Product 90 (LOLA South Pole 80m Regional Foundation)"

    def is_available(self) -> bool:
        """Returns True if the primary 80m elevation GeoTIFF is installed and validated on disk."""
        dem_def = dataset_settings.datasets.get("pgda90_ldem")
        if not dem_def:
            return False
        return dem_def.absolute_local_path.exists()

    def covers_point(self, lat_deg: float, lon_deg: float) -> bool:
        """Covers all longitudes in the Lunar South Pole disk (-90.0° to -80.0°)."""
        return coordinate_manager.is_in_south_pole_zone(lat_deg)

    def sample_point(self, lat_deg: float, lon_deg: float) -> Optional[Dict[str, Any]]:
        """Samples elevation, slope, count density, and uncertainty metrics from 80m rasters."""
        if not self.covers_point(lat_deg, lon_deg):
            return None

        # Sample primary elevation
        dem_def = dataset_settings.datasets.get("pgda90_ldem")
        if not dem_def or not dem_def.absolute_local_path.exists():
            return None

        elev_val, is_valid_pt, is_nodata = raster_sampler.sample_point_value(
            dem_def.absolute_local_path, lat_deg, lon_deg, nodata_val=dem_def.nodata
        )
        if not is_valid_pt:
            return None

        # Sample slope
        slope_val = None
        slp_def = dataset_settings.datasets.get("pgda90_ldsm")
        if slp_def and slp_def.absolute_local_path.exists():
            s_val, _, _ = raster_sampler.sample_point_value(
                slp_def.absolute_local_path, lat_deg, lon_deg, nodata_val=slp_def.nodata
            )
            slope_val = s_val

        # Sample observation count
        count_val = None
        dec_def = dataset_settings.datasets.get("pgda90_ldec")
        if dec_def and dec_def.absolute_local_path.exists():
            c_val, _, _ = raster_sampler.sample_point_value(
                dec_def.absolute_local_path, lat_deg, lon_deg, nodata_val=dec_def.nodata
            )
            count_val = int(c_val) if c_val is not None else None

        # Sample elevation error (uncertainty)
        elev_err_val = None
        err_def = dataset_settings.datasets.get("pgda90_ldem_err")
        if err_def and err_def.absolute_local_path.exists():
            e_err, _, _ = raster_sampler.sample_point_value(
                err_def.absolute_local_path, lat_deg, lon_deg, nodata_val=err_def.nodata
            )
            elev_err_val = e_err

        # Sample slope error
        slope_err_val = None
        slperr_def = dataset_settings.datasets.get("pgda90_ldsm_err")
        if slperr_def and slperr_def.absolute_local_path.exists():
            s_err, _, _ = raster_sampler.sample_point_value(
                slperr_def.absolute_local_path, lat_deg, lon_deg, nodata_val=slperr_def.nodata
            )
            slope_err_val = s_err

        # Sample effective spatial resolution
        effres_val = None
        eff_def = dataset_settings.datasets.get("pgda90_ldem_effres")
        if eff_def and eff_def.absolute_local_path.exists():
            eff, _, _ = raster_sampler.sample_point_value(
                eff_def.absolute_local_path, lat_deg, lon_deg, nodata_val=eff_def.nodata
            )
            effres_val = eff

        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "is_nodata": is_nodata,
            "elevation_m": elev_val if not is_nodata else None,
            "slope_deg": slope_val if not is_nodata else None,
            "observation_count": count_val,
            "elevation_uncertainty_m": elev_err_val,
            "slope_uncertainty_deg": slope_err_val,
            "effective_resolution_m": effres_val or 80.0,
            "nominal_resolution_m": 80.0,
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
        """Extracts spatial sub-window of elevation raster around target coordinate."""
        dem_def = dataset_settings.datasets.get("pgda90_ldem")
        if not dem_def or not dem_def.absolute_local_path.exists():
            return None, None, (0.0, 0.0)

        return raster_sampler.sample_raster_window(
            dem_def.absolute_local_path, lat_deg, lon_deg, radius_m
        )

    def get_provenance(self) -> Dict[str, Any]:
        """Returns NASA metadata, citations, and reference frame specs."""
        return {
            "mission": "Lunar Reconnaissance Orbiter (LRO)",
            "instrument": "Lunar Orbiter Laser Altimeter (LOLA)",
            "archive": "NASA Planetary Geodynamics Laboratory / PDS Geosciences Node",
            "product_url": "https://pgda.gsfc.nasa.gov/products/90",
            "citation": "Barker, M. K., Mazarico, E., Neumann, G. A., et al. (2016). Lunar Orbiter Laser Altimeter (LOLA) South Pole 80m DEM, NASA Planetary Data System.",
            "reference_frame": "MOON_ME (Mean Earth / Polar Axis) DE421",
            "datum_radius_m": 1737400.0,
        }


pgda_product90 = PGDAProduct90Source()
