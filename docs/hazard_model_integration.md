# Lunar Hazard Detection Model Integration & Machine Learning Guide
## Moonscape Phase 4: Crater, Boulder, and Surface Risk Inference Engine

> **Document Version:** 1.0.0  
> **Target Audience:** ML Modeling Engineer, Backend Engineers, Planetary Mission Analysts  
> **Applicable Service:** `Backend/app/services/hazard_detection.py`  
> **API Endpoint:** `POST /api/hazards/predict`  
> **Status:** Live & Tested (68/68 Automated Tests Passing)

---

## 1. Executive Summary & Model Inspection Findings

In accordance with **Moonscape Phase 4**, the backend inference infrastructure has been constructed to receive high-resolution optical, SAR, or digital elevation surface patches and run automated machine-learning hazard inference without risking server downtime.

### Model Inspection Findings
- **Inspection Date:** November 2026
- **Model Storage Target:** `Backend/data/models/`
- **Current Weights State:** No pre-trained weights file (`.onnx` / `.pt` / `.pth`) was found in repository storage.
- **Runtime Resilience:** When no trained weights file is configured or deep learning frameworks are offline, the backend returns the exact operational status contract specified in Task 5:
  ```json
  {
    "status": "not_available",
    "detections": [],
    "crater_count": null,
    "rock_count": null,
    "warnings": ["Hazard detection model is not configured."]
  }
  ```
  The server **never crashes** due to unconfigured models, missing libraries, or corrupt image uploads.

---

## 2. Supported Frameworks & Recommended Deployment

To ensure maximum inference performance on the development laptop (**NVIDIA GeForce RTX 5070 Laptop GPU, 8 GB VRAM, 16 GB System RAM**) while maintaining cross-platform CPU compatibility, the backend natively supports:

### 1. ONNX Runtime (Recommended)
- **File Extension:** `.onnx` (e.g., `Backend/data/models/hazard_detector.onnx`)
- **Execution Providers:**
  - `CUDAExecutionProvider` (Utilizes RTX 5070 GPU via TensorRT/CUDA)
  - `CPUExecutionProvider` (Zero-GPU fallback)
- **Advantage:** Self-contained, lightweight runtime, no heavy PyTorch wheel dependencies required.

### 2. PyTorch TorchScript / State Dict
- **File Extension:** `.pt` or `.pth`
- **Format:** Exported via `torch.jit.trace()` or `torch.jit.script()`
- **Device Management:** Auto-detects `cuda` if PyTorch CUDA is enabled, otherwise runs on `cpu`.

---

## 3. Input Specification for ML Teammate

The inference preprocessor automatically handles image decoding, channel conversion, and resizing, but exported models should conform to the following standard:

| Parameter | Specification | Preprocessor Handling |
| :--- | :--- | :--- |
| **Input Tensor Shape** | `(1, 1, 512, 512)` or `(1, 3, 512, 512)` | Automatically resized using bilinear interpolation |
| **Input Color Channels** | **1 (Grayscale)** preferred for LROC NAC & LOLA DEMs; **3 (RGB)** supported | Automatically converted (`L` or `RGB`) |
| **Data Type** | `float32` | Cast automatically |
| **Normalization** | Pixel values scaled to `[0.0, 1.0]` | Scaled by dividing uint8 `[0, 255]` by `255.0` |
| **Batch Size** | `1` (Single inference tile per request) | Formatted to batch dimension `1` |

---

## 4. Output Specification & Label Mapping

The postprocessor supports two major model categories:

### A. Object Detectors (e.g., YOLO, Faster R-CNN, DETR)
Output tensor with shape `(N, 6)` or list of dictionaries containing:
- `ymin`: Normalized `[0.0, 1.0]` or pixel top boundary
- `xmin`: Normalized `[0.0, 1.0]` or pixel left boundary
- `ymax`: Normalized `[0.0, 1.0]` or pixel bottom boundary
- `xmax`: Normalized `[0.0, 1.0]` or pixel right boundary
- `confidence`: Floating point confidence score `[0.0, 1.0]`
- `class_id`: Integer label matching the class map below

#### Standard Class Mapping
```python
CLASS_MAP = {
    0: "crater",      # Impact depression, rim crest, shadow bowl
    1: "rock",        # Surface boulder / fragment
    2: "boulder",     # High-relief boulder cluster
    3: "escarpment"   # Steep scarp or fault cliff
}
```

### B. Semantic / Instance Segmentation (e.g., U-Net, DeepLabV3)
- Logit masks with shape `(C, H, W)` where $C$ is the number of hazard classes.
- Binary masks converted into contours and serialized into bounding boxes or Run-Length Encoded (RLE) strings.

---

## 5. Metadata Manifest Specification (`model_metadata.json`)

To configure model information, place a `model_metadata.json` alongside the weights file in `Backend/data/models/`:

```json
{
  "model_name": "LOLA-LROC Polar Hazard Detector",
  "version": "1.0.0",
  "framework": "ONNX",
  "architecture": "MobileNetV3-FPN Detector",
  "input_shape": [1, 1, 512, 512],
  "input_channels": 1,
  "color_mode": "grayscale",
  "normalization": {
    "type": "min_max",
    "range": [0.0, 1.0]
  },
  "classes": ["crater", "rock", "boulder", "escarpment"],
  "default_confidence_threshold": 0.50,
  "evaluation_metrics": {
    "crater_f1_score": 0.89,
    "rock_f1_score": 0.84,
    "overall_map": 0.86,
    "precision": 0.88,
    "recall": 0.85
  },
  "training_dataset": "NASA LROC NAC South Pole Orthorectified Imagery & LOLA 5m DEM Curvature Catalog",
  "validation_domain": "Orbital Lunar South Pole (Latitude -80 to -90 deg)"
}
```

---

## 6. Scientific Integrity & Sizing Calibration

### Absolute Physical Sizing Rule
> **Scientific Mandate:** Never convert segmentation pixels or bounding boxes into physical meters unless authentic spatial calibration (meters per pixel) is explicitly provided.

- **Calibrated Request:** When `spatial_resolution_mpp` (e.g., `0.5` meters/pixel) is included in the request:
  $$\text{estimated\_size\_m} = \text{round}(\max(\Delta y, \Delta x) \times \text{spatial\_resolution\_mpp}, 2)$$
- **Uncalibrated Request:** When `spatial_resolution_mpp` is null:
  - `estimated_size_m` is strictly `null`.
  - The API emits the scientific warning:
    `"Optical image scale uncalibrated; real-world metric dimensions (meters) cannot be calculated without spatial resolution (meters per pixel)."`

---

## 7. Critical Scientific Limitation: The Apollo Domain Gap

```
========================================================================================
CRITICAL SCIENTIFIC NOTICE: APOLLO SURFACE IMAGERY VS. ORBITAL SOUTH POLE DOMAIN SHIFT
========================================================================================
```

Models trained exclusively on **Apollo surface astronaut photography** (equatorial and mid-latitude landing sites) are **INVALIDATED** for autonomous lunar South Pole orbital descent certification due to the following fundamental physical differences:

1. **Solar Elevation & Grazing Angles:**
   - Apollo landing sites: Solar elevation was between $15^\circ$ and $45^\circ$, producing moderate shadows and clear surface textures.
   - Lunar South Pole: Sun grazes the horizon at $0.0^\circ$ to $1.5^\circ$, casting extreme, kilometres-long elongated shadows that obscure entire craters and falsely inflate boulder silhouettes.
2. **Permanently Shadowed Regions (PSRs):**
   - Polar craters contain permanent shadow traps ($0\text{ K} - 40\text{ K}$) with zero direct sunlight. Photometric models trained on Apollo images will fail completely in scattered secondary illumination or flash-illuminated SAR data.
3. **Cartographic Perspective:**
   - Apollo surface photos are horizontal/oblique ground-level perspectives taken by astronaut chest-mounted Hasselblad cameras.
   - Orbital South Pole imagery is acquired nadir or near-nadir by the Lunar Reconnaissance Orbiter Camera (LROC NAC) at $0.5\text{ m/pixel}$ in Polar Stereographic projection (ESRI:104903).
4. **Validation Requirement:**
   - Any model integrated into Moonscape must state its validation dataset. Models claiming polar readiness must be evaluated against authentic polar ground truth (e.g., LOLA 5m DEMs, LROC NAC South Pole polar mosaics).

---

## 8. Exporting Your Model for Moonscape

### PyTorch to ONNX Export Template
If your model was trained in PyTorch, export it using the script below:

```python
import torch
import torchvision

# 1. Load trained model
model = MyLunarDetector()
model.load_state_dict(torch.load("best_weights.pth", map_location="cpu"))
model.eval()

# 2. Dummy input matching preprocessor shape (1, 1, 512, 512)
dummy_input = torch.randn(1, 1, 512, 512, dtype=torch.float32)

# 3. Export to ONNX
torch.onnx.export(
    model,
    dummy_input,
    "Backend/data/models/hazard_detector.onnx",
    export_params=True,
    opset_version=17,
    do_constant_folding=True,
    input_names=["input_tensor"],
    output_names=["detections"],
    dynamic_axes={
        "input_tensor": {0: "batch_size"},
        "detections": {0: "batch_size", 1: "num_detections"}
    }
)
print("Successfully exported hazard_detector.onnx to Backend/data/models/")
```
Once exported, restart the backend or run `pytest Backend/tests/ -v` to verify automatic detection and inference!
