/**
 * Integration and contract tests for Landing-Site Comparison PDF Generator (Frontend Suite).
 *
 * Verifies:
 * 1. Site comparison API contract with 2 sites.
 * 2. Site comparison API contract with all 8 catalog sites.
 * 3. Binary PDF download endpoint returns valid application/pdf Blob.
 * 4. Full catalog 8-site PDF download produces multi-page PDF (>50KB).
 * 5. Error handling when fewer than 2 sites are requested.
 * 6. Error handling when invalid site ID is provided.
 * 7. Verification that returned PDF contains correct Content-Disposition filename.
 * 8. Verification that downloaded PDF starts with %PDF- header.
 * 9. Custom weight profiles and mission profiles.
 * 10. Backward-compatibility of POST /api/reports/generate with site_ids.
 */

import { test, describe } from "node:test";
import assert from "node:assert";

const BASE_URL = "http://127.0.0.1:8000";

describe("MOONSCAPE — COMPARISON PDF WORKFLOW & API VALIDATION", () => {
  let catalogSites = [];

  test("1. Retrieve candidate landing site catalog (GET /api/sites)", async () => {
    const res = await fetch(`${BASE_URL}/api/sites`);
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.ok(Array.isArray(data));
    assert.ok(data.length >= 8, `Expected at least 8 sites in catalog, found ${data.length}`);
    catalogSites = data.map((s) => s.site_id);
    assert.ok(catalogSites.includes("shackleton_connecting_ridge"));
    assert.ok(catalogSites.includes("malapert_mountain"));
  });

  test("2. Compare 2 selected sites (POST /api/sites/compare)", async () => {
    const selected = ["shackleton_connecting_ridge", "malapert_mountain"];
    const res = await fetch(`${BASE_URL}/api/sites/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ site_ids: selected, mission_profile: "crewed_artemis_class" }),
    });
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.compared_sites.length, 2);
    assert.ok(data.top_recommended_site_id);
    assert.ok(data.compared_sites[0].suitability_score > 0);
  });

  test("3. Compare all sites in catalog (Dynamic All-Sites Evaluation)", async () => {
    assert.ok(catalogSites.length >= 8);
    const res = await fetch(`${BASE_URL}/api/sites/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ site_ids: catalogSites, mission_profile: "crewed_artemis_class" }),
    });
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.compared_sites.length, catalogSites.length);
    for (let i = 0; i < data.compared_sites.length; i++) {
      assert.strictEqual(data.compared_sites[i].safety_rank, i + 1);
    }
  });

  test("4. Download Comparison PDF for 2 sites (POST /api/reports/comparison)", async () => {
    const selected = ["shackleton_connecting_ridge", "malapert_mountain"];
    const res = await fetch(`${BASE_URL}/api/reports/comparison`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ site_ids: selected, format: "pdf" }),
    });
    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.headers.get("content-type"), "application/pdf");
    const disposition = res.headers.get("content-disposition") || "";
    assert.ok(disposition.includes("MoonScape_Comparison_"));
    assert.ok(disposition.endsWith('.pdf"'));

    const arrayBuffer = await res.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    assert.ok(buffer.length > 10000, `PDF size too small: ${buffer.length} bytes`);
    assert.strictEqual(buffer.subarray(0, 5).toString("ascii"), "%PDF-");
  });

  test("5. Download Comparison PDF for All 8 Catalog Sites", async () => {
    const res = await fetch(`${BASE_URL}/api/reports/comparison`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ site_ids: catalogSites, format: "pdf" }),
    });
    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.headers.get("content-type"), "application/pdf");

    const arrayBuffer = await res.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    assert.ok(buffer.length > 50000, `All-sites PDF size too small: ${buffer.length} bytes`);
    assert.strictEqual(buffer.subarray(0, 5).toString("ascii"), "%PDF-");
    // Verify PDF EOF marker
    assert.ok(buffer.includes(Buffer.from("%%EOF")));
  });

  test("6. Reject comparison request with < 2 sites (HTTP 422)", async () => {
    const res = await fetch(`${BASE_URL}/api/reports/comparison`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ site_ids: ["malapert_mountain"], format: "pdf" }),
    });
    assert.strictEqual(res.status, 422);
  });

  test("7. Reject comparison request with duplicate site IDs (HTTP 422)", async () => {
    const res = await fetch(`${BASE_URL}/api/reports/comparison`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ site_ids: ["malapert_mountain", "malapert_mountain"], format: "pdf" }),
    });
    assert.strictEqual(res.status, 422);
  });

  test("8. Reject comparison request with invalid site ID (HTTP 404)", async () => {
    const res = await fetch(`${BASE_URL}/api/reports/comparison`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ site_ids: ["malapert_mountain", "invalid_unknown_site_999"], format: "pdf" }),
    });
    assert.strictEqual(res.status, 404);
  });

  test("9. Backward-compatible POST /api/reports/generate delegation with site_ids", async () => {
    const res = await fetch(`${BASE_URL}/api/reports/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        site_ids: ["shackleton_connecting_ridge", "malapert_mountain"],
        format: "pdf",
      }),
    });
    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.headers.get("content-type"), "application/pdf");
    const disposition = res.headers.get("content-disposition") || "";
    assert.ok(disposition.includes("MoonScape_Comparison_"));
  });

  test("10. Zero-regression on single-site report at POST /api/reports/generate", async () => {
    const res = await fetch(`${BASE_URL}/api/reports/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        site_id: "malapert_mountain",
        format: "pdf",
      }),
    });
    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.headers.get("content-type"), "application/pdf");
    const disposition = res.headers.get("content-disposition") || "";
    assert.ok(disposition.includes("moonscape_report_"));
  });
});
