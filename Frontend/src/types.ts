/**
 * TypeScript types describing the Moonscape backend API contract.
 *
 * The backend may return `null` for any scientific dataset that is
 * unavailable. The frontend must render "Data unavailable" for nulls —
 * never zero, never a fabricated value.
 *
 * Types are intentionally loose (index signatures) so the UI keeps
 * working if the backend adds fields.
 */

/** Location-based request body used by several endpoints. */
export interface LocationRequest {
  latitude: number;
  longitude: number;
  radius_m: number;
}

export interface HealthResponse {
  status?: string;
  version?: string;
  services?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface Site {
  site_id: string;
  name?: string;
  latitude: number;
  longitude: number;
  description?: string;
  [key: string]: unknown;
}

export interface MapConfig {
  [key: string]: unknown;
}

/** A scientific metric block (elevation / slope / roughness / illumination). */
export interface MetricBlock {
  [key: string]: unknown;
}

export interface TerrainResponse {
  latitude?: number;
  longitude?: number;
  radius_m?: number;
  elevation?: MetricBlock | null;
  slope?: MetricBlock | null;
  roughness?: MetricBlock | null;
  illumination?: MetricBlock | null;
  data_sources?: string[];
  availability?: Record<string, unknown>;
  timestamp?: string;
  [key: string]: unknown;
}

export interface AnalysisResponse extends TerrainResponse {
  analysis_id?: string;
}

export interface HazardItem {
  id?: string;
  type?: string;
  latitude?: number;
  longitude?: number;
  diameter_m?: number | null;
  radius_m?: number | null;
  size_m?: number | null;
  depth_m?: number | null;
  confidence?: number | null;
  [key: string]: unknown;
}

export interface HazardDetection {
  latitude?: number;
  longitude?: number;
  radius_m?: number;
  craters?: HazardItem[] | null;
  rocks?: HazardItem[] | null;
  overlay_image?: string | null;
  image_url?: string | null;
  model?: string;
  limitations?: string[];
  summary?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface ScoreResponse {
  score?: number | null;
  grade?: string | null;
  label?: string | null;
  breakdown?: Record<string, number | null> | null;
  disclaimer?: string | null;
  [key: string]: unknown;
}

export interface CompareSite {
  site_id: string;
  name?: string;
  latitude?: number;
  longitude?: number;
  score?: number | null;
  elevation?: MetricBlock | null;
  slope?: MetricBlock | null;
  roughness?: MetricBlock | null;
  illumination?: MetricBlock | null;
  [key: string]: unknown;
}

export interface CompareResponse {
  sites?: CompareSite[];
  results?: CompareSite[];
  compared_at?: string;
  [key: string]: unknown;
}

export interface ExplanationResponse {
  analysis_id?: string;
  explanation?: string;
  summary?: string;
  positive_factors?: string[];
  risk_factors?: string[];
  uncertainties?: string[];
  limitations?: string[];
  model?: string;
  generated_at?: string;
  [key: string]: unknown;
}

export interface ReportResponse {
  report_id?: string;
  analysis_id?: string;
  format?: string;
  content?: unknown;
  download_url?: string;
  generated_at?: string;
  [key: string]: unknown;
}
