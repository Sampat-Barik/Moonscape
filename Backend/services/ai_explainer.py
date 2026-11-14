"""Root-level shim for Moonscape AI Scientific Explainer service."""

from Backend.app.services.ai_explainer import (
    AIExplainerService,
    EXPLAINER_SYSTEM_PROMPT,
    ai_explainer_service,
)

__all__ = [
    "AIExplainerService",
    "ai_explainer_service",
    "EXPLAINER_SYSTEM_PROMPT",
]
