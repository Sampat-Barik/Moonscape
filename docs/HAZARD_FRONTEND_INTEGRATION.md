# MoonScape — Frontend Hazard Integration & User Experience Specification

**Document ID:** `DOC-HAZ-FE-2026-003`  
**Target Component:** `Frontend/src/components/HazardPanel.tsx`, `Frontend/src/pages/Explorer.tsx`, `Frontend/src/services/api.ts`, `Frontend/src/types.ts`  
**Design Paradigm:** High-Precision Aerospace Telemetry & Monochromatic Cinematic Visual Hierarchy  
**Status:** Certified & Deployed  

---

## 1. Architectural Overview

The MoonScape Hazard Analysis interface has been completely restructured to eliminate misleading visual placeholders and present an uncompromising, mathematically grounded assessment of lunar landing hazards.

The renovated `HazardPanel.tsx` is organized into **four distinct scientific sections**:
1. **Section A · DEM Topographic Hazards:** Evaluates physical slope gradients, RMS surface roughness anomalies, and curvature depressions derived directly from digital elevation models.
2. **Section B · Optical ML Hazard Detection:** Renders real georeferenced bounding box detection overlays and tabular candidate metrics from high-resolution NASA LROC NAC polar orbital frames.
3. **Section C · Dataset Coverage & Provenance:** Displays unambiguous telemetry regarding exploration coverage tier, orbital observation product ID, spatial ground resolution, altimetry tier, and ML inference engine.
4. **Section D · Scientific Limitations & Operational Constraints:** Communicates mission-critical disclaimers, including Apollo lighting domain shift warnings, zero-lux Permanently Shadowed Region (PSR) constraints, and research-grade safety classification.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SECTION HEADER METRICS                                                      │
│ Lat / Lon / Radius / Evaluation Tier / Touchdown Classification             │
├─────────────────────────────────────────────────────────────────────────────┤
│ SECTION A · DEM TOPOGRAPHIC HAZARDS                                         │
│ • Horn Gradient Slope Escarpments (>15°)                                    │
│ • RMS Elevation Roughness Anomalies (>1.5m)                                 │
│ • Concave Curvature Depressions (Laplacian Kernel)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ SECTION B · OPTICAL CRATER & BOULDER DETECTION                              │
│ • Real Georeferenced LROC NAC Overlay Image (Cyan=Craters, Amber=Boulders)   │
│ • Optical Scan Status (Success / Partial / Not Available)                   │
│ • Detected Craters Table & Detected Boulders Table                          │
│ • Truthful Empty States (Differentiates 0 detections from No Optical Data)  │
├─────────────────────────────────────────────────────────────────────────────┤
│ SECTION C · DATASET COVERAGE & PROVENANCE                                   │
│ • Exploration Coverage Zone (Core / Extended / Context)                     │
│ • Optical Observation Frame (e.g. LROC_NAC_POLAR_M145129840LE @ 1.8 mpp)     │
│ • Altimetry Topographic Model (LOLA DEM ESRI:104903)                        │
│ • Detection Engine (YOLOv8n PyTorch / ONNX Engine)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ SECTION D · SCIENTIFIC LIMITATIONS & OPERATIONAL CONSTRAINTS                │
│ • Apollo Lighting Domain Shift Warning                                      │
│ • Permanently Shadowed Region (PSR) LiDAR / Radar Fallback Requirement      │
│ • Flight Certification / Autonomous Descent Disclaimer                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Truthful Semantics & Data Handling

### 2.1 Null vs. Zero Representation
A foundational requirement of scientific telemetry is that the absence of observation data must never be reported as a zero measurement.
- **When Optical Data is Present:**
  - If YOLOv8n detects 12 craters: `crater_count = 12`.
  - If YOLOv8n detects 0 boulders: `rock_count = 0` (rendered as *"Optical scan completed: zero boulders satisfying detection confidence threshold"*).
- **When Optical Data is Absent:**
  - `crater_count = null`, `rock_count = null`, `overlay_image = null`.
  - The UI suppresses numerical counters and renders a dedicated `DataUnavailable` component:
    > *"Optical detection unavailable for this location (no intersecting orbital imagery)"*
- **No Coercion:** JavaScript fallback operators (`value || 0`) were systematically replaced with strict `pickNumber` and null-checking utilities to ensure `null` is never coerced to `0`.

### 2.2 Removal of Static Illustrative Imagery
The legacy interface displayed a static mockup image (`landing-site-closeup.webp`) whenever an analysis was triggered.
- **New Behavior:** The image viewer renders **only authentic georeferenced detection overlays** produced by the YOLOv8n engine (`data:image/png;base64,...`).
- When no optical frame covers the site, the image viewer is cleanly replaced with an empty state illustrating that altimetry LiDAR measurements are the active modality.

---

## 3. Extended Coverage UI in Explorer

The Lunar Explorer page (`Frontend/src/pages/Explorer.tsx`) has been upgraded to support the expanded coverage zones:
- **Input Boundaries:** Allows manual entry and globe point selection for latitudes from $-90.0^\circ$ to $-70.0^\circ$.
- **Live Coverage Tier Badge:** Directly above the coordinate inputs, a live status badge indicates the exploration tier:
  - **Core Tier ($-90^\circ$ to $-80^\circ$):** *"Core Corridor (-90° to -80°)"* — Full orbital and DEM resolution.
  - **Extended Tier ($-80^\circ$ to $-75^\circ$):** *"Extended South Pole (-80° to -75°)"* — Extended highland corridor.
  - **Context Tier ($-75^\circ$ to $-70^\circ$):** *"Context Region (-75° to -70°)"* — Regional terrain context.
- **Boundary Validation:** Inputs beyond $-70.0^\circ$ are blocked with user feedback informing them of the South Pole analysis envelope.

---

## 4. Visual Design System & Monochromatic Polish

The user interface strictly adheres to the monochromatic cinematic aerospace design system:
- **Palette:** Jet black background (`#0a0a0a`), carbon elevated cards (`#141414`), charcoal borders (`#262626`), muted secondary text (`#737373`), and crisp lunar titanium headers (`#f1f1ef`).
- **Detection Overlay Palette:** Cyan (`#00e5ff`) with subtle drop shadow for crater rims; Amber (`#ffb300`) for boulder candidate bounding boxes.
- **Typography:** Monospaced tabular figures (`font-mono`) for numerical telemetry, coordinates, and product IDs to ensure alignment across viewports.
- **Responsiveness:** Fluid grid columns (`sm:grid-cols-2 lg:grid-cols-4`) ensuring seamless viewing on mobile, tablet, and high-DPI desktop displays.
