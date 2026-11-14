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
  };
  notes: string | null;
}

export interface AnalysisRunRequest {
  center_lat: number;
  center_lon: number;
  radius_meters?: number;
  max_acceptable_slope_deg?: number;
  max_acceptable_roughness_m?: number;
}

export interface TopographicStats {
  min_value: number | null;
  max_value: number | null;
  mean_value: number | null;
  median_value: number | null;
  std_dev: number | null;
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
  safe_touchdown_fraction_pct: number;
  preliminary_feasibility: "favorable" | "marginal" | "unfavorable" | "insufficient_data";
  dataset_metadata: Record<string, any>;
  disclaimer: string;
}

export interface HazardPredictRequest {
  center_lat: number;
  center_lon: number;
  radius_meters?: number;
  min_crater_diameter_m?: number;
  boulder_detection_sensitivity?: number;
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
  hazard_assessment_id: string;
  center_lat: number;
  center_lon: number;
  radius_meters: number;
  total_hazards_detected: number;
  craters_count: number;
  boulders_count: number;
  steep_slope_cells: number;
  shadow_coverage_pct: number | null;
  overall_hazard_level: "low" | "moderate" | "high" | "critical";
  hazards: HazardItem[];
  model_metadata: Record<string, any>;
  disclaimer: string;
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
