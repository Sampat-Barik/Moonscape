"""Mission analysis report generation endpoint (Phase 8)."""

from typing import Any, Union
from fastapi import APIRouter, HTTPException, Response, status
from app.schemas.report import ReportGenerateRequest, ReportGenerateResponse
from app.services.report_generator import report_generator

router = APIRouter(prefix="", tags=["Reports"])


@router.post(
    "/reports/generate",
    summary="Compile comprehensive landing site evaluation report",
    description="Assembles measurements, scores, slope distributions, illumination, and hazards into a structured 19-element JSON or downloadable PDF report.",
    response_model=Union[ReportGenerateResponse, Any],  # type: ignore
)
def generate_report(payload: ReportGenerateRequest) -> Union[ReportGenerateResponse, Response]:
    """Assembles measurements, scores, hazard risks, and methodology into exportable JSON or downloadable PDF report."""
    try:
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
