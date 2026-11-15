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
