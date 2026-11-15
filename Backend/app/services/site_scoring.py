"""Lunar landing-site preliminary suitability scoring engine.

Evaluates candidate landing locations using multi-criteria decision analysis (MCDA)
combining topographic slope, surface roughness, elevation, crater hazard density,
rock hazard density, and solar illumination.
"""

from typing import Any, Dict, List, Optional, Tuple
from app.core.constants import SCIENTIFIC_SAFETY_DISCLAIMER
from app.schemas.scoring import (
    FactorSubscore,
    ScoreRequest,
    ScoreResponse,
    ScoringWeights,
)
from app.services.site_service import site_service
from app.services.ml.suitability_model_service import suitability_model_service
from maths.scoring import (
    compute_suitability_with_coverage,
    evaluate_crater_hazard_score,
    evaluate_elevation_score,
    evaluate_hard_constraints,
    evaluate_illumination_score,
    evaluate_rock_hazard_score,
    evaluate_roughness_score,
    evaluate_slope_score,
)

CRITERIA_VERSION = "2.0-phase6"
PROVISIONAL_LIMITS_DISCLAIMER = (
    "PROVISIONAL SCREENING NOTICE: Scoring thresholds are project-defined preliminary "
    "decision criteria informed by lunar landing engineering literature (e.g. Bennett et al. "
    "2020; Apollo LM design margins; Barker et al. 2021). They do NOT represent certified NASA "
    "flight qualification limits."
)


class SiteScoringEngine:
    """Computes transparent, configurable landing-site suitability evaluations with explicit data coverage tracking."""

    def __init__(self) -> None:
        self.version = CRITERIA_VERSION

    def evaluate_suitability(self, req: ScoreRequest, run_monte_carlo: bool = True) -> ScoreResponse:
        """Evaluates multi-criteria landing suitability with complete factor breakdown and coverage metrics."""
        warnings: List[str] = [PROVISIONAL_LIMITS_DISCLAIMER]

        # 1. Resolve raw measurements (either from direct payload or catalog site fallback)
        slope = req.slope_deg
        roughness = req.roughness_m
        elev = req.elevation_m
        craters = req.crater_count
        rocks = req.rock_count
        illum = req.illumination_pct
        comms = req.earth_visibility_pct
        science = req.science_value_rating

        if req.site_id:
            site = site_service.get_site_by_id(req.site_id)
            if site:
                if slope is None:
                    slope = site.mean_slope_deg
                if roughness is None and slope is not None:
                    roughness = 0.30 if slope < 6.0 else (0.50 if slope < 10.0 else 0.85)
                if elev is None:
                    elev = site.elevation_m
                if illum is None:
                    illum = site.illumination_pct
                if comms is None:
                    comms = site.earth_visibility_pct
                if science is None:
                    priority_map = {"high": 90.0, "medium": 75.0, "low": 50.0}
                    science = priority_map.get(site.priority.lower(), 75.0)

        # Fallback: resolve from live point terrain if coordinates are provided and measurements omitted
        if req.latitude is not None and req.longitude is not None:
            if slope is None or roughness is None or elev is None:
                try:
                    from app.services.terrain_service import terrain_service
                    pt = terrain_service.get_point_terrain(
                        lat=req.latitude,
                        lon=req.longitude,
                        radius_m=req.radius_m or 50.0,
                    )
                    if pt and pt.is_valid_point:
                        if slope is None and pt.slope_deg is not None:
                            slope = pt.slope_deg
                        if roughness is None and pt.roughness_m is not None:
                            roughness = pt.roughness_m
                        if elev is None and pt.elevation_m is not None:
                            elev = pt.elevation_m
                        if illum is None and pt.solar_illumination_pct is not None:
                            illum = pt.solar_illumination_pct
                except Exception as ex:
                    warnings.append(f"Point terrain sampling note: {ex}")

        # 2. Extract and configure weights
        w = req.weights or ScoringWeights()

        # Check if caller explicitly provided custom weights
        # If custom weights were provided, evaluate only the criteria specified in custom weights
        has_explicit_custom_weights = (
            req.weights is not None
            and (
                w.communication_weight is not None
                or w.science_weight is not None
            )
        )

        is_legacy = (
            (w.communication_weight is not None and w.communication_weight > 0.0)
            or (w.science_weight is not None and w.science_weight > 0.0)
            or (comms is not None and science is not None and craters is None and rocks is None)
        )

        config_weights: Dict[str, float] = {}

        if is_legacy:
            config_weights = {
                "slope": w.slope_weight,
                "roughness": w.roughness_weight,
                "illumination": w.illumination_weight,
                "communication": w.communication_weight if w.communication_weight is not None else 0.15,
                "science": w.science_weight if w.science_weight is not None else 0.10,
            }
        else:
            config_weights = {
                "slope": w.slope_weight,
                "roughness": w.roughness_weight,
                "illumination": w.illumination_weight,
                "crater_hazard": w.crater_hazard_weight,
                "rock_hazard": w.rock_hazard_weight,
                "elevation": w.elevation_weight,
            }
            if w.communication_weight is not None and w.communication_weight > 0.0:
                config_weights["communication"] = w.communication_weight
            if w.science_weight is not None and w.science_weight > 0.0:
                config_weights["science"] = w.science_weight

        # 3. Calculate individual factor subscores (strictly None if unmeasured, DO NOT treat as zero)
        subscores_dict: Dict[str, Optional[float]] = {}

        subscores_dict["slope"] = evaluate_slope_score(slope) if slope is not None else None
        subscores_dict["roughness"] = evaluate_roughness_score(roughness) if roughness is not None else None
        subscores_dict["illumination"] = evaluate_illumination_score(illum) if illum is not None else None

        if "crater_hazard" in config_weights:
            subscores_dict["crater_hazard"] = evaluate_crater_hazard_score(float(craters)) if craters is not None else None
        if "rock_hazard" in config_weights:
            subscores_dict["rock_hazard"] = evaluate_rock_hazard_score(float(rocks)) if rocks is not None else None
        if "elevation" in config_weights:
            subscores_dict["elevation"] = evaluate_elevation_score(elev) if elev is not None else None
        if "communication" in config_weights:
            subscores_dict["communication"] = max(0.0, min(100.0, float(comms))) if comms is not None else None
        if "science" in config_weights:
            subscores_dict["science"] = max(0.0, min(100.0, float(science))) if science is not None else None

        # 4. Compute transparent weighted composite score with coverage tracking
        # Safety gate: Topographic slope is safety-critical. If slope is missing, overall score cannot be computed.
        slope_missing = subscores_dict["slope"] is None

        # Mission profile selection
        mission_profile = req.mission_profile or "artemis_hls"

        # Check hard engineering constraints
        measurements_dict = {
            "slope_deg": slope,
            "max_slope_deg": req.max_slope_deg,
            "p95_slope_deg": req.p95_slope_deg,
            "roughness_m": roughness,
            "elevation_m": elev,
            "crater_count": craters,
            "rock_count": rocks,
            "illumination_pct": illum,
            "earth_visibility_pct": comms,
            "contiguous_diameter_m": req.contiguous_diameter_m,
            "max_continuous_dark_h": req.max_continuous_dark_h,
        }

        # Evaluate mission constraints
        _, all_violations = evaluate_hard_constraints(
            measurements_dict,
            profile_id=mission_profile,
        )

        hard_violations: List[str] = []
        is_hard_violated = False

        # Universal physical tip-over limit (slope > 15 deg) always triggers disqualification
        if slope is not None and slope > 15.0:
            is_hard_violated = True
            hard_violations.append(f"Mean slope ({slope:.1f}°) exceeds universal Apollo/Artemis tip-over limit (15.0°).")

        # If caller explicitly requested a mission profile, enforce that profile's constraints
        if req.mission_profile is not None:
            for v in all_violations:
                if v not in hard_violations:
                    hard_violations.append(v)
            if all_violations:
                is_hard_violated = True

        for violation in hard_violations:
            warnings.append(f"HARD CONSTRAINT VIOLATION: {violation}")

        composite_score, coverage_fraction, missing_factors, contributions = compute_suitability_with_coverage(
            factor_subscores=subscores_dict,
            factor_weights=config_weights,
            min_coverage_threshold=0.50,
        )

        score_coverage_pct = round(coverage_fraction * 100.0, 1)

        # 5. Determine preliminary category
        if slope_missing:
            composite_score = None
            category = "Insufficient data"
            warnings.append(
                "Topographic slope is missing. Slope is a safety-critical touchdown parameter; "
                "overall suitability score cannot be reliably established without slope."
            )
        elif composite_score is None or score_coverage_pct < 50.0:
            composite_score = None
            category = "Insufficient data"
            warnings.append(
                f"Data coverage ({score_coverage_pct}%) is below minimum threshold (50.0%). "
                "Overall suitability score reported as null to prevent unreliable site ranking."
            )
        elif is_hard_violated:
            # Hard exclusion gating: sites violating physical limits cannot rank highly
            if composite_score is not None and composite_score > 35.0:
                composite_score = 35.0
            if is_legacy:
                category = "Unsuitable"
            else:
                category = "Lower preliminary suitability"
                if slope is not None and slope > 15.0:
                    warnings.append(f"CRITICAL HAZARD: Average slope ({slope:.1f}°) exceeds lander tip-over limit (15.0°).")
        else:
            if is_legacy:
                if slope is not None and slope > 15.0:
                    category = "Unsuitable"
                elif composite_score >= 85.0:
                    category = "Optimal"
                elif composite_score >= 70.0:
                    category = "Nominal"
                elif composite_score >= 50.0:
                    category = "Marginal"
                elif composite_score >= 30.0:
                    category = "High Risk"
                else:
                    category = "Unsuitable"
            else:
                if slope is not None and slope > 15.0:
                    category = "Lower preliminary suitability"
                    warnings.append(f"CRITICAL HAZARD: Average slope ({slope:.1f}°) exceeds lander tip-over limit (15.0°).")
                elif composite_score >= 80.0 and (slope is None or slope <= 8.0) and score_coverage_pct >= 70.0:
                    category = "Higher preliminary suitability"
                elif composite_score >= 60.0 and (slope is None or slope <= 12.0):
                    category = "Moderate preliminary suitability"
                else:
                    category = "Lower preliminary suitability"

        if missing_factors:
            warnings.append(
                f"Missing measurements for: {', '.join(missing_factors)}. Missing factors were NOT scored as zero "
                "and weights were NOT silently redistributed."
            )

        # Evaluate ML surrogate model predictions and uncertainty if data is sufficient
        ml_score: Optional[float] = None
        ml_version: Optional[str] = None
        unc_std: Optional[float] = None
        conf_int: Optional[List[float]] = None
        feat_contribs: Optional[Dict[str, float]] = None

        if not slope_missing and composite_score is not None:
            try:
                ml_pred = suitability_model_service.predict_suitability(
                    features=measurements_dict,
                    mission_profile=mission_profile,
                    run_monte_carlo=run_monte_carlo,
                )
                ml_score = ml_pred.ml_suitability_score
                ml_version = ml_pred.model_version
                unc_std = ml_pred.uncertainty_score_std
                conf_int = ml_pred.confidence_interval_95
                feat_contribs = {**ml_pred.top_positive_features, **ml_pred.top_risk_features}
            except Exception as e:
                warnings.append(f"ML surrogate inference unavailable: {str(e)}")

        # 6. Build detailed subscores breakdown list
        total_w = sum(config_weights.values())
        subscores_list: List[FactorSubscore] = []

        factor_meta: Dict[str, Dict[str, Any]] = {
            "slope": {
                "name": "Topographic Slope",
                "raw": slope,
                "unit": "degrees",
                "dir": "lower_is_better",
                "desc": "Evaluates lander stability against dynamic tip-over and leg buckling (ideal <= 5°, critical > 15°).",
            },
            "roughness": {
                "name": "Surface Roughness",
                "raw": roughness,
                "unit": "meters RMS",
                "dir": "lower_is_better",
                "desc": "Evaluates micro-relief, footpad differential height, and engine nozzle ground clearance.",
            },
            "illumination": {
                "name": "Solar Illumination",
                "raw": illum,
                "unit": "percent",
                "dir": "higher_is_better",
                "desc": "Evaluates solar power harvesting potential and thermal stabilization (ideal >= 80%).",
            },
            "crater_hazard": {
                "name": "Crater Hazards",
                "raw": float(craters) if craters is not None else None,
                "unit": "craters count",
                "dir": "lower_is_better",
                "desc": "Evaluates concave depressions, loose rim regolith, and footpad differential tilt.",
            },
            "rock_hazard": {
                "name": "Rock Hazards",
                "raw": float(rocks) if rocks is not None else None,
                "unit": "boulders count",
                "dir": "lower_is_better",
                "desc": "Evaluates puncture risks to fuel tanks, landing gear hang-up, and chassis clearance.",
            },
            "elevation": {
                "name": "Surface Elevation",
                "raw": elev,
                "unit": "meters",
                "dir": "higher_is_better",
                "desc": "Highland plateaus afford reduced descent delta-V and avoid cryogenic crater floor traps.",
            },
            "communication": {
                "name": "Earth Communication",
                "raw": comms,
                "unit": "percent",
                "dir": "higher_is_better",
                "desc": "Direct line-of-sight communication visibility to Earth.",
            },
            "science": {
                "name": "Scientific Priority",
                "raw": science,
                "unit": "rating (0-100)",
                "dir": "higher_is_better",
                "desc": "Sampling access to volatile-bearing cold traps and ancient crustal stratigraphy.",
            },
        }

        advantages: List[str] = []
        concerns: List[str] = []

        for key, w_val in config_weights.items():
            meta = factor_meta.get(key, {"name": key, "raw": None, "unit": "N/A", "dir": "N/A", "desc": ""})
            sub_score = subscores_dict.get(key)
            norm_w = round(w_val / total_w, 3)
            contrib = round(sub_score * norm_w, 2) if sub_score is not None else None
            is_avail = sub_score is not None

            subscores_list.append(
                FactorSubscore(
                    criterion=meta["name"],
                    raw_measurement=round(meta["raw"], 2) if meta["raw"] is not None else None,
                    unit=meta["unit"],
                    normalized_subscore=round(sub_score, 2) if sub_score is not None else None,
                    weight=norm_w,
                    weighted_contribution=contrib,
                    status="available" if is_avail else "missing",
                    preference_direction=meta["dir"],
                    description=meta["desc"],
                )
            )

            # Analyze key advantages and concerns
            if is_avail and sub_score is not None:
                if sub_score >= 80.0:
                    advantages.append(f"Strong {meta['name'].lower()} profile ({meta['raw']} {meta['unit']}, score {sub_score:.0f}/100)")
                elif sub_score < 40.0:
                    if key == "slope" and meta["raw"] is not None and meta["raw"] > 15.0:
                        concerns.append(f"High slope hazard ({meta['raw']}° approaches or exceeds lander tip-over margin)")
                    else:
                        concerns.append(f"Adverse {meta['name'].lower()} risk ({meta['raw']} {meta['unit']}, score {sub_score:.0f}/100)")
            else:
                concerns.append(f"{meta['name']} is unmeasured (missing scientific data)")

        methodology = (
            "Multi-Criteria Decision Analysis (MCDA) combining piece-wise linear penalty functions "
            "for safety-critical landing constraints (slope, roughness, hazards) with normalized "
            "utility functions for environmental and operational factors. Explicit data coverage tracking "
            "prevents missing factors from being treated as zero or silently inflated."
        )

        return ScoreResponse(
            site_id=req.site_id,
            overall_suitability_score=composite_score,
            scientific_baseline_score=composite_score,
            ml_model_score=ml_score,
            model_version=ml_version,
            mission_profile=mission_profile,
            hard_constraint_status="violated" if is_hard_violated else "passed",
            hard_constraint_violations=hard_violations,
            uncertainty_score_std=unc_std,
            confidence_interval_95=conf_int,
            feature_contributions=feat_contribs,
            suitability_category=category,
            score_coverage_pct=score_coverage_pct,
            missing_factors=missing_factors,
            evaluated_factors_count=len(config_weights) - len(missing_factors),
            total_factors_count=len(config_weights),
            subscores=subscores_list,
            scoring_methodology=methodology,
            key_advantages=advantages,
            critical_concerns=concerns,
            warnings=warnings,
            criteria_version=self.version,
            disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
        )


site_scoring_engine = SiteScoringEngine()
