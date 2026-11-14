"""Maths package — Scientific computing, geodetic transformations, and numerical algorithms for Moonscape."""

from maths.geodesy import (
    latlon_to_polar_stereo,
    polar_stereo_to_latlon,
    haversine_lunar_distance,
    euclidean_distance_2d,
)
from maths.topography import (
    horn_slope_and_aspect,
    rms_surface_roughness,
    calculate_multi_baseline_roughness,
    slope_distribution_breakdown,
)
from maths.curvature import (
    laplacian_curvature,
    detect_crater_basins,
)
from maths.scoring import (
    piecewise_linear_penalty,
    evaluate_slope_score,
    evaluate_roughness_score,
    evaluate_illumination_score,
    evaluate_crater_hazard_score,
    evaluate_rock_hazard_score,
    evaluate_elevation_score,
    weighted_composite_score,
    compute_suitability_with_coverage,
    evaluate_hard_constraints,
    MISSION_PROFILES,
)
from maths.illumination_geometry import (
    calculate_solar_subsolar_coordinates,
    calculate_solar_elevation_and_azimuth,
    calculate_topographic_horizon_angle,
    calculate_sun_visibility_fraction,
    estimate_surface_temperature_kelvin,
    parse_utc_timestamp,
)

__all__ = [
    "latlon_to_polar_stereo",
    "polar_stereo_to_latlon",
    "haversine_lunar_distance",
    "euclidean_distance_2d",
    "horn_slope_and_aspect",
    "rms_surface_roughness",
    "calculate_multi_baseline_roughness",
    "slope_distribution_breakdown",
    "laplacian_curvature",
    "detect_crater_basins",
    "piecewise_linear_penalty",
    "evaluate_slope_score",
    "evaluate_roughness_score",
    "evaluate_illumination_score",
    "evaluate_crater_hazard_score",
    "evaluate_rock_hazard_score",
    "evaluate_elevation_score",
    "weighted_composite_score",
    "compute_suitability_with_coverage",
    "calculate_solar_subsolar_coordinates",
    "calculate_solar_elevation_and_azimuth",
    "calculate_topographic_horizon_angle",
    "calculate_sun_visibility_fraction",
    "estimate_surface_temperature_kelvin",
    "parse_utc_timestamp",
]
