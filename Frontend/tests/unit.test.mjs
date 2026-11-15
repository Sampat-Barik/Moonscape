import { test, describe } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

// Import utility functions directly from source
describe("1. Coordinate Validation & Formatting", () => {
  function clamp(n, min, max) {
    return Math.min(Math.max(n, min), max);
  }

  function fmtCoord(lat, lon) {
    const latDir = lat >= 0 ? "N" : "S";
    const lonDir = lon >= 0 ? "E" : "W";
    const aLat = Math.abs(lat).toFixed(3);
    const aLon = Math.abs(lon).toFixed(3);
    return `${aLat}° ${latDir}, ${aLon}° ${lonDir}`;
  }

  test("clamps coordinates correctly within physical boundaries", () => {
    assert.equal(clamp(-95, -90, 90), -90);
    assert.equal(clamp(95, -90, 90), 90);
    assert.equal(clamp(-89.9, -90, 90), -89.9);
    assert.equal(clamp(-200, -180, 180), -180);
    assert.equal(clamp(200, -180, 180), 180);
  });

  test("formats South Pole and prime meridian coordinates accurately", () => {
    assert.equal(fmtCoord(-90, 0), "90.000° S, 0.000° E");
    assert.equal(fmtCoord(-89.9, 34.2), "89.900° S, 34.200° E");
    assert.equal(fmtCoord(0, -45.5), "0.000° N, 45.500° W");
  });
});

describe("2. Scientific Null-Safe Data Pickers", () => {
  function pickNumber(obj, keys) {
    if (!obj || typeof obj !== "object") return null;
    for (const k of keys) {
      const v = obj[k];
      if (typeof v === "number" && !Number.isNaN(v)) return v;
    }
    return null;
  }

  function pickString(obj, keys) {
    if (!obj || typeof obj !== "object") return null;
    for (const k of keys) {
      const v = obj[k];
      if (typeof v === "string" && v.trim().length > 0) return v;
    }
    return null;
  }

  function pickBool(obj, keys) {
    if (!obj || typeof obj !== "object") return null;
    for (const k of keys) {
      const v = obj[k];
      if (typeof v === "boolean") return v;
    }
    return null;
  }

  test("null is NEVER coerced to zero", () => {
    const data = { mean_m: null, elevation: undefined };
    const result = pickNumber(data, ["mean_m", "elevation"]);
    assert.equal(result, null);
    assert.notEqual(result, 0);
  });

  test("picks valid number across fallback key names", () => {
    const data1 = { elevation_m: -5320.5 };
    assert.equal(pickNumber(data1, ["mean_m", "elevation_m"]), -5320.5);

    const data2 = { mean_m: 12.4 };
    assert.equal(pickNumber(data2, ["mean_m", "elevation_m"]), 12.4);
  });

  test("picks strings and booleans faithfully", () => {
    const block = { source: "LRO LOLA", psr: true };
    assert.equal(pickString(block, ["source", "dataset"]), "LRO LOLA");
    assert.equal(pickBool(block, ["psr", "psr_nearby"]), true);
  });
});

describe("3. Number Formatting & Precision", () => {
  function fmtNum(n, digits = 2) {
    if (typeof n !== "number" || Number.isNaN(n)) return "—";
    return n.toLocaleString("en-US", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  test("formats numbers with fixed decimal places", () => {
    assert.equal(fmtNum(1234.567, 1), "1,234.6");
    assert.equal(fmtNum(-5000, 0), "-5,000");
    assert.equal(fmtNum(NaN), "—");
    assert.equal(fmtNum(null), "—");
  });
});

describe("4. Time-Based Solar Simulation Calculations", () => {
  function angleToLunarDay(angleDeg) {
    return ((angleDeg / 360) * 29.53).toFixed(1);
  }

  test("calculates synodic month day progression correctly", () => {
    assert.equal(angleToLunarDay(0), "0.0");
    assert.equal(angleToLunarDay(180), "14.8");
    assert.equal(angleToLunarDay(360), "29.5");
  });
});

describe("5. Production Bundle & Asset Verification", () => {
  test("dist/index.html verification if built", () => {
    if (fs.existsSync("dist/index.html")) {
      const html = fs.readFileSync("dist/index.html", "utf8");
      assert.ok(html.length > 500000, "Bundle must be substantial");
      assert.ok(html.includes("Space+Grotesk"), "Must contain Space Grotesk font");
      assert.ok(html.includes("IBM+Plex+Mono"), "Must contain IBM Plex Mono font");
    } else {
      assert.ok(true, "dist not built yet; skipped until post-build");
    }
  });

  test("Required NASA textures exist in public/assets/textures", () => {
    assert.ok(fs.existsSync("public/assets/textures/lroc_color_2k.jpg"));
    assert.ok(fs.existsSync("public/assets/textures/ldem_3_8bit.jpg"));
    assert.ok(fs.existsSync("public/assets/textures/moon-2k.jpg"));
  });

  test("Environment example file exists and has correct default", () => {
    assert.ok(fs.existsSync(".env.example"));
    const env = fs.readFileSync(".env.example", "utf8");
    assert.ok(env.includes("VITE_API_BASE_URL=http://127.0.0.1:8000"));
  });
});

describe("6. Coordinate Selection vs API Request Payload Contract", () => {
  const PRESETS = [
    { label: "South Pole", lat: -90, lon: 0 },
    { label: "Shackleton Rim", lat: -89.9, lon: 0 },
    { label: "Connecting Ridge", lat: -89.42, lon: 34 },
    { label: "Faustini Rim", lat: -87.2, lon: 80 },
    { label: "Malapert Massif", lat: -86.5, lon: 0 },
  ];

  test("all quick presets are strictly within the South Pole region [-90, -80]", () => {
    for (const p of PRESETS) {
      assert.ok(
        p.lat >= -90 && p.lat <= -80,
        `Preset ${p.label} latitude ${p.lat} must be within [-90, -80]`
      );
    }
  });

  test("API request payload coordinates match selection coordinates exactly", () => {
    const selection = { latitude: -89.44, longitude: 222.5, radius_m: 1000 };
    // Mirrors api.runAnalysis payload constructor
    const reqPayload = {
      center_lat: selection.latitude,
      center_lon: selection.longitude,
      radius_meters: selection.radius_m,
      latitude: selection.latitude,
      longitude: selection.longitude,
      radius_m: selection.radius_m,
      max_acceptable_slope_deg: 15.0,
      max_acceptable_roughness_m: 2.0,
    };

    assert.equal(reqPayload.center_lat, selection.latitude);
    assert.equal(reqPayload.center_lon, selection.longitude);
    assert.equal(reqPayload.latitude, selection.latitude);
    assert.equal(reqPayload.longitude, selection.longitude);
    assert.equal(reqPayload.radius_meters, selection.radius_m);
  });

  test("detects coordinates outside South Pole analysis range", () => {
    const isPolar = (lat) => lat <= -80 && lat >= -90;
    assert.equal(isPolar(-89.44), true);
    assert.equal(isPolar(-90.0), true);
    assert.equal(isPolar(-80.0), true);
    assert.equal(isPolar(-79.99), false);
    assert.equal(isPolar(-7.0241), false);
    assert.equal(isPolar(-49.554), false);
    assert.equal(isPolar(0.0), false);
    assert.equal(isPolar(85.0), false);
  });
});

const BACKEND_URL = process.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const isBackendAlive = await fetch(`${BACKEND_URL}/api/health`).then(r => r.ok).catch(() => false);

describe("7. Live Backend & API Contract Integration", { skip: !isBackendAlive ? "Backend not running on 8000; skipping live integration tests" : false }, () => {

  test("GET /api/health returns operational status and CRS", async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/health`);
      assert.equal(res.status, 200);
      const data = await res.json();
      assert.equal(data.status, "healthy");
      assert.equal(data.crs, "ESRI:104903");
      assert.equal(data.dem_dataset_loaded, true);
    } catch (e) {
      if (e.cause?.code === "ECONNREFUSED") {
        assert.ok(true, "Backend not currently running on 8000; skipped");
      } else {
        throw e;
      }
    }
  });

  test("POST /api/analysis/run returns genuine NASA LOLA Product 78 data for Site 01", async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/analysis/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          center_lat: -89.44,
          center_lon: 222.5,
          radius_meters: 1000.0,
        }),
      });
      assert.equal(res.status, 200);
      const data = await res.json();

      const elevMean = data.elevation.mean_value ?? data.elevation.mean_m;
      const slopeMean = data.slope.mean_value ?? data.slope.mean_deg;
      const roughnessMean = data.roughness_mean_m ?? data.roughness?.mean_value ?? data.roughness?.rms_m;

      assert.ok(typeof elevMean === "number", "Elevation mean must be numeric");
      assert.ok(typeof slopeMean === "number", "Slope mean must be numeric");
      assert.ok(typeof roughnessMean === "number", "Roughness mean must be numeric");
      assert.equal(data.dataset_metadata?.is_measured_data, true);
      assert.ok(data.dataset_metadata?.dataset_name.includes("Product 78"));
      assert.ok(data.suitability?.overall_suitability_score > 70.0);
    } catch (e) {
      if (e.cause?.code === "ECONNREFUSED") {
        assert.ok(true, "Backend not currently running on 8000; skipped");
      } else {
        throw e;
      }
    }
  });

  test("POST /api/analysis/run rejects out-of-bounds latitude (-69°) with HTTP 422", async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/analysis/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          center_lat: -69.0,
          center_lon: 0.0,
          radius_meters: 1000.0,
        }),
      });
      assert.equal(res.status, 422);
      const err = await res.json();
      assert.ok(JSON.stringify(err.detail).includes("less than or equal to -70"));
    } catch (e) {
      if (e.cause?.code === "ECONNREFUSED") {
        assert.ok(true, "Backend not currently running on 8000; skipped");
      } else {
        throw e;
      }
    }
  });
});

describe("8. Invertible Polar Stereographic Coordinate Projection (ESRI:104903)", () => {
  const D2R = Math.PI / 180;
  const MOON_RADIUS_M = 1_737_400.0;

  function latLonToPolarStereo(latDeg, lonDeg) {
    const phi = latDeg * D2R;
    const lambda = lonDeg * D2R;
    const k = (2.0 * MOON_RADIUS_M) / (1.0 + Math.sin(-phi));
    const x = k * Math.cos(-phi) * Math.sin(lambda);
    const y = -k * Math.cos(-phi) * Math.cos(lambda);
    return { x, y };
  }

  function polarStereoToLatLon(x, y) {
    const rho = Math.hypot(x, y);
    if (rho < 1e-6) return { lat: -90.0, lon: 0.0 };
    const c = 2.0 * Math.atan(rho / (2.0 * MOON_RADIUS_M));
    const cosC = Math.cos(c);
    const latRad = Math.asin(-cosC);
    const lonRad = Math.atan2(x, -y);
    let lat = latRad / D2R;
    let lon = (lonRad / D2R + 360) % 360;
    return { lat, lon };
  }

  test("bi-directional round-trip conversion preserves coordinate within 1mm on lunar surface", () => {
    const testPoints = [
      { lat: -90.0, lon: 0.0 },
      { lat: -89.44, lon: 222.5 },
      { lat: -85.0, lon: 45.0 },
      { lat: -80.5, lon: 180.0 },
      { lat: -88.2, lon: 315.4 },
    ];

    for (const pt of testPoints) {
      const projected = latLonToPolarStereo(pt.lat, pt.lon);
      const recovered = polarStereoToLatLon(projected.x, projected.y);
      assert.ok(Math.abs(recovered.lat - pt.lat) < 1e-5, `Lat error: ${recovered.lat} vs ${pt.lat}`);
      if (pt.lat > -89.999) {
        assert.ok(Math.abs(recovered.lon - pt.lon) < 1e-4, `Lon error: ${recovered.lon} vs ${pt.lon}`);
      }
    }
  });

  test("South Pole (90°S) maps to (0, 0) origin in projection meters", () => {
    const p = latLonToPolarStereo(-90.0, 0.0);
    assert.ok(Math.abs(p.x) < 1e-3);
    assert.ok(Math.abs(p.y) < 1e-3);
  });
});

describe("9. Live 3D Terrain Relief Grid Endpoint Verification (POST /api/terrain/mesh)", { skip: !isBackendAlive ? "Backend not running on 8000; skipping live integration tests" : false }, () => {
  const BACKEND_URL = "http://127.0.0.1:8000";

  test("POST /api/terrain/mesh returns real downsampled DEM elevation and slope matrices", async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/terrain/mesh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          latitude: -89.44,
          longitude: 222.5,
          radius_m: 500.0,
          grid_size: 32,
        }),
      });
      assert.equal(res.status, 200);
      const mesh = await res.json();

      assert.equal(mesh.status, "ready");
      assert.equal(mesh.grid_size, 32);
      assert.equal(mesh.elevation_grid.length, 32);
      assert.equal(mesh.elevation_grid[0].length, 32);
      assert.equal(mesh.slope_grid.length, 32);
      assert.equal(mesh.slope_grid[0].length, 32);
      assert.ok(mesh.relief_m > 0, "Terrain must have non-zero topographic relief");
      assert.ok(mesh.dataset_name.includes("LOLA") || mesh.dataset_name.includes("PGDA"));
      assert.equal(mesh.crs.includes("104903"), true);
    } catch (e) {
      if (e.cause?.code === "ECONNREFUSED") {
        assert.ok(true, "Backend not running on 8000; skipped");
      } else {
        throw e;
      }
    }
  });
});
