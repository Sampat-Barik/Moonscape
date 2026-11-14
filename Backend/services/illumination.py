"""Root-level import shim pointing to app.services.illumination."""

from app.services.illumination import (
    DIVINER_THERMAL_CAVEAT,
    IlluminationService,
    illumination_service,
)

__all__ = [
    "DIVINER_THERMAL_CAVEAT",
    "IlluminationService",
    "illumination_service",
]
