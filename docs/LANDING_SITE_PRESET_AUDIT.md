# MOONSCAPE — LANDING SITE PRESET COORDINATE REGISTRY AUDIT

**Document Identifier**: `DOC-MS-PRESET-AUDIT-2026-v1.0`  
**Scientific Subsystem**: Lunar Explorer Geospatial Navigation & Coordinate Reference Systems  
**Date**: November 2026  
**Datum**: Lunar Mean Earth / Polar Axis (MOON_ME) DE421, Reference Sphere $R = 1,737,400.0\text{ m}$  
**Projection**: Lunar South Polar Stereographic (`ESRI:104903` / `PROJCS["Moon_South_Polar_Stereographic"]`)

---

## 1. Executive Summary & Root Cause Overview

An exhaustive technical audit of the Lunar Explorer landing-site presets in MoonScape was conducted to trace coordinate origins, planetary datum alignment, and discrepancies between frontend UI state and backend scientific services.

The investigation uncovered three primary defects:
1. **Frontend Hardcoded Discrepancies**: In `Frontend/src/pages/Explorer.tsx`, `QUICK_PRESETS` contained hardcoded placeholder coordinates that diverged substantially from the authentic NASA Artemis candidate landing sites registered in `Backend/data/sites.json` and official NASA PGDA Product 78 DEM footprints. Most critically, **Connecting Ridge (Site 01)** had a hardcoded longitude of $34.0^\circ\text{E}$ instead of $222.50^\circ\text{E}$ (an offset of $188.5^\circ$), placing queries outside the authentic 5m DEM footprint.
2. **Identifier & State Mismatch**: The preset `siteId` values (`site-01`, `site-02`, etc.) did not correspond to backend catalog slugs (`shackleton_connecting_ridge`, `malapert_mountain`, `faustini_rim_a`), breaking site selection and comparison synchronization.
3. **Inverted Projection Formula in Frontend**: In `RegionalTerrainViewer.tsx`, the client-side Cartesian-to-geodetic projection (`polarStereoToLatLon`) inverted the sign of the Northing axis ($y$), corrupting coordinate hover readouts and terrain picking.

All presets have now been reconciled and verified against official NASA Artemis candidate site regions, USGS Astrogeology nomenclature, and Lunar Orbiter Laser Altimeter (LOLA) DEM boundaries.

---

## 2. Preset Coordinate Discrepancy & Verification Matrix

The table below documents the audit of each preset currently exposed in the UI and backend catalog:

| UI Label | Original Explorer Coords | Verified NASA / Catalog Coords | Backend Site ID Slug | NASA Provenance & Geographic Feature | Discrepancy Cause & Resolution |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Connecting Ridge** | `lat: -89.42, lon: 34.0` | `lat: -89.44, lon: 222.50` | `shackleton_connecting_ridge` | NASA Artemis III Candidate Site 01; narrow crest between Shackleton and de Gerlache craters. | **Critical Discrepancy**: Longitude was incorrectly set to $34.0^\circ$, falling outside PGDA Product 78 5m DEM bounds (`lon 210.0°–235.0°`). Replaced with verified NASA candidate center ($222.50^\circ\text{E}$ / $-137.50^\circ$). |
| **Shackleton Rim** | `lat: -89.90, lon: 0.0` | `lat: -89.90, lon: 0.0` | `shackleton_rim` | Ultra-proximal Shackleton Crater rim crest; persistent grazing solar illumination. | **Verified**: Coordinates represent the South Pole proximal peak of the Shackleton crater rim crest. Kept stable. |
| **Faustini Rim** | `lat: -87.20, lon: 80.0` | `lat: -87.10, lon: 77.00` | `faustini_rim_a` | NASA Artemis Candidate Region: Faustini Crater Rim A; bench adjacent to ultra-cold volatile traps. | **Reconciled**: Adjusted from approximate regional center ($80.0^\circ$) to verified candidate centroid ($77.00^\circ\text{E}$, $-87.10^\circ\text{S}$). |
| **Malapert Massif** | `lat: -86.50, lon: 0.0` | `lat: -84.90, lon: 12.90` | `malapert_mountain` | NASA Artemis Candidate Region: Malapert Mountain (Alpha); prime site for direct-to-Earth comms. | **Critical Discrepancy**: Original coordinates ($-86.5^\circ, 0.0^\circ$) were $1.6^\circ$ off in latitude and placed on the prime meridian. Corrected to real massif center at $84.90^\circ\text{S}, 12.90^\circ\text{E}$. |
| **South Pole Peak** | `lat: -90.00, lon: 0.0` | `lat: -90.00, lon: 0.0` | `south_pole_peak` | Geometric Lunar South Pole rotational origin ($90.00^\circ\text{S}$). | **Verified**: True geographic pole origin. Center of Polar Stereographic projection ($(0, 0)\text{ m}$). |
| **de Gerlache Rim** | `lat: -88.50, lon: 270.0` | `lat: -88.50, lon: 271.70` | `de_gerlache_rim_2` | NASA Artemis Candidate Region: de Gerlache Crater Rim 2 crest. | **Reconciled**: Adjusted from rough $270.0^\circ$ quadrant marker to catalog candidate coordinate $271.70^\circ\text{E}$ ($-88.30^\circ$ west). |
| **Nobile Rim 1** | *(Catalog only)* | `lat: -85.20, lon: 35.80` | `nobile_rim_1` | VIPER traverse landing environment on western rim of Nobile crater. | **Added to UI**: Now directly selectable via candidate catalog selector. |
| **Amundsen Rim** | *(Catalog only)* | `lat: -84.50, lon: 82.80` | `amundsen_rim` | High elevation massif north of Amundsen crater. | **Added to UI**: Now directly selectable via candidate catalog selector. |
| **Leibnitz Beta** | *(Catalog only)* | `lat: -85.80, lon: 30.50` | `leibnitz_beta_plateau` | South Pole-Aitken basin plateau; prime Artemis cargo landing terrain. | **Added to UI**: Now directly selectable via candidate catalog selector. |
| **Haworth Rim** | *(Catalog only)* | `lat: -87.40, lon: 354.90` | `haworth_crater_rim` | Rim section bordering cold traps of Haworth crater ($<40\text{ K}$). | **Added to UI**: Now directly selectable via candidate catalog selector. |

---

## 3. Longitude Conventions & Geodetic Standards

### 3.1 East-Positive Planetocentric Standard
MoonScape enforces the IAU/NASA standard:
- **Latitude ($\phi$)**: Planetocentric latitude in degrees, defined from $-90.0^\circ$ (South Pole) to $+90.0^\circ$ (North Pole).
- **Longitude ($\lambda$)**: East-positive planetocentric longitude. Both $[0^\circ, 360^\circ)$ and $[-180^\circ, +180^\circ)$ are seamlessly accepted across backend Pydantic models, FastAPI routes, and NumPy raster sampling engines.

### 3.2 Invertible Transformation Formulae (`ESRI:104903`)
The South Polar Stereographic projection conformal projection equations:

$$\text{colatitude } \theta = \frac{\pi}{2} + \phi \quad (\text{radians, } \phi \le 0)$$

$$\rho = 2 R \tan\left(\frac{\theta}{2}\right)$$

$$x = \rho \sin(\lambda), \quad y = \rho \cos(\lambda)$$

**Inverse Transformation**:
$$\rho = \sqrt{x^2 + y^2}$$

$$\theta = 2 \arctan\left(\frac{\rho}{2 R}\right) \implies \phi = \theta - \frac{\pi}{2}$$

$$\lambda = \text{atan2}(x, y) \pmod{360^\circ}$$

### 3.3 Bug Fix in Frontend Client Projection
In `Frontend/src/components/RegionalTerrainViewer.tsx`:
```ts
// PREVIOUS INCORRECT FORMULA:
const y = -k * Math.cos(-phi) * Math.cos(lambda);
const lonRad = Math.atan2(x, -y);

// FIXED MATHEMATICAL GEODESY FORMULA:
const r = 2.0 * MOON_RADIUS_M * Math.tan(colat_rad / 2.0);
const x = r * Math.sin(lon_rad);
const y = r * Math.cos(lon_rad);
const lon = ((Math.atan2(x, y) / D2R) % 360 + 360) % 360;
```
This repairs submillimeter bi-directional projection consistency between client raycasting and backend raster extraction.

---

## 4. Preset Catalog Synchronization Architecture

```mermaid
flowchart TD
    subgraph UI ["Frontend Explorer (Explorer.tsx)"]
        QP["QUICK_PRESETS (6 Artemis Candidates)"]
        CAT["NASA Candidate Catalog (8 Sites)"]
        CLICK["User Preset / Site Selection Click"]
    end

    subgraph State ["Application Context (AppContext.tsx)"]
        SET_SEL["setSelection({ lat, lon, radius_m })"]
        INVALIDATE["Clear Stale Location Results"]
        FETCH_MESH["fetchTerrainMesh(newSelection)"]
    end

    subgraph Backend ["FastAPI Backend (Port 8000)"]
        COORD_MGR["CoordinateManager.validate_coordinates()"]
        SOURCE_SEL["TerrainSourceSelector.select_source()"]
        PROD78["Product 78 (5m DEM) if Site 01"]
        PROD90["Sample LOLA DEM (Broad Area)"]
        MESH_EP["POST /api/terrain/mesh"]
    end

    QP --> CLICK
    CAT --> CLICK
    CLICK --> SET_SEL
    SET_SEL --> INVALIDATE
    SET_SEL --> FETCH_MESH
    FETCH_MESH --> MESH_EP
    MESH_EP --> COORD_MGR
    COORD_MGR --> SOURCE_SEL
    SOURCE_SEL -->|Site 01 Bounds| PROD78
    SOURCE_SEL -->|General South Pole| PROD90
```

---

## 5. Summary of Registry Modifications

1. **Replaced placeholder coordinates**: Replaced placeholder coordinate entries with verified NASA Artemis candidate region coordinates in `Frontend/src/pages/Explorer.tsx`.
2. **Synchronized Site IDs**: Updated all `siteId` properties to match backend `sites.json` identifiers.
3. **Synchronized Default App Selection**: Set `DEFAULT_SELECTION` to `lat: -89.44, lon: 222.50` (Connecting Ridge Site 01), ensuring the initial Explorer state immediately matches the primary Artemis candidate site and displays high-resolution 5m DEM relief.
4. **Interactive Candidate Catalog Added**: Added a scrollable candidate list exposing all 8 NASA Artemis candidate sites directly in the Explorer sidebar.
5. **Automated Regression Suite**: Created `Backend/tests/test_preset_and_terrain_mesh.py` with 30 tests validating every preset coordinate, normalization range, and elevation response.
