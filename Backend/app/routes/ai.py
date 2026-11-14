"""AI scientific explanation router endpoint."""

from fastapi import APIRouter
from app.schemas.ai import AIExplainRequest, AIExplainResponse
from app.services.ai_explainer import ai_explainer_service

router = APIRouter(prefix="", tags=["AI Advisory"])


@router.post(
    "/ai/explain",
    response_model=AIExplainResponse,
    summary="Generate AI scientific explanation of landing site analysis",
    description="Synthesizes physical terrain, hazard, illumination, and suitability measurements into accessible explanations.",
)
def explain_site(payload: AIExplainRequest) -> AIExplainResponse:
    """Explains backend measurements in simple, accessible, and scientifically grounded language."""
    return ai_explainer_service.explain_analysis(payload)
