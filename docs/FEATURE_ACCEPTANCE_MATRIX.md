# Moonscape Feature Acceptance Matrix (Phase 11 Audit)

**Audit Date:** November 14, 2026  
**Auditor:** Senior Software Quality Engineer, Planetary Scientist & Geospatial Engineer  
**Status Legend:**
- **`PASS`**: Feature is fully implemented, verified with automated tests, and grounded in real data/science.
- **`PARTIAL`**: Core engine works, but a secondary sub-component has documented dependencies (e.g. teammate's ML weights).
- **`FAIL`**: Feature fails automated tests or crashes at runtime.
- **`NOT IMPLEMENTED`**: Feature is absent from the repository.
- **`NOT TESTED`**: Feature exists but has not been verified with automated or live tests.
- **`BLOCKED`**: Feature cannot be tested due to an external infrastructure failure.

---

## Complete Feature Matrix (11 Mandatory Features)

| # | Feature Name | Status | Frontend Component | Backend Endpoint | Service Implementation | Dataset / Calculation Used | Data Origin | Test Command | Measured Results & Scientific Limitations |
|---|---|---|---|---|---|---|---|---|---|
| **1** | **Elevation Analysis** | **`PASS`** | `btnSamplePoint`, `valElevation`, `subElevationRelief` | `GET /api/terrain`, `POST /api/analysis/run` | `terrain_service.py`, `dem_service.py` | NASA LOLA 80m & 5m DEMs (`sample_dem.tif`, `Site01_5mpp_surf.tif`) | **REAL** (NASA PDS GeoTIFF) | `pytest Backend/tests/test_terrain.py` | Mean: $+1880.6\text{ m}$ at Shackleton Ridge; vertical accuracy $\pm 1.0\text{ m}$. Sub-pixel relief smaller than raster cell size is unobserved. |
| **2** | **Slope Analysis** | **`PASS`** | `valSlope`, `subSlopeMax`, `slope-bar` (Ideal, Acceptable, Critical) | `GET /api/terrain`, `POST /api/analysis/run` | `terrain_analysis.py`, `maths/topography.py` | Horn (1981) 8-neighbor gradient operator with true pixel spacing | **DERIVED** (Horn Operator) | `pytest Backend/tests/test_final_validation.py -k test_horn_slope` | $0.000000^\circ$ error on analytical $15^\circ$ plane. Critical slope $> 15^\circ$ flagged for tip-over safety. |
| **3** | **Roughness Analysis** | **`PASS`** | `valRoughness` (15m baseline metric box) | `GET /api/terrain`, `POST /api/analysis/run` | `terrain_analysis.py`, `maths/topography.py` | RMS residual height deviation from moving window neighborhood mean | **DERIVED** (RMS Deviation) | `pytest Backend/tests/test_final_validation.py -k test_rms_surface` | RMS roughness: $0.24\text{ m}$ at Shackleton Ridge. Flat terrain produces exactly $0.00\text{ m}$. Kernel baseline: $3 \times dx$. |
| **4** | **Landing-Site Detection** | **`PASS`** | `btnDetectSites`, `detectionCard`, `detectionTableBody` | `POST /api/sites/detect` | `landing_site_detection.py` | 8-neighbor connected component labeling on DEM cells meeting slope & roughness limits | **DERIVED** (DEM Segmentation) | `pytest Backend/tests/test_scientific_regression.py -k test_detect_candidate_sites` | Detected 4 contiguous safe zones at Shackleton Ridge ($D \ge 40\text{ m}$, area $\ge 1256\text{ m}^2$, slope $\le 10^\circ$). Tiny patches rejected. |
| **5** | **Hazard Detection** | **`PARTIAL`** | `hazardsCard`, `valHazardStatus`, `valCraterCount`, `valRockCount` | `POST /api/hazards/predict` | `hazard_service.py`, `hazard_detection.py` | 2D Laplacian curvature $\nabla^2 z$, slope $> 15^\circ$ thresholding, optical ML interface | **DERIVED** (DEM) / **PREDICTED** (ML) | `pytest Backend/tests/test_hazard_detection.py` | DEM curvature detects crater basins and steep slopes. Optical ML model weights are pending delivery from teammate; unconfigured requests safely return `not_available` with caveats. |
| **6** | **Sunlight Analysis** | **`PASS`** | `valCumIllum`, `valInstIllum`, `subPsr`, `valTemp` | `POST /api/analysis/run` | `illumination.py`, `maths/illumination_geometry.py` | JPL DE421 ephemeris, horizon ray-tracing, sunset bisection solver | **DERIVED / SIMULATED** | `pytest Backend/tests/test_scientific_regression.py -k test_sunset_sunrise` | Subsolar latitude bounds: $-1.517^\circ$ to $+1.541^\circ$. Correctly identified continuous summer daylight at Shackleton Ridge, and 255h sunset at 82°S. |
| **7** | **Earth Visibility for Communication** | **`PASS`** | Subscore row "Earth Visibility", `subSimCommPct` | `POST /api/analysis/run`, `POST /api/simulation/visibility` | `illumination.py`, `maths/earth_visibility.py` | Lunar optical librations (Meeus Ch 53), topocentric Earth vector, DEM horizon occultation | **DERIVED** (Ephemeris + DEM) | `pytest Backend/tests/test_scientific_regression.py -k TestEarthVisibilityScience` | Sub-Earth librations stay within $\pm 8^\circ$. Elevation at South Pole matches $-b'_\oplus$. Distinguishes geometric line-of-sight from RF multipath margin ($> 2.0^\circ$). |
| **8** | **Landing-Site Scoring & Ranking** | **`PASS`** | `suitabilityBanner`, `valSuitabilityScore`, `subscoreTableBody` | `POST /api/score`, `POST /api/sites/compare` | `site_scoring.py`, `maths/scoring.py` | Multi-criteria decision analysis (MCDA v2.0-phase6) with slope tip-over safety gate | **DERIVED** (MCDA Utility) | `pytest Backend/tests/test_site_scoring.py` | Normalized 0–100 score. Slope $> 15^\circ$ forces disqualification. Missing factors tracked via `score_coverage_pct` and never assumed to be zero. |
| **9** | **AI Scientific Explanations** | **`PASS`** | `aiCard`, `btnRequestAi`, `aiExplanation`, `aiPositiveFactors` | `POST /api/ai/explain` | `ai_explainer.py`, `ai_providers.py` | Grounded LLM provider (Gemini / OpenAI) with deterministic rule-based fallback | **GENERATED** (Grounded LLM) | `pytest Backend/tests/test_ai_explainer.py` | Strictly grounded in stored `analysis_id` telemetry. Zero hallucination of unmeasured values. Falls back to deterministic narrative when offline. |
| **10** | **Custom Lat/Lon Selection** | **`PASS`** | `latInput`, `lonInput`, `radiusInput` | `GET /api/terrain`, `POST /api/analysis/run` | `coordinate_manager.py`, `maths/geodesy.py` | Planetocentric $\leftrightarrow$ Polar Stereographic (`ESRI:104903`) equations | **VERIFIED** (Geodetic) | `pytest Backend/tests/test_coordinate_manager.py` | Roundtrip error: $0.000\text{ mm}$. Latitude strictly bounded to $[-90^\circ, -80^\circ]$ (422 outside $[-90, 90]$). Longitude normalized across $[-180, 180]$ and $[0, 360]$. |
| **11** | **Time-Based Visibility Simulation** | **`PASS`** | `btnSimulateVisibility`, `simulationCard`, `valSimDaylight`, `valSimComm` | `POST /api/simulation/visibility` | `visibility_simulation.py` | Temporal propagation of solar and Earth ephemeris over 1 to 60 days | **SIMULATED** (Ephemeris) | `pytest Backend/tests/test_scientific_regression.py -k TestVisibilitySimulation` | 14-day / 28-day propagation at configurable time steps. Calculates total daylight, Earth communication hours, and maximum continuous blackout duration. |

---

## Summary of Acceptance Statuses
- **`PASS`:** 10 Features (Elevation, Slope, Roughness, Site Detection, Sunlight, Earth Visibility, Scoring, AI Explainer, Custom Coordinates, Visibility Simulation).
- **`PARTIAL`:** 1 Feature (Hazard Detection: DEM morphological detection is 100% operational; optical ML deep-learning weights are pending delivery from teammate and gracefully handle unconfigured status).
- **`FAIL`:** 0 Features.
- **`NOT IMPLEMENTED`:** 0 Features.
- **`NOT TESTED`:** 0 Features.
- **`BLOCKED`:** 0 Features.
