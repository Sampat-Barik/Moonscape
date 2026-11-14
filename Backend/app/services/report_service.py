"""Report generation service compiling landing-site metrics, hazard risks, and AI synthesis."""

from datetime import datetime, timezone
import json
import uuid
from typing import Any, Dict

from app.core.constants import SCIENTIFIC_SAFETY_DISCLAIMER
from app.schemas.ai import AIExplainRequest
from app.schemas.hazard import HazardPredictRequest
from app.schemas.report import ReportGenerateRequest, ReportGenerateResponse
from app.schemas.scoring import ScoreRequest
from app.services.ai_service import ai_service
from app.services.hazard_service import hazard_service
from app.services.scoring_service import scoring_service
from app.services.site_service import site_service


class ReportService:
    """Compiles multi-source landing assessments into structured mission analysis reports."""

    def generate_report(self, req: ReportGenerateRequest) -> ReportGenerateResponse:
        """Assembles a mission analysis report in JSON, Markdown, or HTML format."""
        report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
        generated_at = datetime.now(timezone.utc).isoformat()

        site = site_service.get_site_by_id(req.site_id)
        if not site:
            raise ValueError(f"Site '{req.site_id}' not found in candidate catalog.")

        # 1. Score
        score_resp = scoring_service.compute_score(ScoreRequest(site_id=req.site_id))

        # 2. Hazard Prediction
        hazard_resp = hazard_service.predict_hazards(
            HazardPredictRequest(
                center_lat=site.latitude,
                center_lon=site.longitude,
                radius_meters=1500.0,
            )
        )

        # 3. AI Scientific Explanation (if requested)
        ai_resp = None
        if req.include_ai_narrative:
            ai_resp = ai_service.explain_landing_site(
                AIExplainRequest(
                    site_id=req.site_id,
                    latitude=site.latitude,
                    longitude=site.longitude,
                )
            )

        structured_summary: Dict[str, Any] = {
            "site_id": site.site_id,
            "site_name": site.name,
            "coordinates": {"latitude": site.latitude, "longitude": site.longitude},
            "elevation_m": site.elevation_m,
            "mean_slope_deg": site.mean_slope_deg,
            "illumination_pct": site.illumination_pct,
            "earth_visibility_pct": site.earth_visibility_pct,
            "overall_suitability_score": score_resp.overall_suitability_score,
            "suitability_category": score_resp.suitability_category,
            "hazard_level": hazard_resp.overall_hazard_level,
            "total_hazards_detected": hazard_resp.total_hazards_detected,
        }

        # Format content
        fmt = req.output_format.lower()
        if fmt == "json":
            content_dict = {
                "report_id": report_id,
                "generated_at": generated_at,
                "mission_title": req.mission_title,
                "site_metadata": site.model_dump(),
                "suitability_scoring": score_resp.model_dump(),
                "hazard_assessment": hazard_resp.model_dump(),
                "ai_scientific_explanation": ai_resp.model_dump() if ai_resp else None,
                "disclaimer": SCIENTIFIC_SAFETY_DISCLAIMER,
            }
            content = json.dumps(content_dict, indent=2)

        elif fmt == "html":
            content = self._render_html_report(
                report_id=report_id,
                title=req.mission_title or "Lunar Landing Site Assessment",
                site=site,
                score=score_resp,
                hazard=hazard_resp,
                ai=ai_resp,
                generated_at=generated_at,
            )

        else:  # Default to Markdown
            content = self._render_markdown_report(
                report_id=report_id,
                title=req.mission_title or "Lunar Landing Site Assessment",
                site=site,
                score=score_resp,
                hazard=hazard_resp,
                ai=ai_resp,
                generated_at=generated_at,
            )

        return ReportGenerateResponse(
            report_id=report_id,
            generated_at=generated_at,
            mission_title=req.mission_title or "Lunar Landing Site Assessment",
            site_id=site.site_id,
            site_name=site.name,
            output_format=fmt,
            content=content,
            structured_summary=structured_summary,
            disclaimer=SCIENTIFIC_SAFETY_DISCLAIMER,
        )

    @staticmethod
    def _render_markdown_report(report_id, title, site, score, hazard, ai, generated_at) -> str:
        md = [
            f"# {title}",
            f"**Candidate Site:** {site.name} (`{site.site_id}`)  ",
            f"**Report ID:** `{report_id}` | **Generated:** `{generated_at}`  ",
            "",
            "---",
            "",
            "## 1. Executive Site Overview",
            f"- **Target Mission:** {site.target_mission}",
            f"- **Location:** Latitude `{site.latitude}°`, Longitude `{site.longitude}°` (Lunar South Pole)",
            f"- **Elevation:** `{site.elevation_m} m` (relative to 1,737.4 km lunar sphere)",
            f"- **Average Slope:** `{site.mean_slope_deg}°`",
            f"- **Annual Solar Illumination:** `{site.illumination_pct}%`",
            f"- **Direct Earth Line-of-Sight:** `{site.earth_visibility_pct}%`",
            f"- **Science Objective:** {site.scientific_value}",
            "",
            "## 2. Suitability Scoring & Decision Matrix",
            f"**Overall Score:** `{score.overall_suitability_score}/100` — **Classification: {score.suitability_category}**",
            "",
            "| Evaluation Factor | Raw Measurement | Normalized Subscore | Weight | Weighted Score |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for sub in score.subscores:
            md.append(
                f"| {sub.criterion} | {sub.raw_measurement} {sub.unit} | {sub.normalized_subscore}/100 | {sub.weight} | {sub.weighted_contribution} |"
            )

        concerns_list = [f"- {c}" for c in score.critical_concerns] if score.critical_concerns else ["- None identified"]
        md.extend([
            "",
            "**Key Advantages:**",
            *[f"- {adv}" for adv in score.key_advantages],
            "",
            "**Critical Concerns:**",
            *concerns_list,
            "",
            "## 3. Surface Hazard Assessment",
            f"- **Overall Hazard Level:** `{hazard.overall_hazard_level.upper()}`",
            f"- **Detected Features:** `{hazard.craters_count}` craters, `{hazard.boulders_count}` boulder clusters, `{hazard.steep_slope_cells}` steep slope zones",
            f"- **Shadow / Cold Trap Coverage:** `{hazard.shadow_coverage_pct}%`",
            "",
        ])

        if ai:
            md.extend([
                "## 4. AI Scientific Advisory & Mission Synthesis",
                f"*{ai.executive_summary}*",
                "",
                "### Geomorphology & Landing Mechanics",
                ai.geomorphology_assessment,
                "",
                "### Thermal & Power Environment",
                ai.thermal_and_power_assessment,
                "",
                "### Communications & Line-of-Sight",
                ai.communication_and_direct_line_of_sight,
                "",
                "### Key Engineering Trade-Offs",
                *[f"- {t}" for t in ai.key_engineering_tradeoffs],
                "",
                "### Recommended Countermeasures",
                *[f"- {m}" for m in ai.mitigation_strategies],
                "",
            ])

        md.extend([
            "---",
            f"**Scientific Safety Disclaimer:** {SCIENTIFIC_SAFETY_DISCLAIMER}",
        ])
        return "\n".join(md)

    @staticmethod
    def _render_html_report(report_id, title, site, score, hazard, ai, generated_at) -> str:
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title} - {site.name}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #24292e; max-width: 900px; margin: 40px auto; padding: 0 20px; }}
    h1 {{ color: #0366d6; border-bottom: 2px solid #eaecef; padding-bottom: 8px; }}
    h2 {{ color: #1b1f23; border-bottom: 1px solid #eaecef; padding-bottom: 6px; margin-top: 28px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
    th, td {{ border: 1px solid #e1e4e8; padding: 10px 12px; text-align: left; }}
    th {{ background-color: #f6f8fa; }}
    .badge {{ display: inline-block; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 0.9em; }}
    .badge-optimal {{ background: #28a745; color: white; }}
    .badge-nominal {{ background: #17a2b8; color: white; }}
    .badge-marginal {{ background: #ffc107; color: #212529; }}
    .badge-high-risk {{ background: #dc3545; color: white; }}
    .disclaimer {{ background-color: #fffbdd; border-left: 4px solid #d99b00; padding: 12px; margin-top: 30px; font-size: 0.85em; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p><strong>Candidate Site:</strong> {site.name} (<code>{site.site_id}</code>)<br>
     <strong>Report ID:</strong> <code>{report_id}</code> | <strong>Generated:</strong> {generated_at}</p>

  <h2>1. Executive Summary & Site Parameters</h2>
  <ul>
    <li><strong>Location:</strong> Latitude {site.latitude}°, Longitude {site.longitude}° (Lunar South Pole)</li>
    <li><strong>Average Terrain Slope:</strong> {site.mean_slope_deg}°</li>
    <li><strong>Annual Illumination:</strong> {site.illumination_pct}%</li>
    <li><strong>Direct Earth Visibility:</strong> {site.earth_visibility_pct}%</li>
    <li><strong>Primary Science Value:</strong> {site.scientific_value}</li>
  </ul>

  <h2>2. Suitability Scoring & Decision Matrix</h2>
  <p><strong>Composite Score:</strong> <span class="badge badge-nominal">{score.overall_suitability_score} / 100 ({score.suitability_category})</span></p>

  <table>
    <thead>
      <tr>
        <th>Factor</th>
        <th>Raw Value</th>
        <th>Subscore</th>
        <th>Weight</th>
        <th>Contribution</th>
      </tr>
    </thead>
    <tbody>
"""
        for s in score.subscores:
            html += f"""      <tr>
        <td>{s.criterion}</td>
        <td>{s.raw_measurement} {s.unit}</td>
        <td>{s.normalized_subscore}/100</td>
        <td>{s.weight}</td>
        <td>{s.weighted_contribution}</td>
      </tr>
"""
        html += f"""    </tbody>
  </table>

  <h2>3. Physical Hazard Assessment</h2>
  <p><strong>Hazard Risk Tier:</strong> <code>{hazard.overall_hazard_level.upper()}</code><br>
     Detected {hazard.craters_count} craters, {hazard.boulders_count} boulder risk clusters, and {hazard.steep_slope_cells} steep slope cells.</p>

  <div class="disclaimer">
    <strong>Scientific Safety Notice:</strong> {SCIENTIFIC_SAFETY_DISCLAIMER}
  </div>
</body>
</html>"""
        return html


report_service = ReportService()
