/**
 * Moonscape Frontend API Client Module
 * Connects to the Moonscape FastAPI backend at http://localhost:8000
 */

import type {
  AIExplainRequest,
  AIExplainResponse,
  AnalysisRunRequest,
  AnalysisRunResponse,
  CandidateSite,
  HazardPredictRequest,
  HazardPredictResponse,
  MapConfigResponse,
  ReportGenerateRequest,
  ReportGenerateResponse,
  ScoreRequest,
  ScoreResponse,
  SiteCompareResponse,
  SystemHealthResponse,
  TerrainResponse,
} from "./types";

export const DEFAULT_API_BASE_URL = "http://localhost:8000/api";

export class MoonscapeApiClient {
  private baseUrl: string;
  private timeoutMs: number;

  constructor(baseUrl: string = DEFAULT_API_BASE_URL, timeoutMs: number = 30000) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.timeoutMs = timeoutMs;
  }

  public setBaseUrl(url: string): void {
    this.baseUrl = url.replace(/\/+$/, "");
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  /**
   * Internal wrapper around window.fetch with AbortController timeout & error handling.
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);

    const url = `${this.baseUrl}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...(options.headers as Record<string, string> || {}),
    };

    if (options.body && !(options.body instanceof FormData) && !(options.body instanceof Blob)) {
      headers["Content-Type"] = "application/json";
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });

      if (!response.ok) {
        let errorDetail = `HTTP ${response.status} ${response.statusText}`;
        try {
          const errJson = await response.json();
          if (errJson && errJson.detail) {
            errorDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
          }
        } catch {
          // Response body was not JSON
        }
        throw new Error(errorDetail);
      }

      return (await response.json()) as T;
    } catch (err: any) {
      if (err.name === "AbortError") {
        throw new Error(`Request to ${endpoint} timed out after ${this.timeoutMs / 1000}s`);
      }
      throw err;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  // -------------------------------------------------------------------------
  // 1. System Health
  // -------------------------------------------------------------------------
  public async checkHealth(): Promise<SystemHealthResponse> {
    return this.request<SystemHealthResponse>("/health");
  }

  // -------------------------------------------------------------------------
  // 2. Candidate Landing Sites
  // -------------------------------------------------------------------------
  public async getSites(): Promise<CandidateSite[]> {
    return this.request<CandidateSite[]>("/sites");
  }

  public async getSite(siteId: string): Promise<CandidateSite> {
    return this.request<CandidateSite>(`/sites/${encodeURIComponent(siteId)}`);
  }

  public async compareSites(
    siteIds: string[],
    weights?: Record<string, number>
  ): Promise<SiteCompareResponse> {
    return this.request<SiteCompareResponse>("/sites/compare", {
      method: "POST",
      body: JSON.stringify({ site_ids: siteIds, weights }),
    });
  }

  // -------------------------------------------------------------------------
  // 3. Cartographic & Map Configuration
  // -------------------------------------------------------------------------
  public async getMapConfig(): Promise<MapConfigResponse> {
    return this.request<MapConfigResponse>("/map/config");
  }

  // -------------------------------------------------------------------------
  // 4. Point Terrain Sampling
  // -------------------------------------------------------------------------
  public async getTerrain(lat: number, lon: number): Promise<TerrainResponse> {
    const params = new URLSearchParams({
      lat: lat.toString(),
      lon: lon.toString(),
    });
    return this.request<TerrainResponse>(`/terrain?${params.toString()}`);
  }

  // -------------------------------------------------------------------------
  // 5. Landing Zone Spatial Analysis
  // -------------------------------------------------------------------------
  public async runAnalysis(req: AnalysisRunRequest): Promise<AnalysisRunResponse> {
    return this.request<AnalysisRunResponse>("/analysis/run", {
      method: "POST",
      body: JSON.stringify(req),
    });
  }

  // -------------------------------------------------------------------------
  // 6. Touchdown Hazard Detection
  // -------------------------------------------------------------------------
  public async predictHazards(req: HazardPredictRequest): Promise<HazardPredictResponse> {
    return this.request<HazardPredictResponse>("/hazards/predict", {
      method: "POST",
      body: JSON.stringify(req),
    });
  }

  // -------------------------------------------------------------------------
  // 7. Transparent Suitability Scoring
  // -------------------------------------------------------------------------
  public async computeScore(req: ScoreRequest): Promise<ScoreResponse> {
    return this.request<ScoreResponse>("/score", {
      method: "POST",
      body: JSON.stringify(req),
    });
  }

  // -------------------------------------------------------------------------
  // 8. AI Scientific Explainer
  // -------------------------------------------------------------------------
  public async explainAnalysis(req: AIExplainRequest): Promise<AIExplainResponse> {
    return this.request<AIExplainResponse>("/ai/explain", {
      method: "POST",
      body: JSON.stringify(req),
    });
  }

  // -------------------------------------------------------------------------
  // 9. Mission Reports Generation
  // -------------------------------------------------------------------------
  public async generateReport(req: ReportGenerateRequest): Promise<ReportGenerateResponse> {
    return this.request<ReportGenerateResponse>("/reports/generate", {
      method: "POST",
      body: JSON.stringify(req),
    });
  }

  /**
   * Automatically detects contiguous safe landing zones from real NASA DEM elevation rasters.
   */
  public async detectLandingSites(params: {
    center_lat: number;
    center_lon: number;
    search_radius_meters?: number;
    max_slope_deg?: number;
    max_roughness_m?: number;
    min_landing_diameter_meters?: number;
  }): Promise<any> {
    return this.request("/sites/detect", {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  /**
   * Propagates time-series Sun and Earth visibility simulation.
   */
  public async simulateVisibility(params: {
    lat: number;
    lon: number;
    start_epoch_iso?: string;
    duration_days?: number;
    step_hours?: number;
  }): Promise<any> {
    return this.request("/simulation/visibility", {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  /**
   * Discovers intersecting NASA LROC NAC targeted stereo DTM footprints.
   */
  public async discoverLROCNACFootprints(lat: number, lon: number, radiusMeters: number = 5000): Promise<any> {
    return this.request(`/data/lroc/footprints?lat=${lat}&lon=${lon}&radius=${radiusMeters}`);
  }

  /**
   * Downloads publication-quality binary PDF report directly as a Blob.
   */
  public async downloadPdfReport(analysisId: string, missionTitle?: string): Promise<Blob> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);
    const url = `${this.baseUrl}/reports/generate`;

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/pdf",
        },
        body: JSON.stringify({
          analysis_id: analysisId,
          format: "pdf",
          mission_title: missionTitle || "Moonscape Lunar Landing Site Scientific Assessment",
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`PDF generation failed: HTTP ${response.status} ${response.statusText}`);
      }

      return await response.blob();
    } finally {
      clearTimeout(timeoutId);
    }
  }
}

// Default singleton instance
export const moonscapeApi = new MoonscapeApiClient();
