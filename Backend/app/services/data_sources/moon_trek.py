"""NASA Moon Trek WMTS Map Layers Integration Service.

Provides verified OGC WMTS layer configurations, capabilities discovery, and tile access
for Lunar South Pole polar stereographic mosaics and global basemaps.

Official Documentation: https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=moon
"""

from collections import OrderedDict
from dataclasses import asdict, dataclass
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

import httpx

from app.core.logging import logger

MOON_TREK_API_BASE = "https://trek.nasa.gov/moon/TrekServices/ws/index"


@dataclass
class MoonTrekLayer:
    """Verified NASA Moon Trek WMTS Layer."""

    id: str
    name: str
    description: str
    wmts_endpoint: str
    capabilities_url: str
    tile_url_template: str
    tile_format: str  # "image/png" or "image/jpeg"
    tile_matrix_set: str  # e.g. "default028mm"
    projection: str  # "IAU2000::30120" or "EPSG::104903"
    projection_type: str  # "polar" or "equirectangular"
    resolution_m: float
    min_zoom: int
    max_zoom: int
    bounds: Dict[str, float]  # min_lat, max_lat, min_lon, max_lon
    attribution: str
    default_opacity: float = 1.0
    is_active_default: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Catalog of verified official NASA Moon Trek South Pole and Global layers
VERIFIED_MOON_TREK_LAYERS: List[MoonTrekLayer] = [
    MoonTrekLayer(
        id="trek_wac_global_mosaic",
        name="NASA Moon Trek LROC WAC Global Morphologic Mosaic",
        description="High-resolution global controlled mosaic from LRO Wide Angle Camera at 100 meters/pixel.",
        wmts_endpoint="https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02",
        capabilities_url="https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/WMTSCapabilities.xml",
        tile_url_template="https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
        tile_format="image/jpeg",
        tile_matrix_set="default028mm",
        projection="urn:ogc:def:crs:EPSG::104903",
        projection_type="equirectangular",
        resolution_m=100.0,
        min_zoom=0,
        max_zoom=7,
        bounds={"min_lat": -90.0, "max_lat": 90.0, "min_lon": 0.0, "max_lon": 360.0},
        attribution="NASA / GSFC / Arizona State University / JPL Solar System Treks",
        default_opacity=1.0,
        is_active_default=True,
    ),
    MoonTrekLayer(
        id="trek_nac_south_pole_mosaic",
        name="NASA Moon Trek LROC NAC South Pole Mosaic (1m/pixel)",
        description="High-precision targeted photogrammetric mosaic of the lunar South Pole down to 85.5°S at 1 meter/pixel resolution.",
        wmts_endpoint="https://trek.nasa.gov/tiles/Moon/SP/LRO_NAC_Mosaic_SPole85.5_1mp",
        capabilities_url="https://trek.nasa.gov/tiles/Moon/SP/LRO_NAC_Mosaic_SPole85.5_1mp/1.0.0/WMTSCapabilities.xml",
        tile_url_template="https://trek.nasa.gov/tiles/Moon/SP/LRO_NAC_Mosaic_SPole85.5_1mp/1.0.0/default/default028mm/{z}/{y}/{x}.png",
        tile_format="image/png",
        tile_matrix_set="default028mm",
        projection="urn:ogc:def:crs:IAU2000::30120",
        projection_type="polar",
        resolution_m=1.0,
        min_zoom=0,
        max_zoom=11,
        bounds={"min_lat": -90.0, "max_lat": -85.5, "min_lon": 0.0, "max_lon": 360.0},
        attribution="NASA / GSFC / Arizona State University / LROC Science Team / JPL Moon Trek",
        default_opacity=0.85,
        is_active_default=False,
    ),
    MoonTrekLayer(
        id="trek_lola_count_south_pole",
        name="NASA Moon Trek LOLA Polar Altimetric Coverage",
        description="Altimetric observation laser shot density map for the lunar South Pole (87.5°S to 90°S) at 5 meters/pixel.",
        wmts_endpoint="https://trek.nasa.gov/tiles/Moon/SP/LRO_LOLA_Count_SPole875_5mp_v04",
        capabilities_url="https://trek.nasa.gov/tiles/Moon/SP/LRO_LOLA_Count_SPole875_5mp_v04/1.0.0/WMTSCapabilities.xml",
        tile_url_template="https://trek.nasa.gov/tiles/Moon/SP/LRO_LOLA_Count_SPole875_5mp_v04/1.0.0/default/default028mm/{z}/{y}/{x}.png",
        tile_format="image/png",
        tile_matrix_set="default028mm",
        projection="urn:ogc:def:crs:IAU2000::30120",
        projection_type="polar",
        resolution_m=5.0,
        min_zoom=0,
        max_zoom=9,
        bounds={"min_lat": -90.0, "max_lat": -87.5, "min_lon": 0.0, "max_lon": 360.0},
        attribution="NASA / GSFC / LOLA Science Team / JPL Solar System Treks",
        default_opacity=0.70,
        is_active_default=False,
    ),
]


class MoonTrekService:
    """Manages NASA Moon Trek WMTS layers, capabilities validation, and tile proxy caching."""

    def __init__(self, tile_cache_capacity: int = 128):
        self._layers: Dict[str, MoonTrekLayer] = {l.id: l for l in VERIFIED_MOON_TREK_LAYERS}
        self._tile_cache: OrderedDict[str, Tuple[float, bytes, str]] = OrderedDict()
        self._cache_capacity = tile_cache_capacity
        self._lock = threading.Lock()

    def get_available_layers(self, projection_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns verified Moon Trek layers matching optional projection filter ('polar' or 'equirectangular')."""
        results = []
        for l in self._layers.values():
            if projection_filter and l.projection_type != projection_filter:
                continue
            results.append(l.to_dict())
        return results

    def get_layer_by_id(self, layer_id: str) -> Optional[MoonTrekLayer]:
        return self._layers.get(layer_id)

    def check_capabilities(self, layer_id: str) -> Dict[str, Any]:
        """Performs live HTTP verification of layer's WMTSCapabilities.xml."""
        layer = self.get_layer_by_id(layer_id)
        if not layer:
            return {"verified": False, "error": f"Unknown layer ID '{layer_id}'"}

        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(layer.capabilities_url)
                if resp.status_code == 200 and "Capabilities" in resp.text:
                    return {
                        "layer_id": layer.id,
                        "verified": True,
                        "status_code": 200,
                        "title": layer.name,
                        "format": layer.tile_format,
                        "tile_matrix_set": layer.tile_matrix_set,
                        "projection": layer.projection,
                    }
                else:
                    return {
                        "layer_id": layer.id,
                        "verified": False,
                        "status_code": resp.status_code,
                        "error": "Capabilities document missing or invalid.",
                    }
        except Exception as exc:
            return {
                "layer_id": layer.id,
                "verified": False,
                "error": f"Connection error: {str(exc)}",
            }

    def fetch_tile(self, layer_id: str, z: int, y: int, x: int) -> Tuple[Optional[bytes], str, int]:
        """Fetches a map tile from Moon Trek WMTS or local LRU cache.

        Returns: (tile_bytes, content_type, http_status)
        """
        layer = self.get_layer_by_id(layer_id)
        if not layer:
            return None, "text/plain", 404

        cache_key = f"{layer_id}:{z}:{y}:{x}"

        with self._lock:
            if cache_key in self._tile_cache:
                _, cached_bytes, content_type = self._tile_cache[cache_key]
                self._tile_cache.move_to_end(cache_key)
                return cached_bytes, content_type, 200

        # Construct tile URL according to WMTS template
        tile_url = layer.tile_url_template.format(z=z, y=y, x=x)

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(tile_url)
                if resp.status_code == 200:
                    c_type = resp.headers.get("content-type", layer.tile_format)
                    tile_bytes = resp.content

                    with self._lock:
                        if len(self._tile_cache) >= self._cache_capacity:
                            self._tile_cache.popitem(last=False)
                        self._tile_cache[cache_key] = (time.time(), tile_bytes, c_type)

                    return tile_bytes, c_type, 200
                else:
                    return None, "text/plain", resp.status_code
        except Exception as exc:
            logger.warning("Moon Trek tile fetch error for %s: %s", tile_url, exc)
            return None, "text/plain", 502


moon_trek_service = MoonTrekService()
