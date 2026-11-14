# Moonscape — Lunar South Pole Landing-Site Analysis Platform

Moonscape is an engineering and scientific analysis platform for evaluating candidate lunar landing locations in the South Pole region (80°S to 90°S).

---

## 📁 Repository Architecture

The project is structured into three clean, modular divisions:

```text
MoonScape/
├── maths/                  # Pure mathematical & scientific computing algorithms
│   ├── geodesy.py          # Geodetics (lat/lon <-> Lunar South Pole Stereographic ESRI:104903)
│   ├── topography.py       # Horn (1981) 8-neighbor slope & RMS surface roughness
│   ├── curvature.py        # 2D Laplacian curvature for crater rim & basin detection
│   ├── scoring.py          # Piece-wise penalty & MCDA decision weighting engine
│   └── tests/              # Mathematical precision unit tests
│
├── Backend/                # FastAPI application & scientific data pipelines
│   ├── app/
│   │   ├── main.py         # Application entry point & CORS configuration
│   │   ├── core/           # Settings, constants, and logging
│   │   ├── config/         # Hardware resource limits & dataset registry config
│   │   ├── schemas/        # Pydantic validation schemas
│   │   ├── services/       # Topographic, hazard, scoring, AI, and report services
│   │   │   ├── data_management/ # Storage, LRU cache, downloads, and coverage
│   │   │   ├── data_sources/    # Adapters (PGDA 90, 78, 104, Diviner, LROC)
│   │   │   └── geospatial/      # Coordinate manager, windowed raster sampler, selector
│   │   └── routes/         # 16 API endpoints (11 Core + 5 Data Management)
│   ├── data/lunar/         # Raw NASA GeoTIFFs, cache, and temporary processing
│   ├── scripts/            # CLI downloader & scientific benchmark tools
│   ├── tests/              # Comprehensive test suites (59+ tests)
│   ├── requirements.txt    # Python dependencies
│   ├── pytest.ini          # Test runner config
│   └── .env                # Environment variables
│
├── docs/                   # Scientific documentation, citations, & download manifest
│   ├── lunar_dataset_inventory.md
│   ├── download_manifest.json
│   └── data_attribution.md
│
└── Frontend/               # Client application (developed independently by teammate)
    ├── README.md           # Frontend onboarding & connection guide
    ├── API_CONTRACT.md     # Full contract specifications & response examples
    └── types.ts            # Auto-aligned TypeScript type definitions
```

---

## 🚀 Phase 2 NASA Lunar Data Integration

### Three-Tier Data Hierarchy
1. **Tier 1 — Essential Regional Foundation:**
   NASA PGDA Product 90 LOLA 80m South Pole elevation, slope, observation count density, and uncertainty layers.
2. **Tier 2 — High-Resolution Candidate Site DEMs:**
   NASA PGDA Product 78 LOLA 5m/pixel models (e.g. Site 01 Shackleton Connecting Ridge).
3. **Tier 3 — Remote / On-Demand Discovery:**
   NASA PGDA Product 104 Shape-from-Shading (SfS) photoclinometry, Diviner thermal environment (PCP), and LROC WAC/NAC stereo models.

### Hardware Optimization Profile
- **CPU:** AMD Ryzen 9 8940HX (16 logical cores)
- **RAM:** 16 GB (In-memory LRU raster window cache capped at 256 MB)
- **GPU:** NVIDIA GeForce RTX 5070 Laptop GPU (8GB VRAM reserved for ML/vision)
- **Storage:** Dynamic SSD headroom detection (minimum 10 GB safety buffer)

---

## 🛠️ Quick Start (Windows PowerShell)

### 1. Activate Python Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Run Complete Test Suite
```powershell
pytest -v
```

### 3. Run Performance Benchmark
```powershell
python Backend/scripts/benchmark_data_access.py
```

### 4. Download Real NASA Terrain Datasets
```powershell
# Recommended installation (~1.24 GB)
python Backend/scripts/download_nasa_data.py --profile profile_b

# Or specific candidate site layers (e.g. Site 01 5m DEM)
python Backend/scripts/download_nasa_data.py --dataset pgda78_site01_surf
```

### 5. Start the Backend API Server
```powershell
uvicorn Backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation: `http://localhost:8000/docs`

---

## 📡 API Endpoints Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | System health, loaded datasets, and projection info |
| `GET` | `/api/sites` | List cataloged Artemis candidate landing sites |
| `GET` | `/api/sites/{site_id}` | Detailed parameters for a specific site |
| `GET` | `/api/map/config` | Lunar Polar Stereographic projection parameters & layers |
| `GET` | `/api/terrain?lat=...&lon=...` | Point elevation, slope, roughness, uncertainty & provenance |
| `POST` | `/api/analysis/run` | Landing ellipse spatial slope & roughness distribution |
| `POST` | `/api/hazards/predict` | Local crater basin & boulder hazard identification |
| `POST` | `/api/sites/compare` | Side-by-side comparison of candidate landing sites |
| `POST` | `/api/score` | Multi-criteria explainable landing suitability score |
| `POST` | `/api/ai/explain` | Scientific engineering assessment & advisory |
| `POST` | `/api/reports/generate` | Exportable JSON, Markdown, or HTML mission reports |
| `GET` | `/api/data/catalog` | List all registered NASA lunar datasets & profiles |
| `GET` | `/api/data/status` | Disk presence & GeoTIFF validation state |
| `GET` | `/api/data/coverage` | Spatial dataset intersection at a coordinate |
| `POST` | `/api/data/download/{id}` | Controlled background download with HTTP Range resume |
| `GET` | `/api/data/downloads/{id}` | Real-time streaming speed & progress percentage |
