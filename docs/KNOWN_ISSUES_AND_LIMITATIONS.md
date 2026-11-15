# MOONSCAPE — KNOWN ISSUES & LIMITATIONS

**Document Version:** 1.0.0-final  
**Date:** November 15, 2026  
**Auditor:** Quality Assurance & Planetary Systems Reliability Engineer  
**Workspace:** `D:\MoonScape`  

---

## 1. Overview of Scientific & Engineering Boundaries

Moonscape is engineered with strict adherence to scientific truthfulness. Rather than concealing system boundaries behind synthetic approximations, all physical limits, coverage regions, and fallback behaviors are documented and programmatically enforced.

---

## 2. Topographic & Elevation Coverage Limits

### 2.1 High-Resolution Measured 5m Data Footprint
- **Current Coverage:** The ultra-high-resolution NASA PGDA Product 78 dataset (5.0 m/pixel) covers the Shackleton Connecting Ridge candidate region (Site 01: $-89.75^\circ$ to $-89.20^\circ$ latitude, $210.0^\circ$ to $235.0^\circ$ longitude).
- **Out-of-Footprint Behavior:** When users query South Polar regions outside Site 01 (such as Malapert Mountain or Amundsen crater rim), Moonscape automatically uses the multi-scale calibrated regional model.
- **Scientific Safeguard:** Every API response explicitly flags `is_measured_data = False`, `source_tier = "Calibrated Topographic Model"`, and emits a quality warning to prevent unmeasured data from being mistaken for laser altimetry.

### 2.2 Polar Stereographic Domain Boundary
- **Latitude Domain:** Moonscape is specialized for the lunar South Pole ($\phi \in [-90^\circ, -80^\circ]$).
- **Enforcement:** Latitudes north of $-80.0^\circ$ are rejected at the Pydantic schema validation layer with HTTP 422 (`"Latitude must be within the lunar South Pole region [-90, -80]"`). Equatorial and northern lunar regions are out of scope.

---

## 3. Optical Hazard Detection & Machine Learning Weights

### 3.1 Pretrained Deep-Learning Weights
- **Limitation:** The deep-learning object detector weights file (`hazard_detector_weights.onnx` / `.pt`) is omitted from the Git repository to keep local repository size under 250 MB.
- **Handling:** When the optical hazard endpoint `/api/hazards/optical-detect` is queried, the backend returns:
  ```json
  {
    "status": "not_available",
    "message": "Pretrained optical weights not installed. Falling back to DEM-based morphological hazard detection.",
    "boulders_detected": 0,
    "craters_detected": 0,
    "confidence": 0.0
  }
  ```
- **Fallback:** The UI and backend seamlessly switch to the DEM morphological hazard engine (analyzing slope thresholds $>15^\circ$, roughness outliers, and negative curvature pockets).

---

## 4. External NASA Services & Offline Operation

### 4.1 NASA JPL Horizons API Rate Limits & Network Latency
- **Limitation:** Live JPL Horizons HTTP queries require an active internet connection and can experience 300ms – 1,500ms network latency or occasional HTTP 429 rate limiting.
- **Handling:** Moonscape implements a two-tier caching strategy:
  1. In-memory LRU cache stores queried ephemeris states.
  2. If the network times out or fails, Moonscape seamlessly falls back to its built-in analytical DE421 ephemeris engine, yielding $< 0.05^\circ$ angular accuracy with zero user disruption.

### 4.2 Moon Trek WMTS Tile Streaming
- **Limitation:** NASA Moon Trek tiles depend on remote NASA JPL server availability.
- **Handling:** If Moon Trek servers are unreachable, the 3D Three.js lunar globe automatically renders using local embedded bump, normal, and displacement textures, ensuring uninterrupted exploration.

---

## 5. Uninstalled Optional Data Catalogs

As verified in `docs/NASA_DATA_SOURCE_STATUS.md`:
- **NASA PGDA Product 90 (80m DEM):** Cataloged in `download_manifest.json` but not pre-downloaded. Can be initiated via `/api/data/download`.
- **NASA PGDA Product 104 (1m SfS):** Shape-from-Shading footprints are cataloged but raster files are not pre-packaged.
- **NASA LRO Diviner (PCP):** Cumulative thermal maps are cataloged; analytical thermal approximations are used when raster files are absent.

All operational endpoints gracefully handle missing rasters through explicit metadata flags and robust mathematical fallbacks.
