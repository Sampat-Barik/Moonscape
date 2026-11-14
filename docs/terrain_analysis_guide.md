# Moonscape Phase 3: Scientific Lunar Terrain Analysis Engine

## Overview & Scientific Traceability

The Moonscape **Lunar Terrain Analysis Engine** provides geodetically rigorous, physically grounded evaluations of candidate lunar South Pole landing regions (-80° to -90° latitude). All calculations operate directly on real NASA Lunar Reconnaissance Orbiter (LRO) elevation models (LOLA 5m candidate region DEMs and 80m regional foundations).

---

## 1. Geodetic & Spatial Foundation

### 1.1 Reference Datum & Coordinate Reference System
- **Planetary Reference Datum:** IAU 2000 Lunar Reference Sphere ($R = 1,737,400.0\text{ m}$).
- **Elevation Datum:** Absolute elevation in meters relative to the $1,737.4\text{ km}$ reference sphere:
  $$h = r_{\text{surface}} - 1,737,400.0\text{ m}$$
- **Map Projection:** Lunar South Polar Stereographic (**ESRI:104903** / IAU 2000 Moon Polar Stereographic).
  - Central Meridian $\lambda_0 = 0.0^\circ$ (Prime Meridian along $+y$ axis)
  - Standard Parallel $\phi_0 = -90.0^\circ$ (South Pole at $(0, 0)\text{ m}$)
  - Reference Frame: **MOON_ME** (Mean Earth / Polar Axis) DE421 ephemeris.

### 1.2 Physical Distance Spatial Masking (Task 4)
Raster analysis windows must represent **true physical distance on the lunar surface in meters**, rather than an arbitrary pixel grid.
Given center projection coordinates $(x_0, y_0)$ in meters and affine transform matrix $A$:
$$\begin{bmatrix} x \\ y \end{bmatrix} = \begin{bmatrix} a & b & c \\ d & e & f \end{bmatrix} \begin{bmatrix} \text{col} \\ \text{row} \\ 1 \end{bmatrix}$$
Every raster cell $(r, c)$ is mapped to its Euclidean distance from the query origin:
$$d(r, c) = \sqrt{(x - x_0)^2 + (y - y_0)^2}$$
A raster cell is included in the spatial analysis if and only if:
$$d(r, c) \le R_{\text{physical}}$$
This guarantees that spatial aggregations (min, max, mean, distribution) accurately sample a physical disc of radius $R_{\text{physical}}$ meters regardless of cell resolution ($5\text{ m}$ vs $80\text{ m}$).

---

## 2. Scientific Topographic Metrics

### 2.1 Elevation Metrics (Task 1)
- **Point Elevation ($z_0$):** Sampled at the exact coordinate $(x_0, y_0)$ using nearest-neighbor/bilinear interpolation.
- **Local Minimum Elevation ($z_{\text{min}}$):** $\min \{ z(r, c) \mid d(r, c) \le R, \text{valid}(r, c) \}$.
- **Local Maximum Elevation ($z_{\text{max}}$):** $\max \{ z(r, c) \mid d(r, c) \le R, \text{valid}(r, c) \}$.
- **Local Mean Elevation ($\bar{z}$):** $\frac{1}{N} \sum_{i=1}^{N} z_i$.
- **Local Elevation Relief / Variation ($\Delta z$):**
  $$\Delta z = z_{\text{max}} - z_{\text{min}}$$
- **Standard Deviation ($\sigma_z$):** Macro-scale elevation spread within the physical disc.

### 2.2 Topographic Slope (Task 2)
Slope represents the maximum rate of change of elevation across the horizontal terrain plane, measured in **degrees**.

#### Hierarchy of Slope Sources:
1. **Authentic NASA Precomputed Slope Products (Preferred):**
   When available (e.g. `Site01_final_adj_5mpp_slp.tif` from Barker et al. 2021 or `LDSM_80S_80MPP_ADJ.TIF`), precomputed slopes are extracted directly from the NASA GeoTIFF.
2. **Horn (1981) 8-Neighbor Gradient Operator (Derived from DEM):**
   When precomputed slope maps are absent or have local nodata gaps, slope is derived directly from the DEM using Horn's weighted convolution kernels:
   $$K_x = \frac{1}{8 \cdot \Delta x} \begin{bmatrix} -1 & 0 & 1 \\ -2 & 0 & 2 \\ -1 & 0 & 1 \end{bmatrix}, \quad K_y = \frac{1}{8 \cdot \Delta y} \begin{bmatrix} 1 & 2 & 1 \\ 0 & 0 & 0 \\ -1 & -2 & -1 \end{bmatrix}$$
   $$\frac{\partial z}{\partial x} = z * K_x, \quad \frac{\partial z}{\partial y} = z * K_y$$
   $$\text{Gradient Magnitude } G = \sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}$$
   $$\theta_{\text{slope}} = \arctan(G) \times \frac{180^\circ}{\pi}$$

#### Slope Safety Thresholds (Apollo & Artemis Lander Specs):
- **Ideal ($\le 5.0^\circ$):** Minimal tip-over risk, optimal engine plume reflection.
- **Acceptable ($5.0^\circ - 10.0^\circ$):** Standard operational envelope for modern human lunar landers.
- **Marginal ($10.0^\circ - 15.0^\circ$):** Elevated tip-over risk; requires adaptive landing leg damping.
- **Critical / Hazardous ($> 15.0^\circ$):** Severe lander tip-over hazard; unfeasible for safe touchdown.

### 2.3 Surface Roughness (Task 3)
Roughness represents the **micro-relief texture and high-frequency bumpiness** of the lunar regolith after removing macro topographic trends.

#### Method: Root-Mean-Square (RMS) Residual Height Deviation
$$\bar{z}_{\text{local}}(r, c) = \frac{1}{K^2} \sum_{i=-k}^{k} \sum_{j=-k}^{k} z(r+i, c+j)$$
$$\text{residual}(r, c) = z(r, c) - \bar{z}_{\text{local}}(r, c)$$
$$\text{Roughness}_{\text{RMS}}(r, c) = \sqrt{\frac{1}{K^2} \sum_{i=-k}^{k} \sum_{j=-k}^{k} \left[\text{residual}(r+i, c+j)\right]^2}$$
- **Configurable Neighborhood:** Default kernel size $K = 3$ ($3 \times 3$ window).
- **Physical Baseline:**
  $$\text{Baseline}_{\text{meters}} = K \times \Delta x_{\text{meters}}$$
  *(e.g., $3 \times 5.0\text{ m} = 15.0\text{ m}$ on Product 78, or $3 \times 80.0\text{ m} = 240.0\text{ m}$ on Product 90)*.

---

## 3. Explicit Scientific Distinctions

It is vital in planetary landing analysis **never to confuse elevation variation, slope, and roughness**:

| Metric | Scientific Concept | Physical Unit | Interpretation |
|---|---|---|---|
| **Elevation Variation ($\Delta z$)** | Macro Topographic Relief | **Meters ($m$)** | Overall height difference between highest crater rim and lowest basin floor across the entire landing zone. |
| **Topographic Slope ($\theta$)** | Angular Gradient | **Degrees ($^\circ$)** | Tilt of the local surface plane relative to horizontal; dictates spacecraft tip-over stability. |
| **Surface Roughness ($\text{RMS}$)** | Micro-Scale Regolith Texture | **Meters ($m$)** | Residual high-frequency bumpy deviations around the local mean plane; indicates boulder clusters, small craters, and landing leg footpad clearance hazards. |

---

## 4. Scientific Assumptions & Known Limitations

1. **Spatial Scale Dependence:**
   Topographic slope and roughness are intrinsically **scale-dependent**. Slopes derived at 80 m/pixel smooth out 10-meter crater walls that a 5 m/pixel DEM captures. Moonscape explicitly tags every measurement with its source resolution.
2. **Missing / Shadowed Pixels:**
   Optical sensors cannot resolve deep Permanently Shadowed Regions (PSRs). While LOLA laser altimetry penetrates shadows, orbital ground track gaps exist. Missing values are flagged with `is_nodata: true` and excluded from statistics rather than replaced with interpolated guesses.
3. **Boundary Padding:**
   Moving window convolutions apply `reflect` padding at image boundaries to prevent edge drop-off artifacts.
4. **Preliminary Nature:**
   A "safe" classification indicates preliminary slope and roughness clearance. It does **not** constitute certified landing safety (hazard detection and boulder distribution are integrated in subsequent phases).

---

## 5. Example JSON Payloads

### 5.1 Point Terrain & Radius Query
**Request:**
```http
GET /api/terrain?lat=-89.46&lon=222.0&radius_m=100.0 HTTP/1.1
Host: localhost:8000
```

**Response (200 OK):**
```json
{
  "latitude": -89.46,
  "longitude": 222.0,
  "is_valid_point": true,
  "is_nodata": false,
  "elevation_m": 1934.41,
  "slope_deg": 3.78,
  "roughness_m": 0.04,
  "aspect_deg": 354.5,
  "solar_illumination_pct": 92.0,
  "landing_hazard_classification": "safe",
  "dataset_info": {
    "dataset_name": "NASA PGDA Product 78 (LOLA 5m/pixel Candidate Site DEM)",
    "product_id": "Site01_final_adj_5mpp_surf",
    "spatial_resolution_m": 5.0,
    "vertical_uncertainty_m": 0.2,
    "slope_method": "NASA GSFC Precomputed Topographic Slope Raster",
    "roughness_baseline_m": 15.0,
    "citation": "Barker, M. K., et al. (2021). High-resolution lunar south pole digital elevation models from LOLA and LROC. Planetary and Space Science, 203, 105119.",
    "is_measured_data": true,
    "source_url": "https://pgda.gsfc.nasa.gov/products/78",
    "crs": "ESRI:104903 (Lunar South Polar Stereographic)",
    "reference_frame": "MOON_ME (Mean Earth / Polar Axis) DE421, R=1737400m"
  },
  "source_tier": "Tier 2 (High-Resolution 5m Candidate Region)",
  "uncertainty_elevation_m": 0.2,
  "uncertainty_slope_deg": 1.7,
  "notes": "Analysis computed over physical disc of 100.0m radius.",
  "analysis_radius_m": 100.0,
  "elevation_summary": {
    "point_m": 1934.41,
    "min_m": 1928.3,
    "max_m": 1941.1,
    "mean_m": 1934.7,
    "variation_m": 12.8,
    "std_dev_m": 3.2,
    "units": "meters"
  },
  "slope_summary": {
    "point_deg": 3.78,
    "min_deg": 0.9,
    "max_deg": 7.8,
    "mean_deg": 3.65,
    "std_dev_deg": 1.3,
    "method": "NASA GSFC Precomputed Topographic Slope Raster",
    "units": "degrees",
    "ideal_pct": 89.2,
    "acceptable_pct": 10.8,
    "marginal_pct": 0.0,
    "critical_hazardous_pct": 0.0
  },
  "roughness_summary": {
    "point_m": 0.04,
    "min_m": 0.01,
    "max_m": 0.12,
    "mean_m": 0.04,
    "std_dev_m": 0.02,
    "method": "Root-Mean-Square (RMS) Residual Height Deviation from Local Neighborhood",
    "kernel_size": 3,
    "baseline_m": 15.0,
    "units": "meters"
  },
  "total_pixels_in_disc": 1256,
  "valid_pixels_in_disc": 1256,
  "nodata_pixels_in_disc": 0
}
```

### 5.2 Landing Zone Spatial Analysis
**Request:**
```http
POST /api/analysis/run HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "center_lat": -89.46,
  "center_lon": 222.0,
  "radius_meters": 1000.0,
  "max_acceptable_slope_deg": 10.0,
  "max_acceptable_roughness_m": 0.5,
  "roughness_kernel_size": 3
}
```

**Response (200 OK):**
```json
{
  "analysis_id": "ANL-9F2B8D14",
  "center_lat": -89.46,
  "center_lon": 222.0,
  "radius_meters": 1000.0,
  "total_samples": 125600,
  "valid_samples": 125600,
  "nodata_samples": 0,
  "elevation": {
    "min_value": 1820.4,
    "max_value": 2010.8,
    "mean_value": 1915.2,
    "median_value": 1934.41,
    "std_dev": 32.5,
    "variation": 190.4,
    "units": "meters"
  },
  "slope": {
    "min_value": 0.8,
    "max_value": 18.2,
    "mean_value": 4.9,
    "median_value": 3.78,
    "std_dev": 2.6,
    "units": "degrees"
  },
  "slope_distribution": {
    "ideal_pct": 68.4,
    "acceptable_pct": 24.1,
    "marginal_pct": 6.2,
    "critical_hazardous_pct": 1.3
  },
  "roughness_mean_m": 0.08,
  "roughness_max_m": 0.42,
  "roughness_baseline_m": 15.0,
  "roughness_method": "Root-Mean-Square (RMS) Residual Height Deviation from Local Neighborhood",
  "slope_method": "NASA GSFC Precomputed Topographic Slope Raster",
  "safe_touchdown_fraction_pct": 92.5,
  "preliminary_feasibility": "favorable",
  "dataset_metadata": {
    "source_tier": "Tier 2 (High-Resolution 5m Candidate Region)",
    "dataset_name": "NASA PGDA Product 78 (LOLA 5m/pixel Candidate Site DEM)",
    "product_id": "Site01_final_adj_5mpp_surf",
    "spatial_resolution_m": 5.0,
    "crs": "ESRI:104903 (Lunar South Polar Stereographic)",
    "is_measured_data": true
  },
  "disclaimer": "PRELIMINARY SCIENTIFIC FEASIBILITY ONLY. NOT CERTIFIED LANDING SAFETY."
}
```
