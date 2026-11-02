"""healthkit-report: parse Apple Health exports and generate health reports."""

from __future__ import annotations

__version__ = "0.1.0"

from .analysis import analyze  # noqa: E402
from .parser import load_dataset, parse_export, save_dataset  # noqa: E402

__all__ = ["__version__", "analyze", "parse_export", "load_dataset", "save_dataset"]
