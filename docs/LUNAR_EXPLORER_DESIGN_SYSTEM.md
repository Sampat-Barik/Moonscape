# Lunar Explorer — Design System, Button Hierarchy & Component Specification

**Document ID:** SPEC-EXPLORER-DS-001  
**Project:** MoonScape (NASA Lunar South Pole Mission Site Analysis)  
**Authors:** Senior React Engineer & High-End Interface Design Engineer  
**Inspection Date:** November 15, 2026  
**Status:** **ACTIVE SPECIFICATION & DEPLOYED COMPONENT LIBRARY**  

---

## 1. Visual Language & Architectural Philosophy

The Lunar Explorer interface design system is built upon a restrained, cinematic, monochromatic aerospace aesthetic. It rejects generic gaming HUDs, gratuitous neon glows, and saturated blue buttons in favor of high-contrast regolith tones, architectural typography, and purposeful semantic indicators.

### 1.1 Core Monochromatic Design Tokens

| Token Name | Value | Purpose |
| :--- | :--- | :--- |
| `--color-space` | `#090909` | Deep vacuum canvas & main page background |
| `--color-surface` | `#151515` | Level 3 Sidebar primary background |
| `--color-deep` | `#121212` | Level 2 Toolbar background & recessed containers |
| `--color-elevated` | `#242424` | Active segmented pills, hovered cards, input surfaces |
| `--color-ink` | `#F1F1EF` | Primary typographic headlines, labels, coordinates |
| `--color-muted` | `#999999` | Secondary metadata tags, metric labels, descriptions |
| `--color-divider` | `rgba(255, 255, 255, 0.12)` | Hairline grid borders & structural section rules |
| `--color-good` | `#4ade80` | Nominal safety status & covered data |
| `--color-warn` | `#fbbf24` | Marginal caution & outside polar coverage warning |
| `--color-bad` | `#f87171` | Critical landing slope hazard & tip-over risk |

---

## 2. Complete Button Design System

The platform replaces all arbitrary inline button styles with a unified, accessible button system implemented in [Frontend/src/components/ui/Button.tsx](file:///d:/MoonScape/Frontend/src/components/ui/Button.tsx) and [Frontend/src/index.css](file:///d:/MoonScape/Frontend/src/index.css).

### 2.1 Variant Specifications

#### Primary Action (`.btn-primary` / `<Button variant="primary">`)
- **Use Cases:** `RUN FULL MISSION ANALYSIS`, critical flight confirmations.
- **Visual Design:** Off-white background (`#F1F1EF`), near-black text (`#090909`), solid white border (`#FFFFFF`).
- **Typography:** `var(--font-condensed)`, weight 600, letter spacing `0.08em`, uppercase.
- **Dimensions:** Min-height $44\text{px}$ (`btn-lg`) or $42\text{px}$ (`btn-md`), horizontal padding $1.375\text{rem}$ ($22\text{px}$), border radius $6\text{px}$ (`rounded-md`).
- **States:**
  - *Hover:* Background `#FFFFFF`, subtle halo shadow `0 0 16px rgba(255, 255, 255, 0.16)`, translateY `(-1px)`.
  - *Active:* translateY `(0)`.
  - *Focus-visible:* Dual-ring outline (`box-shadow: 0 0 0 2px #090909, 0 0 0 4px rgba(255, 255, 255, 0.6)`).
  - *Loading:* Displays an integrated, hardware-accelerated SVG spinner with disabled interactions.
  - *Disabled:* Opacity $0.4$, cursor `not-allowed`.

#### Secondary Action (`.btn-secondary` / `<Button variant="secondary">`)
- **Use Cases:** `Inspect 3D Terrain Relief →`, `Center Connecting Ridge`, `Hide / Show Panel`.
- **Visual Design:** Dark graphite surface (`#181818`), subtle hairline border (`rgba(255, 255, 255, 0.12)`), off-white text (`#F1F1EF`).
- **Dimensions:** Min-height $38\text{px}$, horizontal padding $1.125\text{rem}$ ($18\text{px}$), border radius $6\text{px}$.
- **States:**
  - *Hover:* Background `#242424`, border-color `rgba(255, 255, 255, 0.28)`, text `#FFFFFF`.
  - *Focus-visible:* Ring outline with 40% white opacity.

#### Ghost / Tertiary Action (`.btn-ghost` / `<Button variant="ghost">`)
- **Use Cases:** Basemap popover trigger, Layers trigger, Solar simulation toggle, Reset South Pole.
- **Visual Design:** Transparent background (`rgba(255, 255, 255, 0.02)`), subtle hairline border (`rgba(255, 255, 255, 0.12)`), muted text (`#999999`).
- **Dimensions:** Min-height $36\text{px}$ (`btn-sm` $34\text{px}$), horizontal padding $0.875\text{rem}$, border radius $6\text{px}$.
- **States:**
  - *Hover:* Text `#FFFFFF`, background `rgba(255, 255, 255, 0.06)`, border-color `rgba(255, 255, 255, 0.30)`.

---

## 3. Segmented View Mode Selector Component

Implemented in [Frontend/src/components/ui/SegmentedControl.tsx](file:///d:/MoonScape/Frontend/src/components/ui/SegmentedControl.tsx).

### 3.1 Architectural Features
- **Labels:** `Globe` (Three.js Orbital Sphere), `Terrain` (LOLA 5m DEM 3D Relief), `Cesium` (CesiumJS IAU Moon Ellipsoid).
- **Smooth Physics Transitions:** Utilizes `motion.div` from `motion/react` with `layoutId="segmented-active-pill"` and a spring transition (`stiffness: 450, damping: 35`), allowing the active graphite indicator to smoothly glide between modes.
- **Accessibility & ARIA Compliance:**
  - Implements `role="radiogroup"` on the container with `aria-label="View mode selector"`.
  - Implements `role="radio"` with `aria-checked={true/false}` on each option button.
  - Implements full keyboard navigation via arrow keys (`ArrowRight`, `ArrowLeft`, `Home`, `End`), automatically shifting active selection and DOM focus.
- **Resource Management:** Does not remount WebGL contexts unnecessarily. Inactive renderers are safely detached to conserve laptop GPU VRAM.

---

## 4. Popover & Toolbar Dropdown System

To prevent cluttering the top toolbar with dozens of persistent controls, secondary options are housed in accessible popovers:

1. **Basemap Dropdown (`data-toolbar-menu`):**
   - Trigger: `LayersIcon` + `"Basemap"` + `ChevronDownIcon`.
   - Options: `LROC WAC 2K Albedo` (Equirectangular) and `NASA Moon Trek WMTS` (100m/px OGC streaming tiles).
   - Real-time checkmark indicator reflecting active basemap.
2. **Scientific Overlays Dropdown:**
   - Trigger: `SlidersIcon` + `"Layers"` + `ChevronDownIcon`.
   - Displays real-time operational status for Horn slope colormapping, candidate zone footprints, and polar graticules.
3. **Solar Diurnal Cycle Popover:**
   - Trigger: `SunIcon` + `Day ${d} / 29.5d`.
   - Popover contains an interactive slider ($0^\circ$ to $360^\circ$) calculating apparent solar azimuth and simulated shadow length.
4. **Behavioral Safety:**
   - Listens for `Escape` key and outside `mousedown` events to automatically dismiss open menus.
   - Positioned with `absolute top-full mt-2 right-0 z-40` above the 3D canvas with shadow elevation.

---

## 5. Mission Analysis Sidebar Component System

The right sidebar ([Frontend/src/pages/Explorer.tsx](file:///d:/MoonScape/Frontend/src/pages/Explorer.tsx)) is organized into 6 functional sections:

- **Section 01 — Target Coordinates:** High-contrast coordinate display (`fmtCoord`), radius readout, and polar coverage validation tag.
- **Section 02 — Numerical Coordinate Adjustment:** Explicit number inputs for Latitude and Longitude with unit labels, radius selector chips ($250\text{m}$, $500\text{m}$, $1000\text{m}$, $2000\text{m}$), and a quick-center button.
- **Section 03 — Candidate Regions:** Verified Artemis candidate site chips (Connecting Ridge, Shackleton Rim, Faustini Rim, Malapert Massif, South Pole, de Gerlache) featuring active state borders and lat/lon coordinate subtitles.
- **Section 04 — Regional Terrain Metrics Preview:** Clean metric rows showing real-time elevation ($+1940.7\text{ m}$), slope ($6.05^\circ$), roughness ($0.21\text{ m}$), and insolation ($86.4\%$), with an `"Inspect 3D Terrain Relief →"` action button.
- **Section 05 — NASA Reconnaissance & Archives:** LROC NAC stereo DTM coverage status and deep link button (`Open in NASA LROC QuickMap ↗`).
- **Section 06 — Primary Mission Analysis Action:** Sticky bottom container hosting the prominent $44\text{px}$ `RUN FULL MISSION ANALYSIS` primary button with loading spinner state.
