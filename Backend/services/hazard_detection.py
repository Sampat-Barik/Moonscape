"""Root-level import shim pointing to app.services.hazard_detection."""

from app.services.hazard_detection import (
    APOLLO_DOMAIN_LIMITATION,
    HazardDetectionService,
    hazard_detection_service,
)

__all__ = [
    "APOLLO_DOMAIN_LIMITATION",
    "HazardDetectionService",
    "hazard_detection_service",
]
