"""Candidate landing sites and comparative evaluation endpoints."""

from typing import List
from fastapi import APIRouter, HTTPException, status
from app.schemas.site import (
    CandidateSite,
    SiteCompareRequest,
    SiteCompareResponse,
)
from app.services.site_service import site_service

router = APIRouter(prefix="", tags=["Sites"])


@router.get("/sites", response_model=List[CandidateSite], summary="List all candidate lunar landing sites")
def list_sites() -> List[CandidateSite]:
    """Retrieves all registered NASA Artemis candidate South Pole landing sites."""
    return site_service.get_all_sites()


@router.post("/sites/compare", response_model=SiteCompareResponse, summary="Compare multiple candidate landing sites")
def compare_sites(payload: SiteCompareRequest) -> SiteCompareResponse:
    """Executes a multi-criteria comparative decision matrix between two or more candidate sites.

    Registered before the {site_id} path to prevent FastAPI route collision.
    """
    # Verify all site IDs exist in catalog
    missing_ids = [sid for sid in payload.site_ids if not site_service.get_site_by_id(sid)]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The following site IDs do not exist in the catalog: {missing_ids}",
        )

    return site_service.compare_sites(
        site_ids=payload.site_ids,
        custom_weights=payload.weights,
    )


@router.get("/sites/{site_id}", response_model=CandidateSite, summary="Get metadata for a specific candidate site")
def get_site(site_id: str) -> CandidateSite:
    """Retrieves detailed coordinates, illumination, slopes, and scientific context for a specific candidate site."""
    site = site_service.get_site_by_id(site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate landing site with ID '{site_id}' not found.",
        )
    return site
