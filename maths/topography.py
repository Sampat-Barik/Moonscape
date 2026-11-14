"""Topographic mathematics: Horn's slope algorithm, surface aspect, and RMS roughness."""

from typing import Dict, Tuple
import numpy as np
from scipy.ndimage import convolve, uniform_filter


def horn_slope_and_aspect(
    elevation: np.ndarray,
    dx: float,
    dy: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Calculates topographic surface slope and aspect using Horn's (1981) 8-neighbor convolution kernels.

    Horn 3x3 Kernels:
        dz/dx = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]] / (8 * dx)
        dz/dy = [[ 1, 2, 1], [ 0, 0, 0], [-1,-2,-1]] / (8 * dy)
        slope = arctan(sqrt((dz/dx)^2 + (dz/dy)^2))
        aspect = 180° - arctan2(dz/dy, -dz/dx)

    Args:
        elevation: 2D numpy array of elevation heights in meters.
        dx: Spatial resolution in the x-dimension in meters.
        dy: Spatial resolution in the y-dimension in meters.

    Returns:
        (slope_degrees, aspect_degrees)
    """
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32) / (8.0 * dx)
    ky = np.array([[1, 2, 1], [0, 0, 0], [-1, -2, -1]], dtype=np.float32) / (8.0 * dy)

    dz_dx = convolve(elevation, kx, mode="reflect")
    dz_dy = convolve(elevation, ky, mode="reflect")

    gradient_magnitude = np.sqrt(dz_dx**2 + dz_dy**2)
    slope_rad = np.arctan(gradient_magnitude)
    slope_deg = np.degrees(slope_rad)

    aspect_rad = np.arctan2(dz_dy, -dz_dx)
    aspect_deg = 180.0 - np.degrees(aspect_rad)
    aspect_deg = np.mod(aspect_deg, 360.0)

    return slope_deg, aspect_deg


def rms_surface_roughness(elevation: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """Calculates root-mean-square (RMS) residual height deviation from the local neighborhood mean.

    Math:
        residual_i = z_i - mean(z)
        RMS = sqrt( (1/N) * sum(residual_i^2) )

    Args:
        elevation: 2D numpy array of elevation heights.
        kernel_size: Neighborhood window size (default 3x3).

    Returns:
        2D numpy array of RMS roughness values in meters.
    """
    local_mean = uniform_filter(elevation, size=kernel_size, mode="reflect")
    residuals = elevation - local_mean
    return np.sqrt(uniform_filter(residuals**2, size=kernel_size, mode="reflect"))


def slope_distribution_breakdown(
    slopes: np.ndarray,
    valid_mask: np.ndarray,
    ideal_max_deg: float = 5.0,
    nominal_max_deg: float = 10.0,
    critical_max_deg: float = 15.0,
) -> Dict[str, float]:
    """Computes area percentage breakdown across Apollo/Artemis slope hazard bins."""
    valid_slopes = slopes[valid_mask]
    total = len(valid_slopes)
    if total == 0:
        return {
            "ideal_pct": 0.0,
            "acceptable_pct": 0.0,
            "marginal_pct": 0.0,
            "critical_hazardous_pct": 0.0,
        }

    ideal_count = np.sum(valid_slopes <= ideal_max_deg)
    acceptable_count = np.sum((valid_slopes > ideal_max_deg) & (valid_slopes <= nominal_max_deg))
    marginal_count = np.sum((valid_slopes > nominal_max_deg) & (valid_slopes <= critical_max_deg))
    critical_count = np.sum(valid_slopes > critical_max_deg)

    return {
        "ideal_pct": round(float(ideal_count / total * 100.0), 1),
        "acceptable_pct": round(float(acceptable_count / total * 100.0), 1),
        "marginal_pct": round(float(marginal_count / total * 100.0), 1),
        "critical_hazardous_pct": round(float(critical_count / total * 100.0), 1),
    }
