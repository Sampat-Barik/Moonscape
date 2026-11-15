"""Landing zone spatial analysis endpoints."""

import logging
import time
import uuid
from fastapi import APIRouter, HTTPException, status
from app.schemas.analysis import AnalysisRunRequest, AnalysisRunResponse
from app.services.terrain_service import terrain_service

logger = logging.getLogger("moonscape.analysis")
router = APIRouter(prefix="", tags=["Analysis"])


@router.post("/analysis/run", response_model=AnalysisRunResponse, summary="Execute landing zone spatial slope and roughness analysis")
def run_analysis(payload: AnalysisRunRequest) -> AnalysisRunResponse:
    """Executes a windowed spatial analysis over the landing ellipse.

    Calculates slope distribution, surface roughness, and percentage of touchdown area meeting constraints.
    """
    req_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
    start_time = time.perf_counter()

    logger.info(
        "[%s] /api/analysis/run START - lat=%.4f, lon=%.4f, radius=%.1fm, max_slope=%.1f°, max_roughness=%.2fm",
        req_id,
        payload.center_lat,
        payload.center_lon,
        payload.radius_meters,
        payload.max_acceptable_slope_deg,
        payload.max_acceptable_roughness_m,
    )

    try:
        response = terrain_service.analyze_landing_zone(payload)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        ds_name = response.dataset_metadata.get("dataset_name", "Unknown") if response.dataset_metadata else "N/A"
        feasibility = response.preliminary_feasibility

        logger.info(
            "[%s] /api/analysis/run SUCCESS - analysis_id=%s, dataset=%s, feasibility=%s, duration=%.2fms",
            req_id,
            response.analysis_id,
            ds_name,
            feasibility,
            elapsed_ms,
        )
        return response

    except HTTPException:
        raise
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        logger.error(
            "[%s] /api/analysis/run FAILED after %.2fms: %s",
            req_id,
            elapsed_ms,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis engine calculation failure: {str(exc)}",
        ) from exc
