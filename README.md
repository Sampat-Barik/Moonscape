# Moonscape — Lunar South Pole Landing-Site Analysis Platform

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue.svg?logo=python&logoColor=white)](https://python.org)
[![NASA Data](https://img.shields.io/badge/Data-NASA%20PDS%20%2F%20LOLA%20%2F%20LROC-red.svg)](https://pgda.gsfc.nasa.gov)
[![CRS](https://img.shields.io/badge/CRS-ESRI%3A104903%20(Polar%20Stereographic)-green.svg)](https://epsg.io/104903)
[![Tests](https://img.shields.io/badge/Tests-162%20Passed-brightgreen.svg)](https://pytest.org)

Moonscape is an open-source, scientifically grounded lunar South Pole landing-site suitability and hazard analysis platform. Designed for local development on high-performance laptops (AMD Ryzen 9 / NVIDIA RTX) with authentic NASA planetary datasets, it evaluates candidate Artemis landing locations between 80°S and 90°S using multi-criteria decision analysis (MCDA), Horn (1981) geodetic slope modeling, RMS surface roughness, JPL DE421 solar ephemeris, morphological hazard detection, grounded AI explanations, and automated ReportLab PDF mission reports.

---

## 1. Project Architecture

The Moonscape repository is organized into four distinct tiers:

```text
MoonScape/
├── maths/                             # Pure mathematical & astronomical core (zero backend dependencies)
│   ├── geodesy.py                     # Planetocentric <-> Polar Stereographic (ESRI:104903) conversions
│   ├── topography.py                  # Horn (1981) 8-neighbor gradient & RMS surface roughness
│   ├── curvature.py                   # 2D Laplacian curvature for crater rim & basin delineation
│   ├── illumination_geometry.py       # JPL DE421 solar ephemeris, subsolar coords, & horizon ray-tracing
│   ├── scoring.py                     # Multi-criteria decision analysis (MCDA) & piecewise utility functions
│   └── tests/                         # Mathematical precision unit tests
│
├── Backend/                           # Production FastAPI scientific backend
│   ├── app/
│   │   ├── main.py                    # FastAPI entrypoint, lifespan startup, & CORS configuration
│   │   ├── core/                      # Settings (pydantic-settings), physical constants, & logging
│   │   ├── config/                    # Hardware resource budgets, dataset registries, & hazard limits
│   │   ├── schemas/                   # Pydantic v2 data contracts for all 16 endpoints
│   │   ├── routes/                    # API route definitions (11 Core + 5 Data Management)
│   │   └── services/                  # Business logic & scientific pipelines
│   │       ├── terrain_analysis.py    # Multi-resolution raster window processing engine
│   │       ├── dem_service.py         # GeoTIFF reading, spatial indexing, & bounding boxes
│   │       ├── hazard_detection.py    # ML inference service & optical safeguards
│   │       ├── hazard_service.py      # Morphological DEM curvature hazard analyzer
│   │       ├── illumination.py        # Solar geometry, horizon ray-tracing, & PSR classification
│   │       ├── site_scoring.py        # MCDA suitability scoring engine with slope safety gate
│   │       ├── ai_explainer.py        # Grounded AI scientific explainer (Gemini / OpenAI / Mock)
│   │       ├── report_generator.py    # 19-element scientific report generator (JSON & ReportLab PDF)
│   │       ├── data_management/       # Local storage, LRU raster cache, & HTTP Range downloads
│   │       └── data_sources/          # Adapters (PGDA 90, PGDA 78 Site 01, PGDA 104, Diviner, LROC)
│   ├── data/lunar/                    # Raw NASA GeoTIFFs, spatial indexes, and cache directories
│   ├── scripts/                       # CLI downloaders, benchmark scripts, and validation runners
│   ├── tests/                         # Comprehensive test suites (126 automated tests)
│   ├── requirements.txt               # Pinned Python package dependencies
│   └── pytest.ini                     # Pytest runner configuration
│
├── docs/                              # Scientific methodology guides, citations, & specifications
│   ├── frontend_integration_guide.md  # 12-step data flow & endpoint verification guide
│   ├── terrain_analysis_guide.md      # Horn (1981) slope & RMS roughness derivation
│   ├── illumination_analysis_guide.md # JPL DE421 ephemeris & PSR detection guide
│   ├── landing_suitability_methodology.md # MCDA scoring matrices & lander safety thresholds
│   ├── hazard_model_integration.md    # Hazard detection contract & optical limitations
│   ├── ai_explainer_guide.md          # Grounded AI prompt engineering & fallback architecture
│   ├── report_generation_guide.md     # 19-element scientific report schema & PDF styling
│   ├── lunar_dataset_inventory.md     # NASA PDS product registry & metadata
│   └── download_manifest.json         # SHA-256 checksums & NASA PDS URLs
│
└── Frontend/                          # Interactive client application
    ├── index.html                     # Standalone mission control aerospace dashboard
    ├── app.js                         # Asynchronous client controller (12-step workflow)
    ├── style.css                      # NASA dark-theme responsive design
    ├── api.ts                         # Fully typed TypeScript API client (AbortController timeouts)
    ├── types.ts                       # TypeScript interfaces aligned with FastAPI backend
    └── API_CONTRACT.md                # Shared JSON contracts and schema specifications
```

---

## 2. Installation & Windows Setup

### Hardware Optimization Target
- **CPU:** AMD Ryzen 9 8940HX (16 logical cores)
- **RAM:** 16 GB (In-memory raster window cache capped at 256 MB)
- **GPU:** NVIDIA GeForce RTX 5070 Laptop GPU (8 GB VRAM reserved for vision inference)
- **OS:** Windows 10 / 11 64-bit with PowerShell

### Setup Steps
1. **Clone the repository:**
   ```powershell
   git clone https://github.com/Sampat-Barik/Moonscape.git
   cd MoonScape
   ```

2. **Create and activate a virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   python -m pip install --upgrade pip
   pip install -r Backend/requirements.txt
   ```

---

## 3. Environment Variables

Create a `Backend/.env` file (or set variables in your environment). All settings have safe defaults:

| Variable | Type | Default | Description |
|---|---|---|---|
| `ENVIRONMENT` | string | `development` | Runtime mode (`development`, `staging`, `production`) |
| `API_V1_STR` | string | `/api` | Base API prefix |
| `PROJECT_NAME` | string | `Moonscape Lunar Landing API` | Title displayed in Swagger UI |
| `DATA_ROOT_DIR` | string | `Backend/data/lunar` | Directory for raw NASA GeoTIFF rasters |
| `CACHE_DIR` | string | `Backend/data/lunar/cache` | Directory for tiled spatial window cache |
| `CORS_ORIGINS` | list | `["http://localhost:3000", ...]` | Permitted CORS frontend origins |
| `AI_PROVIDER` | string | `mock` | Active AI backend (`mock`, `gemini`, `openai`) |
| `GEMINI_API_KEY` | string | `""` | Google Gemini API key (optional) |
| `OPENAI_API_KEY` | string | `""` | OpenAI API key (optional) |
| `LLM_MODEL_NAME` | string | `gemini-1.5-flash` | Target model for scientific explanations |
| `MAX_CACHE_MEMORY_MB` | int | `256` | RAM ceiling for in-memory LRU raster cache |

> [!NOTE]
> If `AI_PROVIDER` is set to `mock` or if API keys are left unset/offline, the backend automatically uses its deterministic scientific fallback engine. It will never fail or return blank explanations.

---

## 4. NASA Dataset Setup

Moonscape utilizes authentic NASA Planetary Data System (PDS) elevation rasters:

| Dataset Tier | NASA Product ID | Resolution | Coverage | Purpose |
|---|---|---|---|---|
| **Tier 1** | PGDA Product 90 (`LDEM_80S_100M`) | 80 m/pixel | 80°S to 90°S | Regional topographic foundation |
| **Tier 2** | PGDA Product 78 (`Site01_final_adj_5mpp_surf`) | 5 m/pixel | Shackleton Ridge | High-resolution landing corridor |
| **Tier 3** | PGDA Product 104 / Diviner / LROC | 1 m – 500 m | Variable | Optical, thermal, and slope validation |

### Downloading Data
```powershell
# Download Profile B (Recommended regional foundation, ~1.24 GB)
python Backend/scripts/download_nasa_data.py --profile profile_b

# Or download a specific dataset (e.g. Site 01 Shackleton 5m DEM)
python Backend/scripts/download_nasa_data.py --dataset pgda78_site01_surf
```
*If offline, Moonscape automatically generates a synthetic lunar South Pole crater DEM (`Backend/data/lunar/sample_dem.tif`) so all features function immediately.*

---

## 5. Hazard Detection Model Setup

- **Morphological DEM Detector:** Built-in 2D Laplacian curvature and gradient anomaly detector (`maths/curvature.py`). Runs out of the box on elevation rasters without external weights.
- **Optical ML Inference Service:** `Backend/services/hazard_detection.py` provides inference hooks for deep-learning crater/boulder models (YOLO / U-Net / Detectron2).
- **Graceful Unconfigured Handling:** If model weights (`Backend/models/hazard_detector.pt` or `.onnx`) are not present, image requests return HTTP 200 with `status: "not_available"`, counts as `null`, and explicit guidance.
- **Uncalibrated Optical Safeguard:** Optical predictions without physical pixel scale metadata are flagged with scientific caveats, preventing ungrounded risk assessments.

---

## 6. API Endpoints Overview

### Core Analysis Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Backend status, version, GPU telemetry, and CRS metadata |
| `GET` | `/api/sites` | Catalog of Artemis candidate landing locations |
| `GET` | `/api/sites/{site_id}` | Detailed coordinates and physical specs for a single site |
| `GET` | `/api/map/config` | Cartographic Polar Stereographic (`ESRI:104903`) bounds and layers |
| `GET` | `/api/terrain` | Point query for elevation, Horn slope, RMS roughness, and provenance |
| `POST` | `/api/analysis/run` | Full spatial landing zone analysis; yields cached `analysis_id` |
| `POST` | `/api/hazards/predict` | Crater basin and boulder hazard delineation (DEM or optical) |
| `POST` | `/api/sites/compare` | Side-by-side MCDA comparison of multiple candidate sites |
| `POST` | `/api/score` | Transparent multi-criteria suitability scoring (0–100 scale) |
| `POST` | `/api/ai/explain` | Grounded scientific explanation of an existing `analysis_id` |
| `POST` | `/api/reports/generate` | Generates 19-element JSON or downloadable binary PDF report |

### Data Management Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/data/catalog` | List all registered NASA lunar datasets and profiles |
| `GET` | `/api/data/status` | Disk presence and GeoTIFF header verification |
| `GET` | `/api/data/coverage` | Spatial dataset intersection at a given coordinate |
| `POST` | `/api/data/download/{id}` | Background download task with HTTP Range resume |
| `GET` | `/api/data/downloads/{id}` | Streaming download speed and progress percentage |

---

## 7. Example Requests & Responses

### 1. Point Terrain Query
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/terrain?lat=-89.44&lon=222.50&radius_m=100.0" -Method GET | ConvertTo-Json
```
**Response:**
```json
{
  "latitude": -89.44,
  "longitude": 222.5,
  "is_valid_point": true,
  "elevation_m": -120.4,
  "slope_deg": 6.8,
  "roughness_m": 0.12,
  "landing_hazard_classification": "nominal",
  "dataset_info": {
    "dataset_name": "NASA LRO LOLA (Lunar Orbiter Laser Altimeter)",
    "product_id": "LDEM_80S_100M",
    "spatial_resolution_m": 80.0,
    "slope_method": "Horn (1981) 8-neighbor gradient operator"
  }
}
```

### 2. Full Landing Zone Analysis
```powershell
$body = @{
  center_lat = -89.44
  center_lon = 222.50
  radius_meters = 1000.0
  max_acceptable_slope_deg = 10.0
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/analysis/run" -Method POST -Body $body -ContentType "application/json" | ConvertTo-Json
```

### 3. Generate Downloadable PDF Mission Report
```powershell
$body = @{
  analysis_id = "analysis_001"
  format = "pdf"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/api/reports/generate" -Method POST -Body $body -ContentType "application/json" -OutFile "Mission_Report.pdf"
```

---

## 8. Testing & Validation Instructions

Moonscape includes an automated test suite containing **126 tests** covering mathematical accuracy, functional contracts, edge cases, security, and performance.

```powershell
# Run all tests with verbose output
pytest Backend/tests/ -v

# Run the Phase 10 validation suite
pytest Backend/tests/test_final_validation.py -v

# Run data access latency and memory benchmarks
python Backend/scripts/benchmark_data_access.py

# Run comprehensive validation report generator
python Backend/scripts/final_validation_report.py
```

### Test Coverage Summary
- **Geodesy & Coordinates:** 100% roundtrip accuracy (< 0.001 mm error).
- **Slope Accuracy:** 0.000° error on analytical $15.0^\circ$ tilted plane.
- **Endpoint Latencies:** Health (8.8 ms), Terrain (14.0 ms), 1000m Analysis (41.5 ms), MCDA Scoring (3.2 ms).
- **Memory Footprint:** Peak growth during raster windowing < 0.15 MB.
- **Security:** Zero hardcoded API keys; path traversal defended on all routes.

---

## 9. Scientific Limitations & Assumptions

1. **Topographic Derivations:**
   - Slopes are derived using Horn's (1981) 8-neighbor finite difference operator. Local micro-relief smaller than raster cell size (80m for Tier 1, 5m for Tier 2) is unobserved by orbital altimetry.
   - Surface roughness is calculated as the RMS residual deviation from a $3 \times 3$ neighborhood mean.
2. **Geodetic Reference Datum:**
   - Lunar coordinates reference the IAU 2000 Moon Mean Sphere ($R = 1,737,400\text{ m}$) under Lunar South Polar Stereographic projection (`ESRI:104903`).
3. **Solar Illumination & Ephemeris:**
   - Solar geometry uses an analytical model (Meeus / JPL DE421) accurate to $< 0.05^\circ$.
   - Cumulative illumination values incorporate multi-year LRO LOLA simulation baselines (Barker et al. 2021).
   - Diviner thermal brightness temperatures (Kelvin) measure regolith infrared radiation, not direct optical sunlight percentage.
4. **MCDA Preliminary Suitability Scoring:**
   - Suitability scores (0–100) are multi-criteria screening indicators, **not landing safety certifications**.
   - Slope $> 15.0^\circ$ triggers a critical safety disqualification based on lander tip-over dynamics.
   - Missing factors are tracked via `score_coverage_pct` and are never silently assumed to be zero.
