"""In-memory persistence and retrieval for landing zone analysis results."""

import threading
from typing import Dict, List, Optional

from app.core.constants import SCIENTIFIC_SAFETY_DISCLAIMER
from app.schemas.analysis import (
    AnalysisRunResponse,
    IlluminationSummary,
    SlopeDistribution,
    TopographicStats,
)
from app.schemas.scoring import FactorSubscore, ScoreResponse


class AnalysisStore:
    """Thread-safe store for recent spatial and terrain analysis evaluations."""

    def __init__(self, max_capacity: int = 200) -> None:
        self._max_capacity = max_capacity
        self._lock = threading.Lock()
        self._analyses: Dict[str, AnalysisRunResponse] = {}
        self._seed_default_analyses()

    def _seed_default_analyses(self) -> None:
        """Seeds initial reference analyses such as analysis_001 for out-of-the-box evaluation."""
        subscores = [
            FactorSubscore(
                criterion="Topographic Slope",
                raw_measurement=6.8,
                unit="degrees",
                normalized_subscore=86.4,
                weight=0.30,
                weighted_contribution=25.92,
                status="available",
                preference_direction="lower_is_better",
                description="Critical lander tipping stability metric. Slopes below 5 deg are ideal.",
            ),
            FactorSubscore(
                criterion="Terrain Roughness",
                raw_measurement=0.12,
                unit="meters RMS",
                normalized_subscore=95.2,
                weight=0.20,
                weighted_contribution=19.04,
                status="available",
                preference_direction="lower_is_better",
                description="Micro-topographic relief indicating boulder-field roughness.",
            ),
            FactorSubscore(
                criterion="Solar Illumination",
                raw_measurement=86.4,
                unit="percent",
                normalized_subscore=86.4,
                weight=0.20,
                weighted_contribution=17.28,
                status="available",
                preference_direction="higher_is_better",
                description="Solar energy generation potential and thermal environment stability.",
            ),
            FactorSubscore(
                criterion="Surface Elevation",
                raw_measurement=-120.0,
                unit="meters",
                normalized_subscore=43.11,
                weight=0.10,
                weighted_contribution=4.31,
                status="available",
                preference_direction="higher_is_better",
                description="Elevation above lunar reference datum (1737.4 km sphere).",
            ),
        ]

        suitability = ScoreResponse(
            site_id="shackleton_connecting_ridge",
            overall_suitability_score=83.25,
            suitability_category="Higher preliminary suitability",
            score_coverage_pct=80.0,
            missing_factors=["Crater Hazards", "Rock / Boulder Hazards"],
            evaluated_factors_count=4,
            total_factors_count=6,
            subscores=subscores,
            scoring_methodology="Transparent Multi-Criteria Decision Analysis (MCDA) with missing factor non-redistribution (Criteria v2.0-phase6).",
            key_advantages=[
                "High cumulative solar illumination (86.4%) supports long-duration surface power",
                "Favorable topographic slope profile (6.8 deg) within nominal landing envelope",
            ],
            critical_concerns=[],
            warnings=[
                "MISSING DATA NOTICE: 20.0% of criteria weight could not be evaluated due to unprovided crater/rock hazard inputs.",
            ],
            criteria_version="2.0-phase6",
            disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
        )

        illum = IlluminationSummary(
            status="available",
            solar_elevation_deg=1.15,
            solar_azimuth_deg=218.4,
            instantaneous_sunlit_fraction_pct=100.0,
            cumulative_illumination_pct=86.4,
            time_period_evaluated="LRO LOLA multi-year draconic precession baseline (Barker et al. 2021)",
            is_permanently_shadowed_region=False,
            estimated_surface_temp_k=185.0,
            sunlight_continuous_hours_max=612.0,
            methodology="Analytical solar ephemeris combined with LRO LOLA precession cumulative ground truth.",
            source_attribution="NASA LRO LOLA / Diviner / JPL DE421",
            scientific_caveats=[
                "Surface temperature is a thermal measurement, not a direct optical sunlight percentage.",
            ],
        )

        analysis_001 = AnalysisRunResponse(
            analysis_id="analysis_001",
            center_lat=-89.44,
            center_lon=222.50,
            radius_meters=1000.0,
            total_samples=125600,
            valid_samples=125600,
            nodata_samples=0,
            elevation=TopographicStats(
                min_value=-210.0,
                max_value=15.0,
                mean_value=-120.0,
                median_value=-118.0,
                std_dev=35.0,
                variation=225.0,
                units="meters",
            ),
            slope=TopographicStats(
                min_value=0.8,
                max_value=14.5,
                mean_value=6.8,
                median_value=5.9,
                std_dev=2.4,
                units="degrees",
            ),
            slope_distribution=SlopeDistribution(
                ideal_pct=62.5,
                acceptable_pct=28.5,
                marginal_pct=7.2,
                critical_hazardous_pct=1.8,
            ),
            roughness_mean_m=0.12,
            roughness_max_m=0.38,
            roughness_baseline_m=15.0,
            roughness_method="Root-Mean-Square (RMS) Residual Height Deviation",
            slope_method="Horn 1981 Finite-Difference Slope Operator",
            safe_touchdown_fraction_pct=91.0,
            preliminary_feasibility="favorable",
            dataset_metadata={
                "source_tier": "Tier 2 (High-Resolution 5m Candidate Region)",
                "dataset_name": "NASA PGDA Product 78 (LOLA 5m/pixel Candidate Site DEM)",
                "product_id": "Site01_final_adj_5mpp_surf",
                "spatial_resolution_m": 5.0,
                "crs": "ESRI:104903 (Lunar South Polar Stereographic)",
                "is_measured_data": True,
            },
            disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
            illumination=illum,
            suitability=suitability,
        )

        self._analyses["analysis_001"] = analysis_001

    def save(self, analysis: AnalysisRunResponse) -> None:
        """Stores an analysis result, evicting the oldest if capacity is exceeded."""
        with self._lock:
            if len(self._analyses) >= self._max_capacity and analysis.analysis_id not in self._analyses:
                oldest_key = next(iter(self._analyses.keys()))
                # Keep analysis_001 seeded
                if oldest_key == "analysis_001" and len(self._analyses) > 1:
                    keys = list(self._analyses.keys())
                    oldest_key = keys[1]
                del self._analyses[oldest_key]
            self._analyses[analysis.analysis_id] = analysis

    def get(self, analysis_id: str) -> Optional[AnalysisRunResponse]:
        """Retrieves an analysis by its ID."""
        with self._lock:
            return self._analyses.get(analysis_id)

    def has(self, analysis_id: str) -> bool:
        """Checks if an analysis ID exists in the store."""
        with self._lock:
            return analysis_id in self._analyses

    def list_ids(self) -> List[str]:
        """Lists all stored analysis IDs."""
        with self._lock:
            return list(self._analyses.keys())


analysis_store = AnalysisStore()
