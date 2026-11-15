# MOONSCAPE — PORT AND IMPORT AUDIT REPORT

**Document Version:** 1.0.0  
**Date:** November 15, 2026  
**Auditor:** Senior FastAPI, TypeScript, Systems Debugging & Scientific Computing Engineer  
**Workspace:** `D:\MoonScape`  

---

## 1. Executive Summary

This report documents the investigation, root causes, and verified repairs for:
1. **Import Failures & Typing Annotations** (`model_trainer.py` missing `Optional` import under Python 3.14 deferred annotation evaluation).
2. **Dual-Singleton Package Inconsistency** (`app.*` vs `Backend.app.*` split causing separate memory instances of services).
3. **Port & Hostname Audit** across all 10 configuration and environment files.
4. **CORS Security Tightening** (removal of overly broad regular expression origin matching).

---

## 2. TASK 1: Import Failures & Strategy Standardization

### 2.1 The `model_trainer.py` Bug (Root Cause & Fix)
- **File:** [Backend/app/services/ml/model_trainer.py](file:///D:/MoonScape/Backend/app/services/ml/model_trainer.py)
- **Root Cause:** Line 59 annotated `__init__(self, data_dir: Optional[Path] = None, models_dir: Optional[Path] = None)` using `Optional`, but line 11 only imported `from typing import Any, Dict, List, Tuple`.
- **Failure Mode:** Under Python 3.14 (PEP 649 / PEP 563 lazy annotations), inspecting function signatures with `typing.get_type_hints(LunarModelTrainer.__init__)` failed with:
  ```
  NameError: name 'Optional' is not defined
  ```
- **Fix Applied:** Updated line 11 to import `Optional`:
  ```python
  from typing import Any, Dict, List, Optional, Tuple
  ```
- **Verification:** `typing.get_type_hints(LunarModelTrainer.__init__)` executed successfully, returning `{'data_dir': pathlib.Path | None, 'models_dir': pathlib.Path | None}`.

### 2.2 Inconsistent Import Architecture & Dual Singletons
- **Root Cause:** Prior to this audit, 37 files imported `from app.*` while 57 files imported `from Backend.app.*`. Even [Backend/app/main.py](file:///D:/MoonScape/Backend/app/main.py) mixed both styles.
- **Critical Bug Discovered:** Python treats `app.services.site_service` and `Backend.app.services.site_service` as two separate module keys in `sys.modules`. Testing `s1 is s2` in Python evaluated to `False`! This meant:
  - Memory caches and singleton state were duplicated.
  - Updates in one module were invisible to the other.
  - Launching scripts from the root directory required manual `$env:PYTHONPATH="Backend"` prefixes to prevent `ModuleNotFoundError`.
- **Fix Applied:**
  1. Standardized all 57 occurrences across `Backend/app/` and `Backend/tests/` to use canonical `from app.*` imports.
  2. Added an automatic `sys.path` bootstrap in [Backend/app/__init__.py](file:///D:/MoonScape/Backend/app/__init__.py) and [Backend/__init__.py](file:///D:/MoonScape/Backend/__init__.py):
     ```python
     import sys
     from pathlib import Path
     _backend_dir = Path(__file__).resolve().parent.parent
     if str(_backend_dir) not in sys.path:
         sys.path.insert(0, str(_backend_dir))
     ```
- **Verification:** All 172 backend pytest tests execute and pass cleanly.

### 2.3 Comprehensive Library & Module Import Test Results
Evaluated using Python 3.14.4 in `.venv`:

| Module / Service | Import Path | Status | Details |
|---|---|---|---|
| NumPy | `numpy` | **OK** | v2.2 |
| SciPy | `scipy` | **OK** | v1.15 |
| Rasterio | `rasterio` | **OK** | v1.4 |
| scikit-learn | `sklearn` | **OK** | v1.6 |
| PyProj | `pyproj` | **NOT REQUIRED** | Not in `requirements.txt`; Moonscape uses native NumPy algorithms in `maths/polar_stereographic.py`. |
| PyTorch | `torch` | **NOT INSTALLED** | Optional; optical hazard detector operates in DEM fallback mode. |
| Main App | `app.main` | **OK** | All 35 routers initialized |
| DEM Service | `app.services.dem_service` | **OK** | LOLA Product 78 + baseline DEM |
| Terrain Service | `app.services.terrain_service` | **OK** | Topographic gradient & statistics |
| Hazard Service | `app.services.hazard_service` | **OK** | Geometric obstacle detector |
| Site Scoring | `app.services.site_scoring` | **OK** | MCDA suitability engine |
| ML Suitability | `app.services.ml.suitability_model_service` | **OK** | Random Forest surrogate model |
| Model Trainer | `app.services.ml.model_trainer` | **OK** | Geographic CV & training |
| Dataset Generator | `app.services.ml.dataset_generator` | **OK** | Synthetic polar site generator |
| AI Explainer | `app.services.ai_explainer` | **OK** | Deterministic domain knowledge engine |

---

## 3. TASK 2: Port and Hostname Audit

Every reference to network ports and hostnames was audited across 10 project files:

| File | Configured Port / Host | Verified Parameter | Compliance |
|---|---|---|---|
| `Frontend/src/config.ts` | `127.0.0.1:8000` | `API_BASE_URL`, `REQUEST_TIMEOUT_MS: 30000` | **MATCH** |
| `Frontend/src/services/api.ts` | `API_BASE_URL` | Calls `/api/*` endpoints; no hardcoded ports | **MATCH** |
| `Frontend/vite.config.ts` | `127.0.0.1:5173` | `server: { port: 5173, strictPort: true }` | **MATCH** |
| `Frontend/package.json` | `vite` | Standard Vite dev server script | **MATCH** |
| `Frontend/.env.local` | `http://127.0.0.1:8000` | `VITE_API_BASE_URL`, `VITE_API_MODE=live` | **MATCH** |
| `Frontend/.env.example` | `http://127.0.0.1:8000` | `VITE_API_BASE_URL`, `VITE_API_MODE=live` | **MATCH** |
| `Backend/app/main.py` | `8000` | `api_prefix = "/api"` | **MATCH** |
| `Backend/app/core/config.py` | `0.0.0.0:8000` | `PORT: 8000`, `API_V1_STR = "/api"` | **MATCH** |
| `Backend/.env` | `0.0.0.0:8000` | `PORT=8000`, `API_V1_STR="/api"` | **MATCH** |
| `Backend/.env.example` | `0.0.0.0:8000` | `PORT=8000`, `API_V1_STR="/api"` | **MATCH** |

### 3.1 Strict Port Enforcement in Vite
- **Problem:** If port 5173 is occupied, Vite by default silently increments to 5174, 5175, etc., causing browser connections and CORS configurations to fail without a clear error.
- **Fix:** Added `strictPort: true` to both `server` and `preview` blocks in [Frontend/vite.config.ts](file:///D:/MoonScape/Frontend/vite.config.ts). Vite will now fail immediately with a descriptive error if 5173 is unavailable rather than silently binding to an arbitrary port.

### 3.2 Port Availability Check
PowerShell `netstat -ano` verified that both `5173` and `8000` bind cleanly to their respective single processes with zero conflicts.

---

## 4. TASK 3: CORS Configuration Audit & Tightening

### 4.1 Vulnerability Identified
In [Backend/app/main.py](file:///D:/MoonScape/Backend/app/main.py), the previous configuration included:
```python
allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
```
This regex matched **any** localhost port (e.g. `http://localhost:9999`), allowing unauthorized local web applications to execute cross-origin requests.

### 4.2 Hardened CORS Rule Applied
Removed `allow_origin_regex` and restricted `CORS_ORIGINS` to the exact trusted dev and preview origins:
```python
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]
```
Configured in `main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
```

### 4.3 Automated CORS Test Results
- **Allowed `http://localhost:5173`:** OPTIONS `/api/analysis/run` $\to$ HTTP 200, `Access-Control-Allow-Origin: http://localhost:5173`.
- **Allowed `http://127.0.0.1:5173`:** OPTIONS `/api/analysis/run` $\to$ HTTP 200, `Access-Control-Allow-Origin: http://127.0.0.1:5173`.
- **Disallowed `http://malicious.com`:** OPTIONS `/api/analysis/run` $\to$ HTTP 400, `Access-Control-Allow-Origin: None`.
