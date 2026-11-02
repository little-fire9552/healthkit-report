"""Minimal end-to-end example.

Usage:
    python examples/quickstart.py ~/Downloads/apple_health_export/export.xml out/

Requires: pip install healthkit-report
"""

import json
import sys
from pathlib import Path

from healthkit_report import analyze, parse_export
from healthkit_report.render.docx import build_report
from healthkit_report.render.html import build_dashboard
from healthkit_report.render.xlsx import build_workbook


def main(export_path: str, out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    dataset = parse_export(export_path)
    findings = analyze(dataset)

    build_report(dataset, findings, str(out / "report.docx"), name="Demo")
    build_workbook(dataset, findings, str(out / "report.xlsx"))
    (out / "dashboard.html").write_text(
        build_dashboard(dataset, findings, name="Demo"), encoding="utf-8"
    )
    (out / "findings.json").write_text(
        json.dumps(findings, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    mean_steps = findings["metrics"]["steps"]["mean"]
    print(f"{findings['span']['days']} days, {mean_steps:,.0f} steps/day on average")
    print(f"written to {out.resolve()}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
