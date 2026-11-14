"""Schemas for mission landing-site evaluation report generation."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    """Input payload to compile a comprehensive lunar landing evaluation report."""

    site_id: str = Field(..., description="Target site slug identifier from catalog")
    mission_title: Optional[str] = Field("Artemis Candidate Landing Site Assessment", description="Mission or report title")
    include_ai_narrative: bool = Field(True, description="Whether to include synthesized AI scientific explanation")
    output_format: str = Field("json", description="Desired report format: 'json', 'markdown', or 'html'")


class ReportGenerateResponse(BaseModel):
    """Structured report response."""

    report_id: str
    generated_at: str
    mission_title: str
    site_id: str
    site_name: str
    output_format: str
    content: str = Field(..., description="Full text or formatted markup content of the report")
    structured_summary: Dict[str, Any] = Field(..., description="Key metrics and decision matrices")
    disclaimer: str
