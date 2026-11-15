# MoonScape — Lunar Hazard Inference & Coordinate Workflow Integration

**Document ID:** `DOC-HAZ-INT-2026-004`  
**System Components:** `Backend/app/services/hazard_detection.py`, `Backend/app/services/hazard_service.py`, `Frontend/src/pages/Hazards.tsx`, `Frontend/src/components/HazardPanel.tsx`  
**API Endpoints:** `POST /api/hazards/predict` & `POST /api/hazards/detect`  
**Status:** Operational & Integrated  

---

## 1. End-to-End Workflow Architecture

The MoonScape Hazard Analysis subsystem connects planetary coordinate queries with authentic NASA LROC NAC and ISRO Chandrayaan-2 polar observation frames, executing deep-learning detection and delivering georeferenced visual telemetry to the browser.

```
Coordinate Query: (Latitude, Longitude, Radius)
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. POLAR OPTICAL FRAME DISCOVERY                            │
│ Intersects coordinates against calibrated orbital manifest  │
│ (80 LROC NAC polar scenes + ISRO OHRC / TMC-2 strips)       │
└─────────────────────────────────────────────────────────────┘
         │                                       │
    [Tile Found]                          [Tile Absent]
         │                                       │
         ▼                                       ▼
┌────────────────────────────────┐     ┌───────────────────────┐
│ 2. OPTICAL YOLOv8n INFERENCE   │     │ 2b. UNAVAILABLE STATE │
│ Runs luna_hazard_yolov8n.pt/onnx│     │ • crater_count = None │
│ Extracts boxes, labels, conf   │     │ • rock_count = None   │
│ Computes metric size (pixels*mpp│     │ • overlay_image = None│
│ Renders georeferenced overlay  │     │ • optical_status =    │
└────────────────────────────────┘     │   "not_available"     │
         │                             └───────────────────────┘
         ├───────────────────────────────────────┤
         ▼                                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. DEM TOPOGRAPHIC HAZARD EXTRACTION (LOLA Altimetry)       │
│ • Horn finite-difference kernel: steep slopes (>15.0°)      │
│ • RMS elevation deviation: roughness anomalies (>1.5m)      │
│ • Discrete Laplacian curvature: concave basin depressions   │
│ Strictly cataloged under 'topographic_hazards', NOT boulders│
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. MULTI-MODAL SYNTHESIS & TELEMETRY SERIALIZATION          │
│ Emits HazardPredictResponse with verified test split metrics│
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. MONOCHROMATIC AEROSPACE FRONTEND RENDERING               │
│ • Section A · DEM Topographic Slope & Roughness Hazards     │
│ • Section B · Real LROC NAC Overlay Image & Detection Tables│
│ • Section C · Exploration Zone, Product ID, & Resolution    │
│ • Section D · Apollo Domain Shift & PSR Safety Constraints  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. API Contract & Payload Specifications

### 2.1 Request Schema (`POST /api/hazards/predict`)
```json
{
  "center_lat": -87.400,
  "center_lon": -5.100,
  "radius_meters": 1000.0,
  "min_crater_diameter_m": 5.0,
  "boulder_detection_sensitivity": 0.70
}
```

### 2.2 Response Telemetry (Haworth Rim Example)
```json
{
  "status": "partial",
  "optical_status": "success",
  "crater_count": 12,
  "rock_count": 0,
  "source_product_id": "LROC_NAC_POLAR_M145129840LE",
  "source_resolution_m": 1.8,
  "overlay_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "coverage_zone": "core",
  "detections": [
    {
      "label": "crater",
      "confidence": 0.6533,
      "bounding_box": { "ymin": 488.5, "xmin": 348.3, "ymax": 517.2, "xmax": 377.0 },
      "center_pixel": [503, 363],
      "pixel_diameter": 28.7,
      "estimated_size_m": 51.66,
      "severity": "critical"
    }
  ],
  "topographic_hazards": [],
  "model_metadata": {
    "architecture": "YOLOv8n-Detection",
    "version": "1.0.0",
    "parameters": "3.0M",
    "evaluation_metrics": {
      "held_out_test_split": {
        "overall": { "precision": 0.5608, "recall": 0.5627, "f1_score": 0.5617, "mAP50": 0.5818 },
        "crater": { "precision": 0.4082, "recall": 0.7552, "mAP50": 0.6100 },
        "boulder": { "precision": 0.7133, "recall": 0.3702, "mAP50": 0.5537 }
      }
    }
  }
}
```

---

## 3. Truthful Zero vs. Unavailable Semantics

A critical flaw in legacy systems was coercing missing observations to zero. MoonScape implements rigorous scientific semantics:

| Physical Remote-Sensing Condition | `optical_status` | `crater_count` | `rock_count` | `overlay_image` | Frontend UI Display |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Observation Frame Intersects Site** | `"success"` | `12` | `0` | Base64 PNG | Renders real overlay + detected item tables |
| **No Observation Frame Intersects Site** | `"not_available"` | `None` | `None` | `None` | Renders `DataUnavailable` banner ("No intersecting frame") |
| **Zero Boulders Detected in Frame** | `"success"` | `12` | `0` | Base64 PNG | *"Optical scan completed: zero boulders satisfying confidence threshold"* |

---

## 4. Hardware Execution & Concurrency Safety

* **Single-Instance In-Memory Loading:** The detector is initialized once at FastAPI startup (`hazard_detection_service.load_model()`), preventing model reload latency on concurrent requests.
* **Execution Provider Fallback:** Checks for NVIDIA CUDA execution providers; safely defaults to optimized CPU execution via ONNX Runtime / PyTorch on the AMD Ryzen 9 894HX processor.
* **Memory Boundedness:** Maximum image dimensions ($4096 \times 4096$) and file sizes ($50\text{ MB}$) are enforced, guaranteeing RAM usage remains under $250\text{ MB}$ even under rapid query sequences.
