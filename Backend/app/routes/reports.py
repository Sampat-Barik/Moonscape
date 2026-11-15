"""Mission analysis and comparative report generation endpoints (Phase 8 & Comparison Extension)."""

from datetime import datetime, timezone
from typing import Any, Union
from fastapi import APIRouter, HTTPException, Response, status
from app.schemas.report import (
    ComparisonReportRequest,
    ComparisonReportResponse,
    ReportGenerateRequest,
    ReportGenerateResponse,
)
from app.services.comparison_report_generator import comparison_report_generator
from app.services.report_generator import report_generator

router = APIRouter(prefix="", tags=["Reports"])


@router.post(
    "/reports/comparison",
    summary="Generate comprehensive multi-site comparative assessment report",
    description="Assembles multi-site rankings, charts, master matrices, and sensor citations into a multi-page PDF or JSON.",
    response_model=Union[ComparisonReportResponse, Any],  # type: ignore
)
def generate_comparison_report(payload: ComparisonReportRequest) -> Union[ComparisonReportResponse, Response]:
    """Generates comprehensive comparative PDF report across 2 or more landing sites."""
    try:
        report_res, pdf_bytes = comparison_report_generator.generate_comparison_report(payload)

        req_fmt = (payload.format or payload.output_format or "pdf").strip().lower()
        if req_fmt == "pdf" and pdf_bytes:
            report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            summary_tag = "_Summary" if getattr(payload, "summary_only", False) else ""
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="MoonScape_Comparison{summary_tag}_{report_date}.pdf"',
                    "Content-Type": "application/pdf",
                },
            )
        elif req_fmt in ["markdown", "html"] and pdf_bytes:
            media = "text/markdown" if req_fmt == "markdown" else "text/html"
            return Response(content=pdf_bytes, media_type=media)

        return report_res

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/reports/generate",
    summary="Compile comprehensive landing site evaluation report",
    description="Assembles measurements, scores, slope distributions, illumination, and hazards into a structured 19-element JSON or downloadable PDF report.",
    response_model=Union[ReportGenerateResponse, ComparisonReportResponse, Any],  # type: ignore
)
def generate_report(payload: ReportGenerateRequest) -> Union[ReportGenerateResponse, ComparisonReportResponse, Response]:
    """Assembles measurements, scores, hazard risks, and methodology into exportable JSON or downloadable PDF report."""
    try:
        # Multi-site delegation if site_ids contains >= 2 sites
        if payload.site_ids and len(payload.site_ids) >= 2:
            comp_req = ComparisonReportRequest(
                site_ids=payload.site_ids,
                mission_profile=payload.mission_profile,
                custom_weights=payload.custom_weights or payload.weights,
                mission_title=payload.mission_title or "MoonScape Lunar South Pole Comparative Landing Site Assessment",
                format=payload.format or payload.output_format or "pdf",
            )
            report_res, pdf_bytes = comparison_report_generator.generate_comparison_report(comp_req)
            req_fmt = (payload.format or payload.output_format or "pdf").strip().lower()
            if req_fmt == "pdf" and pdf_bytes:
                report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                summary_tag = "_Summary" if getattr(payload, "summary_only", False) else ""
                return Response(
                    content=pdf_bytes,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f'attachment; filename="MoonScape_Comparison{summary_tag}_{report_date}.pdf"',
                        "Content-Type": "application/pdf",
                    },
                )
            elif req_fmt in ["markdown", "html"] and pdf_bytes:
                media = "text/markdown" if req_fmt == "markdown" else "text/html"
                return Response(content=pdf_bytes, media_type=media)
            return report_res

        # Single-site evaluation report
        report_res, pdf_bytes = report_generator.generate_report(payload)

        # Downloadable PDF response
        req_fmt = (payload.format or payload.output_format or "json").strip().lower()
        if req_fmt == "pdf" and pdf_bytes:
            filename_id = report_res.analysis_id or report_res.site_id or "lunar_site"
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="moonscape_report_{filename_id}.pdf"',
                    "Content-Type": "application/pdf",
                },
            )

        return report_res

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
