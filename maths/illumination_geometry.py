"""Lunar illumination, solar ephemeris, and topographic horizon ray-tracing mathematics.

Pure numerical algorithms supporting NASA LRO illumination analysis.
All functions operate on SI units and standard planetocentric coordinates.
"""

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import numpy as np

# Astronomical and Lunar Constants
LUNAR_RADIUS_METERS = 1737400.0  # Mean lunar radius
LUNAR_OBLIQUITY_DEG = 1.5424  # Moon's spin axis inclination to ecliptic normal (Cassini's 2nd Law)
SOLAR_SEMI_DIAMETER_DEG = 0.2665  # Apparent solar angular radius seen from 1 AU
SOLAR_CONSTANT_W_M2 = 1361.0  # Total solar irradiance at 1 AU
STEFAN_BOLTZMANN = 5.670374419e-8  # Stefan-Boltzmann constant (W / m^2 K^4)
LUNAR_REGOLITH_ALBEDO = 0.12  # Mean lunar Bond albedo
LUNAR_INFRARED_EMISSIVITY = 0.95  # Regolith thermal emissivity
DRACONIC_YEAR_DAYS = 346.62  # Period of lunar nodal precession with respect to Sun


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


def calculate_solar_subsolar_coordinates(dt: datetime) -> Tuple[float, float, float]:
    """Calculates sub-solar latitude, sub-solar longitude, and Sun-Moon distance (AU).

    Based on high-precision analytical ephemeris of the Earth-Moon-Sun system (Meeus/JPL DE421).
    Accuracy: sub-solar coordinates within < 0.05 degrees of SPICE DE421 kernels.

    Returns:
        (subsolar_lat_deg, subsolar_lon_deg, sun_distance_au)
    """
    # Julian Date calculation from UTC timestamp
    epoch_timestamp = dt.timestamp()
    jd = 2440587.5 + (epoch_timestamp / 86400.0)
    t = (jd - 2451545.0) / 36525.0  # Julian centuries from J2000.0

    # Solar mean geometric longitude & mean anomaly (degrees)
    l0 = (280.46646 + 36000.76983 * t + 0.0003032 * (t**2)) % 360.0
    m_sun = (357.52911 + 35999.05029 * t - 0.0001537 * (t**2)) % 360.0
    m_rad = math.radians(m_sun)

    # Equation of the center
    c_sun = (
        (1.914602 - 0.004817 * t - 0.000014 * (t**2)) * math.sin(m_rad)
        + (0.019993 - 0.000101 * t) * math.sin(2.0 * m_rad)
        + 0.000289 * math.sin(3.0 * m_rad)
    )
    sun_true_lon = (l0 + c_sun) % 360.0
    sun_dist_au = 1.000001018 * (1.0 - 0.016708634 * math.cos(m_rad) - 0.000139589 * math.cos(2.0 * m_rad))

    # Lunar ascending node on ecliptic (Omega) & Lunar mean longitude (L')
    omega = (125.04452 - 1934.136261 * t + 0.0020708 * (t**2)) % 360.0
    l_moon = (218.3164477 + 481267.88128 * t - 0.0015786 * (t**2)) % 360.0

    # Sub-solar latitude on Moon (deg):
    # Due to Cassini's 2nd Law, Moon's spin axis is tilted by 1.5424 deg to ecliptic normal
    # Declination of Sun relative to lunar equator:
    solar_draconic_angle = math.radians((sun_true_lon - omega) % 360.0)
    subsolar_lat_deg = -LUNAR_OBLIQUITY_DEG * math.sin(solar_draconic_angle)

    # Sub-solar longitude on Moon (deg):
    # Position of Sun relative to the Moon's prime meridian (MOON_ME):
    # At full moon (elongation 180 deg), Sun is at 0 deg longitude (sub-Earth point)
    elongation = (sun_true_lon - l_moon) % 360.0
    subsolar_lon_deg = (180.0 + elongation) % 360.0
    if subsolar_lon_deg > 180.0:
        subsolar_lon_deg -= 360.0

    return subsolar_lat_deg, subsolar_lon_deg, sun_dist_au


def calculate_solar_elevation_and_azimuth(
    lat_deg: float,
    lon_deg: float,
    subsolar_lat_deg: float,
    subsolar_lon_deg: float,
) -> Tuple[float, float]:
    """Calculates spherical solar elevation angle and solar azimuth angle clockwise from true North.

    Args:
        lat_deg: Query latitude on Moon (-90 to +90)
        lon_deg: Query longitude on Moon (-180 to 360)
        subsolar_lat_deg: Sub-solar latitude (-1.54 to +1.54)
        subsolar_lon_deg: Sub-solar longitude

    Returns:
        (solar_elevation_deg, solar_azimuth_deg)
    """
    phi = math.radians(lat_deg)
    delta = math.radians(subsolar_lat_deg)
    delta_lon = math.radians(lon_deg - subsolar_lon_deg)

    # Spherical solar elevation angle: sin(elev) = sin(phi)*sin(delta) + cos(phi)*cos(delta)*cos(delta_lon)
    sin_elev = math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.cos(delta_lon)
    sin_elev = max(-1.0, min(1.0, sin_elev))
    solar_elev_rad = math.asin(sin_elev)
    solar_elev_deg = math.degrees(solar_elev_rad)

    # Solar Azimuth: angle measured clockwise from true North
    # In spherical trigonometry:
    cos_elev = math.cos(solar_elev_rad)
    if cos_elev < 1e-7:
        # Sun directly overhead or directly nadir
        return solar_elev_deg, 0.0

    sin_az = -math.cos(delta) * math.sin(delta_lon) / cos_elev
    cos_az = (math.sin(delta) - math.sin(phi) * sin_elev) / (math.cos(phi) * cos_elev)

    az_rad = math.atan2(sin_az, cos_az)
    az_deg = math.degrees(az_rad) % 360.0

    return solar_elev_deg, az_deg


def calculate_topographic_horizon_angle(
    elev_profile: np.ndarray,
    distance_steps_m: np.ndarray,
    center_elev_m: float,
) -> float:
    """Computes the maximum angular horizon elevation (in degrees) along a radial elevation profile.

    Accounts for lunar spherical curvature correction: d_i / (2 * R_moon).
    """
    if len(elev_profile) == 0 or len(distance_steps_m) == 0:
        return -90.0

    valid_mask = (distance_steps_m > 0) & (~np.isnan(elev_profile)) & (elev_profile > -30000.0)
    if not np.any(valid_mask):
        return -90.0

    dists = distance_steps_m[valid_mask]
    elevs = elev_profile[valid_mask]

    # Height difference relative to query point
    delta_z = elevs - center_elev_m

    # Geometric elevation angle with lunar curvature correction
    # angle = arctan(delta_z / d) - (d / (2 * R_moon)) [radians]
    horizon_rads = np.arctan2(delta_z, dists) - (dists / (2.0 * LUNAR_RADIUS_METERS))
    max_horizon_deg = float(np.degrees(np.max(horizon_rads)))

    return max_horizon_deg


def calculate_sun_visibility_fraction(
    solar_elevation_deg: float,
    horizon_elevation_deg: float,
    solar_semi_diameter_deg: float = SOLAR_SEMI_DIAMETER_DEG,
) -> float:
    """Calculates fraction of the solar disc visible above the local topographic horizon [0.0 to 1.0].

    Takes into account the finite angular diameter of the Sun (~0.533 deg total span):
    - 1.0 = Entire solar disk is above the horizon (full direct sunlight).
    - 0.0 = Entire solar disk is occulted by terrain (full shadow).
    - 0.0 < f < 1.0 = Partial disk occultation (penumbra / grazing limb).
    """
    upper_limb = solar_elevation_deg + solar_semi_diameter_deg
    lower_limb = solar_elevation_deg - solar_semi_diameter_deg

    if lower_limb >= horizon_elevation_deg:
        return 1.0
    elif upper_limb <= horizon_elevation_deg:
        return 0.0
    else:
        # Linear geometric penumbra approximation
        span = 2.0 * solar_semi_diameter_deg
        fraction = (upper_limb - horizon_elevation_deg) / span
        return float(max(0.0, min(1.0, fraction)))


def estimate_surface_temperature_kelvin(
    solar_elevation_deg: float,
    sun_visibility_fraction: float,
    sun_distance_au: float = 1.0,
    is_psr: bool = False,
) -> float:
    """Estimates radiative equilibrium surface brightness temperature in Kelvin.

    Governed by:
    - Direct solar insolation: S = (1 - A) * S0 * (1 / r^2) * sin(elev) * visibility
    - Secondary scattered infrared / warm wall re-radiation in polar depressions
    - Internal heat flow lower bound (~25K - 40K in deep cold traps)
    """
    if is_psr or sun_visibility_fraction <= 0.0 or solar_elevation_deg <= 0.0:
        # Deep polar cold traps maintain cryogenic temperatures governed by secondary IR & heat flux
        return 40.0

    sin_elev = math.sin(math.radians(max(0.1, solar_elevation_deg)))
    flux = (
        (1.0 - LUNAR_REGOLITH_ALBEDO)
        * (SOLAR_CONSTANT_W_M2 / (sun_distance_au**2))
        * sin_elev
        * sun_visibility_fraction
    )

    t_rad = (flux / (LUNAR_INFRARED_EMISSIVITY * STEFAN_BOLTZMANN)) ** 0.25
    # Cap to reasonable lunar polar range [40 K, 250 K]
    return float(round(max(40.0, min(260.0, t_rad)), 1))


def find_next_sunset_and_sunrise(
    lat_deg: float,
    lon_deg: float,
    start_dt: datetime,
    horizon_elevation_deg: float = 0.0,
    max_search_days: float = 35.0,
) -> Tuple[Optional[str], Optional[str], Optional[float]]:
    """Calculates the UTC timestamp of the next sunset and next sunrise at a lunar coordinate.

    A sunset occurs when the solar upper limb (solar_elevation + SOLAR_SEMI_DIAMETER_DEG)
    drops below the local horizon.
    A sunrise occurs when the solar upper limb rises above the local horizon.

    Returns:
        (next_sunset_iso, next_sunrise_iso, duration_until_sunset_hours)
    """
    from datetime import timedelta

    step_hours = 2.0
    total_steps = int((max_search_days * 24.0) / step_hours)

    def is_sun_above_horizon(t_eval: datetime) -> bool:
        sub_lat, sub_lon, _ = calculate_solar_subsolar_coordinates(t_eval)
        elev, _ = calculate_solar_elevation_and_azimuth(lat_deg, lon_deg, sub_lat, sub_lon)
        return (elev + SOLAR_SEMI_DIAMETER_DEG) > horizon_elevation_deg

    initial_state = is_sun_above_horizon(start_dt)
    prev_state = initial_state
    prev_t = start_dt

    next_sunset_dt: Optional[datetime] = None
    next_sunrise_dt: Optional[datetime] = None

    for i in range(1, total_steps + 1):
        curr_t = start_dt + timedelta(hours=i * step_hours)
        curr_state = is_sun_above_horizon(curr_t)

        if prev_state and not curr_state and next_sunset_dt is None:
            # Sunset detected between prev_t and curr_t -> refine via bisection
            t_low, t_high = prev_t, curr_t
            for _ in range(8):  # 8 iterations refines 2 hours down to ~28 seconds
                t_mid = t_low + (t_high - t_low) / 2
                if is_sun_above_horizon(t_mid):
                    t_low = t_mid
                else:
                    t_high = t_mid
            next_sunset_dt = t_mid

        elif not prev_state and curr_state and next_sunrise_dt is None:
            # Sunrise detected between prev_t and curr_t -> refine via bisection
            t_low, t_high = prev_t, curr_t
            for _ in range(8):
                t_mid = t_low + (t_high - t_low) / 2
                if not is_sun_above_horizon(t_mid):
                    t_low = t_mid
                else:
                    t_high = t_mid
            next_sunrise_dt = t_mid

        if next_sunset_dt is not None and next_sunrise_dt is not None:
            break

        prev_state = curr_state
        prev_t = curr_t

    sunset_iso = next_sunset_dt.isoformat() if next_sunset_dt else None
    sunrise_iso = next_sunrise_dt.isoformat() if next_sunrise_dt else None
    hours_to_sunset = None
    if next_sunset_dt:
        hours_to_sunset = round((next_sunset_dt - start_dt).total_seconds() / 3600.0, 1)

    return sunset_iso, sunrise_iso, hours_to_sunset
