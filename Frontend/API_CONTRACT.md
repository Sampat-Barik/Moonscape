# Moonscape Fixed API Contract Specification

> **Base URL:** `http://localhost:8000`  
> **Interactive Documentation:** `http://localhost:8000/docs`

---

## 1. System Health
### `GET /api/health`
Returns system status, loaded LOLA dataset state, registered site count, active CRS, and scientific disclaimer.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "dem_dataset_loaded": true,
  "sites_loaded": 8,
  "crs": "ESRI:104903",
  "disclaimer": "DISCLAIMER: Suitability evaluations and hazard predictions..."
}
```

---

## 2. Candidate Landing Sites
### `GET /api/sites`
Returns all registered NASA Artemis III South Pole candidate landing sites.

**Response (200 OK):**
```json
[
  {
    "site_id": "shackleton_connecting_ridge",
    "name": "Shackleton Connecting Ridge",
    "latitude": -89.44,
    "longitude": 222.50,
    "elevation_m": -120.0,
    "mean_slope_deg": 6.8,
    "illumination_pct": 86.4,
    "earth_visibility_pct": 68.2,
    "description": "Narrow elevated ridge connecting Shackleton and de Gerlache craters...",
    "scientific_value": "Direct access to Shackleton crater cold traps...",
    "target_mission": "Artemis III",
    "priority": "high"
  }
]
```

---

### `GET /api/sites/{site_id}`
Returns details for a single candidate site by its unique slug.

**Response (200 OK):** CandidateSite object  
**Response (404 Not Found):** `{"detail": "Candidate landing site with ID 'xyz' not found."}`

---

### `POST /api/sites/compare`
Evaluates and ranks multiple candidate sites against user-defined or default weights.

**Request Body:**
```json
{
  "site_ids": ["shackleton_connecting_ridge", "malapert_mountain"],
  "weights": {
    "slope": 0.40,
    "illumination": 0.30,
    "communication": 0.20,
    "science": 0.10
  }
}
```

**Response (200 OK):**
```json
{
  "compared_sites": [
    {
      "site_id": "shackleton_connecting_ridge",
      "name": "Shackleton Connecting Ridge",
      "suitability_score": 83.25,
      "safety_rank": 1,
      "key_strengths": ["High solar power potential (86.4% illumination)"],
      "key_vulnerabilities": []
    }
  ],
  "top_recommended_site_id": "shackleton_connecting_ridge",
  "tradeoff_summary": "Comparative analysis evaluates 2 candidates...",
  "disclaimer": "..."
}
```

---

## 3. Cartographic & GIS Map Configuration
### `GET /api/map/config`
Provides map bounds, polar projection details, default zoom levels, and colormap ranges.

**Response (200 OK):**
```json
{
  "projection": "Lunar Polar Stereographic",
  "epsg_code": "ESRI:104903",
  "default_center": [-89.5, 0.0],
  "default_zoom": 5,
  "min_zoom": 1,
  "max_zoom": 12,
  "latitude_bounds": [-90.0, -80.0],
  "longitude_bounds": [-180.0, 180.0],
  "layers": [
    {
      "id": "lola_elevation",
      "name": "NASA LOLA Elevation",
      "unit": "meters",
      "color_scale": "viridis",
      "min_value": -4500.0,
      "max_value": 3500.0
    }
  ]
}
```

---

## 4. Point Terrain & Local Neighborhood Query
### `GET /api/terrain?lat={latitude}&lon={longitude}&radius_m={radius}`
Queries elevation, slope, surface roughness, relief variation, and preliminary landing safety classification at a specific coordinate and physical radius.

**Query Parameters:**
- `lat`: float (-90.0 to +90.0) — Planetocentric latitude in degrees
- `lon`: float (-180.0 to +360.0) — Longitude in degrees
- `radius_m`: float (optional, default: `50.0`, range `10.0` to `25000.0`) — Physical radius in meters

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
  "notes": "Analysis computed over physical disc of 50.0m radius.",
  "analysis_radius_m": 50.0,
  "elevation_summary": {
    "point_m": 1934.41,
    "min_m": 1931.2,
    "max_m": 1938.5,
    "mean_m": 1934.8,
    "variation_m": 7.3,
    "std_dev_m": 1.8,
    "units": "meters"
  },
  "slope_summary": {
    "point_deg": 3.78,
    "min_deg": 1.2,
    "max_deg": 6.4,
    "mean_deg": 3.65,
    "std_dev_deg": 1.1,
    "method": "NASA GSFC Precomputed Topographic Slope Raster",
    "units": "degrees",
    "ideal_pct": 88.0,
    "acceptable_pct": 12.0,
    "marginal_pct": 0.0,
    "critical_hazardous_pct": 0.0
  },
  "roughness_summary": {
    "point_m": 0.04,
    "min_m": 0.01,
    "max_m": 0.09,
    "mean_m": 0.04,
    "std_dev_m": 0.02,
    "method": "Root-Mean-Square (RMS) Residual Height Deviation from Local Neighborhood",
    "kernel_size": 3,
    "baseline_m": 15.0,
    "units": "meters"
  },
  "total_pixels_in_disc": 314,
  "valid_pixels_in_disc": 314,
  "nodata_pixels_in_disc": 0
}
```

---

## 5. Landing Zone Spatial Analysis
### `POST /api/analysis/run`
Executes spatial analysis across a candidate landing zone bounded by a physical distance radius in meters.

**Request Body:**
```json
{
  "center_lat": -89.46,
  "center_lon": 222.00,
  "radius_meters": 1000.0,
  "max_acceptable_slope_deg": 10.0,
  "max_acceptable_roughness_m": 0.5,
  "roughness_kernel_size": 3
}
```

**Response (200 OK):**
```json
{
  "analysis_id": "ANL-A1B2C3D4",
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
    "median_value": 1934.4,
    "std_dev": 32.5,
    "variation": 190.4,
    "units": "meters"
  },
  "slope": {
    "min_value": 0.8,
    "max_value": 18.2,
    "mean_value": 4.9,
    "median_value": 3.8,
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

---

## 6. Touchdown Hazard Prediction
### `POST /api/hazards/predict`
Detects and predicts surface touchdown hazards (craters, boulders, steep slopes, shadows) using either NASA LOLA DEM curvature algorithms or Deep Learning ML optical inference.

#### Mode A: Optical / SAR Image ML Inference (Phase 4)
Supports base64-encoded lunar surface imagery or onboard image file paths.

**Request Body (Image ML Query):**
```json
{
  "image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "spatial_resolution_mpp": 0.50,
  "confidence_threshold": 0.50
}
```

**Response (200 OK — Model Available):**
```json
{
  "status": "success",
  "detections": [
    {
      "label": "crater",
      "confidence": 0.942,
      "bounding_box": {
        "ymin": 30.0,
        "xmin": 30.0,
        "ymax": 60.0,
        "xmax": 60.0
      },
      "center_pixel": [45, 45],
      "pixel_diameter": 30.0,
      "estimated_size_m": 15.0,
      "severity": "high",
      "mask_rle": null
    },
    {
      "label": "rock",
      "confidence": 0.885,
      "bounding_box": {
        "ymin": 80.0,
        "xmin": 80.0,
        "ymax": 88.0,
        "xmax": 88.0
      },
      "center_pixel": [84, 84],
      "pixel_diameter": 8.0,
      "estimated_size_m": 4.0,
      "severity": "critical",
      "mask_rle": null
    }
  ],
  "crater_count": 1,
  "rock_count": 1,
  "warnings": [],
  "model_name": "LOLA-LROC Polar Hazard Detector",
  "model_version": "1.0.0",
  "limitations": "CRITICAL SCIENTIFIC NOTICE: Models trained exclusively on Apollo surface photography (equatorial/mid-latitude, sun elevation > 15 deg) are INVALIDATED for orbital South Pole landing corridors due to extreme grazing-angle illumination (< 1.5 deg), severe elongated shadows, permanently shadowed regions (PSRs), and polar stereographic distortion. Current status: Ground-truth validation required against high-resolution LROC NAC and LOLA polar datasets."
}
```

**Response (200 OK — Model Unconfigured / Unavailable):**
When no ML model is installed in `Backend/data/models/`, the API returns a graceful operational fallback without crashing:
```json
{
  "status": "not_available",
  "detections": [],
  "crater_count": null,
  "rock_count": null,
  "warnings": ["Hazard detection model is not configured."]
}
```

> **Scientific Calibration Rule:** If `spatial_resolution_mpp` is omitted or uncalibrated, `estimated_size_m` is strictly `null` and an explicit warning is returned. Pixels are NEVER converted to meters without authentic spatial calibration.

---

#### Mode B: Coordinate-based Topographic DEM Analysis
**Request Body (Coordinate Query):**
```json
{
  "center_lat": -89.90,
  "center_lon": 0.0,
  "radius_meters": 2000.0,
  "min_crater_diameter_m": 5.0,
  "boulder_detection_sensitivity": 0.8
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "hazard_assessment_id": "HAZ-E5F6G7H8",
  "center_lat": -89.90,
  "center_lon": 0.0,
  "radius_meters": 2000.0,
  "total_hazards_detected": 4,
  "craters_count": 2,
  "boulders_count": 1,
  "steep_slope_cells": 1,
  "shadow_coverage_pct": 0.0,
  "overall_hazard_level": "moderate",
  "hazards": [
    {
      "hazard_type": "crater",
      "latitude": -89.895,
      "longitude": 0.012,
      "estimated_size_m": 14.2,
      "severity": "high",
      "confidence_score": 0.88,
      "source": "LOLA_DEM_curvature"
    }
  ],
  "detections": [
    {
      "label": "crater",
      "confidence": 0.88,
      "estimated_size_m": 14.2,
      "severity": "high"
    }
  ],
  "crater_count": 2,
  "rock_count": 1,
  "warnings": [],
  "model_metadata": {
    "model_architecture": "Morphological Curvature & Gradient Anomaly Detector v1.2",
    "evaluation_dataset": "NASA LRO LOLA South Pole Ground Truth Catalog",
    "f1_score_crater_detection": 0.88
  },
  "disclaimer": "DISCLAIMER: Suitability evaluations and hazard predictions..."
}
```

---

## 7. Explainable Suitability Scoring
### `POST /api/score`
Calculates a composite suitability score (0-100) with complete factor breakdown.

**Request Body:**
```json
{
  "site_id": "shackleton_connecting_ridge"
}
```

**Response (200 OK):**
```json
{
  "site_id": "shackleton_connecting_ridge",
  "overall_suitability_score": 80.48,
  "suitability_category": "Nominal",
  "subscores": [
    {
      "criterion": "Topographic Slope",
      "raw_measurement": 6.8,
      "unit": "degrees",
      "normalized_subscore": 89.2,
      "weight": 0.35,
      "weighted_contribution": 31.22
    }
  ],
  "key_advantages": ["Favorable topographic slope profile", "Strong solar energy and thermal stability"]
}
```

---

## 8. AI Scientific Advisory
### `POST /api/ai/explain`
Generates physics-grounded scientific explanations and engineering trade-offs.

**Request Body:**
```json
{
  "site_id": "shackleton_connecting_ridge",
  "focus_topics": ["topography", "thermal", "traverse"]
}
```

**Response (200 OK):**
```json
{
  "explanation_id": "EXP-12345678",
  "target_site": "Shackleton Connecting Ridge",
  "executive_summary": "...",
  "geomorphology_assessment": "...",
  "thermal_and_power_assessment": "...",
  "key_engineering_tradeoffs": ["..."],
  "mitigation_strategies": ["..."]
}
```

---

## 9. Mission Reports Generation
### `POST /api/reports/generate`
Compiles evaluation data into exportable formats (`json`, `markdown`, or `html`).

**Request Body:**
```json
{
  "site_id": "malapert_mountain",
  "mission_title": "Artemis III Base Camp Staging Assessment",
  "output_format": "markdown"
}
```

**Response (200 OK):**
```json
{
  "report_id": "RPT-98765432",
  "output_format": "markdown",
  "content": "# Artemis III Base Camp Staging Assessment\n...",
  "structured_summary": { ... }
}
```

---

## 10. NASA Lunar Dataset Catalog & Coverage (Phase 2)

### `GET /api/data/catalog`
Lists all registered NASA lunar datasets, download profiles (`profile_a`, `profile_b`, `profile_c`), and current installation statuses.

**Response (200 OK):**
```json
{
  "total_datasets": 11,
  "installed_count": 1,
  "default_profile": "profile_b",
  "profiles": {
    "profile_a": {
      "name": "Minimum Working Installation",
      "total_size_mb": 521.10,
      "datasets": ["pgda90_ldem", "pgda90_ldsm", "pgda90_ldec"]
    },
    "profile_b": {
      "name": "Recommended Installation",
      "total_size_mb": 1241.23,
      "datasets": ["pgda90_ldem", "pgda90_ldsm", "pgda90_ldec", "pgda90_ldem_err", "pgda90_ldem_effres", "pgda90_ldsm_err"]
    }
  },
  "datasets": [
    {
      "id": "pgda90_ldem",
      "name": "LOLA South Pole 80m Elevation DEM",
      "source_provider": "NASA GSFC / LOLA Science Team",
      "product_id": "LDEM_80S_80MPP_ADJ",
      "filename": "LDEM_80S_80MPP_ADJ.TIF",
      "size_mb": 180.40,
      "spatial_resolution_m": 80.0,
      "units": "meters",
      "tier": "local_required",
      "byte_range_supported": true,
      "status": "available",
      "is_installed": true,
      "bounds": { "min_lat": -90.0, "max_lat": -80.0, "min_lon": -180.0, "max_lon": 360.0 }
    }
  ]
}
```

### `GET /api/data/status`
Returns real-time disk presence and GeoTIFF validation details for all datasets.

### `GET /api/data/coverage?lat={latitude}&lon={longitude}`
Evaluates spatial coverage across all NASA tiers for the given lunar coordinate.

**Query Parameters:**
- `lat`: Latitude in degrees (-90.0 to 90.0)
- `lon`: Longitude in degrees (-180.0 to 360.0)

**Response (200 OK):**
```json
{
  "valid_coordinate": true,
  "latitude": -89.5,
  "longitude": 220.0,
  "in_south_pole_zone": true,
  "best_installed_resolution_m": 5.0,
  "total_covering_sources": 5,
  "installed_covering_sources": 2,
  "layers": [
    {
      "source_id": "pgda_product78",
      "name": "NASA PGDA Product 78 (LOLA 5m/pixel High-Resolution Candidate Site DEM)",
      "tier": "Tier 2: High-Resolution Regional",
      "covers": true,
      "is_installed": true,
      "resolution_m": 5.0,
      "status": "available",
      "detail": "Site 01 Shackleton Connecting Ridge"
    }
  ]
}
```

---

## 11. NASA Data Acquisition & Download Management (Phase 2)

### `POST /api/data/download/{dataset_id}`
Triggers background streaming download with byte-range resume and disk headroom validation.

**Response (200 OK):**
```json
{
  "task_id": "DL-A1B2C3D4",
  "dataset_id": "pgda90_ldem",
  "filename": "LDEM_80S_80MPP_ADJ.TIF",
  "status": "downloading",
  "bytes_downloaded": 10485760,
  "total_bytes": 189158392,
  "progress_pct": 5.5,
  "speed_mbps": 4.25,
  "error_message": null
}
```

### `POST /api/data/download/profile/{profile_name}`
Enqueues all datasets in a preset profile (`profile_a`, `profile_b`, `profile_c`).

### `GET /api/data/downloads/{task_id}`
Queries live progress, speed in MB/s, and completion status.

### `POST /api/data/downloads/{task_id}/cancel`
Cancels an active download stream.
