"""Touchdown hazard prediction endpoints."""

from fastapi import APIRouter
from app.schemas.hazard import HazardPredictRequest, HazardPredictResponse
from app.services.hazard_service import hazard_service

router = APIRouter(prefix="", tags=["Hazards"])


@router.post("/hazards/predict", response_model=HazardPredictResponse, summary="Detect and predict landing hazards")
def predict_hazards(payload: HazardPredictRequest) -> HazardPredictResponse:
    """Predicts physical touchdown risks (craters, boulders, steep escarpments, shadows) within the landing ellipse."""
    return hazard_service.predict_hazards(payload)
