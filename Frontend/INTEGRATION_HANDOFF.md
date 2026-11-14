# MOONSCAPE — Backend Integration & Handoff Guide

This document is for the **backend engineer** to connect, configure, and test their local Python/FastAPI backend with this Moonscape frontend application.

---

## 1. Quick Connection Steps (For the Backend Engineer)

### Step 1: Start Your FastAPI Backend
Ensure your backend service is running locally on your laptop:
```bash
# Example FastAPI command:
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Step 2: Configure the Frontend Environment
In the `frontend/` directory, create or modify `.env.local`:
```bash
cp .env.example .env.local
```
Ensure `VITE_API_BASE_URL` points to your active backend address:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_API_MODE=live
```

### Step 3: Run the Frontend
```bash
npm install
npm run dev
```
Open **[http://localhost:5173/](http://localhost:5173/)** in your browser. Verify the status indicator in the top navbar says:
```
DATA: LIVE
```

---

## 2. CORS Requirements (Critical)

FastAPI must permit cross-origin requests from the frontend development server (`http://localhost:5173`) and production previews:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 3. Implemented API Contract & Endpoints

All frontend API calls originate exclusively from [`src/services/api.ts`](src/services/api.ts).

### 1. Health Probe
- **Endpoint**: `GET /api/health`
- **Frontend Usage**: Probed on application launch when `VITE_API_MODE=auto`.
- **Expected Response**:
  ```json
  {
    "status": "ok",
    "version": "1.0.0"
  }
  ```

### 2. Candidate Landing Sites
- **Endpoint**: `GET /api/sites`
- **Frontend Usage**: Renders markers on the 3D Moon (`/explorer`), populated candidate lists, and site selector in `/compare`.
- **Expected Response**: Array of candidate sites:
  ```json
  [
    {
      "site_id": "shackleton_rim",
      "name": "Shackleton Rim",
      "latitude": -89.9,
      "longitude": 0.0,
      "description": "Connecting ridge near the rim with elevated solar visibility."
    }
  ]
  ```

### 3. Real-Time Terrain Preview
- **Endpoint**: `GET /api/terrain?lat={latitude}&lon={longitude}`
- **Frontend Usage**: Debounced (450ms) preview panel in the 3D Explorer sidebar when dragging or clicking coordinates.
- **Expected Response**:
  ```json
  {
    "latitude": -89.9,
    "longitude": 0.0,
    "elevation": { "mean_m": -5210.4 },
    "slope": { "mean_deg": 6.8 },
    "roughness": { "rms_m": 0.95 },
    "illumination": { "sunlight_percent": 68.5, "psr_nearby": true }
  }
  ```

### 4. Full Landing-Site Terrain Analysis
- **Endpoint**: `POST /api/analysis/run`
- **Payload**:
  ```json
  {
    "latitude": -89.9,
    "longitude": 0.0,
    "radius_m": 500
  }
  ```
- **Expected Response**: `AnalysisResponse` with `analysis_id`, full terrain statistics, and dataset availability flags.

### 5. Preliminary Suitability Scoring
- **Endpoint**: `POST /api/score`
- **Payload**: `{ "latitude": -89.9, "longitude": 0.0, "radius_m": 500 }`
- **Expected Response**:
  ```json
  {
    "score": 84.5,
    "grade": "A",
    "label": "High Suitability",
    "breakdown": {
      "slope": 92.0,
      "illumination": 88.0,
      "roughness": 78.5,
      "earth_comm": 80.0
    },
    "disclaimer": "Preliminary decision-support score."
  }
  ```

### 6. Hazard & Crater/Boulder Detection
- **Endpoint**: `POST /api/hazards/predict`
- **Payload**: `{ "latitude": -89.9, "longitude": 0.0, "radius_m": 500 }`
- **Expected Response**:
  ```json
  {
    "craters": [
      { "id": "CR-1", "latitude": -89.91, "longitude": 0.02, "diameter_m": 35.2, "depth_m": 4.1, "confidence": 0.91 }
    ],
    "rocks": [
      { "id": "RK-1", "latitude": -89.89, "longitude": 0.01, "size_m": 1.8, "confidence": 0.85 }
    ],
    "model": "YOLO-LunarHazards-v2",
    "limitations": [
      "Sub-meter boulder detection limited by LROC NAC optical resolution."
    ]
  }
  ```

### 7. Multi-Site Comparison
- **Endpoint**: `POST /api/sites/compare`
- **Payload**: `{ "site_ids": ["shackleton_rim", "malapert_massif"] }`
- **Expected Response**:
  ```json
  {
    "sites": [
      {
        "site_id": "shackleton_rim",
        "name": "Shackleton Rim",
        "score": 85.0,
        "elevation": { "mean_m": -5210.0 },
        "slope": { "mean_deg": 6.8, "max_deg": 18.2 },
        "roughness": { "rms_m": 0.95 },
        "illumination": { "sunlight_percent": 68.5 }
      }
    ],
    "compared_at": "2026-11-15T00:00:00Z"
  }
  ```

### 8. AI Scientific Explanation
- **Endpoint**: `POST /api/ai/explain`
- **Payload**: `{ "analysis_id": "analysis_123" }`
- **Expected Response**:
  ```json
  {
    "analysis_id": "analysis_123",
    "explanation": "Narrative assessment of terrain viability...",
    "positive_factors": ["High average illumination", "Moderate slope gradients"],
    "risk_factors": ["Proximity to steep crater rim"],
    "uncertainties": ["Seasonal shadows during southern winter"],
    "limitations": ["Altimetry averaged across 500m radius"],
    "model": "Gemini-1.5-Pro / Aerospace-FineTuned",
    "generated_at": "2026-11-15T00:00:00Z"
  }
  ```

### 9. Technical Report Generation
- **Endpoint**: `POST /api/reports/generate`
- **Payload**: `{ "analysis_id": "analysis_123", "format": "json" }`

---

## 4. Frontend Resilience & Null Handling

- **Null Is Never Zero**: If a calculation fails or a dataset has no coverage for given polar coordinates, your backend should return `null`. The frontend will gracefully display `"Data unavailable"` without throwing an error or presenting false zeroes.
- **Error Responses**: Return standard HTTP 4xx or 5xx codes with a JSON error payload `{ "detail": "error explanation" }`. The frontend's `ApiError` class parses `detail` and presents it in the UI error panel with a retry button.

---

## 5. Contact & Support

All frontend code is located in the `frontend/` directory. For testing inquiries or contract adjustments, consult the frontend team lead.
