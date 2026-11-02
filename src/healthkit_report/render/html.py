"""Self-contained HTML dashboard (no JavaScript, no external assets)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional, Sequence

from .svg import CHART_CSS, PALETTE, bar_chart, line_chart, multi_line_chart

_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei","Segoe UI","Helvetica Neue",Arial,sans-serif;margin:0;background:#f6f8fb;color:#1f2937}}
.wrap{{max-width:980px;margin:0 auto;padding:28px 20px 60px}}
h1{{font-size:24px;margin:0 0 6px}} .sub{{color:#6b7280;font-size:13px;margin-bottom:22px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:26px}}
.card{{background:#fff;border-radius:10px;padding:12px 14px;box-shadow:0 1px 3px rgba(16,24,40,.06)}}
.card .k{{font-size:11px;color:#6b7280}} .card .v{{font-size:20px;font-weight:600;margin-top:2px}}
.card .u{{font-size:11px;color:#9ca3af;margin-left:2px}}
section{{background:#fff;border-radius:12px;padding:16px 14px 6px;margin-bottom:18px;box-shadow:0 1px 3px rgba(16,24,40,.06)}}
section h2{{font-size:14px;margin:0 0 4px;color:#374151}}
section p{{font-size:12.5px;color:#4b5563;line-height:1.65;margin:2px 6px 10px}}
.note{{font-size:11.5px;color:#9ca3af;margin-top:18px;line-height:1.6}}
{chart_css}
</style></head><body><div class="wrap">
<h1>{title}</h1>
<div class="sub">{subtitle}</div>
<div class="cards">{cards}</div>
{sections}
<div class="note">{note}</div>
</div></body></html>"""


def _calendar_series(dataset: Dict, key: str, smooth: int = 0) -> Sequence:
    days = sorted(dataset.get("daily", {}))
    if not days:
        return [], []
    start, end = date.fromisoformat(days[0]), date.fromisoformat(days[-1])
    calendar = [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]
    values: List[Optional[float]] = []
    buffer: List[float] = []
    for day in calendar:
        value = dataset["daily"].get(day, {}).get(key)
        if smooth:
            if value is None:
                values.append(None)
                continue
            buffer.append(value)
            if len(buffer) > smooth:
                buffer.pop(0)
            values.append(sum(buffer) / len(buffer))
        else:
            values.append(value)
    return calendar, values


def _card(label: str, value: str, unit: str = "", hint: str = "") -> str:
    suffix = f'<span class="u">{unit}</span>' if unit else ""
    hint_html = f'<div class="u">{hint}</div>' if hint else ""
    return f'<div class="card"><div class="k">{label}</div><div class="v">{value}{suffix}</div>{hint_html}</div>'


def _section(title: str, text: str, chart: str) -> str:
    return f"<section><h2>{title}</h2><p>{text}</p>{chart}</section>"


def build_dashboard(
    dataset: Dict,
    findings: Dict,
    *,
    title: str = "Apple 健康数据面板",
    name: str = "",
) -> str:
    metrics = findings.get("metrics", {})
    sleep = findings.get("sleep", {})
    workouts = findings.get("workouts", {})
    days = findings["span"]

    cards = []
    steps = metrics.get("steps")
    if steps:
        cards.append(_card("日均步数", f"{steps['mean']:,.0f}", "步", f"中位 {steps['median']:,.0f}"))
    rhr = metrics.get("resting_hr")
    if rhr:
        oct_value = findings.get("monthly", {}).get(days["last"][:7], {}).get("resting_hr")
        cards.append(_card("静息心率", f"{rhr['mean']:.0f}", "bpm",
                           f"最近月 {oct_value:.0f}" if oct_value else ""))
    hrv = metrics.get("hrv")
    if hrv:
        cards.append(_card("HRV", f"{hrv['mean']:.0f}", "ms"))
    if sleep:
        cards.append(_card("日均睡眠", f"{sleep['mean']:.1f}", "h", f"{sleep['n']} 夜"))
    vo2 = metrics.get("vo2max")
    if vo2:
        cards.append(_card("VO₂max", f"{vo2['mean']:.0f}", "mL/min·kg"))
    if workouts.get("runs"):
        cards.append(_card("跑步", f"{workouts['run_km']:.0f}", "km", f"{workouts['runs']} 次"))

    sections = []

    # steps
    calendar, steps_smooth = _calendar_series(dataset, "steps", 7)
    chart = line_chart(list(zip(calendar, steps_smooth)), title="步数 7 日均线", ylabel="步/日",
                       color=PALETTE[0])
    dist = findings.get("steps_distribution", {})
    sections.append(_section(
        "步数",
        f"日均 {steps['mean']:,.0f} 步，{dist.get('ge_10000', 0) * 100:.0f}% 的天数过万，"
        f"{dist.get('lt_5000', 0) * 100:.0f}% 的天数不足 5,000。" if steps else "无步数数据",
        chart,
    ))

    # resting HR / HRV
    if rhr and hrv:
        cal_r, rhr_smooth = _calendar_series(dataset, "resting_hr", 7)
        cal_h, hrv_smooth = _calendar_series(dataset, "hrv", 7)
        chart = multi_line_chart(
            [("静息心率 7 日均", PALETTE[1], list(zip(cal_r, rhr_smooth))),
             ("HRV 7 日均", PALETTE[2], list(zip(cal_h, hrv_smooth)))],
            title="静息心率 vs HRV",
        )
        sections.append(_section(
            "静息心率与 HRV",
            f"静息心率均值 {rhr['mean']:.0f} bpm，HRV 均值 {hrv['mean']:.0f} ms；两者通常呈镜像关系。",
            chart,
        ))

    # hourly heart rate
    hourly = dataset.get("hourly", {}).get("hr", {})
    if hourly:
        labels = [f"{hour:02d}" for hour in range(24)]
        values = [hourly.get(f"{hour:02d}", 0) or hourly.get(hour, 0) for hour in range(24)]
        chart = bar_chart(labels, values, title="一天中不同时段的平均心率", color=PALETTE[5])
        sections.append(_section("心率昼夜节律", "柱高为该时段所有记录的平均心率。", chart))

    # sleep
    if sleep:
        cal_s, sleep_smooth = _calendar_series(dataset, "sleep_h", 7)
        chart = line_chart(list(zip(cal_s, sleep_smooth)), title="睡眠 7 夜均线", ylabel="小时",
                           color=PALETTE[3], band=(7, 9), value_fmt="{:.1f}")
        sections.append(_section(
            "睡眠",
            f"平均 {sleep['mean']:.2f} 小时，{sleep['lt7'] * 100:.0f}% 的夜晚不足 7 小时。"
            "灰带为 7–9 小时参考区间。",
            chart,
        ))

    # VO2max
    if vo2:
        cal_v, vo2_values = _calendar_series(dataset, "vo2max")
        chart = line_chart(list(zip(cal_v, vo2_values)), title="VO₂max 估算", ylabel="mL/min·kg",
                           color=PALETTE[4], dots=True, value_fmt="{:.1f}")
        sections.append(_section("VO₂max", "每次手表估算一个点；趋势比单点更有意义。", chart))

    # headphone level
    if "hp_audio" in metrics:
        cal_a, audio_values = _calendar_series(dataset, "hp_audio")
        chart = line_chart(list(zip(cal_a, audio_values)), title="耳机日均音量", ylabel="dB",
                           color=PALETTE[3])
        audio = findings.get("audio", {}).get("hp_audio", {})
        sections.append(_section(
            "耳机音量",
            f"日均 {audio.get('mean', 0):.1f} dB，累计 {audio.get('hours_ge_80', 0):.0f} 小时 ≥80 dB、"
            f"{audio.get('hours_ge_90', 0):.0f} 小时 ≥90 dB。",
            chart,
        ))

    # walking speed
    if "walk_speed" in metrics:
        cal_w, speed_values = _calendar_series(dataset, "walk_speed", 7)
        chart = line_chart(list(zip(cal_w, speed_values)), title="步行速度（7 日均线）",
                           ylabel="km/h", color=PALETTE[2], value_fmt="{:.1f}")
        sections.append(_section("步行速度", "长期下降可能与活动量减少有关。", chart))

    # monthly steps
    monthly = findings.get("monthly", {})
    labels = [m[2:].replace("-", "/") for m, row in monthly.items()
              if row.get("days", 0) >= 5 and "steps" in row]
    values = [row["steps"] for m, row in monthly.items() if row.get("days", 0) >= 5 and "steps" in row]
    if labels:
        chart = bar_chart(labels, values, title="月均每日步数", color=PALETTE[0])
        sections.append(_section("月度活动量", "仅统计数据完整（≥5 天）的月份。", chart))

    subtitle = f"{days['first']} – {days['last']} · {dataset.get('meta', {}).get('record_count', 0):,} 条记录"
    if name:
        subtitle = f"{name} · " + subtitle
    note = ("数据经多设备去重处理；报告仅用于个人回顾，不构成医学建议。"
            if not dataset.get("meta", {}).get("since") else "已按指定区间截取。")
    return _HTML.format(
        title=title,
        subtitle=subtitle,
        cards="".join(cards),
        sections="".join(sections),
        note=note,
        chart_css=CHART_CSS,
    )
