# Model Card: Moonscape Lunar South Pole Optical Hazard Detector

**Model Name:** Moonscape Lunar South Pole Optical Hazard Detector  
**Version:** 1.0.0  
**Model Architecture:** YOLOv8n (Anchor-Free Convolutional Neural Network)  
**Model Checkpoints:** 
- `Backend/data/models/luna_hazard_yolov8n.pt` (PyTorch)
- `Backend/data/models/luna_hazard_yolov8n.onnx` (ONNX Opset 18)
**Metadata File:** `Backend/data/models/luna_hazard_yolov8n.meta.json`  
**License:** NASA / PDS Open Data License & Apache 2.0  
**Date of Release:** November 15, 2026  

---

## 1. Model Details

### Basic Information
* **Developer:** Moonscape Planetary AI & Computer Vision Engineering Team.
* **Model Type:** Single-stage object detection model for extraterrestrial optical imagery.
* **Base Architecture:** YOLOv8n (Nano variant, Ultralytics implementation).
* **Input Specifications:** 
  * Shape: `(1, 3, 640, 640)` (Batch, Channels, Height, Width).
  * Data type: Float32.
  * Normalization: Scaled to $[0.0, 1.0]$.
* **Output Classes:**
  * `0`: **crater** (impact craters, depressions, and rim structures).
  * `1`: **boulder** (positive-relief rocky ejecta, boulders, and rubble blocks).
* **Frameworks Supported:** PyTorch $\ge 2.0$, ONNX Runtime $\ge 1.16$, Ultralytics $\ge 8.0$.

---

## 2. Intended Use & Target Tasks

### Primary Intended Use
* **Preliminary Landing-Site Screening:** Rapid screening of candidate touchdown corridors at the lunar South Pole (80°S to 90°S) from orbital optical reconnaissance imagery.
* **Corridor Hazard Counting:** Automated counting and density estimation of craters and boulders to feed multi-criteria suitability scoring algorithms.
* **Interactive Web Visualization:** Low-latency ($< 20$ ms) inference for interactive display of detection boxes and physical metric sizes in the Moonscape frontend.

### Primary Intended Users
* Planetary scientists, landing site selection working groups, mission planners, and aerospace engineering students evaluating Artemis candidate landing regions.

---

## 3. Out-of-Scope & Prohibited Use Cases

> [!CAUTION]
> **SAFETY-CRITICAL & HUMAN FLIGHT DISCLAIMER**
> 
> 1. **NOT FOR REAL-TIME AUTONOMOUS DESCENT:** This model is **NOT** certified or qualified for autonomous real-time closed-loop terminal hazard avoidance on a landing spacecraft. Real-time descent guidance requires multi-sensor fusion (flash LiDAR, radar altimetry, optical flow), rad-hard flight computer execution, and NASA NPR 7150.2 human-rated software certification.
> 2. **NOT CERTIFIED FOR HUMAN-RATED TOUCHDOWN DECISIONS:** Detections from this model represent preliminary screening indications only. All mission-critical landing site selections require human planetary science review and high-resolution stereophotogrammetric DEM validation.
> 3. **PROHIBITED IN ZERO-ILLUMINATION PSRs:** The model relies on reflected sunlight. Within Permanently Shadowed Regions (PSRs), it will produce zero reliable detections. Active sensor data (LiDAR and radar) must be used instead.
> 4. **PROHIBITED ON APOLLO-STYLE EQUATORIAL SURFACE PHOTOGRAPHY:** Deploying this model on astronaut-eye-level, high-sun Apollo Hasselblad photography violates the physical domain boundaries of the model.

---

## 4. Training Data & Geographic Splitting

* **Data Source:** Authentic NASA Lunar Reconnaissance Orbiter (LRO) Narrow Angle Camera (NAC) and ISRO Chandrayaan-2 OHRC polar frames.
* **Solar Illumination:** Solar incidence angles between 78.0° and 84.5° (low grazing polar sun).
* **Ground Resolution:** 1.2 to 1.8 meters per pixel.
* **Total Dataset Volume:** 80 tiles, 4,136 hand-labeled ground-truth instances.
* **Geographic Scene Partitioning (Strict Zero-Leakage):**
  * **Train Set (40 tiles, 1,694 instances):** Shackleton Connecting Ridge & Bench (candidate Artemis Site 01).
  * **Validation Set (20 tiles, 1,216 instances):** Malapert Mountain Summit Massif & Haworth Rim (candidate Artemis Site 02).
  * **Held-Out Test Set (20 tiles, 1,226 instances):** de Gerlache Crater Rim 1 & 2 (candidate Artemis Sites 03 & 04) — **100% geographically unseen during training**.

---

## 5. Quantitative Performance Summary

### Held-Out Test Evaluation (de Gerlache Crater Rim — Unseen Holdout)

| Metric | Overall | Crater (Class 0) | Boulder (Class 1) |
|---|---|---|---|
| **Precision** | 0.5608 | 0.4082 | **0.7133** |
| **Recall** | 0.5627 | **0.7552** | 0.3702 |
| **F1-Score** | 0.5617 | 0.5299 | 0.4874 |
| **mAP@50** | **0.5818** | **0.6100** | **0.5537** |
| **mAP@50-95** | 0.2415 | 0.2651 | 0.2179 |

### Hardware Benchmarks (AMD Ryzen 9 894HX CPU)
* **Mean Inference Latency:** **18.23 ms**
* **P95 Latency:** **19.92 ms**
* **Framerate:** **54.9 FPS**
* **VRAM/RAM Usage:** $< 180$ MB peak memory

---

## 6. Environmental & Operational Constraints

1. **Sun Elevation Sensitivity:** Optimum performance is achieved when the solar incidence angle is between 75° and 85°. At near-noon equatorial angles ($< 45^\circ$), crater shadows disappear and detection accuracy drops.
2. **Spatial Calibration Prerequisite:** The model outputs pixel coordinates. Real-world metric dimensions (meters) are **only** computed when the caller supplies `spatial_resolution_mpp`. If uncalibrated, metric size is reported as `null` with an explicit scientific warning.
3. **Sensor Artifacts:** Cosmic ray streaks, high-energy particle hits, and spacecraft jitter in uncalibrated raw telemetry must be pre-filtered using NASA PDS standard calibration pipelines (e.g., ISIS `lronaccal`).
