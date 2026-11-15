# MOONSCAPE — CRITICAL BACKEND, NUMPY, MATHEMATICS AND COORDINATE INTEGRATION REPAIR REPORT

**System:** Moonscape Lunar South Pole Landing Site Analysis Platform  
**Workspace:** `D:\MoonScape`  
**Date:** November 15, 2026  
**Hardware Profile:** AMD Ryzen 9 8940HX, 16 GB System RAM, NVIDIA GeForce RTX 5070 Laptop GPU (8 GB VRAM), Windows 11  
**Services:** Frontend on `http://localhost:5173`, FastAPI Backend on `http://127.0.0.1:8000`  

---

## A. CONFIRMED ROOT CAUSES AND APPLIED FIXES

### Defect 1: Three.js Map Drag Snapped Globe from South Pole to Mid-Latitudes

- **File:** `Frontend/src/components/LunarMap.tsx`
- **Functions:** `onPointerMove` (lines 406–410) and damping render loop (lines 509–513)
- **Error:** When dragging or touching the 3D lunar globe, the Moon abruptly rotated away from the South Pole (-90°S) to mid-latitudes and equatorial regions (-7°S to -49°S).
- **Scientific Root Cause:** The initial South Pole view correctly rotated the Moon to the polar orientation (`rotation.x = -1.5708` rad / -90°). However, the pointer movement and damping loops clamped `group.rotation.x` to `[-1.2, 1.2]` radians (-68.75° to +68.75°). This clamping was designed for equatorial orbital cameras and actively prevented the lunar South Pole from facing the camera. As soon as the pointer moved by 1 pixel, `rotation.x` was clamped to -1.2 rad, instantly displacing the pole and causing gimbal lock in Euler angle space.
- **Applied Fix:** Removed the Euler angle clamp and transitioned rotation tracking to incremental Quaternion multiplication (`group.quaternion.premultiply(qy).premultiply(qx)`). Horizontal mouse movement rotates around camera up (`0, 1, 0`) and vertical movement rotates around camera right (`1, 0, 0`). The lunar South Pole can now be inspected, tilted, and orbited smoothly without snapping or gimbal lock.

---

### Defect 2: Raycaster Intersected Selection Pulse Ring Billboard Sprites

- **File:** `Frontend/src/components/LunarMap.tsx`
- **Function:** `pick(e: PointerEvent)`
- **Error:** Clicking near the selected location generated distorted, inconsistent coordinates (e.g., clicking on the pole returned mid-latitude coordinates).
- **Scientific Root Cause:** The raycaster target array was defined as `[moon, ...markerGroup.children]`. The `markerGroup` contains not only site markers but also the active selection indicator: a pulse ring sprite (`scale: 0.17` sphere units, covering ~10% of the Moon radius) and dot sprite. Three.js sprites are 2D planes that continuously face the camera billboard-style. When a user clicked on or near their selection, the ray intersected the planar billboard rather than the 3D lunar sphere. The resulting intersection point off the sphere surface was transformed into local coordinates and passed to `vec3ToLatLon`, producing severely skewed coordinates. Additionally, `group.updateMatrixWorld(true)` was not called prior to raycasting.
- **Applied Fix:** Separated marker picking from sphere raycasting. The raycaster now first tests registered candidate site markers (which carry exact `userData.latlon`). If no marker is clicked, it raycasts directly against `moon` (the true `SphereGeometry` mesh). The selection ring and dot sprites never intercept rays. `group.updateMatrixWorld(true)` is explicitly invoked prior to raycasting.

---

### Defect 3: Missing Validation Guard and UI Feedback for Non-Polar Coordinates

- **Files:** `Frontend/src/pages/Explorer.tsx`, `Frontend/src/pages/Dashboard.tsx`, `Frontend/src/context/AppContext.tsx`
- **Functions:** `onAnalyse`, `runAnalysis`, `errMsg`
- **Error:** When users visually explored areas outside the South Pole coverage zone (latitudes > -80°), clicking "Analyse" or "Run Analysis" fired `POST /api/analysis/run` with the out-of-range latitude, which FastAPI correctly rejected with HTTP 422 (`"Input should be less than or equal to -80"`). The UI then displayed an error banner that lingered even if the user subsequently clicked another location.
- **Scientific Root Cause:** The frontend did not guard the analysis trigger or communicate that NASA South Pole LOLA datasets only cover 80°S–90°S.
- **Applied Fix:**
  1. In `Explorer.tsx`, introduced `isInAnalysisRegion` (`selection.latitude <= -80 && selection.latitude >= -90`).
  2. Added a warning banner in the Explorer sidebar when outside coverage: *"Selected latitude is outside the supported lunar South Pole analysis region (80°S–90°S). Visual exploration is available, but terrain analysis requires coordinates within the polar coverage zone."* with a one-click *"Reset to South Pole (89.44°S)"* button.
  3. Disabled both "Analyse" and "Run Analysis" buttons when `!isInAnalysisRegion`.
  4. In `AppContext.tsx`, added a pre-flight range check in `runAnalysis` returning a clean explanatory message without making an unnecessary network request.
  5. Enhanced `errMsg` to parse Pydantic v2 validation error lists into readable messages (e.g. `center_lat: Input should be less than or equal to -80`).
  6. In `Dashboard.tsx`, disabled the analysis trigger and displayed a coverage advisory when coordinates are outside the polar zone.

---

### Defect 4: CoordinateSelector Longitude Upper Bound Truncation

- **File:** `Frontend/src/components/CoordinateSelector.tsx`
- **Input:** `id="cs-lon"`
- **Error:** Longitude input was restricted to `min={-180} max={180}`, whereas lunar landing sites in the backend catalog use 0°–360° East longitude convention (e.g., Connecting Ridge at 222.50°).
- **Scientific Root Cause:** Lunar cartography routinely employs both [-180°, +180°] and [0°, 360°] conventions. The backend schema accepts `ge=-180.0, le=360.0`, but the frontend input clamped values to 180°.
- **Applied Fix:** Updated input bounds to `min={-180} max={360}` with `step="0.01"`, allowing users to input either convention without form validation errors.

---

### Defect 5: Outdated Roughness Step-Down Test Assertion in Maths Suite

- **File:** `maths/tests/test_maths.py`
- **Function:** `test_scoring_roughness_penalty`
- **Error:** Pytest failure: `assert evaluate_roughness_score(0.3) == 100.0` failed with `assert 94.0 == 100.0`.
- **Scientific Root Cause:** `evaluate_roughness_score` was updated to reflect strict Artemis Human Landing System (HLS) limits (<= 0.25m = 100.0, 0.25m–0.50m drops 100->70, 0.50m–1.20m drops 70->0). Under this curve, roughness 0.30m evaluates to 94.0. The test suite in `Backend/tests/test_site_scoring.py` had been updated, but `maths/tests/test_maths.py` still expected an older curve (<= 0.30m = 100.0, 0.50m = 75.0).
- **Applied Fix:** Synchronized `maths/tests/test_maths.py` with Artemis HLS thresholds:
  - `evaluate_roughness_score(0.20) == 100.0`
  - `evaluate_roughness_score(0.25) == 100.0`
  - `evaluate_roughness_score(0.30) == 94.0`
  - `evaluate_roughness_score(0.50) == 70.0`
  - `evaluate_roughness_score(1.20) == 0.0`
  - `evaluate_roughness_score(1.50) == 0.0`

---

### Defect 6: Terrain Endpoint Query Parameter Aliasing

- **File:** `Backend/app/routes/terrain.py`
- **Function:** `get_terrain_at_point`
- **Error:** `GET /api/terrain` returned HTTP 422 if clients provided `latitude` / `longitude` query parameter names instead of `lat` / `lon`.
- **Applied Fix:** Added `Query(None)` aliases for `latitude`, `longitude`, and `radius_meters` alongside `lat`, `lon`, and `radius_m`, guaranteeing backward and forward client compatibility.

---

### Defect 7: Missing Structured Backend Observability

- **File:** `Backend/app/routes/analysis.py`
- **Function:** `run_analysis`
- **Error:** Minimal endpoint lacked execution tracing, request IDs, calculation timing, and root-cause logging on failure.
- **Applied Fix:** Added structured logging with unique request IDs (`REQ-XXXXXXXX`), coordinates, radius, slope/roughness thresholds, elapsed latency in milliseconds, dataset provenance, and full exception traceback logging on internal errors.

---

## B. PYTHON ENVIRONMENT DIAGNOSIS

| Component | Verified Specification | Status |
| :--- | :--- | :--- |
| **Python Executable** | `D:\MoonScape\.venv\Scripts\python.exe` | Verified |
| **Python Version** | 3.14.4 (tags/v3.14.4:23116f9, Apr 7 2026, 14:10:54) [MSC v.1944 64 bit (AMD64)] | Verified |
| **NumPy** | `2.5.4` | Verified |
| **SciPy** | `1.18.1` | Verified |
| **Rasterio** | `1.5.2` (includes GDAL C bindings) | Verified |
| **FastAPI** | `0.162.7` | Verified |
| **Pydantic** | `2.14.3` (v2 core) | Verified |
| **scikit-learn** | `1.9.1` | Verified |
| **Affine** | `3.0.1` | Verified |
| **HTTPX** | `0.28.1` | Verified |
| **Pytest** | `9.2.0` | Verified |

### Package Dependency Analysis

1. **`pyproj`**: Not installed and NOT required. Lunar polar stereographic forward/inverse projections are implemented analytically in `maths/geodesy.py` and via Rasterio's bundled GDAL transform engine.
2. **`pandas`**: Not installed and NOT required. All tabular and matrix calculations utilize NumPy ndarrays and Pydantic models.
3. **`osgeo` / direct GDAL**: Not installed directly. Rasterio 1.5.2 natively encapsulates the necessary GDAL geospatial raster I/O libraries.
4. **`torch`**: Optional. `Backend/app/services/hazard_detection.py` gracefully checks `import torch` inside a try/except block. If PyTorch is absent, it seamlessly utilizes computer-vision heuristics (Horn slope, RMS roughness, morphological filters).
5. **`spiceypy`**: Optional. `Backend/app/services/spice_service.py` gracefully falls back to high-precision analytical ephemeris models (Meeus lunar libration, subsolar coordinates) implemented in `maths/illumination_geometry.py` and `maths/earth_visibility.py`.

---

## C. MATHEMATICAL ENGINE AUDIT

All 6 core modules in `maths/` and their corresponding backend services were audited and verified:

| Module | Purpose | Status | Verification Details |
| :--- | :--- | :--- | :--- |
| `maths/geodesy.py` | Polar stereographic projection (`latlon_to_polar_stereo`, `polar_stereo_to_latlon`), Haversine distance, Euclidean 2D distance. | **WORKING** | Roundtrips within `< 1e-4` deg. South Pole (-90°, 0°) maps to `(0, 0)` meters. Haversine matches 1° lunar latitude (~30.32 km). |
| `maths/topography.py` | Horn (1981) 8-neighbor slope & aspect gradient operator, RMS surface roughness across configurable baselines, slope distribution breakdown. | **WORKING** | Flat plane produces 0.0° slope. Uniform 1:1 gradient produces 45.0° slope. RMS roughness of smooth terrain is 0.0m. |
| `maths/curvature.py` | 2D Laplacian curvature operator, morphological crater basin segmentation. | **WORKING** | Correctly detects crater rim convexity and basin concavity across 50x50 test DEMs. |
| `maths/illumination_geometry.py` | Analytical subsolar point calculation, solar elevation & azimuth, topographic horizon raycasting, diurnal temperature estimation, sunset/sunrise solver. | **WORKING** | Subsolar point aligns with J2000 epoch progression. Solar elevation at South Pole correctly calculates negative/grazing sun angles. |
| `maths/earth_visibility.py` | Meeus optical libration in longitude & latitude, sub-Earth coordinates, Earth elevation & azimuth, direct RF communication link budget. | **WORKING** | Libration amplitudes bounded within ±7.9° lon and ±6.7° lat. Direct line-of-sight margins calculated correctly. |
| `maths/scoring.py` | Multi-criteria decision analysis (MCDA), piecewise linear penalties, Artemis HLS hard constraints evaluation, coverage-weighted scoring. | **WORKING** | Hard safety constraints precede scoring. Missing factors cannot fabricate scores. 10/10 unit tests passing. |

---

## D. FULL API ENDPOINT AUDIT (LOCAL LIVE PORT 8000)

All 11 endpoints were tested against the active FastAPI server on `http://127.0.0.1:8000`:

| Method | Endpoint | Tested Parameters | Response Status | Key Response Verification |
| :--- | :--- | :--- | :---: | :--- |
| `GET` | `/api/health` | None | **HTTP 200** | `status: "healthy"` |
| `GET` | `/api/sites` | None | **HTTP 200** | 8 candidate landing sites loaded from catalog |
| `GET` | `/api/map/config` | None | **HTTP 200** | `projection: "Lunar Polar Stereographic"`, bounds defined |
| `GET` | `/api/terrain` | `lat=-89.44, lon=222.50` | **HTTP 200** | `elevation_m: 1958.32`, `slope_deg: 1.73`, `roughness_m: 0.20` |
| `GET` | `/api/terrain` | `lat=-49.554, lon=-65.256` | **HTTP 200** | `is_valid_point: false` (non-polar location gracefully handled) |
| `POST` | `/api/analysis/run` | `center_lat: -89.44, center_lon: 222.50, radius_meters: 1000` | **HTTP 200** | Generated `analysis_id: ANL-2AFFB3C9`, `feasibility: "marginal"`, valid elevation/slope stats |
| `POST` | `/api/analysis/run` | `center_lat: -7.0241, center_lon: 65.256` | **HTTP 422** | Rejection: `"Input should be less than or equal to -80"` (strict scientific coverage guard) |
| `POST` | `/api/hazards/predict` | `latitude: -89.44, longitude: 222.50, radius_m: 1000` | **HTTP 200** | Slope and roughness hazard zones evaluated, heuristic classifier executed |
| `POST` | `/api/score` | `slope_deg: 6.5, roughness_m: 0.25, illumination_pct: 82.0, profile: "artemis_hls"` | **HTTP 200** | `overall_suitability_score: 96.14`, `grade: "A"`, constraint status: `passed` |
| `POST` | `/api/sites/compare` | `site_ids: ["shackleton_connecting_ridge", "malapert_mountain"]` | **HTTP 200** | Multi-site MCDA comparison matrix generated across 2 sites |
| `POST` | `/api/ai/explain` | `analysis_id: "ANL-2AFFB3C9", selected_site: {...}, score_data: {...}` | **HTTP 200** | AI scientific narrative and mission recommendation generated |
| `POST` | `/api/simulation/visibility` | `lat: -89.44, lon: 222.50, duration_days: 14, step_hours: 4` | **HTTP 200** | 85 time steps simulated, `sunlight_percentage: 100.0%`, comm link budgets evaluated |
| `POST` | `/api/reports/generate` | `analysis_id: "ANL-2AFFB3C9", format: "markdown"` | **HTTP 200** | `report_id: "RPT-1DCE5028"`, complete scientific dossier compiled |

---

## E. COORDINATE-SYSTEM TRACEABILITY AND VALIDATION

```
User Click / Selection:
  Three.js Raycaster -> lunar sphere mesh (worldToLocal) -> vec3ToLatLon
  Coordinates: Lat = -89.4400°, Lon = 222.5000°
       |
       v
React State (`AppContext.tsx`):
  selection = { latitude: -89.44, longitude: 222.5, radius_m: 1000 }
       |
       +---> Display Formatting (`Explorer.tsx`):
       |       fmtCoord(-89.44, 222.5) -> "89.440° S, 137.500° W" (or 222.500° E)
       |
       +---> API Request Payload (`api.ts` -> `runAnalysis`):
       |       {
       |         "center_lat": -89.44,
       |         "center_lon": 222.5,
       |         "radius_meters": 1000.0,
       |         "max_acceptable_slope_deg": 15.0,
       |         "max_acceptable_roughness_m": 2.0
       |       }
       |
       v
FastAPI Pydantic Request Validation (`schemas/analysis.py`):
  AnalysisRunRequest:
    center_lat: -89.44 (validated: -90.0 <= -89.44 <= -80.0) -> PASS
    center_lon: 222.50 (validated: -180.0 <= 222.50 <= 360.0) -> PASS
       |
       v
Geospatial Projection Engine (`maths/geodesy.py` & `nasa_data.py`):
  latlon_to_polar_stereo(-89.44, 222.50) -> x = -11,465.3m, y = -12,492.1m
       |
       v
Raster Window Sampling (`raster_sampler.py`):
  Window centered at (x=-11,465.3m, y=-12,492.1m), radius = 1000.0m
```

**Conclusion:** Map selection, UI coordinate display, API request payload, and backend spatial sampling represent the identical physical lunar location with zero coordinate drift or inversion.

---

## F. AUTOMATED TEST SUITE REPORT

### 1. Mathematical Core Tests (`maths/tests/test_maths.py`)
```text
Command: .venv\Scripts\python.exe -m pytest maths\tests\test_maths.py -v
Result: 10 passed in 0.36s
Status: 100% PASS
```

### 2. Backend Unit and Integration Tests (`Backend/tests`)
```text
Command: .venv\Scripts\python.exe -m pytest Backend\tests -v
Result: 164 passed, 1 warning (deprecation notice for httpx2) in 2.49s
Status: 100% PASS
```

### 3. Frontend Unit & Contract Tests (`Frontend/tests/unit.test.mjs`)
```text
Command: npm --prefix Frontend test
Result: 13 passed in 79.58ms across 6 test suites:
  - 1. Coordinate Validation & Formatting
  - 2. Scientific Null-Safe Data Pickers
  - 3. Number Formatting & Precision
  - 4. Time-Based Solar Simulation Calculations
  - 5. Production Bundle & Asset Verification
  - 6. Coordinate Selection vs API Request Payload Contract
Status: 100% PASS
```

### 4. Frontend TypeScript Static Type Analysis
```text
Command: npm --prefix Frontend run typecheck
Result: tsc --noEmit exited with code 0 (zero errors)
Status: 100% PASS
```

### 5. Frontend Production Bundle Build
```text
Command: npm --prefix Frontend run build
Result: Built singlefile distribution (935.20 kB, gzip: 244.59 kB) in 1.73s
Status: 100% PASS
```

---

## G. REMAINING SCIENTIFIC DATASET & MODEL LIMITATIONS

1. **NASA Regional Foundation DEM (PGDA Product 90)**:
   - *Status:* Cataloged and supported in code, but the multi-gigabyte raw regional raster files (`pgda90_ldem`, `pgda90_ldsm`) are not downloaded to local disk.
   - *Installed Real Data:* High-resolution NASA PGDA Product 78 (Site 01, 5m/pixel resolution) is installed in `Backend/data/lunar/raw/pgda78/`.
   - *Fallback Behavior:* Queries in the lunar South Pole outside Site 01 use `sample_dem.tif`, which is explicitly flagged in API responses with `is_measured_data: false`, `source_tier: "Tier 0 (Calibrated Sample Baseline)"`, and quality notices. Synthetic data cannot silently masquerade as authentic NASA observations.
   - *Resolution Action:* To install full 80m regional data, execute the verified pipeline downloader in `Backend/app/services/data_management/downloader.py` or trigger `/api/data/download/profile/profile_b`.

2. **Optical Deep Learning Hazard Inference**:
   - *Status:* The random forest tabular surrogate model (`landing_suitability_rf_v1.joblib`) is installed and active for ML site scoring.
   - *Deep Learning Weights:* A pre-trained PyTorch `.pt` convolutional neural network for boulder/crater instance segmentation from raw NAC imagery is not included in the repository.
   - *Operational Behavior:* The platform automatically falls back to mathematical computer-vision heuristics (Horn slope gradients, RMS roughness, and Laplacian basin detection), logging an informational warning rather than failing.

3. **NAIF SPICE Kernels**:
   - *Status:* `spiceypy` C bindings and raw SPICE ephemeris binary kernels (`.bsp`, `.tpc`) are not bundled locally.
   - *Operational Behavior:* The platform utilizes high-precision analytical planetary geometry (Meeus optical libration theory and subsolar celestial coordinates), providing sub-degree accuracy for solar illumination and Earth line-of-sight analysis.
