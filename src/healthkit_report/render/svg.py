"""Tiny dependency-free SVG chart toolkit.

The charts are plain strings so they can be embedded in an HTML dashboard
without matplotlib, Javascript or external assets.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

PALETTE = ["#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed", "#0891b2", "#db2777"]

Point = Tuple[str, Optional[float]]


def esc(text: object) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def nice_range(low: float, high: float, ticks: int = 4) -> Tuple[float, float, float]:
    if high <= low:
        high = low + 1.0
    raw = (high - low) / max(1, ticks)
    magnitude = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    norm = raw / magnitude
    step = magnitude * (1 if norm <= 1.5 else 2 if norm <= 3 else 5 if norm <= 7 else 10)
    start = math.floor(low / step) * step
    end = math.ceil(high / step) * step
    if low >= 0:
        start = max(0.0, start)
    return start, end, step


def tick_values(low: float, high: float, step: float) -> List[float]:
    values = []
    value = low
    while value <= high + step * 0.001:
        values.append(round(value, 6))
        value += step
    return values


def _trim(points: Sequence[Point]) -> List[Point]:
    data = list(points)
    indexes = [i for i, (_, v) in enumerate(data) if v is not None]
    if not indexes:
        return data
    return data[indexes[0]: indexes[-1] + 1]


def _fmt_date(day: str) -> str:
    return day[5:].replace("-", "/") if len(day) >= 10 else day


def _fmt_value(value: float, pattern: str) -> str:
    try:
        return pattern.format(value)
    except (ValueError, IndexError):
        return f"{value:,.0f}"


def line_chart(
    points: Sequence[Point],
    *,
    title: str = "",
    ylabel: str = "",
    width: int = 860,
    height: int = 250,
    color: str = PALETTE[0],
    band: Optional[Tuple[float, float]] = None,
    dots: bool = False,
    value_fmt: str = "{:,.0f}",
    x_ticks: int = 6,
) -> str:
    data = _trim(points)
    values = [v for _, v in data if v is not None]
    if not values:
        return ""
    pad_l, pad_r, pad_t, pad_b = 54, 14, 26, 30
    inner_w, inner_h = width - pad_l - pad_r, height - pad_t - pad_b
    low, high = min(values), max(values)
    span = high - low or 1.0
    low, high, step = nice_range(low - span * 0.06, high + span * 0.06)

    def x_at(i: int) -> float:
        return pad_l + inner_w * i / max(1, len(data) - 1)

    def y_at(v: float) -> float:
        return pad_t + inner_h - (v - low) / (high - low) * inner_h

    out = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" aria-label="{esc(title)}">',
           f'<rect width="{width}" height="{height}" fill="#ffffff"/>']
    if band:
        band_low, band_high = band
        top, bottom = y_at(min(band_high, high)), y_at(max(band_low, low))
        out.append(f'<rect x="{pad_l}" y="{top:.1f}" width="{inner_w}" '
                   f'height="{max(1.0, bottom - top):.1f}" fill="#f1f5f9"/>')
    for value in tick_values(low, high, step):
        y = y_at(value)
        out.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width - pad_r}" y2="{y:.1f}" '
                   f'stroke="#e8edf3" stroke-width="1"/>')
        out.append(f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" class="ylab">'
                   f'{_fmt_value(value, value_fmt)}</text>')
    step_x = max(1, len(data) // x_ticks)
    for i in range(0, len(data), step_x):
        out.append(f'<text x="{x_at(i):.1f}" y="{height - 10}" text-anchor="middle" class="xlab">'
                   f'{esc(_fmt_date(data[i][0]))}</text>')

    segment: List[Tuple[float, float]] = []

    def flush() -> None:
        if len(segment) > 1:
            path = f"M{segment[0][0]:.1f},{segment[0][1]:.1f}" + "".join(
                f"L{x:.1f},{y:.1f}" for x, y in segment[1:])
            out.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.6" '
                       f'stroke-linejoin="round"/>')

    for i, (_, value) in enumerate(data):
        if value is None:
            flush()
            segment = []
        else:
            segment.append((x_at(i), y_at(value)))
    flush()

    if dots:
        for i, (_, value) in enumerate(data):
            if value is not None:
                out.append(f'<circle cx="{x_at(i):.1f}" cy="{y_at(value):.1f}" r="2.2" fill="{color}"/>')
    out.append(f'<text x="{pad_l}" y="16" class="ctitle">{esc(title)}</text>')
    if ylabel:
        out.append(f'<text x="{width - pad_r}" y="16" text-anchor="end" class="ylab">{esc(ylabel)}</text>')
    out.append("</svg>")
    return "".join(out)


def multi_line_chart(
    series: Sequence[Tuple[str, str, Sequence[Point]]],
    *,
    title: str = "",
    width: int = 860,
    height: int = 280,
    value_fmt: str = "{:,.0f}",
    x_ticks: int = 6,
) -> str:
    if not series:
        return ""
    lengths = [len(_trim(points)) for _, _, points in series]
    length = max(lengths)
    aligned = []
    for name, color, points in series:
        data = _trim(points)
        aligned.append((name, color, data[-length:] if len(data) >= length else data))
    dates = aligned[0][2]
    values = [v for _, _, points in aligned for _, v in points if v is not None]
    if not values:
        return ""
    pad_l, pad_r, pad_t, pad_b = 54, 14, 36, 30
    inner_w, inner_h = width - pad_l - pad_r, height - pad_t - pad_b
    low, high = min(values), max(values)
    span = high - low or 1.0
    low, high, step = nice_range(low - span * 0.06, high + span * 0.06)

    def x_at(i: int) -> float:
        return pad_l + inner_w * i / max(1, length - 1)

    def y_at(v: float) -> float:
        return pad_t + inner_h - (v - low) / (high - low) * inner_h

    out = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" aria-label="{esc(title)}">',
           f'<rect width="{width}" height="{height}" fill="#ffffff"/>']
    for value in tick_values(low, high, step):
        y = y_at(value)
        out.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width - pad_r}" y2="{y:.1f}" stroke="#e8edf3"/>')
        out.append(f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" class="ylab">'
                   f'{_fmt_value(value, value_fmt)}</text>')
    step_x = max(1, length // x_ticks)
    for i in range(0, length, step_x):
        out.append(f'<text x="{x_at(i):.1f}" y="{height - 10}" text-anchor="middle" class="xlab">'
                   f'{esc(_fmt_date(dates[i][0]))}</text>')

    for _name, color, points in aligned:
        segment: List[Tuple[float, float]] = []

        def flush(segment=segment, color=color) -> None:
            if len(segment) > 1:
                path = f"M{segment[0][0]:.1f},{segment[0][1]:.1f}" + "".join(
                    f"L{x:.1f},{y:.1f}" for x, y in segment[1:])
                out.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.8"/>')

        for i, (_, value) in enumerate(points):
            if value is None:
                flush()
                segment = []
            else:
                segment.append((x_at(i), y_at(value)))
        flush()

    out.append(f'<text x="{pad_l}" y="18" class="ctitle">{esc(title)}</text>')
    for index, (name, color, _points) in enumerate(aligned):
        top = 24 + index * 16
        out.append(f'<rect x="{width - pad_r - 160}" y="{top}" width="9" height="9" fill="{color}"/>')
        out.append(f'<text x="{width - pad_r - 146}" y="{top + 8}" class="legend">{esc(name)}</text>')
    out.append("</svg>")
    return "".join(out)


def bar_chart(
    labels: Sequence[str],
    values: Sequence[float],
    *,
    title: str = "",
    width: int = 860,
    height: int = 220,
    color: str = "#0d9488",
    value_fmt: str = "{:,.0f}",
) -> str:
    if not values:
        return ""
    pad_l, pad_r, pad_t, pad_b = 54, 14, 26, 34
    inner_w, inner_h = width - pad_l - pad_r, height - pad_t - pad_b
    low = min(min(values), 0)
    high = max(values)
    span = (high - low) or 1.0
    low, high, step = nice_range(max(0.0, low - span * 0.05), high + span * 0.12, ticks=3)
    bar_width = inner_w / len(values) * 0.72

    def y_at(v: float) -> float:
        return pad_t + inner_h - (v - low) / (high - low) * inner_h

    out = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" aria-label="{esc(title)}">',
           f'<rect width="{width}" height="{height}" fill="#ffffff"/>']
    for value in tick_values(low, high, step):
        y = y_at(value)
        out.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width - pad_r}" y2="{y:.1f}" stroke="#e8edf3"/>')
        out.append(f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" class="ylab">'
                   f'{_fmt_value(value, value_fmt)}</text>')
    for index, (label, value) in enumerate(zip(labels, values)):
        x = pad_l + inner_w * (index + 0.5) / len(values) - bar_width / 2
        top = y_at(value)
        out.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{bar_width:.1f}" '
                   f'height="{pad_t + inner_h - top:.1f}" fill="{color}" rx="2"/>')
        out.append(f'<text x="{x + bar_width / 2:.1f}" y="{height - 12}" text-anchor="middle" '
                   f'class="xlab">{esc(label)}</text>')
        out.append(f'<text x="{x + bar_width / 2:.1f}" y="{top - 5:.1f}" text-anchor="middle" '
                   f'class="ylab">{_fmt_value(value, value_fmt)}</text>')
    out.append(f'<text x="{pad_l}" y="16" class="ctitle">{esc(title)}</text>')
    out.append("</svg>")
    return "".join(out)


CHART_CSS = """
svg.chart{width:100%;height:auto;display:block}
.ctitle{font-size:12px;fill:#374151;font-weight:600}
.ylab{font-size:10px;fill:#9ca3af}
.xlab{font-size:10px;fill:#9ca3af}
.legend{font-size:11px;fill:#4b5563}
"""
