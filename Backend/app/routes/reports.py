"""Mission analysis report generation endpoint."""

from fastapi import APIRouter, HTTPException, status
from app.schemas.report import ReportGenerateRequest, ReportGenerateResponse
from app.services.report_service import report_service

router = APIRouter(prefix="", tags=["Reports"])


@router.post("/reports/generate", response_model=ReportGenerateResponse, summary="Compile comprehensive landing site evaluation report")
def generate_report(payload: ReportGenerateRequest) -> ReportGenerateResponse:
    """Assembles measurements, scores, hazard risks, and AI synthesis into an exportable mission report."""
    try:
        return report_service.generate_report(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
