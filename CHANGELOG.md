# Changelog

All notable changes to this project will be documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-11-02

### Added

- 短于 3 小时的睡眠按「午睡」处理，不再计入夜间均值；报告会单独说明午睡次数与时长。
- VO₂max 改为三段分级（偏低 / 正常偏低 / 正常），阈值按性别与年龄取 FRIEND 第 20 与第 25 百分位，
  与 Apple「最低 20%」的口径一致。
- 解析时记录数据中出现过的 UTC 偏移，跨时区时报告会给出提示。

### Fixed

- 听力暴露的周剂量按全部监测天数折算（此前按手表佩戴天数，会高估暴露量）。
- 身高、体重在封面与表格中统一取最近一次测量。

## [0.1.2] - 2026-11-02

### Fixed

- 封面与表格使用同一次测量：身高/体重取最近一条，此前封面取首条、表格取日均值，
  会显示成 168 与 170 两个数字。
- 未测量项（血压、体温）不再标成「参考」，改为「未检测」。
- 听力暴露按 WHO-ITU 周剂量计算，不再固定标「需关注」。
- 报告改为按性别与年龄查 FRIEND 百分位，VO₂max、腰围不再写死男性标准。
- 步数补充设备口径说明：手表佩戴期与仅 iPhone 记录期分别给出日均值。
- XLSX 概览的单位由 `count` 改为「步」等中文单位。

## [0.1.1] - 2026-11-02

### Added

- Windows support: the DSH plugin now finds `python.exe` in the runtime layout,
  forces UTF-8 for child output, and the report uses a platform-appropriate
  Chinese font (Microsoft YaHei / PingFang SC / Noto Sans CJK SC).
- `安装.bat` alongside `安装.command` in the standalone share package.

### Fixed

- The plugin falls back to the DSH runtime interpreter when `DSH_HOME` is not
  exported by the desktop process.

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

[0.1.0]: https://github.com/little-fire9552/healthkit-report/releases/tag/v0.1.0
