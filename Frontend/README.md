# MOONSCAPE — Lunar South Pole Landing-Site Analysis (Frontend)

Moonscape is an AI-assisted aerospace web platform engineered for exploring, analyzing, and evaluating preliminary lunar South Pole landing locations. This directory contains the **complete frontend application** (React 19 + TypeScript + Vite + Tailwind CSS v4 + Three.js).

The Python FastAPI backend is developed separately by the backend team and is consumed through a typed, centralized API integration layer.

---

## 1. System Requirements & Architecture

- **Node.js**: >= 18.0.0 (Node 20+ recommended)
- **Package Manager**: `npm`
- **Framework**: React 19 (`react`, `react-dom`)
- **Build Tool**: Vite 7 (`vite`, `@vitejs/plugin-react`, `vite-plugin-singlefile`)
- **Styling**: Tailwind CSS v4 (`@tailwindcss/vite`, `tailwindcss`)
- **3D Visualization**: Three.js (`three`, `@types/three`)
- **Type Checking**: TypeScript 5.9 (`typescript`)

---

## 2. Quick Start

### Installation
```bash
npm install
```

### Development Server
```bash
npm run dev
# Starts local Vite server at http://localhost:5173
```

### Production Build
```bash
npm run build
# Compiles optimized single-file production artifact to dist/index.html
```

### Verification & Automated Testing
```bash
npm run typecheck   # Full TypeScript verification (zero emit)
npm test            # Automated unit & integration suite via node:test
npm run preview     # Preview production build locally
```

---

## 3. Environment & Backend Configuration

The frontend does **not** hardcode backend URLs. All requests flow through `src/config.ts` and `src/services/api.ts`.

To configure your local backend connection, copy `.env.example` to `.env.local`:
```bash
cp .env.example .env.local
```

### Configuration Parameters:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | Base URL of the FastAPI backend service |
| `VITE_API_MODE` | `auto` | `auto` (probes health and falls back to mock if offline) \| `live` \| `mock` |
| `VITE_API_TIMEOUT_MS` | `10000` | Per-request timeout in milliseconds (10s) |

---

## 4. Implemented Moonscape Features (All 11 Core Features)

| # | Feature | Status | Implementation Component / Route |
| :--- | :--- | :--- | :--- |
| 1 | **Elevation Analysis** | Integration-Ready | Mean, Min, Max, StdDev in [`TerrainCard.tsx`](src/components/TerrainCard.tsx) (`/dashboard`) |
| 2 | **Slope Analysis** | Integration-Ready | Mean, Max, P95 slope in [`TerrainCard.tsx`](src/components/TerrainCard.tsx) (`/dashboard`) |
| 3 | **Roughness Analysis** | Integration-Ready | RMS and Max surface roughness in [`TerrainCard.tsx`](src/components/TerrainCard.tsx) |
| 4 | **Landing-Site Detection** | Fully Functional | 3D lunar raycaster picking + Candidate sites list (`/explorer` and Home matrix) |
| 5 | **Hazard Detection** | Integration-Ready | Boulder & crater tables with confidence metrics in [`HazardPanel.tsx`](src/components/HazardPanel.tsx) (`/hazards`) |
| 6 | **Sunlight Analysis** | Integration-Ready | Illumination %, solar elevation, duration, and sunset in [`Dashboard.tsx`](src/pages/Dashboard.tsx) |
| 7 | **Earth Visibility & Comm** | Integration-Ready | Direct-to-Earth line-of-sight communication status in [`Dashboard.tsx`](src/pages/Dashboard.tsx) |
| 8 | **Suitability Scoring & Ranking**| Integration-Ready | Preliminary score gauge ([`SuitabilityScore.tsx`](src/components/SuitabilityScore.tsx)) & Site Comparison table (`/compare`) |
| 9 | **AI Scientific Assistant** | Integration-Ready | Mission narrative synthesis & 4-category factor matrix in [`Report.tsx`](src/pages/Report.tsx) |
| 10 | **Custom Coordinate Selection** | Fully Functional | Coordinate inputs, radius selector, presets, and 3D Moon click-to-pick (`/explorer`) |
| 11 | **Time-Based Solar Simulation** | Fully Functional | Interactive orbital diurnal cycle scrubber (0–29.5d) in 3D Lunar HUD (`/explorer`) |

---

## 5. Directory Structure

```text
frontend/
├── dist/                          # Production build output (dist/index.html)
├── public/
│   ├── assets/
│   │   ├── hero/                  # Apollo & NASA LRO photography
│   │   ├── lunar/                 # Lunar surface elevation visuals
│   │   ├── models/                # NASA SVS 14959 3D lunar model (moon_small.glb)
│   │   └── textures/              # NASA SVS 4720 LROC 2K color map & LOLA DEM bump map
│   ├── images/                    # Baseline imagery assets
│   └── ASSET-MANIFEST.md          # NASA mission identifiers and public domain licenses
├── src/
│   ├── components/                # Modular UI & scientific visualization components
│   │   ├── AIExplanation.tsx      # Aerospace mission narrative synthesis
│   │   ├── CoordinateSelector.tsx # Lat/lon/radius input & preset selector
│   │   ├── DataUnavailable.tsx    # Null-safe data fallback label
│   │   ├── ErrorBoundary.tsx      # UI & WebGL crash recovery boundary
│   │   ├── ErrorState.tsx         # Actionable error notification panel
│   │   ├── Footer.tsx             # Aerospace footer with NASA attributions
│   │   ├── HazardPanel.tsx        # Crater & rock hazard inspection table
│   │   ├── icons.tsx              # Lightweight stroke-based inline SVG icons
│   │   ├── LoadingState.tsx       # Standardized loading indicator
│   │   ├── Logo.tsx               # Minimal vector crescent logo
│   │   ├── LunarMap.tsx           # Three.js 3D Moon with LOLA bump relief & solar simulation
│   │   ├── Navbar.tsx             # Fixed navigation, mode pill, and high-contrast toggle
│   │   ├── SiteComparison.tsx     # Side-by-side telemetry comparison table
│   │   ├── Stars.tsx              # Canvas starfield background
│   │   ├── SuitabilityScore.tsx   # Score gauge & breakdown visualization
│   │   └── TerrainCard.tsx        # Scientific metric readout card
│   ├── context/
│   │   └── AppContext.tsx         # Central state store for selection, analysis, and API modes
│   ├── hooks/
│   │   ├── useHashRoute.ts        # Zero-dependency hash router
│   │   └── useReveal.ts           # IntersectionObserver scroll reveal hook
│   ├── pages/
│   │   ├── Home.tsx               # Cinematic aerospace homepage
│   │   ├── Explorer.tsx           # Full-screen 3D Lunar Explorer workspace
│   │   ├── Dashboard.tsx          # Mission-control terrain analysis dashboard
│   │   ├── Hazards.tsx            # Hazard detection workspace
│   │   ├── Compare.tsx            # Candidate landing site comparison
│   │   └── Report.tsx             # Aerospace research dossier & printable PDF export
│   ├── services/
│   │   ├── api.ts                 # Centralized, typed backend API client
│   │   └── mockData.ts            # Deterministic offline demo mode generator
│   ├── utils/
│   │   ├── cn.ts                  # Tailwind class merge helper
│   │   └── format.ts              # Coordinate and null-safe data extraction utilities
│   ├── App.tsx                    # Root application shell
│   ├── config.ts                  # Environment configuration & URL resolvers
│   ├── index.css                  # Tailwind v4 theme, design tokens, and @media print
│   ├── main.tsx                   # React 19 entry point
│   └── types.ts                   # Authoritative TypeScript API schemas
├── tests/
│   └── unit.test.mjs              # Automated node:test unit & integration test suite
├── .env.example                   # Clean template for environment variables
├── .gitignore                     # Production Git ignore rules
├── index.html                     # Application entry point with Space Grotesk & IBM Plex Mono
├── package.json                   # Scripts, dependencies, and metadata
├── tsconfig.json                  # Strict TypeScript compiler options
└── vite.config.ts                 # Vite bundler configuration
```

---

## 6. Build Troubleshooting & Known Limitations

- **Backend Offline Fallback**: If the FastAPI backend is not running at `VITE_API_BASE_URL`, the application automatically enters **Demo Mode** (`auto` mode). In this state, a yellow status pill is displayed in the bottom-left corner and realistic deterministic mock calculations are used so the UI can be demonstrated offline.
- **Null Safety**: If any scientific measurement is unavailable or returns `null` from the backend, the UI renders `"Data unavailable"`. A missing score or elevation is **never** coerced to zero.
- **PDF Export**: The dossier export uses native browser printing (`window.print()`) paired with custom print stylesheet rules in `src/index.css` to format publication-quality reports on clean white paper without navigation bars.
