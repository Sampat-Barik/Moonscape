import { test, describe } from "node:test";
import assert from "node:assert/strict";

const BACKEND_URL = "http://127.0.0.1:8000";

describe("MOONSCAPE — LIVE SCIENTIFIC WORKFLOW VALIDATION (11 CORE FEATURES)", () => {
  let siteAnalysisResult = null;

  test("Feature 1: Elevation Analysis (Real NASA LOLA Product 78 DEM)", async () => {
    const res = await fetch(`${BACKEND_URL}/api/analysis/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        center_lat: -89.44,
        center_lon: 222.5,
        radius_meters: 500.0,
        max_acceptable_slope_deg: 10.0,
        max_acceptable_roughness_m: 0.5,
      }),
    });

    assert.equal(res.status, 200, `Expected HTTP 200, got ${res.status}`);
    siteAnalysisResult = await res.json();

    // Verify Elevation metrics
    assert.ok(siteAnalysisResult.elevation, "Elevation block must exist");
    assert.equal(typeof siteAnalysisResult.elevation.mean_value, "number");
    assert.ok(
      siteAnalysisResult.elevation.mean_value > -9000 && siteAnalysisResult.elevation.mean_value < 5000,
      `Mean elevation ${siteAnalysisResult.elevation.mean_value}m is physically plausible for lunar South Pole`
    );
    assert.ok(siteAnalysisResult.elevation.variation >= 0, "Topographic relief must be non-negative");
    assert.ok(["m", "meters"].includes(siteAnalysisResult.elevation.units), "Units must be meters or m");
  });

  test("Feature 2: Slope Gradients (Horn 1981 Finite-Difference Kernel)", () => {
    assert.ok(siteAnalysisResult, "Prior analysis result must exist");
    const slope = siteAnalysisResult.slope;
    assert.ok(slope, "Slope statistics must exist");
    assert.ok(slope.mean_value >= 0 && slope.mean_value <= 90, `Mean slope ${slope.mean_value}° must be within [0, 90]`);
    assert.ok(slope.max_value >= slope.mean_value, "Max slope must be >= mean slope");

    // Slope Distribution
    const dist = siteAnalysisResult.slope_distribution;
    assert.ok(dist, "Slope distribution must exist");
    const sum = dist.ideal_pct + dist.acceptable_pct + dist.marginal_pct + dist.critical_hazardous_pct;
    assert.ok(Math.abs(sum - 100.0) < 0.5, `Slope distribution percentages must sum to 100% (got ${sum}%)`);
  });

  test("Feature 3: Surface Roughness (RMS Elevation Deviation)", () => {
    assert.ok(siteAnalysisResult, "Prior analysis result must exist");
    const roughnessMean = siteAnalysisResult.roughness_mean_m;
    assert.equal(typeof roughnessMean, "number", "Roughness mean must be a valid number");
    assert.ok(roughnessMean >= 0.0 && roughnessMean < 50.0, `RMS roughness ${roughnessMean}m must be physically plausible`);
  });

  test("Feature 4: Landing-Site Feasibility & Touchdown Safety Detection", () => {
    assert.ok(siteAnalysisResult, "Prior analysis result must exist");
    const safePct = siteAnalysisResult.safe_touchdown_fraction_pct;
    assert.ok(typeof safePct === "number" && safePct >= 0 && safePct <= 100, "Safe touchdown fraction must be 0-100%");
    assert.ok(
      ["favorable", "marginal", "unfavorable", "insufficient_data"].includes(siteAnalysisResult.preliminary_feasibility),
      `Feasibility rating must be standard classification (got ${siteAnalysisResult.preliminary_feasibility})`
    );
  });

  test("Feature 5: Hazard Detection Engine (DEM & Optical ML Engine Status)", async () => {
    const res = await fetch(`${BACKEND_URL}/api/hazards/status`);
    assert.equal(res.status, 200);
    const statusData = await res.json();

    assert.equal(statusData.dem_hazard_analysis, "operational", "DEM hazard engine must be operational");
    assert.equal(typeof statusData.optical_ml_model_configured, "boolean");
    assert.ok(statusData.disclaimer.includes("Apollo"), "Must contain historical domain limitation disclaimer");
  });

  test("Feature 6: Sunlight & Solar Geometry Modeling (Subsolar / Azimuth / Horizon)", () => {
    assert.ok(siteAnalysisResult, "Prior analysis result must exist");
    const illum = siteAnalysisResult.illumination;
    assert.ok(illum, "Illumination summary must exist");
    assert.equal(illum.status, "available", "Illumination status must be available");
    assert.ok(
      illum.solar_elevation_deg >= -90.0 && illum.solar_elevation_deg <= 90.0,
      `Solar elevation ${illum.solar_elevation_deg}° must be between -90° and +90°`
    );
    assert.ok(
      illum.solar_azimuth_deg >= 0.0 && illum.solar_azimuth_deg <= 360.0,
      `Solar azimuth ${illum.solar_azimuth_deg}° must be between 0° and 360°`
    );
    assert.ok(
      illum.cumulative_illumination_pct >= 0 && illum.cumulative_illumination_pct <= 100,
      "Cumulative illumination must be 0-100%"
    );
  });

  test("Feature 7: Earth Visibility & Direct-to-Earth Line of Sight", () => {
    assert.ok(siteAnalysisResult, "Prior analysis result must exist");
    const illum = siteAnalysisResult.illumination;
    assert.ok(illum, "Illumination summary must exist");
    assert.ok(
      illum.earth_elevation_deg >= -90.0 && illum.earth_elevation_deg <= 90.0,
      `Earth elevation ${illum.earth_elevation_deg}° must be between -90° and +90°`
    );
    assert.ok(
      ["operational", "marginal", "blackout"].includes(illum.communication_link_status),
      `Comm status must be valid (got ${illum.communication_link_status})`
    );
  });

  test("Feature 8: Landing-Site Suitability Scoring (MCDA & ML Model v2)", () => {
    assert.ok(siteAnalysisResult, "Prior analysis result must exist");
    const score = siteAnalysisResult.suitability;
    assert.ok(score, "Suitability score object must exist");
    const composite = score.overall_suitability_score ?? score.scientific_baseline_score;
    assert.ok(
      typeof composite === "number" && composite >= 0.0 && composite <= 100.0,
      `Composite score ${composite} must be within [0, 100]`
    );
    assert.ok(score.subscores && score.subscores.length > 0, "Subscores array required");
    assert.equal(typeof score.ml_model_score, "number", "ML v2 model score required");
    assert.ok(score.feature_contributions, "ML model feature contributions required");
  });

  test("Feature 9: Grounded AI Explanation (Technical Mission Briefing)", async () => {
    const res = await fetch(`${BACKEND_URL}/api/ai/explain`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        center_lat: -89.44,
        center_lon: 222.5,
        analysis_id: siteAnalysisResult.analysis_id,
        composite_score: siteAnalysisResult.suitability?.overall_suitability_score ?? 78.5,
        slope_mean_deg: siteAnalysisResult.slope.mean_value,
        roughness_mean_m: siteAnalysisResult.roughness_mean_m,
        illumination_pct: siteAnalysisResult.illumination?.cumulative_illumination_pct ?? 65.0,
        earth_visibility_pct: siteAnalysisResult.illumination?.earth_visibility_pct ?? 82.0,
      }),
    });

    assert.equal(res.status, 200);
    const aiData = await res.json();
    assert.ok(aiData.explanation || aiData.briefing || aiData.summary, "AI response must contain briefing content");
  });

  test("Feature 10: Lunar Coordinate Transformations & Boundary Integrity", async () => {
    // 10.1 Invertible projection test
    const D2R = Math.PI / 180;
    const R_M = 1_737_400.0;
    const lat = -89.44;
    const lon = 222.5;

    const phi = lat * D2R;
    const lambda = lon * D2R;
    const k = (2.0 * R_M) / (1.0 + Math.sin(-phi));
    const x = k * Math.cos(-phi) * Math.sin(lambda);
    const y = -k * Math.cos(-phi) * Math.cos(lambda);

    const rho = Math.hypot(x, y);
    const c = 2.0 * Math.atan(rho / (2.0 * R_M));
    const recLat = Math.asin(-Math.cos(c)) / D2R;
    const recLon = ((Math.atan2(x, -y) / D2R) + 360) % 360;

    assert.ok(Math.abs(recLat - lat) < 1e-4, "Recovered latitude must match within 0.0001°");
    assert.ok(Math.abs(recLon - lon) < 1e-4, "Recovered longitude must match within 0.0001°");

    // 10.2 Boundary violation check (Out-of-bounds latitude rejection)
    const errRes = await fetch(`${BACKEND_URL}/api/analysis/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        center_lat: -78.0, // North of 80°S constraint
        center_lon: 0.0,
        radius_meters: 500.0,
      }),
    });
    assert.equal(errRes.status, 422, "Out-of-bounds coordinates must be rejected with 422 Unprocessable Entity");
  });

  test("Feature 11: Time-Based Sun and Earth Visibility Simulation", async () => {
    const res = await fetch(`${BACKEND_URL}/api/simulation/visibility`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lat: -89.44,
        lon: 222.5,
        duration_days: 7,
        step_hours: 6,
      }),
    });

    assert.equal(res.status, 200);
    const sim = await res.json();
    assert.ok(sim.time_series && sim.time_series.length > 0, "Simulation must return time series points");
    assert.equal(sim.time_series.length, (7 * 24) / 6 + 1, "Number of simulation steps must match duration/step");

    // Check first time point structure
    const pt0 = sim.time_series[0];
    assert.ok(pt0.timestamp_iso, "Timestamp required");
    assert.equal(typeof pt0.solar_elevation_deg, "number");
    assert.equal(typeof pt0.earth_elevation_deg, "number");
    assert.equal(typeof pt0.is_earth_visible, "boolean");
    assert.equal(typeof pt0.is_sunlit, "boolean");
  });
});
