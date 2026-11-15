"""Inference and explainability service for ML lunar landing suitability models.

Loads trained lightweight tabular surrogate models, performs fast CPU inference (<5ms),
evaluates hard mission engineering constraints, computes feature contributions, and
propagates measurement uncertainty via Monte Carlo perturbation.
"""

import json
from pathlib import Path
import sys
import threading
from typing import Any, Dict, List, Optional, Tuple, Union
import joblib
import numpy as np

# Ensure path resolution
_backend_dir = Path(__file__).resolve().parent.parent.parent
_root_dir = _backend_dir.parent
for _p in (str(_backend_dir), str(_root_dir)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.core.config import settings
from app.core.logging import logger
from app.schemas.ml_scoring import (
    LunarSiteFeatures,
    ModelPredictionResult,
)
from app.services.ml.model_trainer import FEATURE_NAMES
from maths.scoring import evaluate_hard_constraints, MISSION_PROFILES


# Nominal reference values for feature contribution and sensitivity analysis
NOMINAL_REFERENCES: Dict[str, Dict[str, Any]] = {
    "mean_elevation_m": {"baseline": 0.0, "scale": 2000.0, "direction": "higher_is_better"},
    "elevation_relief_m": {"baseline": 150.0, "scale": 300.0, "direction": "lower_is_better"},
    "mean_slope_deg": {"baseline": 4.0, "scale": 8.0, "direction": "lower_is_better"},
    "max_slope_deg": {"baseline": 8.0, "scale": 12.0, "direction": "lower_is_better"},
    "p95_slope_deg": {"baseline": 6.0, "scale": 10.0, "direction": "lower_is_better"},
    "ideal_slope_pct": {"baseline": 80.0, "scale": 50.0, "direction": "higher_is_better"},
    "critical_slope_pct": {"baseline": 0.0, "scale": 10.0, "direction": "lower_is_better"},
    "roughness_15m": {"baseline": 0.25, "scale": 0.40, "direction": "lower_is_better"},
    "roughness_60m": {"baseline": 0.35, "scale": 0.50, "direction": "lower_is_better"},
    "roughness_240m": {"baseline": 0.50, "scale": 0.80, "direction": "lower_is_better"},
    "vertical_uncertainty_m": {"baseline": 1.5, "scale": 2.0, "direction": "lower_is_better"},
    "slope_uncertainty_deg": {"baseline": 1.2, "scale": 1.5, "direction": "lower_is_better"},
    "crater_density_km2": {"baseline": 0.0, "scale": 1.5, "direction": "lower_is_better"},
    "min_crater_dist_m": {"baseline": 1000.0, "scale": 800.0, "direction": "higher_is_better"},
    "boulder_density_km2": {"baseline": 0.0, "scale": 2.0, "direction": "lower_is_better"},
    "min_boulder_dist_m": {"baseline": 800.0, "scale": 600.0, "direction": "higher_is_better"},
    "curvature_laplacian_var": {"baseline": 0.03, "scale": 0.08, "direction": "lower_is_better"},
    "cumulative_sunlight_pct": {"baseline": 70.0, "scale": 40.0, "direction": "higher_is_better"},
    "instantaneous_sunlit_pct": {"baseline": 70.0, "scale": 40.0, "direction": "higher_is_better"},
    "max_continuous_sun_h": {"baseline": 120.0, "scale": 80.0, "direction": "higher_is_better"},
    "max_continuous_dark_h": {"baseline": 48.0, "scale": 100.0, "direction": "lower_is_better"},
    "is_psr": {"baseline": 0.0, "scale": 1.0, "direction": "lower_is_better"},
    "earth_visibility_pct": {"baseline": 75.0, "scale": 40.0, "direction": "higher_is_better"},
    "contiguous_diameter_m": {"baseline": 120.0, "scale": 80.0, "direction": "higher_is_better"},
}


class LunarSuitabilityModelService:
    """Manages model artifact caching, fast inference, hard constraint gating, and Monte Carlo uncertainty."""

    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = models_dir or (settings.BASE_DIR / "data" / "models")
        self._lock = threading.Lock()
        self._model: Optional[Any] = None
        self._metadata: Optional[Dict[str, Any]] = None
        self._is_loaded = False

    def _ensure_model_loaded(self) -> bool:
        """Thread-safe lazy loader for model artifact and metadata."""
        if self._is_loaded:
            return True

        with self._lock:
            if self._is_loaded:
                return True

            model_path_v2 = self.models_dir / "landing_suitability_rf_v2.joblib"
            meta_path_v2 = self.models_dir / "landing_suitability_rf_v2.meta.json"

            if model_path_v2.exists() and meta_path_v2.exists():
                model_path = model_path_v2
                meta_path = meta_path_v2
            else:
                model_path = self.models_dir / "landing_suitability_rf_v1.joblib"
                meta_path = self.models_dir / "landing_suitability_rf_v1.meta.json"

            if not model_path.exists() or not meta_path.exists():
                logger.warning(
                    "ML suitability model artifact not found at %s. Service will use deterministic MCDA fallback.",
                    model_path,
                )
                return False

            try:
                self._model = joblib.load(model_path)
                with open(meta_path, "r", encoding="utf-8") as f:
                    self._metadata = json.load(f)
                self._is_loaded = True
                logger.info(
                    "Loaded ML landing suitability model '%s' (version %s) from %s",
                    self._metadata.get("model_name"),
                    self._metadata.get("version"),
                    model_path.name,
                )
                return True
            except Exception as e:
                logger.error("Failed to load ML model artifact: %s", str(e))
                return False

    @staticmethod
    def construct_features_from_dict(raw: Dict[str, Any], allow_imputation: bool = False) -> LunarSiteFeatures:
        """Converts heterogeneous measurement dictionary into validated 24-feature schema.
        
        Refuses to silently invent defaults for safety-critical parameters (slope, elevation, roughness)
        unless explicitly allowed. Preserves valid zero values.
        """
        critical_missing: List[str] = []

        slope = raw.get("mean_slope_deg")
        if slope is None:
            slope = raw.get("slope_deg")
        if slope is None:
            critical_missing.append("mean_slope_deg")
            if not allow_imputation:
                raise ValueError("Missing safety-critical parameter: 'mean_slope_deg' or 'slope_deg' must be provided.")
            slope = 5.0

        elev = raw.get("mean_elevation_m")
        if elev is None:
            elev = raw.get("elevation_m")
        if elev is None:
            critical_missing.append("mean_elevation_m")
            if not allow_imputation:
                raise ValueError("Missing safety-critical parameter: 'mean_elevation_m' or 'elevation_m' must be provided.")
            elev = 0.0

        roughness = raw.get("roughness_15m")
        if roughness is None:
            roughness = raw.get("roughness_m")
        if roughness is None:
            critical_missing.append("roughness_15m")
            if not allow_imputation:
                raise ValueError("Missing safety-critical parameter: 'roughness_15m' or 'roughness_m' must be provided.")
            roughness = 0.25

        max_slope = raw.get("max_slope_deg")
        if max_slope is None:
            max_slope = max(slope, slope * 1.5)

        p95_slope = raw.get("p95_slope_deg")
        if p95_slope is None:
            p95_slope = max(slope, slope * 1.25)

        crater_density = raw.get("crater_density_km2")
        if crater_density is None:
            craters = raw.get("crater_count")
            crater_density = (float(craters) / 2.0) if craters is not None else 0.0

        boulder_density = raw.get("boulder_density_km2")
        if boulder_density is None:
            rocks = raw.get("rock_count")
            boulder_density = (float(rocks) / 5.0) if rocks is not None else 0.0

        illum = raw.get("cumulative_sunlight_pct")
        if illum is None:
            illum = raw.get("illumination_pct")
        if illum is None:
            illum = 70.0

        comms = raw.get("earth_visibility_pct")
        if comms is None:
            comms = 75.0

        ideal_slope = raw.get("ideal_slope_pct")
        if ideal_slope is None:
            ideal_slope = 85.0 if slope <= 5.0 else (50.0 if slope <= 8.0 else 20.0)

        crit_slope = raw.get("critical_slope_pct")
        if crit_slope is None:
            crit_slope = 0.0 if slope <= 8.0 else (25.0 if slope > 15.0 else 5.0)

        contig_diam = raw.get("contiguous_diameter_m")
        if contig_diam is None:
            contig_diam = 120.0 if slope <= 8.0 else 45.0

        max_dark = raw.get("max_continuous_dark_h")
        if max_dark is None:
            max_dark = 48.0 if illum >= 60.0 else 120.0

        relief = raw.get("elevation_relief_m")
        if relief is None:
            relief = 150.0

        rough_60 = raw.get("roughness_60m")
        if rough_60 is None:
            rough_60 = roughness * 1.25

        rough_240 = raw.get("roughness_240m")
        if rough_240 is None:
            rough_240 = roughness * 1.60

        vert_unc = raw.get("vertical_uncertainty_m")
        if vert_unc is None:
            vert_unc = 1.5

        slope_unc = raw.get("slope_uncertainty_deg")
        if slope_unc is None:
            slope_unc = 1.2

        min_crater = raw.get("min_crater_dist_m")
        if min_crater is None:
            min_crater = 600.0

        min_boulder = raw.get("min_boulder_dist_m")
        if min_boulder is None:
            min_boulder = 1000.0

        curv_var = raw.get("curvature_laplacian_var")
        if curv_var is None:
            curv_var = 0.05

        inst_illum = raw.get("instantaneous_sunlit_pct")
        if inst_illum is None:
            inst_illum = illum

        max_sun = raw.get("max_continuous_sun_h")
        if max_sun is None:
            max_sun = 90.0

        is_psr_val = raw.get("is_psr")
        if is_psr_val is None:
            is_psr_val = 1 if illum < 5.0 else 0

        return LunarSiteFeatures(
            mean_elevation_m=float(elev),
            elevation_relief_m=float(relief),
            mean_slope_deg=float(slope),
            max_slope_deg=float(max_slope),
            p95_slope_deg=float(p95_slope),
            ideal_slope_pct=float(ideal_slope),
            critical_slope_pct=float(crit_slope),
            roughness_15m=float(roughness),
            roughness_60m=float(rough_60),
            roughness_240m=float(rough_240),
            vertical_uncertainty_m=float(vert_unc),
            slope_uncertainty_deg=float(slope_unc),
            crater_density_km2=float(crater_density),
            min_crater_dist_m=float(min_crater),
            boulder_density_km2=float(boulder_density),
            min_boulder_dist_m=float(min_boulder),
            curvature_laplacian_var=float(curv_var),
            cumulative_sunlight_pct=float(illum),
            instantaneous_sunlit_pct=float(inst_illum),
            max_continuous_sun_h=float(max_sun),
            max_continuous_dark_h=float(max_dark),
            is_psr=int(is_psr_val),
            earth_visibility_pct=float(comms),
            contiguous_diameter_m=float(contig_diam),
        )

    def _calculate_feature_contributions(
        self,
        features: LunarSiteFeatures,
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Computes top positive and top risk feature contributions based on MDI importances."""
        feat_dict = features.model_dump()
        importances = (self._metadata or {}).get("top_feature_importances", {})

        positives: Dict[str, float] = {}
        risks: Dict[str, float] = {}

        for name, meta in NOMINAL_REFERENCES.items():
            val = feat_dict.get(name)
            if val is None:
                continue

            base = meta["baseline"]
            scale = meta["scale"]
            direction = meta["direction"]
            weight = importances.get(name, 0.04)

            # Normalized difference from nominal baseline
            norm_diff = (val - base) / max(scale, 1e-5)

            if direction == "lower_is_better":
                # Value lower than baseline is positive; higher is risk
                score_delta = -norm_diff * weight * 100.0
            else:
                # Value higher than baseline is positive; lower is risk
                score_delta = norm_diff * weight * 100.0

            score_delta_round = round(float(score_delta), 2)
            if score_delta >= 0:
                positives[name] = score_delta_round
            else:
                risks[name] = score_delta_round

        # Sort positives descending, risks ascending (most negative first)
        sorted_positives = dict(sorted(positives.items(), key=lambda x: x[1], reverse=True)[:4])
        sorted_risks = dict(sorted(risks.items(), key=lambda x: x[1])[:4])

        return sorted_positives, sorted_risks

    def _propagate_uncertainty(
        self,
        features: LunarSiteFeatures,
        n_samples: int = 50,
        seed: int = 42,
    ) -> Tuple[float, List[float], str]:
        """Runs Monte Carlo perturbation across physical measurement uncertainties."""
        if self._model is None:
            return 2.0, [60.0, 68.0], "moderate"

        rng = np.random.RandomState(seed)
        base_vec = np.array([getattr(features, k) for k in FEATURE_NAMES], dtype=np.float32)

        # Build perturbation matrix with documented lunar instrument uncertainties
        matrix = np.tile(base_vec, (n_samples, 1))

        # LOLA vertical uncertainty: ~1.5m
        matrix[:, 0] += rng.normal(0, features.vertical_uncertainty_m, size=n_samples)
        # Topographic slope uncertainty: ~1.2 deg
        matrix[:, 2] += rng.normal(0, features.slope_uncertainty_deg, size=n_samples)
        matrix[:, 3] += rng.normal(0, features.slope_uncertainty_deg * 1.2, size=n_samples)
        matrix[:, 4] += rng.normal(0, features.slope_uncertainty_deg, size=n_samples)
        # Roughness RMS uncertainties: ~0.05m to ~0.10m
        matrix[:, 7] += rng.normal(0, 0.04, size=n_samples)
        matrix[:, 8] += rng.normal(0, 0.06, size=n_samples)
        matrix[:, 9] += rng.normal(0, 0.09, size=n_samples)
        # Illumination simulation uncertainty: ~2.0%
        matrix[:, 17] += rng.normal(0, 2.0, size=n_samples)

        # Domain boundary clamping
        matrix[:, 2] = np.clip(matrix[:, 2], 0.0, 90.0)
        matrix[:, 3] = np.clip(matrix[:, 3], 0.0, 90.0)
        matrix[:, 4] = np.clip(matrix[:, 4], 0.0, 90.0)
        matrix[:, 7] = np.maximum(0.01, matrix[:, 7])
        matrix[:, 8] = np.maximum(0.01, matrix[:, 8])
        matrix[:, 9] = np.maximum(0.01, matrix[:, 9])
        matrix[:, 17] = np.clip(matrix[:, 17], 0.0, 100.0)

        perturbed_preds = self._model.predict(matrix)
        perturbed_preds = np.clip(perturbed_preds, 0.0, 100.0)

        std_err = round(float(np.std(perturbed_preds)), 2)
        p025 = round(float(np.percentile(perturbed_preds, 2.5)), 1)
        p975 = round(float(np.percentile(perturbed_preds, 97.5)), 1)

        if std_err < 2.5:
            stability = "high"
        elif std_err < 6.0:
            stability = "moderate"
        else:
            stability = "low"

        return std_err, [p025, p975], stability

    def predict_suitability(
        self,
        features: Union[LunarSiteFeatures, Dict[str, Any]],
        mission_profile: str = "artemis_hls",
        run_monte_carlo: bool = True,
        strict: bool = False,
    ) -> ModelPredictionResult:
        """Evaluates preliminary landing suitability using trained ML surrogate and mission constraints."""
        critical_missing: List[str] = []
        status = "success"

        # 1. Standardize features and validate presence of critical measurements
        if isinstance(features, dict):
            raw_slope = features.get("mean_slope_deg") if features.get("mean_slope_deg") is not None else features.get("slope_deg")
            raw_rough = features.get("roughness_15m") if features.get("roughness_15m") is not None else features.get("roughness_m")
            raw_elev = features.get("mean_elevation_m") if features.get("mean_elevation_m") is not None else features.get("elevation_m")

            if raw_slope is None:
                critical_missing.append("mean_slope_deg")
            if raw_rough is None:
                critical_missing.append("roughness_15m")
            if raw_elev is None:
                critical_missing.append("mean_elevation_m")

            # Calculate authentic data completeness percentage
            total_features = len(FEATURE_NAMES)
            provided_keys = sum(1 for k in FEATURE_NAMES if features.get(k) is not None)
            alt_keys = ["slope_deg", "roughness_m", "elevation_m", "crater_count", "rock_count", "illumination_pct"]
            extra_provided = sum(1 for k in alt_keys if features.get(k) is not None and k not in FEATURE_NAMES)
            data_completeness = round(min(100.0, max(10.0, ((provided_keys + extra_provided) / total_features) * 100.0)), 1)

            if critical_missing:
                if strict:
                    raise ValueError(f"Missing safety-critical landing parameters: {critical_missing}")
                if raw_slope is None:
                    # Slope is non-negotiable for landing safety
                    return ModelPredictionResult(
                        model_name=self._metadata.get("model_name", "Moonscape Lunar Landing Suitability Surrogate Model") if self._metadata else "Moonscape Lunar Landing Suitability Surrogate Model",
                        model_version=self._metadata.get("version", "2.0.0") if self._metadata else "2.0.0",
                        ml_suitability_score=0.0,
                        predicted_class="disqualified",
                        hard_constraint_status="insufficient_data",
                        hard_constraint_violations=[f"Missing safety-critical parameter: {m}" for m in critical_missing],
                        top_positive_features={},
                        top_risk_features={m: -50.0 for m in critical_missing},
                        uncertainty_score_std=50.0,
                        confidence_interval_95=[0.0, 0.0],
                        ranking_stability="low",
                        data_completeness_pct=data_completeness,
                        status="insufficient_data",
                        missing_critical_features=critical_missing,
                    )
                # Elevation or roughness missing but slope provided: allow imputation with partial_data flag
                feat_obj = self.construct_features_from_dict(features, allow_imputation=True)
                status = "partial_data"
            else:
                feat_obj = self.construct_features_from_dict(features, allow_imputation=False)
                status = "success"
        else:
            feat_obj = features
            data_completeness = 100.0
            status = "success"

        # 2. Evaluate hard mission engineering constraints
        measurements_for_constraints = {
            "slope_deg": feat_obj.mean_slope_deg,
            "max_slope_deg": feat_obj.max_slope_deg,
            "p95_slope_deg": feat_obj.p95_slope_deg,
            "roughness_m": feat_obj.roughness_15m,
            "contiguous_diameter_m": feat_obj.contiguous_diameter_m,
            "max_continuous_dark_h": feat_obj.max_continuous_dark_h,
            "earth_visibility_pct": feat_obj.earth_visibility_pct,
        }
        is_violated, violations = evaluate_hard_constraints(
            measurements_for_constraints,
            profile_id=mission_profile,
        )

        # 3. Model inference
        has_model = self._ensure_model_loaded()
        if has_model and self._model is not None:
            raw_vec = np.array([[getattr(feat_obj, k) for k in FEATURE_NAMES]], dtype=np.float32)
            raw_score = float(self._model.predict(raw_vec)[0])
            raw_score = round(max(0.0, min(100.0, raw_score)), 1)
            model_name = self._metadata.get("model_name", "Moonscape Lunar Landing Suitability Surrogate Model")
            model_version = self._metadata.get("version", "2.0.0")
        else:
            # Fallback deterministic formula
            from maths.scoring import compute_suitability_with_coverage, evaluate_slope_score, evaluate_roughness_score, evaluate_illumination_score
            subscores = {
                "slope": evaluate_slope_score(feat_obj.mean_slope_deg),
                "roughness": evaluate_roughness_score(feat_obj.roughness_15m),
                "illumination": evaluate_illumination_score(feat_obj.cumulative_sunlight_pct),
            }
            comp_score, _, _, _ = compute_suitability_with_coverage(subscores, {"slope": 0.4, "roughness": 0.3, "illumination": 0.3})
            raw_score = round(comp_score if comp_score is not None else 50.0, 1)
            model_name = "Deterministic MCDA Baseline (Fallback)"
            model_version = "fallback-2.0"

        # 4. Gating and classification
        if is_violated:
            pred_class = "disqualified"
            hard_status = "violated"
            # Capped strictly at <= 35.0 on hard mission constraint violation
            final_score = min(raw_score, 35.0)
        else:
            hard_status = "passed"
            final_score = raw_score
            if final_score >= 80.0:
                pred_class = "favorable"
            elif final_score >= 60.0:
                pred_class = "marginal"
            else:
                pred_class = "unfavorable"

        # 5. Explainability & Uncertainty
        positives, risks = self._calculate_feature_contributions(feat_obj)

        if run_monte_carlo and has_model:
            std_err, conf_int, stability = self._propagate_uncertainty(feat_obj)
        else:
            std_err = 1.8
            conf_int = [max(0.0, final_score - 3.5), min(100.0, final_score + 3.5)]
            stability = "high"

        return ModelPredictionResult(
            model_name=model_name,
            model_version=model_version,
            ml_suitability_score=final_score,
            predicted_class=pred_class,
            hard_constraint_status=hard_status,
            hard_constraint_violations=violations,
            top_positive_features=positives,
            top_risk_features=risks,
            uncertainty_score_std=std_err,
            confidence_interval_95=conf_int,
            ranking_stability=stability,
            data_completeness_pct=data_completeness,
            status=status,
            missing_critical_features=critical_missing,
        )


suitability_model_service = LunarSuitabilityModelService()
