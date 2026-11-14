"""Root-level shim for Moonscape Scientific Report Generator."""

from Backend.app.services.report_generator import (
    ReportGenerator,
    report_generator,
)

__all__ = ["ReportGenerator", "report_generator"]
