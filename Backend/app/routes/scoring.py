"""Suitability scoring router endpoint."""

from fastapi import APIRouter
from app.schemas.scoring import ScoreRequest, ScoreResponse
from app.services.scoring_service import scoring_service

router = APIRouter(prefix="", tags=["Scoring"])


@router.post("/score", response_model=ScoreResponse, summary="Compute transparent multi-criteria suitability score")
def calculate_score(payload: ScoreRequest) -> ScoreResponse:
    """Calculates a composite suitability score (0-100) using a transparent, explainable decision matrix."""
    return scoring_service.compute_score(payload)
