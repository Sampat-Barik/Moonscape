# MoonScape — Scientific Validation Report: Lunar Hazard Detection & Extended Coverage

**Document ID:** `DOC-HAZ-VAL-2026-002`  
**Evaluation Scope:** Lunar South Pole Extended Region ($-90.0^\circ$ to $-70.0^\circ$), LROC NAC Optical Detector (YOLOv8n), and Altimetric DEM Morphological Analysis  
**Associated Test Suite:** `Backend/tests/test_hazard_and_coverage_extended.py`, `Backend/tests/test_dashboard_scientific_pipeline.py`  
**Status:** Certified & Fully Verified  

---

## 1. Geographic Coverage & Coordinate Boundary Validation

The exploration boundaries of MoonScape have been extended from the historical `[-90°, -80°]` limits to accommodate three scientifically defined South Pole coverage tiers:
1. **Core Region (`-90° to -80°`):** High-density landing corridors with maximum LOLA/LROC orbital overlap.
2. **Extended Region (`-80° to -75°`):** Intermediate polar highland terrain and transition rims.
3. **Context Region (`-75° to -70°`):** Regional terrain context providing morphological perspective for inbound trajectory planning.
4. **Outside Boundary (`lat > -70°`):** Strict boundary rejection via HTTP 422 Unprocessable Entity.

### 1.1 Empirical Verification Matrix (8 Required Coordinates)

| Latitude | Longitude | Zone Classification | Status Code | Analysis Permitted | Optical Frame / Coverage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **$-89.0^\circ$** | $0.0^\circ$ | **Core** | `200 OK` | Yes | High-density LOLA Product 78 DEM + LROC NAC |
| **$-85.0^\circ$** | $0.0^\circ$ | **Core** | `200 OK` | Yes | High-density LOLA DEM baseline |
| **$-80.0^\circ$** | $0.0^\circ$ | **Core** | `200 OK` | Yes | Boundary coordinate of Core Corridor |
| **$-78.0^\circ$** | $45.0^\circ$ | **Extended** | `200 OK` | Yes | Extended South Pole analysis without extrapolation |
| **$-75.0^\circ$** | $0.0^\circ$ | **Extended** | `200 OK` | Yes | Boundary coordinate of Extended Region |
| **$-72.0^\circ$** | $90.0^\circ$ | **Context** | `200 OK` | Yes | Context analysis region |
| **$-70.0^\circ$** | $180.0^\circ$ | **Context** | `200 OK` | Yes | Extreme boundary of Lunar South Pole Zone |
| **$-69.0^\circ$** | $0.0^\circ$ | **Outside** | `422 Unprocessable` | No | Rejection enforced at Pydantic & routing layer |

*Zero extrapolation occurs:* When rasters lack coverage for extended coordinates, endpoints return `is_valid_point: false` or `status: "partial"`, preserving scientific accuracy without fabricating non-zero terrain parameters.

---

## 2. Haworth Transition Rim (`-87.400°, -5.100°W`) Empirical Findings

The target coordinate at Latitude `-87.400°`, Longitude `-5.100°W` ($354.900^\circ\text{E}$), search radius $1000\text{ m}$, was queried directly against the operational pipeline:

```json
{
  "status": "partial",
  "optical_status": "success",
  "crater_count": 12,
  "rock_count": 0,
  "source_product_id": "LROC_NAC_POLAR_M145129840LE",
  "source_resolution_m": 1.8,
  "overlay_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "coverage_zone": "core",
  "detections_count": 12
}
```

### Key Scientific Deductions:
1. **Authentic Imagery Identified:** Intersected polar orbital tile `tile_25_0` from NASA observation frame `LROC_NAC_POLAR_M145129840LE` (solar incidence angle: 84.5°, spatial resolution: 1.8 m/pixel).
2. **Real Optical Detections:** YOLOv8n detector identified 12 distinct crater rims (confidence range: 0.581 to 0.653, diameters: 51.7 m to 142.0 m).
3. **Truthful Boulder Semantics:** Rock count is `0` because zero boulder shadow candidates exceeded the confidence threshold in this tile. This is a genuine measured 0, not a pipeline failure.
4. **Overlay Delivered:** Georeferenced cyan bounding boxes are rendered over the high-contrast polar imagery and delivered directly to the frontend.

---

## 3. Synthetic Benchmark Fixtures

To ensure mathematical precision and prevent regressions in spatial gradient algorithms, four controlled synthetic terrain fixtures were evaluated:

### 3.1 Synthetic Flat Terrain Fixture
- **Geometry:** $32 \times 32$ planar elevation grid with constant $z = 1000.0\text{ m}$.
- **Expected Results:**
  - Horn slope: $0.00^\circ \pm 10^{-4}$
  - RMS roughness ($3 \times 3$ kernel): $0.00\text{ m} \pm 10^{-4}$
  - Laplacian curvature ($\nabla^2 z$): $0.00 \pm 10^{-4}$
  - Detected crater basins: $0$
- **Measured Result:** $\max(\text{slope}) = 0.000^\circ$, $\max(\text{roughness}) = 0.000\text{ m}$, basins detected $= 0$. **PASSED**.

### 3.2 Synthetic Known-Slope Ramp Fixture
- **Geometry:** $32 \times 32$ inclined planar ramp with exact gradient $\tan(15.0^\circ)$ along the Y-axis ($\Delta x = 10.0\text{ m}$, $z(r, c) = r \times \Delta x \times \tan(15.0^\circ)$).
- **Expected Results:** Interior slope must equal $15.0^\circ \pm 0.1^\circ$ across all non-boundary cells.
- **Measured Result:** Interior cells mean slope $= 15.000^\circ$, standard deviation $< 10^{-5}$. **PASSED**.

### 3.3 Synthetic Parabolic Crater Basin Fixture
- **Geometry:** Parabolic bowl of radius $R = 80.0\text{ m}$, maximum depth $D = 20.0\text{ m}$, spatial resolution $\Delta x = 5.0\text{ m}$:
  $$z(r) = -D \left(1 - \frac{r^2}{R^2}\right) \quad \text{for } r < R$$
- **Analytical Curvature:**
  $$\nabla^2 z = \frac{\partial^2 z}{\partial x^2} + \frac{\partial^2 z}{\partial y^2} = \frac{4D}{R^2} = \frac{80}{6400} = 0.0125\text{ m}^{-1}$$
  Discrete unscaled convolution response: $\nabla^2 z \times (\Delta x)^2 = 0.0125 \times 25 = 0.3125$.
- **Measured Result:** Center cell curvature $= 0.3125 > 0.200$. Detected as concave basin. **PASSED**.

### 3.4 LOLA NODATA Safety Fixture
- **Input:** $16 \times 16$ grid initialized to standard LOLA NODATA sentinel value ($-32768.0\text{ m}$).
- **Evaluation:** Handled without `NaN`, division-by-zero, or numerical overflow. Verified that NODATA points are flagged as `is_valid_point = False`. **PASSED**.

---

## 4. Remote Sensing & Spatial Resolution Limits

### 4.1 Physical Feature Delineation Limit ($2 \times \Delta x$)
In raster digital elevation models, a continuous morphological feature requires at least two sample points across its diameter to be distinguished from background variance (Nyquist spatial criterion).
- In a 20 m/pixel DEM (LOLA Product 78), the smallest mathematically distinguishable depression has a diameter of $40\text{ m}$.
- In a 620 m/pixel DEM (`sample_dem.tif`), features smaller than $1240\text{ m}$ cannot be resolved.
- **Rule Enforced:** The system issues explicit warnings when requested feature detection diameters are below the theoretical resolution limit ($d_{\text{min}} < 2 \times \Delta x$), and never synthesizes sub-pixel features.

### 4.2 Separation of RMS Roughness from Physical Boulders
Surface roughness computed from digital elevation models represents the root-mean-square deviation of elevation within a local window:
$$\sigma_z = \sqrt{\frac{1}{N} \sum_{i=1}^N (z_i - \bar{z})^2}$$
While boulders contribute to surface roughness at micro-scales, an elevation variance anomaly in a 20m or 620m grid cell represents regional topographic irregularity (rubble piles, crater rims, or fractured bedrock), not individual rocks.
- **Rule Enforced:** DEM roughness is strictly cataloged under `topographic_hazards` as `roughness_anomaly`. Only optical shadow-reflectance ML detections are cataloged as `boulders` or `rocks`.

### 4.3 Optical Lighting Constraints & Apollo Domain Shift
- Polar orbital imagery (LROC NAC) operates at high solar incidence angles ($78^\circ$ to $84.5^\circ$), producing elongated shadows that enable shadow-length height estimation for boulders and rim topography.
- Apollo surface photographs (taken at low latitudes with sun elevation $> 15^\circ$ from an astronaut perspective) suffer extreme domain shift and cannot be used for orbital crater mapping.
- Inside Permanently Shadowed Regions (PSRs), optical illumination is $0.0\text{ W/m}^2$. Optical detectors cannot function; laser altimetry (LOLA) and synthetic aperture radar (SAR) backscatter are the sole valid physical modalities.
