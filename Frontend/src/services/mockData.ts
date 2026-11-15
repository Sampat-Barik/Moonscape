/**
 * ============================================================================
 * mockData.ts — MOCK RESPONSES ONLY (development / demo mode).
 * ============================================================================
 * These functions imitate the FastAPI backend so the frontend can be developed
 * and demoed while the backend is unavailable. They are clearly separated from
 * real API responses: `services/api.ts` only calls these when the mode is
 * "mock" (or when "auto" mode cannot reach the backend), and the UI shows a
 * visible "Demo mode — mock data" banner whenever mock data is being used.
 *
 * Mock values are deterministic per coordinate (seeded hash) so the demo is
 * stable. They are NOT real scientific measurements.
 * ============================================================================
 */

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

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

/** Deterministic pseudo-random in [0, 1) from coordinates + salt. */
function hash2(lat: number, lon: number, salt = 0): number {
  let h =
    Math.imul(Math.round(lat * 1000) + 90000, 374761393) +
    Math.imul(Math.round(lon * 1000) + 180000, 668265263) +
    Math.imul(salt + 1, 2246822519);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}
const r1 = (v: number) => Math.round(v * 10) / 10;
const r2 = (v: number) => Math.round(v * 100) / 100;

export const MOCK_SITES: Site[] = [
  { site_id: "site_001", name: "Shackleton Rim", latitude: -89.9, longitude: 0.0, description: "Rim of Shackleton crater near the south pole — a candidate Artemis-era region." },
  { site_id: "site_002", name: "Connecting Ridge", latitude: -89.42, longitude: 34.0, description: "Ridge between Shackleton and Faustini with high illumination potential." },
  { site_id: "site_003", name: "Faustini Rim", latitude: -87.2, longitude: 80.0, description: "Faustini crater rim; possible access to permanently shadowed regions." },
  { site_id: "site_004", name: "Haworth", latitude: -87.4, longitude: 15.0, description: "Haworth crater region candidate." },
  { site_id: "site_005", name: "Malapert Massif", latitude: -86.5, longitude: 0.0, description: "Malapert massif — notable Earth-communication visibility." },
  { site_id: "site_006", name: "Shoemaker Basin", latitude: -88.1, longitude: 45.0, description: "Shoemaker crater region candidate." },
];

export async function health(): Promise<HealthResponse> {
  await delay(150);
  return {
    status: "ok",
    version: "0.0.0-mock",
    services: { terrain: "mock", hazards: "mock", ai: "mock", reports: "mock" },
  };
}

export async function getSites(): Promise<Site[]> {
  await delay(300);
  return MOCK_SITES;
}

export async function getSite(siteId: string): Promise<Site> {
  await delay(250);
  const s = MOCK_SITES.find((x) => x.site_id === siteId);
  if (!s) throw new Error(`Mock backend: unknown site_id "${siteId}"`);
  return s;
}

export async function getMapConfig(): Promise<MapConfig> {
  await delay(200);
  return {
    projection: "equirectangular",
    focus: { latitude: -90, longitude: 0 },
    south_pole: { latitude: -90, longitude: 0 },
    min_radius_m: 100,
    max_radius_m: 5000,
    attribution: "Mock map config (concepts: NASA LRO LOLA / LROC WAC)",
  };
}

export async function getTerrain(lat: number, lon: number): Promise<TerrainResponse> {
  await delay(400);
  const h = hash2(lat, lon);
  const hasIllumination = hash2(lat, lon, 7) > 0.3; // sometimes null, to demo "Data unavailable"
  return {
    latitude: lat,
    longitude: lon,
    radius_m: 500,
    elevation: {
      mean_m: r1(-5300 + (lat + 90) * 60 + h * 240),
      min_m: r1(-5620 + h * 120),
      max_m: r1(-4920 + h * 220),
      stddev_m: r2(18 + h * 60),
    },
    slope: { mean_deg: r2(5 + h * 9), max_deg: r2(18 + h * 16), p95_deg: r2(12 + h * 12) },
    roughness: { rms_m: r2(0.5 + h * 2.2), max_m: r2(1.5 + h * 4) },
    illumination: hasIllumination
      ? {
        sunlight_percent: r1(18 + h * 60),
        psr_nearby: hash2(lat, lon, 3) > 0.5,
        note: "Mock illumination estimate",
      }
      : null,
    data_sources: ["LOLA (mock)", "LROC WAC (mock)"],
    availability: { elevation: true, slope: true, roughness: true, illumination: hasIllumination },
  };
}

export async function runAnalysis(body: LocationRequest): Promise<AnalysisResponse> {
  const terrain = await getTerrain(body.latitude, body.longitude);
  await delay(250);
  return {
    ...terrain,
    radius_m: body.radius_m,
    analysis_id: `analysis_mock_${Math.round(hash2(body.latitude, body.longitude) * 1e6)}`,
    timestamp: new Date().toISOString(),
  };
}

export async function predictHazards(body: LocationRequest): Promise<HazardDetection> {
  await delay(600);
  const h = hash2(body.latitude, body.longitude, 11);
  const nCraters = 3 + Math.floor(h * 4);
  const nRocks = 5 + Math.floor(hash2(body.latitude, body.longitude, 12) * 9);
  const j = (salt: number) => (hash2(body.latitude, body.longitude, salt) - 0.5) * 0.02;
  const craters = Array.from({ length: nCraters }, (_, i) => ({
    id: `CR-${i + 1}`,
    latitude: r2(body.latitude + j(20 + i)),
    longitude: r2(body.longitude + j(40 + i)),
    diameter_m: r1(8 + hash2(body.latitude, body.longitude, 60 + i) * 160),
    depth_m: r1(1 + hash2(body.latitude, body.longitude, 80 + i) * 18),
    confidence: r2(0.55 + hash2(body.latitude, body.longitude, 100 + i) * 0.42),
  }));
  const rocks = Array.from({ length: nRocks }, (_, i) => ({
    id: `RK-${i + 1}`,
    latitude: r2(body.latitude + j(120 + i)),
    longitude: r2(body.longitude + j(140 + i)),
    size_m: r2(0.2 + hash2(body.latitude, body.longitude, 160 + i) * 4.5),
    confidence: r2(0.5 + hash2(body.latitude, body.longitude, 180 + i) * 0.48),
  }));
  return {
    latitude: body.latitude,
    longitude: body.longitude,
    radius_m: body.radius_m,
    craters,
    rocks,
    overlay_image: null, // mock returns no overlay → UI must show "Data unavailable"
    model: "moonscape-hazard-net v0 (mock)",
    limitations: [
      "Mock model output — not a real detection result.",
      "The live backend will report its own model limitations here.",
      "A confidence value is not a probability of impact or damage.",
    ],
    summary: { crater_count: craters.length, rock_count: rocks.length },
  };
}

export async function compareSites(siteIds: string[]): Promise<CompareResponse> {
  await delay(500);
  const sites = siteIds.map((id) => {
    const base = MOCK_SITES.find((s) => s.site_id === id) ?? {
      site_id: id,
      name: id,
      latitude: -88,
      longitude: 0,
    };
    const h = hash2(base.latitude, base.longitude, 99);
    return {
      ...base,
      elevation: { mean_m: r1(-5400 + h * 300) },
      slope: { mean_deg: r2(4 + h * 12), max_deg: r2(15 + h * 18) },
      roughness: { rms_m: r2(0.4 + h * 2.6) },
      illumination: hash2(base.latitude, base.longitude, 98) > 0.3 ? { sunlight_percent: r1(15 + h * 65) } : null,
      score: Math.round(38 + h * 57),
    };
  });
  return { sites, compared_at: new Date().toISOString() };
}

export async function scoreSite(body: LocationRequest): Promise<ScoreResponse> {
  await delay(450);
  const h = hash2(body.latitude, body.longitude, 5);
  const score = Math.round(35 + h * 60);
  return {
    score,
    grade: score >= 75 ? "A" : score >= 60 ? "B" : score >= 45 ? "C" : "D",
    label: "Preliminary suitability (mock)",
    breakdown: {
      terrain: Math.round(30 + hash2(body.latitude, body.longitude, 21) * 70),
      slope: Math.round(30 + hash2(body.latitude, body.longitude, 22) * 70),
      hazards: Math.round(30 + hash2(body.latitude, body.longitude, 23) * 70),
      illumination: Math.round(30 + hash2(body.latitude, body.longitude, 24) * 70),
    },
    disclaimer: "Preliminary decision-support score only — not a certification of landing safety.",
  };
}

export async function explainAnalysis(analysisId: string): Promise<ExplanationResponse> {
  await delay(900);
  return {
    analysis_id: analysisId,
    explanation:
      "MOCK EXPLANATION: The analysed region near the lunar south pole combines moderate slopes with locally high illumination. Permanently shadowed regions may be reachable within a short traverse, which is scientifically interesting for volatiles but raises thermal and operational constraints. Treat every value above as demo data until the live backend is connected.",
    positive_factors: [
      "Moderate mean slope in the analysed radius (mock data).",
      "High fraction of sunlight during the analysed period (mock data).",
      "Candidate access to permanently shadowed regions nearby (mock data).",
    ],
    risk_factors: [
      "Roughness and crater density may complicate touchdown (mock data).",
      "Low sun angles near the pole create long shadows that hide hazards (mock data).",
    ],
    uncertainties: [
      "Elevation and slope depend on the resolution of the source DEM.",
      "Illumination varies strongly with lunar season and local horizon.",
    ],
    limitations: [
      "This is a mock explanation generated without a real model.",
      "The live backend will replace this text with a model-generated explanation.",
    ],
    model: "moonscape-explainer (mock LLM)",
    generated_at: new Date().toISOString(),
  };
}

export async function generateReport(analysisId: string, format: string): Promise<ReportResponse> {
  await delay(700);
  return {
    report_id: `report_mock_${Math.round(hash2(0, analysisId.length, 31) * 1e6)}`,
    analysis_id: analysisId,
    format,
    generated_at: new Date().toISOString(),
    content: {
      title: "Moonscape preliminary landing-site report (MOCK)",
      analysis_id: analysisId,
      format,
      disclaimer: "Preliminary decision support only — not a certification of landing safety.",
      sections: {
        terrain: "See the Analysis Dashboard for elevation, slope, roughness and illumination.",
        hazards: "See Hazard Analysis for detected craters and rocks with confidence values.",
        score: "See the Analysis Dashboard for the preliminary suitability score.",
      },
    },
  };
}

export async function checkCoverage(lat: number, lon: number) {
  await delay(200);
  const inPole = lat <= -70.0 && lat >= -90.0;
  const coverageZone = lat <= -80.0 ? "core" : (lat <= -75.0 ? "extended" : (lat <= -70.0 ? "context" : "outside"));
  return {
    valid_coordinate: inPole,
    latitude: lat,
    longitude: lon,
    coverage_zone: coverageZone,
    in_south_pole_zone: inPole,
    best_installed_resolution_m: 80.0,
    total_covering_sources: 2,
    installed_covering_sources: 1,
    layers: [
      {
        source_id: "pgda_product90",
        name: "NASA PGDA Product 90 (LOLA South Pole 80m Regional Foundation)",
        tier: "Tier 1: Essential Local",
        covers: inPole,
        is_installed: true,
        resolution_m: 80.0,
      },
    ],
  };
}

export async function detectLandingSites(req: { center_lat: number; center_lon: number; search_radius_meters?: number }) {
  await delay(600);
  return {
    status: "success",
    center_lat: req.center_lat,
    center_lon: req.center_lon,
    search_radius_meters: req.search_radius_meters ?? 1500.0,
    total_sites_detected: 2,
    candidate_zones: [
      {
        zone_id: "ZONE-MOCK-A",
        centroid_lat: req.center_lat + 0.002,
        centroid_lon: req.center_lon + 0.005,
        contiguous_area_m2: 125000.0,
        effective_diameter_m: 398.9,
        pixel_count: 500,
        mean_slope_deg: 4.8,
        max_slope_deg: 7.2,
        mean_roughness_m: 0.12,
        mean_elevation_m: 1650.0,
        suitability_score: 92.4,
        hard_constraint_status: "passed",
        safety_rank: 1,
        feasibility_status: "optimal",
      },
      {
        zone_id: "ZONE-MOCK-B",
        centroid_lat: req.center_lat - 0.003,
        centroid_lon: req.center_lon - 0.004,
        contiguous_area_m2: 85000.0,
        effective_diameter_m: 328.9,
        pixel_count: 340,
        mean_slope_deg: 6.2,
        max_slope_deg: 8.9,
        mean_roughness_m: 0.18,
        mean_elevation_m: 1620.0,
        suitability_score: 84.1,
        hard_constraint_status: "passed",
        safety_rank: 2,
        feasibility_status: "nominal",
      },
    ],
    summary: "Mock landing zone detection around coordinate.",
  };
}

export async function simulateVisibility(req: { lat: number; lon: number; duration_days?: number; step_hours?: number }) {
  await delay(500);
  const duration = req.duration_days ?? 14;
  const step = req.step_hours ?? 2;
  const count = Math.floor((duration * 24) / step) + 1;
  const timeSeries = [];
  const start = new Date();
  for (let i = 0; i < count; i++) {
    const elapsed = i * step;
    const t = new Date(start.getTime() + elapsed * 3600 * 1000);
    const angle = (elapsed / 708.7) * 2 * Math.PI; // synodic period
    const sunElev = Math.sin(angle) * 1.5;
    const earthElev = 2.0 + Math.sin(angle * 1.05) * 4.0;
    const isSun = sunElev > 0;
    const isEarth = earthElev > 0;
    timeSeries.push({
      timestamp_iso: t.toISOString(),
      elapsed_hours: elapsed,
      solar_elevation_deg: Math.round(sunElev * 100) / 100,
      solar_azimuth_deg: Math.round(((elapsed * 0.5) % 360) * 10) / 10,
      sunlit_fraction_pct: isSun ? 100.0 : 0.0,
      is_sunlit: isSun,
      earth_elevation_deg: Math.round(earthElev * 100) / 100,
      earth_azimuth_deg: 120.0,
      earth_visibility_fraction: isEarth ? 1.0 : 0.0,
      is_earth_visible: isEarth,
      communication_status: isEarth ? "operational" : "blackout",
      surface_temp_k: isSun ? 220.0 : 40.0,
      horizon_elevation_sun_deg: 0.0,
      horizon_elevation_earth_deg: 0.0,
      is_combined_ops_available: isSun && isEarth,
    });
  }
  return {
    query_lat: req.lat,
    query_lon: req.lon,
    start_epoch_iso: start.toISOString(),
    end_epoch_iso: new Date(start.getTime() + duration * 24 * 3600 * 1000).toISOString(),
    duration_days: duration,
    total_steps: count,
    total_sunlight_hours: Math.round(duration * 24 * 0.65),
    sunlight_percentage: 65.0,
    total_earth_comm_hours: Math.round(duration * 24 * 0.8),
    earth_comm_percentage: 80.0,
    max_continuous_sunlight_hours: 120.0,
    max_continuous_darkness_hours: 48.0,
    max_continuous_comm_blackout_hours: 24.0,
    time_series: timeSeries,
    scientific_methodology: "Mock ephemeris and horizon occultation simulation.",
    caveats: ["Demo mock data."],
  };
}
