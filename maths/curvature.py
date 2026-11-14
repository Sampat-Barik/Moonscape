"""Curvature and morphological mathematics for crater and depression detection."""

import numpy as np
from scipy.ndimage import laplace


def laplacian_curvature(elevation: np.ndarray) -> np.ndarray:
    """Calculates the discrete 2D Laplace operator (second spatial derivative) of the elevation surface.

    Math:
        nabla^2(z) = d^2z/dx^2 + d^2z/dy^2

    In discrete 2D grid:
        Positive values indicate concave upward depressions (crater bowls).
        Negative values indicate convex ridges and ejecta crests.
    """
    return laplace(elevation)


def detect_crater_basins(curvature: np.ndarray, threshold: float = 15.0) -> np.ndarray:
    """Returns a boolean mask where surface concave curvature exceeds the crater basin threshold."""
    return curvature > threshold
