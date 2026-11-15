"""Scientific coordinate management, normalization, and projection conversions for the Moon."""

import math
from typing import Tuple
from maths.geodesy import (
    DEFAULT_MOON_RADIUS_M,
    haversine_lunar_distance,
    latlon_to_polar_stereo,
    polar_stereo_to_latlon,
)


class CoordinateManager:
    """Manages lunar coordinate systems, planetary datum parameters, and geodetic projections."""

    RADIUS_METERS: float = DEFAULT_MOON_RADIUS_M
    SOUTH_POLE_MIN_LAT: float = -90.0
    SOUTH_POLE_CORE_MAX_LAT: float = -80.0       # Core South Pole: -90° to -80°
    SOUTH_POLE_EXTENDED_MAX_LAT: float = -75.0   # Extended region: -80° to -75°
    SOUTH_POLE_CONTEXT_MAX_LAT: float = -70.0    # Optional context region: -75° to -70°
    SOUTH_POLE_MAX_LAT: float = -70.0            # Boundary of configured South Pole exploration envelope

    @staticmethod
    def normalize_longitude(lon_deg: float, target_range: str = "360") -> float:
        """Normalizes longitude into standard planetary science ranges.

        Args:
            lon_deg: Input longitude in degrees.
            target_range: Either '360' for [0, 360) or '180' for [-180, 180).
        """
        mod_lon = lon_deg % 360.0
        if target_range == "360":
            return mod_lon if mod_lon >= 0 else mod_lon + 360.0
        else:  # -180 to +180
            return mod_lon if mod_lon <= 180.0 else mod_lon - 360.0

    @classmethod
    def validate_coordinates(cls, lat_deg: float, lon_deg: float) -> Tuple[bool, str]:
        """Validates geographic planetocentric coordinates for lunar analysis."""
        if not (-90.0 <= lat_deg <= 90.0):
            return False, f"Latitude {lat_deg}° is outside physical lunar bounds [-90.0°, +90.0°]."
        if not (-360.0 <= lon_deg <= 720.0):
            return False, f"Longitude {lon_deg}° is outside allowable numerical range."
        return True, "Valid"

    @classmethod
    def get_coverage_zone(cls, lat_deg: float) -> str:
        """Classifies latitude into exploration coverage levels.

        Returns:
            'core'     : Core South Pole (-90° to -80°)
            'extended' : Extended South Pole (-80° to -75°)
            'context'  : Optional Context Region (-75° to -70°)
            'outside'  : Outside configured analysis region (lat > -70° or invalid)
        """
        if not (-90.0 <= lat_deg <= 90.0):
            return "invalid"
        if lat_deg > cls.SOUTH_POLE_CONTEXT_MAX_LAT:
            return "outside"
        if lat_deg > cls.SOUTH_POLE_EXTENDED_MAX_LAT:
            return "context"
        if lat_deg > cls.SOUTH_POLE_CORE_MAX_LAT:
            return "extended"
        return "core"

    @classmethod
    def is_in_core_zone(cls, lat_deg: float) -> bool:
        """Checks if coordinate falls inside the Core South Pole region (-90° to -80°)."""
        return cls.SOUTH_POLE_MIN_LAT <= lat_deg <= cls.SOUTH_POLE_CORE_MAX_LAT

    @classmethod
    def is_in_analysis_region(cls, lat_deg: float) -> bool:
        """Checks if coordinate falls within configured South Pole exploration/analysis region (-90° to -70°)."""
        return cls.SOUTH_POLE_MIN_LAT <= lat_deg <= cls.SOUTH_POLE_MAX_LAT

    @classmethod
    def is_in_south_pole_zone(cls, lat_deg: float) -> bool:
        """Legacy helper: Checks if coordinate falls inside the Core South Pole zone (-90° to -80°)."""
        return cls.is_in_core_zone(lat_deg)

    @classmethod
    def to_polar_stereographic(cls, lat_deg: float, lon_deg: float) -> Tuple[float, float]:
        """Converts planetocentric lat/lon (degrees) to Lunar South Polar Stereographic (x, y) meters."""
        valid, msg = cls.validate_coordinates(lat_deg, lon_deg)
        if not valid:
            raise ValueError(msg)
        return latlon_to_polar_stereo(lat_deg, lon_deg, radius_m=cls.RADIUS_METERS)

    @classmethod
    def from_polar_stereographic(cls, x: float, y: float) -> Tuple[float, float]:
        """Converts Lunar South Polar Stereographic (x, y) meters to planetocentric lat/lon degrees."""
        return polar_stereo_to_latlon(x, y, radius_m=cls.RADIUS_METERS)

    @classmethod
    def surface_distance_m(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates great-circle distance along lunar sphere surface in meters."""
        return haversine_lunar_distance(lat1, lon1, lat2, lon2, radius_m=cls.RADIUS_METERS)


coordinate_manager = CoordinateManager()
