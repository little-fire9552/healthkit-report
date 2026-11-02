"""Command line interface: ``healthkit-report`` / ``hkrep``."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from . import __version__
from .analysis import analyze
from .parser import load_dataset, parse_export, save_dataset
from .render.docx import build_report
from .render.html import build_dashboard
from .render.xlsx import build_workbook


def _log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _parse_command(args: argparse.Namespace) -> int:
    export = args.export
    if os.path.isdir(export):
        for candidate in ("export.xml", "导出.xml", "apple_health_export/export.xml"):
            path = os.path.join(export, candidate) if not candidate.startswith("apple_health_export") \
                else os.path.join(export, "apple_health_export", "export.xml")
            if os.path.exists(path):
                export = path
                break
    _log(f"解析 {export}")
    dataset = parse_export(
        export,
        since=args.since,
        until=args.until,
        device_priority=args.priority,
        progress=lambda count: _log(f"  {count:,} 条记录…"),
    )
    save_dataset(dataset, args.out)
    _log(f"完成：{dataset['meta']['record_count']:,} 条记录，"
         f"{len(dataset['daily'])} 天 -> {args.out}")
    return 0


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _analyze_command(args: argparse.Namespace) -> int:
    dataset = load_dataset(args.dataset)
    findings = analyze(dataset)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(findings, handle, ensure_ascii=False, indent=1)
    _log(f"完成：{len(findings['metrics'])} 个指标 -> {args.out}")
    return 0


def _report_command(args: argparse.Namespace) -> int:
    dataset = load_dataset(args.dataset)
    findings = _load(args.findings) if args.findings else analyze(dataset)
    os.makedirs(args.out, exist_ok=True)
    prefix = os.path.join(args.out, args.prefix)
    formats = {item.strip().lower() for item in args.formats.split(",") if item.strip()}
    written: List[str] = []
    if "docx" in formats:
        written.append(build_report(dataset, findings, prefix + ".docx", name=args.name, title=args.title))
    if "xlsx" in formats:
        written.append(build_workbook(dataset, findings, prefix + ".xlsx", name=args.name))
    if "html" in formats:
        html = build_dashboard(dataset, findings, name=args.name)
        with open(prefix + ".html", "w", encoding="utf-8") as handle:
            handle.write(html)
        written.append(prefix + ".html")
    for path in written:
        _log(f"已生成 {path}")
    return 0


def _all_command(args: argparse.Namespace) -> int:
    dataset_cache = os.path.join(args.out, "dataset.json")
    os.makedirs(args.out, exist_ok=True)
    dataset = parse_export(
        args.export,
        since=args.since,
        until=args.until,
        device_priority=args.priority,
        progress=lambda count: _log(f"  {count:,} 条记录…"),
    )
    save_dataset(dataset, dataset_cache)
    findings = analyze(dataset)
    with open(os.path.join(args.out, "findings.json"), "w", encoding="utf-8") as handle:
        json.dump(findings, handle, ensure_ascii=False, indent=1)
    args.dataset = dataset_cache
    args.findings = None
    return _report_command(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="healthkit-report",
        description="解析 Apple 健康导出，去重多设备记录，生成健康报告（DOCX / XLSX / HTML）。",
    )
    parser.add_argument("--version", action="version", version=f"healthkit-report {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    parse_cmd = sub.add_parser("parse", help="解析 export.xml，输出 JSON 数据集")
    parse_cmd.add_argument("export", help="export.xml 或解压后的 apple_health_export 目录")
    parse_cmd.add_argument("-o", "--out", default="dataset.json", help="输出 JSON（默认 dataset.json）")
    parse_cmd.add_argument("--since", help="起始日期 YYYY-MM-DD（含）")
    parse_cmd.add_argument("--until", help="结束日期 YYYY-MM-DD（含）")
    parse_cmd.add_argument("--priority", nargs="+", default=None,
                           help="设备优先级，默认 Watch iPhone iPad Mac iPod")
    parse_cmd.set_defaults(func=_parse_command)

    analyze_cmd = sub.add_parser("analyze", help="对数据集做统计，输出 findings.json")
    analyze_cmd.add_argument("dataset", help="parse 生成的 JSON")
    analyze_cmd.add_argument("-o", "--out", default="findings.json")
    analyze_cmd.set_defaults(func=_analyze_command)

    report_cmd = sub.add_parser("report", help="生成报告文件")
    report_cmd.add_argument("dataset", help="parse 生成的 JSON")
    report_cmd.add_argument("-o", "--out", default="out", help="输出目录")
    report_cmd.add_argument("--findings", help="复用已有的 findings.json")
    report_cmd.add_argument("--name", default="", help="受检者姓名（可选）")
    report_cmd.add_argument("--title", default="健康体检报告")
    report_cmd.add_argument("--prefix", default="health-report", help="输出文件名前缀")
    report_cmd.add_argument("--formats", default="docx,xlsx,html", help="docx,xlsx,html 的组合")
    report_cmd.set_defaults(func=_report_command)

    all_cmd = sub.add_parser("all", help="解析 + 统计 + 生成报告，一步完成")
    all_cmd.add_argument("export", help="export.xml 或解压后的目录")
    all_cmd.add_argument("-o", "--out", default="out", help="输出目录")
    all_cmd.add_argument("--since")
    all_cmd.add_argument("--until")
    all_cmd.add_argument("--priority", nargs="+", default=None)
    all_cmd.add_argument("--name", default="")
    all_cmd.add_argument("--title", default="健康体检报告")
    all_cmd.add_argument("--prefix", default="health-report")
    all_cmd.add_argument("--formats", default="docx,xlsx,html")
    all_cmd.set_defaults(func=_all_command)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as error:
        _log(f"找不到文件：{error}")
        return 2
    except KeyboardInterrupt:
        _log("已取消")
        return 130
