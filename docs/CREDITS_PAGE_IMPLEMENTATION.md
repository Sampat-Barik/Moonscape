# MoonScape — Scientific Credits, Data Provenance & Team Page Implementation

**Document ID:** ARCH-CREDITS-001  
**Project:** MoonScape (Autonomous Lunar South Pole Landing Site Analysis Platform)  
**Component:** `Frontend/src/pages/Credits.tsx`  
**Route:** `#/credits`  
**Authors:** Senior React Engineer, Information Designer, Scientific Data Specialist  
**Verification Date:** November 15, 2026  
**Status:** **IMPLEMENTED & VERIFIED (BUILD PASSING)**  

---

## 1. Architectural Overview & Objective

The Credits page (`Frontend/src/pages/Credits.tsx`) serves as the capstone chapter of the MoonScape mission analysis web application. Styled with the restraint, depth, and atmospheric precision of a scientific documentary, it presents the complete computational and observational provenance behind every metric, gradient, and landing suitability score calculated by the platform.

Unlike typical software attribution pages that merely list dependency names, the MoonScape Credits page acts as an interactive, audit-grade scientific registry. It allows flight controllers, planetary scientists, and software evaluators to:
1. Trace physical measurements directly to their NASA/LRO instrument origins.
2. Interactively explore the 6-stage end-to-end dataflow pipeline from orbital laser pulses to mission dossiers.
3. Verify formal academic citations, instrument limitations, and geodetic reference frames.
4. Audit the underlying open-source computational stack.
5. Review the official project team roster and institutional non-endorsement declaration.

---

## 2. Visual Hierarchy & Monochromatic Art Direction

In strict accordance with the MoonScape cinematic design system, the Credits page avoids saturated SaaS accent colors, gratuitous glow effects, or decorative illustrations. Instead, it utilizes an architectural, monochromatic palette evoking the stark contrast of the lunar South Pole:

| Design Token | Hex / Value | Architectural Purpose |
| :--- | :--- | :--- |
| **Space Black** | `#090909` | Deep vacuum background |
| **Deep Charcoal** | `#111111` | Secondary recessed surfaces |
| **Surface Graphite** | `#171717` | Standard card panel surface (`.panel`) |
| **Elevated Surface** | `#242424` | Active interactive elements & hovered states |
| **Lunar Silver / Ink** | `#F1F1EF` | High-contrast typographic headlines & labels |
| **Muted Regolith** | `#999999` | Secondary scientific prose & metadata tags |
| **Hairline Dividers** | `rgba(255, 255, 255, 0.12)` | Clean structural borders & grid lines |
| **Subtle Grid Overlay** | `64px x 64px (3.5% opacity)` | Cartographic coordinate grid background |

---

## 3. Section-by-Section Structural Breakdown

### Section 1 — Editorial Opening Statement
- **Monospace Taxonomy Header:** `[07] MISSION PROVENANCE & SCIENTIFIC ATTRIBUTION` with live verification badge.
- **Editorial Headline:** `"THE SCIENCE BEHIND THE SURFACE."` set in bold, uppercase *Space Grotesk*.
- **Narrative Content:** Explains the physical realities of the lunar South Pole (80°S–90°S), grazing solar angles (< 2°), permanent shadows, and how MoonScape synthesizes NASA LOLA laser altimetry, LROC optical reconnaissance, and JPL Horizons celestial mechanics to eliminate speculative guesswork in landing site qualification.
- **Telemetry Card:** Displays target coordinate reference system (`IAU 2000 Moon / ESRI:104903`), altimetry resolution bounds (5 m micro-DEM, 80 m regional DEM), ephemeris integration core (JPL DE421/DE441), and verified asset count (12 sources).

### Section 2 — Interactive Scientific Data Directory
- **Filtering System:**
  - Category Pills: `ALL SOURCES (12)`, `TERRAIN & ELEVATION`, `OPTICAL IMAGERY`, `SOLAR GEOMETRY`, `EARTH COMMS`, `HAZARDS`, `AI & ML MODELS`, `FRAMEWORKS`.
  - Real-time text search filter: Matches name, organization, instrument, purpose, or product ID.
- **Card Metadata:**
  - Category classification tag (`[CAT A]` through `[CAT F]`).
  - Integration Status Badge:
    * `Actively Used` (Green tint: Direct numerical computation or primary Three.js texturing).
    * `Actively Integrated` (Silver tint: Live HTTPS API queries to JPL Horizons or Moon Trek).
    * `Actively Configured` (Amber tint: Machine learning model inference via PyTorch / Scikit-Learn).
    * `Reference Only` (Neutral tint: Literature citations and interaction references).
  - Spatial and temporal resolution specifications.
  - Geographic coverage boundaries.
  - Operational purpose in MoonScape.
- **Interactive Expandable Drawer:**
  - Toggled via `"VIEW CITATION & LIMITS"` button.
  - Reveals local file paths / integration modules, verified formal academic citations (DOI, authors, journals), and physical sensor limitations (e.g., laser footprint spacing, polar projection distortion).
  - Direct external hyperlink to official NASA/PDS/JPL archives.

### Section 3 — Interactive 6-Stage Scientific Pipeline
A stepped dataflow architecture showing how raw orbital telemetry transforms into operational mission intelligence:
1. **Stage 01 — NASA Orbital Observations:** LOLA Product 90, Product 78, LROC WAC mosaic, JPL Horizons ephemerides.
2. **Stage 02 — Geospatial & Geodetic Processing:** Polar stereographic re-projection (`ESRI:104903`), GeoTIFF parsing via Rasterio, bilinear sub-pixel interpolation.
3. **Stage 03 — Terrain & Hazard Analysis:** Horn (1981) 8-neighbor slope matrix $\theta$, RMS roughness $\sigma_z$ across 10m–50m baselines, YOLOv8 optical obstacle bounding boxes.
4. **Stage 04 — Solar & Earth Visibility Modeling:** Astronomical topocentric vector math, 360° radial DEM ray-tracing shadow occultation, and Earth line-of-sight elevation tracking.
5. **Stage 05 — Landing-Site Multi-Criteria Scoring:** Analytical Multi-Criteria Decision Analysis (MCDA) matrix and 24-feature Random Forest regressor (`v2`).
6. **Stage 06 — Grounded AI Explanation & Dossier:** Contextual flight safety rationales, hazard mitigation advice, and publication-ready vector PDF mission dossiers (`ReportLab`).

*Interactivity:* Clicking any of the 6 stages dynamically updates the deep-dive inspector, revealing input datasets, backend Python service paths, derived physical equations, and flight decision value.

### Section 4 — Computational & Visualization Stack
Understated, typography-driven technical specification grid detailing all 14 core packages:
- **Client & Graphics:** React 19.2, TypeScript 5.9, Three.js r187, CesiumJS 1.147, Motion for React 14.14, Tailwind CSS 4.1.
- **Scientific Backend:** FastAPI 0.115, Python 3.10+, ReportLab 4.2.
- **Geospatial & Mathematics:** NumPy 2.1+, SciPy 1.14+, Rasterio 1.4+, PyProj 3.6+.
- **Machine Learning:** Scikit-Learn 1.5+, PyTorch 2.5+, ONNX Runtime 1.19+.

### Section 5 — Scientific Acknowledgements & Legal Disclaimer
- **Academic Bibliography:** Formal bibliographic entries for Barker et al. (2021), Smith et al. (2010), Horn (1981), Robinson et al. (2010), and Giorgini et al. (1996).
- **Institutional Non-Endorsement Notice:** Explicit compliance with 14 CFR § 1212.100, stating unequivocally that MoonScape is an independent academic project not affiliated with or endorsed by NASA or the Artemis Program.

### Section 6 — The Team (Roster)
Strictly adheres to project governance requirements:
- **Team Name:** `MoonScape`
- **Team Members (Exact specified order, no invented roles or titles):**
  1. `Sampat Barik`
  2. `Ritam Dawn`
  3. `Ranit Ratan Bose`
  4. `Paromita Dan`
  5. `Soumili Kar`
  6. `Somasri Mondal`

### Section 7 — Final Documentary Signature
Placed at the absolute terminus of the page:
```
MOONSCAPE

Independent lunar exploration and analysis.

Sampat Barik · Ritam Dawn · Ranit Ratan Bose
Paromita Dan · Soumili Kar · Somasri Mondal
```
Accompanied by clean navigation action buttons returning to `/explorer`, `/`, or `/report`.

---

## 4. State Management & Interaction Architecture

The page is implemented in pure React 19 with TypeScript and `motion/react`:

```typescript
// Active Category Filter State
const [selectedCategory, setSelectedCategory] = useState<SourceCategory>("all");

// Real-Time Query State
const [searchQuery, setSearchQuery] = useState("");

// Expandable Citation Drawer
const [expandedSourceId, setExpandedSourceId] = useState<string | null>(null);

// Active Pipeline Stage
const [activeStageId, setActiveStageId] = useState<string>("stage-1");
```

### Performance & Motion Optimizations
- **Memoized Filtering (`useMemo`):** Multi-factor filtering across categories and string queries operates in $< 1\text{ ms}$ over the 12 master sources, eliminating layout stutter during keystrokes.
- **Motion Layout Animations (`motion/react`):** Source cards use `<motion.div layout>` with `<AnimatePresence>` for physics-based filtering transitions without jump cuts.
- **Micro-Interaction Affordances:** Buttons and links feature explicit `cursor-pointer`, subtle border brightness adjustments on hover, and high-contrast focus rings for accessibility.

---

## 5. Verification & Quality Assurance

### 5.1 Static Type Checking
```powershell
npm --prefix Frontend run typecheck
```
- **Result:** Exited with code `0`. Zero type errors across `Frontend/src/pages/Credits.tsx` and all dependent modules.

### 5.2 Unit Test Suite Execution
```powershell
npm --prefix Frontend test
```
- **Result:** Exited with code `0`. All 19 test cases across 9 test suites passed:
  - Coordinate Validation & Formatting (Pass)
  - Scientific Null-Safe Data Pickers (Pass)
  - Number Formatting & Precision (Pass)
  - Solar Simulation Calculations (Pass)
  - Production Bundle & Asset Verification (Pass)
  - Coordinate Selection Contract (Pass)
  - Live Backend API Health & Analysis Run (Pass)
  - Invertible Polar Stereographic Conversion (Pass)
  - 3D Terrain Relief Mesh Verification (Pass)

### 5.3 Production Singlefile Bundle Build
```powershell
npm --prefix Frontend run build
```
- **Result:** Exited with code `0`.
- **Output:** `dist/index.html` (6,183.72 kB inlined bundle, gzip: 1,701.51 kB). Build duration: 13.81 seconds.

---

*MoonScape Architecture Documentation — Confirmed and Archived.*
