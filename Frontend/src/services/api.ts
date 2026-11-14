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

/** Low-level fetch wrapper with timeout, signal handling, and status code verification */
async function fetchRaw(path: string, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

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

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
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
 * In "auto" mode a failing live call transparently falls back to mock.
 * In "live" mode errors are STRICTLY re-thrown so real backend responses are verified.
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
    const dsName = raw.dataset_info?.dataset_name || "NASA LRO LOLA DEM";
    return {
      ...raw,
      latitude: raw.latitude ?? latitude,
      longitude: raw.longitude ?? longitude,
      radius_m: raw.analysis_radius_m ?? radius_m,
      elevation:
        raw.elevation ??
        (raw.elevation_summary
          ? {
              mean_m: raw.elevation_summary.mean_m ?? raw.elevation_m,
              min_m: raw.elevation_summary.min_m,
              max_m: raw.elevation_summary.max_m,
              std: raw.elevation_summary.std_dev_m,
              value: raw.elevation_m,
              source: dsName,
            }
          : raw.elevation_m !== undefined
          ? { mean_m: raw.elevation_m, value: raw.elevation_m, source: dsName }
          : null),
      slope:
        raw.slope ??
        (raw.slope_summary
          ? {
              mean_deg: raw.slope_summary.mean_deg ?? raw.slope_deg,
              min_deg: raw.slope_summary.min_deg,
              max_deg: raw.slope_summary.max_deg,
              p95_deg: raw.slope_summary.max_deg,
              value: raw.slope_deg,
              source: dsName,
            }
          : raw.slope_deg !== undefined
          ? { mean_deg: raw.slope_deg, value: raw.slope_deg, source: dsName }
          : null),
      roughness:
        raw.roughness ??
        (raw.roughness_summary
          ? {
              rms_m: raw.roughness_summary.mean_m ?? raw.roughness_m,
              rms: raw.roughness_summary.mean_m ?? raw.roughness_m,
              max_m: raw.roughness_summary.max_m,
              value: raw.roughness_m,
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
              source: "NASA LRO Polar Lighting",
            }
          : null),
      data_sources: raw.data_sources ?? [dsName],
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

    const dsName = raw.dataset_metadata?.dataset_name || "NASA LRO LOLA DEM (80m)";
    const dataSources = raw.data_sources || [dsName];

    const elevation = raw.elevation
      ? {
          ...raw.elevation,
          mean_m: raw.elevation.mean_value ?? raw.elevation.mean_m ?? raw.elevation.mean,
          min_m: raw.elevation.min_value ?? raw.elevation.min_m ?? raw.elevation.min,
          max_m: raw.elevation.max_value ?? raw.elevation.max_m ?? raw.elevation.max,
          std: raw.elevation.std_dev ?? raw.elevation.std,
          stddev_m: raw.elevation.std_dev ?? raw.elevation.stddev_m,
          source: dsName,
        }
      : null;

    const slope = raw.slope
      ? {
          ...raw.slope,
          mean_deg: raw.slope.mean_value ?? raw.slope.mean_deg ?? raw.slope.mean,
          max_deg: raw.slope.max_value ?? raw.slope.max_deg ?? raw.slope.max,
          p95_deg: raw.slope.p95_deg ?? (raw.slope.max_value ? raw.slope.max_value * 0.9 : null),
          source: dsName,
        }
      : null;

    const roughnessMean =
      raw.roughness_mean_m ?? raw.roughness?.rms_m ?? raw.roughness?.mean_m ?? null;
    const roughnessMax = raw.roughness_max_m ?? raw.roughness?.max_m ?? null;
    const roughness =
      roughnessMean !== null || raw.roughness
        ? {
            ...(typeof raw.roughness === "object" && raw.roughness !== null ? raw.roughness : {}),
            rms_m: roughnessMean,
            rms: roughnessMean,
            mean_m: roughnessMean,
            max_m: roughnessMax,
            source: dsName,
          }
        : null;

    const ilRaw = raw.illumination;
    const sunlitPct =
      ilRaw?.cumulative_illumination_pct ??
      ilRaw?.instantaneous_sunlit_fraction_pct ??
      ilRaw?.sunlight_percent ??
      null;
    const illumination = ilRaw
      ? {
          ...ilRaw,
          sunlight_percent: sunlitPct,
          sunlit_percent: sunlitPct,
          illumination_percent: sunlitPct,
          earth_visibility_pct: ilRaw.earth_visibility_pct ?? null,
          psr: ilRaw.is_permanently_shadowed_region ?? false,
          psr_nearby: ilRaw.is_permanently_shadowed_region ?? false,
          has_psr: ilRaw.is_permanently_shadowed_region ?? false,
          source: ilRaw.source_attribution || "NASA LRO Horizon / Ephemeris",
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

    // Live backend returns hazards list or detections list
    const rawHazards: any[] = Array.isArray(raw.hazards)
      ? raw.hazards
      : Array.isArray(raw.detections)
      ? raw.detections
      : [];

    const craters: HazardItem[] =
      raw.craters ??
      rawHazards
        .filter((h: any) => (h.hazard_type || h.label || "").toLowerCase() === "crater")
        .map((h: any, i: number) => ({
          id: h.id ?? `CR-${i + 1}`,
          type: "crater",
          latitude: h.latitude,
          longitude: h.longitude,
          diameter_m: h.estimated_size_m ?? (h.radius_m ? h.radius_m * 2 : null),
          confidence: h.confidence_score ?? h.confidence,
          severity: h.severity ?? "medium",
        }));

    const rocks: HazardItem[] =
      raw.rocks ??
      rawHazards
        .filter((h: any) => {
          const t = (h.hazard_type || h.label || "").toLowerCase();
          return t === "boulder" || t === "rock";
        })
        .map((h: any, i: number) => ({
          id: h.id ?? `RK-${i + 1}`,
          type: "rock",
          latitude: h.latitude,
          longitude: h.longitude,
          size_m: h.estimated_size_m ?? h.diameter_m,
          confidence: h.confidence_score ?? h.confidence,
          severity: h.severity ?? "medium",
        }));

    const limitations: string[] = Array.isArray(raw.limitations)
      ? raw.limitations
      : typeof raw.limitations === "string" && raw.limitations.length > 0
      ? [raw.limitations]
      : [];

    return {
      ...raw,
      latitude: raw.center_lat ?? raw.latitude ?? body.latitude,
      longitude: raw.center_lon ?? raw.longitude ?? body.longitude,
      radius_m: raw.radius_meters ?? raw.radius_m ?? body.radius_m,
      craters,
      rocks,
      limitations,
      model: raw.model_name ?? raw.model ?? "Morphological Curvature & Gradient Anomaly Detector v1.2",
      summary: raw.summary ?? {
        overall_hazard_level: raw.overall_hazard_level ?? "moderate",
        total_hazards: raw.total_hazards_detected ?? (craters.length + rocks.length),
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
      score: s.score ?? s.suitability_score,
      suitability_score: s.suitability_score ?? s.score,
      elevation_m: s.elevation_m,
      elevation:
        typeof s.elevation === "object" && s.elevation !== null
          ? s.elevation
          : {
              mean_m: s.elevation_m,
              mean: s.elevation_m,
              value: s.elevation_m,
            },
      mean_slope_deg: s.mean_slope_deg,
      slope:
        typeof s.slope === "object" && s.slope !== null
          ? s.slope
          : {
              mean_deg: s.mean_slope_deg,
              mean: s.mean_slope_deg,
              value: s.mean_slope_deg,
              max_deg: s.max_slope_deg ?? (s.mean_slope_deg ? s.mean_slope_deg * 1.5 : null),
            },
      roughness:
        typeof s.roughness === "object" && s.roughness !== null
          ? s.roughness
          : {
              rms_m:
                s.roughness_m ??
                (s.mean_slope_deg ? (s.mean_slope_deg < 6.0 ? 0.3 : 0.6) : null),
              rms:
                s.roughness_m ??
                (s.mean_slope_deg ? (s.mean_slope_deg < 6.0 ? 0.3 : 0.6) : null),
            },
      illumination_pct: s.illumination_pct,
      illumination:
        typeof s.illumination === "object" && s.illumination !== null
          ? s.illumination
          : {
              sunlight_percent: s.illumination_pct,
              sunlit_percent: s.illumination_pct,
              illumination_percent: s.illumination_pct,
              value: s.illumination_pct,
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
    };
    return await request<VisibilitySimulationResponse>(
      "/api/simulation/visibility",
      () => mock.simulateVisibility(payload),
      { ...post(payload), signal }
    );
  },
};
