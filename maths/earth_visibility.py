"""Lunar Earth visibility, lunar optical/physical libration, and communication line-of-sight mathematics.

Pure numerical algorithms supporting NASA Artemis communication corridor analysis.
All functions operate on SI units and standard planetocentric coordinates.
"""

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import numpy as np

# Astronomical Constants
MOON_RADIUS_METERS = 1737400.0  # Mean lunar radius
EARTH_RADIUS_METERS = 6378137.0  # WGS-84 equatorial Earth radius
MEAN_EARTH_MOON_DISTANCE_M = 384400000.0  # 384,400 km
EARTH_SEMI_DIAMETER_DEG = math.degrees(math.atan(EARTH_RADIUS_METERS / MEAN_EARTH_MOON_DISTANCE_M))  # ~0.95 deg


def parse_utc_timestamp(epoch: Optional[str] = None) -> datetime:
    """Parses an ISO-8601 UTC timestamp string or returns current UTC time."""
    if epoch is None or not epoch.strip():
        return datetime.now(timezone.utc)

    clean_str = epoch.strip()
    if clean_str.endswith("Z"):
        clean_str = clean_str[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError as e:
        raise ValueError(f"Invalid ISO-8601 datetime format '{epoch}'. Expected e.g. '2026-10-15T12:00:00Z'.") from e


def calculate_subearth_coordinates(dt: datetime) -> Tuple[float, float, float]:
    """Calculates sub-Earth point latitude and longitude on the Moon, and Earth-Moon distance.

    Based on lunar optical libration theory (Meeus, Astronomical Algorithms Chapter 53).
    The sub-Earth point corresponds to the direction of Earth in the Mean Earth/Polar Axis (MOON_ME) frame.
    Libration amplitudes:
      - Latitude: up to ~6.7 deg (caused by Moon's orbit inclination to lunar equator)
      - Longitude: up to ~7.9 deg (caused by orbital eccentricity & inequality of motion)

    Returns:
        (subearth_lat_deg, subearth_lon_deg, earth_distance_km)
    """
    epoch_timestamp = dt.timestamp()
    jd = 2440587.5 + (epoch_timestamp / 86400.0)
    t = (jd - 2451545.0) / 36525.0  # Julian centuries from J2000.0

    # Fundamental lunar arguments (degrees)
    # Mean elongation of the Moon
    d = (297.8501921 + 445267.1114034 * t - 0.0018819 * (t**2)) % 360.0
    # Sun's mean anomaly
    m = (357.5291092 + 35999.0502909 * t - 0.0001536 * (t**2)) % 360.0
    # Moon's mean anomaly
    m_prime = (134.9633964 + 477198.8675055 * t + 0.0087414 * (t**2)) % 360.0
    # Moon's argument of latitude (distance from ascending node)
    f = (93.2720950 + 483202.0175233 * t - 0.0036539 * (t**2)) % 360.0

    d_rad = math.radians(d)
    m_rad = math.radians(m)
    mp_rad = math.radians(m_prime)
    f_rad = math.radians(f)

    # Optical libration in longitude (degrees)
    # Primary terms from equation of the center, evection, and variation:
    l_lib = (
        -6.2887 * math.sin(mp_rad)
        + 1.2740 * math.sin(2.0 * d_rad - mp_rad)
        + 0.6583 * math.sin(2.0 * d_rad)
        + 0.2136 * math.sin(2.0 * mp_rad)
        - 0.1851 * math.sin(m_rad)
        - 0.1143 * math.sin(2.0 * f_rad)
    )

    # Optical libration in latitude (degrees)
    # Governed by Moon's orbit inclination to lunar equator (~6.69 deg total inclination)
    b_lib = (
        -6.688 * math.sin(f_rad)
        + 0.173 * math.sin(f_rad - 2.0 * d_rad)
        - 0.075 * math.sin(f_rad + 2.0 * d_rad)
        + 0.046 * math.sin(f_rad - 2.0 * mp_rad)
        - 0.033 * math.sin(f_rad + mp_rad)
    )

    # Earth-Moon distance (km)
    dist_km = 385000.56 - 20905.35 * math.cos(mp_rad) - 3699.11 * math.cos(2.0 * d_rad - mp_rad)

    # Normalize longitude to [-180, 180]
    subearth_lon = (l_lib + 180.0) % 360.0 - 180.0
    subearth_lat = max(-10.0, min(10.0, b_lib))

    return subearth_lat, subearth_lon, dist_km


def calculate_earth_elevation_and_azimuth(
    lat_deg: float,
    lon_deg: float,
    subearth_lat_deg: float,
    subearth_lon_deg: float,
) -> Tuple[float, float]:
    """Calculates geometric Earth elevation angle and azimuth clockwise from true North on Moon.

    Args:
        lat_deg: Query latitude on Moon (-90 to +90)
        lon_deg: Query longitude on Moon (-180 to 360)
        subearth_lat_deg: Sub-Earth latitude (-10 to +10)
        subearth_lon_deg: Sub-Earth longitude (-10 to +10)

    Returns:
        (earth_elevation_deg, earth_azimuth_deg)
    """
    phi = math.radians(lat_deg)
    delta = math.radians(subearth_lat_deg)
    delta_lon = math.radians(lon_deg - subearth_lon_deg)

    # Spherical elevation: sin(elev) = sin(phi)*sin(delta) + cos(phi)*cos(delta)*cos(delta_lon)
    sin_elev = math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.cos(delta_lon)
    sin_elev = max(-1.0, min(1.0, sin_elev))
    earth_elev_rad = math.asin(sin_elev)
    earth_elev_deg = math.degrees(earth_elev_rad)

    # Earth Azimuth: angle measured clockwise from true North
    cos_elev = math.cos(earth_elev_rad)
    if cos_elev < 1e-7:
        return earth_elev_deg, 0.0

    sin_az = -math.cos(delta) * math.sin(delta_lon) / cos_elev
    cos_az = (math.sin(delta) - math.sin(phi) * sin_elev) / (math.cos(phi) * cos_elev)

    az_rad = math.atan2(sin_az, cos_az)
    az_deg = math.degrees(az_rad) % 360.0

    return earth_elev_deg, az_deg


def calculate_earth_visibility_fraction(
    earth_elevation_deg: float,
    horizon_elevation_deg: float,
    earth_semi_diameter_deg: float = EARTH_SEMI_DIAMETER_DEG,
) -> float:
    """Calculates visible fraction of the Earth's disc [0.0 to 1.0] above local topographic horizon.

    - 1.0 = Full Earth disc visible above terrain.
    - 0.0 = Complete terrain occlusion (communication shadow).
    - 0.0 < f < 1.0 = Partial occultation by terrain.
    """
    upper_limb = earth_elevation_deg + earth_semi_diameter_deg
    lower_limb = earth_elevation_deg - earth_semi_diameter_deg

    if lower_limb >= horizon_elevation_deg:
        return 1.0
    elif upper_limb <= horizon_elevation_deg:
        return 0.0
    else:
        span = 2.0 * earth_semi_diameter_deg
        fraction = (upper_limb - horizon_elevation_deg) / span
        return float(max(0.0, min(1.0, fraction)))


def evaluate_communication_link(
    earth_elevation_deg: float,
    visibility_fraction: float,
    min_operational_elevation_deg: float = 2.0,
) -> Tuple[bool, str]:
    """Evaluates direct-to-Earth communication feasibility.

    Distinguishes geometric line-of-sight from guaranteed operational communication:
    - Geometric visibility requires visibility_fraction > 0.
    - Operational RF link requires Earth elevation >= 2.0° to clear near-surface
      multipath fading, and >= 50% unocculted disc for sufficient link margin.

    Returns:
        (is_operational, rationale)
    """
    if earth_elevation_deg < 0.0:
        return False, "Earth is below the mean spherical lunar horizon."
    elif visibility_fraction <= 0.0:
        return False, "Complete Earth occlusion by surrounding lunar topography (radio shadow)."
    elif earth_elevation_deg < min_operational_elevation_deg:
        return (
            False,
            f"Marginal Earth elevation ({earth_elevation_deg:.2f}° < {min_operational_elevation_deg}°). "
            "High risk of multi-path regolith scattering and signal degradation.",
        )
    elif visibility_fraction < 0.5:
        return (
            False,
            f"Partial Earth disc occultation ({visibility_fraction * 100.0:.1f}% visible). "
            "Insufficient RF aperture margin for high-bandwidth direct link.",
        )
    else:
        return True, "Direct line-of-sight with favorable Earth elevation and clear RF link margin."
