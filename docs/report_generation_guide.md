# Moonscape Scientific Report Generator Guide (Phase 8)
**Document Version:** 1.0-phase8  
**Module:** `backend/services/report_generator.py`  
**Classification:** Scientific Technical Documentation & API Architecture Guide  

---

## 1. Overview & Architectural Principles

The **Moonscape Scientific Report Generator** compiles multi-source planetary data, slope distributions, roughness statistics, solar illumination conditions, hazard detections, and transparent multi-criteria suitability scoring into publication-quality mission analysis reports.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Web Layer                             │
│                    POST /api/reports/generate                          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         ReportGenerator                                │
│  - Analysis Record Retrieval (from AnalysisStore by analysis_id)       │
│  - Assemble 19 Mandated Scientific Elements                            │
│  - Multi-Format Rendering: JSON, PDF, Markdown, and HTML               │
└───────────────┬───────────────────────────────────┬────────────────────┘
                │ format="json"                     │ format="pdf"
                ▼                                   ▼
┌───────────────────────────────────┐   ┌────────────────────────────────┐
│   Structured JSON Report (200)    │   │  Downloadable Binary PDF (200) │
│  - 19 Typed Scientific Elements   │   │  - ReportLab Multi-Page Layout │
│  - Machine-readable summary       │   │  - NASA Blue Styling & Tables  │
└───────────────────────────────────┘   └────────────────────────────────┘
```

### Key Engineering Invariants
1. **Never Recalculate Measurements:** The report generator is strictly an assembly and rendering engine. It pulls verified measurements directly from completed analysis records in `AnalysisStore` without re-running CPU-intensive Horn gradient or ray-tracing operators.
2. **Comprehensive 19-Element Schema:** Every report systematically incorporates 19 standard scientific sections, ensuring compliance with lunar exploration mission planning standards.
3. **Downloadable PDF Streaming:** High-resolution PDF reports are generated on-the-fly using ReportLab and returned directly as an HTTP attachment (`application/pdf`).
4. **Resilient to Missing Data:** If certain factors are unmeasured (e.g., optical boulder hazard models not run or illumination data unavailable), the report generator does not crash. It accurately reports them as `"unavailable"` or `"unmeasured"` and explicitly itemizes them under **Missing Data** and **Limitations**.

---

## 2. The 19 Mandated Scientific Elements

Every generated report contains:

1. **Report Title & Generation Timestamp:** Human-readable and ISO-8601 UTC timestamps.
2. **Analysis ID:** Traceable identifier linking back to the spatial analysis run (e.g., `analysis_001` or `ANL-XXXXXXXX`).
3. **Selected Lunar Coordinates:** Geodetic Latitude and Longitude in degrees and direction formatted (e.g., `89.4400° S, 222.5000° E`).
4. **Analysis Radius:** Physical distance bounded in meters (e.g., `1000.0 m`).
5. **Elevation Measurements:** Min, max, mean, relief variation, standard deviation, and vertical reference datum ($R = 1737.4\text{ km}$ lunar sphere).
6. **Slope Measurements:** Min, max, mean, median, standard deviation, calculation operator (Horn 1981), and slope distribution breakdown ($\le 5^\circ$, $5\text{--}10^\circ$, $10\text{--}15^\circ$, $>15^\circ$).
7. **Roughness Measurements:** Mean RMS roughness, peak roughness, evaluation baseline ($15\text{ m}$), and safe touchdown area fraction ($91.0\%$).
8. **Illumination Information:** Cumulative illumination %, instantaneous sunlit fraction, permanently shadowed region (PSR) status, estimated surface temperature (Kelvin), and thermal secondary balance caveat.
9. **Crater & Rock Detection Results:** Detected counts, detection status, severity assessment, and spatial resolution constraints.
10. **Preliminary Suitability Score:** Composite MCDA score ($0\text{--}100$), preliminary category (Higher, Moderate, Lower, Insufficient data), and score coverage percentage.
11. **Factor Breakdown Table:** Transparent matrix of raw measurements, normalized subscores, weights, and weighted contributions.
12. **Positive Factors:** Enumerated list of favourable landing, stability, and power conditions.
13. **Risk Factors:** Enumerated list of operational hazards (slopes $>10^\circ$, sub-pixel boulders, shadow occultation).
14. **Data Sources:** NASA LRO LOLA product name, spatial resolution ($5\text{ m/px}$ or $80\text{ m/px}$), and CRS (`ESRI:104903`).
15. **Methodology:** Documented computational algorithms (Horn gradient, RMS residual filter, DE421 ephemeris, MCDA v2.0-phase6).
16. **Missing Data:** Explicit list of unmeasured or unprovided factors.
17. **Measurement Uncertainties:** Instrument vertical accuracy ($\pm 1.0\text{ m}$), horizontal resolution limit, and bilinear interpolation error.
18. **Operational Limitations & Caveats:** Screening indicator disclaimer, flight qualification boundary, and ephemeris sensitivity.
19. **Final Preliminary Conclusion:** Clear executive recommendation for mission planners.

---

## 3. Supported Export Formats

### 1. JSON (`format: "json"`)
Returns the complete `ReportGenerateResponse` object with `report_data` containing all 19 typed sub-objects for programmatic consumption by the frontend application.

### 2. PDF (`format: "pdf"`)
Generates a multi-page, formatted PDF document containing:
- NASA Deep Slate Blue header banner with document metadata.
- Two-column Executive Summary box with suitability pill badge.
- Formatted tables for Topographic Elevation & Slope Breakdown.
- Solar Illumination and Permanently Shadowed Region (PSR) status.
- Multi-Criteria Decision Analysis (MCDA) factor breakdown table.
- Bulleted operational advantages vs. risks.
- Data source attribution and scientific disclaimer footer.

### 3. Markdown & HTML (`format: "markdown"` / `format: "html"`)
Produces formatted Markdown text or a standalone HTML file with inline CSS styling for direct web previewing.

---

## 4. API Request & Verification Examples

### Example: Generate JSON Report
```http
POST /api/reports/generate
Content-Type: application/json

{
  "analysis_id": "analysis_001",
  "format": "json"
}
```

### Example: Download PDF Report
```http
POST /api/reports/generate
Content-Type: application/json

{
  "analysis_id": "analysis_001",
  "format": "pdf"
}
```
*Returns binary `application/pdf` stream with `Content-Disposition: attachment; filename="moonscape_report_analysis_001.pdf"`.*
