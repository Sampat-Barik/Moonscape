"""NASA LROC QuickMap and Narrow Angle Camera (NAC) Stereo DTM Integration Service.

Connects target coordinates to official NASA LROC PDS archive products, targeted polar stereo DTM footprints,
optical inspection links, and LROC QuickMap deep-linking.

Official LROC Resources:
- LROC PDS Archive: https://pds.lroc.im-ldi.com/data
- LROC NAC DTM Shapefiles: https://data.lroc.im-ldi.com/lroc/view_rdr/SHAPEFILE_NAC_DTMS
- LROC QuickMap: https://quickmap.lroc.im-ldi.com/
"""

from dataclasses import asdict, dataclass
import math
from typing import Any, Dict, List, Optional, Tuple

from app.services.data_sources.lroc_nac import KNOWN_NAC_DTM_FOOTPRINTS, lroc_nac
from app.services.geospatial.coordinate_manager import coordinate_manager
from maths.geodesy import haversine_lunar_distance


@dataclass
class LROCProductCoverage:
    """LROC NAC high-resolution photogrammetric coverage report for a location."""

    latitude: float
    longitude: float
    is_covered: bool
    covering_dtms: List[Dict[str, Any]]
    nearest_dtm: Optional[Dict[str, Any]]
    distance_to_nearest_dtm_km: float
    best_resolution_m: Optional[float]
    quickmap_url: str
    lroc_archive_url: str
    optical_hazard_validation_supported: bool
    status_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LROCService:
    """Service for LROC NAC targeted stereo DTM discovery, QuickMap navigation, and hazard context."""

    def __init__(self):
        self.dtm_catalog = KNOWN_NAC_DTM_FOOTPRINTS

    def get_coverage(self, lat_deg: float, lon_deg: float) -> LROCProductCoverage:
        """Finds high-resolution LROC NAC stereo DTM coverage and generate QuickMap deep link."""
        norm_lat = max(-90.0, min(90.0, float(lat_deg)))
        norm_lon_360 = coordinate_manager.normalize_longitude(lon_deg, target_range="360")
        norm_lon_180 = coordinate_manager.normalize_longitude(lon_deg, target_range="180")

        # 1. Search for direct footprint coverage
        covering_matches = lroc_nac.find_covering_dtms(norm_lat, norm_lon_360)

        # 2. Find nearest DTM in catalog if not directly covered
        min_dist_m = float("inf")
        nearest_dtm_item: Optional[Dict[str, Any]] = None

        for dtm in self.dtm_catalog:
            c = dtm["centroid"]
            dist_m = haversine_lunar_distance(norm_lat, norm_lon_360, c["lat"], c["lon"])
            if dist_m < min_dist_m:
                min_dist_m = dist_m
                nearest_dtm_item = dtm

        dist_km = round(min_dist_m / 1000.0, 2)
        is_covered = len(covering_matches) > 0

        best_res = None
        if is_covered:
            best_res = min(m["resolution_m"] for m in covering_matches)
        elif nearest_dtm_item and dist_km < 10.0:
            # Proximal coverage
            best_res = nearest_dtm_item["resolution_m"]

        # Generate QuickMap URL with lunar South Pole stereographic projection
        # QuickMap supports extent or center with zoom
        quickmap_url = (
            f"https://quickmap.lroc.im-ldi.com/?center={norm_lon_180:.4f},{norm_lat:.4f}"
            f"&zoom=6&proj=southpole&layers=lroc_color_poles_85s"
        )

        lroc_archive_url = (
            covering_matches[0]["pds_url"]
            if is_covered
            else "https://wms.lroc.asu.edu/lroc/rdr_product_select"
        )

        if is_covered:
            note = (
                f"Location is encompassed by {len(covering_matches)} official NASA LROC NAC stereo DTM(s). "
                f"Peak spatial resolution: {best_res} m/pixel photogrammetry."
            )
            hazard_supp = True
        else:
            dtm_name = nearest_dtm_item["name"] if nearest_dtm_item else "Unknown"
            note = (
                f"Outside contiguous targeted NAC stereo DTM footprints. "
                f"Nearest NAC DTM is '{dtm_name}' located {dist_km} km away."
            )
            hazard_supp = False

        return LROCProductCoverage(
            latitude=norm_lat,
            longitude=norm_lon_360,
            is_covered=is_covered,
            covering_dtms=covering_matches,
            nearest_dtm=nearest_dtm_item,
            distance_to_nearest_dtm_km=dist_km,
            best_resolution_m=best_res,
            quickmap_url=quickmap_url,
            lroc_archive_url=lroc_archive_url,
            optical_hazard_validation_supported=hazard_supp,
            status_note=note,
        )


lroc_service = LROCService()
