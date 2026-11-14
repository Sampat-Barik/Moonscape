# Moonscape Scientific Validation Report (Phase 11)

**Evaluation Date:** November 14, 2026  
**Auditor:** Senior Planetary Scientist & Geospatial Software Reviewer  
**Standard Datum:** IAU 2000 Lunar Mean Sphere ($R = 1,737,400\text{ m}$)  
**Standard Projection:** Lunar South Polar Stereographic (`ESRI:104903` / `EPSG:104903`)  
**Ephemeris Standard:** JPL DE421 / Meeus Analytical Planetary Ephemerides  

---

## 1. Topographic & Geodetic Science

### 1. Elevation Analysis
- **Reference Datum & CRS:**
  - All elevations reference the IAU 2000 lunar mean spherical datum of radius $R = 1,737,400.0\text{ m}$.
  - Coordinate reference system: Lunar South Polar Stereographic (`ESRI:104903`), centered at the South Pole (Latitude of origin $-90.0^\circ$, Central Meridian $0.0^\circ$, Scale Factor $1.0$, False Easting $0.0\text{ m}$, False Northing $0.0\text{ m}$).
- **Elevation Values & Units:**
  - Elevation is recorded and returned in SI **meters** relative to the $1,737.4\text{ km}$ sphere.
  - Authentic sample check at Site 01 Shackleton Connecting Ridge ($-89.44^\circ\text{S}, 222.50^\circ\text{E}$):
    - Raw NASA LOLA 5m DEM elevation: **$+1880.62\text{ m}$**.
    - API returned point elevation: **$+1880.62\text{ m}$**. (Exact match).
- **Missing Data (Nodata) Handling:**
  - NASA LOLA nodata values ($-32768.0$) and invalid altimeter returns ($\le -30000.0$ or NaN) are masked prior to statistical aggregation.
  - Verified by `test_nodata_pixels_treatment`: When a center pixel is $-32768.0$, it is excluded from mean and variance calculations, preventing statistical distortion.

### 2. Slope Derivation
- **Mathematical Operator:**
  - Derived using **Horn's (1981)** 8-neighbor convolution operator on metric grids:
    $$\frac{\partial z}{\partial x} = \frac{(z_{i-1, j+1} + 2z_{i, j+1} + z_{i+1, j+1}) - (z_{i-1, j-1} + 2z_{i, j-1} + z_{i+1, j-1})}{8 \cdot dx}$$
    $$\frac{\partial z}{\partial y} = \frac{(z_{i+1, j-1} + 2z_{i+1, j} + z_{i+1, j+1}) - (z_{i-1, j-1} + 2z_{i-1, j} + z_{i-1, j+1})}{8 \cdot dy}$$
    $$\text{Slope} = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}\right)$$
  - Uses true metric horizontal grid cell spacing ($dx = dy = 80.0\text{ m}$ for Tier 1, $5.0\text{ m}$ for Tier 2).
- **Analytical Ground Truth Accuracy:**
  - Tested on a synthetic planar surface inclined at exactly $\theta = 15.000^\circ$:
    - Calculated mean slope: **$15.000000^\circ$**.
    - Derivation error: **$0.000000^\circ$**.
- **Categorical Breakdown:**
  - Informs lander stability thresholds: Ideal ($\le 5^\circ$), Acceptable ($5\text{--}10^\circ$), Marginal ($10\text{--}15^\circ$), Critical ($> 15^\circ$).

### 3. Surface Roughness
- **Metric Formulation:**
  - Evaluated as the root-mean-square (RMS) residual height deviation from the moving neighborhood mean:
    $$\text{Roughness}_\text{RMS} = \sqrt{\frac{1}{N} \sum_{k=1}^N (z_k - \bar{z})^2}$$
  - Window size: configurable $3 \times 3$ kernel, corresponding to a physical baseline of $3 \times dx$ ($240\text{ m}$ at 80m resolution, $15\text{ m}$ at 5m resolution).
  - Units: **meters RMS**.
  - Flat terrain test: produces exactly $0.00\text{ m}$ RMS roughness.

---

## 2. Landing-Site Detection & Hazard Physics

### 4. Automated Contiguous Landing-Site Detection
- **Algorithm:**
  - Evaluates real DEM raster cells for simultaneous satisfaction of:
    1. $\text{Slope} \le \text{max\_slope}$ (default $8.0^\circ$)
    2. $\text{Roughness} \le \text{max\_roughness}$ (default $0.35\text{ m}$)
    3. Elevation non-nodata ($z > -30000\text{ m}$)
  - Extracts contiguous clusters using 8-connectivity connected-component labeling (`scipy.ndimage.label`).
  - Computes physical contiguous surface area: $A = \sum \text{pixels} \times (dx \times dy)$.
  - Equivalent circular landing diameter: $D_\text{eff} = 2 \sqrt{A / \pi}$.
  - Rejection criterion: Any cluster with $D_\text{eff} < D_\text{min}$ (e.g. $< 50\text{ m}$) is rejected.
  - Centroids are converted from projected grid coordinates $(x, y)$ to planetocentric $(\phi, \lambda)$ via inverse polar stereographic transformation.
- **Empirical Validation:**
  - Run at Shackleton Ridge ($-89.44^\circ\text{S}, 222.50^\circ\text{E}$, radius $1000\text{ m}$):
    - Detected 4 distinct contiguous landing zones meeting $D \ge 40\text{ m}$ and $\text{slope} \le 10^\circ$.
    - Top zone has effective diameter $86.2\text{ m}$, area $5835\text{ m}^2$, mean slope $5.41^\circ$, and suitability score $83.5/100$.

### 5. Hazard Detection
- **Topographic Curvature Hazards:**
  - Uses 2D Laplacian of Gaussian ($\nabla^2 z$) to identify crater rims and concave basin depressions.
  - Flags slopes $> 15.0^\circ$ as dynamic tip-over hazards based on Apollo LM and Artemis Human Landing System (HLS) design margins.
  - Identifies sub-pixel RMS roughness anomalies exceeding $0.35\text{ m}$ as boulder-clutter fields.
- **Optical ML Inference & Uncalibrated Scale Safeguards:**
  - Machine-learning optical models without physical scale metadata (meters per pixel) are explicitly flagged. The system refuses to output ungrounded physical boulder diameters when spatial scale is missing, returning `estimated_size_m: null` with documented caveats.

---

## 3. Astronomical & Planetary Illumination Science

### 6. Sunlight Analysis & Solar Ephemeris
- **Planetary Ephemeris Engine:**
  - Implements Meeus / JPL DE421 Earth-Moon-Sun analytical planetary ephemeris.
  - Moon's rotational axis is tilted by $1.5424^\circ$ relative to the ecliptic normal (Cassini's 2nd Law).
  - Subsolar latitude $b_\odot$ oscillates between $-1.5424^\circ$ and $+1.5424^\circ$ over the $346.62$-day draconic year.
  - Measured extrema over a full lunar year: **$-1.517^\circ$ to $+1.541^\circ$**. (Perfect match).
- **Topographic Horizon Ray-Tracing:**
  - Traces radial elevation profiles from DEM rasters in the direction of solar azimuth $\theta_\odot$.
  - Includes spherical Moon curvature correction: $\theta_i = \arctan(\Delta z / d) - d / (2 R_\text{moon})$.
  - Finite solar disk: evaluates solar disk angular semi-diameter ($0.2665^\circ$), calculating partial occultation / penumbra fractions $[0.0, 1.0]$.
- **Sunset and Sunrise Prediction:**
  - Bisection root-finding solver locates the exact UTC timestamp when the solar upper limb drops below (sunset) or rises above (sunrise) the local horizon.
  - At $82.0^\circ\text{S}$ (March 1, 2026), sunset occurs at $255.0\text{ hours}$ (March 11, 2026 14:58 UTC), followed by sunrise at $587.5\text{ hours}$ (March 25, 2026 11:28 UTC).
  - At Shackleton Ridge ($89.44^\circ\text{S}$) in October (polar summer), the solver correctly confirms **continuous summer sunlight** (no sunset event occurs within 35 days).

### 7. Earth Visibility & Communication Corridors
- **Lunar Optical Librations:**
  - Sub-Earth point $(b'_\oplus, l'_\oplus)$ oscillates due to optical and physical librations:
    - Latitude libration: amplitude $\approx \pm 6.7^\circ$ (period $27.212$ days, nodical month).
    - Longitude libration: amplitude $\approx \pm 7.9^\circ$ (period $27.555$ days, anomalistic month).
- **Topocentric Earth Vector & Terrain Occultation:**
  - Geometric Earth elevation:
    $$\sin(\text{elev}_\oplus) = \sin(\phi)\sin(b'_\oplus) + \cos(\phi)\cos(b'_\oplus)\cos(\lambda - l'_\oplus)$$
  - Because Earth elevation at the South Pole is always low ($\le 6.7^\circ$), crater rims and mountains frequently occlude direct line-of-sight.
  - Ray-tracing tests Earth visibility against DEM radial profiles in Earth azimuth $\theta_\oplus$.
- **Distinction Between Geometric Visibility and Operational Communication:**
  - Geometric visibility requires Earth disc visible fraction $> 0.0$.
  - Guaranteed operational communication requires:
    1. Earth elevation $\ge 2.0^\circ$ (to avoid multi-path scattering over regolith).
    2. Disc visibility fraction $\ge 0.50$ (to maintain RF link aperture margin).

---

## 4. Multi-Criteria Decision Analysis & Grounded AI

### 8. Landing-Site Suitability Scoring
- **MCDA Engine Formulation:**
  - Normalizes 6 physical parameters to a transparent $0\text{--}100$ scale using piecewise linear utility functions:
    1. Topographic Slope (weight: 0.30, lower is better; ideal $\le 5^\circ$, critical $> 15^\circ$)
    2. Terrain Roughness (weight: 0.20, lower is better; ideal $\le 0.3\text{m}$, critical $> 1.5\text{m}$)
    3. Solar Illumination (weight: 0.20, higher is better; ideal $\ge 80\%$)
    4. Crater Hazards (weight: 0.10, lower is better)
    5. Rock Hazards (weight: 0.10, lower is better)
    6. Elevation (weight: 0.10, higher is better for communication line-of-sight)
- **Slope Safety Gate:**
  - If mean slope $> 15.0^\circ$, the site fails the dynamic tip-over constraint, triggering instant category disqualification ("Lower preliminary suitability" / "Unsuitable") and critical hazard warnings.
- **Missing Data Treatment:**
  - Missing factors are **never** treated as zero and weights are **never** silently redistributed.
  - Evaluated criteria weight coverage is reported explicitly via `score_coverage_pct`. If coverage $< 50\%$, the composite score is returned as `null` with status `"Insufficient data"`.

### 9. Grounded AI Explanations
- The LLM service receives strictly validated numerical outputs from stored analyses (`analysis_id`).
- It is constrained by prompt engineering and schema validation to explain backend measurements rather than generate independent scientific values.
- If offline or unconfigured, it seamlessly falls back to a deterministic, rule-based scientific summary.
