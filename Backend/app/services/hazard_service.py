"""Hazard detection and prediction service for lunar touchdown corridors.

Integrates authentic NASA LROC NAC polar optical frames with trained YOLOv8n ML inference,
combined with LOLA DEM morphological depression, slope escarpment, and roughness analysis.
"""

import base64
import io
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

import numpy as np
from PIL import Image

from app.core.config import settings
from app.core.constants import (
    BOULDER_HAZARD_THRESHOLD_M,
    CRATER_HAZARD_MIN_DIAMETER_M,
    LOLA_NODATA_VALUE,
    MOON_RADIUS_METERS,
    SCIENTIFIC_SAFETY_DISCLAIMER,
    SLOPE_CRITICAL_MAX_DEG,
    SLOPE_NOMINAL_MAX_DEG,
)
from app.core.logging import logger
from app.schemas.hazard import (
    BoundingBox,
    DetectionItem,
    HazardItem,
    HazardPredictRequest,
    HazardPredictResponse,
)
from app.services.dem_service import dem_service
from app.services.hazard_detection import APOLLO_DOMAIN_LIMITATION, hazard_detection_service
from app.services.terrain_service import terrain_service
from app.services.geospatial.coordinate_manager import coordinate_manager
from app.services.nasa_data import nasa_data_manager
from maths.curvature import laplacian_curvature, detect_crater_basins


class HazardService:
    """Detects and predicts physical landing hazards using elevation curvature, gradient anomalies, and surface models."""

    def __init__(self) -> None:
        self._manifest: Optional[List[Dict[str, Any]]] = None
        base = getattr(settings, "BASE_DIR", Path(__file__).resolve().parent.parent.parent)
        self._manifest_path = base / "data" / "hazard_dataset" / "metadata_manifest.json"
        self._images_dir = base / "data" / "hazard_dataset" / "images"

    def _get_manifest(self) -> List[Dict[str, Any]]:
        """Loads metadata manifest of calibrated NASA/ISRO polar optical image tiles."""
        if self._manifest is None:
            if self._manifest_path.exists():
                try:
                    with open(self._manifest_path, "r", encoding="utf-8") as f:
                        self._manifest = json.load(f)
                except Exception as err:
                    logger.warning("Failed to load hazard dataset metadata manifest: %s", str(err))
                    self._manifest = []
            else:
                self._manifest = []
        return self._manifest

    def find_covering_optical_tile(self, lat: float, lon: float) -> Optional[Tuple[Dict[str, Any], Path]]:
        """Searches catalog of calibrated LROC NAC / OHRC polar tiles for an authentic frame encompassing coordinate."""
        norm_lon = coordinate_manager.normalize_longitude(lon, target_range="360")
        manifest = self._get_manifest()

        # 1. Exact bounding box intersection
        for item in manifest:
            b_lat = item.get("latitude_bounds", [-90, -80])
            b_lon = item.get("longitude_bounds", [0, 360])
            split = item.get("split", "train")
            sample_id = item.get("sample_id")

            if b_lon[0] > b_lon[1]:
                lon_match = (norm_lon >= b_lon[0]) or (norm_lon <= b_lon[1])
            else:
                lon_match = min(b_lon) <= norm_lon <= max(b_lon)

            lat_match = min(b_lat) <= lat <= max(b_lat)

            if lat_match and lon_match:
                tile_p = self._images_dir / split / f"{sample_id}.png"
                if tile_p.exists():
                    matched_item = dict(item)
                    matched_item["coverage_state"] = "exact_frame_processed"
                    return matched_item, tile_p

        # 2. Proximity search (within 5 km of tile centroid for marginal coverage)
        for item in manifest:
            b_lat = item.get("latitude_bounds", [-90, -80])
            b_lon = item.get("longitude_bounds", [0, 360])
            c_lat = (b_lat[0] + b_lat[1]) / 2.0
            c_lon = (b_lon[0] + b_lon[1]) / 2.0
            dist_m = coordinate_manager.surface_distance_m(lat, norm_lon, c_lat, c_lon)
            if dist_m <= 5000.0:
                split = item.get("split", "train")
                sample_id = item.get("sample_id")
                tile_p = self._images_dir / split / f"{sample_id}.png"
                if tile_p.exists():
                    matched_item = dict(item)
                    matched_item["coverage_state"] = "proximity_frame_cataloged"
                    return matched_item, tile_p

        return None

    def predict_hazards(self, req: HazardPredictRequest) -> HazardPredictResponse:
        """Executes full hazard evaluation across both optical high-resolution imagery and DEM morphology."""
        # Route pure image requests directly to ML detection service
        if (req.image_base64 is not None or req.image_path is not None) and (req.center_lat is None or req.center_lon is None):
            return hazard_detection_service.predict(req)

        assessment_id = f"HAZ-{uuid.uuid4().hex[:8].upper()}"
        target_lat = req.center_lat if req.center_lat is not None else -89.5
        target_lon = req.center_lon if req.center_lon is not None else 0.0
        target_radius = req.radius_meters if req.radius_meters is not None else 1000.0
        boulder_sens = req.boulder_detection_sensitivity if req.boulder_detection_sensitivity is not None else 0.7
        min_crater_dia = req.min_crater_diameter_m if req.min_crater_diameter_m is not None else 5.0

        coverage_zone = coordinate_manager.get_coverage_zone(target_lat)
        warnings: List[str] = []

        # Coordinate boundary check
        if coverage_zone in ["outside", "invalid"]:
            return HazardPredictResponse(
                status="not_available",
                detections=[],
                crater_count=None,
                rock_count=None,
                warnings=[f"Coordinates ({target_lat}°, {target_lon}°) are outside the configured lunar South Pole exploration region (-90° to -70°)."],
                model_name=None,
                model_version=None,
                limitations=APOLLO_DOMAIN_LIMITATION,
                hazard_assessment_id=assessment_id,
                center_lat=target_lat,
                center_lon=target_lon,
                radius_meters=target_radius,
                total_hazards_detected=0,
                coverage_zone=coverage_zone,
                optical_status="outside_coverage",
                disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
            )

        # ------------------------------------------------------------------
        # 1. OPTICAL IMAGERY & MACHINE LEARNING INFERENCE
        # ------------------------------------------------------------------
        optical_match = self.find_covering_optical_tile(target_lat, target_lon)
        optical_detections: List[DetectionItem] = []
        optical_craters: Optional[List[HazardItem]] = None
        optical_rocks: Optional[List[HazardItem]] = None
        optical_overlay: Optional[str] = None
        optical_product_id: Optional[str] = None
        optical_res_m: Optional[float] = None
        optical_status: str = "not_available"

        if not hazard_detection_service.is_available():
            # Attempt to lazy load weights if unconfigured
            hazard_detection_service.load_model()

        if optical_match and hazard_detection_service.is_available():
            tile_meta, tile_img_path = optical_match
            try:
                pil_img = Image.open(tile_img_path)
                res_mpp = float(tile_meta.get("resolution_mpp", 1.2))
                optical_product_id = tile_meta.get("product_id")
                optical_res_m = res_mpp

                # Execute ML optical inference
                ml_req = HazardPredictRequest(
                    image_path=str(tile_img_path),
                    spatial_resolution_mpp=res_mpp,
                    confidence_threshold=req.confidence_threshold or 0.25,
                )
                ml_resp = hazard_detection_service.predict(ml_req)

                optical_detections = ml_resp.detections
                optical_overlay = ml_resp.overlay_image
                optical_status = "success"

                # Georeference detections into lunar coordinates
                b_lat = tile_meta.get("latitude_bounds", [target_lat, target_lat])
                b_lon = tile_meta.get("longitude_bounds", [target_lon, target_lon])
                img_w, img_h = pil_img.size

                craters_list: List[HazardItem] = []
                rocks_list: List[HazardItem] = []

                for d in optical_detections:
                    if d.center_pixel:
                        py, px = d.center_pixel
                    elif d.bounding_box:
                        py = (d.bounding_box.ymin + d.bounding_box.ymax) / 2.0
                        px = (d.bounding_box.xmin + d.bounding_box.xmax) / 2.0
                    else:
                        py, px = img_h / 2.0, img_w / 2.0

                    # Linear geodetic mapping within tile bounds
                    d_lat = max(b_lat) - (py / max(1, img_h)) * (max(b_lat) - min(b_lat))
                    d_lon = min(b_lon) + (px / max(1, img_w)) * (max(b_lon) - min(b_lon))
                    is_crater = d.label.lower() == "crater"
                    feat_id = f"CR-{len(craters_list) + 1:02d}" if is_crater else f"RK-{len(rocks_list) + 1:02d}"
                    feat_sz = d.estimated_size_m or 0.0

                    h_item = HazardItem(
                        id=feat_id,
                        hazard_type="crater" if is_crater else "boulder",
                        latitude=round(d_lat, 5),
                        longitude=round(d_lon, 5),
                        estimated_size_m=feat_sz,
                        measurement_name="Feature Diameter" if is_crater else "Bounding Span",
                        measurement_unit="m",
                        measurement_value=feat_sz,
                        severity=d.severity or "medium",
                        confidence_score=round(float(d.confidence), 4),
                        confidence_type="model_confidence",
                        detection_method="YOLOv8n Polar Neural Detector",
                        source=f"LROC_optical_{optical_product_id}",
                    )
                    if is_crater:
                        craters_list.append(h_item)
                    else:
                        rocks_list.append(h_item)

                optical_craters = craters_list
                optical_rocks = rocks_list

            except Exception as e:
                logger.error("Optical hazard inference failed on tile %s: %s", tile_img_path, str(e))
                optical_status = "error"
                warnings.append(f"Optical inference failed on intersecting image frame: {str(e)}")
        else:
            optical_status = "not_available"
            warnings.append("Detection imagery unavailable — no georeferenced optical analysis was performed for this location.")

        # ------------------------------------------------------------------
        # 2. DIGITAL ELEVATION MODEL (DEM) TOPOGRAPHIC MORPHOLOGY
        # ------------------------------------------------------------------
        window = nasa_data_manager.get_spatial_window(
            lat_deg=target_lat,
            lon_deg=target_lon,
            radius_m=target_radius,
        )

        if window is None or window.elevation_data is None or window.elevation_data.size == 0:
            elev_data, transform, res = dem_service.read_window_around_point(
                lat_deg=target_lat,
                lon_deg=target_lon,
                radius_m=target_radius,
            )
            slope_data = None
            is_measured = False
            dataset_name = "Calibrated Sample Baseline DEM"
            source_tier = "Tier 0 (Calibrated Sample Baseline)"
        else:
            elev_data = window.elevation_data
            slope_data = window.slope_data
            transform = window.transform
            res = (window.dx_meters, window.dy_meters)
            is_measured = window.is_measured_data
            dataset_name = window.dataset_name
            source_tier = window.source_tier

        if not is_measured:
            warnings.append("Operating on calibrated baseline synthetic DEM. Morphological hazard features are simulated and not verified NASA observations.")

        topographic_hazards: List[HazardItem] = []
        steep_count = 0
        shadow_pct = 0.0

        if elev_data is not None and elev_data.size >= 4:
            valid_mask = (elev_data != LOLA_NODATA_VALUE) & (elev_data > -30000) & (~np.isnan(elev_data))
            if np.sum(valid_mask) >= 4:
                dx = res[0] if res[0] > 0 else 620.0
                dy = res[1] if res[1] > 0 else 620.0
                rows, cols = elev_data.shape

                if slope_data is not None and slope_data.shape == elev_data.shape:
                    slopes = slope_data
                else:
                    slopes, _ = terrain_service.calculate_slope_and_aspect(elev_data, dx, dy)
                roughness = terrain_service.calculate_roughness_rms(elev_data)
                curvature = laplacian_curvature(elev_data)

                def _cell_to_latlon(r_idx: int, c_idx: int, off_x: float, off_y: float) -> Tuple[float, float]:
                    if transform is not None:
                        px = transform.c + (c_idx + 0.5) * transform.a + (r_idx + 0.5) * transform.b
                        py = transform.f + (c_idx + 0.5) * transform.d + (r_idx + 0.5) * transform.e
                        calc_lat, calc_lon = coordinate_manager.from_polar_stereographic(px, py)
                        return round(calc_lat, 5), round(calc_lon, 5)
                    m_per_deg_lat = MOON_RADIUS_METERS * math.pi / 180.0
                    m_per_deg_lon = m_per_deg_lat * max(0.005, math.cos(math.radians(target_lat)))
                    return round(target_lat + (off_y / m_per_deg_lat), 5), round(target_lon + (off_x / m_per_deg_lon), 5)

                # A. Large DEM-derived depression candidates (diameter >= 2*dx)
                crater_mask = valid_mask & detect_crater_basins(curvature, threshold=15.0)
                crater_indices = np.argwhere(crater_mask)
                sampled_craters = []
                if len(crater_indices) > 0:
                    selected_basin_coords = []
                    for r, c in crater_indices:
                        offset_y = (rows // 2 - r) * dy
                        offset_x = (c - cols // 2) * dx
                        dist = math.sqrt(offset_x**2 + offset_y**2)
                        if dist > target_radius:
                            continue
                        too_close = False
                        for prev_r, prev_c in selected_basin_coords:
                            if math.sqrt((r - prev_r)**2 + (c - prev_c)**2) * dx < (3.0 * dx):
                                too_close = True
                                break
                        if not too_close:
                            selected_basin_coords.append((r, c))
                            sampled_craters.append((r, c))
                            if len(sampled_craters) >= 6:
                                break

                for dep_idx, (r, c) in enumerate(sampled_craters, start=1):
                    offset_y = (rows // 2 - r) * dy
                    offset_x = (c - cols // 2) * dx
                    raw_dia = float(np.abs(curvature[r, c]) * 1.8)
                    est_dia = raw_dia if raw_dia >= (2.0 * dx) else None
                    h_lat, h_lon = _cell_to_latlon(r, c, offset_x, offset_y)
                    conf = min(0.92, max(0.40, float(curvature[r, c] / 50.0)))
                    dia_val = round(est_dia, 1) if est_dia is not None else 0.0

                    topographic_hazards.append(
                        HazardItem(
                            id=f"DEP-{dep_idx:02d}",
                            hazard_type="morphological_depression",
                            latitude=h_lat,
                            longitude=h_lon,
                            estimated_size_m=dia_val,
                            measurement_name="Basin Diameter",
                            measurement_unit="m",
                            measurement_value=dia_val,
                            severity="high" if (est_dia and est_dia > 50.0) else "medium",
                            confidence_score=round(conf, 2),
                            confidence_type="heuristic_indicator",
                            detection_method="DEM Laplacian Curvature",
                            source="DEM_Laplacian_curvature",
                        )
                    )

                # B. Surface roughness obstacle risk (Grouped / spatially separated patches)
                roughness_threshold = 0.5 * (1.0 / boulder_sens)
                rough_mask = valid_mask & (roughness > roughness_threshold)
                rough_indices = np.argwhere(rough_mask)
                sampled_rough = []
                if len(rough_indices) > 0:
                    selected_rough_coords = []
                    sorted_rough = sorted(rough_indices, key=lambda rc: roughness[rc[0], rc[1]], reverse=True)
                    for r, c in sorted_rough:
                        offset_y = (rows // 2 - r) * dy
                        offset_x = (c - cols // 2) * dx
                        dist = math.sqrt(offset_x**2 + offset_y**2)
                        if dist > target_radius:
                            continue
                        too_close = False
                        for prev_r, prev_c in selected_rough_coords:
                            if math.sqrt((r - prev_r)**2 + (c - prev_c)**2) * dx < max(100.0, 3.0 * dx):
                                too_close = True
                                break
                        if not too_close:
                            selected_rough_coords.append((r, c))
                            sampled_rough.append((r, c))
                            if len(sampled_rough) >= 4:
                                break

                for rough_idx, (r, c) in enumerate(sampled_rough, start=1):
                    offset_y = (rows // 2 - r) * dy
                    offset_x = (c - cols // 2) * dx
                    r_val = float(roughness[r, c])
                    h_lat, h_lon = _cell_to_latlon(r, c, offset_x, offset_y)
                    r_num = round(r_val, 2)
                    conf = round(min(0.88, 0.50 + (r_val / 5.0)), 2)

                    topographic_hazards.append(
                        HazardItem(
                            id=f"ROUGH-{rough_idx:02d}",
                            hazard_type="surface_roughness_anomaly",
                            latitude=h_lat,
                            longitude=h_lon,
                            estimated_size_m=r_num,
                            measurement_name="RMS Surface Roughness",
                            measurement_unit="m",
                            measurement_value=r_num,
                            severity="high" if r_val > 1.0 else "medium",
                            confidence_score=conf,
                            confidence_type="heuristic_indicator",
                            detection_method="DEM RMS Height Deviation",
                            source="DEM_RMS_roughness",
                        )
                    )

                # C. Steep slope cells (> 15 deg) — Grouped into physical escarpment features
                steep_mask = valid_mask & (slopes > SLOPE_CRITICAL_MAX_DEG)
                steep_count = int(np.sum(steep_mask))
                if steep_count > 0:
                    labeled_array, num_features = None, 0
                    try:
                        import scipy.ndimage
                        labeled_array, num_features = scipy.ndimage.label(steep_mask, structure=np.ones((3, 3)))
                    except Exception as nd_err:
                        logger.warning("scipy.ndimage unavailable for escarpment clustering: %s", nd_err)

                    escarpment_components = []
                    if labeled_array is not None and num_features > 0:
                        for feat_id in range(1, num_features + 1):
                            comp = (labeled_array == feat_id)
                            c_count = int(np.sum(comp))
                            if c_count == 0:
                                continue
                            comp_slopes = np.where(comp, slopes, -1.0)
                            peak_r, peak_c = np.unravel_index(np.argmax(comp_slopes), slopes.shape)
                            pk_slope = float(slopes[peak_r, peak_c])
                            mn_slope = float(np.mean(slopes[comp]))
                            offset_y = (rows // 2 - peak_r) * dy
                            offset_x = (peak_c - cols // 2) * dx
                            dist = math.sqrt(offset_x**2 + offset_y**2)
                            feat_extent = math.sqrt(c_count * dx * dy)
                            if dist > (target_radius + max(100.0, feat_extent / 2.0)):
                                continue
                            pk_lat, pk_lon = _cell_to_latlon(peak_r, peak_c, offset_x, offset_y)
                            escarpment_components.append({
                                "cell_count": c_count,
                                "peak_slope": pk_slope,
                                "mean_slope": mn_slope,
                                "extent_m": feat_extent,
                                "lat": pk_lat,
                                "lon": pk_lon,
                                "dist": dist,
                            })
                        escarpment_components.sort(key=lambda f: (f["peak_slope"], f["cell_count"]), reverse=True)
                    else:
                        steep_indices = np.argwhere(steep_mask)
                        selected_steep = []
                        for r, c in steep_indices:
                            offset_y = (rows // 2 - r) * dy
                            offset_x = (c - cols // 2) * dx
                            dist = math.sqrt(offset_x**2 + offset_y**2)
                            if dist > target_radius:
                                continue
                            too_close = False
                            for prev_r, prev_c in selected_steep:
                                if math.sqrt((r - prev_r)**2 + (c - prev_c)**2) * dx < max(150.0, 3.0 * dx):
                                    too_close = True
                                    break
                            if not too_close:
                                selected_steep.append((r, c))
                                pk_lat, pk_lon = _cell_to_latlon(r, c, offset_x, offset_y)
                                escarpment_components.append({
                                    "cell_count": 1,
                                    "peak_slope": float(slopes[r, c]),
                                    "mean_slope": float(slopes[r, c]),
                                    "extent_m": float(dx),
                                    "lat": pk_lat,
                                    "lon": pk_lon,
                                    "dist": dist,
                                })

                    for esc_idx, esc in enumerate(escarpment_components[:4], start=1):
                        pk_slope = round(esc["peak_slope"], 1)
                        sev = "critical" if pk_slope >= 20.0 else "high"
                        topographic_hazards.append(
                            HazardItem(
                                id=f"ESC-{esc_idx:02d}",
                                hazard_type="escarpment",
                                latitude=esc["lat"],
                                longitude=esc["lon"],
                                estimated_size_m=pk_slope,
                                measurement_name="Peak Slope Gradient",
                                measurement_unit="deg",
                                measurement_value=pk_slope,
                                feature_extent_m=round(esc["extent_m"], 1),
                                cell_count=esc["cell_count"],
                                severity=sev,
                                confidence_score=1.0,
                                confidence_type="deterministic_gradient",
                                detection_method="DEM Horn 8-Neighbor Slope Gradient",
                                source="DEM_Horn_slope",
                            )
                        )

                # Shadow coverage
                shadow_cells = np.sum(valid_mask & (elev_data < -2500.0))
                shadow_pct = round(float(shadow_cells / np.sum(valid_mask) * 100.0), 1)

        # ------------------------------------------------------------------
        # 3. OVERALL HAZARD LEVEL & STATUS DETERMINATION
        # ------------------------------------------------------------------
        all_hazards = (optical_craters or []) + (optical_rocks or []) + topographic_hazards
        num_craters = len(optical_craters) if optical_craters is not None else 0
        num_rocks = len(optical_rocks) if optical_rocks is not None else 0

        if steep_count > 10 or any(h.severity == "critical" for h in all_hazards):
            overall_level = "critical"
        elif num_craters > 15 or num_rocks > 10 or steep_count > 3:
            overall_level = "high"
        elif num_craters > 0 or num_rocks > 0 or len(topographic_hazards) > 0:
            overall_level = "moderate"
        else:
            overall_level = "low"

        # Explicit status semantics: never return false success on missing data
        if optical_status == "success" and is_measured:
            final_status = "success"
        elif optical_status == "success" or is_measured:
            final_status = "partial"
        elif elev_data is not None and elev_data.size > 0:
            final_status = "partial"
        else:
            final_status = "insufficient_data"

        # Documented model metadata — removes unsupported 0.88 / 0.94 claims
        ml_meta = hazard_detection_service.get_metadata()
        model_eval_metadata = {
            "model_architecture": ml_meta.get("architecture", "YOLOv8n-Detection"),
            "model_version": ml_meta.get("version", "1.0.0"),
            "model_parameters": ml_meta.get("parameters", "3.0M"),
            "optical_inference_status": optical_status,
            "source_product_id": optical_product_id or dataset_name,
            "source_resolution_mpp": optical_res_m or (res[0] if 'res' in locals() else None),
            "evaluation_metrics": ml_meta.get("evaluation_metrics", {}),
            "performance_benchmarks": ml_meta.get("performance_benchmarks", {}),
            "operational_limitations": ml_meta.get("operational_limitations", {}),
            "evaluation_caveat": APOLLO_DOMAIN_LIMITATION,
            "terrain_elevation_tier": source_tier,
            "is_measured_dem_data": is_measured,
        }

        return HazardPredictResponse(
            status=final_status,
            detections=optical_detections,
            crater_count=len(optical_craters) if optical_craters is not None else None,
            rock_count=len(optical_rocks) if optical_rocks is not None else None,
            craters_count=len(optical_craters) if optical_craters is not None else None,
            boulders_count=len(optical_rocks) if optical_rocks is not None else None,
            craters=optical_craters,
            rocks=optical_rocks,
            overlay_image=optical_overlay,
            source_product_id=optical_product_id,
            source_resolution_m=optical_res_m,
            optical_status=optical_status,
            optical_provenance_state=optical_match[0].get("coverage_state", "exact_frame_processed") if (optical_match and optical_status == "success") else ("outside_coverage" if coverage_zone in ["outside", "invalid"] else "unavailable"),
            dem_provenance_state="measured_lola_dem" if is_measured else "calibrated_sample_baseline",
            coverage_zone=coverage_zone,
            warnings=warnings,
            model_name="Moonscape Lunar South Pole Optical Hazard Detector (YOLOv8n) & DEM Morphological Curvature Engine",
            model_version="1.2.0",
            limitations=APOLLO_DOMAIN_LIMITATION,
            hazard_assessment_id=assessment_id,
            center_lat=target_lat,
            center_lon=target_lon,
            radius_meters=target_radius,
            total_hazards_detected=len(all_hazards),
            steep_slope_cells=steep_count,
            shadow_coverage_pct=shadow_pct,
            overall_hazard_level=overall_level,
            hazards=all_hazards,
            model_metadata=model_eval_metadata,
            disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
        )


hazard_service = HazardService()
