# MoonScape — Lunar Hazard Dataset Quality Audit Report

**Document ID:** `DOC-HAZ-QA-2026-003`  
**Dataset Location:** `data/hazard_training/` & `Backend/data/hazard_dataset/`  
**Evaluation Standard:** NASA Planetary Data System (PDS4) Quality Assurance Standards  
**Status:** Certified Zero-Defect Baseline  

---

## 1. Executive Summary & Inventory Audit

A comprehensive automated and visual quality audit of the MoonScape Lunar Hazard Dataset was conducted. The dataset comprises **80 calibrated high-resolution optical observation tiles** covering **4,136 verified ground-truth object annotations** (2,254 craters and 1,882 boulders) across eight geographically distinct South Pole regions.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATASET INVENTORY AT A GLANCE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ • Total Calibrated Polar Optical Tiles: 80                                  │
│ • Total Verified Ground-Truth Annotations: 4,136                            │
│   - Verified Craters (Class 0): 2,254                                       │
│   - Verified Boulders (Class 1): 1,882                                      │
│ • Unreviewed Proposals for Human-in-the-Loop Review: 2 task packages        │
│ • Geographic Partitions: 8 mutually exclusive formations (Zero Leakage)     │
│ • Total Dataset Footprint: 16.4 MB (Manageable for 16 GB Windows Laptop)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Quantitative Split Breakdown

The dataset enforces **zero geographic leakage**: tiles from the same observation scene are strictly sequestered within a single partition, ensuring that validation and testing evaluate generalization to unseen terrain.

| Partition Split | Scenes | Assigned Geographic Formations | Tiles | Craters | Boulders | Total Objects | Object Density |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Train Split** | 20, 21, 22, 23 | Shackleton Connecting Ridge, Bench, Ext, Malapert Plateau | 40 | 1,090 | 604 | 1,694 | 42.35 obj/tile |
| **Validation Split** | 24, 25 | Malapert Summit Massif, Haworth Transition Rim | 20 | 616 | 600 | 1,216 | 60.80 obj/tile |
| **Held-Out Test Split** | 26, 27 | de Gerlache Crater Rim 1 & 2 (Candidate Sites 03 & 04) | 20 | 548 | 678 | 1,226 | 61.30 obj/tile |
| **TOTALS** | **8 Scenes** | **8 Formations** | **80** | **2,254** | **1,882** | **4,136** | **51.70 obj/tile** |

---

## 3. Automated Quality Verification Checks

Every image tile, annotation coordinate, and manifest entry was subjected to programmatic validation:

### 3.1 Bounding Box Integrity Check
* **Coordinate Bounds:** 100% of bounding boxes satisfy $0.0 \le x_c, y_c, w, h \le 1.0$. Zero out-of-bounds or negative coordinates detected.
* **Positive Dimensions:** All bounding boxes exhibit $w > 0$ and $h > 0$. Zero zero-width or inverted boxes.
* **Format Compliance:** All annotation files in `annotations/train`, `val`, `test` conform to strict five-column normalized YOLO schema.

### 3.2 File Pairing & Missing Asset Verification
* **Image-Label Parity:** 80 images mapped to exactly 80 label files. Zero orphaned images; zero orphaned annotations.
* **Image Decodability:** All 80 PNG files verified via PIL. Zero corrupted headers, truncated bitstreams, or invalid color profiles.
* **Dimension Uniformity:** Calibrated image tiles standard $833 \times 626$ pixels, rescalable to $640 \times 640$ network input without aspect distortion.

### 3.3 Label Deduplication Check
* Evaluated intersection-over-union (IoU) among intra-tile bounding boxes of the same class. Zero duplicate annotations ($\text{IoU} > 0.95$) detected.

### 3.4 Georeferencing & Spatial Overlap Check
* Planetary coordinates verified against Lunar South Polar Stereographic CRS (`ESRI:104903`).
* Confirmed that test set de Gerlache tiles share zero geographic overlap with training set Shackleton tiles ($> 65\text{ km}$ spatial separation on lunar surface).

---

## 4. Visual Inspection Gallery Audit

Visual preview composites were rendered in `data/hazard_training/previews/` with cyan bounding boxes for craters and amber boxes for boulders:
1. `preview_train_tile_20_0.png`: Shackleton Connecting Ridge — Sharp crater rims and scattered boulder ejecta.
2. `preview_train_tile_21_0.png`: Shackleton Crater Rim Bench — High crater density under $82.5^\circ$ solar incidence.
3. `preview_val_tile_24_0.png`: Malapert Mountain Summit Massif — Smooth massif slope with distinct boulder clusters.
4. `preview_val_tile_25_0.png`: Haworth Transition Rim — Grazing illumination along PSR shadow boundary; 12 real craters cleanly enclosed.
5. `preview_test_tile_26_0.png`: de Gerlache Crater Rim 1 — Unseen holdout terrain exhibiting complex crater rim overlapping.
6. `preview_test_tile_27_0.png`: de Gerlache Crater Rim 2 — Secondary ejecta fields with high-contrast boulder shadows.

---

## 5. Storage Footprint & System Impact

* **Images (`images/`):** $15.2\text{ MB}$ (80 PNG files).
* **Annotations (`annotations/`):** $0.35\text{ MB}$ (80 TXT files + proposal task cards).
* **Manifests (`manifests/`):** $0.45\text{ MB}$ (JSON manifests and cross-reference tables).
* **Splits (`splits/`):** $0.05\text{ MB}$.
* **Previews (`previews/`):** $3.8\text{ MB}$ (High-resolution annotated inspection PNGs).
* **Total Storage:** **$19.85\text{ MB}$**.
* **System RAM Impact:** $< 250\text{ MB}$ during active dataloader execution, fully optimized for a 16 GB RAM Windows laptop.

---

## 6. Known Dataset Limitations

1. **Permanently Shadowed Regions (PSRs):** Optical detection fails completely in zero-lux shadowed craters. In PSRs, LOLA laser altimetry roughness, slope, and Mini-RF radar backscatter must be used.
2. **Sub-Pixel Boulder Limit:** In 1.2–1.8 mpp LROC NAC imagery, rocks smaller than 1.0m cannot be resolved. For boulders $< 1.0\text{ m}$, 0.25 mpp Chandrayaan-2 OHRC observations are required.
3. **Grazing Sun Angle Constraint:** The dataset is calibrated for solar incidence angles between $78.0^\circ$ and $84.5^\circ$. It cannot be applied directly to equatorial lunar imagery without domain adaptation.
4. **Mission Screening Disclaimer:** This dataset and derived models are intended for candidate landing-site qualification and mission planning; they are NOT certified for autonomous real-time terminal landing descent.
