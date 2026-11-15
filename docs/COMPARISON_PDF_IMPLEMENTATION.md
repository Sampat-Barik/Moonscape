# MOONSCAPE — COMPREHENSIVE LANDING-SITE COMPARISON PDF GENERATOR
## Architecture, Technical Specification & Implementation Guide

**Document Version:** 1.0.0  
**Date:** 2026-11-15  
**System Component:** Phase 8 Scientific Report Generation Extension  
**Sample PDF Location:** `docs/samples/MoonScape_Comparison_Sample_8Sites.pdf`  

---

## 1. Executive Summary

The MoonScape Landing-Site Comparison PDF Generator extends the existing single-site reporting infrastructure into a multi-page, publication-grade comparative mission evaluation engine. Planetary scientists and flight planners can evaluate 2 or more candidate landing sites side-by-side or trigger a full 8-site comparative assessment across the lunar South Pole (latitudes $-90^\circ$ to $-75^\circ$S).

The system reuses ReportLab 5.1.0, Matplotlib 3.11.2, and existing multi-criteria evaluation models to synthesize high-resolution charts, master engineering matrices, photometric/telemetry tables, individual candidate dossiers, and verified NASA/ISRO dataset citations into a cohesive, uncompressed PDF document without introducing competing libraries or breaking existing single-site report generation.

---

## 2. Modified & Created Files

| File Path | Role | Description |
|---|---|---|
| `Backend/app/schemas/report.py` | Schema Extension | Added `ComparisonReportRequest`, `ComparisonReportResponse`, and extended `ReportGenerateRequest` with optional multi-site `site_ids`. |
| `Backend/app/services/comparison_report_generator.py` | Service (New) | Implemented `ComparisonReportGenerator` with `ComparisonNumberedCanvas`, in-memory Matplotlib chart rendering, 10-page report flow, and uncompressed text streams. |
| `Backend/app/routes/reports.py` | Route Endpoint | Added dedicated `POST /api/reports/comparison` endpoint with dynamic date filename attachment, plus delegation in `POST /api/reports/generate`. |
| `Frontend/src/services/api.ts` | API Client | Added `api.downloadComparisonPdf(siteIds, missionProfile, customWeights)` handling binary Blobs, error extraction, and object URL downloads. |
| `Frontend/src/components/SiteComparison.tsx` | UI Component | Integrated `Compare All Sites` dynamic catalog action, `Download Comparison PDF` button with spinner and disabled states, and error alerts. |
| `Backend/tests/test_comparison_report.py` | Test Suite (New) | 20 automated tests covering multi-site PDF compilation, error states, null metric handling, filename headers, and regression. |
| `Frontend/tests/comparison_workflow.test.mjs` | Test Suite (New) | 10 end-to-end integration tests verifying API contracts, dynamic catalog selection, binary downloads, and zero regressions. |
| `docs/samples/MoonScape_Comparison_Sample_8Sites.pdf` | Verification Artifact | 10-page sample PDF comparing all 8 candidate landing sites (186,849 bytes). |

---

## 3. API Endpoints & Request/Response Contracts

### 3.1 Dedicated Endpoint: `POST /api/reports/comparison`

Generates a multi-site comparative assessment in PDF, JSON, Markdown, or HTML format.

#### Request Schema (`ComparisonReportRequest`)
```json
{
  "site_ids": ["shackleton_connecting_ridge", "malapert_mountain"],
  "mission_profile": "crewed_artemis_class",
  "custom_weights": {
    "slope": 0.35,
    "illumination": 0.25,
    "communication": 0.20,
    "science": 0.20
  },
  "mission_title": "MoonScape Lunar South Pole Comparative Landing Site Assessment",
  "format": "pdf"
}
```

#### Validation Rules:
- `site_ids`: Must contain at least 2 distinct landing site IDs. Duplicate IDs are rejected with HTTP 422.
- Unknown site IDs are validated against the memory catalog and rejected with HTTP 404.
- `format`: One of `pdf` (default), `json`, `markdown`, or `html`.

#### Response:
- **PDF Format (`format="pdf"`):**
  - `Content-Type: application/pdf`
  - `Content-Disposition: attachment; filename="MoonScape_Comparison_YYYY-MM-DD.pdf"`
  - Binary PDF stream starting with `%PDF-` and terminating with `%%EOF`.
- **JSON Format (`format="json"`):**
  - Returns `ComparisonReportResponse` containing report metadata, rankings, and summary statistics.

---

### 3.2 Backward-Compatible Endpoint: `POST /api/reports/generate`

The existing single-site endpoint was extended with zero-regression delegation:
- When called with single-site parameters (`analysis_id` or `site_id`), it executes the existing 19-element single-site report workflow.
- When called with `site_ids` containing $\ge 2$ sites, it automatically delegates to `comparison_report_generator`, returning the comparative PDF with full backward compatibility.

---

## 4. Multi-Page PDF Document Structure

The comparison report conforms to a strict monochrome scientific dossier aesthetic:

1. **Page 1 — Cover Page:**
   - Formal header: `MOONSCAPE | LUNAR SOUTH POLE COMPARATIVE LANDING SITE ASSESSMENT`.
   - Subtitle: `A Multi-Criteria Topographic, Photometric, Hazard & Orbital Accessibility Analysis`.
   - Metadata grid: Report ID, generation timestamp (UTC), candidate count, mission profile, and weight matrix.
   - Regulatory and educational research disclaimer box.
   - Suppresses running headers and footers.

2. **Page 2 — Executive Summary:**
   - Evaluated candidate site count and South Pole geographic envelope.
   - Primary recommended site identification with composite score and engineering constraint status.
   - Primary alternative candidate evaluation.
   - Category-by-category narrative summaries: topographic variations, surface hazard distribution, and photometric/Earth visibility coverage.

3. **Page 3 — Master Candidate Comparison Table:**
   - Formatted tabular matrix containing all evaluated candidates.
   - Columns: Site Name, Coordinates, Elevation (m), Mean Slope (°), Estimated Peak Slope (°), RMS Roughness (15m baseline), Sunlit Fraction (%), Earth Comms (%), Composite Score, Safety Rank, and Hard Constraint Status (`PASSED` / `VIOLATION`).
   - Uses `repeatRows=1` for repeated column headers if pages overflow.

4. **Page 4 — Multi-Criteria Suitability Ranking:**
   - In-memory Matplotlib horizontal bar chart (150 DPI) displaying candidate scores and safety ranks.
   - Visual distinction between sites passing hard constraints (dark charcoal `#1F2937`) and sites with violations (muted slate `#9CA3AF`).
   - Weight configuration breakdown and Monte Carlo perturbation uncertainty notes ($\pm 2.4$ points).

5. **Page 5 — Topographic Relief & Slope Gradient Comparison:**
   - Grouped bar chart comparing mean slope vs estimated peak slope across all evaluated candidates.
   - Benchmark threshold lines: Artemis nominal maximum slope ($8.0^\circ$, dashed red) and Apollo lunar lander limit ($12.0^\circ$, dotted dark red).
   - Terrain slope classification criteria description (Ideal, Marginal, Critical/Hazardous).

6. **Page 6 — Surface Hazards & Detection Provenance:**
   - Multi-sensor hazard synthesis table clearly differentiating deterministic DEM hazards from optical object-based detections.
   - Columns: Candidate Site, DEM Hazard Status, Craters Identified, Boulder Scan Status, and Optical Coverage.
   - Explicit disclaimer regarding shadowed optical frames (missing data is labeled as shadow-masked/unavailable rather than assumed to be zero hazards).

7. **Page 7 — Illumination & Direct Earth Visibility:**
   - Telemetry table evaluating candidates over a standardized lunar synodic cycle ($29.53$ Earth days).
   - Columns: Site Name, Sunlit Fraction (%), Cumulative Darkness Duration (hours), Earth Visibility (%), and Communication Blackout Duration (hours).

8. **Pages 8–9 — Individual Candidate Site Dossiers:**
   - Structured 2-column technical parameter boxes for each evaluated site: coordinates, datum elevation, slope distribution, illumination, Earth visibility, constraint status, and sensor provenance.
   - Itemized operational assessment: primary mission strengths and engineering vulnerabilities.

9. **Page 10 — Scientific Methodology & Dataset Provenance:**
   - Mathematical operator specifications: Horn (1981) 3x3 finite-difference kernel on LOLA SHDR DEMs, 15m baseline RMS height deviation, and SPICE ephemerides.
   - Computer vision hazard model specifications: YOLOv8n polar-trained neural detector on LROC NAC frames.
   - Formal bibliographic citations for NASA LOLA, NASA LROC NAC, NASA PGDA / PDS Geosciences, NASA Diviner, JPL Horizons, and ISRO Chandrayaan-2/3 TMC-2 / OHRC datasets.
   - Final institutional research disclaimer.

---

## 5. Frontend UI Integration

The Comparison page at `http://localhost:5173/#/compare` was enhanced with intuitive controls adhering to the existing monochrome design system:

1. **Dynamic "Compare All Sites" Action:**
   - Button reads `Compare All Sites (${sites.length})`.
   - Derives the candidate count directly from `api.getSites()` (8 sites currently in catalog).
   - Automatically selects all registered catalog sites and initiates comparative analysis.

2. **"Download Comparison PDF" Action:**
   - Positioned in the comparative matrix header bar alongside API telemetry chips.
   - Displays a download icon, clear label, and active loading state (`Generating Comparison PDF...` with spinning SVG indicator).
   - Automatically disabled when $< 2$ sites are compared or while generation is in flight to prevent accidental concurrent requests.
   - Clean dismissal-capable error alert banner if the network request fails.

3. **Memory & Resource Management:**
   - Binary PDF responses are parsed as Blobs via `window.URL.createObjectURL(blob)`.
   - Download is triggered programmatically via a temporary DOM anchor.
   - Temporary object URLs are immediately revoked with `window.URL.revokeObjectURL(url)` to prevent browser memory leaks.
