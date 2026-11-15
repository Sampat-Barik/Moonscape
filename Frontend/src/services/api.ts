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
 *   GET  /api/terrain?lat={latitude}&lon={longitude}&radius_m={radius}
 *   POST /api/analysis/run        body: { center_lat, center_lon, radius_meters, ... }
 *   POST /api/hazards/predict     body: { center_lat, center_lon, radius_meters, ... }
 *   POST /api/sites/compare       body: { site_ids: string[] }
 *   POST /api/score               body: { latitude, longitude, radius_m, ... }
 *   POST /api/ai/explain          body: { analysis_id }
 *   POST /api/reports/generate    body: { analysis_id, format }
 *
 * Modes (see config.ts / .env):
 *   - "live": always call the backend; failures throw and are shown in the UI.
 *             NO silent fallback to mock data occurs.
 *   - "mock": always use mockData.ts (no network).
 *   - "auto": probe /api/health once at startup; if backend unreachable, fall back to mock.
 *             Per-request, in auto mode, a failing live call falls back to mock.
 *
 * Data availability:
 *   The backend may return null for unavailable datasets — that is passed
 *   through untouched; the UI renders "Data unavailable" for nulls.
 * ============================================================================
 */

import { API_BASE_URL, API_MODE, REQUEST_TIMEOUT_MS, type ApiMode } from "@/config";
import type {
  AnalysisResponse,
  CompareResponse,
  CompareSite,
  DataCoverageResponse,
  DetectLandingSitesRequest,
  DetectLandingSitesResponse,
  ExplanationResponse,
  HazardDetection,
  HazardItem,
  HealthResponse,
  LocationRequest,
  MapConfig,
  ReportResponse,
  ScoreResponse,
  Site,
  TerrainResponse,
  VisibilitySimulationRequest,
  VisibilitySimulationResponse,
  ExternalSourcesStatusResponse,
  MoonTrekLayersResponse,
  LROCCoverageResponse,
  HorizonsQueryRequest,
  HorizonsQueryResponse,
  TerrainMeshRequest,
  TerrainMeshResponse,
} from "@/types";
import * as mock from "./mockData";

export { API_BASE_URL };

export class ApiError extends Error {
  status: number;
  detail?: string | unknown;
  constructor(message: string, status = 0, detail?: string | unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

type ResolvedMode = "live" | "mock";

let requestedMode: ApiMode = API_MODE;
let activeMode: ResolvedMode = requestedMode === "mock" ? "mock" : "live";

/** Active in-flight controllers categorized by request type to abort stale requests */
const inFlightCategoryControllers = new Map<string, AbortController>();

export function abortCategory(category: string): void {
  const existing = inFlightCategoryControllers.get(category);
  if (existing) {
    existing.abort();
    inFlightCategoryControllers.delete(category);
  }
}

export function createCategorySignal(category: string): AbortSignal {
  abortCategory(category);
  const ctrl = new AbortController();
  inFlightCategoryControllers.set(category, ctrl);
  return ctrl.signal;
}

/** Currently active data source ("live" backend or "mock"). */
export function getApiMode(): ResolvedMode {
  return activeMode;
}

/** Switch data source at runtime (used by the navbar toggle). */
export function setApiMode(m: ResolvedMode): void {
  activeMode = m;
  requestedMode = m;
}

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

/** Low-level fetch wrapper with timeout, signal handling, and status code verification */
async function fetchRaw(path: string, init?: RequestOptions): Promise<Response> {
  const controller = new AbortController();
  const timeout = init?.timeoutMs ?? REQUEST_TIMEOUT_MS;
  const timer = setTimeout(() => controller.abort(), timeout);

  if (init?.signal) {
    if (init.signal.aborted) {
      clearTimeout(timer);
      controller.abort();
    } else {
      init.signal.addEventListener("abort", () => {
        clearTimeout(timer);
        controller.abort();
      });
    }
  }

  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { ...(init?.headers ?? {}) },
    });
    if (!res.ok) {
      let detailMessage = `${res.status} ${res.statusText}`;
      let rawDetail: unknown;
      try {
        const errJson = await res.json();
        if (errJson && errJson.detail) {
          rawDetail = errJson.detail;
          detailMessage =
            typeof errJson.detail === "string"
              ? errJson.detail
              : JSON.stringify(errJson.detail);
        }
      } catch {
        // Body was not JSON
      }
      throw new ApiError(`HTTP ${res.status}: ${detailMessage} for ${path}`, res.status, rawDetail);
    }
    return res;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (e instanceof DOMException && e.name === "AbortError") {
      if (init?.signal?.aborted) {
        throw new ApiError(`Request to ${path} was aborted`, 499);
      }
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

async function fetchJson<T>(path: string, init?: RequestOptions): Promise<T> {
  const res = await fetchRaw(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const post = (body: unknown): RequestInit => ({
  method: "POST",
  body: JSON.stringify(body),
});

/**
 * Central request helper: live mode → fetch, mock mode → mock fn.
 * In "auto" mode a network failure transparently falls back to mock.
 * Client errors (HTTP 4xx like 422, 400, 404) are NEVER treated as network outages and are strictly re-thrown.
 * In "live" mode errors are STRICTLY re-thrown so real backend responses are verified.
 */
async function request<T>(
  path: string,
  mockFn: () => Promise<T> | T,
  init?: RequestOptions
): Promise<T> {
  if (activeMode === "mock") return mockFn();
  try {
    return await fetchJson<T>(path, init);
  } catch (e) {
    if (requestedMode === "auto") {
      // Do not mask client errors (HTTP 4xx, e.g. 422 Unprocessable Entity) with mock data
      if (e instanceof ApiError && e.status >= 400 && e.status < 500) {
        throw e;
      }
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
    activeMode = "live";
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

  /** GET /api/terrain?lat={latitude}&lon={longitude}&radius_m={radius_m} */
  getTerrain: async (latitude: number, longitude: number, radius_m = 50): Promise<TerrainResponse> => {
    const signal = createCategorySignal("terrain");
    const raw = await request<any>(
      `/api/terrain?lat=${encodeURIComponent(latitude)}&lon=${encodeURIComponent(longitude)}&radius_m=${encodeURIComponent(radius_m)}`,
      () => mock.getTerrain(latitude, longitude),
      { signal }
    );
    // Authentic dataset attribution from backend metadata; null if unmeasured/absent
    const dsName = raw.dataset_info?.dataset_name ?? raw.dataset_name ?? null;
    return {
      ...raw,
      latitude: raw.latitude ?? latitude,
      longitude: raw.longitude ?? longitude,
      radius_m: raw.analysis_radius_m ?? radius_m,
      elevation:
        raw.elevation ??
        (raw.elevation_summary
          ? {
              mean_m: raw.elevation_summary.mean_m ?? raw.elevation_m ?? null,
              min_m: raw.elevation_summary.min_m ?? null,
              max_m: raw.elevation_summary.max_m ?? null,
              std: raw.elevation_summary.std_dev_m ?? null,
              value: raw.elevation_m ?? null,
              source: dsName,
            }
          : raw.elevation_m !== undefined
          ? { mean_m: raw.elevation_m, value: raw.elevation_m, source: dsName }
          : null),
      slope:
        raw.slope ??
        (raw.slope_summary
          ? {
              mean_deg: raw.slope_summary.mean_deg ?? raw.slope_deg ?? null,
              min_deg: raw.slope_summary.min_deg ?? null,
              max_deg: raw.slope_summary.max_deg ?? null,
              p95_deg: raw.slope_summary.p95_deg ?? null,
              value: raw.slope_deg ?? null,
              source: dsName,
            }
          : raw.slope_deg !== undefined
          ? { mean_deg: raw.slope_deg, value: raw.slope_deg, source: dsName }
          : null),
      roughness:
        raw.roughness ??
        (raw.roughness_summary
          ? {
              rms_m: raw.roughness_summary.mean_m ?? raw.roughness_m ?? null,
              rms: raw.roughness_summary.mean_m ?? raw.roughness_m ?? null,
              max_m: raw.roughness_summary.max_m ?? null,
              value: raw.roughness_m ?? null,
              source: dsName,
            }
          : raw.roughness_m !== undefined
          ? { rms_m: raw.roughness_m, value: raw.roughness_m, source: dsName }
          : null),
      illumination:
        raw.illumination ??
        (raw.solar_illumination_pct !== undefined
          ? {
              sunlight_percent: raw.solar_illumination_pct,
              sunlit_percent: raw.solar_illumination_pct,
              value: raw.solar_illumination_pct,
              source: raw.illumination_source ?? raw.illumination?.source ?? null,
            }
          : null),
      data_sources: raw.data_sources ?? (dsName ? [dsName] : []),
    };
  },

  /** POST /api/analysis/run — body supports center_lat/center_lon and lat/lon */
  runAnalysis: async (body: LocationRequest): Promise<AnalysisResponse> => {
    const reqPayload = {
      center_lat: body.latitude,
      center_lon: body.longitude,
      radius_meters: body.radius_m,
      latitude: body.latitude,
      longitude: body.longitude,
      radius_m: body.radius_m,
      max_acceptable_slope_deg: 15.0,
      max_acceptable_roughness_m: 2.0,
    };
    const raw = await request<any>(
      "/api/analysis/run",
      () => mock.runAnalysis(body),
      post(reqPayload)
    );

    const dsName = raw.dataset_metadata?.dataset_name ?? raw.dataset_name ?? null;
    const dataSources = raw.data_sources || (dsName ? [dsName] : []);

    const elevation = raw.elevation
      ? {
          ...raw.elevation,
          mean_m: raw.elevation.mean_value ?? raw.elevation.mean_m ?? raw.elevation.mean ?? null,
          min_m: raw.elevation.min_value ?? raw.elevation.min_m ?? raw.elevation.min ?? null,
          max_m: raw.elevation.max_value ?? raw.elevation.max_m ?? raw.elevation.max ?? null,
          std: raw.elevation.std_dev ?? raw.elevation.std ?? null,
          stddev_m: raw.elevation.std_dev ?? raw.elevation.stddev_m ?? null,
          source: raw.elevation.source ?? dsName,
        }
      : null;

    const slope = raw.slope
      ? {
          ...raw.slope,
          mean_deg: raw.slope.mean_value ?? raw.slope.mean_deg ?? raw.slope.mean ?? null,
          max_deg: raw.slope.max_value ?? raw.slope.max_deg ?? raw.slope.max ?? null,
          p95_deg: raw.slope.p95_value ?? raw.slope.p95_deg ?? raw.slope.p95 ?? null,
          p95_value: raw.slope.p95_value ?? raw.slope.p95_deg ?? raw.slope.p95 ?? null,
          p95: raw.slope.p95_value ?? raw.slope.p95_deg ?? raw.slope.p95 ?? null,
          source: raw.slope.source ?? dsName,
        }
      : null;

    const roughnessMean =
      raw.roughness_mean_m ?? raw.roughness?.rms_m ?? raw.roughness?.mean_m ?? null;
    const roughnessMax = raw.roughness_max_m ?? raw.roughness?.max_m ?? null;
    const roughnessBaseline = raw.roughness_baseline_m ?? raw.roughness?.baseline_m ?? null;
    const roughnessMethod = raw.roughness_method ?? raw.roughness?.method ?? "RMS height deviation from local neighborhood mean";
    const roughness =
      roughnessMean !== null || raw.roughness
        ? {
            ...(typeof raw.roughness === "object" && raw.roughness !== null ? raw.roughness : {}),
            rms_m: roughnessMean,
            rms: roughnessMean,
            mean_m: roughnessMean,
            max_m: roughnessMax,
            baseline_m: roughnessBaseline,
            roughness_baseline_m: roughnessBaseline,
            method: roughnessMethod,
            roughness_method: roughnessMethod,
            multi_baseline: raw.roughness_multi_baseline ?? raw.roughness?.multi_baseline ?? null,
            source: raw.roughness?.source ?? dsName,
          }
        : null;

    const ilRaw = raw.illumination;
    const sunlitPct =
      ilRaw?.cumulative_illumination_pct ??
      ilRaw?.instantaneous_sunlit_fraction_pct ??
      ilRaw?.sunlight_percent ??
      null;

    const commStatus = ilRaw?.communication_link_status ?? ((ilRaw?.earth_visibility_pct ?? 0) > 0 ? "operational" : "blackout");
    const earthLosText = commStatus === "operational"
      ? "Direct LOS"
      : commStatus === "marginal"
      ? "Marginal LOS"
      : "No Direct LOS (Obscured)";

    const durationDays = ilRaw?.sunlight_duration_remaining_hours != null
      ? Number((ilRaw.sunlight_duration_remaining_hours / 24).toFixed(1))
      : (ilRaw?.sunlight_continuous_hours_max != null ? Number((ilRaw.sunlight_continuous_hours_max / 24).toFixed(1)) : null);

    const nextSunsetText = ilRaw?.next_sunset_iso
      ? `In ${(ilRaw.sunlight_duration_remaining_hours ? (ilRaw.sunlight_duration_remaining_hours / 24).toFixed(1) : "—")}d (${new Date(ilRaw.next_sunset_iso).toLocaleDateString("en-US", { month: "short", day: "numeric" })})`
      : (ilRaw?.is_permanently_shadowed_region
          ? "Polar Night (Permanent)"
          : (ilRaw?.instantaneous_sunlit_fraction_pct > 0
              ? "Continuous (>35d)"
              : (ilRaw ? "In Shadow" : null)));

    const illumination = ilRaw
      ? {
          ...ilRaw,
          sunlight_percent: sunlitPct,
          sunlit_percent: sunlitPct,
          illumination_percent: sunlitPct,
          cumulative_pct: ilRaw.cumulative_illumination_pct ?? null,
          instantaneous_pct: ilRaw.instantaneous_sunlit_fraction_pct ?? null,
          sunlight_duration_days: durationDays,
          duration_days: durationDays,
          duration: durationDays,
          sunlight_duration_hours: ilRaw.sunlight_duration_remaining_hours ?? null,
          earth_visibility: earthLosText,
          earth_visibility_state: commStatus,
          earth_comm_los: earthLosText,
          earth_visibility_pct: ilRaw.earth_visibility_pct ?? null,
          next_sunset: nextSunsetText,
          next_sunset_iso: ilRaw.next_sunset_iso ?? null,
          sunset_time: ilRaw.next_sunset_iso ?? null,
          psr: ilRaw.is_permanently_shadowed_region ?? false,
          psr_nearby: ilRaw.is_permanently_shadowed_region ?? false,
          has_psr: ilRaw.is_permanently_shadowed_region ?? false,
          source: ilRaw.source_attribution ?? ilRaw.source ?? null,
        }
      : null;

    // Map embedded suitability score if available
    const scoreVal =
      raw.suitability?.overall_suitability_score ??
      raw.suitability?.score ??
      raw.score ??
      null;
    const scoreCategory =
      raw.suitability?.suitability_category ??
      raw.suitability?.label ??
      raw.preliminary_feasibility ??
      null;

    let scoreGrade = raw.suitability?.grade ?? null;
    if (!scoreGrade && scoreCategory) {
      if (scoreCategory.includes("Higher") || scoreCategory === "favorable") scoreGrade = "A";
      else if (scoreCategory.includes("Moderate") || scoreCategory === "marginal") scoreGrade = "B";
      else if (scoreCategory.includes("Lower") || scoreCategory === "unfavorable") scoreGrade = "C";
      else if (scoreCategory.includes("Disqualified")) scoreGrade = "F";
      else scoreGrade = "N/A";
    }

    const breakdown: Record<string, number | null> = {};
    if (Array.isArray(raw.suitability?.subscores)) {
      for (const sub of raw.suitability.subscores) {
        if (sub?.criterion) {
          breakdown[sub.criterion] = sub.normalized_subscore ?? null;
        }
      }
    } else if (raw.suitability?.breakdown && typeof raw.suitability.breakdown === "object") {
      Object.assign(breakdown, raw.suitability.breakdown);
    }

    return {
      ...raw,
      latitude: raw.latitude ?? raw.center_lat ?? body.latitude,
      longitude: raw.longitude ?? raw.center_lon ?? body.longitude,
      radius_m: raw.radius_m ?? raw.radius_meters ?? body.radius_m,
      elevation,
      slope,
      roughness,
      illumination,
      earth_visibility: earthLosText,
      earth_visibility_state: commStatus,
      earth_visible: commStatus === "operational" || (ilRaw?.earth_visibility_pct ?? 0) > 0,
      has_earth_los: commStatus === "operational" || (ilRaw?.earth_visibility_pct ?? 0) > 0,
      data_sources: dataSources,
      score: scoreVal,
      suitability_score: scoreVal,
      grade: scoreGrade,
      label: scoreCategory,
      score_label: scoreCategory,
      breakdown: Object.keys(breakdown).length > 0 ? breakdown : undefined,
      score_breakdown: Object.keys(breakdown).length > 0 ? breakdown : undefined,
      timestamp: raw.timestamp ?? new Date().toISOString(),
    };
  },

  /** POST /api/hazards/predict — body supports center_lat/center_lon and lat/lon */
  predictHazards: async (body: LocationRequest): Promise<HazardDetection> => {
    const reqPayload = {
      center_lat: body.latitude,
      center_lon: body.longitude,
      radius_meters: body.radius_m,
      latitude: body.latitude,
      longitude: body.longitude,
      radius_m: body.radius_m,
    };
    const raw = await request<any>(
      "/api/hazards/predict",
      () => mock.predictHazards(body),
      post(reqPayload)
    );

    // Distinguish optical scan completion from unavailable/unexecuted scan
    const opticalRan = raw.optical_status === "success" || (raw.crater_count !== null && raw.crater_count !== undefined);

    const rawHazards: any[] = Array.isArray(raw.hazards) ? raw.hazards : [];
    const rawDetections: any[] = Array.isArray(raw.detections) ? raw.detections : [];

    let craters: HazardItem[] | null = null;
    let rocks: HazardItem[] | null = null;

    if (opticalRan) {
      if (Array.isArray(raw.craters)) {
        craters = raw.craters.map((h: any, i: number) => ({
          id: h.id ?? `CR-${i + 1}`,
          type: "crater",
          latitude: h.latitude,
          longitude: h.longitude,
          diameter_m: h.estimated_size_m ?? (h.radius_m ? h.radius_m * 2 : null),
          confidence: h.confidence_score ?? h.confidence ?? null,
          severity: h.severity ?? "medium",
        }));
      } else {
        craters = rawDetections
          .filter((d: any) => (d.label || "").toLowerCase() === "crater")
          .map((d: any, i: number) => ({
            id: `CR-${i + 1}`,
            type: "crater",
            latitude: body.latitude,
            longitude: body.longitude,
            diameter_m: d.estimated_size_m ?? null,
            confidence: d.confidence ?? null,
            severity: d.severity ?? "medium",
          }));
      }

      if (Array.isArray(raw.rocks)) {
        rocks = raw.rocks.map((h: any, i: number) => ({
          id: h.id ?? `RK-${i + 1}`,
          type: "rock",
          latitude: h.latitude,
          longitude: h.longitude,
          size_m: h.estimated_size_m ?? h.diameter_m ?? null,
          confidence: h.confidence_score ?? h.confidence ?? null,
          severity: h.severity ?? "medium",
        }));
      } else {
        rocks = rawDetections
          .filter((d: any) => {
            const l = (d.label || "").toLowerCase();
            return l === "boulder" || l === "rock";
          })
          .map((d: any, i: number) => ({
            id: `RK-${i + 1}`,
            type: "rock",
            latitude: body.latitude,
            longitude: body.longitude,
            size_m: d.estimated_size_m ?? null,
            confidence: d.confidence ?? null,
            severity: d.severity ?? "medium",
          }));
      }
    }

    // Topographic hazards from DEM
    const topographicHazards: HazardItem[] = rawHazards
      .filter((h: any) => {
        const t = (h.hazard_type || "").toLowerCase();
        return t === "escarpment" || t === "morphological_depression" || t === "surface_roughness_anomaly";
      })
      .map((h: any, i: number) => ({
        id: h.id ?? `TOPO-${i + 1}`,
        type: h.hazard_type,
        latitude: h.latitude,
        longitude: h.longitude,
        diameter_m: h.estimated_size_m ?? null,
        size_m: h.estimated_size_m ?? null,
        confidence: h.confidence_score ?? 0.90,
        severity: h.severity ?? "medium",
        source: h.source,
      }));

    const limitations: string[] = Array.isArray(raw.limitations)
      ? raw.limitations
      : typeof raw.limitations === "string" && raw.limitations.length > 0
      ? [raw.limitations]
      : [];

    const warnings: string[] = Array.isArray(raw.warnings) ? raw.warnings : [];

    return {
      ...raw,
      latitude: raw.center_lat ?? raw.latitude ?? body.latitude,
      longitude: raw.center_lon ?? raw.longitude ?? body.longitude,
      radius_m: raw.radius_meters ?? raw.radius_m ?? body.radius_m,
      status: raw.status ?? "success",
      optical_status: raw.optical_status ?? (opticalRan ? "success" : "not_available"),
      source_product_id: raw.source_product_id ?? null,
      source_resolution_m: raw.source_resolution_m ?? null,
      coverage_zone: raw.coverage_zone ?? "core",
      craters,
      rocks,
      crater_count: raw.crater_count ?? (craters ? craters.length : null),
      rock_count: raw.rock_count ?? (rocks ? rocks.length : null),
      topographic_hazards: topographicHazards,
      overlay_image: raw.overlay_image ?? null,
      limitations,
      warnings,
      model: raw.model_name ?? raw.model ?? null,
      summary: raw.summary ?? {
        overall_hazard_level: raw.overall_hazard_level ?? "low",
        total_hazards: raw.total_hazards_detected ?? ((craters ? craters.length : 0) + (rocks ? rocks.length : 0) + topographicHazards.length),
        steep_slope_cells: raw.steep_slope_cells ?? 0,
      },
    };
  },

  /** POST /api/sites/compare — body: { site_ids: [...] } */
  compareSites: async (siteIds: string[]): Promise<CompareResponse> => {
    const raw = await request<any>(
      "/api/sites/compare",
      () => mock.compareSites(siteIds),
      post({ site_ids: siteIds })
    );

    const items = raw.sites ?? raw.compared_sites ?? [];
    const adaptedSites: CompareSite[] = items.map((s: any) => ({
      ...s,
      site_id: s.site_id,
      name: s.name,
      latitude: s.latitude,
      longitude: s.longitude,
      score: s.score ?? s.suitability_score ?? null,
      suitability_score: s.suitability_score ?? s.score ?? null,
      elevation_m: s.elevation_m ?? null,
      elevation:
        typeof s.elevation === "object" && s.elevation !== null
          ? s.elevation
          : {
              mean_m: s.elevation_m ?? null,
              mean: s.elevation_m ?? null,
              value: s.elevation_m ?? null,
            },
      mean_slope_deg: s.mean_slope_deg ?? null,
      slope:
        typeof s.slope === "object" && s.slope !== null
          ? s.slope
          : {
              mean_deg: s.mean_slope_deg ?? null,
              mean: s.mean_slope_deg ?? null,
              value: s.mean_slope_deg ?? null,
              max_deg: s.max_slope_deg ?? null,
            },
      roughness:
        typeof s.roughness === "object" && s.roughness !== null
          ? s.roughness
          : {
              rms_m: s.roughness_m ?? null,
              rms: s.roughness_m ?? null,
            },
      illumination_pct: s.illumination_pct ?? null,
      illumination:
        typeof s.illumination === "object" && s.illumination !== null
          ? s.illumination
          : {
              sunlight_percent: s.illumination_pct ?? null,
              sunlit_percent: s.illumination_pct ?? null,
              illumination_percent: s.illumination_pct ?? null,
              value: s.illumination_pct ?? null,
            },
    }));

    return {
      ...raw,
      sites: adaptedSites,
      results: adaptedSites,
    };
  },

  /** POST /api/score — body: LocationRequest */
  scoreSite: async (body: LocationRequest): Promise<ScoreResponse> => {
    const reqPayload = {
      latitude: body.latitude,
      longitude: body.longitude,
      radius_m: body.radius_m,
      center_lat: body.latitude,
      center_lon: body.longitude,
    };
    const raw = await request<any>(
      "/api/score",
      () => mock.scoreSite(body),
      post(reqPayload)
    );

    const breakdown: Record<string, number | null> = {};
    if (Array.isArray(raw.subscores)) {
      for (const sub of raw.subscores) {
        if (sub && sub.criterion) {
          breakdown[sub.criterion] = sub.normalized_subscore ?? null;
        }
      }
    } else if (raw.breakdown && typeof raw.breakdown === "object") {
      Object.assign(breakdown, raw.breakdown);
    }

    let grade = raw.grade ?? null;
    if (!grade && raw.suitability_category) {
      if (raw.suitability_category.includes("Higher")) grade = "A";
      else if (raw.suitability_category.includes("Moderate")) grade = "B";
      else if (raw.suitability_category.includes("Lower")) grade = "C";
      else if (raw.suitability_category.includes("Disqualified")) grade = "F";
      else grade = "N/A";
    }

    return {
      ...raw,
      score: raw.score ?? raw.overall_suitability_score ?? null,
      grade,
      label: raw.label ?? raw.suitability_category ?? null,
      breakdown,
      disclaimer: raw.disclaimer ?? null,
    };
  },

  /** POST /api/ai/explain — body: { analysis_id } */
  explainAnalysis: async (analysisId: string): Promise<ExplanationResponse> => {
    const raw = await request<any>(
      "/api/ai/explain",
      () => mock.explainAnalysis(analysisId),
      post({ analysis_id: analysisId })
    );

    return {
      ...raw,
      analysis_id: raw.analysis_id ?? analysisId,
      explanation: raw.explanation ?? raw.summary ?? raw.executive_summary,
      summary: raw.summary ?? raw.explanation ?? raw.executive_summary,
      positive_factors: raw.positive_factors ?? [],
      risk_factors: raw.risk_factors ?? [],
      limitations: raw.limitations ?? [],
      model: raw.model ?? raw.model_origin ?? "Scientific Explainer Engine",
      generated_at: raw.generated_at ?? new Date().toISOString(),
    };
  },

  /** POST /api/reports/generate — body: { analysis_id, format } */
  generateReport: async (analysisId: string, format = "json"): Promise<ReportResponse> => {
    if (activeMode === "mock") return mock.generateReport(analysisId, format);
    try {
      const res = await fetchRaw("/api/reports/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ analysis_id: analysisId, format }),
      });
      const contentType = res.headers.get("content-type") || "";
      if (contentType.includes("application/pdf")) {
        const blob = await res.blob();
        return {
          report_id: `PDF-${analysisId}`,
          analysis_id: analysisId,
          format: "pdf",
          content: { message: "Binary PDF generated successfully", size_bytes: blob.size },
          pdf_blob: blob,
          generated_at: new Date().toISOString(),
        } as ReportResponse;
      }
      return (await res.json()) as ReportResponse;
    } catch (e) {
      if (requestedMode === "auto") {
        activeMode = "mock";
        return mock.generateReport(analysisId, format);
      }
      throw e;
    }
  },

  /** Direct binary PDF download from POST /api/reports/generate with format: "pdf" */
  downloadPdfReport: async (analysisId: string): Promise<Blob> => {
    if (activeMode === "mock") {
      return new Blob(["%PDF-1.4 Mock Lunar Landing Site Evaluation Report"], {
        type: "application/pdf",
      });
    }
    const res = await fetchRaw("/api/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analysis_id: analysisId, format: "pdf" }),
    });
    return await res.blob();
  },

  /** GET /api/coverage?lat={latitude}&lon={longitude} — checks NASA dataset spatial coverage */
  checkCoverage: async (latitude: number, longitude: number): Promise<DataCoverageResponse> => {
    const signal = createCategorySignal("coverage");
    return await request<DataCoverageResponse>(
      `/api/coverage?lat=${encodeURIComponent(latitude)}&lon=${encodeURIComponent(longitude)}`,
      () => mock.checkCoverage(latitude, longitude),
      { signal }
    );
  },

  /** POST /api/sites/detect — automated contiguous safe landing zone detection from DEM */
  detectLandingSites: async (req: DetectLandingSitesRequest): Promise<DetectLandingSitesResponse> => {
    const payload = {
      center_lat: req.center_lat,
      center_lon: req.center_lon,
      search_radius_meters: req.search_radius_meters ?? 1500.0,
      max_slope_deg: req.max_slope_deg ?? 8.0,
      max_roughness_m: req.max_roughness_m ?? 0.35,
      min_landing_diameter_meters: req.min_landing_diameter_meters ?? 50.0,
      mission_profile: req.mission_profile ?? "artemis_hls",
    };
    return await request<DetectLandingSitesResponse>(
      "/api/sites/detect",
      () => mock.detectLandingSites(payload),
      post(payload)
    );
  },

  /** POST /api/simulation/visibility — time-series solar & Earth visibility propagation */
  simulateVisibility: async (req: VisibilitySimulationRequest): Promise<VisibilitySimulationResponse> => {
    const signal = createCategorySignal("simulation");
    const payload = {
      lat: req.lat,
      lon: req.lon,
      start_epoch_iso: req.start_epoch_iso || null,
      duration_days: req.duration_days ?? 14.0,
      step_hours: req.step_hours ?? 2.0,
      ephemeris_source: req.ephemeris_source ?? "auto",
    };
    return await request<VisibilitySimulationResponse>(
      "/api/simulation/visibility",
      () => mock.simulateVisibility(payload),
      { ...post(payload), signal }
    );
  },

  /** GET /api/external/sources — operational status of JPL Horizons, Moon Trek, LROC */
  getExternalSourcesStatus: async (): Promise<ExternalSourcesStatusResponse> => {
    return await request<ExternalSourcesStatusResponse>(
      "/api/external/sources",
      () => ({
        horizons: {
          source_id: "nasa_jpl_horizons",
          name: "NASA JPL Horizons On-Line Ephemeris System",
          status: "operational",
          endpoint_url: "https://ssd.jpl.nasa.gov/api/horizons.api",
          description: "Numerical ephemeris DE441",
          documentation_url: "https://ssd.jpl.nasa.gov/horizons/manual.html",
          is_live_accessible: true,
          cached_entries_count: 0,
          notes: "Operational",
        },
        moon_trek: {
          source_id: "nasa_moon_trek",
          name: "NASA Solar System Treks (Moon Trek WMTS)",
          status: "operational",
          endpoint_url: "https://trek.nasa.gov/moon/TrekServices/ws/index",
          description: "Moon Trek WMTS",
          documentation_url: "https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=moon",
          is_live_accessible: true,
          cached_entries_count: 0,
          notes: "Operational",
        },
        lroc_quickmap: {
          source_id: "nasa_lroc_quickmap",
          name: "NASA LROC QuickMap & Targeted Stereo DTM Archive",
          status: "operational",
          endpoint_url: "https://quickmap.lroc.im-ldi.com",
          description: "LROC QuickMap and NAC DTMs",
          documentation_url: "https://www.lroc.asu.edu",
          is_live_accessible: true,
          cached_entries_count: 0,
          notes: "Operational",
        },
        timestamp: new Date().toISOString(),
      }),
      { timeoutMs: 5000 }
    );
  },

  /** GET /api/external/moon-trek/layers — catalog of verified official Moon Trek WMTS layers */
  getMoonTrekLayers: async (): Promise<MoonTrekLayersResponse> => {
    return await request<MoonTrekLayersResponse>(
      "/api/external/moon-trek/layers",
      () => ({
        layers_count: 3,
        layers: [
          {
            id: "trek_wac_global_mosaic",
            name: "NASA Moon Trek LROC WAC Global Morphologic Mosaic",
            description: "Global controlled mosaic at 100 meters/pixel.",
            wmts_endpoint: "https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02",
            capabilities_url: "https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/WMTSCapabilities.xml",
            tile_url_template: "https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
            tile_format: "image/jpeg",
            tile_matrix_set: "default028mm",
            projection: "EPSG::104903",
            projection_type: "equirectangular",
            resolution_m: 100.0,
            min_zoom: 0,
            max_zoom: 7,
            bounds: { min_lat: -90, max_lat: 90, min_lon: -180, max_lon: 180 },
            attribution: "NASA / GSFC / ASU / JPL Moon Trek",
          },
        ],
        supported_projections: ["IAU2000::30120", "EPSG::104903"],
        documentation_url: "https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=moon",
      }),
      { timeoutMs: 5000 }
    );
  },

  /** GET /api/external/lroc/coverage?lat={latitude}&lon={longitude} */
  getLROCCoverage: async (latitude: number, longitude: number): Promise<LROCCoverageResponse> => {
    return await request<LROCCoverageResponse>(
      `/api/external/lroc/coverage?lat=${encodeURIComponent(latitude)}&lon=${encodeURIComponent(longitude)}`,
      () => ({
        latitude,
        longitude,
        is_covered: latitude <= -85.0,
        covering_dtms_count: latitude <= -85.0 ? 1 : 0,
        covering_dtms: [],
        nearest_dtm: null,
        distance_to_nearest_dtm_km: 0.0,
        best_resolution_m: latitude <= -85.0 ? 1.5 : null,
        quickmap_url: `https://quickmap.lroc.im-ldi.com/?center=${encodeURIComponent(longitude)},${encodeURIComponent(latitude)}&zoom=6&proj=southpole`,
        lroc_archive_url: "https://data.lroc.im-ldi.com/lroc/view_rdr/SHAPEFILE_NAC_DTMS",
        optical_hazard_validation_supported: latitude <= -85.0,
        status_note: "LROC QuickMap deep link ready",
      }),
      { timeoutMs: 6000 }
    );
  },

  /** POST /api/ephemeris/query — query NASA JPL Horizons on-line ephemerides */
  queryHorizons: async (req: HorizonsQueryRequest): Promise<HorizonsQueryResponse> => {
    return await request<HorizonsQueryResponse>(
      "/api/ephemeris/query",
      () => ({
        success: true,
        target: req.target ?? "Sun",
        observer: {
          latitude_deg: req.latitude,
          longitude_deg: req.longitude,
          altitude_km: req.altitude_km ?? 0.0,
        },
        temporal_window: {
          start_iso: req.start_epoch_iso,
          stop_iso: req.stop_epoch_iso ?? "",
          step: `${req.step_hours ?? 2}h`,
        },
        points_count: 0,
        points: [],
        source_attribution: "NASA JPL Horizons On-Line Ephemeris System (DE441)",
        is_cached: false,
        query_duration_ms: 10.0,
      }),
      post(req)
    );
  },

  /** POST /api/terrain/mesh — extract downsampled DEM elevation and slope grid */
  getTerrainMesh: async (req: TerrainMeshRequest): Promise<TerrainMeshResponse> => {
    return await request<TerrainMeshResponse>(
      "/api/terrain/mesh",
      () => {
        const sz = req.grid_size || 64;
        const grid: number[][] = [];
        const slopeGrid: number[][] = [];
        for (let r = 0; r < sz; r++) {
          const row: number[] = [];
          const slopeRow: number[] = [];
          for (let c = 0; c < sz; c++) {
            const dr = (r - sz / 2) / sz;
            const dc = (c - sz / 2) / sz;
            const dist = Math.sqrt(dr * dr + dc * dc);
            const rim = Math.exp(-Math.pow(dist - 0.28, 2) / 0.008) * 45;
            const floor = -Math.exp(-Math.pow(dist, 2) / 0.05) * 80;
            const elev = -1750.0 + rim + floor;
            row.push(Math.round(elev * 10) / 10);
            slopeRow.push(Math.round(Math.min(35, Math.abs(rim * 0.4 + floor * 0.2)) * 10) / 10);
          }
          grid.push(row);
          slopeGrid.push(slopeRow);
        }
        return {
          status: "ready",
          latitude: req.latitude,
          longitude: req.longitude,
          radius_m: req.radius_m || 500.0,
          grid_size: sz,
          resolution_m: Math.round(((req.radius_m || 500.0) * 2) / sz),
          center_x_polar_m: 0.0,
          center_y_polar_m: 0.0,
          min_elevation_m: -1830.0,
          max_elevation_m: -1705.0,
          mean_elevation_m: -1755.0,
          relief_m: 125.0,
          elevation_grid: grid,
          slope_grid: slopeGrid,
          dataset_name: "NASA LOLA 80m DEM (Simulated Mock)",
          product_id: "LOLA_SHDR_80M",
          crs: "ESRI:104903",
          disclaimer: "Mock terrain relief.",
        };
      },
      post(req)
    );
  },
};
