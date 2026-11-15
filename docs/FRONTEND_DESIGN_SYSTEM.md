# MoonScape — Monochromatic Cinematic Design System

**Project:** Moonscape Lunar Mission Analysis Platform  
**Design Version:** 2.0-monochrome  
**Aesthetic:** Cinematic Aerospace Documentary + Precision Mission Control  
**Date:** November 15, 2026  

---

## 1. Design Principles

1. **Monochrome Dominance:** Pure blacks, rich charcoals, and stark silvers. Color is never decorative; it is reserved exclusively for vital semantic alerts (e.g. hazardous slopes $> 10^\circ$).
2. **Architectural Restraint:** Clean negative space, generous margins, sharp geometric outlines, and crisp $1\text{px}$ dividers. No fuzzy colorful dropshadows or glowing neon borders.
3. **Typography as Structure:** Stark visual contrast between massive, sparse editorial headlines and micro-monospaced technical metadata tags.
4. **Physical Plausibility:** Lighting and rendering mimic the harsh vacuum of space—stark sunlight, pitch-black shadows, zero atmospheric haze.
5. **Quiet Motion:** Physics-based micro-interactions, smooth camera transitions, and controlled fade reveals that respect `prefers-reduced-motion`.

---

## 2. Color Palette & Semantic Tokens

### Core Neutral Palette

```
+------------------+---------+-------------------------------------------------------+
| Token Name       | Hex / Value | Usage Description                                 |
+------------------+---------+-------------------------------------------------------+
| `--color-space`   | #090909 | Deep cosmic void background                           |
| `--color-deep`    | #111111 | Recessed container background                         |
| `--color-surface` | #171717 | Primary content card surface                          |
| `--color-elevated`| #242424 | Elevated modals, dropdowns, floating panels           |
| `--color-ink`     | #F1F1EF | Primary high-contrast typography                      |
| `--color-muted`   | #999999 | Secondary technical labels, metadata, captions        |
| `--color-faint`   | #555555 | Disabled states, subtle reticle ticks, guide lines    |
| `--color-divider` | rgba(255,255,255,0.10) | Structural card borders and dividing rules |
| `--color-highlight`| rgba(255,255,255,0.18)| Active selection border, focused input outline |
+------------------+---------+-------------------------------------------------------+
```

### Subdued Semantic Accents (Restrained Use Only)

```
+------------------+---------+-------------------------------------------------------+
| Token Name       | Hex     | Permitted Context                                     |
+------------------+---------+-------------------------------------------------------+
| `--color-good`   | #4ADE80 | Acceptable touchdown criteria, verified data integrity|
| `--color-warn`   | #FBBF24 | Marginal criteria, uncalibrated optical estimates     |
| `--color-bad`    | #F87171 | Disqualified landing slope, critical crater hazard    |
+------------------+---------+-------------------------------------------------------+
```

*Rule: Semantic colors are applied strictly to badges, status dots, and warning banners. Buttons, navigation links, cards, and headers MUST remain monochromatic.*

---

## 3. Typography Scale & Hierarchy

### Typefaces
* **Display & Headlines:** `"Space Grotesk"`, sans-serif (Architectural, high-impact, geometric).
* **Technical Labels & Telemetry:** `"IBM Plex Mono"`, monospace (Tabular, precise, coordinates, measurements).
* **Editorial Body:** `"Inter"`, sans-serif (Clean, neutral, highly legible at small sizes).

### Type Hierarchy Specifications

```
+---------------+------------------------+------------------+-----------------------------+
| Role          | Font Family            | Size / Line-Ht   | Case / Letter-Spacing       |
+---------------+------------------------+------------------+-----------------------------+
| Hero Title    | Space Grotesk (Bold)   | 5.5rem - 7.5rem  | Uppercase, tracking -0.03em |
| Page Heading  | Space Grotesk (Semibold)| 2.25rem - 3.0rem | Normal case, tracking -0.02em|
| Section Title | Space Grotesk (Medium) | 1.25rem - 1.5rem | Normal case, tracking -0.01em|
| Eyebrow / Tag | IBM Plex Mono (Medium) | 0.70rem - 0.75rem| Uppercase, tracking +0.15em |
| Body Text     | Inter (Regular)        | 0.875rem (14px)  | Normal case, leading 1.6    |
| Telemetry Data| IBM Plex Mono (Regular)| 0.8125rem (13px) | Tabular figures, no spacing |
| Microcopy     | IBM Plex Mono (Regular)| 0.65rem (10.5px) | Uppercase, tracking +0.10em |
+---------------+------------------------+------------------+-----------------------------+
```

---

## 4. UI Components Specification

### 1. Panel Surface (`.panel`)
* **Background:** Solid or translucent `#171717` with subtle linear gradient (`linear-gradient(180deg, #1A1A1A 0%, #141414 100%)`).
* **Border:** `1px solid rgba(255, 255, 255, 0.10)`.
* **Radius:** `4px` or `6px` (sharp, architectural corners; avoid pill-shaped cards).
* **Shadow:** `0 12px 32px -8px rgba(0, 0, 0, 0.8)`.

### 2. Primary Action Button (`.btn-primary`)
* **Background:** High-contrast white/silver `#F1F1EF`.
* **Text:** Solid deep black `#090909`, uppercase, font-weight 600, tracking `0.08em`.
* **Hover:** Subtle silver glow, background `#FFFFFF`, translateY `-1px`.
* **Active:** Background `#D9D9D6`, translateY `0px`.

### 3. Ghost / Secondary Action Button (`.btn-ghost`)
* **Background:** Transparent or `rgba(255, 255, 255, 0.04)`.
* **Border:** `1px solid rgba(255, 255, 255, 0.14)`.
* **Text:** `#F1F1EF`.
* **Hover:** Border `rgba(255, 255, 255, 0.40)`, background `rgba(255, 255, 255, 0.08)`.

### 4. Technical Telemetry Chip (`.chip`)
* **Background:** `#111111`.
* **Border:** `1px solid rgba(255, 255, 255, 0.08)`.
* **Typography:** `font-mono text-[11px] text-[#999999]`.
* **Active State:** Border `#FFFFFF`, text `#FFFFFF`.

---

## 5. 3D Planetary Visualization Specifications

1. **Color Profile:** Grayscale surface reflectance ($I/F$), gamma corrected for realistic dynamic range.
2. **Lighting Model:** Single directional light simulating the distant Sun, zero ambient bounce in empty space, and subtle rim light ($< 10\%$ intensity) to maintain silhouette definition against deep space.
3. **Surface Texture:** Authentic NASA LROC WAC 2K global basemap paired with LOLA 8-bit elevation normal displacement.
4. **Interaction:** Smooth inertia damping ($0.05$), restricted zoom limits, and mouse hover parallax.
