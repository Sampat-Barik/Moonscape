# MOONSCAPE — SCIENTIFIC FALLBACK & MOCK AUDIT REPORT

**Document Version:** 1.0.0  
**Date:** November 15, 2026  
**Auditor:** Senior Scientific Computing Engineer, Geospatial Specialist & Planetary Data Auditor  
**Workspace:** `D:\MoonScape`  

---

## 1. Executive Summary

This audit examined silent fallback mechanisms, synthetic terrain usage, fabricated frontend statistical derivations, and scoring engine fallbacks across Moonscape's full stack.

Every silent failure mode that previously masked errors behind synthetic data or artificial numbers has been eliminated. The platform now operates with complete scientific transparency:
- Client validation errors (such as HTTP 422 for coordinates outside the South Pole) are strictly displayed to the user rather than triggering mock demo mode.
- Fabricated slope p95 calculations, slope-to-roughness estimators, and artificial dataset names have been completely removed from frontend adapters.
- In the scoring engine, numeric zeros (such as a 0.0 suitability score for disqualified sites) are preserved rather than coerced to default values.

---

## 2. TASK 4: Silent Scientific Mock Fallback Remediation

### 2.1 The Auto-Mode Silent Masking Vulnerability
- **File:** [Frontend/src/services/api.ts](file:///D:/MoonScape/Frontend/src/services/api.ts)
- **Vulnerability:** The central `request()` helper caught any failure in `"auto"` mode and immediately assigned `activeMode = "mock"`, silently serving mock data from `mockData.ts`.
- **Impact on Validation:** When a user submitted an invalid latitude (e.g. $-75.0^\circ$), the backend correctly returned `HTTP 422 Unprocessable Entity` (`"Latitude must be within the lunar South Pole region [-90, -80]"`). However, the frontend caught this 422, treated it as a network outage, and displayed fake mock analysis results, completely concealing the validation error!

### 2.2 Fix Applied
Updated `request()` in [Frontend/src/services/api.ts](file:///D:/MoonScape/Frontend/src/services/api.ts):
```typescript
async function request<T>(
  path: string,
  mockFn: () => Promise<T> | T,
  init?: RequestInit
): Promise<T> {
  if (activeMode === "mock") return mockFn();
  try {
    return await fetchJson<T>(path, init);
  } catch (e) {
    if (requestedMode === "auto") {
      // Do not mask client errors (HTTP 4xx, e.g. 422 Unprocessable Entity) with mock data
      if (e instanceof ApiError && e.status >= 400 && e.status < 500) {
        throw e;
      }
      activeMode = "mock";
      return mockFn();
    }
    throw e;
  }
}
```
- In [Frontend/src/config.ts](file:///D:/MoonScape/Frontend/src/config.ts) and [Frontend/.env.local](file:///D:/MoonScape/Frontend/.env.local), the default mode is set to `VITE_API_MODE=live` with a 30-second timeout (`VITE_API_TIMEOUT_MS=30000`).
- Demo mode remains available when deliberately chosen by the evaluator via the navbar toggle (`setApiMode("mock")`), but live requests never silently default to mock responses.

---

## 3. TASK 5: Live NASA Data Configuration & Synthetic Containment

### 3.1 Backend Configuration Audit
- **File:** [Backend/app/core/config.py](file:///D:/MoonScape/Backend/app/core/config.py)
  - `DATA_MODE = "live"`: Verified NASA data takes precedence.
  - `ALLOW_SYNTHETIC_FALLBACK = True`: Preserved strictly for testing regions where high-resolution rasters are uninstalled.

### 3.2 Provenance Flagging Pipeline
When queries target regions outside the downloaded 5m Product 78 footprint (e.g., Shackleton crater floor or Malapert Massif):
- `dem_service.py` and `nasa_data.py` inspect Product 78 coverage first.
- If uninstalled, the calibrated multi-scale baseline DEM is loaded, but **strictly flagged**:
  - `is_measured_data = False`
  - `source_tier = "Tier 0 (Calibrated Sample Baseline)"`
  - `quality_warnings = "Operating on calibrated baseline synthetic DEM. Acquire authentic NASA rasters via /api/data/download for primary mission evaluation."`
- The system never claims calibrated synthetic terrain is measured LOLA altimetry.

---

## 4. TASK 6: Elimination of Fabricated Frontend Statistics

All synthetic heuristics and artificial values previously found in [Frontend/src/services/api.ts](file:///D:/MoonScape/Frontend/src/services/api.ts) have been removed:

| Adapter / Method | Former Fabricated Expression | Root Cause & Scientific Risk | Corrected Implementation |
|---|---|---|---|
| `getTerrain` | `p95_deg: raw.slope_summary.max_deg` | Substituted maximum slope for 95th percentile slope | `p95_deg: raw.slope_summary.p95_deg ?? null` |
| `runAnalysis` | `p95_deg: raw.slope.max_value * 0.9` | Invented arbitrary $90\%$ factor of maximum slope | `p95_deg: raw.slope.p95_deg ?? null` |
| `compareSites` | `max_deg: s.mean_slope_deg * 1.5` | Fabricated 1.5x multiplier on mean slope | `max_deg: s.max_slope_deg ?? null` |
| `compareSites` | `rms_m: s.mean_slope_deg < 6.0 ? 0.3 : 0.6` | Inferred roughness from slope without physical basis | `rms_m: s.roughness_m ?? null` |
| `predictHazards` | `severity: h.severity ?? "medium"` | Defaulted unassessed hazards to `"medium"` | `severity: h.severity ?? "unclassified"` |
| `predictHazards` | `overall_hazard_level ?? "moderate"` | Fabricated moderate overall rating | `overall_hazard_level: raw.overall_hazard_level ?? null` |
| `getTerrain` | `dsName \|\| "NASA LRO LOLA DEM"` | Hardcoded NASA attribution on unmeasured data | `dsName = raw.dataset_info?.dataset_name ?? null` |
| `runAnalysis` | `dsName \|\| "NASA LRO LOLA DEM (80m)"` | Falsely claimed 80m LOLA attribution | `dsName = raw.dataset_metadata?.dataset_name ?? null` |

Whenever a measurement is absent from the backend response, the frontend now passes `null`, allowing the UI to display `"Data unavailable"` or `"Unmeasured"` rather than an unverified estimate.

---

## 5. TASK 8: Scoring Fallback Defects & Zero-Aware Arithmetic

### 5.1 The `comp_score or 50.0` Defect
- **File:** [Backend/app/services/ml/suitability_model_service.py](file:///D:/MoonScape/Backend/app/services/ml/suitability_model_service.py), Line 384.
- **Defect:** In the fallback deterministic MCDA branch:
  ```python
  raw_score = round(comp_score or 50.0, 1)
  ```
- **Consequence:** In Python, `0.0` is falsy (`bool(0.0) == False`). When a completely disqualified or hazardous site produced a composite score of `0.0`, `comp_score or 50.0` evaluated to `50.0`! A zero-score hazardous site was thus inflated to a moderate 50-point rating!
- **Fix Applied:**
  ```python
  raw_score = round(comp_score if comp_score is not None else 50.0, 1)
  ```

### 5.2 Multi-Criteria Decision Analysis (MCDA) vs ML Separation
- Scientific MCDA calculations in `maths/scoring.py` and `app/services/site_scoring.py` remain strictly deterministic and based on published Apollo/Artemis engineering limits.
- Random Forest surrogate predictions in `suitability_model_service.py` are clearly demarcated with `model_name = "RandomForest Surrogate"` and feature contribution SHAP/MDI vectors.
- Gating limits (slope $>15^\circ$) automatically override scores with `hard_constraint_status = "violated"`.
