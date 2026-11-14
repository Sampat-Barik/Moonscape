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
    weighted_composite_score,
)

__all__ = [
    "latlon_to_polar_stereo",
    "polar_stereo_to_latlon",
    "haversine_lunar_distance",
    "euclidean_distance_2d",
    "horn_slope_and_aspect",
    "rms_surface_roughness",
    "slope_distribution_breakdown",
    "laplacian_curvature",
    "detect_crater_basins",
    "piecewise_linear_penalty",
    "evaluate_slope_score",
    "evaluate_roughness_score",
    "weighted_composite_score",
]
