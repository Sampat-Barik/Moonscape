# Frontend Developer Guide — Moonscape API Integration

Welcome! This folder contains everything you need to connect your frontend application (e.g. React, Vue, Next.js, or Vite) to the Moonscape Backend.

---

## 🛰️ Backend Connection Details

- **Base URL:** `http://localhost:8000`
- **Interactive Swagger Docs:** `http://localhost:8000/docs`
- **OpenAPI Schema (JSON):** `http://localhost:8000/openapi.json`
- **CORS Allowed Origins:**
  - `http://localhost:3000`
  - `http://localhost:5173`
  - `http://127.0.0.1:3000`
  - `http://127.0.0.1:5173`

---

## 📦 TypeScript Types

All request and response types are pre-compiled and exported in:
`Frontend/types.ts`

Import them directly into your components:
```typescript
import type { CandidateSite, ScoreResponse, TerrainResponse } from "./types";
```

---

## ⚡ Quick Example (Fetch)

```typescript
// 1. Fetch Candidate Sites
async function getSites(): Promise<CandidateSite[]> {
  const response = await fetch("http://localhost:8000/api/sites");
  return response.json();
}

// 2. Query Terrain Elevation & Slope at South Pole
async function getTerrain(lat: number, lon: number): Promise<TerrainResponse> {
  const response = await fetch(`http://localhost:8000/api/terrain?lat=${lat}&lon=${lon}`);
  return response.json();
}

// 3. Compute Transparent Suitability Score
async function getScore(siteId: string): Promise<ScoreResponse> {
  const response = await fetch("http://localhost:8000/api/score", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ site_id: siteId }),
  });
  return response.json();
}
```

Refer to [API_CONTRACT.md](file:///D:/MoonScape/Frontend/API_CONTRACT.md) for full endpoint specifications.
