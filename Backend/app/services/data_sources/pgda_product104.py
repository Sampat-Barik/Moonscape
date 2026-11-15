"""Adapter for NASA PGDA Product 104 / Zenodo 17954508: Photoclinometry / Shape-from-Shading (SfS) DEMs."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from affine import Affine

from app.core.config import settings
from app.services.data_sources.base import BaseDataSource
from app.services.geospatial.coordinate_manager import coordinate_manager
from app.services.geospatial.raster_sampler import raster_sampler


# Known Artemis Candidate Site Footprints from Product 104 (Barker et al. 2023)
SFS_REGIONAL_FOOTPRINTS = [
    {
        "site_id": "artemis_shackleton_connecting_ridge",
        "name": "Shackleton Connecting Ridge",
        "bounds": {"min_lat": -89.85, "max_lat": -89.20, "min_lon": 200.0, "max_lon": 240.0},
        "resolution_m": 1.0,
        "filename": "sfs_shackleton_connecting_ridge_1m.tif",
        "size_mb": 312.0,
    },
    {
        "site_id": "artemis_de_gerlache_rim_1",
        "name": "de Gerlache Rim 1",
        "bounds": {"min_lat": -88.80, "max_lat": -88.30, "min_lon": 270.0, "max_lon": 295.0},
        "resolution_m": 1.0,
        "filename": "sfs_de_gerlache_rim_1_1m.tif",
        "size_mb": 285.0,
    },
    {
        "site_id": "artemis_malapert_mountain",
        "name": "Malapert Mountain",
        "bounds": {"min_lat": -86.20, "max_lat": -85.60, "min_lon": 355.0, "max_lon": 5.0},
        "resolution_m": 1.0,
        "filename": "sfs_malapert_mountain_1m.tif",
        "size_mb": 350.0,
    },
    {
        "site_id": "artemis_nobile_rim_1",
        "name": "Nobile Rim 1",
        "bounds": {"min_lat": -85.50, "max_lat": -85.00, "min_lon": 33.0, "max_lon": 43.0},
        "resolution_m": 1.0,
        "filename": "sfs_nobile_rim_1_1m.tif",
        "size_mb": 290.0,
    },
    {
        "site_id": "artemis_faustini_rim",
        "name": "Faustini Rim",
        "bounds": {"min_lat": -87.40, "max_lat": -86.90, "min_lon": 75.0, "max_lon": 90.0},
        "resolution_m": 1.0,
        "filename": "sfs_faustini_rim_1m.tif",
        "size_mb": 280.0,
    },
]


class PGDAProduct104Source(BaseDataSource):
    """Adapter for Shape-from-Shading (SfS) photoclinometry candidate Artemis landing site models."""

    def __init__(self):
        self.raw_dir = settings.BASE_DIR / "data" / "lunar" / "raw" / "pgda104"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    @property
    def source_id(self) -> str:
        return "pgda_product104"

    @property
    def source_name(self) -> str:
        return "NASA PGDA Product 104 / Zenodo 17954508 (Shape-from-Shading Photoclinometry DEMs)"

    def is_available(self) -> bool:
        """Returns True if at least one local SfS raster is present on disk."""
        if not self.raw_dir.exists():
            return False
        return any(self.raw_dir.glob("*.tif"))

    def covers_point(self, lat_deg: float, lon_deg: float) -> bool:
        """Checks if coordinate falls inside any cataloged SfS candidate site bounding box."""
        return len(self.find_covering_tiles(lat_deg, lon_deg)) > 0

    def find_covering_tiles(self, lat_deg: float, lon_deg: float) -> List[Dict[str, Any]]:
        """Finds all cataloged candidate site tiles that encompass the coordinate."""
        norm_lon = coordinate_manager.normalize_longitude(lon_deg, target_range="360")
        covering = []
        for site in SFS_REGIONAL_FOOTPRINTS:
            b = site["bounds"]
            # Handle lon wrap across 0/360
            if b["min_lon"] > b["max_lon"]:
                lon_match = (norm_lon >= b["min_lon"]) or (norm_lon <= b["max_lon"])
            else:
                lon_match = b["min_lon"] <= norm_lon <= b["max_lon"]

            if (b["min_lat"] <= lat_deg <= b["max_lat"]) and lon_match:
                local_path = self.raw_dir / site["filename"]
                site_info = dict(site)
                site_info["is_installed_locally"] = local_path.exists()
                site_info["local_path"] = str(local_path)
                covering.append(site_info)
        return covering

    def sample_point(self, lat_deg: float, lon_deg: float) -> Optional[Dict[str, Any]]:
        """Samples local SfS high-resolution raster if available on disk."""
        covering = self.find_covering_tiles(lat_deg, lon_deg)
        if not covering:
            return None

        # Check if any covering tile is present on disk
        for tile in covering:
            local_path = Path(tile["local_path"])
            if local_path.exists():
                elev_val, is_valid_pt, is_nodata = raster_sampler.sample_point_value(
                    local_path, lat_deg, lon_deg, nodata_val=-32768.0
                )
                if is_valid_pt and not is_nodata:
                    return {
                        "source_id": self.source_id,
                        "source_name": self.source_name,
                        "site_id": tile["site_id"],
                        "site_name": tile["name"],
                        "elevation_m": elev_val,
                        "spatial_resolution_m": tile["resolution_m"],
                        "nominal_resolution_m": tile["resolution_m"],
                        "spatial_units": "meters",
                        "crs": "ESRI:104903 (Lunar South Polar Stereographic)",
                        "reference_sphere_radius_m": coordinate_manager.RADIUS_METERS,
                        "provenance": self.get_provenance(),
                    }

        # If not installed locally, return discovery metadata
        primary = covering[0]
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "site_id": primary["site_id"],
            "site_name": primary["name"],
            "is_installed_locally": False,
            "elevation_m": None,
            "spatial_resolution_m": primary["resolution_m"],
            "message": f"Candidate Artemis landing site '{primary['name']}' covered by Shape-from-Shading DEM ({primary['size_mb']} MB). Available on-demand via Zenodo/PGDA.",
            "provenance": self.get_provenance(),
        }

    def sample_window(
        self,
        lat_deg: float,
        lon_deg: float,
        radius_m: float,
    ) -> Tuple[Optional[np.ndarray], Optional[Affine], Tuple[float, float]]:
        """Extracts spatial sub-window from local SfS raster if installed."""
        covering = self.find_covering_tiles(lat_deg, lon_deg)
        for tile in covering:
            local_path = Path(tile["local_path"])
            if local_path.exists():
                return raster_sampler.sample_raster_window(local_path, lat_deg, lon_deg, radius_m)
        return None, None, (0.0, 0.0)

    def get_provenance(self) -> Dict[str, Any]:
        """Returns scientific attribution for PGDA Product 104."""
        return {
            "mission": "Lunar Reconnaissance Orbiter (LRO)",
            "instruments": "LOLA laser altimetry + LROC Narrow Angle Camera (NAC) photoclinometry",
            "archive": "NASA Planetary Geodynamics Laboratory / Zenodo Record 17954508",
            "product_url": "https://pgda.gsfc.nasa.gov/products/104",
            "citation": "Barker, M. K., et al. (2023). Shape-from-Shading Topography of the Lunar South Pole Candidate Artemis Landing Sites. NASA Goddard Space Flight Center.",
            "reference_frame": "MOON_ME (Mean Earth / Polar Axis) DE421",
            "datum_radius_m": 1737400.0,
        }


pgda_product104 = PGDAProduct104Source()
