"""Touchdown hazard prediction endpoints."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas.hazard import HazardPredictRequest, HazardPredictResponse
from app.services.hazard_detection import hazard_detection_service
from app.services.hazard_service import hazard_service

router = APIRouter(prefix="", tags=["Hazards"])


@router.post("/hazards/predict", summary="Detect and predict landing hazards")
def predict_hazards(payload: HazardPredictRequest):
    """Predicts physical touchdown risks (craters, boulders, steep escarpments, shadows)

    via digital elevation models (DEM) or machine-learning optical image inference.
    """
    is_image_request = payload.image_base64 is not None or payload.image_path is not None
    is_coordinate_request = payload.center_lat is not None and payload.center_lon is not None

    # Image inference or empty query without coordinates
    if is_image_request or not is_coordinate_request:
        if not hazard_detection_service.is_available():
            # TASK 5: Return exact required dictionary when model is not configured
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "not_available",
                    "detections": [],
                    "crater_count": None,
                    "rock_count": None,
                    "warnings": ["Hazard detection model is not configured."],
                },
            )

        try:
            return hazard_detection_service.predict(payload)
        except ValueError as val_err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(val_err),
            ) from val_err
        except RuntimeError as rt_err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(rt_err),
            ) from rt_err

    # Coordinate-based topographic DEM hazard evaluation
    return hazard_service.predict_hazards(payload)
