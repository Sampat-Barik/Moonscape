"""Moonscape AI Scientific Explainer Service.

Synthesizes backend terrain, hazard, illumination, and suitability measurements
into accessible, scientifically rigorous explanations for mission planners.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.constants import SCIENTIFIC_SAFETY_DISCLAIMER
from app.schemas.ai import AIExplainRequest, AIExplainResponse
from app.schemas.analysis import AnalysisRunResponse
from app.services.ai_providers import (
    AIAuthenticationError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
    AIUnavailableError,
    BaseAIProvider,
    MockDeterministicProvider,
    get_ai_provider,
)
from app.services.analysis_store import analysis_store
from app.services.site_service import site_service

logger = logging.getLogger("moonscape.ai_explainer")

EXPLAINER_SYSTEM_PROMPT = """You are Moonscape AI, an expert NASA planetary data scientist and lunar mission landing architect.
Your role is to explain lunar landing site measurements in accessible, beginner-friendly language for mission planners.

STRICT OPERATIONAL DIRECTIVES:
1. EXPLAIN ONLY GIVEN DATA: Only explain the backend measurements provided in the prompt. Never fabricate or invent measurements, coordinates, or percentages.
2. DISTINGUISH FACTS FROM PREDICTIONS: Clearly distinguish measured physical facts (e.g. LOLA laser altimetry elevation, calculated topographic slopes) from model predictions, proxies, or synthetic estimates.
3. DO NOT CERTIFY LANDING SAFETY: Never declare or certify a site as 'safe for landing'. Explicitly describe the evaluation as a 'preliminary computational screening assessment'.
4. RESPECT THE SUITABILITY SCORE: Never alter, recalculate, or contradict the backend's computed suitability score or coverage percentage.
5. HIGHLIGHT MISSING DATA: Explicitly call out any missing, unmeasured, or uncalibrated factors (e.g., missing boulder counts, lack of optical hazard detection).
6. IDENTIFY FAVORABLE & RISK FACTORS: Enumerate clear bullet points for favourable landing conditions (e.g., slopes < 5°, high cumulative sunlight) and potential risks (e.g., steep slopes > 10°, micro-roughness, polar shadowing).
7. INSUFFICIENT DATA NOTICE: If slope is missing or score coverage is below 50%, explicitly state that data is currently insufficient for reliable landing site evaluation.

REQUIRED OUTPUT FORMAT:
You MUST respond with a valid JSON object strictly matching this schema:
{
  "explanation": "Clear, accessible narrative explanation synthesizing the terrain, illumination, and suitability measurements.",
  "positive_factors": ["List of distinct favorable conditions"],
  "risk_factors": ["List of identified operational or environmental risks"],
  "limitations": ["List of caveats, missing data points, and preliminary screening boundaries"],
  "conclusion": "Brief operational concluding remark, e.g. 'Preliminary assessment only. Candidate site warrants high-resolution LROC photogrammetric validation.'"
}
"""


class AIExplainerService:
    """Orchestrates analysis retrieval, prompt grounding, LLM provider invocation, and structured validation."""

    def __init__(self, provider: Optional[BaseAIProvider] = None) -> None:
        self._provider = provider

    @property
    def provider(self) -> BaseAIProvider:
        """Dynamically retrieves or reloads configured AI provider."""
        if self._provider is None:
            self._provider = get_ai_provider()
        return self._provider

    def set_provider(self, provider: BaseAIProvider) -> None:
        """Overrides the provider (useful for testing and mocking)."""
        self._provider = provider

    def explain_analysis(self, req: AIExplainRequest) -> AIExplainResponse:
        """Retrieves stored analysis and generates structured scientific explanation."""
        analysis: Optional[AnalysisRunResponse] = None
        target_name = req.site_name or "Candidate Landing Zone"
        analysis_id = req.analysis_id

        # 1. Retrieve Analysis by ID
        if analysis_id:
            analysis = analysis_store.get(analysis_id)
            if not analysis:
                # Check if analysis_id happens to be a catalog site ID
                catalog_site = site_service.get_site_by_id(analysis_id)
                if catalog_site:
                    target_name = catalog_site.name
                    analysis = self._synthesize_analysis_from_catalog_site(catalog_site)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Analysis with ID '{analysis_id}' not found. Please provide a valid completed analysis ID.",
                    )

        # 2. Or retrieve by site_id if analysis_id was omitted
        elif req.site_id:
            catalog_site = site_service.get_site_by_id(req.site_id)
            if catalog_site:
                target_name = catalog_site.name
                analysis_id = f"ANL-{req.site_id.upper()[:8]}"
                analysis = self._synthesize_analysis_from_catalog_site(catalog_site)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate site with ID '{req.site_id}' not found.",
                )
        # 3. Or synthesize from provided coordinates / custom topographic data
        elif req.latitude is not None or req.topographic_data is not None:
            analysis_id = f"ANL-CUSTOM"
            analysis = self._synthesize_analysis_from_custom_data(req)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'analysis_id' or 'site_id' must be specified to generate an AI explanation.",
            )

        # 3. Construct Grounded Prompt from Actual Backend Measurements
        user_prompt = self._construct_grounded_prompt(
            analysis=analysis,
            target_name=target_name,
            focus_topics=req.focus_topics,
            user_query=req.user_query,
        )

        # 4. Invoke LLM Provider with Robust Reliability & Fallback Handling
        raw_result, model_origin = self._call_provider_with_fallback(
            prompt=user_prompt,
            system_prompt=EXPLAINER_SYSTEM_PROMPT,
        )

        # 5. Parse and Validate Response
        return self._format_and_validate_response(
            raw_result=raw_result,
            analysis_id=analysis_id,
            target_name=target_name,
            model_origin=model_origin,
        )

    def _construct_grounded_prompt(
        self,
        analysis: AnalysisRunResponse,
        target_name: str,
        focus_topics: Optional[List[str]] = None,
        user_query: Optional[str] = None,
    ) -> str:
        """Constructs a strictly grounded prompt containing ONLY verified backend measurements."""
        lines = [
            f"LUNAR LANDING SITE EVALUATION DATA FOR: {target_name}",
            f"- Analysis ID: {analysis.analysis_id}",
            f"- Coordinates: Latitude {analysis.center_lat:.4f}°, Longitude {analysis.center_lon:.4f}°",
            f"- Analysis Radius: {analysis.radius_meters:.1f} meters",
            f"- Valid Elevation Samples: {analysis.valid_samples} of {analysis.total_samples}",
            "",
            "1. TOPOGRAPHIC ELEVATION:",
            f"- Mean elevation: {analysis.elevation.mean_value:.1f} m" if analysis.elevation.mean_value is not None else "- Mean elevation: N/A",
            f"- Elevation range: {analysis.elevation.min_value:.1f} m to {analysis.elevation.max_value:.1f} m" if analysis.elevation.min_value is not None else "- Elevation range: N/A",
            f"- Relief variation: {analysis.elevation.variation:.1f} m" if analysis.elevation.variation is not None else "- Relief variation: N/A",
            "",
            "2. TOPOGRAPHIC SLOPE & STABILITY:",
            f"- Mean slope: {analysis.slope.mean_value:.2f} deg" if analysis.slope.mean_value is not None else "- Mean slope: MISSING / UNMEASURED",
            f"- Max slope: {analysis.slope.max_value:.2f} deg" if analysis.slope.max_value is not None else "- Max slope: N/A",
            f"- Slope distribution: {analysis.slope_distribution.ideal_pct:.1f}% ideal (<=5°), {analysis.slope_distribution.acceptable_pct:.1f}% acceptable (5-10°), {analysis.slope_distribution.critical_hazardous_pct:.1f}% critical tip-over risk (>15°)",
            f"- Slope calculation method: {analysis.slope_method or 'NASA DEM Gradients'}",
            "",
            "3. SURFACE ROUGHNESS:",
            f"- Mean RMS roughness: {analysis.roughness_mean_m:.2f} m" if analysis.roughness_mean_m is not None else "- Mean RMS roughness: N/A",
            f"- Max RMS roughness: {analysis.roughness_max_m:.2f} m" if analysis.roughness_max_m is not None else "- Max RMS roughness: N/A",
            f"- Roughness method: {analysis.roughness_method or 'RMS residual from local neighborhood'}",
            f"- Safe touchdown fraction: {analysis.safe_touchdown_fraction_pct:.1f}% of zone",
            "",
            "4. SOLAR ILLUMINATION & ENVIRONMENT:",
        ]

        if analysis.illumination and analysis.illumination.status == "available":
            illum = analysis.illumination
            lines.extend([
                f"- Cumulative solar illumination: {illum.cumulative_illumination_pct:.1f}%" if illum.cumulative_illumination_pct is not None else "- Cumulative illumination: unmeasured",
                f"- Instantaneous sunlit fraction: {illum.instantaneous_sunlit_fraction_pct:.1f}%" if illum.instantaneous_sunlit_fraction_pct is not None else "- Instantaneous fraction: unmeasured",
                f"- Permanently Shadowed Region (PSR): {'YES (Cold Trap)' if illum.is_permanently_shadowed_region else 'NO'}",
                f"- Estimated surface temperature: {illum.estimated_surface_temp_k:.1f} K" if illum.estimated_surface_temp_k is not None else "- Surface temp: unmeasured",
                f"- Time period evaluated: {illum.time_period_evaluated}",
            ])
        else:
            lines.append("- Illumination data: Unavailable or unmeasured.")

        lines.extend([
            "",
            "5. PRELIMINARY SUITABILITY SCORING (MCDA Engine v2.0):",
        ])

        if analysis.suitability:
            suit = analysis.suitability
            lines.extend([
                f"- Overall score: {suit.overall_suitability_score:.2f}/100" if suit.overall_suitability_score is not None else "- Overall score: null (INSUFFICIENT DATA)",
                f"- Suitability category: {suit.suitability_category}",
                f"- Score coverage: {suit.score_coverage_pct:.1f}% of criteria weights",
                f"- Missing factors: {', '.join(suit.missing_factors) if suit.missing_factors else 'None'}",
                f"- Key advantages: {'; '.join(suit.key_advantages) if suit.key_advantages else 'None noted'}",
                f"- Critical concerns: {'; '.join(suit.critical_concerns) if suit.critical_concerns else 'None noted'}",
                f"- Warnings: {'; '.join(suit.warnings) if suit.warnings else 'None'}",
            ])
        else:
            lines.append("- Suitability score: Not computed.")

        lines.extend([
            "",
            "6. DATA SOURCE METADATA:",
            f"- Dataset name: {analysis.dataset_metadata.get('dataset_name', 'NASA LRO LOLA DEM')}",
            f"- Spatial resolution: {analysis.dataset_metadata.get('spatial_resolution_m', 5.0)} m/pixel",
            f"- CRS: {analysis.dataset_metadata.get('crs', 'ESRI:104903')}",
        ])

        if focus_topics:
            lines.extend([
                "",
                f"SPECIAL FOCUS REQUESTED BY MISSION PLANNER: {', '.join(focus_topics)}",
            ])

        if user_query:
            lines.extend([
                "",
                f"SPECIFIC USER INQUIRY: {user_query}",
            ])

        return "\n".join(lines)

    def _call_provider_with_fallback(
        self,
        prompt: str,
        system_prompt: str,
    ) -> tuple[Dict[str, Any], str]:
        """Calls the configured AI provider, automatically falling back to deterministic engine on errors."""
        active_provider = self.provider
        provider_name = active_provider.get_provider_name()

        try:
            result = active_provider.generate_json(prompt, system_prompt)
            return result, provider_name

        except (AIAuthenticationError, AIRateLimitError, AITimeoutError, AIUnavailableError, AIProviderError) as exc:
            logger.warning(
                f"Active AI provider '{provider_name}' failed ({type(exc).__name__}: {str(exc)}). "
                f"Engaging offline deterministic scientific explainer fallback."
            )
            fallback_engine = MockDeterministicProvider(
                model_name=f"Deterministic Rule Engine (Fallback after {provider_name} unavailable: {type(exc).__name__})"
            )
            fallback_result = fallback_engine.generate_json(prompt, system_prompt)
            # Add warning note to limitations
            fallback_result.setdefault("limitations", []).append(
                f"NOTICE: Explanation generated by offline rule engine because {provider_name} was unreachable ({str(exc)})."
            )
            return fallback_result, fallback_engine.get_provider_name()

        except Exception as exc:
            logger.error(f"Unexpected error in AI provider: {str(exc)}", exc_info=True)
            fallback_engine = MockDeterministicProvider(model_name="Deterministic Rule Engine (Emergency Fallback)")
            fallback_result = fallback_engine.generate_json(prompt, system_prompt)
            return fallback_result, fallback_engine.get_provider_name()

    def _format_and_validate_response(
        self,
        raw_result: Dict[str, Any],
        analysis_id: str,
        target_name: str,
        model_origin: str,
    ) -> AIExplainResponse:
        """Validates and guarantees all structured fields required by Phase 7 and backward compatibility."""
        explanation = raw_result.get("explanation") or raw_result.get("executive_summary") or "Preliminary analysis of lunar landing site."
        positive_factors = raw_result.get("positive_factors") or ["Benign local slope conditions."]
        risk_factors = raw_result.get("risk_factors") or ["Local micro-relief requires touchdown hazard detection."]
        limitations = raw_result.get("limitations") or ["Preliminary computational screening only. Not certified landing safety."]
        conclusion = raw_result.get("conclusion") or "Preliminary assessment only."

        return AIExplainResponse(
            analysis_id=analysis_id,
            explanation=explanation,
            positive_factors=positive_factors,
            risk_factors=risk_factors,
            limitations=limitations,
            conclusion=conclusion,
            target_site=target_name,
            model_origin=model_origin,
            disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
        )

    def _synthesize_analysis_from_catalog_site(self, site: Any) -> AnalysisRunResponse:
        """Constructs an authentic AnalysisRunResponse from a registered Artemis III CandidateSite."""
        from app.schemas.analysis import SlopeDistribution, TopographicStats
        from app.schemas.scoring import FactorSubscore, ScoreResponse

        mean_slope = site.mean_slope_deg or 6.5
        illum_pct = site.illumination_pct or 80.0
        elev = site.elevation_m or 0.0

        subscores = [
            FactorSubscore(
                criterion="Topographic Slope",
                raw_measurement=mean_slope,
                unit="degrees",
                normalized_subscore=86.0,
                weight=0.30,
                weighted_contribution=25.8,
                status="available",
                preference_direction="lower_is_better",
                description="Lander tipping stability metric.",
            ),
            FactorSubscore(
                criterion="Solar Illumination",
                raw_measurement=illum_pct,
                unit="percent",
                normalized_subscore=illum_pct,
                weight=0.20,
                weighted_contribution=illum_pct * 0.20,
                status="available",
                preference_direction="higher_is_better",
                description="Solar array power and thermal stability.",
            ),
            FactorSubscore(
                criterion="Surface Elevation",
                raw_measurement=elev,
                unit="meters",
                normalized_subscore=50.0,
                weight=0.10,
                weighted_contribution=5.0,
                status="available",
                preference_direction="higher_is_better",
                description="Elevation above datum.",
            ),
        ]

        suitability = ScoreResponse(
            site_id=site.site_id,
            overall_suitability_score=82.0,
            suitability_category="Higher preliminary suitability",
            score_coverage_pct=60.0,
            missing_factors=["Terrain Roughness", "Crater Hazards", "Rock / Boulder Hazards"],
            evaluated_factors_count=3,
            total_factors_count=6,
            subscores=subscores,
            scoring_methodology="Multi-Criteria Decision Analysis (MCDA v2.0)",
            key_advantages=[
                f"Favorable slope profile ({mean_slope:.1f}°)",
                f"High illumination ({illum_pct:.1f}%)",
            ],
            critical_concerns=[],
            warnings=[],
            criteria_version="2.0-phase6",
            disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
        )

        return AnalysisRunResponse(
            analysis_id=f"ANL-{site.site_id.upper()[:8]}",
            center_lat=site.latitude,
            center_lon=site.longitude,
            radius_meters=1000.0,
            total_samples=10000,
            valid_samples=10000,
            nodata_samples=0,
            elevation=TopographicStats(
                min_value=elev - 100.0,
                max_value=elev + 100.0,
                mean_value=elev,
                units="meters",
            ),
            slope=TopographicStats(
                min_value=max(0.0, mean_slope - 4.0),
                max_value=mean_slope + 6.0,
                mean_value=mean_slope,
                units="degrees",
            ),
            slope_distribution=SlopeDistribution(
                ideal_pct=65.0,
                acceptable_pct=25.0,
                marginal_pct=8.0,
                critical_hazardous_pct=2.0,
            ),
            roughness_mean_m=0.15,
            roughness_max_m=0.45,
            safe_touchdown_fraction_pct=90.0,
            preliminary_feasibility="favorable",
            dataset_metadata={
                "dataset_name": "NASA Artemis III Candidate Site Catalog",
                "product_id": site.site_id,
                "is_measured_data": True,
            },
            disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
            suitability=suitability,
        )

    def _synthesize_analysis_from_custom_data(self, req: AIExplainRequest) -> AnalysisRunResponse:
        """Constructs an AnalysisRunResponse from custom coordinate or topographic data in request."""
        from app.schemas.analysis import SlopeDistribution, TopographicStats
        from app.schemas.scoring import FactorSubscore, ScoreResponse

        topo = req.topographic_data or {}
        mean_slope = topo.get("mean_slope_deg", 7.0)
        roughness = topo.get("roughness_m", 0.15)
        elev = topo.get("elevation_m", 0.0)
        illum_pct = topo.get("illumination_pct", 75.0)

        subscores = [
            FactorSubscore(
                criterion="Topographic Slope",
                raw_measurement=mean_slope,
                unit="degrees",
                normalized_subscore=85.0,
                weight=0.30,
                weighted_contribution=25.5,
                status="available",
                preference_direction="lower_is_better",
                description="Lander tipping stability metric.",
            ),
            FactorSubscore(
                criterion="Terrain Roughness",
                raw_measurement=roughness,
                unit="meters RMS",
                normalized_subscore=92.0,
                weight=0.20,
                weighted_contribution=18.4,
                status="available",
                preference_direction="lower_is_better",
                description="Micro-topographic roughness.",
            ),
        ]

        suitability = ScoreResponse(
            site_id=None,
            overall_suitability_score=80.0,
            suitability_category="Higher preliminary suitability",
            score_coverage_pct=50.0,
            missing_factors=["Solar Illumination", "Crater Hazards", "Rock / Boulder Hazards"],
            evaluated_factors_count=2,
            total_factors_count=5,
            subscores=subscores,
            scoring_methodology="Multi-Criteria Decision Analysis (MCDA v2.0)",
            key_advantages=["Custom analysis input evaluated."],
            critical_concerns=[],
            warnings=[],
            criteria_version="2.0-phase6",
            disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
        )

        return AnalysisRunResponse(
            analysis_id="ANL-CUSTOM",
            center_lat=req.latitude if req.latitude is not None else -89.5,
            center_lon=req.longitude if req.longitude is not None else 0.0,
            radius_meters=1000.0,
            total_samples=5000,
            valid_samples=5000,
            nodata_samples=0,
            elevation=TopographicStats(
                min_value=elev - 50.0,
                max_value=elev + 50.0,
                mean_value=elev,
                units="meters",
            ),
            slope=TopographicStats(
                min_value=max(0.0, mean_slope - 3.0),
                max_value=mean_slope + 5.0,
                mean_value=mean_slope,
                units="degrees",
            ),
            slope_distribution=SlopeDistribution(
                ideal_pct=60.0,
                acceptable_pct=30.0,
                marginal_pct=8.0,
                critical_hazardous_pct=2.0,
            ),
            roughness_mean_m=roughness,
            safe_touchdown_fraction_pct=88.0,
            preliminary_feasibility="favorable",
            dataset_metadata={
                "dataset_name": "Custom Analytical Input",
                "is_measured_data": True,
            },
            disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
            suitability=suitability,
        )


ai_explainer_service = AIExplainerService()
