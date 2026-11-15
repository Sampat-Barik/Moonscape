"""Multi-criteria decision analysis (MCDA) and mathematical utility scoring functions.

Contains normalization functions, penalty curves, and transparent weighted scoring
for lunar landing site preliminary suitability screening.
"""

from typing import Any, Dict, List, Optional, Tuple


# Configurable Lunar Landing Mission Profiles
MISSION_PROFILES: Dict[str, Dict[str, Any]] = {
    "artemis_hls": {
        "id": "artemis_hls",
        "name": "Artemis Human Landing System (HLS)",
        "description": "Crewed lunar polar landing with strict slope stability and footprint margins.",
        "max_slope_deg": 10.0,
        "max_p95_slope_deg": 8.0,
        "max_roughness_m": 0.40,
        "min_contiguous_diameter_m": 100.0,
        "min_cumulative_sunlight_pct": 50.0,
        "max_continuous_darkness_hours": 72.0,
        "min_earth_visibility_pct": 45.0,
        "weights": {
            "slope": 0.35,
            "roughness": 0.20,
            "illumination": 0.20,
            "crater_hazard": 0.10,
            "rock_hazard": 0.05,
            "elevation": 0.10,
        },
    },
    "clps_cargo": {
        "id": "clps_cargo",
        "name": "Commercial Lunar Payload Services (CLPS Cargo)",
        "description": "Uncrewed medium robotic lander payload delivery (e.g. Nova-C, Blue Ghost).",
        "max_slope_deg": 12.0,
        "max_p95_slope_deg": 10.0,
        "max_roughness_m": 0.60,
        "min_contiguous_diameter_m": 40.0,
        "min_cumulative_sunlight_pct": 40.0,
        "max_continuous_darkness_hours": 120.0,
        "min_earth_visibility_pct": 30.0,
        "weights": {
            "slope": 0.30,
            "roughness": 0.20,
            "illumination": 0.20,
            "crater_hazard": 0.15,
            "rock_hazard": 0.10,
            "elevation": 0.05,
        },
    },
    "polar_rover": {
        "id": "polar_rover",
        "name": "Polar Volatiles Scout / Rover",
        "description": "Traversability-focused robotic mission targeting volatile concentration zones (VIPER-class).",
        "max_slope_deg": 8.0,
        "max_p95_slope_deg": 6.0,
        "max_roughness_m": 0.35,
        "min_contiguous_diameter_m": 40.0,
        "min_cumulative_sunlight_pct": 35.0,
        "max_continuous_darkness_hours": 150.0,
        "min_earth_visibility_pct": 60.0,
        "weights": {
            "slope": 0.35,
            "roughness": 0.25,
            "illumination": 0.15,
            "crater_hazard": 0.10,
            "rock_hazard": 0.10,
            "elevation": 0.05,
        },
    },
    "base_camp": {
        "id": "base_camp",
        "name": "Permanent Lunar Base Camp Staging",
        "description": "Long-duration surface habitat and power station requiring peak solar harvesting.",
        "max_slope_deg": 8.0,
        "max_p95_slope_deg": 6.0,
        "max_roughness_m": 0.30,
        "min_contiguous_diameter_m": 150.0,
        "min_cumulative_sunlight_pct": 70.0,
        "max_continuous_darkness_hours": 48.0,
        "min_earth_visibility_pct": 70.0,
        "weights": {
            "slope": 0.25,
            "roughness": 0.15,
            "illumination": 0.30,
            "crater_hazard": 0.10,
            "rock_hazard": 0.05,
            "elevation": 0.15,
        },
    },
}


def evaluate_hard_constraints(
    measurements: Dict[str, Any],
    profile_id: str = "artemis_hls",
    custom_constraints: Optional[Dict[str, float]] = None,
) -> Tuple[bool, List[str]]:
    """Evaluates whether candidate site violates hard mission engineering constraints.

    Crucial Planetary Rule:
        Hard exclusions precede soft scoring. A site that violates an engineering limit
        is strictly marked as disqualified and must not rank highly due to strong sunlight.

    Returns:
        (is_violated: bool, violations: List[str])
    """
    profile = MISSION_PROFILES.get(profile_id, MISSION_PROFILES["artemis_hls"])
    limits = dict(profile)
    if custom_constraints:
        limits.update(custom_constraints)

    violations: List[str] = []

    # 1. Slope Check (Safety-Critical)
    slope = measurements.get("slope_deg")
    max_slope = measurements.get("max_slope_deg")
    p95_slope = measurements.get("p95_slope_deg")

    if slope is None and max_slope is None:
        violations.append("Missing essential topographic slope data; touchdown safety cannot be evaluated.")
    else:
        # Check against absolute physical tip-over limit (15.0 deg)
        if slope is not None and slope > 15.0:
            violations.append(f"Mean slope ({slope:.1f}°) exceeds universal Apollo/Artemis tip-over limit (15.0°).")
        if max_slope is not None and max_slope > limits.get("max_slope_deg", 12.0):
            violations.append(f"Peak localized slope ({max_slope:.1f}°) exceeds mission constraint ({limits['max_slope_deg']:.1f}°).")
        if p95_slope is not None and p95_slope > limits.get("max_p95_slope_deg", 10.0):
            violations.append(f"95th percentile slope ({p95_slope:.1f}°) exceeds mission constraint ({limits['max_p95_slope_deg']:.1f}°).")

    # 2. Contiguous Landing Footprint
    diameter = measurements.get("contiguous_diameter_m")
    req_diam = limits.get("min_contiguous_diameter_m", 40.0)
    if diameter is not None and diameter < req_diam:
        violations.append(f"Contiguous safe landing diameter ({diameter:.1f}m) is smaller than required mission footprint ({req_diam:.1f}m).")

    # 3. Surface Roughness / Undercarriage Clearance
    roughness = measurements.get("roughness_m")
    max_rough = limits.get("max_roughness_m", 0.60)
    if roughness is not None and roughness > max_rough:
        violations.append(f"Surface roughness ({roughness:.2f}m) exceeds lander undercarriage clearance margin ({max_rough:.2f}m).")

    # 4. Long-Duration Darkness (Power / Battery Sizing)
    max_dark_h = measurements.get("max_continuous_dark_h")
    limit_dark = limits.get("max_continuous_darkness_hours")
    if max_dark_h is not None and limit_dark is not None and max_dark_h > limit_dark:
        violations.append(f"Maximum continuous darkness ({max_dark_h:.1f}h) exceeds battery survival limit ({limit_dark:.1f}h).")

    # 5. Direct Earth Visibility (Communication Margin)
    comms = measurements.get("earth_visibility_pct")
    min_comm = limits.get("min_earth_visibility_pct")
    if comms is not None and min_comm is not None and comms < min_comm:
        violations.append(f"Direct Earth visibility ({comms:.1f}%) is below minimum mission communication requirement ({min_comm:.1f}%).")

    is_violated = len(violations) > 0
    return is_violated, violations


def piecewise_linear_penalty(
    value: float,
    ideal_max: float,
    nominal_max: float,
    critical_max: float,
) -> float:
    """Computes a normalized piece-wise linear penalty score (0.0 to 100.0).

    Behavior:
        - value <= ideal_max: 100.0 (Optimal)
        - ideal_max < value <= nominal_max: Drops linearly from 100.0 down to 70.0 (Nominal)
        - nominal_max < value <= critical_max: Drops linearly from 70.0 down to 0.0 (Marginal)
        - value > critical_max: 0.0 (Critical failure / Tip-over risk)
    """
    if value <= ideal_max:
        return 100.0
    elif value <= nominal_max:
        ratio = (value - ideal_max) / (nominal_max - ideal_max)
        return round(100.0 - (ratio * 30.0), 2)
    elif value <= critical_max:
        ratio = (value - nominal_max) / (critical_max - nominal_max)
        return round(70.0 - (ratio * 70.0), 2)
    else:
        return 0.0


def evaluate_slope_score(slope_deg: float) -> float:
    """Evaluates topographic slope against lander safety envelopes (Bennett 2020, Apollo LM).

    - <= 5°: 100.0 (Ideal flat terrain)
    - 5° - 10°: 100.0 -> 70.0 (Nominal lander stability)
    - 10° - 15°: 70.0 -> 0.0 (Marginal; approaches tip-over limit)
    - > 15°: 0.0 (Critical dynamic tip-over / strut buckling threshold)
    """
    return piecewise_linear_penalty(
        value=slope_deg,
        ideal_max=5.0,
        nominal_max=10.0,
        critical_max=15.0,
    )


def evaluate_roughness_score(roughness_m: float) -> float:
    """Evaluates surface RMS roughness against lander footpad and engine clearance limits.

    - <= 0.25m: 100.0
    - 0.25m - 0.50m: 100.0 -> 70.0
    - 0.50m - 1.20m: 70.0 -> 0.0
    - > 1.20m: 0.0
    """
    if roughness_m <= 0.25:
        return 100.0
    elif roughness_m <= 0.50:
        ratio = (roughness_m - 0.25) / 0.25
        return round(100.0 - (ratio * 30.0), 2)
    elif roughness_m <= 1.20:
        ratio = (roughness_m - 0.50) / 0.70
        return round(70.0 - (ratio * 70.0), 2)
    else:
        return 0.0


def evaluate_illumination_score(illumination_pct: float) -> float:
    """Evaluates solar illumination percentage for surface power harvesting and thermal stability.

    - >= 80%: 100.0
    - 60% - 80%: 70.0 -> 100.0
    - 40% - 60%: 30.0 -> 70.0
    - < 40%: 0.0 -> 30.0
    """
    pct = max(0.0, min(100.0, illumination_pct))
    if pct >= 80.0:
        return 100.0
    elif pct >= 60.0:
        ratio = (pct - 60.0) / 20.0
        return round(70.0 + (ratio * 30.0), 2)
    elif pct >= 40.0:
        ratio = (pct - 40.0) / 20.0
        return round(30.0 + (ratio * 40.0), 2)
    else:
        return round((pct / 40.0) * 30.0, 2)


def evaluate_crater_hazard_score(crater_count: float) -> float:
    """Evaluates crater hazard density/count within landing ellipse.

    - 0 craters: 100.0
    - 1 crater: 85.0
    - 2 craters: 70.0
    - 3 - 5 craters: 70.0 -> 25.0
    - > 5 craters: 10.0
    """
    c = max(0.0, crater_count)
    if c == 0:
        return 100.0
    elif c <= 1:
        return 85.0
    elif c <= 2:
        return 70.0
    elif c <= 5:
        ratio = (c - 2.0) / 3.0
        return round(70.0 - (ratio * 45.0), 2)
    else:
        return 10.0


def evaluate_rock_hazard_score(rock_count: float) -> float:
    """Evaluates boulder/rock obstacle count within touchdown footprint.

    - 0 boulders: 100.0
    - 1 boulder: 80.0
    - 2 boulders: 65.0
    - 3 - 5 boulders: 65.0 -> 20.0
    - > 5 boulders: 5.0
    """
    r = max(0.0, rock_count)
    if r == 0:
        return 100.0
    elif r <= 1:
        return 80.0
    elif r <= 2:
        return 65.0
    elif r <= 5:
        ratio = (r - 2.0) / 3.0
        return round(65.0 - (ratio * 45.0), 2)
    else:
        return 5.0


def evaluate_elevation_score(elevation_m: float) -> float:
    """Evaluates elevation relative to 1737.4 km lunar sphere.

    Elevated highland massifs (+1000m to +2000m) afford superior horizon visibility
    and reduced descent delta-V compared to cryogenic basin depressions (<-2000m).
    """
    if elevation_m >= 1000.0:
        return 100.0
    elif elevation_m >= 0.0:
        ratio = elevation_m / 1000.0
        return round(80.0 + (ratio * 20.0), 2)
    elif elevation_m >= -1500.0:
        ratio = (elevation_m + 1500.0) / 1500.0
        return round(50.0 + (ratio * 30.0), 2)
    elif elevation_m >= -2500.0:
        ratio = (elevation_m + 2500.0) / 1000.0
        return round(20.0 + (ratio * 30.0), 2)
    else:
        return 10.0


def weighted_composite_score(
    subscores: Dict[str, float],
    weights: Dict[str, float],
) -> float:
    """Computes a normalized weighted composite score (0.0 to 100.0)."""
    total_weight = sum(weights.values())
    if total_weight <= 0:
        return 0.0

    composite = sum(subscores.get(k, 0.0) * (w / total_weight) for k, w in weights.items())
    return round(float(composite), 2)


def compute_suitability_with_coverage(
    factor_subscores: Dict[str, Optional[float]],
    factor_weights: Dict[str, float],
    min_coverage_threshold: float = 0.50,
) -> Tuple[Optional[float], float, List[str], Dict[str, float]]:
    """Calculates composite suitability score without fabricating missing data or silently redistributing weights.

    Args:
        factor_subscores: Dict of factor name -> normalized subscore (or None if measurement is missing)
        factor_weights: Dict of factor name -> configured weight (should sum to ~1.0)
        min_coverage_threshold: Minimum fraction of total weight required to compute a valid score (default 50%)

    Returns:
        (composite_score, score_coverage_fraction, missing_factors_list, weighted_contributions)
    """
    total_config_weight = sum(factor_weights.values())
    if total_config_weight <= 0.0:
        return None, 0.0, list(factor_subscores.keys()), {}

    # Normalize weights so they sum to 1.0 relative to total configured weight
    normalized_weights = {k: v / total_config_weight for k, v in factor_weights.items()}

    available_weight = 0.0
    weighted_sum = 0.0
    missing_factors: List[str] = []
    contributions: Dict[str, float] = {}

    for factor, weight in normalized_weights.items():
        score = factor_subscores.get(factor)
        if score is not None:
            available_weight += weight
            contrib = round(score * weight, 3)
            contributions[factor] = contrib
            weighted_sum += contrib
        else:
            missing_factors.append(factor)
            contributions[factor] = 0.0

    score_coverage = round(available_weight, 3)

    # If available factors cover less than the threshold, or if no factors are available:
    if score_coverage < min_coverage_threshold or available_weight == 0.0:
        return None, score_coverage, missing_factors, contributions

    # Composite score scaled across available coverage
    scaled_composite = round(weighted_sum / available_weight, 2)
    return scaled_composite, score_coverage, missing_factors, contributions
