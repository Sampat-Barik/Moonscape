"""Health check router endpoint."""

from fastapi import APIRouter
from app.core.config import settings
from app.core.constants import PROJECTION_EPSG, SCIENTIFIC_SAFETY_DISCLAIMER
from app.schemas.health import HealthResponse
from app.services.dem_service import dem_service
from app.services.site_service import site_service

router = APIRouter(prefix="", tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="System health and operational status")
def get_health() -> HealthResponse:
    """Verifies that the Moonscape backend, scientific datasets, and candidate catalogs are operational."""
    dem_ready = dem_service.is_available()
    sites_count = site_service.count_sites()
    status = "healthy" if dem_ready and sites_count > 0 else "degraded"

    return HealthResponse(
        status=status,
        version=settings.VERSION,
        dem_dataset_loaded=dem_ready,
        sites_loaded=sites_count,
        crs=PROJECTION_EPSG,
        disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
    )
