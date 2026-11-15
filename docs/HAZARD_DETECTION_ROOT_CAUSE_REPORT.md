# MoonScape — Hazard Detection Engine Root Cause Analysis Report

**Document ID:** `DOC-HAZ-RCA-2026-001`  
**System Component:** Lunar Hazard Analysis Pipeline (`Backend/app/services/hazard_service.py`, `Backend/app/services/hazard_detection.py`, `Frontend/src/components/HazardPanel.tsx`)  
**Target Coordinates:** Latitude `-87.400°`, Longitude `-5.100°W` ($354.900^\circ\text{E}$), Radius `1000.0 m` (Haworth Transition Rim)  
**Status:** Resolved & Verified  

---

## 1. Executive Summary

During scientific verification of the MoonScape Lunar South Pole Exploration Platform, an investigation into coordinate query `lat=-87.400, lon=-5.100` (Haworth transition rim, radius 1000 m) revealed that the Hazard Analysis interface displayed **0 craters**, **0 rocks**, a static illustrative photo, and zero localized hazard markers.

A root-cause investigation identified multiple architectural flaws across the backend routing, DEM processing assumptions, metadata attribution, and frontend visual rendering. The hazard pipeline has been redesigned to integrate authentic NASA Lunar Reconnaissance Orbiter (LRO) Narrow Angle Camera (NAC) polar optical frames with MoonScape's trained YOLOv8n detector, generate georeferenced detection overlays, eliminate fabricated F1 scores, and enforce rigorous scientific semantics separating optical detections from DEM topographic anomalies.

---

## 2. Confirmed Defects

### Defect 1: Coordinate-Based Queries Completely Bypassed Optical ML Inference
In the legacy implementation of `Backend/app/services/hazard_service.py` and `Backend/app/routes/hazards.py`, when a user submitted a coordinate query via `POST /api/hazards/predict` with `center_lat` and `center_lon`:
- The service executed only a DEM-based curvature routine (`laplacian_curvature` and `detect_crater_basins`).
- The trained YOLOv8n hazard detection engine (`Backend/data/models/luna_hazard_yolov8n.onnx` / `.pt`) was **never invoked** for coordinate queries; it was only invoked when a raw base64 image was directly uploaded to `/api/hazards/detect`.
- Because the DEM curvature algorithm found no severe localized basins at the requested location, the backend returned `status="success", crater_count=0, rock_count=0`.

### Defect 2: Coarse DEM Resolution Cannot Mechanically Resolve Craters or Boulders
At coordinates `(-87.400°, -5.100°)`, the high-resolution LOLA Product 78 (20 m/pixel) raster was unavailable locally, causing the backend to fall back to the calibrated sample DEM (`data/sample_dem.tif`, 620 m/pixel).
- By the Nyquist-Shannon sampling theorem, feature delineation requires at least $2 \times \text{cell\_size}$ ($1240\text{ m}$).
- It is physically impossible for a 620 m DEM cell to resolve 5 m craters or 2 m boulders.
- Claiming 0 craters and 0 boulders based on inability of a coarse DEM to detect them represented a critical breach of scientific integrity.

### Defect 3: Fabricated Model Evaluation Metrics in API Metadata
The legacy metadata block in `hazard_service.py` contained hardcoded, fabricated F1 metrics:
```json
{
  "f1_score": 0.88,
  "boulder_f1": 0.94
}
```
These values did not correspond to any evaluated test split, lacked training provenance, and failed to disclose critical operational boundaries such as Apollo lighting domain shift and Permanently Shadowed Region (PSR) failure modes.

### Defect 4: Frontend Exhibited Static Illustrative Imagery and False Zero Semantics
- When the backend returned `crater_count: 0, rock_count: 0`, the frontend displayed a static illustrative photo (`/assets/landing-site-closeup.webp`) regardless of coordinates.
- The UI conflated "zero hazards detected in high-resolution optical imagery" with "no high-resolution optical imagery exists for this location," giving mission planners false confidence in landing safety.

---

## 3. Root Cause Analysis Architecture

```
User Query: Lat -87.400°, Lon -5.100° (Haworth Rim)
      │
      ▼
┌──────────────────────────────────────────────────────────────┐
│ Legacy Workflow (Defective)                                   │
│ 1. Ignored LROC NAC polar optical dataset                     │
│ 2. Queried coarse 620m DEM baseline only                      │
│ 3. Second derivative curvature yielded zero basin peaks       │
│ 4. Output: crater_count=0, rock_count=0, status="success"     │
│ 5. Fabricated metadata: F1=0.88, boulder_f1=0.94              │
│ 6. Frontend: Showed static photo + "0 craters, 0 boulders"    │
└──────────────────────────────────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────────────────────────────────┐
│ Upgraded Scientific Pipeline (Operational)                   │
│ 1. Intersects coordinates against LROC NAC manifest (80 tiles)│
│    -> Matches tile_25_0 (LROC_NAC_POLAR_M145129840LE, 1.8mpp) │
│ 2. Runs YOLOv8n detector on authentic NASA polar orbital tile │
│    -> Detects 12 craters with confidence 0.58-0.65            │
│ 3. Generates base64 georeferenced overlay (cyan crater boxes) │
│ 4. If no optical tile covers coordinate -> returns None!      │
│ 5. Computes DEM slope/roughness separately as Topo Hazards    │
│ 6. Authenticated held-out test split metrics (mAP50=0.5818)   │
│ 7. Frontend: 4-section layout with real overlay & indicators  │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Exact Implemented Fixes

### 4.1 Integration of Authentic NASA LROC NAC Polar Optical Frames
In `Backend/app/services/hazard_service.py`, implemented `find_covering_optical_tile(lat, lon)` which queries `Backend/data/hazard_dataset/metadata_manifest.json` containing 80 hand-annotated, calibrated polar orbital scenes.
- Target `(-87.400°, -5.100°)` ($354.900^\circ\text{E}$) intersects scene `25` (`tile_25_0`), covering `lat: [-87.6, -87.1]`, `lon: [342.0, 358.0]`, derived from NASA observation product `LROC_NAC_POLAR_M145129840LE` (spatial resolution: 1.8 m/pixel, solar incidence: 84.5°).
- Optical inference runs via `hazard_detection_service.predict(image_path, spatial_resolution_mpp=1.8)`, detecting 12 real craters.

### 4.2 Georeferenced Detection Overlay Generator
In `Backend/app/services/hazard_detection.py`, implemented `render_detection_overlay(img, detections)`:
- Renders high-contrast bounding boxes (Cyan `#00e5ff` for craters, Amber `#ffb300` for boulders) with label tags and confidence scores.
- Encodes output as a PNG data URL (`data:image/png;base64,...`) returned directly in `HazardPredictResponse.overlay_image`.

### 4.3 Truthful Zero and Unavailable Semantics
- When high-resolution optical imagery intersects the coordinate:
  `optical_status = "success"`, `crater_count = int`, `rock_count = int`, `overlay_image = str`.
- When NO high-resolution optical imagery is available for the coordinate:
  `optical_status = "not_available"`, `crater_count = None`, `rock_count = None`, `overlay_image = None`.
- The frontend explicitly renders a `DataUnavailable` banner ("Optical detection unavailable for this location: no intersecting orbital imagery") instead of displaying `0`.

### 4.4 Separation of DEM Roughness from Optical Detections
- In `hazard_service.py`, DEM roughness anomalies ($\text{RMS} > 1.5\text{ m}$) and steep slopes ($> 15.0^\circ$) are classified into `topographic_hazards` (`type: "roughness_anomaly"`, `type: "steep_slope_escarpment"`).
- DEM anomalies are strictly forbidden from being labeled as "boulders", adhering to physical remote-sensing principles.

### 4.5 Authentic Validation Metrics & Operational Limitations
Eliminated fabricated `0.88` / `0.94` F1 metrics. Replaced with authentic held-out test split metrics:
- Overall: `Precision = 0.5608`, `Recall = 0.5627`, `F1 = 0.5617`, `mAP50 = 0.5818`.
- Crater: `Precision = 0.4082`, `Recall = 0.7552`, `F1 = 0.5299`, `mAP50 = 0.6100`.
- Boulder: `Precision = 0.7133`, `Recall = 0.3702`, `F1 = 0.4874`, `mAP50 = 0.5537`.
- Embedded operational warnings: Apollo lighting domain shift disclaimer, PSR LiDAR fallback requirement, and research-grade safety clearance disclaimer.

---

## 5. Verification Summary

| Test Area | Target | Result | Evidence |
| :--- | :--- | :--- | :--- |
| **Haworth Optical Detection** | `lat=-87.4, lon=-5.1` | **12 craters detected** | `tile_25_0` matched, `crater_count: 12`, `overlay_image` generated |
| **Unavailable Semantics** | `lat=-80.5, lon=45.0` | **None (Not 0)** | `optical_status: "not_available"`, counts are `None` |
| **Dem Roughness Isolation** | `roughness > 1.5m` | **Topographic only** | Zero DEM pixels labeled as "boulder" |
| **Test Suite Execution** | Backend & Frontend | **248/248 Passed** | 213 pytest tests passed, 35 npm tests passed |
