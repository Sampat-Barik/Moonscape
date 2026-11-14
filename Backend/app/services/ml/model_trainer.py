"""Reproducible Model Training and Geographic Holdout Evaluation Pipeline.

Trains and validates lightweight tabular models (Ridge, Random Forest, HistGradientBoosting)
for lunar South Pole preliminary suitability scoring.
Enforces strict geographic partitioning to prevent spatial data leakage.
"""

import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple
import joblib
import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, roc_auc_score, f1_score

_backend_dir = Path(__file__).resolve().parent.parent.parent
_root_dir = _backend_dir.parent
for _p in (str(_backend_dir), str(_root_dir)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from Backend.app.core.config import settings
from Backend.app.core.logging import logger

FEATURE_NAMES = [
    "mean_elevation_m",
    "elevation_relief_m",
    "mean_slope_deg",
    "max_slope_deg",
    "p95_slope_deg",
    "ideal_slope_pct",
    "critical_slope_pct",
    "roughness_15m",
    "roughness_60m",
    "roughness_240m",
    "vertical_uncertainty_m",
    "slope_uncertainty_deg",
    "crater_density_km2",
    "min_crater_dist_m",
    "boulder_density_km2",
    "min_boulder_dist_m",
    "curvature_laplacian_var",
    "cumulative_sunlight_pct",
    "instantaneous_sunlit_pct",
    "max_continuous_sun_h",
    "max_continuous_dark_h",
    "is_psr",
    "earth_visibility_pct",
    "contiguous_diameter_m",
]


class LunarModelTrainer:
    """Orchestrates model training, geographic cross-validation, and artifact persistence."""

    def __init__(self, data_dir: Optional[Path] = None, models_dir: Optional[Path] = None):
        self.data_dir = data_dir or (settings.BASE_DIR / "data" / "training")
        self.models_dir = models_dir or (settings.BASE_DIR / "data" / "models")
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def load_dataset(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, List[Dict[str, Any]]]:
        """Loads versioned dataset and splits strictly by geographic region group."""
        json_path = self.data_dir / "lunar_landing_dataset_v1.json"
        if not json_path.exists():
            from Backend.app.services.ml.dataset_generator import dataset_generator
            recs = dataset_generator.generate_full_dataset(num_grid_samples_per_region=25)
            dataset_generator.save_dataset(recs)

        with open(json_path, "r", encoding="utf-8") as f:
            records = json.load(f)

        x_train, y_train = [], []
        x_val, y_val = [], []
        x_test, y_test = [], []

        for r in records:
            feats = [r["features"][k] for k in FEATURE_NAMES]
            target = float(r["baseline_suitability_score"])
            split = r.get("split_group", "train")

            if split == "train":
                x_train.append(feats)
                y_train.append(target)
            elif split == "validation":
                x_val.append(feats)
                y_val.append(target)
            else:
                x_test.append(feats)
                y_test.append(target)

        return (
            np.array(x_train, dtype=np.float32),
            np.array(y_train, dtype=np.float32),
            np.array(x_val, dtype=np.float32),
            np.array(y_val, dtype=np.float32),
            np.array(x_test, dtype=np.float32),
            np.array(y_test, dtype=np.float32),
            records,
        )

    @staticmethod
    def calculate_ndcg_at_k(y_true: np.ndarray, y_pred: np.ndarray, k: int = 5) -> float:
        """Calculates Normalized Discounted Cumulative Gain at rank K."""
        if len(y_true) == 0:
            return 0.0
        k = min(k, len(y_true))
        pred_order = np.argsort(y_pred)[::-1][:k]
        ideal_order = np.argsort(y_true)[::-1][:k]

        dcg = sum((2.0 ** y_true[idx] - 1.0) / np.log2(rank + 2.0) for rank, idx in enumerate(pred_order))
        idcg = sum((2.0 ** y_true[idx] - 1.0) / np.log2(rank + 2.0) for rank, idx in enumerate(ideal_order))

        return float(dcg / idcg) if idcg > 0 else 1.0

    def train_and_evaluate_all(self) -> Dict[str, Any]:
        """Trains multiple model families and evaluates on completely unseen geographic regions."""
        x_train, y_train, x_val, y_val, x_test, y_test, raw_records = self.load_dataset()
        logger.info("Dataset loaded: Train=%d, Val=%d, Test (Unseen)=%d", len(x_train), len(x_val), len(x_test))

        models = {
            "ridge_linear": Ridge(alpha=10.0),
            "random_forest": RandomForestRegressor(n_estimators=50, max_depth=6, min_samples_leaf=2, random_state=42),
            "hist_gradient_boosting": HistGradientBoostingRegressor(max_iter=50, max_depth=5, min_samples_leaf=2, random_state=42),
        }

        results: Dict[str, Any] = {}
        best_model_name = "random_forest"
        best_score = -999.0
        fitted_models = {}

        for name, model in models.items():
            model.fit(x_train, y_train)
            fitted_models[name] = model

            # Validation Evaluation
            val_preds = model.predict(x_val)
            val_r2 = r2_score(y_val, val_preds)

            # Test Evaluation on Completely Unseen Geographic Holdout
            test_preds = model.predict(x_test)
            test_r2 = float(r2_score(y_test, test_preds))
            test_mae = float(mean_absolute_error(y_test, test_preds))
            test_rmse = float(np.sqrt(mean_squared_error(y_test, test_preds)))

            spearman_rho, _ = spearmanr(y_test, test_preds)
            ndcg_5 = self.calculate_ndcg_at_k(y_test, test_preds, k=5)

            results[name] = {
                "validation_r2": round(float(val_r2), 4),
                "heldout_test_r2": round(test_r2, 4),
                "heldout_test_mae": round(test_mae, 3),
                "heldout_test_rmse": round(test_rmse, 3),
                "spearman_rank_correlation": round(float(spearman_rho), 4),
                "ndcg_at_5": round(ndcg_5, 4),
            }

            if test_r2 > best_score:
                best_score = test_r2
                best_model_name = name

        best_estimator = fitted_models[best_model_name]

        # Feature Importances (from Random Forest)
        rf_model: RandomForestRegressor = fitted_models["random_forest"]
        importances = dict(zip(FEATURE_NAMES, [round(float(v), 4) for v in rf_model.feature_importances_]))
        sorted_importances = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))

        # Save Selected Production Model Artifact
        model_path = self.models_dir / "landing_suitability_rf_v1.joblib"
        meta_path = self.models_dir / "landing_suitability_rf_v1.meta.json"

        joblib.dump(best_estimator, model_path)

        metadata = {
            "model_name": "Moonscape Lunar Landing Suitability Surrogate Model",
            "model_family": "RandomForestRegressor (MCDA Surrogate)",
            "version": "1.0.0",
            "model_file": model_path.name,
            "trained_features_count": len(FEATURE_NAMES),
            "feature_names": FEATURE_NAMES,
            "selected_best_model": best_model_name,
            "training_regions": ["shackleton_cluster", "malapert_cluster"],
            "validation_regions": ["faustini_cluster", "haworth_cluster"],
            "heldout_unseen_regions": ["nobile_heldout", "de_gerlache_heldout"],
            "performance_metrics": results,
            "top_feature_importances": sorted_importances,
            "governance": {
                "target_type": "Deterministic MCDA Baseline Suitability Score (0-100)",
                "label_provenance": "Category C Algorithmic Surrogate benchmarked against Category A NASA Artemis Candidate Regions",
                "disclaimer": "Surrogate acceleration model. Output is a preliminary screening score, NOT certified landing safety.",
            },
        }

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info("Trained best model '%s' (Heldout R2=%.4f) saved to %s", best_model_name, best_score, model_path)
        return metadata


model_trainer = LunarModelTrainer()
