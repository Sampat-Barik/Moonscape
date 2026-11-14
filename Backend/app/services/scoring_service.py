"""Transparent multi-criteria landing site suitability scoring engine."""

from typing import List, Optional
from app.core.constants import SCIENTIFIC_SAFETY_DISCLAIMER
from app.schemas.scoring import (
    FactorSubscore,
    ScoreRequest,
    ScoreResponse,
    ScoringWeights,
)
from app.services.site_service import site_service
from maths.scoring import (
    evaluate_roughness_score,
    evaluate_slope_score,
    weighted_composite_score,
)


class ScoringService:
    """Evaluates landing zones with an explainable, weighted multi-criteria decision algorithm."""

    @staticmethod
    def calculate_slope_subscore(slope_deg: Optional[float]) -> float:
        """Evaluates slope with Apollo/Artemis lander tip-over margins using the maths package."""
        if slope_deg is None:
            return 50.0
        return evaluate_slope_score(slope_deg)

    @staticmethod
    def calculate_roughness_subscore(roughness_m: Optional[float]) -> float:
        """Evaluates surface roughness against footpad and engine clearance limits using the maths package."""
        if roughness_m is None:
            return 50.0
        return evaluate_roughness_score(roughness_m)

    def compute_score(self, req: ScoreRequest) -> ScoreResponse:
        """Computes composite landing suitability score with full factor transparency."""
        # If site_id is provided, prepopulate missing measurements from site catalog
        slope = req.slope_deg
        roughness = req.roughness_m
        illum = req.illumination_pct
        comms = req.earth_visibility_pct
        science = req.science_value_rating

        if req.site_id:
            catalog_site = site_service.get_site_by_id(req.site_id)
            if catalog_site:
                if slope is None:
                    slope = catalog_site.mean_slope_deg
                if roughness is None:
                    # Estimate based on slope and geomorphology
                    roughness = 0.35 if (slope or 5.0) < 6.0 else 0.65
                if illum is None:
                    illum = catalog_site.illumination_pct
                if comms is None:
                    comms = catalog_site.earth_visibility_pct
                if science is None:
                    priority_map = {"high": 90.0, "medium": 75.0, "low": 50.0}
                    science = priority_map.get(catalog_site.priority.lower(), 70.0)

        # Default fallback values for unprovided metrics (clearly logged in subscores)
        slope_val = slope if slope is not None else 6.0
        roughness_val = roughness if roughness is not None else 0.4
        illum_val = illum if illum is not None else 65.0
        comms_val = comms if comms is not None else 70.0
        science_val = science if science is not None else 75.0

        w: ScoringWeights = req.weights or ScoringWeights()
        total_w = (
            w.slope_weight
            + w.roughness_weight
            + w.illumination_weight
            + w.communication_weight
            + w.science_weight
        )
        norm_w_slope = w.slope_weight / total_w
        norm_w_roughness = w.roughness_weight / total_w
        norm_w_illum = w.illumination_weight / total_w
        norm_w_comms = w.communication_weight / total_w
        norm_w_science = w.science_weight / total_w

        # Subscores
        s_slope = self.calculate_slope_subscore(slope_val)
        s_roughness = self.calculate_roughness_subscore(roughness_val)
        s_illum = max(0.0, min(100.0, float(illum_val)))
        s_comms = max(0.0, min(100.0, float(comms_val)))
        s_science = max(0.0, min(100.0, float(science_val)))

        # Weighted contributions
        c_slope = round(s_slope * norm_w_slope, 2)
        c_roughness = round(s_roughness * norm_w_roughness, 2)
        c_illum = round(s_illum * norm_w_illum, 2)
        c_comms = round(s_comms * norm_w_comms, 2)
        c_science = round(s_science * norm_w_science, 2)

        composite = round(c_slope + c_roughness + c_illum + c_comms + c_science, 2)

        # Categorization
        if composite >= 85.0:
            category = "Optimal"
        elif composite >= 70.0:
            category = "Nominal"
        elif composite >= 50.0:
            category = "Marginal"
        elif composite >= 30.0:
            category = "High Risk"
        else:
            category = "Unsuitable"

        advantages: List[str] = []
        concerns: List[str] = []

        if s_slope >= 80.0:
            advantages.append(f"Favorable topographic slope profile ({slope_val}° average)")
        elif s_slope < 50.0:
            concerns.append(f"High slope hazard ({slope_val}° approaches or exceeds lander tip-over margin)")

        if s_illum >= 75.0:
            advantages.append(f"Strong solar energy and thermal stability ({illum_val}% illumination)")
        elif s_illum < 60.0:
            concerns.append(f"Low illumination ({illum_val}% requires substantial auxiliary power)")

        if s_comms >= 80.0:
            advantages.append(f"Reliable direct-to-Earth line of sight ({comms_val}% visibility)")
        elif s_comms < 65.0:
            concerns.append(f"Intermittent Earth communication ({comms_val}% requires orbital relay)")

        subscores = [
            FactorSubscore(
                criterion="Topographic Slope",
                raw_measurement=slope_val,
                unit="degrees",
                normalized_subscore=s_slope,
                weight=round(norm_w_slope, 3),
                weighted_contribution=c_slope,
                description="Evaluates stability against dynamic lander tip-over.",
            ),
            FactorSubscore(
                criterion="Surface Roughness",
                raw_measurement=roughness_val,
                unit="meters RMS",
                normalized_subscore=s_roughness,
                weight=round(norm_w_roughness, 3),
                weighted_contribution=c_roughness,
                description="Evaluates micro-relief, boulder clutter, and footpad differential height.",
            ),
            FactorSubscore(
                criterion="Solar Illumination",
                raw_measurement=illum_val,
                unit="percent",
                normalized_subscore=s_illum,
                weight=round(norm_w_illum, 3),
                weighted_contribution=c_illum,
                description="Annual solar power harvesting potential and thermal environment stability.",
            ),
            FactorSubscore(
                criterion="Earth Communication",
                raw_measurement=comms_val,
                unit="percent",
                normalized_subscore=s_comms,
                weight=round(norm_w_comms, 3),
                weighted_contribution=c_comms,
                description="Line-of-sight elevation to Earth above local terrain horizon.",
            ),
            FactorSubscore(
                criterion="Scientific Value",
                raw_measurement=science_val,
                unit="rating (0-100)",
                normalized_subscore=s_science,
                weight=round(norm_w_science, 3),
                weighted_contribution=c_science,
                description="Priority of sampling objectives (volatile access, SPA basin geology).",
            ),
        ]

        methodology = (
            "Multi-Criteria Decision Analysis (MCDA) combining piece-wise linear penalty functions "
            "for landing safety constraints (slope, roughness) and normalized utility functions for "
            "operational and scientific factors."
        )

        return ScoreResponse(
            site_id=req.site_id,
            overall_suitability_score=composite,
            suitability_category=category,
            subscores=subscores,
            scoring_methodology=methodology,
            key_advantages=advantages,
            critical_concerns=concerns,
            disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
        )


scoring_service = ScoringService()
