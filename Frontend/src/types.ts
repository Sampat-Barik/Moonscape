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
  score?: number | null;
  grade?: string | null;
  label?: string | null;
  score_label?: string | null;
  breakdown?: Record<string, number | null> | null;
  score_breakdown?: Record<string, number | null> | null;
  preliminary_feasibility?: string;
  safe_touchdown_fraction_pct?: number;
  dataset_metadata?: Record<string, unknown>;
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
  pdf_blob?: Blob;
  generated_at?: string;
  [key: string]: unknown;
}

// ============================================================================
// Spatial Dataset Coverage Types
// ============================================================================

export interface CoverageLayer {
  source_id: string;
  name: string;
  tier?: string;
  covers: boolean;
  is_installed: boolean;
  resolution_m?: number;
  status?: string | null;
  detail?: string | null;
  measurement_type?: string | null;
}

export interface DataCoverageResponse {
  valid_coordinate: boolean;
  latitude: number;
  longitude: number;
  in_south_pole_zone: boolean;
  best_installed_resolution_m?: number | null;
  total_covering_sources: number;
  installed_covering_sources: number;
  layers: CoverageLayer[];
  [key: string]: unknown;
}

// ============================================================================
// Automated Landing Zone Detection Types (Feature 7)
// ============================================================================

export interface DetectLandingSitesRequest {
  center_lat: number;
  center_lon: number;
  search_radius_meters?: number;
  max_slope_deg?: number;
  max_roughness_m?: number;
  min_landing_diameter_meters?: number;
  mission_profile?: string;
}

export interface DetectedLandingZone {
  zone_id: string;
  centroid_lat: number;
  centroid_lon: number;
  contiguous_area_m2: number;
  effective_diameter_m: number;
  pixel_count: number;
  mean_slope_deg: number;
  max_slope_deg: number;
  mean_roughness_m: number;
  mean_elevation_m: number;
  suitability_score: number;
  ml_model_score?: number | null;
  hard_constraint_status: string;
  safety_rank: number;
  feasibility_status: string;
  [key: string]: unknown;
}

export interface DetectLandingSitesResponse {
  status: string;
  center_lat: number;
  center_lon: number;
  search_radius_meters: number;
  total_sites_detected: number;
  candidate_zones: DetectedLandingZone[];
  dataset_metadata?: Record<string, unknown>;
  summary: string;
  mission_profile?: string;
  warnings?: string[];
  [key: string]: unknown;
}

// ============================================================================
// Sun / Earth Visibility Simulation Types (Features 8, 9, 10)
// ============================================================================

export interface VisibilitySimulationRequest {
  lat: number;
  lon: number;
  start_epoch_iso?: string | null;
  duration_days?: number;
  step_hours?: number;
  ephemeris_source?: string;
}

export interface SimulationTimeStep {
  timestamp_iso: string;
  elapsed_hours: number;
  solar_elevation_deg: number;
  solar_azimuth_deg: number;
  sunlit_fraction_pct: number;
  is_sunlit: boolean;
  earth_elevation_deg: number;
  earth_azimuth_deg: number;
  earth_visibility_fraction: number;
  is_earth_visible: boolean;
  communication_status: "operational" | "marginal" | "blackout" | string;
  surface_temp_k: number;
  horizon_elevation_sun_deg?: number | null;
  horizon_elevation_earth_deg?: number | null;
  is_combined_ops_available?: boolean | null;
  [key: string]: unknown;
}

export interface VisibilitySimulationResponse {
  query_lat: number;
  query_lon: number;
  start_epoch_iso: string;
  end_epoch_iso: string;
  duration_days: number;
  total_steps: number;
  total_sunlight_hours: number;
  sunlight_percentage: number;
  total_earth_comm_hours: number;
  earth_comm_percentage: number;
  max_continuous_sunlight_hours: number;
  max_continuous_darkness_hours: number;
  max_continuous_comm_blackout_hours: number;
  combined_ops_hours?: number | null;
  combined_ops_percentage?: number | null;
  horizon_min_deg?: number | null;
  horizon_max_deg?: number | null;
  horizon_mean_deg?: number | null;
  terrain_dataset?: string | null;
  ephemeris_provider?: string | null;
  time_series: SimulationTimeStep[];
  scientific_methodology: string;
  caveats: string[];
  [key: string]: unknown;
}

// ============================================================================
// External NASA Integration Types (JPL Horizons, Moon Trek, LROC QuickMap)
// ============================================================================

export interface ExternalSourceStatus {
  source_id: string;
  name: string;
  status: "operational" | "degraded" | "offline" | string;
  endpoint_url: string;
  description: string;
  documentation_url: string;
  is_live_accessible: boolean;
  cached_entries_count: number;
  notes: string;
}

export interface ExternalSourcesStatusResponse {
  horizons: ExternalSourceStatus;
  moon_trek: ExternalSourceStatus;
  lroc_quickmap: ExternalSourceStatus;
  timestamp: string;
}

export interface MoonTrekLayer {
  id: string;
  name: string;
  description: string;
  wmts_endpoint: string;
  capabilities_url: string;
  tile_url_template: string;
  tile_format: string;
  tile_matrix_set: string;
  projection: string;
  projection_type: "polar" | "equirectangular" | string;
  resolution_m: number;
  min_zoom: number;
  max_zoom: number;
  bounds: {
    min_lat: number;
    max_lat: number;
    min_lon: number;
    max_lon: number;
  };
  attribution: string;
  default_opacity?: number;
  is_active_default?: boolean;
}

export interface MoonTrekLayersResponse {
  layers_count: number;
  layers: MoonTrekLayer[];
  supported_projections: string[];
  documentation_url: string;
}

export interface LROCDTMItem {
  name: string;
  pds_id: string;
  centroid: { lat: number; lon: number };
  resolution_m: number;
  footprint_bounds: {
    min_lat: number;
    max_lat: number;
    min_lon: number;
    max_lon: number;
  };
  pds_url: string;
  [key: string]: unknown;
}

export interface LROCCoverageResponse {
  latitude: number;
  longitude: number;
  is_covered: boolean;
  covering_dtms_count: number;
  covering_dtms: LROCDTMItem[];
  nearest_dtm?: LROCDTMItem | null;
  distance_to_nearest_dtm_km: number;
  best_resolution_m?: number | null;
  quickmap_url: string;
  lroc_archive_url: string;
  optical_hazard_validation_supported: boolean;
  status_note: string;
}

export interface HorizonsQueryRequest {
  latitude: number;
  longitude: number;
  altitude_km?: number;
  target?: "Sun" | "Earth" | "both" | string;
  start_epoch_iso: string;
  stop_epoch_iso?: string | null;
  duration_days?: number;
  step_hours?: number;
}

export interface HorizonsPoint {
  epoch_iso: string;
  target: string;
  target_id: string;
  azimuth_deg: number;
  elevation_deg: number;
  distance_au?: number | null;
  distance_km?: number | null;
  range_rate_km_s?: number | null;
  apparent_coordinates: boolean;
  ref_body: string;
}

export interface HorizonsQueryResponse {
  success: boolean;
  target: string;
  observer: {
    latitude_deg: number;
    longitude_deg: number;
    altitude_km: number;
  };
  temporal_window: {
    start_iso: string;
    stop_iso: string;
    step: string;
  };
  points_count: number;
  points: HorizonsPoint[];
  source_attribution: string;
  is_cached: boolean;
  query_duration_ms: number;
  error_message?: string | null;
}
