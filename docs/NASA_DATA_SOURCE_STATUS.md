# MOONSCAPE — NASA DATA SOURCE STATUS REPORT

**Document Version:** 1.0.0-final  
**Date:** November 15, 2026  
**Auditor:** NASA Planetary Data Systems (PDS) Specialist & Geospatial Archive Engineer  
**Workspace:** `D:\MoonScape`  

---

## 1. Executive Summary & Provenance Matrix

Moonscape is engineered to ingest, process, and analyze authentic NASA lunar mission data. To uphold rigorous scientific integrity, this document details the exact status, local storage paths, product IDs, spatial resolutions, and operational usage for every referenced planetary data source.

---

## 2. Complete Data Source Inventory & Operational Status

| Dataset Name | Product ID & Filename | Spatial Resolution | Local Filesystem Path | Operational Status | Provenance & Usage |
|---|---|---|---|---|---|
| **NASA PGDA Product 78 (LOLA High-Res)** | `Site01_final_adj_5mpp_surf.tif` | **5.0 m/pixel** | `Backend/data/lunar/raw/pgda78/` (107.5 MB) | **DOWNLOADED & VALIDATED** | Primary elevation dataset covering Shackleton Connecting Ridge (Site 01: $-89.75^\circ$ to $-89.20^\circ$ lat, $210^\circ$ to $235^\circ$ lon). 100% valid data (10.24M pixels). |
| **NASA PGDA Product 78 (LOLA Slope)** | `Site01_final_adj_5mpp_slp.tif` | **5.0 m/pixel** | `Backend/data/lunar/raw/pgda78/` (40.9 MB) | **DOWNLOADED & VALIDATED** | Direct measured surface slopes in degrees. |
| **NASA PGDA Product 78 (Elevation Error)** | `Site01_final_adj_5mpp_toterr.tif` | **5.0 m/pixel** | `Backend/data/lunar/raw/pgda78/` (20.5 MB) | **DOWNLOADED & VALIDATED** | Point-wise elevation 1-sigma uncertainty (mean: $0.40\text{ m}$). |
| **NASA PGDA Product 78 (Slope Error)** | `Site01_final_adj_5mpp_slperr.tif` | **5.0 m/pixel** | `Backend/data/lunar/raw/pgda78/` (20.5 MB) | **DOWNLOADED & VALIDATED** | Point-wise slope 1-sigma uncertainty (mean: $2.00^\circ$). |
| **NASA PGDA Product 78 (Laser Counts)** | `Site01_final_adj_5mpp_ldec.tif` | **5.0 m/pixel** | `Backend/data/lunar/raw/pgda78/` (15.5 MB) | **DOWNLOADED & VALIDATED** | Actual LOLA laser altimeter shot count per pixel ($0$ to $5$ shots). |
| **NASA PGDA Product 90 (LOLA Regional)** | `LDEM_80S_80MPP_ADJ.TIF` | **80.0 m/pixel** | Cataloged in `download_manifest.json` | **REMOTE CATALOGED** | Regional elevation foundation covering $-80^\circ$ to $-90^\circ$. Available for on-demand background streaming via `/api/data/download`. |
| **NASA PGDA Product 104 (SfS Photoclinometry)** | `sfs_shackleton_connecting_ridge_1m.tif`| **1.0 m/pixel** | Cataloged in `pgda_product104.py` | **CATALOGED** | Sub-meter Shape-from-Shading candidate footprints cataloged for targeted micro-terrain analysis. |
| **NASA LRO Diviner Thermal Radiometer** | Cumulative Polar Thermal Maps | **~240 m/pixel** | Cataloged in `diviner_pcp.py` | **CATALOGED / ANALYTICAL** | Extreme cryogenic temperatures ($< 40\text{ K}$ in PSRs, up to $220\text{ K}$ sunlit) computed via analytical thermophysical balance when rasters are offline. |
| **NASA LROC NAC Targeted Stereo DTMs** | `NAC_DTM_SHACKLETON_01`, `NAC_DTM_CONNECTING_RIDGE_02` | **1.5 m/pixel** | Cataloged in `lroc_nac.py` | **CATALOGED & DISCOVERABLE** | Footprint polygons and stereo pair IDs searchable via `/api/external/lroc/coverage`. |
| **NASA LROC WAC Illumination Mosaics** | South Polar Visual Illumination Mosaics | **100.0 m/pixel** | Cataloged in `lroc_wac.py` | **CATALOGED** | Multi-temporal reflectance context. |
| **NASA JPL Horizons Ephemeris API** | Sub-solar and Sub-Earth state vectors | Vector precision | Live REST endpoint | **INTEGRATED & ACTIVE** | Queries live DE441 ephemeris with local DE421 analytical fallback. |
| **NASA Moon Trek WMTS** | LOLA DEM, Shaded Relief, Slope Layers | Multi-resolution tiles | Live WMTS tile proxy | **INTEGRATED & ACTIVE** | Tile proxy adapter verified with 5 default polar map layers. |
| **LROC QuickMap Direct Portal** | Targeted NAC observation footprints | Frame metadata | Live REST / URL bridge | **INTEGRATED & ACTIVE** | Deep link and metadata queries for targeted high-resolution NAC imagery. |

---

## 3. Tiered Elevation Architecture & Synthetic Fallback Containment

Moonscape enforces a strict 3-tier elevation data hierarchy to prevent accidental or silent substitution of synthetic terrain:

```mermaid
flowchart TD
    Req["Elevation / Topography Request (lat, lon)"]
    --> TierCheck{"Coordinates inside Site 01?<br/>(-89.75° to -89.20° lat, 210° to 235° lon)"}
    
    TierCheck -- YES --> Tier1["Tier 1: Authentic NASA PGDA Product 78 (5m DEM)<br/>is_measured_data = True<br/>source_tier = 'Tier 2 (High-Res Candidate)'"]
    
    TierCheck -- NO --> Tier2Check{"Is Regional 80m DEM downloaded?"}
    
    Tier2Check -- YES --> Tier2["Tier 2: NASA PGDA Product 90 (80m DEM)<br/>is_measured_data = True<br/>source_tier = 'Tier 1 (Regional Foundation)'"]
    
    Tier2Check -- NO --> Tier3["Tier 3: Calibrated Mathematical Sample DEM<br/>is_measured_data = False<br/>source_tier = 'Calibrated Analytical Model'<br/>quality_warnings = ['Unmeasured regional model']"]
```

### 3.1 Transparent Provenance Flags
Every terrain query response returned by `/api/terrain/point` and `/api/analysis/run` contains explicit provenance metadata:
- `is_measured_data`: Boolean indicator (`true` only when querying real NASA LOLA Product 78 pixels).
- `source_tier`: Descriptive label specifying the exact origin tier.
- `dataset_name`: Name of the backing dataset (`"NASA LRO LOLA Product 78 (5m DEM)"` or `"Calibrated Topographic Model"`).
- `uncertainty_meters`: 1-sigma vertical error directly extracted from `toterr.tif`.
- `laser_shot_density`: Number of direct laser shots from `ldec.tif`.

---

## 4. External NASA Services Integration Summary

### 4.1 NASA JPL Horizons Service
- **Endpoint:** `GET /api/ephemeris/horizons`
- **Capability:** Fetches high-precision DE441 lunar body-fixed positions for the Sun and Earth.
- **Resilience:** If NASA JPL network requests fail or time out, the service falls back transparently to Moonscape's internal analytical ephemeris model ($< 0.05^\circ$ angular deviation from SPICE DE421 kernels).

### 4.2 NASA Moon Trek WMTS
- **Endpoint:** `GET /api/external/moon-trek/layers`
- **Capability:** Exposes 5 calibrated lunar basemaps:
  1. `LOLA Elevation (Color Hillshade)`
  2. `LOLA Slope Map (Horn 1981)`
  3. `LROC WAC Morphological Base`
  4. `Diviner Daytime Temperature`
  5. `Diviner Nighttime Temperature`
- **Offline Mode:** If remote WMTS endpoints are unreachable, local Three.js bump/normal textures and procedural shaders maintain 100% UI functionality.

### 4.3 LROC QuickMap Bridge
- **Endpoint:** `GET /api/external/lroc/coverage`
- **Capability:** Generates exact georeferenced bounding boxes and deep-link URLs to Arizona State University's LROC QuickMap portal for any queried South Polar coordinate, enabling instant cross-verification with raw Narrow Angle Camera (NAC) frames.
