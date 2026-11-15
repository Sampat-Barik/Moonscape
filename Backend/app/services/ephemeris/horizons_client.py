"""NASA JPL Horizons On-Line Solar System Ephemeris Client.

Provides topocentric lunar observer ephemerides for the Sun (target 10) and Earth (target 399)
relative to any surface coordinate on the Moon (body 301).

Official API Documentation: https://ssd-api.jpl.nasa.gov/doc/horizons.html
Official Query Endpoint: https://ssd.jpl.nasa.gov/api/horizons.api
"""

from collections import OrderedDict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import logging
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.logging import logger
from maths.geodesy import DEFAULT_MOON_RADIUS_M
from maths.illumination_geometry import parse_utc_timestamp

HORIZONS_API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"


@dataclass
class HorizonsEphemerisPoint:
    """Single time-step ephemeris observation from JPL Horizons."""

    epoch_iso: str
    target: str  # "Sun" or "Earth"
    target_id: str  # "10" or "399"
    azimuth_deg: float
    elevation_deg: float
    distance_au: Optional[float] = None
    distance_km: Optional[float] = None
    range_rate_km_s: Optional[float] = None
    apparent_coordinates: bool = True
    ref_body: str = "Moon (301)"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HorizonsQueryResult:
    """Complete ephemeris series returned by JPL Horizons query."""

    success: bool
    target: str
    target_id: str
    observer_lat: float
    observer_lon: float
    observer_alt_km: float
    start_epoch_iso: str
    stop_epoch_iso: str
    step_hours: float
    points: List[HorizonsEphemerisPoint]
    source_attribution: str
    is_cached: bool = False
    query_duration_ms: float = 0.0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["points"] = [p.to_dict() for p in self.points]
        return d


class HorizonsClient:
    """Adapter for NASA JPL Horizons API tailored for topocentric lunar surface observers."""

    def __init__(self, cache_capacity: int = 128, cache_ttl_seconds: float = 7200.0):
        self.api_url = HORIZONS_API_URL
        self._cache: OrderedDict[str, Tuple[float, HorizonsQueryResult]] = OrderedDict()
        self._cache_capacity = cache_capacity
        self._cache_ttl = cache_ttl_seconds
        self._lock = threading.Lock()
        self._timeout_seconds = 12.0

    def query_observer_ephemeris(
        self,
        lat_deg: float,
        lon_deg: float,
        target_id: str,  # '10' for Sun, '399' for Earth
        start_dt: datetime,
        stop_dt: datetime,
        step_hours: float = 2.0,
        alt_km: float = 0.0,
    ) -> HorizonsQueryResult:
        """Queries JPL Horizons for topocentric apparent azimuth and elevation from lunar coordinates.

        Coordinate System:
          - Center: 'coord@301' (Moon-centered topocentric observer)
          - Frame: Body-fixed Moon coordinate system (IAU MOON_ME)
          - Longitude: 0° to 360° East (or -180° to +180°)
          - Latitude: -90° to +90°
        """
        # Normalize and validate inputs
        norm_lat = max(-90.0, min(90.0, float(lat_deg)))
        norm_lon = ((float(lon_deg) + 360.0) % 360.0)
        norm_alt = max(-10.0, min(10.0, float(alt_km)))

        target_name = "Sun" if str(target_id) in ["10", "Sun", "sun"] else ("Earth" if str(target_id) in ["399", "Earth", "earth"] else f"Target-{target_id}")
        t_id = "10" if target_name == "Sun" else ("399" if target_name == "Earth" else str(target_id))

        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if stop_dt.tzinfo is None:
            stop_dt = stop_dt.replace(tzinfo=timezone.utc)

        if stop_dt <= start_dt:
            stop_dt = start_dt + timedelta(hours=max(step_hours, 2.0))

        start_str = start_dt.strftime("%Y-%m-%d %H:%M")
        stop_str = stop_dt.strftime("%Y-%m-%d %H:%M")
        step_str = f"{int(step_hours)} h" if step_hours >= 1.0 else f"{int(step_hours * 60)} m"

        cache_key = f"{t_id}:{norm_lat:.4f}:{norm_lon:.4f}:{norm_alt:.2f}:{start_str}:{stop_str}:{step_str}"

        # 1. Check local cache
        now = time.time()
        with self._lock:
            if cache_key in self._cache:
                timestamp, cached_result = self._cache[cache_key]
                if now - timestamp < self._cache_ttl:
                    self._cache.move_to_end(cache_key)
                    # Return clone with is_cached=True
                    cached_dict = cached_result.to_dict()
                    return HorizonsQueryResult(
                        success=cached_result.success,
                        target=cached_result.target,
                        target_id=cached_result.target_id,
                        observer_lat=cached_result.observer_lat,
                        observer_lon=cached_result.observer_lon,
                        observer_alt_km=cached_result.observer_alt_km,
                        start_epoch_iso=cached_result.start_epoch_iso,
                        stop_epoch_iso=cached_result.stop_epoch_iso,
                        step_hours=cached_result.step_hours,
                        points=list(cached_result.points),
                        source_attribution=cached_result.source_attribution,
                        is_cached=True,
                        query_duration_ms=0.5,
                        error_message=cached_result.error_message,
                    )
                else:
                    del self._cache[cache_key]

        # 2. Prepare API payload
        params = {
            "format": "json",
            "COMMAND": f"'{t_id}'",
            "CENTER": "'coord@301'",
            "COORD_TYPE": "'GEODETIC'",
            "SITE_COORD": f"'{norm_lon:.4f},{norm_lat:.4f},{norm_alt:.3f}'",
            "START_TIME": f"'{start_str}'",
            "STOP_TIME": f"'{stop_str}'",
            "STEP_SIZE": f"'{step_str}'",
            "QUANTITIES": "'4,20'",  # 4: Azimuth & Elevation; 20: Range & Range-rate
            "REF_SYSTEM": "'ICRF'",
            "ANG_FORMAT": "'DEG'",
            "TIME_DIGITS": "'MIN'",
            "CSV_FORMAT": "'NO'",
        }

        query_start = time.perf_counter()
        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                resp = client.get(self.api_url, params=params)
                elapsed_ms = (time.perf_counter() - query_start) * 1000.0

                if resp.status_code != 200:
                    err_msg = f"Horizons API returned HTTP {resp.status_code}: {resp.text[:200]}"
                    logger.warning(err_msg)
                    return HorizonsQueryResult(
                        success=False,
                        target=target_name,
                        target_id=t_id,
                        observer_lat=norm_lat,
                        observer_lon=norm_lon,
                        observer_alt_km=norm_alt,
                        start_epoch_iso=start_dt.isoformat(),
                        stop_epoch_iso=stop_dt.isoformat(),
                        step_hours=step_hours,
                        points=[],
                        source_attribution="NASA / JPL Horizons Ephemeris System",
                        is_cached=False,
                        query_duration_ms=elapsed_ms,
                        error_message=err_msg,
                    )

                data = resp.json()
                raw_result = data.get("result", "")

                # Verify presence of valid ephemeris block
                if "$$SOE" not in raw_result or "$$EOE" not in raw_result:
                    # Parse error details if provided by Horizons
                    err_hint = "No ephemeris block ($$SOE) found in Horizons output."
                    if "Cannot interpret" in raw_result or "ERROR" in raw_result:
                        err_hint = raw_result.split("*********************************")[0].strip()[:300]
                    return HorizonsQueryResult(
                        success=False,
                        target=target_name,
                        target_id=t_id,
                        observer_lat=norm_lat,
                        observer_lon=norm_lon,
                        observer_alt_km=norm_alt,
                        start_epoch_iso=start_dt.isoformat(),
                        stop_epoch_iso=stop_dt.isoformat(),
                        step_hours=step_hours,
                        points=[],
                        source_attribution="NASA / JPL Horizons Ephemeris System",
                        is_cached=False,
                        query_duration_ms=elapsed_ms,
                        error_message=err_hint,
                    )

                # Parse data rows between $$SOE and $$EOE
                soe_block = raw_result.split("$$SOE")[1].split("$$EOE")[0].strip()
                parsed_points = self._parse_horizons_block(soe_block, target_name, t_id)

                result_obj = HorizonsQueryResult(
                    success=len(parsed_points) > 0,
                    target=target_name,
                    target_id=t_id,
                    observer_lat=norm_lat,
                    observer_lon=norm_lon,
                    observer_alt_km=norm_alt,
                    start_epoch_iso=start_dt.isoformat(),
                    stop_epoch_iso=stop_dt.isoformat(),
                    step_hours=step_hours,
                    points=parsed_points,
                    source_attribution="NASA JPL Solar System Dynamics (Horizons API DE441)",
                    is_cached=False,
                    query_duration_ms=round(elapsed_ms, 2),
                    error_message=None if len(parsed_points) > 0 else "Ephemeris table contained zero parsable entries.",
                )

                # Store in cache if successful
                if result_obj.success:
                    with self._lock:
                        if len(self._cache) >= self._cache_capacity:
                            self._cache.popitem(last=False)
                        self._cache[cache_key] = (now, result_obj)

                return result_obj

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - query_start) * 1000.0
            logger.error("Horizons API network exception: %s", exc)
            return HorizonsQueryResult(
                success=False,
                target=target_name,
                target_id=t_id,
                observer_lat=norm_lat,
                observer_lon=norm_lon,
                observer_alt_km=norm_alt,
                start_epoch_iso=start_dt.isoformat(),
                stop_epoch_iso=stop_dt.isoformat(),
                step_hours=step_hours,
                points=[],
                source_attribution="NASA / JPL Horizons Ephemeris System",
                is_cached=False,
                query_duration_ms=round(elapsed_ms, 2),
                error_message=f"Network/Connection error querying Horizons: {str(exc)}",
            )

    def _parse_horizons_block(
        self, block: str, target_name: str, target_id: str
    ) -> List[HorizonsEphemerisPoint]:
        """Extracts timestamp, azimuth, elevation, and distance from space-delimited text rows."""
        points: List[HorizonsEphemerisPoint] = []
        lines = block.splitlines()

        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("$$"):
                continue

            # Example lines:
            # 2026-Oct-15 00:00 *   269.434749   1.265884
            # 2026-Oct-15 00:00 *   139.540919  -7.154871  0.00269113676190   0.0250915
            tokens = line_str.split()
            if len(tokens) < 3:
                continue

            # First two tokens are Date and Time (e.g. '2026-Oct-15', '00:00')
            date_token = tokens[0]
            time_token = tokens[1]

            try:
                dt_str = f"{date_token} {time_token}"
                dt_obj = datetime.strptime(dt_str, "%Y-%b-%d %H:%M").replace(tzinfo=timezone.utc)
                iso_str = dt_obj.isoformat()
            except Exception:
                continue

            # Remaining tokens contain flags (*, m, t) followed by floats
            numeric_tokens = []
            for tok in tokens[2:]:
                try:
                    val = float(tok)
                    numeric_tokens.append(val)
                except ValueError:
                    # Ignore single character solar/lunar horizon flags e.g. '*', 'm', 'r'
                    continue

            if len(numeric_tokens) < 2:
                continue

            azimuth = round(numeric_tokens[0], 4)
            elevation = round(numeric_tokens[1], 4)

            dist_au = None
            dist_km = None
            range_rate = None

            if len(numeric_tokens) >= 3:
                dist_au = float(numeric_tokens[2])
                dist_km = round(dist_au * 149_597_870.7, 1)

            if len(numeric_tokens) >= 4:
                range_rate = float(numeric_tokens[3])

            points.append(
                HorizonsEphemerisPoint(
                    epoch_iso=iso_str,
                    target=target_name,
                    target_id=target_id,
                    azimuth_deg=azimuth,
                    elevation_deg=elevation,
                    distance_au=dist_au,
                    distance_km=dist_km,
                    range_rate_km_s=range_rate,
                    apparent_coordinates=True,
                    ref_body="Moon (301)",
                )
            )

        return points

    def query_simultaneous_ephemeris(
        self,
        lat_deg: float,
        lon_deg: float,
        start_dt: datetime,
        duration_days: float = 3.0,
        step_hours: float = 2.0,
        alt_km: float = 0.0,
    ) -> Dict[str, Any]:
        """Queries both Sun and Earth ephemerides simultaneously for full illumination & comm linkage."""
        stop_dt = start_dt + timedelta(days=duration_days)

        sun_res = self.query_observer_ephemeris(
            lat_deg=lat_deg,
            lon_deg=lon_deg,
            target_id="10",
            start_dt=start_dt,
            stop_dt=stop_dt,
            step_hours=step_hours,
            alt_km=alt_km,
        )

        earth_res = self.query_observer_ephemeris(
            lat_deg=lat_deg,
            lon_deg=lon_deg,
            target_id="399",
            start_dt=start_dt,
            stop_dt=stop_dt,
            step_hours=step_hours,
            alt_km=alt_km,
        )

        return {
            "success": sun_res.success and earth_res.success,
            "sun": sun_res.to_dict(),
            "earth": earth_res.to_dict(),
            "observer": {
                "latitude": lat_deg,
                "longitude": lon_deg,
                "altitude_km": alt_km,
            },
            "temporal_window": {
                "start_iso": start_dt.isoformat(),
                "stop_iso": stop_dt.isoformat(),
                "duration_days": duration_days,
                "step_hours": step_hours,
            },
        }


# Global singleton instance
horizons_client = HorizonsClient()
