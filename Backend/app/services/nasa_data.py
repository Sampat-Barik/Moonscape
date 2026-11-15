"""NASA Lunar Data Service for Moonscape.

Provides unified access to official NASA LOLA polar elevation and slope rasters,
extracting physical distance-bounded spatial windows with full geodetic tracing.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from affine import Affine
import numpy as np

from app.config.dataset_settings import dataset_settings
from app.core.constants import (
    LOLA_DATASET_NAME,
    LOLA_NODATA_VALUE,
    LOLA_PRODUCT_ID,
    LOLA_SPATIAL_RESOLUTION_M,
    LOLA_VERTICAL_ACCURACY_M,
)
from app.services.data_sources.pgda_product78 import pgda_product78
from app.services.data_sources.pgda_product90 import pgda_product90
from app.services.dem_service import dem_service
from app.services.geospatial.coordinate_manager import coordinate_manager
from app.services.geospatial.raster_sampler import raster_sampler
from app.services.geospatial.terrain_source_selector import terrain_source_selector


@dataclass
class NASASpatialWindow:
    """Encapsulates a physical distance-bounded window extracted from NASA lunar rasters."""

    elevation_data: np.ndarray
    slope_data: Optional[np.ndarray]
    transform: Affine
    dx_meters: float
    dy_meters: float
    center_x_meters: float
    center_y_meters: float
    nodata_value: float
    source_tier: str
    source_id: str
    dataset_name: str
    product_id: str
    source_url: str
    citation: str
    crs: str
    reference_frame: str
    is_measured_data: bool
    elevation_units: str = "meters"
    slope_units: str = "degrees"
    vertical_uncertainty_m: Optional[float] = None
    slope_uncertainty_deg: Optional[float] = None
    effective_resolution_m: Optional[float] = None
    observation_count: Optional[int] = None
    quality_warnings: Optional[str] = None


class NASADataManager:
    """Manages acquisition of spatial raster windows from verified NASA lunar sources."""

    CRS_ESRI_104903: str = "ESRI:104903 (Lunar South Polar Stereographic)"
    REFERENCE_FRAME_DE421: str = "MOON_ME (Mean Earth / Polar Axis) DE421, R=1737400m"

    @classmethod
    def get_spatial_window(
        cls,
        lat_deg: float,
        lon_deg: float,
        radius_m: float,
    ) -> Optional[NASASpatialWindow]:
        """Extracts spatial sub-windows of elevation and slope for requested location and physical radius in meters."""
        is_valid, _ = coordinate_manager.validate_coordinates(lat_deg, lon_deg)
        if not is_valid or not coordinate_manager.is_in_analysis_region(lat_deg):
            return None

        # Determine center in projection coordinates
        center_x, center_y = coordinate_manager.to_polar_stereographic(lat_deg, lon_deg)
        source_id = terrain_source_selector.select_source(lat_deg, lon_deg)

        # ------------------------------------------------------------------
        # 1. Product 78 (5 m/pixel LOLA Candidate Region DEM - Site 01)
        # ------------------------------------------------------------------
        if source_id == "pgda_product78":
            surf_def = dataset_settings.datasets.get("pgda78_site01_surf")
            slp_def = dataset_settings.datasets.get("pgda78_site01_slp")
            toterr_def = dataset_settings.datasets.get("pgda78_site01_toterr")
            slperr_def = dataset_settings.datasets.get("pgda78_site01_slperr")
            ldec_def = dataset_settings.datasets.get("pgda78_site01_ldec")

            read_radius = max(radius_m, 25.0)
            elev_arr, transform, res = raster_sampler.sample_raster_window(
                surf_def.absolute_local_path, lat_deg, lon_deg, read_radius
            )
            if elev_arr is not None and elev_arr.size > 0:
                slope_arr = None
                if slp_def and slp_def.absolute_local_path.exists():
                    slope_arr, _, _ = raster_sampler.sample_raster_window(
                        slp_def.absolute_local_path, lat_deg, lon_deg, read_radius
                    )

                # Sample point-wise uncertainty metrics
                v_unc = None
                if toterr_def and toterr_def.absolute_local_path.exists():
                    v_unc, _, _ = raster_sampler.sample_point_value(
                        toterr_def.absolute_local_path, lat_deg, lon_deg, nodata_val=toterr_def.nodata
                    )

                s_unc = None
                if slperr_def and slperr_def.absolute_local_path.exists():
                    s_unc, _, _ = raster_sampler.sample_point_value(
                        slperr_def.absolute_local_path, lat_deg, lon_deg, nodata_val=slperr_def.nodata
                    )

                obs_count = None
                if ldec_def and ldec_def.absolute_local_path.exists():
                    cnt, _, _ = raster_sampler.sample_point_value(
                        ldec_def.absolute_local_path, lat_deg, lon_deg, nodata_val=ldec_def.nodata
                    )
                    obs_count = int(cnt) if cnt is not None else None

                return NASASpatialWindow(
                    elevation_data=elev_arr,
                    slope_data=slope_arr,
                    transform=transform,
                    dx_meters=res[0] if res[0] > 0 else 5.0,
                    dy_meters=res[1] if res[1] > 0 else 5.0,
                    center_x_meters=center_x,
                    center_y_meters=center_y,
                    nodata_value=surf_def.nodata,
                    source_tier="Tier 2 (High-Resolution 5m Candidate Region)",
                    source_id="pgda_product78",
                    dataset_name="NASA PGDA Product 78 (LOLA 5m/pixel Candidate Site DEM)",
                    product_id="Site01_final_adj_5mpp_surf",
                    source_url="https://pgda.gsfc.nasa.gov/products/78",
                    citation="Barker, M. K., et al. (2021). High-resolution lunar south pole digital elevation models from LOLA and LROC. Planetary and Space Science, 203, 105119.",
                    crs=cls.CRS_ESRI_104903,
                    reference_frame=cls.REFERENCE_FRAME_DE421,
                    is_measured_data=True,
                    vertical_uncertainty_m=v_unc or 1.5,
                    slope_uncertainty_deg=s_unc,
                    effective_resolution_m=5.0,
                    observation_count=obs_count,
                    quality_warnings=None,
                )

        # ------------------------------------------------------------------
        # 2. Product 90 (80 m/pixel LOLA Regional South Pole Foundation)
        # ------------------------------------------------------------------
        if source_id == "pgda_product90":
            ldem_def = dataset_settings.datasets.get("pgda90_ldem")
            ldsm_def = dataset_settings.datasets.get("pgda90_ldsm")
            err_def = dataset_settings.datasets.get("pgda90_ldem_err")
            slperr_def = dataset_settings.datasets.get("pgda90_ldsm_err")
            effres_def = dataset_settings.datasets.get("pgda90_ldem_effres")
            ldec_def = dataset_settings.datasets.get("pgda90_ldec")

            read_radius = max(radius_m, 250.0)
            elev_arr, transform, res = raster_sampler.sample_raster_window(
                ldem_def.absolute_local_path, lat_deg, lon_deg, read_radius
            )
            if elev_arr is not None and elev_arr.size > 0:
                slope_arr = None
                if ldsm_def and ldsm_def.absolute_local_path.exists():
                    slope_arr, _, _ = raster_sampler.sample_raster_window(
                        ldsm_def.absolute_local_path, lat_deg, lon_deg, read_radius
                    )

                v_unc = None
                if err_def and err_def.absolute_local_path.exists():
                    v_unc, _, _ = raster_sampler.sample_point_value(
                        err_def.absolute_local_path, lat_deg, lon_deg, nodata_val=err_def.nodata
                    )

                s_unc = None
                if slperr_def and slperr_def.absolute_local_path.exists():
                    s_unc, _, _ = raster_sampler.sample_point_value(
                        slperr_def.absolute_local_path, lat_deg, lon_deg, nodata_val=slperr_def.nodata
                    )

                eff_res = None
                if effres_def and effres_def.absolute_local_path.exists():
                    eff_res, _, _ = raster_sampler.sample_point_value(
                        effres_def.absolute_local_path, lat_deg, lon_deg, nodata_val=effres_def.nodata
                    )

                obs_count = None
                if ldec_def and ldec_def.absolute_local_path.exists():
                    cnt, _, _ = raster_sampler.sample_point_value(
                        ldec_def.absolute_local_path, lat_deg, lon_deg, nodata_val=ldec_def.nodata
                    )
                    obs_count = int(cnt) if cnt is not None else None

                return NASASpatialWindow(
                    elevation_data=elev_arr,
                    slope_data=slope_arr,
                    transform=transform,
                    dx_meters=res[0] if res[0] > 0 else 80.0,
                    dy_meters=res[1] if res[1] > 0 else 80.0,
                    center_x_meters=center_x,
                    center_y_meters=center_y,
                    nodata_value=ldem_def.nodata,
                    source_tier="Tier 1 (LOLA 80m Regional Foundation)",
                    source_id="pgda_product90",
                    dataset_name="NASA PGDA Product 90 (LOLA South Pole 80m Regional Foundation)",
                    product_id="LDEM_80S_80MPP_ADJ",
                    source_url="https://pgda.gsfc.nasa.gov/products/90",
                    citation="Barker, M. K., et al. (2016). Lunar Orbiter Laser Altimeter (LOLA) South Pole 80m DEM. NASA Planetary Data System.",
                    crs=cls.CRS_ESRI_104903,
                    reference_frame=cls.REFERENCE_FRAME_DE421,
                    is_measured_data=True,
                    vertical_uncertainty_m=v_unc or 1.0,
                    slope_uncertainty_deg=s_unc,
                    effective_resolution_m=eff_res or 80.0,
                    observation_count=obs_count,
                    quality_warnings=None,
                )

        # ------------------------------------------------------------------
        # 3. Fallback: Calibrated baseline sample DEM
        # ------------------------------------------------------------------
        from app.core.config import settings

        if settings.DATA_MODE == "live" and not settings.ALLOW_SYNTHETIC_FALLBACK:
            # Strict live mode disallows synthetic DEM substitution
            return None

        read_radius = max(radius_m, 1500.0)
        elev_arr, transform, res = dem_service.read_window_around_point(lat_deg, lon_deg, read_radius)
        if elev_arr is None or elev_arr.size == 0:
            return None

        return NASASpatialWindow(
            elevation_data=elev_arr,
            slope_data=None,
            transform=transform,
            dx_meters=res[0] if res[0] > 0 else LOLA_SPATIAL_RESOLUTION_M,
            dy_meters=res[1] if res[1] > 0 else LOLA_SPATIAL_RESOLUTION_M,
            center_x_meters=center_x,
            center_y_meters=center_y,
            nodata_value=LOLA_NODATA_VALUE,
            source_tier="Tier 0 (Calibrated Sample Baseline)",
            source_id="dem_sample_fallback",
            dataset_name=LOLA_DATASET_NAME,
            product_id=LOLA_PRODUCT_ID,
            source_url="https://pgda.gsfc.nasa.gov/products/90",
            citation="Moonscape Baseline Sample DEM (Download Profile B for real 80m NASA GeoTIFF rasters)",
            crs=cls.CRS_ESRI_104903,
            reference_frame=cls.REFERENCE_FRAME_DE421,
            is_measured_data=False,
            vertical_uncertainty_m=LOLA_VERTICAL_ACCURACY_M,
            slope_uncertainty_deg=None,
            effective_resolution_m=LOLA_SPATIAL_RESOLUTION_M,
            observation_count=None,
            quality_warnings="Operating on calibrated baseline synthetic DEM. Acquire authentic NASA rasters via /api/data/download for primary mission evaluation.",
        )


nasa_data_manager = NASADataManager()
