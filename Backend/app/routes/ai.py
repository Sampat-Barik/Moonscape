"""AI scientific explanation router endpoint."""

from fastapi import APIRouter, HTTPException, status
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


@router.post(
    "/ai/compare",
    response_model=AIExplainResponse,
    summary="Generate AI comparative landing site evaluation and trade-off synthesis",
    description="Synthesizes multi-site comparison measurements into an executive narrative debrief, favorable advantages, risk factors, and engineering trade-offs.",
)
def explain_comparison(payload: AIExplainRequest) -> AIExplainResponse:
    """Generates comparative scientific mission debrief and trade-off assessment across candidate landing sites."""
    if payload.site_ids and len(payload.site_ids) >= 2:
        return ai_explainer_service.explain_comparison(
            site_ids=payload.site_ids,
            mission_profile=payload.mission_profile or "crewed_artemis_class",
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="At least two site IDs are required for comparative explanation.",
    )
