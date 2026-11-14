"""Multi-criteria decision analysis (MCDA) and mathematical utility scoring functions."""

from typing import Dict


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
    """Evaluates topographic slope against Apollo/Artemis lander safety envelopes.

    <= 5°: 100.0
    5° - 10°: 100.0 -> 70.0
    10° - 15°: 70.0 -> 0.0
    > 15°: 0.0 (Dynamic tip-over threshold)
    """
    return piecewise_linear_penalty(
        value=slope_deg,
        ideal_max=5.0,
        nominal_max=10.0,
        critical_max=15.0,
    )


def evaluate_roughness_score(roughness_m: float) -> float:
    """Evaluates surface RMS roughness against lander footpad and engine clearance limits.

    <= 0.3m: 100.0
    0.3m - 0.5m: 100.0 -> 75.0
    0.5m - 1.5m: 75.0 -> 0.0
    > 1.5m: 0.0
    """
    if roughness_m <= 0.3:
        return 100.0
    elif roughness_m <= 0.5:
        ratio = (roughness_m - 0.3) / 0.2
        return round(100.0 - (ratio * 25.0), 2)
    elif roughness_m <= 1.5:
        ratio = (roughness_m - 0.5) / 1.0
        return round(75.0 - (ratio * 75.0), 2)
    else:
        return 0.0


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
