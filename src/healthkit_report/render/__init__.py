"""Report renderers: DOCX, XLSX and a self-contained HTML dashboard."""

from .docx import build_report
from .html import build_dashboard
from .xlsx import build_workbook

__all__ = ["build_report", "build_dashboard", "build_workbook"]
