# healthkit-report

[中文](README.md) · English

Turn an Apple Health export into a readable health report — without the double counting.

[![CI](https://github.com/little-fire9552/healthkit-report/actions/workflows/ci.yml/badge.svg)](https://github.com/little-fire9552/healthkit-report/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Why

`export.xml` contains **raw samples per source**, not the numbers the Health app shows:

- iPhone and Apple Watch both count the same walk → naive sums are ~2x too high.
- Third-party apps (Keep, Mi Fitness…) write their own copies.
- Units differ between sources (`Cal`/`kcal`, `km`/`mi`, `min`/`hr`, fractions vs percent).

This package reproduces Apple's de-duplication by taking the **union of time intervals**
per metric and preferring the higher-priority device. Validated against the Move ring:
median ratio **1.000** across 486 days.

See [docs/algorithm.md](docs/algorithm.md) for the algorithm and its trade-offs.

## Install

```bash
pip install healthkit-report
pip install "healthkit-report[fast]"   # lxml parser, 5–10x faster
```

Python 3.9+.

## Use

```bash
healthkit-report all ~/Downloads/apple_health_export/export.xml -o out --name Alice
```

Outputs:

| File | Content |
|---|---|
| `out/health-report.docx` | multi-page check-up report (Chinese): cover, summary, 32-item results table with reference ranges, interpretation, attention list, follow-up plan |
| `out/health-report.xlsx` | overview, daily metrics, monthly summary, workouts, sleep, notes |
| `out/health-report.html` | self-contained dashboard with dependency-free SVG charts |

Step by step:

```bash
healthkit-report parse   export.xml     -o dataset.json
healthkit-report analyze dataset.json   -o findings.json
healthkit-report report  dataset.json   -o out --name Alice --formats docx,html
```

Options: `--since/--until` filter dates, `--priority` sets device precedence
(default `Watch iPhone iPad Mac iPod`), `--formats` selects outputs.

## Python API

```python
from healthkit_report import parse_export, analyze
from healthkit_report.render.docx import build_report

dataset = parse_export("export.xml")
findings = analyze(dataset)
print(findings["metrics"]["steps"]["mean"], findings["sleep"]["mean"])
build_report(dataset, findings, "report.docx", name="Alice")
```

## What it computes

34 metrics: steps, distance, energy, exercise/stand time, daylight, heart rate,
resting HR, HRV, heart-rate recovery, respiratory rate, SpO2, VO₂max, sleep stages,
running dynamics, walking speed/step length/asymmetry, headphone and environmental
audio exposure. See [docs/metrics.md](docs/metrics.md).

Reference ranges come from published sources (Chinese BMI standard, AASM sleep
recommendations, FRIEND cardiorespiratory fitness percentiles, WHO-ITU safe listening).
They are defaults, not clinical cut-offs.

## Limitations

- Data before the watch was paired has no heart rate, HRV or sleep; iPhone-only step
  counts are systematically lower.
- Watch metrics (VO₂max, SpO₂, wrist temperature) are estimates.
- The report prose is Chinese; English requires editing `render/docx.py`.
- Not a medical device. Not a diagnosis.

## Contributing

Issues and PRs welcome — new metrics, translations and report templates are especially
useful. See [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
pip install -e ".[fast,dev]"
python -m unittest discover -s tests -v
ruff check src tests
```

## License

MIT
