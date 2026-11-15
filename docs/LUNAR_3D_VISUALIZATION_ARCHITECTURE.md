# MoonScape — Lunar 3D Visualization Architecture

**Document ID:** LUNAR-3D-ARCH-001  
**Project:** MoonScape (NASA Lunar South Pole Analysis Platform)  
**Authors:** Senior Graphics Engineer, CesiumJS Geospatial Specialist, Planetary GIS Specialist  
**Status:** Approved Architecture Specification  
**Date:** November 15, 2026  

---

## 1. Architectural Dilemma & Requirements Analysis

### 1.1 Existing Implementation vs. Scientific Terrain Reality
The existing MoonScape map implementation in `Frontend/src/components/LunarMap.tsx` renders a normalized unit sphere ($R = 1$) in Three.js textured with equirectangular orbital mosaics (e.g. LROC WAC 2K, LOLA 8-bit bump). While visually compelling for global context, an equirectangular unit sphere exhibits severe physical limitations when applied to lunar polar mission engineering:

| Architectural Aspect | Existing Global Sphere (`LunarMap.tsx`) | Scientific South Pole 3D Terrain Requirement |
|---|---|---|
| **Coordinate System** | Spherical polar coordinates $(r, \theta, \phi)$ on unit sphere. | Cartographic Lunar South Polar Stereographic (`ESRI:104903` / IAU 2000: 30120) with physical metric coordinates $(X, Y, Z)$ centered at South Pole ($90^\circ\text{S}$). |
| **Polar Singularity** | All meridian lines converge to a single pole vertex; severe texture pinching and geometric distortion beyond $80^\circ\text{S}$. | Conformal polar stereographic projection preserving true angles and local area shapes without polar pole pinching. |
| **Surface Relief** | 8-bit visual grayscale bump map (`ldem_3_8bit.jpg`) modifying surface lighting normals without geometric vertex displacement. | True metric elevation relief ($Z$ in meters) extracted from NASA LOLA 80m and PGDA Product 78 (1-5 m/pixel) digital elevation models. |
| **Spatial Resolution** | Equator $\approx 5.5\text{ km/pixel}$; Polar regions $< 80^\circ\text{S}$ compressed into $< 2\%$ of the total texture pixels. | Sub-windowed raster grids matching actual sensor resolutions ($1\text{ m}$ to $80\text{ m}$ per sample) over 50m–25,000m candidate mission footprints. |
| **Scientific Overlays** | Simple 2D billboard sprites for candidate sites and a static South Pole label. | Georeferenced vector overlays: contiguous landing corridors, slope gradient maps, illumination masks, and detected crater/boulder hazard footprints. |

### 1.2 The Need for Two Distinct Visualization Modes
Attempting to force both global orbital reconnaissance and micro-scale terrain touchdown inspection into a single Three.js scene causes floating-point precision jitter (Z-fighting at millimetric scales on a 1,737.4 km body) and texture resolution degradation.

Therefore, MoonScape defines **two distinct, tightly coupled visualization modes**:
1. **Mode A — Global Moon (Three.js):**
   - Cinematic orbital overview of the lunar sphere ($R = 1,737.4\text{ km}$ scaled to Three.js world units).
   - Real LROC WAC global mosaic with realistic vacuum directional lighting and earthshine.
   - Interactive camera orbit, South Pole glide animation, site pins, and coordinate picking.
2. **Mode B — Georeferenced Regional Terrain Relief (Three.js South Pole Mesh Engine):**
   - High-fidelity 3D elevation mesh generated directly from authentic NASA LOLA / PGDA Product 78 DEM elevation samples.
   - Physical East-North-Up (ENU) metric space georeferenced to the user-selected coordinates.
   - Dynamic scientific color scales (Elevation, Slope, Roughness, Illumination) with numeric legends.
   - Dynamic terrain profiling (cross-sectional elevation slice along any azimuth).
   - Real hazard footprint rings (craters, boulders) and contiguous candidate safe zones.

---

## 2. In-Depth CesiumJS vs. Three.js Evaluation

A primary objective of this architecture is evaluating the appropriateness of CesiumJS for lunar polar terrain visualization.

### 2.1 CesiumJS Capabilities & Lunar Constraints
CesiumJS is the industry standard for terrestrial planetary GIS, but its architecture is inherently optimized for Earth (WGS84 ellipsoid, $a = b = 6,378,137\text{ m}$, $c = 6,356,752\text{ m}$):

1. **Terrain Provider Incompatibility:**
   - Cesium's standard 3D terrain providers (`createWorldTerrain`, `CesiumTerrainProvider`) query Quantized-Mesh tiles hosted on Cesium ion that represent terrestrial Earth elevation (SRTM, NED, Bathymetry).
   - Cesium has **no built-in lunar terrain tile server**. Applying Earth terrain tiles to a lunar ellipsoid creates catastrophic geographic distortion.
   - Generating a custom Quantized-Mesh lunar terrain pyramid requires specialized server-side offline tiling pipelines (e.g. `cesium-terrain-builder` or Cesium ion private asset pipelines) that do not exist locally on the client laptop.
2. **Body-Fixed Coordinate & Projection Handling:**
   - Cesium supports custom ellipsoids via `new Cesium.Ellipsoid(1737400, 1737400, 1737400)`. However, Cesium's camera controller, tiling schemas (`GeographicTilingScheme`), and imagery reprojections assume longitude ranges and horizon culling tailored for Earth.
   - Polar Stereographic rasters (`ESRI:104903`) cannot be projected natively onto a Cesium globe without on-the-fly GDAL reprojection to EPSG:4326, which introduces re-sampling artifacts and substantial latency.
3. **Micro-Scale Terrain Precision:**
   - In lunar landing site engineering ($50\text{ m}$ to $5,000\text{ m}$ footprints), camera distances are measured in tens to hundreds of meters. Cesium's camera collision and near-plane clipping are tuned for planetary orbits and regional flights ($> 1,000\text{ m}$).
4. **Memory Footprint & Dual-Canvas Conflicts:**
   - Running a CesiumJS `Viewer` and a Three.js `WebGLRenderer` simultaneously consumes $> 1.8\text{ GB}$ of VRAM and risks browser WebGL context loss (`CONTEXT_LOST_WEBGL`).

### 2.2 Architectural Decision: Role of CesiumJS and Three.js
- **Primary Detailed Terrain Renderer:** **Three.js** is selected as the primary engine for both Mode A (Global Moon) and Mode B (Detailed South Pole 3D Regional Terrain). Three.js allows direct, hardware-accelerated vertex displacement from raw DEM elevation rasters, custom GLSL slope/elevation shader colormaps, interactive elevation cross-sections, and zero overhead vector hazard rendering.
- **CesiumJS Integration:** Retained as an **on-demand IAU Lunar Ellipsoid Macro-Viewer** (`CesiumLunarViewer.tsx`). CesiumJS is strictly lazy-loaded: when the operator activates Cesium mode, the Three.js render loop is suspended and Three.js resources are preserved; when returning to Three.js, the Cesium viewer is cleanly destroyed, preventing WebGL context starvation.

---

## 3. Data Pipeline & Backend Mesh Contract

### 3.1 Eliminating Heavy Client-Side DEM Processing
The raw LOLA South Pole DEM GeoTIFF is $400+\text{ MB}$, and high-resolution PGDA Product 78 rasters exceed $1\text{ GB}$. Downloading raw rasters to the browser causes out-of-memory errors and sluggish network transfer.

The backend exposes a windowed, downsampled grid endpoint:
`POST /api/terrain/mesh`

**Request Payload:**
```json
{
  "latitude": -89.44,
  "longitude": 222.50,
  "radius_m": 500.0,
  "grid_size": 64
}
```

**Response Payload:**
```json
{
  "status": "ready",
  "center": {
    "latitude": -89.44,
    "longitude": 222.50,
    "x_polar_m": 7241.1,
    "y_polar_m": -15230.4
  },
  "radius_m": 500.0,
  "grid_size": 64,
  "resolution_m": 15.62,
  "elevation_grid": [[...], ...],
  "slope_grid": [[...], ...],
  "min_elevation_m": -1842.5,
  "max_elevation_m": -1710.2,
  "mean_elevation_m": -1780.8,
  "relief_m": 132.3,
  "dataset_name": "NASA LOLA 80m DEM (PGDA Product 78 prioritized)",
  "crs": "ESRI:104903 (Lunar South Polar Stereographic)",
  "disclaimer": "Preliminary engineering model; remote sensing data."
}
```

This compact JSON payload ($\approx 40\text{ KB}$ for a $64 \times 64$ grid) downloads in $< 20\text{ ms}$ over localhost, allowing instantaneous 60 FPS 3D mesh reconstruction.

---

## 4. Coordinate Transformations & Mathematical Georeferencing

### 4.1 Lunar South Polar Stereographic (`ESRI:104903`)
Given planetocentric latitude $\phi \in [-90^\circ, -80^\circ]$ and longitude $\lambda \in [0^\circ, 360^\circ]$, the projection coordinates $(x, y)$ on the conformal plane tangent to the South Pole ($R = 1,737,400\text{ m}$) are:

$$k = \frac{2 R}{1 + \sin(-\phi)}$$
$$x = k \cos(-\phi) \sin(\lambda)$$
$$y = -k \cos(-\phi) \cos(\lambda)$$

### 4.2 Local Tangent Plane (ENU) for 3D Mesh
To eliminate numeric jitter in Three.js, the terrain mesh is placed in a local coordinate frame with origin at the center $(x_0, y_0, z_0)$:
$$X_{\text{local}} = x - x_0$$
$$Y_{\text{local}} = z_{\text{elev}} - z_0$$
$$Z_{\text{local}} = -(y - y_0)$$

When the operator clicks a vertex $(X_{\text{local}}, Y_{\text{local}}, Z_{\text{local}})$ on the 3D terrain mesh:
1. The local coordinates are inverted to projected coordinates $(x, y)$.
2. The exact inverse polar stereographic formula is applied to obtain $(\phi_{\text{picked}}, \lambda_{\text{picked}})$.
3. The coordinate is validated against the $80^\circ\text{S} - 90^\circ\text{S}$ boundary.
4. The exact physical coordinate is submitted to FastAPI `/api/analysis/run`.

---

## 5. Summary of Architectural Guarantees
- **No Synthetic Terrain:** All vertices are displaced by genuine NASA LOLA / PGDA elevation data.
- **Zero WebGL Context Loss:** Lazy loading and strict resource disposal prevent multi-canvas VRAM exhaustion.
- **Bi-directional Accuracy:** Point clicked on 3D terrain $\equiv$ point analyzed by FastAPI.
- **Performance:** 60 FPS rendering on NVIDIA RTX 5070 GPU with $< 50\text{ MB}$ client memory footprint.
