import { test, describe } from "node:test";
import assert from "node:assert/strict";

const BACKEND_URL = "http://127.0.0.1:8000";
const isBackendAlive = await fetch(`${BACKEND_URL}/api/health`).then(r => r.ok).catch(() => false);

describe("MOONSCAPE — DASHBOARD SCIENTIFIC PIPELINE & ADAPTER VALIDATION", { skip: !isBackendAlive ? "Backend not running on 8000; skipping live integration tests" : false }, () => {
  test("Slope P95 is returned and matches scientific range", async () => {
    const res = await fetch(`${BACKEND_URL}/api/analysis/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        center_lat: -87.1,
        center_lon: 77.0,
        radius_meters: 1000.0,
      }),
    });
    assert.equal(res.status, 200);
    const data = await res.json();
    assert.ok(data.slope, "Slope block must be present");
    assert.equal(typeof data.slope.p95_value, "number", "p95_value must be a number");
    assert.ok(data.slope.p95_value <= data.slope.max_value, "P95 slope must be <= max slope");
    assert.ok(data.slope.p95_value >= data.slope.min_value, "P95 slope must be >= min slope");
  });

  test("Roughness baseline and method are included in analysis", async () => {
    const res = await fetch(`${BACKEND_URL}/api/analysis/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        center_lat: -87.1,
        center_lon: 77.0,
        radius_meters: 1000.0,
      }),
    });
    const data = await res.json();
    assert.equal(typeof data.roughness_mean_m, "number");
    assert.equal(typeof data.roughness_baseline_m, "number");
    assert.ok(data.roughness_baseline_m > 0);
    assert.ok(data.roughness_method.includes("RMS"));
  });

  test("Illumination contains duration, Earth comm status, and next sunset event", async () => {
    const res = await fetch(`${BACKEND_URL}/api/analysis/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        center_lat: -87.1,
        center_lon: 77.0,
        radius_meters: 1000.0,
      }),
    });
    const data = await res.json();
    const il = data.illumination;
    assert.ok(il, "Illumination must exist");
    assert.equal(typeof il.cumulative_illumination_pct, "number");
    assert.equal(typeof il.instantaneous_sunlit_fraction_pct, "number");
    assert.equal(typeof il.solar_elevation_deg, "number");
    assert.ok(["operational", "marginal", "blackout"].includes(il.communication_link_status));
    assert.ok(il.next_sunset_iso === null || typeof il.next_sunset_iso === "string");
  });

  test("Candidate detection provides resolution warning and valid schema", async () => {
    const res = await fetch(`${BACKEND_URL}/api/sites/detect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        center_lat: -87.1,
        center_lon: 77.0,
        search_radius_meters: 1000.0,
        min_landing_diameter_meters: 50.0,
      }),
    });
    assert.equal(res.status, 200);
    const data = await res.json();
    assert.ok(["success", "no_sites_found"].includes(data.status));
    assert.equal(typeof data.total_sites_detected, "number");
    assert.ok(Array.isArray(data.candidate_zones));
    assert.ok(data.warnings.some((w) => w.includes("coarser than requested minimum landing diameter")));
  });

  test("Visibility simulation accepts center_lat / center_lon aliases and returns time series", async () => {
    const res = await fetch(`${BACKEND_URL}/api/simulation/visibility`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        center_lat: -87.1,
        center_lon: 77.0,
        duration_days: 3.0,
        step_hours: 2.0,
      }),
    });
    assert.equal(res.status, 200);
    const data = await res.json();
    assert.ok(data.total_steps > 0);
    assert.equal(data.time_series.length, data.total_steps);
    assert.ok(data.sunlight_percentage >= 0 && data.sunlight_percentage <= 100);
    assert.ok(data.earth_comm_percentage >= 0 && data.earth_comm_percentage <= 100);
  });
});
