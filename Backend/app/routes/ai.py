"""AI scientific explanation router endpoint."""

from fastapi import APIRouter
from app.schemas.ai import AIExplainRequest, AIExplainResponse
from app.services.ai_service import ai_service

router = APIRouter(prefix="", tags=["AI Advisory"])


@router.post("/ai/explain", response_model=AIExplainResponse, summary="Generate AI scientific explanation and trade-off analysis")
def explain_site(payload: AIExplainRequest) -> AIExplainResponse:
    """Synthesizes physical measurements into a coherent, physics-grounded scientific explanation and engineering trade-offs."""
    return ai_service.explain_landing_site(payload)
