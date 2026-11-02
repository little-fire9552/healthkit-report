"""Word health check-up report (Chinese).

The layout mirrors a conventional printed physical-examination report: cover
page, summary, demographics, a results table with reference ranges and grades,
prose interpretation, an attention list, a follow-up plan, and methodology.
"""

from __future__ import annotations

import os
from dataclasses import replace
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from ..references import (
    GROUPS,
    NORMAL,
    SEVERITY,
    UNDETECTED,
    Reference,
    default_references,
    profile_from_dataset,
)

FONT = "PingFang SC"

NAVY = RGBColor(0x1F, 0x38, 0x64)
BLUE = RGBColor(0x2E, 0x75, 0xB6)
DARK = RGBColor(0x1F, 0x29, 0x37)
GRAY = RGBColor(0x6B, 0x72, 0x80)
LGRAY = RGBColor(0x9C, 0xA3, 0xAF)
RED = RGBColor(0xC0, 0x00, 0x00)
AMBER = RGBColor(0xB4, 0x53, 0x09)
GREEN = RGBColor(0x2E, 0x7D, 0x32)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

BAND = "1F3864"
LIGHT = "EAF1F8"
LIGHT2 = "F4F7FB"
LINEC = "D5DEE8"

UNIT_ZH = {
    "count": "步",
    "min": "分钟",
    "breaths/min": "次/分",
    "bpm": "bpm",
    "ms": "ms",
    "%": "%",
    "km": "km",
    "km/h": "km/h",
    "mL/min/kg": "mL/min·kg",
    "dB": "dB",
    "cm": "cm",
    "h": "小时",
    "kg": "kg",
    "kcal": "kcal",
}

RATING_COLOR = {
    NORMAL: GREEN, "良好": GREEN, "正常偏高": AMBER, "正常偏低": AMBER,
    "偏低": RED, "偏高": RED, "不足": AMBER, "不规律": AMBER, "偏慢": AMBER,
    "临界": AMBER, "需关注": AMBER, "需注意": AMBER, "未检测": LGRAY,
}

TC_AFTER_SHD = ("w:noWrap", "w:tcMar", "w:textDirection", "w:tcFitText", "w:vAlign",
                "w:hideMark", "w:headers", "w:cellIns", "w:cellDel", "w:cellMerge", "w:tcPrChange")
P_AFTER_BDR = ("w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap",
               "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi",
               "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind", "w:contextualSpacing",
               "w:mirrorIndents", "w:suppressOverlap", "w:jc", "w:textDirection",
               "w:textAlignment", "w:textboxTightWrap", "w:outlineLvl", "w:divId",
               "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange")


class _Builder:
    def __init__(self, *, name: str, title: str) -> None:
        self.doc = Document()
        self.name = name or "受检者"
        self.title = title
        section = self.doc.sections[0]
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(1.8)
        section.left_margin = Cm(2.2)
        section.right_margin = Cm(2.2)
        section.footer_distance = Cm(0.9)
        self.content_width = 21.0 - 4.4
        normal = self.doc.styles["Normal"]
        normal.font.name = FONT
        normal.font.size = Pt(10.5)
        normal.font.color.rgb = DARK
        normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        normal.paragraph_format.space_after = Pt(0)
        normal.paragraph_format.line_spacing = 1.35

    # -- primitives ---------------------------------------------------------
    def font(self, run, size=10.5, bold=False, color=DARK, name=FONT):
        run.font.name = name
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        rpr = run._element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.append(rfonts)
        for attr in ("w:eastAsia", "w:ascii", "w:hAnsi"):
            rfonts.set(qn(attr), name)

    @staticmethod
    def shade(cell, hex_color: str) -> None:
        tc_pr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_color)
        tc_pr.insert_element_before(shd, *TC_AFTER_SHD)

    @staticmethod
    def para_shade(paragraph, hex_color: str) -> None:
        p_pr = paragraph._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_color)
        p_pr.insert_element_before(shd, *P_AFTER_BDR[1:])

    @staticmethod
    def para_border(paragraph, edge: str, color, size: int = 8, space: int = 2) -> None:
        p_pr = paragraph._p.get_or_add_pPr()
        bdr = p_pr.find(qn("w:pBdr"))
        if bdr is None:
            bdr = OxmlElement("w:pBdr")
            p_pr.insert_element_before(bdr, *P_AFTER_BDR)
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), str(space))
        if isinstance(color, RGBColor):
            el.set(qn("w:color"), "%02X%02X%02X" % (color[0], color[1], color[2]))
        else:
            el.set(qn("w:color"), str(color))
        bdr.append(el)

    def P(self, text="", size=10.5, bold=False, color=DARK, align=WD_ALIGN_PARAGRAPH.LEFT,
          before=0, after=4, line=1.45):
        paragraph = self.doc.add_paragraph()
        paragraph.alignment = align
        fmt = paragraph.paragraph_format
        fmt.space_before = Pt(before)
        fmt.space_after = Pt(after)
        fmt.line_spacing = line
        if text:
            run = paragraph.add_run(text)
            self.font(run, size, bold, color)
        return paragraph

    def H(self, text: str, number: str = "", before: int = 14, after: int = 6):
        paragraph = self.doc.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(before)
        paragraph.paragraph_format.space_after = Pt(after)
        paragraph.paragraph_format.keep_with_next = True
        self.para_shade(paragraph, LIGHT)
        self.para_border(paragraph, "left", NAVY, 24, 4)
        if number:
            run = paragraph.add_run(f"{number}  ")
            self.font(run, 13, True, BLUE)
        run = paragraph.add_run(text)
        self.font(run, 13, True, NAVY)
        return paragraph

    def H2(self, text: str, before: int = 12, after: int = 5):
        paragraph = self.doc.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(before)
        paragraph.paragraph_format.space_after = Pt(after)
        paragraph.paragraph_format.keep_with_next = True
        self.para_border(paragraph, "bottom", LINEC, 6, 3)
        run = paragraph.add_run(text)
        self.font(run, 11, True, NAVY)
        return paragraph

    def bullet(self, label: str, text: str, size: float = 9.8, color=DARK) -> None:
        paragraph = self.doc.add_paragraph()
        fmt = paragraph.paragraph_format
        fmt.left_indent = Cm(0.75)
        fmt.first_line_indent = Cm(-0.45)
        fmt.space_after = Pt(3)
        fmt.line_spacing = 1.4
        run = paragraph.add_run("▪ ")
        self.font(run, size, False, BLUE)
        if label:
            run = paragraph.add_run(label)
            self.font(run, size, True, NAVY)
        run = paragraph.add_run(text)
        self.font(run, size, False, color)

    def table(self, rows: int, cols: int, widths: Sequence[float], *, borderless: bool = False):
        table = self.doc.add_table(rows=rows, cols=cols)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        tbl_pr = table._tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            el = OxmlElement(f"w:{edge}")
            if borderless:
                el.set(qn("w:val"), "nil")
            else:
                el.set(qn("w:val"), "single")
                el.set(qn("w:sz"), "4")
                el.set(qn("w:space"), "0")
                el.set(qn("w:color"), LINEC)
            borders.append(el)
        tbl_pr.insert_element_before(borders, "w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook")
        grid = table._tbl.tblGrid
        for index, column in enumerate(grid.findall(qn("w:gridCol"))):
            column.set(qn("w:w"), str(int(round(widths[index] * 567))))
        tbl_w = tbl_pr.find(qn("w:tblW"))
        if tbl_w is not None:
            tbl_w.set(qn("w:type"), "dxa")
            tbl_w.set(qn("w:w"), str(int(round(sum(widths) * 567))))
        for row in table.rows:
            for index, width in enumerate(widths):
                row.cells[index].width = Cm(width)
        return table

    @staticmethod
    def margins(cell, top=60, bottom=60, left=110, right=110) -> None:
        tc_pr = cell._tc.get_or_add_tcPr()
        mar = OxmlElement("w:tcMar")
        for name, value in (("top", top), ("start", left), ("bottom", bottom), ("end", right)):
            el = OxmlElement(f"w:{name}")
            el.set(qn("w:w"), str(value))
            el.set(qn("w:type"), "dxa")
            mar.append(el)
        tc_pr.insert_element_before(mar, "w:textDirection", "w:tcFitText", "w:vAlign",
                                    "w:hideMark", "w:headers", "w:cellIns", "w:cellDel",
                                    "w:cellMerge", "w:tcPrChange")

    def cell_text(self, cell, text, size=9, bold=False, color=DARK,
                  align=WD_ALIGN_PARAGRAPH.LEFT) -> None:
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        paragraph = cell.paragraphs[0]
        paragraph.alignment = align
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = 1.25
        run = paragraph.add_run(str(text))
        self.font(run, size, bold, color)

    @staticmethod
    def no_split(row) -> None:
        tr_pr = row._tr.get_or_add_trPr()
        tr_pr.append(OxmlElement("w:cantSplit"))

    @staticmethod
    def repeat_header(table) -> None:
        tr_pr = table.rows[0]._tr.get_or_add_trPr()
        el = OxmlElement("w:tblHeader")
        el.set(qn("w:val"), "true")
        tr_pr.append(el)

    def page_fields(self, paragraph) -> None:
        for instruction, tail in (("PAGE", " 页 / 共 "), ("NUMPAGES", " 页")):
            run = paragraph.add_run()
            self.font(run, 8, False, LGRAY)
            begin = OxmlElement("w:fldChar")
            begin.set(qn("w:fldCharType"), "begin")
            instr = OxmlElement("w:instrText")
            instr.set(qn("xml:space"), "preserve")
            instr.text = instruction
            end = OxmlElement("w:fldChar")
            end.set(qn("w:fldCharType"), "end")
            run._r.append(begin)
            run._r.append(instr)
            run._r.append(end)
            tail_run = paragraph.add_run(tail)
            self.font(tail_run, 8, False, LGRAY)

    def footer(self) -> None:
        style = self.doc.styles["Footer"]
        stops = style.paragraph_format.tab_stops
        stops.clear_all()
        stops.add_tab_stop(Cm(self.content_width), WD_TAB_ALIGNMENT.RIGHT)
        paragraph = self.doc.sections[0].footer.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(f"{self.title} · {self.name} · HK-REPORT")
        self.font(run, 8, False, LGRAY)
        run = paragraph.add_run("\t第 ")
        self.font(run, 8, False, LGRAY)
        self.page_fields(paragraph)


def _value_text(value: Optional[float], unit: str, digits: int) -> str:
    if value is None:
        return "未检测"
    if digits == 0:
        return f"{value:,.0f} {unit}".strip()
    return f"{value:,.{digits}f} {unit}".strip()


def _row_values(findings: Dict, profile: Dict) -> Dict[str, Tuple[Optional[float], str]]:
    metrics = findings.get("metrics", {})
    sleep = findings.get("sleep", {})
    values: Dict[str, Tuple[Optional[float], str]] = {}
    for key, record in metrics.items():
        unit = UNIT_ZH.get(record.get("unit", ""), record.get("unit", ""))
        values[key] = (record["mean"], _value_text(record["mean"], unit, record.get("digits", 0)))
    if sleep:
        values["sleep_h"] = (sleep["mean"], f"{sleep['mean']:.2f} 小时")
        if sleep.get("bed_median") is not None:
            minutes = int(sleep["bed_median"])
            values["bed_time"] = (None, f"{minutes // 60 % 24:02d}:{minutes % 60:02d}")
        values["deep_share"] = (sleep.get("deep_share", 0) * 100, f"{sleep.get('deep_share', 0) * 100:.0f}%")
        values["rem_share"] = (sleep.get("rem_share", 0) * 100, f"{sleep.get('rem_share', 0) * 100:.0f}%")
    audio = findings.get("audio", {}).get("hp_audio", {})
    if audio:
        values["audio_exposure"] = (
            None,
            f"≥80 dB {audio['hours_ge_80']:.0f} 小时 / ≥90 dB {audio['hours_ge_90']:.0f} 小时",
        )
    for key in ("waist", "bp", "temp"):
        values.setdefault(key, (None, "未检测"))
    workouts = findings.get("workouts", {})
    pace = workouts.get("run_pace_median")
    if pace:
        minutes = int(pace["median"])
        values["run_pace"] = (None, f"{minutes}:{round((pace['median'] - minutes) * 60):02d} /km")
    if profile.get("height_cm") and profile.get("weight_kg"):
        height = profile["height_cm"] / 100.0
        values["bmi"] = (profile["weight_kg"] / height ** 2,
                         f"{profile['weight_kg'] / height ** 2:.1f}")
    return values


def _interpretation(findings: Dict, refs: Dict[str, Reference]) -> Dict[str, str]:
    metrics = findings.get("metrics", {})
    sleep = findings.get("sleep", {})
    paragraphs: Dict[str, str] = {}
    rhr = metrics.get("resting_hr")
    trend = findings.get("trend_28d", {}).get("resting_hr")
    if rhr:
        text = (f"静息心率平均 {rhr['mean']:.0f} 次/分（中位 {rhr['median']:.0f}，"
                f"范围 {rhr['min']:.0f}–{rhr['max']:.0f}）。")
        if trend:
            direction = "下降" if trend["delta"] < 0 else "上升"
            text += f"最近 28 天均值较起始 28 天{direction} {abs(trend['delta']):.1f} 次/分。"
        paragraphs["rhr"] = text
    if sleep:
        paragraphs["sleep"] = (
            f"睡眠平均 {sleep['mean']:.2f} 小时（中位 {sleep['median']:.2f}），"
            f"{sleep['lt7'] * 100:.0f}% 的夜晚不足 7 小时；深睡 {sleep['deep']:.1f} 小时"
            f"（{sleep['deep_share'] * 100:.0f}%），REM {sleep['rem']:.1f} 小时"
            f"（{sleep['rem_share'] * 100:.0f}%）。"
        )
    vo2 = metrics.get("vo2max")
    if vo2:
        paragraphs["vo2"] = (
            f"VO₂max 估算 {vo2['mean']:.1f} mL/min·kg（范围 {vo2['min']:.1f}–{vo2['max']:.1f}），"
            "是本次最需要投入的指标：它对有氧训练量非常敏感，8–12 周的系统训练通常能提升 3–5 点。"
        )
    steps = metrics.get("steps")
    if steps:
        dist = findings.get("steps_distribution", {})
        paragraphs["steps"] = (
            f"日均 {steps['mean']:,.0f} 步（中位 {steps['median']:,.0f}），"
            f"{dist.get('ge_10000', 0) * 100:.0f}% 的天数 ≥1 万步，"
            f"{dist.get('lt_5000', 0) * 100:.0f}% 不足 5,000 步，活动量两极分化。"
        )
    return paragraphs


def build_report(
    dataset: Dict,
    findings: Dict,
    path: str,
    *,
    name: str = "",
    title: str = "健康体检报告",
    references: Optional[Sequence[Reference]] = None,
) -> str:
    profile = profile_from_dataset(dataset)
    profile["name"] = name or profile.get("name") or ""
    refs = {ref.key: ref for ref in (references or default_references())}
    if profile.get("height_cm"):
        height_m = profile["height_cm"] / 100.0
        low, high = 18.5 * height_m ** 2, 23.9 * height_m ** 2
        refs["weight"] = replace(refs["weight"], low=low, high=high,
                                 text=f"{low:.0f}–{high:.0f} kg")
    values = _row_values(findings, profile)
    builder = _Builder(name=profile["name"], title=title)
    builder.footer()

    span = findings["span"]
    meta = dataset.get("meta", {})
    bmi = values.get("bmi", (None, "—"))[1]

    # ---------------- cover ----------------
    band = builder.table(1, 1, [builder.content_width], borderless=True)
    builder.shade(band.rows[0].cells[0], BAND)
    band.rows[0].height = Cm(0.35)
    builder.P("", after=46)
    builder.P("APPLE HEALTH DATA  ·  WEARABLE HEALTH ASSESSMENT", 8.5, False, BLUE, after=10)
    builder.P(title, 34, True, NAVY, after=4, line=1.1)
    builder.P("基于 Apple Watch 与 iPhone 连续监测数据", 11.5, False, GRAY, after=2)
    builder.P(f"数据区间 {span['first']} — {span['last']}（{span['days']} 天）", 9.5, False, LGRAY, after=26)
    rule = builder.doc.add_paragraph()
    builder.para_border(rule, "bottom", LINEC, 10)
    builder.P("", after=22)

    info_rows = [
        ("姓　　名", profile["name"] or "—", "性　　别", profile.get("sex", "—")),
        ("年　　龄", f"{profile['age']} 岁" if profile.get("age") else "—",
         "身　　高", f"{profile['height_cm']:.0f} cm" if profile.get("height_cm") else "—"),
        ("体　　重", f"{profile['weight_kg']:.1f} kg" if profile.get("weight_kg") else "—",
         "BMI", bmi),
        ("报告编号", f"HK-{date.today():%Y%m%d}", "数据来源", "Apple 健康导出"),
    ]
    info = builder.table(4, 4, [3.4, 5.1, 3.4, 4.7])
    for row_index, row in enumerate(info_rows):
        for column, text in enumerate(row):
            cell = info.rows[row_index].cells[column]
            builder.margins(cell, 80, 80, 140, 120)
            if column % 2 == 0:
                builder.shade(cell, LIGHT2)
                builder.cell_text(cell, text, 9.5, True, NAVY)
            else:
                builder.cell_text(cell, text, 9.5, False, DARK)
        builder.no_split(info.rows[row_index])

    builder.P("", after=56)
    top_rule = builder.doc.add_paragraph()
    builder.para_border(top_rule, "top", LINEC, 8)
    builder.P("本报告由可穿戴设备连续监测数据自动生成，含身高体重、心率、血氧、睡眠、活动与听力等指标；"
              "不含血液检验、影像学与临床查体，未经执业医师审核。", 8.5, False, GRAY, after=3)
    builder.P(f"生成日期：{date.today():%Y-%m-%d}　　"
              f"数据导出：{meta.get('export_date') or '—'}", 8.5, False, LGRAY)
    builder.doc.add_page_break()

    # ---------------- summary ----------------
    builder.H("报告摘要", "一", before=0)
    box = builder.table(1, 1, [builder.content_width])
    cell = box.rows[0].cells[0]
    builder.shade(cell, LIGHT2)
    builder.margins(cell, 160, 160, 200, 200)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
    first = cell.paragraphs[0]
    first.paragraph_format.space_after = Pt(6)
    run = first.add_run("总体结论：")
    builder.font(run, 10.5, True, NAVY)
    run = first.add_run("本次数据回顾未见急性异常，生命体征总体平稳；主要问题为可干预的功能性指标。")
    builder.font(run, 10.5, False, DARK)

    attention = [row for row in _grade_rows(refs, values) if row["severity"] >= 2]
    for label, text, color in (
        ("近 3 个月趋势  ", _trend_sentence(findings), GREEN),
        ("需要重点关注  ", "；".join(row["label"] for row in attention[:4]) or "无", AMBER),
        ("本次未覆盖  ", "血压、血常规、生化、影像、眼科与口腔检查需在医院完成。", GRAY),
    ):
        paragraph = cell.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(4)
        paragraph.paragraph_format.line_spacing = 1.35
        run = paragraph.add_run("▪ ")
        builder.font(run, 9.5, False, color)
        run = paragraph.add_run(label)
        builder.font(run, 9.5, True, color)
        run = paragraph.add_run(text)
        builder.font(run, 9.5, False, DARK)

    # ---------------- demographics ----------------
    builder.P("", after=8)
    builder.H("基本信息与检查条件", "二")
    basic_rows = [
        ("检查日期", f"{span['last']}（数据截止）", "报告日期", f"{date.today():%Y-%m-%d}"),
        ("数据来源", "HealthKit Export", "记录总量", f"{meta.get('record_count', 0):,} 条"),
        ("监测设备", "Apple Watch", "辅助设备", "iPhone"),
        ("有效监测", f"{findings['coverage']['days_with_heart_rate']} 天（手表佩戴）",
         "睡眠记录", f"{findings.get('sleep', {}).get('n', 0)} 夜"),
        ("既往病史", "未采集", "用药情况", "未采集"),
    ]
    basic = builder.table(5, 4, [3.4, 5.1, 3.4, 4.7])
    for row_index, row in enumerate(basic_rows):
        for column, text in enumerate(row):
            cell = basic.rows[row_index].cells[column]
            builder.margins(cell, 70, 70, 120, 110)
            if column % 2 == 0:
                builder.shade(cell, LIGHT2)
                builder.cell_text(cell, text, 9, True, NAVY)
            else:
                builder.cell_text(cell, text, 9, False, DARK)
        builder.no_split(basic.rows[row_index])
    builder.P("注：设备更换或佩戴间断会影响跨月比较；手表未佩戴的日期缺少心率、HRV 与睡眠。",
              8.5, False, GRAY, before=4)

    # ---------------- results table ----------------
    builder.H("检查结果总表", "三")
    rows = _grade_rows(refs, values)
    measured = [row for row in rows if row["value"] != "未检测"]
    builder.P(f"本次共呈现 {len(measured)} 项指标，其中 {len(attention)} 项需关注；"
              f"另有 {len(rows) - len(measured)} 项因设备限制未检测，见第七节。", 9, False, GRAY, after=5)

    lines: List[Tuple[str, Optional[Dict]]] = []
    current_group = None
    for row in rows:
        if row["group"] != current_group:
            current_group = row["group"]
            lines.append(("group", {"label": current_group}))
        lines.append(("data", row))

    table = builder.table(len(lines) + 1, 4, [5.1, 4.8, 4.1, 2.6])
    for column, label in enumerate(["检查项目", "结果", "参考范围", "评价"]):
        cell = table.rows[0].cells[column]
        builder.shade(cell, BAND)
        builder.margins(cell, 80, 80, 110, 100)
        builder.cell_text(cell, label, 9, True, WHITE, WD_ALIGN_PARAGRAPH.CENTER)
    builder.no_split(table.rows[0])
    builder.repeat_header(table)

    for index, (kind, payload) in enumerate(lines, start=1):
        line = table.rows[index]
        builder.no_split(line)
        if kind == "group":
            merged = line.cells[0].merge(line.cells[3])
            builder.shade(merged, LIGHT)
            builder.margins(merged, 62, 62, 110, 100)
            builder.cell_text(merged, f"【{payload['label']}】", 9, True, NAVY)
            merged.paragraphs[0].paragraph_format.keep_with_next = True
            continue
        for column, text in enumerate((payload["label"], payload["value"],
                                       payload["reference"], payload["grade"])):
            cell = line.cells[column]
            builder.margins(cell, 55, 55, 110, 100)
            if column == 0:
                builder.cell_text(cell, text, 9, False, DARK)
            elif column == 1:
                builder.cell_text(cell, text, 9, True, DARK)
            elif column == 2:
                builder.cell_text(cell, text, 8.5, False, GRAY)
            else:
                builder.cell_text(cell, text, 8.5, True, RATING_COLOR.get(text, GRAY),
                                  WD_ALIGN_PARAGRAPH.CENTER)

    builder.P("注：参考范围为成人常用区间或公开推荐，手表测量值（VO₂max、血氧、手腕温度）为估算，"
              "不能替代临床检验。", 8, False, GRAY, before=5)

    # ---------------- interpretation ----------------
    builder.H("分项解读", "四")
    text = _interpretation(findings, refs)
    builder.H2("1. 生命体征与心血管", before=8)
    for key in ("rhr", "sleep"):
        if key in text:
            builder.P(text[key])
    builder.H2("2. 心肺适能")
    if "vo2" in text:
        builder.P(text["vo2"])
    builder.H2("3. 活动与生活方式")
    if "steps" in text:
        builder.P(text["steps"])
    rings = findings.get("rings", {})
    if rings and all(rings.get(key) is not None for key in ("active", "exercise", "stand")):
        builder.P(f"三环完成率：活动 {rings['active'] * 100:.0f}%、锻炼 {rings['exercise'] * 100:.0f}%、"
                  f"站立 {rings['stand'] * 100:.0f}%。锻炼环完成率通常最低，说明“每天 30 分钟”尚未形成习惯。")
    audio = findings.get("audio", {}).get("hp_audio")
    if audio:
        builder.H2("4. 听力暴露")
        daily_mean = findings.get("metrics", {}).get("hp_audio", {}).get("mean", audio["mean"])
        builder.P(f"耳机日均 {daily_mean:.1f} dB，累计 {audio['hours_ge_80']:.0f} 小时 ≥80 dB、"
                  f"{audio['hours_ge_90']:.0f} 小时 ≥90 dB（最高 {audio['max']} dB）。"
                  "按 WHO-ITU 安全听音标准（80 dB / 40 小时每周），总量可控但集中在少数时段。")
    workouts = findings.get("workouts", {})
    if workouts.get("runs"):
        builder.H2("5. 运动表现")
        builder.P(f"记录到 {workouts['runs']} 次跑步，共 {workouts['run_km']:.1f} km、"
                  f"{workouts['run_hours']:.1f} 小时；中位配速 {values.get('run_pace', (None, '—'))[1]}。"
                  f"训练分布在 {', '.join(f'{m}: {km:.0f} km' for m, km in workouts['run_by_month'].items()) or '—'}。")

    # ---------------- attention ----------------
    builder.H("异常项汇总与处理建议", "五")
    table2 = builder.table(len(attention) + 1, 4, [4.0, 4.8, 2.8, 5.0])
    for column, label in enumerate(["项目", "本次结果", "处理级别", "建议"]):
        cell = table2.rows[0].cells[column]
        builder.shade(cell, BAND)
        builder.margins(cell, 75, 75, 100, 90)
        builder.cell_text(cell, label, 9, True, WHITE, WD_ALIGN_PARAGRAPH.CENTER)
    builder.no_split(table2.rows[0])
    builder.repeat_header(table2)
    for index, row in enumerate(attention, start=1):
        line = table2.rows[index]
        builder.no_split(line)
        level = "生活方式干预" if row["grade"] != UNDETECTED else "未检测"
        for column, text in enumerate((row["label"], row["value"], level, row["advice"] or "—")):
            cell = line.cells[column]
            builder.margins(cell, 60, 60, 100, 90)
            if column == 0:
                builder.cell_text(cell, text, 8.8, True, DARK)
            elif column == 3:
                builder.cell_text(cell, text, 8.2, False, DARK)
            elif column == 2:
                builder.cell_text(cell, text, 8.2, True, RATING_COLOR.get(level, GRAY),
                                  WD_ALIGN_PARAGRAPH.CENTER)
            else:
                builder.cell_text(cell, text, 8.8, False, DARK)
    builder.P("本次数据回顾未发现需要立即就医的急性异常。若出现胸痛、持续心悸、晕厥或静息气促，请直接就诊。",
              8.5, False, RED, before=6)

    # ---------------- plan ----------------
    builder.doc.add_page_break()
    builder.H("健康管理处方", "六", before=0)
    builder.P("按时间优先级排列，先做前两条，其余自然带动。", 9, False, GRAY)
    for phase, items in _plan(findings).items():
        paragraph = builder.P("", after=4, before=6)
        run = paragraph.add_run("▍" + phase)
        builder.font(run, 10.5, True, BLUE)
        for title, desc in items:
            builder.bullet(title + "：", desc)

    # ---------------- gaps ----------------
    builder.H("本次未覆盖的检查项目", "七")
    builder.P("可穿戴设备只能反映连续、无创、可自测的生理信号。以下项目必须由医疗机构完成：", after=4)
    gaps = builder.table(4, 4, [5.2, 3.1, 5.2, 3.1])
    for row_index, row in enumerate([("血压 / 血管弹性", "未检测", "血常规 / 血型", "未检测"),
                                     ("肝功能 / 肾功能", "未检测", "血脂 / 血糖", "未检测"),
                                     ("甲状腺功能", "未检测", "尿常规", "未检测"),
                                     ("胸片 / 低剂量 CT", "未检测", "腹部超声", "未检测")]):
        for column, text in enumerate(row):
            cell = gaps.rows[row_index].cells[column]
            builder.margins(cell, 65, 65, 110, 100)
            if column % 2 == 0:
                builder.shade(cell, LIGHT2)
                builder.cell_text(cell, text, 9, True, NAVY)
            else:
                builder.cell_text(cell, text, 9, False, LGRAY, WD_ALIGN_PARAGRAPH.CENTER)
        builder.no_split(gaps.rows[row_index])
    builder.P("另有眼科、口腔、外科查体、乙肝/结核筛查与疫苗接种史，建议在年度体检中一并完成。",
              8.5, False, GRAY, before=4)

    # ---------------- method ----------------
    builder.H("数据与方法说明", "八")
    builder.bullet("数据来源：", f"{os.path.basename(meta.get('source_path', 'export.xml'))}，"
                                f"导出时间 {meta.get('export_date') or '—'}。")
    builder.bullet("去重口径：", "同一时间窗内多设备会重复记录。按设备优先级（"
                                + " > ".join(meta.get("device_priority", [])) + "）做时间区间并集去重。")
    builder.bullet("统计口径：", "步数、距离、能量、时长为当日累加；心率、HRV、血氧取当日均值；"
                                "睡眠按醒来日期归档。")
    builder.bullet("参考范围：", "BMI 采用中国成人标准，睡眠采用 AASM 推荐，VO₂max 采用 FRIEND 百分位，"
                                "听音安全采用 WHO-ITU 标准。")
    builder.bullet("主要局限：", "设备更换前的数据不完整；手表指标为估算值；单导联心电图仅作筛查；"
                                "无血压、体重序列与临床检验数据。")

    builder.P("", after=6)
    rule2 = builder.doc.add_paragraph()
    builder.para_border(rule2, "top", LINEC, 8)
    builder.P("免责声明：本报告由程序对个人可穿戴设备数据自动统计生成，仅供健康管理与就医参考，"
              "不构成医学诊断、治疗建议或体检结论，未经执业医师审核。", 8.2, False, GRAY, before=4)

    builder.P("", after=14)
    end = builder.doc.add_paragraph()
    end.alignment = WD_ALIGN_PARAGRAPH.CENTER
    builder.para_border(end, "top", LINEC, 6, 1)
    run = end.add_run("— 报 告 结 束 —")
    builder.font(run, 9, False, LGRAY)

    builder.doc.save(path)
    return path


def _grade_rows(refs: Dict[str, Reference], values: Dict[str, Tuple[Optional[float], str]]) -> List[Dict]:
    rows = []
    for key, ref in refs.items():
        if key not in values:
            continue
        value, text = values[key]
        if key == "bed_time":
            grade = "参考"
        elif key == "audio_exposure":
            grade = "需关注"
        elif ref.low is None and ref.high is None and ref.caution_high is None and ref.caution_low is None:
            grade = "参考"
        else:
            grade = ref.grade(value)
        rows.append({
            "key": key,
            "group": ref.group,
            "label": ref.label_zh,
            "value": text,
            "reference": ref.text,
            "grade": grade,
            "severity": SEVERITY.get(grade, 0) if grade not in ("不规律",) else 1,
            "advice": ref.advice,
            "source": ref.source,
        })
    order = {group: index for index, group in enumerate(GROUPS)}
    rows.sort(key=lambda row: order.get(row["group"], 99))
    return rows


def _trend_sentence(findings: Dict) -> str:
    trend = findings.get("trend_28d", {})
    parts = []
    if "resting_hr" in trend:
        delta = trend["resting_hr"]["delta"]
        parts.append(f"静息心率{'下降' if delta < 0 else '上升'} {abs(delta):.0f} bpm")
    if "hrv" in trend:
        delta = trend["hrv"]["delta"]
        parts.append(f"HRV {'上升' if delta > 0 else '下降'} {abs(delta):.0f} ms")
    if "sleep_h" in trend:
        delta = trend["sleep_h"]["delta"]
        parts.append(f"睡眠{'增加' if delta > 0 else '减少'} {abs(delta):.1f} h")
    return "；".join(parts) + "。" if parts else "数据不足以判断趋势。"


def _plan(findings: Dict) -> Dict[str, List[Tuple[str, str]]]:
    plan: Dict[str, List[Tuple[str, str]]] = {
        "立即（本周内）": [
            ("设定睡眠锚点", "固定上床与起床时间，周末误差不超过 1 小时。"),
            ("耳机音量上限", "在手机设置中把耳机安全音量上限设为 80 dB。"),
            ("补齐基础数据", "每周固定时间称重并记录，便于校正基础代谢与 VO₂max。"),
        ],
        "1–4 周": [
            ("低强度有氧重启", "每周 3 次、每次 30 分钟，心率控制在能说短句的强度。"),
            ("每日步数下限", "把低于 5,000 步的日子补到 6,000 步以上。"),
            ("跑姿微调", "步频提高 5 步/分，步幅自然缩短，观察触地时间变化。"),
        ],
        "2–3 个月": [
            ("加入一次间歇", "如 6×400 m 快跑 + 200 m 慢走，每周 1 次。"),
            ("复测与对比", "8 周后对比静息心率、HRV、VO₂max 与睡眠时长。"),
            ("补齐临床体检", "完成血压、血常规、生化、腹部超声与眼科口腔检查。"),
        ],
    }
    return plan
