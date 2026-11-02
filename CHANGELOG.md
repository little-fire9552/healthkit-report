# Changelog

All notable changes to this project will be documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-02

### Added

- Streaming parser for Apple Health `export.xml` (HealthKit Export v16/v17),
  with `lxml` acceleration when available.
- Interval-union de-duplication across devices, with configurable priority
  (`Watch > iPhone > iPad > Mac > iPod` by default) and per-minute de-duplication
  for rate/level metrics.
- Sleep aggregation per night (Core / Deep / REM / InBed / Awake), attributed to
  the wake-up date and resolved across sources.
- 34 canonical metrics with unit normalisation (`Cal`/`kcal`, `mi`/`km`,
  `min`/`hr`, `lb`/`kg`, fraction vs percent).
- Analysis layer: descriptives, monthly aggregates, 28-day trend comparison,
  activity rings, audio-exposure histogram, correlations, coverage, extremes.
- Renderers:
  - DOCX health check-up report (cover, summary, results table with reference
    ranges and grading, interpretation, attention list, follow-up plan,
    methodology, disclaimer).
  - XLSX workbook (overview, daily, monthly, workouts, sleep, notes).
  - Self-contained HTML dashboard with dependency-free SVG charts.
- CLI with `parse`, `analyze`, `report` and `all` subcommands.
- 27 unit tests covering parsing, de-duplication, analysis and renderers.

[0.1.0]: https://github.com/your-name/healthkit-report/releases/tag/v0.1.0
