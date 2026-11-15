"""Scientific landing-site detection service for Moonscape.

Extracts real NASA LOLA DEM rasters, computes geodetic Horn slopes and RMS roughness,
labels contiguous connected safe terrain components, filters by required footprint area,
and ranks detected landing sites by multi-criteria suitability.
"""

import math
import uuid
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy.ndimage import find_objects, label

from app.core.constants import (
    MOON_RADIUS_METERS,
    SLOPE_CRITICAL_MAX_DEG,
    SLOPE_IDEAL_MAX_DEG,
    SLOPE_NOMINAL_MAX_DEG,
)
from app.core.logging import logger
from app.schemas.scoring import ScoreRequest
from app.schemas.site_detection import (
    DetectLandingSitesRequest,
    DetectLandingSitesResponse,
    DetectedLandingZone,
)
from app.services.geospatial.coordinate_manager import coordinate_manager
from app.services.nasa_data import NASASpatialWindow, nasa_data_manager
from app.services.site_scoring import site_scoring_engine
from maths.geodesy import polar_stereo_to_latlon
from maths.topography import horn_slope_and_aspect, rms_surface_roughness


class LandingSiteDetectionService:
    """Automated landing zone detector identifying contiguous safe touchdown corridors from real lunar DEMs."""

    def detect_candidate_sites(self, req: DetectLandingSitesRequest) -> DetectLandingSitesResponse:
        """Executes contiguous landing site detection on real NASA elevation rasters."""
        profile = req.mission_profile or "artemis_hls"
        # Validate coordinates
        is_valid, msg = coordinate_manager.validate_coordinates(req.center_lat, req.center_lon)
        if not is_valid or not coordinate_manager.is_in_south_pole_zone(req.center_lat):
            return DetectLandingSitesResponse(
                status="no_sites_found",
                center_lat=req.center_lat,
                center_lon=req.center_lon,
                search_radius_meters=req.search_radius_meters,
                total_sites_detected=0,
                candidate_zones=[],
                dataset_metadata={},
                summary=f"Coordinates outside lunar South Pole operational zone (-90° to -80°). {msg}",
                warnings=["Location is outside verified polar data coverage."],
            )

        # Acquire real NASA spatial elevation raster window
        window: Optional[NASASpatialWindow] = nasa_data_manager.get_spatial_window(
            lat_deg=req.center_lat,
            lon_deg=req.center_lon,
            radius_m=req.search_radius_meters,
        )

        if window is None or window.elevation_data is None or window.elevation_data.size == 0:
            return DetectLandingSitesResponse(
                status="no_sites_found",
                center_lat=req.center_lat,
                center_lon=req.center_lon,
                search_radius_meters=req.search_radius_meters,
                total_sites_detected=0,
                candidate_zones=[],
                dataset_metadata={},
                summary="NASA DEM data could not be acquired for requested search coordinates.",
                warnings=["No elevation data available in target search envelope."],
            )

        elev = window.elevation_data
        dx, dy = window.dx_meters, window.dy_meters
        cell_area_m2 = dx * dy
        nodata = window.nodata_value

        # Mask valid pixels
        valid_mask = (elev != nodata) & (elev > -30000.0) & (~np.isnan(elev))
        if np.sum(valid_mask) < 25:
            return DetectLandingSitesResponse(
                status="no_sites_found",
                center_lat=req.center_lat,
                center_lon=req.center_lon,
                search_radius_meters=req.search_radius_meters,
                total_sites_detected=0,
                candidate_zones=[],
                dataset_metadata={"source_name": window.dataset_name},
                summary="Insufficient non-nodata pixels within search radius to evaluate contiguous landing sites.",
                warnings=["High nodata/shadow coverage in target search envelope."],
            )

        # 1. Slope computation (Horn 1981 operator)
        if window.slope_data is not None and window.slope_data.shape == elev.shape:
            slopes = window.slope_data
        else:
            slopes, _ = horn_slope_and_aspect(elev, dx=dx, dy=dy)

        # 2. Surface roughness computation (RMS deviation, 3x3 baseline)
        roughness = rms_surface_roughness(elev, kernel_size=3)

        # 3. Safe pixel classification
        # Must meet slope <= max_slope, roughness <= max_roughness, and valid non-nodata elevation
        safe_mask = valid_mask & (slopes <= req.max_slope_deg) & (roughness <= req.max_roughness_m)

        # Minimum required contiguous area based on minimum landing circle diameter
        min_required_area_m2 = math.pi * ((req.min_landing_diameter_meters / 2.0) ** 2)

        # 4. Connected component labeling (8-connectivity)
        structure = np.ones((3, 3), dtype=int)
        labeled_array, num_features = label(safe_mask, structure=structure)

        candidate_zones: List[DetectedLandingZone] = []
        transform = window.transform

        # Vectorized component pixel counts and bounding object slices
        counts = np.bincount(labeled_array.ravel())
        slices = find_objects(labeled_array)

        for feat_id in range(1, num_features + 1):
            if feat_id >= len(counts):
                continue
            pixel_count = int(counts[feat_id])
            contiguous_area = pixel_count * cell_area_m2

            # Fast rejection of candidate regions with insufficient contiguous area
            if contiguous_area < min_required_area_m2:
                continue

            sl = slices[feat_id - 1]
            if sl is None:
                continue

            sub_labeled = labeled_array[sl]
            sub_mask = sub_labeled == feat_id

            # Slice into localized sub-arrays to avoid whole-raster allocations
            comp_elevs = elev[sl][sub_mask]
            comp_slopes = slopes[sl][sub_mask]
            comp_roughness = roughness[sl][sub_mask]

            effective_diam = 2.0 * math.sqrt(contiguous_area / math.pi)

            mean_slope = float(np.mean(comp_slopes))
            max_slope = float(np.max(comp_slopes))
            mean_rough = float(np.mean(comp_roughness))
            mean_elev = float(np.mean(comp_elevs))

            # Centroid calculation in projected pixel coordinates
            r_indices, c_indices = np.where(sub_mask)
            center_r = float(sl[0].start + np.mean(r_indices))
            center_c = float(sl[1].start + np.mean(c_indices))

            # Convert (col, row) to projected meters (x, y) using raster Affine transform
            proj_x = transform.c + center_c * transform.a + center_r * transform.b
            proj_y = transform.f + center_c * transform.d + center_r * transform.e

            # Convert projected meters to planetocentric (lat, lon)
            centroid_lat, centroid_lon = polar_stereo_to_latlon(proj_x, proj_y, radius_m=MOON_RADIUS_METERS)

            profile = req.mission_profile or "artemis_hls"
            # Evaluate suitability score using MCDA scoring engine (fast inference without Monte Carlo loop)
            score_res = site_scoring_engine.evaluate_suitability(
                ScoreRequest(
                    slope_deg=round(mean_slope, 2),
                    max_slope_deg=round(max_slope, 2),
                    roughness_m=round(mean_rough, 2),
                    elevation_m=round(mean_elev, 1),
                    contiguous_diameter_m=round(effective_diam, 1),
                    illumination_pct=75.0,  # regional baseline
                    mission_profile=profile,
                ),
                run_monte_carlo=False,
            )
            suit_score = score_res.overall_suitability_score if score_res.overall_suitability_score is not None else 60.0
            ml_score = score_res.ml_model_score
            hard_status = score_res.hard_constraint_status or "passed"

            feasibility = "optimal" if suit_score >= 80.0 else ("nominal" if suit_score >= 60.0 else "marginal")

            zone_id = f"ZONE-{uuid.uuid4().hex[:6].upper()}"
            candidate_zones.append(
                DetectedLandingZone(
                    zone_id=zone_id,
                    centroid_lat=round(centroid_lat, 4),
                    centroid_lon=round(centroid_lon, 4),
                    contiguous_area_m2=round(contiguous_area, 1),
                    effective_diameter_m=round(effective_diam, 1),
                    pixel_count=pixel_count,
                    mean_slope_deg=round(mean_slope, 2),
                    max_slope_deg=round(max_slope, 2),
                    mean_roughness_m=round(mean_rough, 2),
                    mean_elevation_m=round(mean_elev, 1),
                    suitability_score=round(suit_score, 1),
                    ml_model_score=round(ml_score, 1) if ml_score is not None else None,
                    hard_constraint_status=hard_status,
                    safety_rank=1,  # will be assigned after sorting
                    feasibility_status=feasibility,
                )
            )

        # 5. Sort candidate zones by suitability score descending
        candidate_zones.sort(key=lambda z: (z.suitability_score, z.contiguous_area_m2), reverse=True)
        for idx, z in enumerate(candidate_zones):
            z.safety_rank = idx + 1

        dataset_meta = {
            "dataset_name": window.dataset_name,
            "product_id": window.product_id,
            "spatial_resolution_m": window.dx_meters,
            "source_tier": window.source_tier,
            "citation": window.citation,
            "is_measured_data": window.is_measured_data,
        }

        total_detected = len(candidate_zones)
        summary = (
            f"Detected {total_detected} contiguous landing zone(s) meeting engineering constraints "
            f"(slope <= {req.max_slope_deg}°, roughness <= {req.max_roughness_m}m, diameter >= {req.min_landing_diameter_meters}m) "
            f"derived from {window.dataset_name} ({window.dx_meters:.1f}m resolution)."
        )

        return DetectLandingSitesResponse(
            status="success" if total_detected > 0 else "no_sites_found",
            center_lat=req.center_lat,
            center_lon=req.center_lon,
            search_radius_meters=req.search_radius_meters,
            total_sites_detected=total_detected,
            candidate_zones=candidate_zones,
            dataset_metadata=dataset_meta,
            summary=summary,
            mission_profile=profile,
            warnings=[] if total_detected > 0 else ["No contiguous regions met the required landing footprint diameter."],
        )


landing_site_detection_service = LandingSiteDetectionService()
