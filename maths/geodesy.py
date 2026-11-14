"""Geodetic mathematics and coordinate reference system transformations for the Moon."""

import math
from typing import Tuple

# Standard IAU 2000 Moon Mean Radius in meters
DEFAULT_MOON_RADIUS_M: float = 1_737_400.0


def latlon_to_polar_stereo(
    lat_deg: float,
    lon_deg: float,
    radius_m: float = DEFAULT_MOON_RADIUS_M,
) -> Tuple[float, float]:
    """Converts planetocentric latitude and longitude to Lunar South Pole Stereographic coordinates (x, y) in meters.

    Math:
        colatitude = 90° + latitude (0 at South Pole, π/2 at equator)
        r = 2 * R * tan(colatitude / 2)
        x = r * sin(longitude)
        y = -r * cos(longitude)

    Args:
        lat_deg: Latitude in degrees (-90.0 at South Pole to +90.0 at North Pole).
        lon_deg: Longitude in degrees (-180.0 to +360.0).
        radius_m: Lunar reference sphere radius (default 1,737,400.0 meters).

    Returns:
        (x, y) in meters in the South Pole Stereographic projection.
    """
    lat_rad = math.radians(lat_deg)
    lon_rad = math.radians(lon_deg)
    colat_rad = (math.pi / 2.0) + lat_rad
    r = 2.0 * radius_m * math.tan(colat_rad / 2.0)
    x = r * math.sin(lon_rad)
    y = -r * math.cos(lon_rad)
    return x, y


def polar_stereo_to_latlon(
    x: float,
    y: float,
    radius_m: float = DEFAULT_MOON_RADIUS_M,
) -> Tuple[float, float]:
    """Converts South Pole Stereographic coordinates (x, y) in meters to planetocentric lat/lon in degrees.

    Math:
        r = sqrt(x^2 + y^2)
        colatitude = 2 * arctan(r / (2 * R))
        latitude = colatitude - π/2
        longitude = arctan2(x, -y)

    Args:
        x: Easting in meters.
        y: Northing in meters.
        radius_m: Lunar reference sphere radius in meters.

    Returns:
        (latitude_deg, longitude_deg) in degrees.
    """
    r = math.sqrt(x**2 + y**2)
    if r == 0.0:
        return -90.0, 0.0

    colat_rad = 2.0 * math.atan(r / (2.0 * radius_m))
    lat_rad = colat_rad - (math.pi / 2.0)
    lat_deg = math.degrees(lat_rad)

    lon_rad = math.atan2(x, -y)
    lon_deg = math.degrees(lon_rad)
    if lon_deg < 0.0:
        lon_deg += 360.0

    return lat_deg, lon_deg


def haversine_lunar_distance(
    lat1_deg: float,
    lon1_deg: float,
    lat2_deg: float,
    lon2_deg: float,
    radius_m: float = DEFAULT_MOON_RADIUS_M,
) -> float:
    """Calculates great-circle surface distance between two lunar coordinates using the Haversine formula."""
    phi1 = math.radians(lat1_deg)
    phi2 = math.radians(lat2_deg)
    delta_phi = math.radians(lat2_deg - lat1_deg)
    delta_lambda = math.radians(lon2_deg - lon1_deg)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return radius_m * c


def euclidean_distance_2d(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculates flat 2D Euclidean distance in projected coordinates."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
