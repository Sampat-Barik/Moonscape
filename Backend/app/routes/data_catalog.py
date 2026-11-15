"""API endpoints for NASA dataset catalog discovery, disk status, and coordinate coverage."""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query

from app.config.dataset_settings import dataset_settings
from app.schemas.dataset_schemas import (
    DataCoverageResponse,
    DatasetCatalogResponse,
    DatasetItem,
    DatasetProfile,
)
from app.services.data_management.coverage_manager import coverage_manager
from app.services.data_management.dataset_registry import dataset_registry

router = APIRouter(prefix="/data", tags=["NASA Data Management"])


@router.get("/catalog", response_model=DatasetCatalogResponse, summary="List all registered NASA lunar datasets and profiles")
def get_dataset_catalog() -> DatasetCatalogResponse:
    """Returns the complete dataset catalog loaded from the verified manifest, including installation status."""
    dataset_registry.refresh_all_statuses()
    all_defs = dataset_settings.datasets.values()

    items: List[DatasetItem] = []
    installed_count = 0

    for d in all_defs:
        status = dataset_registry.get_status(d.id)
        is_installed = (status.value == "available")
        if is_installed:
            installed_count += 1

        items.append(
            DatasetItem(
                id=d.id,
                name=d.name,
                source_provider=d.source_provider,
                product_id=d.product_id,
                filename=d.filename,
                size_mb=d.size_mb,
                spatial_resolution_m=d.spatial_resolution_m,
                units=d.units,
                tier=d.tier.value,
                byte_range_supported=d.byte_range_supported,
                status=status.value,
                validation_detail=dataset_registry.get_validation_detail(d.id),
                is_installed=is_installed,
                bounds={
                    "min_lat": d.bounds.min_lat,
                    "max_lat": d.bounds.max_lat,
                    "min_lon": d.bounds.min_lon,
                    "max_lon": d.bounds.max_lon,
                },
            )
        )

    # Load profiles from manifest
    profiles_dict: Dict[str, DatasetProfile] = {}
    manifest_profiles = dataset_settings.get_profiles() if hasattr(dataset_settings, "get_profiles") else {}
    for p_id, p_info in manifest_profiles.items():
        profiles_dict[p_id] = DatasetProfile(
            name=p_info.get("name", p_id),
            description=p_info.get("description", ""),
            total_size_mb=p_info.get("total_size_mb", 0.0),
            datasets=p_info.get("datasets", []),
        )

    return DatasetCatalogResponse(
        total_datasets=len(items),
        installed_count=installed_count,
        default_profile="profile_b",
        profiles=profiles_dict,
        datasets=items,
    )


@router.get("/status", summary="Retrieve disk installation and validation status for all datasets")
def get_dataset_statuses() -> Dict[str, dict]:
    """Returns real-time status, file presence, and GeoTIFF validation details for every dataset."""
    dataset_registry.refresh_all_statuses()
    result = {}
    for d_id, defn in dataset_settings.datasets.items():
        status = dataset_registry.get_status(d_id)
        result[d_id] = {
            "name": defn.name,
            "filename": defn.filename,
            "status": status.value,
            "is_available": (status.value == "available"),
            "file_exists": defn.absolute_local_path.exists(),
            "size_mb": defn.size_mb,
            "validation_detail": dataset_registry.get_validation_detail(d_id),
            "tier": defn.tier.value,
        }
    return result


@router.get("/coverage", response_model=DataCoverageResponse, summary="Query spatial dataset coverage at a lunar coordinate")
def get_spatial_coverage(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude in degrees (-90 to 90)"),
    lon: float = Query(..., ge=-180.0, le=360.0, description="Longitude in degrees (-180 to 360)"),
) -> DataCoverageResponse:
    """Evaluates spatial coverage across all NASA tiers for the coordinate."""
    report = coverage_manager.get_coverage_report(lat, lon)
    return DataCoverageResponse(**report)


@router.get("/lroc/footprints", summary="Discover intersecting NASA LROC NAC targeted stereo DTM footprints")
def discover_lroc_nac_footprints(
    lat: float = Query(..., ge=-90.0, le=-70.0, description="Center latitude in degrees (-90 to -70)"),
    lon: float = Query(..., ge=-180.0, le=360.0, description="Center longitude in degrees (-180 to 360)"),
    radius: float = Query(5000.0, ge=100.0, le=50000.0, description="Search radius in meters (100m to 50km)"),
) -> Dict[str, Any]:
    """Performs spatial footprint intersection for high-resolution (0.5 - 2.0 m/pixel) LROC NAC DTMs.

    Delineates optical boulder/crater visual detections from LOLA laser altimetry slopes.
    """
    from app.services.data_sources.lroc_nac import lroc_nac
    return lroc_nac.discover_footprints(center_lat=lat, center_lon=lon, search_radius_meters=radius)
