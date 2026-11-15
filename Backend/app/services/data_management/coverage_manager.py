"""Coverage Manager evaluating spatial intersections between lunar coordinates and NASA datasets."""

from typing import Any, Dict, List
from app.config.dataset_settings import dataset_settings
from app.services.data_management.dataset_registry import dataset_registry
from app.services.data_sources.diviner import diviner_thermal
from app.services.data_sources.lroc_nac import lroc_nac
from app.services.data_sources.lroc_wac import lroc_wac
from app.services.data_sources.pgda_product104 import pgda_product104
from app.services.data_sources.pgda_product78 import pgda_product78
from app.services.data_sources.pgda_product90 import pgda_product90
from app.services.data_sources.isro_chandrayaan2 import isro_chandrayaan2
from app.services.geospatial.coordinate_manager import coordinate_manager


class CoverageManager:
    """Evaluates spatial coverage, local presence, and resolution tiers for any coordinate."""

    @classmethod
    def get_coverage_report(cls, lat_deg: float, lon_deg: float) -> Dict[str, Any]:
        """Returns comprehensive coverage report for a specific lunar coordinate."""
        is_valid, val_msg = coordinate_manager.validate_coordinates(lat_deg, lon_deg)
        if not is_valid:
            return {
                "valid_coordinate": False,
                "error": val_msg,
                "latitude": lat_deg,
                "longitude": lon_deg,
                "coverage_zone": "invalid",
                "in_south_pole_zone": False,
                "available_layers": [],
            }

        zone = coordinate_manager.get_coverage_zone(lat_deg)
        in_sp = coordinate_manager.is_in_analysis_region(lat_deg)
        norm_lon = coordinate_manager.normalize_longitude(lon_deg, target_range="360")

        layers: List[Dict[str, Any]] = []

        # 1. Product 90 (Regional 80m)
        if pgda_product90.covers_point(lat_deg, lon_deg):
            p90_status = dataset_registry.get_status("pgda90_ldem")
            layers.append({
                "source_id": pgda_product90.source_id,
                "name": pgda_product90.source_name,
                "tier": "Tier 1: Essential Local",
                "covers": True,
                "is_installed": p90_status.value == "available",
                "resolution_m": 80.0,
                "status": p90_status.value,
            })

        # 2. Product 78 (Site 01 5m)
        p78_covers = pgda_product78.covers_point(lat_deg, lon_deg)
        p78_status = dataset_registry.get_status("pgda78_site01_surf")
        layers.append({
            "source_id": pgda_product78.source_id,
            "name": pgda_product78.source_name,
            "tier": "Tier 2: High-Resolution Regional",
            "covers": p78_covers,
            "is_installed": p78_status.value == "available",
            "resolution_m": 5.0,
            "status": p78_status.value,
            "detail": "Site 01 Shackleton Connecting Ridge" if p78_covers else "Outside Site 01 footprint",
        })

        # 3. Product 104 (Shape-from-Shading)
        sfs_tiles = pgda_product104.find_covering_tiles(lat_deg, lon_deg)
        layers.append({
            "source_id": pgda_product104.source_id,
            "name": pgda_product104.source_name,
            "tier": "Tier 3: Remote / On-Demand",
            "covers": len(sfs_tiles) > 0,
            "is_installed": any(t.get("is_installed_locally", False) for t in sfs_tiles),
            "resolution_m": 1.0,
            "covering_candidate_sites": [t["name"] for t in sfs_tiles],
        })

        # 4. Diviner Thermal PCP
        diviner_covers = diviner_thermal.covers_point(lat_deg, lon_deg)
        layers.append({
            "source_id": diviner_thermal.source_id,
            "name": diviner_thermal.source_name,
            "tier": "Tier 3: Remote / On-Demand",
            "covers": diviner_covers,
            "is_installed": diviner_thermal.is_available(),
            "resolution_m": 240.0,
            "measurement_type": "Surface brightness temperature (Kelvin)",
        })

        # 5. LROC WAC Visual Mosaic
        layers.append({
            "source_id": lroc_wac.source_id,
            "name": lroc_wac.source_name,
            "tier": "Tier 3: Remote / On-Demand",
            "covers": lroc_wac.covers_point(lat_deg, lon_deg),
            "is_installed": lroc_wac.is_available(),
            "resolution_m": 100.0,
            "measurement_type": "Optical reflectance (Albedo)",
        })

        # 6. LROC NAC DTM Footprints
        nac_dtms = lroc_nac.find_covering_dtms(lat_deg, lon_deg)
        layers.append({
            "source_id": lroc_nac.source_id,
            "name": lroc_nac.source_name,
            "tier": "Tier 3: Remote / On-Demand",
            "covers": len(nac_dtms) > 0,
            "is_installed": lroc_nac.is_available(),
            "resolution_m": 1.5,
            "covering_nac_dtms": [d["name"] for d in nac_dtms],
        })

        # 7. ISRO Chandrayaan-2 (OHRC & TMC-2)
        ch2_covering = isro_chandrayaan2.covers_point(lat_deg, lon_deg)
        ch2_products = isro_chandrayaan2.find_covering_products(lat_deg, lon_deg)
        layers.append({
            "source_id": isro_chandrayaan2.source_id,
            "name": isro_chandrayaan2.source_name,
            "tier": "Tier 3: Remote / On-Demand",
            "covers": ch2_covering,
            "is_installed": isro_chandrayaan2.is_available(),
            "resolution_m": 0.25 if any(p["instrument"] == "OHRC" for p in ch2_products) else 5.0,
            "covering_isro_products": [p["name"] for p in ch2_products],
            "agency": "ISRO",
        })

        # Determine best available resolution
        installed_resolutions = [l["resolution_m"] for l in layers if l["covers"] and l["is_installed"]]
        best_res = min(installed_resolutions) if installed_resolutions else None

        return {
            "valid_coordinate": True,
            "latitude": lat_deg,
            "longitude": norm_lon,
            "coverage_zone": zone,
            "in_south_pole_zone": in_sp,
            "best_installed_resolution_m": best_res,
            "total_covering_sources": len([l for l in layers if l["covers"]]),
            "installed_covering_sources": len([l for l in layers if l["covers"] and l["is_installed"]]),
            "layers": layers,
        }


coverage_manager = CoverageManager()
