# MoonScape — Frontend Redesign & Architectural Migration Plan

**Project:** Moonscape — Cinematic Monochromatic Lunar Mission Analysis Platform  
**Target Environment:** React 19 + TypeScript + Vite + Tailwind CSS v4 + Three.js + Motion  
**Document Status:** APPROVED & IN PROGRESS  
**Date:** November 15, 2026  

---

## 1. Vision & Art Direction Overview

The redesigned Moonscape frontend transforms the existing web application into a **cinematic, monochromatic lunar mission analysis experience** reminiscent of precision aerospace mission-control systems and high-end scientific space documentaries.

### Core Aesthetic Keywords
* **Monochrome:** Elimination of saturated neon blues, cyans, and rainbow graphs. Dominated by deep cosmic blacks (`#090909`), architectural charcoal surfaces (`#171717`, `#242424`), silver/white typography (`#F1F1EF`), and subtle graphite borders (`rgba(255,255,255,0.12)`).
* **Cinematic & Architectural:** Negative space, dramatic scale contrast, stark chiaroscuro lighting, and documentary-grade typography.
* **Precision & Scientific Rigor:** Uncompromising data truthfulness, telemetry tags, micro-monospaced labels, and zero synthetic exaggeration.
* **Subtle & Controlled Motion:** Restrained, physics-based fluid transitions via Motion for React (`motion/react`) with full `prefers-reduced-motion` compliance.

---

## 2. Component Migration Matrix

### A. Components to Preserve (Business Logic & Science Intact)
* **`AppContext.tsx`:** Coordinates, backend status mode ("live" / "mock"), selection state, analysis triggers, score queries, hazard detections, and mission configurations.
* **`services/api.ts`:** Typed endpoints, request handling, error boundaries, and response mapping.
* **`utils/format.ts`:** Scientific unit formatting (`fmtCoord`, `fmtNum`, `pickNumber`, `pickString`).
* **`hooks/useHashRoute.ts`:** Hash routing ensuring clean standalone client navigation without server router requirements.

### B. Components to Restyle (Visual Modernization to Monochrome Aerospace System)
* **`Navbar.tsx`:** Minimal top bar with architectural spacing, sleek monospaced telemetry status, subtle active indicator lines, and accessible menu.
* **`Footer.tsx`:** Editorial colophon aesthetic, quiet monochrome data source citations, and disclaimers.
* **`TerrainCard.tsx`:** Precision metric typography, high-contrast dark panels, removing blue card gradients.
* **`SuitabilityScore.tsx`:** Monochromatic score dials with subdued semantic alert indicators (restrained amber/emerald only for critical thresholds).
* **`HazardPanel.tsx`:** Scientific detection table with clean monochrome confidence bars and high-contrast bounding box inspection.
* **`CandidateRegionsPanel.tsx` & `SimulationPanel.tsx`:** Streamlined timeline scrubbing and contour summaries.
* **`SiteComparison.tsx`:** Architectural comparison matrix with crisp tabular typography.
* **`AIExplanation.tsx`:** Clean mission brief dossier typography.

### C. Components Requiring Structural & Experience Improvements
* **`Home.tsx`:** Complete transformation into the reference composition:
  * **Left:** Technical eyebrow tag, massive sparse MoonScape typography, succinct mission briefing, primary "Explore Surface" CTA, secondary "Mission Dossier" action, and real-time polar coordinate indicator.
  * **Right:** Massive interactive photorealistic 3D Moon powered by Three.js with realistic directional sunlight, surface craters/roughness, subtle inertia rotation, and mouse parallax.
  * **Bottom:** Minimalist vertical section marker and telemetry microcopy.
* **`LunarMap.tsx`:** Clean monochrome polar stereographic shader/lighting updates, crisp reticles, and smooth camera tweening.
* **`index.css`:** Replacement of blue/cyan variables with the new monochromatic color scale, typography definitions, and component primitives.

### D. Components to Add
* **`CinematicMoon.tsx`:** Dedicated Three.js photorealistic lunar globe component for the homepage with progressive texture loading, physically plausible directional lighting, and graceful 2D fallback.
* **`CesiumLunarViewer.tsx`:** Optional high-precision geospatial viewer for 3D lunar surface navigation with custom lunar ellipsoid.
* **`CreditsModal.tsx` / `Credits.tsx`:** Dedicated mission credits and planetary data provenance panel accessible directly from navigation.

---

## 3. Third-Party Dependencies Evaluation

1. **`three` & `@types/three` (Installed):** Core 3D engine for real-time interactive lunar globes, lighting, and coordinate raycasting.
2. **`motion` (Installed):** Official Motion for React library for fluid entrance reveals, navigation drawers, and tab transitions.
3. **`cesium` (Installed):** Specialized geospatial engine for planetary coordinate projection and high-fidelity tile rendering.
4. **Tailwind CSS v4 (Installed):** Styling engine powered by the new monochromatic CSS theme tokens.

---

## 4. Preservation of Scientific Workflow

The frontend redesign preserves all 11 core scientific capabilities without modification:
1. LOLA digital elevation model extraction (`/api/terrain/point`).
2. Topographic slope calculations and Apollo/Artemis tip-over margins.
3. RMS surface roughness and footpad obstacle hazards.
4. Automated contiguous candidate landing zone delineation (`/api/landing-sites/detect`).
5. Optical crater and boulder detection (`POST /api/hazards/predict`).
6. Solar illumination diurnal simulations (`/api/simulation/visibility`).
7. Earth direct line-of-sight communications visibility.
8. Multi-criteria suitability scoring (MCDA) and Random Forest ML inference (`/api/score`).
9. AI scientific assistant explanation synthesis (`/api/ai/explain`).
10. Target coordinate selection across polar candidate corridors.
11. Real-data mode enforcement with explicit fallback warnings.

---

## 5. Execution Roadmap

```
[Phase 1] Design Tokens & Theme Setup in index.css
    │
[Phase 2] Shared Typography & Component Classes
    │
[Phase 3] Minimalist Navigation Bar & Credits View
    │
[Phase 4] Photorealistic Three.js Moon & Cinematic Homepage
    │
[Phase 5] Fluid Motion Integration across Transitions
    │
[Phase 6] Map-First Explorer Redesign
    │
[Phase 7] Scientific Pages (Dashboard, Hazards, Compare, Report)
    │
[Phase 8] Verification, Performance Benchmarks & Build Check
```
