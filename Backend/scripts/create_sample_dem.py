"""Utility script to generate a scientifically accurate synthetic NASA LOLA Lunar South Pole DEM GeoTIFF.

Projection: Lunar South Pole Stereographic
Reference Sphere: Moon 2000 (Radius = 1,737,400 m)
Coverage: Latitudes -80.0 to -90.0 (Lunar South Pole)
"""

import math
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS

MOON_RADIUS = 1_737_400.0
NODATA_VALUE = -32768.0


def latlon_to_polar_stereo(lat_deg: float, lon_deg: float) -> tuple[float, float]:
    """Converts planetocentric lat/lon to South Pole Stereographic (x, y) meters."""
    lat_rad = math.radians(lat_deg)
    lon_rad = math.radians(lon_deg)
    # Polar stereographic true at -90 deg
    colat_rad = math.pi / 2.0 + lat_rad  # colatitude from south pole (0 at -90)
    r = 2.0 * MOON_RADIUS * math.tan(colat_rad / 2.0)
    x = r * math.sin(lon_rad)
    y = -r * math.cos(lon_rad)
    return x, y


def generate_lunar_dem(output_path: Path) -> None:
    """Generates a realistic lunar South Pole elevation model and writes to GeoTIFF."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Grid parameters
    width = 1000
    height = 1000
    pixel_size = 620.0  # meters per pixel (~620km span, covering -80 to -90 deg)

    # Origin at top-left
    x_min = -(width * pixel_size) / 2.0
    y_max = (height * pixel_size) / 2.0
    transform = from_origin(x_min, y_max, pixel_size, pixel_size)

    # Coordinate grids in projected meters
    xs = x_min + np.arange(width) * pixel_size
    ys = y_max - np.arange(height) * pixel_size
    xx, yy = np.meshgrid(xs, ys)
    rr = np.sqrt(xx**2 + yy**2)

    # Baseline elevation: South Pole-Aitken Basin regional slope (~ -1500m to +500m)
    elevation = -1200.0 + (xx * 0.001) - (yy * 0.0015)

    # Add multiscale topographic roughness (simulating ancient lunar impact bombardment)
    np.random.seed(42)
    for freq, amp in [(0.00002, 400.0), (0.00008, 150.0), (0.0003, 50.0), (0.001, 15.0)]:
        phase_x = np.random.uniform(0, 2 * np.pi)
        phase_y = np.random.uniform(0, 2 * np.pi)
        elevation += amp * (np.sin(xx * freq + phase_x) * np.cos(yy * freq + phase_y))

    # Craters and Peaks Definition: (lat, lon, radius_m, depth_m, is_peak)
    features = [
        # Shackleton Crater (South Pole, 21 km diameter, 4.2 km deep)
        (-89.9, 0.0, 10500.0, 4200.0, False),
        # Malapert Mountain (Alpha Massif, prominent elevation peak +3500m)
        (-84.9, 12.9, 25000.0, 3200.0, True),
        # Nobile Crater (73 km diameter, 3.5 km deep)
        (-85.2, 35.8, 36500.0, 3500.0, False),
        # Haworth Crater (35 km diameter, 3.8 km deep cold trap)
        (-87.4, -5.1, 17500.0, 3800.0, False),
        # Faustini Crater (39 km diameter, 3.4 km deep)
        (-87.1, 77.0, 19500.0, 3400.0, False),
        # Amundsen Crater (103 km diameter, 4.5 km deep)
        (-84.5, 82.8, 51500.0, 4500.0, False),
        # de Gerlache Crater (32 km diameter, 3.2 km deep)
        (-88.5, -88.3, 16000.0, 3200.0, False),
        # Connecting Ridge elevated crest
        (-89.44, 222.5, 8000.0, 800.0, True),
        # Leibnitz Beta Plateau elevated highland
        (-85.8, 30.5, 30000.0, 2500.0, True),
    ]

    for lat, lon, radius, height_delta, is_peak in features:
        cx, cy = latlon_to_polar_stereo(lat, lon)
        dist = np.sqrt((xx - cx)**2 + (yy - cy)**2)
        mask = dist < (radius * 1.8)

        norm_dist = dist[mask] / radius
        if is_peak:
            # Gaussian bell peak
            elev_contrib = height_delta * np.exp(-((norm_dist * 1.5)**2))
            elevation[mask] += elev_contrib
        else:
            # Impact crater profile: parabolic bowl with raised rim
            crater_profile = np.zeros_like(norm_dist)
            # Crater floor / bowl
            bowl_mask = norm_dist <= 1.0
            crater_profile[bowl_mask] = -height_delta * (1.0 - (norm_dist[bowl_mask] ** 2))
            # Raised rim (ejecta crest)
            rim_mask = (norm_dist > 0.8) & (norm_dist < 1.6)
            crater_profile[rim_mask] += (height_delta * 0.18) * np.sin((norm_dist[rim_mask] - 0.8) / 0.8 * np.pi)
            elevation[mask] += crater_profile

    # Outer polar bounds: anything beyond 80 deg South is outside this product extent (set to LOLA nodata)
    max_radius_m = 305_000.0  # Distance from pole to 80 deg South
    outside_coverage = rr > max_radius_m
    elevation[outside_coverage] = NODATA_VALUE

    elevation = elevation.astype(np.float32)

    # South Pole Stereographic CRS
    crs = CRS.from_proj4("+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +R=1737400 +units=m +no_defs")

    # Write GeoTIFF with LZW compression
    with rasterio.open(
        output_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=np.float32,
        crs=crs,
        transform=transform,
        nodata=NODATA_VALUE,
        compress="lzw",
    ) as dst:
        dst.write(elevation, 1)

    print(f"Sample Lunar DEM created successfully at: {output_path}")
    print(f"Dimensions: {width}x{height}, Pixel size: {pixel_size}m, CRS: {crs}")


if __name__ == "__main__":
    generate_lunar_dem(Path("data/sample_dem.tif"))
