"""Topographic mathematics: Horn's slope algorithm, surface aspect, and RMS roughness."""

from typing import Any, Dict, List, Optional, Tuple
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
    return np.sqrt(np.maximum(0.0, uniform_filter(residuals**2, size=kernel_size, mode="reflect")))


def calculate_multi_baseline_roughness(
    elevation: np.ndarray,
    dx_meters: float,
    valid_mask: Optional[np.ndarray] = None,
    candidate_baselines_m: Optional[Tuple[float, ...]] = (15.0, 60.0, 100.0, 240.0, 480.0, 1600.0),
) -> Dict[str, Dict[str, Any]]:
    """Evaluates multi-baseline RMS surface roughness following Barker et al. (2016) / NASA PGDA 90 methodology.

    Lunar surface roughness is inherently scale-dependent; shorter baselines capture micro-roughness
    relevant to lander footpads and belly clearance, while longer baselines measure macroscopic slope variations.

    Args:
        elevation: 2D array of elevation values in meters.
        dx_meters: Spatial pixel resolution in meters.
        valid_mask: Optional boolean array marking non-nodata pixels within the physical analysis disc.
        candidate_baselines_m: Tuple of target physical baseline lengths in meters.

    Returns:
        Dictionary keyed by baseline label (e.g. '15m', '60m', '240m') with:
            - 'resolvable': bool
            - 'kernel_size': int (if resolvable)
            - 'actual_baseline_m': float (if resolvable)
            - 'mean_m': float (if resolvable and valid data exists)
            - 'max_m': float
            - 'min_m': float
            - 'status': description string
    """
    if candidate_baselines_m is None:
        candidate_baselines_m = (15.0, 60.0, 100.0, 240.0, 480.0, 1600.0)

    rows, cols = elevation.shape
    min_dim = min(rows, cols)
    results: Dict[str, Dict[str, Any]] = {}

    if valid_mask is None:
        valid_mask = (~np.isnan(elevation)) & (elevation > -30000.0)

    # Pre-clean nodata for filtering
    cleaned = elevation.copy()
    if np.any(valid_mask):
        reg_mean = float(np.mean(cleaned[valid_mask]))
        cleaned[~valid_mask] = reg_mean
    else:
        reg_mean = 0.0

    for target_m in candidate_baselines_m:
        label = f"{int(target_m)}m" if target_m >= 1.0 else f"{target_m:.1f}m"

        # Check Nyquist and minimum 3x3 kernel rule
        k_est = int(round(target_m / dx_meters))
        if k_est < 3:
            results[label] = {
                "resolvable": False,
                "target_baseline_m": target_m,
                "status": f"Unresolvable (DEM resolution {dx_meters:.1f}m exceeds Nyquist limit for {target_m}m baseline; minimum kernel requires dx <= {target_m/3.0:.1f}m)",
            }
            continue

        if k_est >= min_dim:
            results[label] = {
                "resolvable": False,
                "target_baseline_m": target_m,
                "status": f"Unresolvable (Baseline {target_m}m requires kernel {k_est}x{k_est} which exceeds window bounds {rows}x{cols})",
            }
            continue

        # Force kernel to be odd for symmetric centered window
        kernel_size = k_est if (k_est % 2 != 0) else (k_est + 1)
        actual_baseline = round(kernel_size * dx_meters, 1)

        rough_map = rms_surface_roughness(cleaned, kernel_size=kernel_size)
        valid_vals = rough_map[valid_mask]

        if valid_vals.size > 0:
            results[label] = {
                "resolvable": True,
                "target_baseline_m": target_m,
                "actual_baseline_m": actual_baseline,
                "kernel_size": kernel_size,
                "mean_m": round(float(np.mean(valid_vals)), 3),
                "max_m": round(float(np.max(valid_vals)), 3),
                "min_m": round(float(np.min(valid_vals)), 3),
                "std_dev_m": round(float(np.std(valid_vals)), 3),
                "status": "computed",
            }
        else:
            results[label] = {
                "resolvable": True,
                "target_baseline_m": target_m,
                "actual_baseline_m": actual_baseline,
                "kernel_size": kernel_size,
                "mean_m": None,
                "status": "no_valid_pixels",
            }

    return results


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
