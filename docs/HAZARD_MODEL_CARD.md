# MoonScape — Model Card: Lunar South Pole Optical Hazard Detector

**Document ID:** `DOC-HAZ-CARD-2026-003`  
**Standard:** Mitchell et al. (2019) Model Cards for Model Reporting  
**Version:** 1.0.0  
**Status:** Certified Production Artifact  

---

## 1. Model Details

* **Model Name:** Moonscape Lunar South Pole Optical Hazard Detector
* **Model Version:** 1.0.0
* **Architecture:** YOLOv8n-Detection (Nano single-stage object detector)
* **Backbone:** Modified CSPDarknet53 with Cross Stage Partial (C2f) modules
* **Neck:** Spatial Pyramid Pooling Fast (SPPF) + Path Aggregation Network (PANet)
* **Head:** Anchor-free decoupled head predicting bounding boxes $[x_c, y_c, w, h]$ via Distribution Focal Loss (DFL) and class probabilities via Binary Cross-Entropy (BCE)
* **Parameter Count:** 3,006,038 (3.0M)
* **Computational Complexity:** 8.1 GFLOPs at $640 \times 640$ input resolution
* **Model Size:** 6.2 MB (PyTorch `.pt`), 11.7 MB (ONNX `.onnx`)
* **Input Tensor:** BCHW Float32 `(1, 3, 640, 640)` normalized to $[0.0, 1.0]$
* **Output Tensor:** `(1, 6, 8400)` representing 8,400 multi-scale candidate predictions with $[x_c, y_c, w, h, \text{score}_{\text{crater}}, \text{score}_{\text{boulder}}]$
* **License:** GNU General Public License v3.0 (Ultralytics) / NASA Open Data Policy (Training Imagery)
* **Release Date:** November 15, 2026
* **Maintainer:** Sampat Barik / MoonScape Planetary Engineering Group

---

## 2. Intended Use & Target Tasks

### 2.1 Primary Intended Uses
* Automated crater and boulder hazard identification from high-resolution ($0.25\text{ mpp}$ to $2.0\text{ mpp}$) lunar polar orbital reconnaissance imagery.
* Preliminary candidate landing corridor screening and feasibility ranking for robotic and crewed exploration missions (e.g., Artemis, Chandrayaan).
* Multi-modal hazard data fusion: combining optical visual detections with digital elevation model (LOLA) slope and roughness baselines.

### 2.2 Out-of-Scope & Prohibited Uses
* **Real-Time Terminal Descent:** NOT flight-certified for autonomous real-time landing hazard detection and avoidance (HDA) during active powered descent.
* **Permanently Shadowed Regions (PSRs):** Zero optical utility inside permanently shadowed craters ($0.0\text{ lux}$). Laser altimetry (LOLA) and radar backscatter (Mini-RF) must be used.
* **Low-Latitude Apollo Imagery:** Invalid for equatorial or mid-latitude surface photography where solar incidence angles are low ($\theta_{\text{inc}} < 70^\circ$).

---

## 3. Training & Validation Data

* **Optical Imagery Sources:** Calibrated panchromatic nadir orbital frames from NASA LRO Narrow Angle Camera (NAC) and ISRO Chandrayaan-2 Orbiter High Resolution Camera (OHRC).
* **Dataset Volume:** 80 calibrated image tiles ($833 \times 626$ pixels) divided into 40 train, 20 validation, and 20 held-out test samples.
* **Annotations:** 4,136 hand-delineated bounding boxes (2,254 craters, 1,882 boulders).
* **Geographic Coverage:**
  - Train: Shackleton Connecting Ridge & Bench (Artemis Site 01), Malapert Plateau.
  - Validation: Malapert Summit Massif (Site 02), Haworth Transition Rim.
  - Test (Unseen Holdout): de Gerlache Crater Rim 1 & 2 (Sites 03 & 04).

---

## 4. Quantitative Evaluation & Metrics

### 4.1 Held-Out Test Set Performance (Unseen de Gerlache Rim 1 & 2)

| Class | Precision (P) | Recall (R) | F1-Score | mAP@50 | mAP@50-95 | Primary Strength |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Crater** | 0.4082 | **0.7552** | 0.5299 | 0.6100 | 0.2651 | High sensitivity catches 75.5% of craters |
| **Boulder** | **0.7133** | 0.3702 | 0.4874 | 0.5537 | 0.2179 | High purity: 71.3% of flags are real rocks |
| **Overall** | **0.5608** | **0.5627** | **0.5617** | **0.5818** | **0.2415** | Stable out-of-domain generalization |

### 4.2 Local Hardware Benchmarks (AMD Ryzen 9 894HX)

| Metric | Measured Value | Operational Impact |
| :--- | :--- | :--- |
| **Mean Inference Latency** | **18.23 ms** | Ultra-responsive interactive web screening |
| **95th Percentile Latency (P95)** | **19.92 ms** | Deterministic bounded response time |
| **Throughput** | **54.9 FPS** | High-throughput batch reconnaissance |
| **Peak RAM Footprint** | **< 180 MB** | Lightweight execution on 16 GB laptop |

---

## 5. Operational Limitations & Scientific Safety Warnings

1. **Nyquist Spatial Resolution Limit ($2 \times \text{GSD}$):** The detector cannot reliably delineate features smaller than two physical pixels. In 1.4 mpp imagery, craters $< 3\text{ m}$ or boulders $< 1.5\text{ m}$ cannot be geometrically resolved without sub-pixel shadow modeling.
2. **Topographic Separation:** DEM roughness anomalies and steep slope escarpments must remain separate from optical object detections. DEM pixels must never be labeled as boulders.
3. **Engineering Research Disclaimer:** Outputs from MoonScape represent preliminary computational screening models derived from remote sensing data and do NOT constitute certified landing safety clearance.
