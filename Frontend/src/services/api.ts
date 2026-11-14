/**
 * ============================================================================
 * api.ts — the ONE AND ONLY place where the frontend talks to the backend.
 * ============================================================================
 *
 * Every API call in the app goes through the `api` object below. The agreed
 * contract (base URL configurable via VITE_API_BASE_URL, default
 * http://localhost:8000 — backend on port 8000, frontend dev server on 5173):
 *
 *   GET  /api/health
 *   GET  /api/sites
 *   GET  /api/sites/{site_id}
 *   GET  /api/map/config
 *   GET  /api/terrain?lat={latitude}&lon={longitude}
 *   POST /api/analysis/run        body: { latitude, longitude, radius_m }
 *   POST /api/hazards/predict     body: { latitude, longitude, radius_m }
 *   POST /api/sites/compare       body: { site_ids: string[] }
 *   POST /api/score               body: { latitude, longitude, radius_m }
 *   POST /api/ai/explain          body: { analysis_id }
 *   POST /api/reports/generate    body: { analysis_id, format }
 *
 * Modes (see config.ts / .env):
 *   - "live": always call the backend; failures throw and are shown in the UI.
 *   - "mock": always use mockData.ts (no network).
 *   - "auto" (default): probe /api/health once at startup; if the backend is
 *     unreachable, fall back to mock data. Per-request, "auto" also falls back
 *     to mock if a live call fails, and the UI always shows which mode is active.
 *
 * The backend may return null for unavailable datasets — that is passed
 * through untouched; the UI renders "Data unavailable" for nulls.
 * ============================================================================
 */

import { API_BASE_URL, API_MODE, REQUEST_TIMEOUT_MS, type ApiMode } from "@/config";
import type {
  AnalysisResponse,
  CompareResponse,
  ExplanationResponse,
  HazardDetection,
  HealthResponse,
  LocationRequest,
  MapConfig,
  ReportResponse,
  ScoreResponse,
  Site,
  TerrainResponse,
} from "@/types";
import * as mock from "./mockData";

export { API_BASE_URL };

export class ApiError extends Error {
  status: number;
  constructor(message: string, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type ResolvedMode = "live" | "mock";

let requestedMode: ApiMode = API_MODE;
let activeMode: ResolvedMode = requestedMode === "mock" ? "mock" : "live";

/** Currently active data source ("live" backend or "mock"). */
export function getApiMode(): ResolvedMode {
  return activeMode;
}

/** Switch data source at runtime (used by the navbar toggle). */
export function setApiMode(m: ResolvedMode): void {
  activeMode = m;
  requestedMode = m;
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
    if (!res.ok) {
      throw new ApiError(`HTTP ${res.status} ${res.statusText} for ${path}`, res.status);
    }
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new ApiError(`Request to ${path} timed out after ${REQUEST_TIMEOUT_MS} ms`, 0);
    }
    throw new ApiError(
      e instanceof Error ? e.message : `Network error while calling ${path}`,
      0
    );
  } finally {
    clearTimeout(timer);
  }
}

const post = (body: unknown): RequestInit => ({
  method: "POST",
  body: JSON.stringify(body),
});

/**
 * Central request helper: live mode → fetch, mock mode → mock fn.
 * In "auto" mode a failing live call transparently falls back to mock.
 */
async function request<T>(
  path: string,
  mockFn: () => Promise<T> | T,
  init?: RequestInit
): Promise<T> {
  if (activeMode === "mock") return mockFn();
  try {
    return await fetchJson<T>(path, init);
  } catch (e) {
    if (requestedMode === "auto") {
      activeMode = "mock";
      return mockFn();
    }
    throw e;
  }
}

/**
 * Probe the backend once (used at startup in "auto" mode).
 * Never throws — reports which mode ended up active.
 */
export async function probeBackend(): Promise<{
  mode: ResolvedMode;
  health: HealthResponse | null;
  error?: string;
}> {
  if (requestedMode === "mock") {
    activeMode = "mock";
    return { mode: "mock", health: await mock.health() };
  }
  try {
    const health = await fetchJson<HealthResponse>("/api/health");
    activeMode = "live";
    return { mode: "live", health };
  } catch (e) {
    if (requestedMode === "auto") {
      activeMode = "mock";
      return {
        mode: "mock",
        health: null,
        error: e instanceof Error ? e.message : String(e),
      };
    }
    return {
      mode: "live",
      health: null,
      error: e instanceof Error ? e.message : String(e),
    };
  }
}

/** All backend calls. Every page/component must use these — never fetch() directly. */
export const api = {
  /** GET /api/health */
  health: () => request<HealthResponse>("/api/health", mock.health),

  /** GET /api/sites — normalised to always return an array. */
  getSites: async (): Promise<Site[]> => {
    const data = await request<unknown>("/api/sites", mock.getSites);
    if (Array.isArray(data)) return data as Site[];
    const arr = (data as { sites?: unknown } | null)?.sites;
    return Array.isArray(arr) ? (arr as Site[]) : [];
  },

  /** GET /api/sites/{site_id} */
  getSite: (siteId: string) =>
    request<Site>(
      `/api/sites/${encodeURIComponent(siteId)}`,
      () => mock.getSite(siteId)
    ),

  /** GET /api/map/config */
  getMapConfig: () => request<MapConfig>("/api/map/config", mock.getMapConfig),

  /** GET /api/terrain?lat={latitude}&lon={longitude} */
  getTerrain: (latitude: number, longitude: number) =>
    request<TerrainResponse>(
      `/api/terrain?lat=${encodeURIComponent(latitude)}&lon=${encodeURIComponent(longitude)}`,
      () => mock.getTerrain(latitude, longitude)
    ),

  /** POST /api/analysis/run — body: { latitude, longitude, radius_m } */
  runAnalysis: (body: LocationRequest) =>
    request<AnalysisResponse>("/api/analysis/run", () => mock.runAnalysis(body), post(body)),

  /** POST /api/hazards/predict — body: { latitude, longitude, radius_m } */
  predictHazards: (body: LocationRequest) =>
    request<HazardDetection>(
      "/api/hazards/predict",
      () => mock.predictHazards(body),
      post(body)
    ),

  /** POST /api/sites/compare — body: { site_ids: [...] } */
  compareSites: (siteIds: string[]) =>
    request<CompareResponse>(
      "/api/sites/compare",
      () => mock.compareSites(siteIds),
      post({ site_ids: siteIds })
    ),

  /** POST /api/score — body: { latitude, longitude, radius_m } */
  scoreSite: (body: LocationRequest) =>
    request<ScoreResponse>("/api/score", () => mock.scoreSite(body), post(body)),

  /** POST /api/ai/explain — body: { analysis_id } */
  explainAnalysis: (analysisId: string) =>
    request<ExplanationResponse>(
      "/api/ai/explain",
      () => mock.explainAnalysis(analysisId),
      post({ analysis_id: analysisId })
    ),

  /** POST /api/reports/generate — body: { analysis_id, format } */
  generateReport: (analysisId: string, format = "json") =>
    request<ReportResponse>(
      "/api/reports/generate",
      () => mock.generateReport(analysisId, format),
      post({ analysis_id: analysisId, format })
    ),
};
