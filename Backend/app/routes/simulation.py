"""Time-based Sun and Earth visibility simulation endpoints."""

from fastapi import APIRouter
from Backend.app.schemas.simulation import (
    VisibilitySimulationRequest,
    VisibilitySimulationResponse,
)
from Backend.app.services.visibility_simulation import visibility_simulation_service

router = APIRouter(prefix="", tags=["Simulation"])


@router.post(
    "/simulation/visibility",
    response_model=VisibilitySimulationResponse,
    summary="Propagate time-based Sun and Earth visibility over user-defined duration",
)
def simulate_visibility(payload: VisibilitySimulationRequest) -> VisibilitySimulationResponse:
    """Propagates solar elevation, surface insolation, Earth elevation, and direct communication

    line-of-sight over a configurable time horizon (1 to 60 days).
    """
    return visibility_simulation_service.simulate_visibility(payload)
