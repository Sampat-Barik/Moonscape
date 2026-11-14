"""Landing zone spatial analysis endpoints."""

from fastapi import APIRouter
from app.schemas.analysis import AnalysisRunRequest, AnalysisRunResponse
from app.services.terrain_service import terrain_service

router = APIRouter(prefix="", tags=["Analysis"])


@router.post("/analysis/run", response_model=AnalysisRunResponse, summary="Execute landing zone spatial slope and roughness analysis")
def run_analysis(payload: AnalysisRunRequest) -> AnalysisRunResponse:
    """Executes a windowed spatial analysis over the landing ellipse.

    Calculates slope distribution, surface roughness, and percentage of touchdown area meeting constraints.
    """
    return terrain_service.analyze_landing_zone(payload)
