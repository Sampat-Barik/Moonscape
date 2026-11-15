"""Service managing the NASA Artemis Lunar South Pole candidate landing sites catalog."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import settings
from app.core.constants import SCIENTIFIC_SAFETY_DISCLAIMER
from app.core.logging import logger
from app.schemas.site import (
    CandidateSite,
    SiteCompareResponse,
    SiteComparisonItem,
)
from app.services.ml.suitability_model_service import suitability_model_service
from maths.scoring import evaluate_hard_constraints


class SiteService:
    """Provides access, filtering, and comparative analysis of candidate landing sites."""

    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or settings.resolved_sites_path
        self._sites_cache: Dict[str, CandidateSite] = {}
        self._load_catalog()

    def _load_catalog(self) -> None:
        """Loads and validates candidate sites from JSON catalog."""
        if not self.data_path.exists():
            logger.warning("Candidate sites catalog file not found at %s", self.data_path)
            return

        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                for item in raw_data:
                    site = CandidateSite(**item)
                    self._sites_cache[site.site_id] = site
            logger.info("Successfully loaded %d candidate sites from catalog", len(self._sites_cache))
        except Exception as e:
            logger.error("Error loading sites catalog: %s", str(e))
            raise

    def get_all_sites(self) -> List[CandidateSite]:
        """Returns all registered candidate landing sites."""
        return list(self._sites_cache.values())

    def get_site_by_id(self, site_id: str) -> Optional[CandidateSite]:
        """Retrieves a specific site by its slug identifier."""
        return self._sites_cache.get(site_id)

    def count_sites(self) -> int:
        """Returns total count of registered candidate sites."""
        return len(self._sites_cache)

    def compare_sites(
        self,
        site_ids: List[str],
        custom_weights: Optional[Dict[str, float]] = None,
        mission_profile: str = "artemis_hls",
    ) -> SiteCompareResponse:
        """Performs a multi-criteria comparative evaluation among candidate sites."""
        weights = {
            "slope": 0.35,
            "illumination": 0.25,
            "communication": 0.20,
            "science": 0.20,
        }
        if custom_weights:
            weights.update(custom_weights)

        # Normalize weights to sum to 1.0
        total_w = sum(weights.values())
        if total_w > 0:
            weights = {k: v / total_w for k, v in weights.items()}

        compared_items: List[SiteComparisonItem] = []

        for sid in site_ids:
            site = self.get_site_by_id(sid)
            if not site:
                continue

            # Calculate individual criterion scores (0 to 100)
            # Slope score: 0 deg -> 100, 15 deg -> 0
            if site.mean_slope_deg is not None:
                slope_score = max(0.0, min(100.0, 100.0 * (1.0 - (site.mean_slope_deg / 15.0))))
            else:
                slope_score = 50.0

            # Illumination score: direct %
            illum_score = site.illumination_pct if site.illumination_pct is not None else 50.0

            # Earth visibility: direct %
            comms_score = site.earth_visibility_pct if site.earth_visibility_pct is not None else 50.0

            # Science priority: high -> 95, medium -> 75, low -> 50
            priority_map = {"high": 95.0, "medium": 75.0, "low": 50.0}
            science_score = priority_map.get(site.priority.lower(), 70.0)

            # Composite weighted suitability score
            composite = (
                weights["slope"] * slope_score
                + weights["illumination"] * illum_score
                + weights["communication"] * comms_score
                + weights["science"] * science_score
            )
            composite = round(composite, 2)

            strengths: List[str] = []
            vulnerabilities: List[str] = []

            if site.mean_slope_deg is not None and site.mean_slope_deg <= 5.0:
                strengths.append(f"Benign topography (average slope {site.mean_slope_deg}°)")
            elif site.mean_slope_deg is not None and site.mean_slope_deg > 8.0:
                vulnerabilities.append(f"Elevated slope risk (average slope {site.mean_slope_deg}°)")

            if site.illumination_pct is not None and site.illumination_pct >= 75.0:
                strengths.append(f"High solar power potential ({site.illumination_pct}% illumination)")
            elif site.illumination_pct is not None and site.illumination_pct < 65.0:
                vulnerabilities.append(f"Limited solar illumination ({site.illumination_pct}%)")

            if site.earth_visibility_pct is not None and site.earth_visibility_pct >= 85.0:
                strengths.append(f"Direct Earth line-of-sight communication ({site.earth_visibility_pct}%)")
            elif site.earth_visibility_pct is not None and site.earth_visibility_pct < 70.0:
                vulnerabilities.append("Intermittent direct-to-Earth communication coverage")

            # Check hard mission engineering constraints and ML predictions
            measurements = {
                "slope_deg": site.mean_slope_deg,
                "elevation_m": site.elevation_m,
                "illumination_pct": site.illumination_pct,
                "earth_visibility_pct": site.earth_visibility_pct,
            }
            is_violated, violations = evaluate_hard_constraints(
                measurements,
                profile_id=mission_profile,
            )
            for v in violations:
                vulnerabilities.append(f"Hard constraint violation: {v}")

            try:
                ml_pred = suitability_model_service.predict_suitability(
                    measurements,
                    mission_profile=mission_profile,
                    run_monte_carlo=True,
                )
                ml_score = ml_pred.ml_suitability_score
                unc_std = ml_pred.uncertainty_score_std
                conf_int = ml_pred.confidence_interval_95
            except Exception:
                ml_score = None
                unc_std = None
                conf_int = None

            compared_items.append(
                SiteComparisonItem(
                    site_id=site.site_id,
                    name=site.name,
                    latitude=site.latitude,
                    longitude=site.longitude,
                    elevation_m=site.elevation_m,
                    mean_slope_deg=site.mean_slope_deg,
                    illumination_pct=site.illumination_pct,
                    earth_visibility_pct=site.earth_visibility_pct,
                    suitability_score=composite,
                    safety_rank=1,  # Will sort and rank below
                    key_strengths=strengths,
                    key_vulnerabilities=vulnerabilities,
                    ml_model_score=ml_score,
                    hard_constraint_status="violated" if is_violated else "passed",
                    uncertainty_score_std=unc_std,
                    confidence_interval_95=conf_int,
                )
            )

        # Sort descending by composite score (unviolated sites prioritized)
        compared_items.sort(
            key=lambda x: (x.hard_constraint_status == "passed", x.suitability_score),
            reverse=True,
        )
        for idx, item in enumerate(compared_items, start=1):
            item.safety_rank = idx

        top_site = compared_items[0].site_id if compared_items else ""
        top_name = compared_items[0].name if compared_items else "None"

        summary = (
            f"Comparative analysis evaluates {len(compared_items)} candidates for profile '{mission_profile}'. "
            f"'{top_name}' ranks highest with a composite score of "
            f"{compared_items[0].suitability_score if compared_items else 0.0}/100, "
            f"demonstrating the optimal balance between topographic landing safety, "
            f"solar energy availability, and mission communication constraints."
        )

        return SiteCompareResponse(
            compared_sites=compared_items,
            top_recommended_site_id=top_site,
            tradeoff_summary=summary,
            criteria_weights=weights,
            mission_profile=mission_profile,
            disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
        )


site_service = SiteService()
