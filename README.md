# Moonscape — Lunar South Pole Landing-Site Analysis Platform

Moonscape is an engineering and scientific analysis platform for evaluating candidate lunar landing locations in the South Pole region (80°S to 90°S).

---

## 📁 Repository Architecture

The project is structured into three clean, modular divisions:

```text
MoonScape/
├── maths/                  # Pure mathematical & scientific computing algorithms
│   ├── geodesy.py          # Coordinate conversions (lat/lon <-> South Pole Stereographic)
│   ├── topography.py       # Horn (1981) 8-neighbor slope & RMS roughness
│   ├── curvature.py        # 2D Laplacian curvature for crater detection
│   ├── scoring.py          # Piece-wise penalty & MCDA decision weighting
│   └── tests/              # Mathematical precision unit tests
│
├── Backend/                # FastAPI application & scientific services
│   ├── app/
│   │   ├── main.py         # Application entry point & CORS configuration
│   │   ├── core/           # Settings, constants, and logging
│   │   ├── schemas/        # Pydantic validation schemas
│   │   ├── services/       # Topographic, hazard, scoring, and report services
│   │   └── routes/         # 11 fixed API endpoints
│   ├── data/               # NASA Artemis candidate sites & LOLA DEM GeoTIFF
│   ├── scripts/            # DEM generator utilities
│   ├── tests/              # Comprehensive endpoint integration tests
│   ├── requirements.txt    # Python dependencies
│   ├── pytest.ini          # Test runner config
│   └── .env                # Environment variables
│
└── Frontend/               # Client application (developed independently by teammate)
    ├── README.md           # Frontend onboarding & connection guide
    ├── API_CONTRACT.md     # Full contract specifications & response examples
    └── types.ts            # Auto-aligned TypeScript type definitions
```

---

## 🛠️ Quick Start (Windows PowerShell)

### 1. Activate Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Run All Tests (35 Tests: 25 Backend + 10 Maths)
```powershell
pytest -v
```

### 3. Start the Backend API Server
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger docs: `http://localhost:8000/docs`
