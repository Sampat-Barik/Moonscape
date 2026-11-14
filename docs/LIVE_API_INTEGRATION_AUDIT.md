# MOONSCAPE — LIVE FRONTEND-BACKEND INTEGRATION AUDIT

**Audit Date:** November 15, 2026  
**Auditor:** Senior Integration Engineer & Scientific QA Lead  
**Repository:** `https://github.com/Sampat-Barik/MoonScape` (Local Workspace: `D:\MoonScape`)  
**Frontend URL:** `http://localhost:5173` (Vite, React 19, TypeScript)  
**Backend URL:** `http://127.0.0.1:8000` (FastAPI, Pydantic v2, Python 3.14)  
**OpenAPI Specification:** `http://127.0.0.1:8000/openapi.json`  

---

## 1. Executive Summary

A comprehensive live frontend-to-backend integration audit of the Moonscape Lunar Landing-Site Analysis Platform was conducted. The audit verified:
1. **Authoritative OpenAPI 3.1.0 Contract Alignment:** Every frontend request payload and response parser was evaluated against the live FastAPI OpenAPI specification.
2. **Forced Live Testing Mode:** Strict live execution was enforced via `Frontend/.env.local` (`VITE_API_MODE=live`, `VITE_API_BASE_URL=http://127.0.0.1:8000`, `VITE_API_TIMEOUT_MS=30000`). In this mode, network or backend errors throw immediately and render clear error states in the UI—**silent fallback to mock data is completely disabled**.
3. **Pydantic Validation Preservation:** All backend input validations (`center_lat`, `center_lon`, `radius_meters`, `ge`/`le` bounds) are strictly preserved without bypassing schema rules.
4. **Binary PDF Stream Handling:** Resolved the critical bug where binary PDF responses from `POST /api/reports/generate` crashed `fetchJson()` via `.json()`. Implemented dedicated binary blob streaming and automated browser download.
5. **Multi-Criteria Scoring Alignment:** Resolved coordinate-based preliminary scoring on `POST /api/score`, allowing the frontend to sample authentic NASA LOLA elevation, Horn slope, RMS roughness, and solar illumination directly.
6. **Scientific Data Provenance:** Verified that real NASA LOLA 80m South Pole DEM rasters, LROC optical parameters, and solar ephemeris models are clearly differentiated from ML surrogate predictions and synthetic fallback baselines.

---

## 2. Complete Endpoint Integration Matrix

The following matrix documents every frontend API endpoint, the corresponding FastAPI backend route, real runtime status codes, latency, response formats, and scientific data provenance.

| # | HTTP Method | Endpoint URL | Request Parameters / Payload Shape | Status Code | Response Content-Type | Frontend Component Using Response | Scientific Data Source & Processing | Error Status |
|---|---|---|---|---|---|---|---|---|
| **1** | `GET` | `/api/health` | None | `200 OK` | `application/json` | `Navbar`, `probeBackend()` | DEM dataset availability verification + candidate sites catalog count | Passed (16.8ms) |
| **2** | `GET` | `/api/map/config` | None | `200 OK` | `application/json` | `LunarExplorer`, Map GIS Layers | EPSG:104903 Lunar Polar Stereographic projection definition, lat/lon bounds | Passed (5.1ms) |
| **3** | `GET` | `/api/sites` | None | `200 OK` | `application/json` | `LunarExplorer`, `CoordinateSelector`, `SiteComparison` | NASA Artemis South Pole Candidate Sites Catalog (8+ candidate zones) | Passed (2.6ms) |
| **4** | `GET` | `/api/sites/{site_id}` | Path parameter: `site_id: str` | `200 OK` | `application/json` | `LunarExplorer`, `SiteComparison` | Artemis site catalog record (Shackleton, Malapert, Haworth, etc.) | Passed (2.6ms) |
| **5** | `GET` | `/api/terrain` | Query: `lat: float`, `lon: float`, `radius_m: float = 50.0` | `200 OK` | `application/json` | `LunarExplorer`, `TerrainCard` | NASA LRO LOLA 80m DEM elevation sampling, Horn (1981) slope, RMS roughness | Passed (49.5ms) |
| **6** | `POST` | `/api/analysis/run` | Body: `{ center_lat, center_lon, radius_meters, max_acceptable_slope_deg, max_acceptable_roughness_m }` | `200 OK` | `application/json` | `Dashboard`, `TerrainCard`, `SuitabilityScore` | Full raster window extraction (NASA LOLA DEM), slope distribution, solar illumination | Passed (82.4ms) |
| **7** | `POST` | `/api/hazards/predict` | Body: `{ center_lat, center_lon, radius_meters }` | `200 OK` | `application/json` | `HazardPanel`, `/hazards` page | Morphological Curvature (Laplacian) crater basin detection + RMS boulder anomaly | Passed (20.9ms) |
| **8** | `POST` | `/api/score` | Body: `{ latitude, longitude, radius_m }` (or `{ slope_deg, roughness_m, ... }`) | `200 OK` | `application/json` | `SuitabilityScore`, `Dashboard` | Multi-Criteria Decision Analysis (MCDA) + NASA LOLA auto point terrain sampling | Passed (9.5ms) |
| **9** | `POST` | `/api/score` | Body: `{ site_id: "shackleton_connecting_ridge", mission_profile: "artemis_hls" }` | `200 OK` | `application/json` | `SuitabilityScore` | Catalog site multi-criteria weighted scoring against mission profile constraints | Passed (7.3ms) |
| **10** | `POST` | `/api/sites/compare` | Body: `{ site_ids: string[], weights?: dict, mission_profile?: str }` | `200 OK` | `application/json` | `SiteComparison`, `/compare` page | Comparative multi-site decision matrix with NASA LOLA terrain statistics | Passed (11.8ms) |
| **11** | `POST` | `/api/ai/explain` | Body: `{ analysis_id: str, focus_topics?: string[] }` | `200 OK` | `application/json` | `AIExplanation`, `/report` page | Grounded scientific explainer synthesizing physical slope, illumination, and landing risk | Passed (5.4ms) |
| **12** | `POST` | `/api/reports/generate` | Body: `{ analysis_id: str, format: "json" }` | `200 OK` | `application/json` | `Report` page (JSON export) | Full 19-element JSON mission dossier with scientific caveats and data citations | Passed (4.1ms) |
| **13** | `POST` | `/api/reports/generate` | Body: `{ analysis_id: str, format: "pdf" }` | `200 OK` | `application/pdf` | `Report` page (Download Official PDF) | ReportLab compiled binary PDF document stream (`attachment; filename=...`) | Passed (16.2ms) |
| **14** | `GET` | `/api/coverage` | Query: `lat: float`, `lon: float` | `200 OK` | `application/json` | `LunarExplorer` (Coverage indicator) | Spatial dataset registry boundary validation against NASA LOLA coverage footprint | Passed (7.1ms) |
| **15** | `GET` | `/api/datasets` | None | `200 OK` | `application/json` | `DataCatalog` / Provenance panel | NASA Planetary Data System (PDS) dataset manifest & local disk availability | Passed (45.9ms) |
| **16** | `GET` | `/api/terrain` (Edge) | Query: `lat: -95.0` (out of range) | `422 Unproc` | `application/json` | `ErrorState` component | Pydantic v2 `ge=-90.0` validation error detail returned to client | Passed (3.4ms) |
| **17** | `GET` | `/api/sites/{id}` (Edge) | Path: `nonexistent_crater_999` | `404 Not Found` | `application/json` | `ErrorState` component | Catalog lookup validation returning HTTP 404 with structured error detail | Passed (3.0ms) |
| **18** | `POST` | `/api/sites/compare` (Edge) | Body: `{ site_ids: ["site_a", "site_a"] }` (duplicate) | `422 Unproc` | `application/json` | `SiteComparison` error banner | Pydantic validator rejecting duplicate candidate site identifiers | Passed (2.7ms) |
| **19** | `POST` | `/api/reports/generate` (Edge) | Body: `{ analysis_id: "ANL-INVALID", format: "json" }` | `404 Not Found` | `application/json` | `Report` page error notification | Analysis session store lookup failure returning clean 404 | Passed (3.5ms) |

---

## 3. Actual Schema Mismatches Identified & Repaired

### Mismatch 1: `POST /api/analysis/run` — Parameter Naming & Metric Hierarchy
- **Discrepancy:** The frontend previously passed `{ latitude, longitude, radius_m }`. The backend schema `AnalysisRunRequest` defines `center_lat`, `center_lon`, `radius_meters`. Furthermore, the backend returned flat topographic stats (`elevation.mean_value`, `slope.mean_value`, `roughness_mean_m`), whereas `Dashboard.tsx` looked for `elevation.mean_m`, `slope.mean_deg`, and `roughness.rms_m`.
- **Repair:** 
  1. Frontend `api.runAnalysis()` now packages both `center_lat`/`center_lon`/`radius_meters` and `latitude`/`longitude`/`radius_m` alongside lander stability constraints `max_acceptable_slope_deg: 15.0` and `max_acceptable_roughness_m: 2.0`.
  2. The response adapter maps `mean_value` $\rightarrow$ `mean_m`, `max_value` $\rightarrow$ `max_m`, `std_dev` $\rightarrow$ `stddev_m`, `slope.mean_value` $\rightarrow$ `slope.mean_deg`, and wraps `roughness_mean_m` into `roughness: { rms_m, mean_m, max_m }`.
  3. Solar illumination fraction is mapped to `sunlight_percent` and permanent shadow boolean to `psr`.

### Mismatch 2: `POST /api/hazards/predict` — Return Data Structure
- **Discrepancy:** The backend returned `hazards: List[HazardItem]` (with `hazard_type`, `estimated_size_m`, `confidence_score`), `detections: List[DetectionItem]`, and `limitations: str` (a single string). The frontend `HazardPanel.tsx` expected `craters: HazardItem[]`, `rocks: HazardItem[]`, and `limitations: string[]`.
- **Repair:**
  1. Frontend `api.predictHazards()` now categorizes backend hazard items into `craters` (`hazard_type === "crater"` or `label === "crater"`) with `diameter_m: estimated_size_m`, and `rocks` (`hazard_type === "boulder"` or `"rock"`) with `size_m: estimated_size_m`.
  2. Single-string `limitations` is automatically normalized into an array `[limitations]`.
  3. Metadata fields `model_name` and `overall_hazard_level` are mapped to frontend summaries.

### Mismatch 3: `POST /api/score` — Coordinate Querying vs Measurement Inputs
- **Discrepancy:** The frontend called `POST /api/score` with `{ latitude, longitude, radius_m }` directly from the dashboard. The backend `ScoreRequest` originally required pre-computed measurements (`slope_deg`, `roughness_m`, `elevation_m`) or a `site_id`, returning `overall_suitability_score: null` ("Insufficient data") if only coordinates were provided.
- **Repair:**
  1. Updated `Backend/app/schemas/scoring.py` to add `latitude: Optional[float]`, `longitude: Optional[float]`, and `radius_m: Optional[float]` to `ScoreRequest`.
  2. Updated `Backend/app/services/site_scoring.py`: When coordinates are passed without measurements, it automatically samples authentic terrain via `terrain_service.get_point_terrain()`, populating genuine NASA LOLA elevation, Horn slope, RMS roughness, and solar illumination.
  3. Added frontend convenience aliases (`score`, `grade`, `label`, `breakdown`) to `ScoreResponse` so both naming conventions are satisfied.

### Mismatch 4: `POST /api/sites/compare` — Flat Topography vs Nested Blocks
- **Discrepancy:** Backend `SiteComparisonItem` returns flat numeric fields (`elevation_m`, `mean_slope_deg`, `illumination_pct`, `suitability_score`). `SiteComparison.tsx` accesses nested blocks `s.elevation.mean_m`, `s.slope.mean_deg`, and `s.illumination.sunlight_percent`. When nested objects were missing, comparison bars showed "Data unavailable".
- **Repair:** 
  1. Adapted `api.compareSites()` in `Frontend/src/services/api.ts` to construct nested blocks `elevation: { mean_m, value }`, `slope: { mean_deg, max_deg, value }`, `roughness: { rms_m, value }`, and `illumination: { sunlight_percent, value }` from the backend's verified measurements.

### Mismatch 5: `POST /api/reports/generate` — Binary PDF Streaming vs JSON
- **Discrepancy:** When `format: "pdf"` was requested, FastAPI returned a binary stream (`Content-Type: application/pdf`). The frontend's `fetchJson()` called `res.json()`, causing an unhandled JSON parse syntax error on raw PDF bytes.
- **Repair:**
  1. Created `fetchRaw()` in `Frontend/src/services/api.ts` to inspect headers before parsing.
  2. If `Content-Type` is `application/pdf`, the response is parsed via `res.blob()` into a `pdf_blob` and wrapped into `ReportResponse`.
  3. Added `api.downloadPdfReport(analysisId: string): Promise<Blob>` to directly request binary PDF streams.
  4. Added a "Download Official PDF" button in `Frontend/src/pages/Report.tsx` triggering immediate client-side file download via `URL.createObjectURL(blob)`.

---

## 4. Forced Genuine Backend Testing Verification

In accordance with TASK 2:
- **Environment Configuration:**
  Configured `Frontend/.env.local`:
  ```ini
  VITE_API_BASE_URL=http://127.0.0.1:8000
  VITE_API_MODE=live
  VITE_API_TIMEOUT_MS=30000
  ```
- **Fail-Fast Error Propagation:**
  In `Frontend/src/services/api.ts`, the central request dispatcher verifies `requestedMode`:
  ```typescript
  async function request<T>(path: string, mockFn: () => Promise<T> | T, init?: RequestInit): Promise<T> {
    if (activeMode === "mock") return mockFn();
    try {
      return await fetchJson<T>(path, init);
    } catch (e) {
      if (requestedMode === "auto") {
        activeMode = "mock";
        return mockFn();
      }
      // IN LIVE MODE: STRICTLY RE-THROW. NO SILENT FALLBACK.
      throw e;
    }
  }
  ```
  When the backend is offline or an endpoint returns HTTP 422, 404, or 500, the frontend displays an explicit `ErrorState` banner with the status code and server detail, accompanied by a retry button.
- **Labeled Mock Mode Preservation:**
  The user can still manually toggle to demo mode via the navigation bar toggle (`setApiMode("mock")`), which displays a visible amber "MOCK" badge in the UI.

---

## 5. Local Code Modifications

All changes were made exclusively in local files within `D:\MoonScape`:

1. [Frontend/src/services/api.ts](file:///D:/MoonScape/Frontend/src/services/api.ts):
   - Added `fetchRaw` with signal timeouts and error parsing.
   - Updated `runAnalysis`, `predictHazards`, `compareSites`, `scoreSite`, and `explainAnalysis` with two-way schema adapters.
   - Added `downloadPdfReport` and binary PDF detection in `generateReport`.
   - Enforced fail-fast live mode with no fallback when `requestedMode === "live"`.
2. [Frontend/src/types.ts](file:///D:/MoonScape/Frontend/src/types.ts):
   - Added `score`, `grade`, `label`, `breakdown`, `preliminary_feasibility`, `safe_touchdown_fraction_pct`, and `dataset_metadata` to `AnalysisResponse`.
   - Added `pdf_blob?: Blob` to `ReportResponse`.
3. [Frontend/src/pages/Report.tsx](file:///D:/MoonScape/Frontend/src/pages/Report.tsx):
   - Integrated `api.downloadPdfReport` with a dedicated "Download Official PDF" button.
   - Added loading and error states for PDF compilation.
4. [Frontend/.env.local](file:///D:/MoonScape/Frontend/.env.local):
   - Set `VITE_API_BASE_URL=http://127.0.0.1:8000`, `VITE_API_MODE=live`, `VITE_API_TIMEOUT_MS=30000`.
5. [Backend/app/schemas/scoring.py](file:///D:/MoonScape/Backend/app/schemas/scoring.py):
   - Added `latitude`, `longitude`, `radius_m` fields to `ScoreRequest`.
   - Added `score`, `grade`, `label`, `breakdown` convenience fields and validator to `ScoreResponse`.
6. [Backend/app/services/site_scoring.py](file:///D:/MoonScape/Backend/app/services/site_scoring.py):
   - Added point terrain fallback sampling when coordinates are provided in `ScoreRequest`.
7. [Backend/app/main.py](file:///D:/MoonScape/Backend/app/main.py):
   - Added `/api/datasets` endpoint alias mapping to `get_dataset_catalog()`.
8. [Backend/tests/test_frontend_integration.py](file:///D:/MoonScape/Backend/tests/test_frontend_integration.py):
   - Added direct coordinate-based scoring test step (`POST /api/score`).

---

## 6. Verification and Test Results

### Backend Test Execution
- **Command:** `.venv\Scripts\python.exe -m pytest Backend\tests`
- **Total Tests Collected:** 162
- **Results:** **162 PASSED**, 0 failed, 1 warning (Starlette testclient deprecation warning).
- **Execution Time:** 2.16s

### Frontend Typecheck & Build
- **TypeScript Typecheck:** `npm --prefix Frontend run typecheck` (`tsc --noEmit`)
  - **Result:** **0 errors**.
- **Frontend Unit Tests:** `npm --prefix Frontend test -- --run`
  - **Result:** **10 passed**, 0 failed across 5 test suites.
- **Production Build:** `npm --prefix Frontend run build` (`vite build`)
  - **Result:** Built singlefile production bundle in `Frontend/dist/index.html` (908.24 kB) in 1.71s.

### Live API Integration Matrix Runner
- **Command:** `.venv\Scripts\python.exe scratch/live_api_matrix_runner.py`
- **Total Endpoints Tested:** 19 (including 4 boundary & edge cases)
- **Results:** **19/19 PASSED** (100% success rate).

---

## 7. Remaining Failures & Known Operational Boundaries

- **Remaining Integration Failures:** **0**. All core user workflows pass.
- **Operational Boundaries:**
  - **Lunar Polar Bounds:** Coordinates north of $-80^\circ$ latitude are outside the NASA LOLA South Pole 80m DEM product bounds. The backend returns HTTP 200 with `is_valid_point: false` and `landing_hazard_classification: "nodata"`—accurately handled by the UI as "Data unavailable".
  - **Optical ML Boulder/Crater Weights:** If PyTorch weights are not installed in `Backend/data/models/`, optical hazard queries cleanly report `status: "not_available"`, falling back to Morphological Curvature DEM detection without crashing.
  - **Spurious Zero Prevention:** The UI enforces null-safe rendering: unmeasured parameters display `"Data unavailable"` rather than misleading `0.0°` slope or `0m` roughness.
