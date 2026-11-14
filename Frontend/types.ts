/**
 * Moonscape API Contract TypeScript Definitions
 * Auto-aligned with Moonscape Backend FastAPI schemas
 * Base URL: http://localhost:8000
 */

export interface HealthResponse {
  status: "healthy" | "degraded";
  version: string;
  dem_dataset_loaded: boolean;
  sites_loaded: number;
  crs: string;
  disclaimer: string;
}

export interface CandidateSite {
  site_id: string;
  name: string;
  latitude: number;
  longitude: number;
  elevation_m: number | null;
  mean_slope_deg: number | null;
  illumination_pct: number | null;
  earth_visibility_pct: number | null;
  description: string;
  scientific_value: string;
  target_mission: string;
  priority: "high" | "medium" | "low";
}

export interface MapLayerConfig {
  id: string;
  name: string;
  type: "raster" | "vector" | "tile" | "geojson";
  description: string;
  unit: string;
  color_scale: string;
  min_value: number;
  max_value: number;
  attribution: string;
}

export interface MapConfigResponse {
  projection: string;
  epsg_code: string;
  central_meridian_deg: number;
  latitude_of_origin_deg: number;
  reference_radius_m: number;
  default_center: [number, number];
  default_zoom: number;
  min_zoom: number;
  max_zoom: number;
  latitude_bounds: [number, number];
  longitude_bounds: [number, number];
  layers: MapLayerConfig[];
  data_sources: Array<{
    name: string;
    product: string;
    repository: string;
    doi: string;
  }>;
}

export interface ElevationSummary {
  point_m: number | null;
  min_m: number | null;
  max_m: number | null;
  mean_m: number | null;
  variation_m: number | null; // Macro relief: max - min
  std_dev_m: number | null;
  units: string;
}

export interface SlopeSummary {
  point_deg: number | null;
  min_deg: number | null;
  max_deg: number | null;
  mean_deg: number | null;
  std_dev_deg: number | null;
  method: string;
  units: string;
  ideal_pct?: number | null;
  acceptable_pct?: number | null;
  marginal_pct?: number | null;
  critical_hazardous_pct?: number | null;
}

export interface RoughnessSummary {
  point_m: number | null;
  min_m: number | null;
  max_m: number | null;
  mean_m: number | null;
  std_dev_m: number | null;
  method: string;
  kernel_size: number;
  baseline_m: number;
  units: string;
}

export interface TerrainResponse {
  latitude: number;
  longitude: number;
  is_valid_point: boolean;
  is_nodata: boolean;
  elevation_m: number | null;
  slope_deg: number | null;
  roughness_m: number | null;
  aspect_deg: number | null;
  solar_illumination_pct: number | null;
  landing_hazard_classification: "safe" | "marginal" | "hazardous" | "nodata";
  dataset_info: {
    dataset_name: string;
    product_id: string;
    spatial_resolution_m: number;
    vertical_uncertainty_m: number;
    slope_method: string;
    roughness_baseline_m: number;
    citation?: string | null;
    observation_count?: number | null;
    slope_uncertainty_deg?: number | null;
    effective_resolution_m?: number | null;
    is_measured_data?: boolean;
    source_url?: string | null;
    crs?: string | null;
    reference_frame?: string | null;
    quality_warnings?: string | null;
  };
  source_tier?: string | null;
  uncertainty_elevation_m?: number | null;
  uncertainty_slope_deg?: number | null;
  notes: string | null;
  analysis_radius_m?: number | null;
  elevation_summary?: ElevationSummary | null;
  slope_summary?: SlopeSummary | null;
  roughness_summary?: RoughnessSummary | null;
  total_pixels_in_disc?: number | null;
  valid_pixels_in_disc?: number | null;
  nodata_pixels_in_disc?: number | null;
}

export interface AnalysisRunRequest {
  center_lat: number;
  center_lon: number;
  radius_meters?: number;
  max_acceptable_slope_deg?: number;
  max_acceptable_roughness_m?: number;
  roughness_kernel_size?: number;
  epoch_iso?: string;
  time_period?: string;
}

export interface IlluminationSummary {
  status: "available" | "degraded" | "unavailable";
  solar_elevation_deg: number | null;
  solar_azimuth_deg: number | null;
  instantaneous_sunlit_fraction_pct: number | null;
  cumulative_illumination_pct: number | null;
  time_period_evaluated: string;
  is_permanently_shadowed_region: boolean;
  estimated_surface_temp_k: number | null;
  sunlight_continuous_hours_max: number | null;
  methodology: string;
  source_attribution: string;
  scientific_caveats: string[];
}

export interface TopographicStats {
  min_value: number | null;
  max_value: number | null;
  mean_value: number | null;
  median_value: number | null;
  std_dev: number | null;
  variation?: number | null;
  units: string;
}

export interface SlopeDistribution {
  ideal_pct: number;
  acceptable_pct: number;
  marginal_pct: number;
  critical_hazardous_pct: number;
}

export interface AnalysisRunResponse {
  analysis_id: string;
  center_lat: number;
  center_lon: number;
  radius_meters: number;
  total_samples: number;
  valid_samples: number;
  nodata_samples: number;
  elevation: TopographicStats;
  slope: TopographicStats;
  slope_distribution: SlopeDistribution;
  roughness_mean_m: number | null;
  roughness_max_m?: number | null;
  roughness_baseline_m?: number | null;
  roughness_method?: string | null;
  slope_method?: string | null;
  safe_touchdown_fraction_pct: number;
  preliminary_feasibility: "favorable" | "marginal" | "unfavorable" | "insufficient_data";
  dataset_metadata: Record<string, any>;
  disclaimer: string;
  illumination?: IlluminationSummary | null;
}

export interface BoundingBox {
  ymin: number;
  xmin: number;
  ymax: number;
  xmax: number;
}

export interface DetectionItem {
  label: "crater" | "rock" | "boulder" | "escarpment";
  confidence: number;
  bounding_box?: BoundingBox | null;
  center_pixel?: [number, number] | null;
  pixel_diameter?: number | null;
  estimated_size_m?: number | null;
  severity?: "low" | "medium" | "high" | "critical";
  mask_rle?: string | null;
}

export interface HazardPredictRequest {
  center_lat?: number;
  center_lon?: number;
  radius_meters?: number;
  min_crater_diameter_m?: number;
  boulder_detection_sensitivity?: number;
  image_base64?: string;
  image_path?: string;
  spatial_resolution_mpp?: number;
  confidence_threshold?: number;
}

export interface HazardItem {
  hazard_type: "crater" | "boulder" | "escarpment" | "permanent_shadow";
  latitude: number;
  longitude: number;
  estimated_size_m: number;
  severity: "low" | "medium" | "high" | "critical";
  confidence_score: number;
  source: string;
}

export interface HazardPredictResponse {
  status: "success" | "not_available" | "error";
  detections: DetectionItem[];
  crater_count: number | null;
  rock_count: number | null;
  warnings: string[];
  model_name?: string | null;
  model_version?: string | null;
  limitations?: string | null;

  // Topographic DEM analysis fields (present on coordinate queries)
  hazard_assessment_id?: string | null;
  center_lat?: number | null;
  center_lon?: number | null;
  radius_meters?: number | null;
  total_hazards_detected?: number | null;
  craters_count?: number | null;
  boulders_count?: number | null;
  steep_slope_cells?: number | null;
  shadow_coverage_pct?: number | null;
  overall_hazard_level?: "low" | "moderate" | "high" | "critical" | null;
  hazards?: HazardItem[];
  model_metadata?: Record<string, any>;
  disclaimer?: string | null;
}

export interface SiteCompareRequest {
  site_ids: string[];
  weights?: {
    slope?: number;
    illumination?: number;
    communication?: number;
    science?: number;
  };
}

export interface SiteComparisonItem {
  site_id: string;
  name: string;
  latitude: number;
  longitude: number;
  elevation_m: number | null;
  mean_slope_deg: number | null;
  illumination_pct: number | null;
  earth_visibility_pct: number | null;
  suitability_score: number;
  safety_rank: number;
  key_strengths: string[];
  key_vulnerabilities: string[];
}

export interface SiteCompareResponse {
  compared_sites: SiteComparisonItem[];
  top_recommended_site_id: string;
  tradeoff_summary: string;
  criteria_weights: Record<string, number>;
  disclaimer: string;
}

export interface ScoreRequest {
  site_id?: string;
  slope_deg?: number;
  roughness_m?: number;
  illumination_pct?: number;
  earth_visibility_pct?: number;
  science_value_rating?: number;
  weights?: {
    slope_weight?: number;
    roughness_weight?: number;
    illumination_weight?: number;
    communication_weight?: number;
    science_weight?: number;
  };
}

export interface FactorSubscore {
  criterion: string;
  raw_measurement: number | null;
  unit: string;
  normalized_subscore: number;
  weight: number;
  weighted_contribution: number;
  description: string;
}

export interface ScoreResponse {
  site_id: string | null;
  overall_suitability_score: number;
  suitability_category: "Optimal" | "Nominal" | "Marginal" | "High Risk" | "Unsuitable";
  subscores: FactorSubscore[];
  scoring_methodology: string;
  key_advantages: string[];
  critical_concerns: string[];
  disclaimer: string;
}

export interface AIExplainRequest {
  site_id?: string;
  site_name?: string;
  latitude?: number;
  longitude?: number;
  topographic_data?: Record<string, any>;
  score_data?: Record<string, any>;
  focus_topics?: string[];
  user_query?: string;
}

export interface AIExplainResponse {
  explanation_id: string;
  target_site: string;
  executive_summary: string;
  geomorphology_assessment: string;
  thermal_and_power_assessment: string;
  communication_and_direct_line_of_sight: string;
  traverse_and_sampling_potential: string;
  key_engineering_tradeoffs: string[];
  mitigation_strategies: string[];
  model_origin: string;
  disclaimer: string;
}

export interface ReportGenerateRequest {
  site_id: string;
  mission_title?: string;
  include_ai_narrative?: boolean;
  output_format?: "json" | "markdown" | "html";
}

export interface ReportGenerateResponse {
  report_id: string;
  generated_at: string;
  mission_title: string;
  site_id: string;
  site_name: string;
  output_format: "json" | "markdown" | "html";
  content: string;
  structured_summary: Record<string, any>;
  disclaimer: string;
}

// ---------------------------------------------------------------------------
// Phase 2: NASA Lunar Data Management Types
// ---------------------------------------------------------------------------

export interface DatasetItem {
  id: string;
  name: string;
  source_provider: string;
  product_id: string;
  filename: string;
  size_mb: number;
  spatial_resolution_m: number;
  units: string;
  tier: "local_required" | "local_optional" | "remote_metadata" | "remote_window" | "remote_full_file" | "not_supported";
  byte_range_supported: boolean;
  status: "not_installed" | "remote_available" | "download_queued" | "downloading" | "downloaded" | "validating" | "available" | "partial" | "failed" | "invalid" | "unavailable";
  validation_detail?: string | null;
  is_installed: boolean;
  bounds: {
    min_lat: number;
    max_lat: number;
    min_lon: number;
    max_lon: number;
  };
}

export interface DatasetProfile {
  name: string;
  description: string;
  total_size_mb: number;
  datasets: string[];
}

export interface DatasetCatalogResponse {
  total_datasets: number;
  installed_count: number;
  default_profile: string;
  profiles: Record<string, DatasetProfile>;
  datasets: DatasetItem[];
}

export interface CoverageLayer {
  source_id: string;
  name: string;
  tier: string;
  covers: boolean;
  is_installed: boolean;
  resolution_m: number;
  status?: string | null;
  detail?: string | null;
  measurement_type?: string | null;
  covering_candidate_sites?: string[] | null;
  covering_nac_dtms?: string[] | null;
}

export interface DataCoverageResponse {
  valid_coordinate: boolean;
  latitude: number;
  longitude: number;
  in_south_pole_zone: boolean;
  best_installed_resolution_m: number | null;
  total_covering_sources: number;
  installed_covering_sources: number;
  layers: CoverageLayer[];
}

export interface DownloadTaskResponse {
  task_id: string;
  dataset_id: string;
  filename: string;
  status: "queued" | "downloading" | "validating" | "completed" | "cancelled" | "failed";
  bytes_downloaded: number;
  total_bytes: number;
  progress_pct: number;
  speed_mbps: number;
  error_message?: string | null;
}
