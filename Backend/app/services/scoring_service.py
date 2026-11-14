"""Suitability scoring service adapter wrapping site_scoring_engine."""

from typing import Optional
from app.schemas.scoring import ScoreRequest, ScoreResponse
from app.services.site_scoring import site_scoring_engine
from maths.scoring import evaluate_roughness_score, evaluate_slope_score


class ScoringService:
    """Evaluates landing zones with an explainable, weighted multi-criteria decision algorithm."""

    @staticmethod
    def calculate_slope_subscore(slope_deg: Optional[float]) -> float:
        """Evaluates slope with Apollo/Artemis lander tip-over margins."""
        if slope_deg is None:
            return 50.0
        return evaluate_slope_score(slope_deg)

    @staticmethod
    def calculate_roughness_subscore(roughness_m: Optional[float]) -> float:
        """Evaluates surface roughness against footpad and engine clearance limits."""
        if roughness_m is None:
            return 50.0
        return evaluate_roughness_score(roughness_m)

    def compute_score(self, req: ScoreRequest) -> ScoreResponse:
        """Computes composite landing suitability score with full factor transparency."""
        return site_scoring_engine.evaluate_suitability(req)


scoring_service = ScoringService()
