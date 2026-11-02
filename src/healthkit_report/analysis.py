"""Descriptive analysis of a parsed Apple Health dataset.

The output is a plain dictionary (JSON friendly) that the report renderers
consume.  Everything is derived from :func:`healthkit_report.parser.parse_export`
output, so analysis and rendering stay decoupled.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .metrics import METRICS

AIR = "\u2009"  # thin space, only used for formatting helpers


# --------------------------------------------------------------------------- #
# small statistics helpers
# --------------------------------------------------------------------------- #

def quantile(ordered: Sequence[float], p: float) -> float:
    """Linear-interpolated quantile (same convention as numpy's default)."""
    if not ordered:
        raise ValueError("empty sequence")
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * p
    low = int(math.floor(position))
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] * (1 - fraction) + ordered[high] * fraction


def describe(values: Sequence[float]) -> Optional[Dict[str, float]]:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mean = sum(ordered) / n
    variance = sum((v - mean) ** 2 for v in ordered) / n if n > 1 else 0.0

    return {
        "n": n,
        "mean": mean,
        "median": quantile(ordered, 0.5),
        "p10": quantile(ordered, 0.1),
        "p90": quantile(ordered, 0.9),
        "min": ordered[0],
        "max": ordered[-1],
        "sd": variance ** 0.5,
        "sum": sum(ordered),
    }


def pearson(pairs: Iterable[Tuple[float, float]]) -> Optional[float]:
    data = [(float(a), float(b)) for a, b in pairs]
    if len(data) < 8:
        return None
    mx = sum(a for a, _ in data) / len(data)
    my = sum(b for _, b in data) / len(data)
    num = sum((a - mx) * (b - my) for a, b in data)
    den = (sum((a - mx) ** 2 for a, _ in data) * sum((b - my) ** 2 for _, b in data)) ** 0.5
    return num / den if den else None


def _minutes(text: str) -> Optional[int]:
    try:
        hour, minute = text.split(":")
        return int(hour) * 60 + int(minute)
    except (ValueError, AttributeError):
        return None


# --------------------------------------------------------------------------- #
# analysis
# --------------------------------------------------------------------------- #

def analyze(dataset: Dict) -> Dict:
    """Compute the findings dictionary used by every renderer."""
    daily: Dict[str, Dict[str, float]] = dataset.get("daily", {})
    days = sorted(daily)
    if not days:
        raise ValueError("dataset contains no daily records")

    findings: Dict = {
        "schema": dataset.get("schema", 1),
        "source": dataset.get("meta", {}),
        "span": {"first": days[0], "last": days[-1], "days": len(days)},
        "metrics": {},
        "monthly": {},
        "trend_28d": {},
        "sleep": {},
        "workouts": {},
        "rings": {},
        "audio": {},
        "correlations": {},
        "coverage": {},
    }

    # ---- per metric descriptives -------------------------------------------
    for key, metric in METRICS.items():
        values = [d[key] for d in daily.values() if key in d]
        if not values:
            continue
        stats = describe(values)
        if stats is None:
            continue
        first = min(d for d, v in daily.items() if key in v)
        last = max(d for d, v in daily.items() if key in v)
        findings["metrics"][key] = {
            **stats,
            "unit": metric.unit,
            "digits": metric.digits,
            "label_zh": metric.label_zh,
            "label_en": metric.label_en,
            "first": first,
            "last": last,
        }

    # ---- sleep -------------------------------------------------------------
    nights = {d: rec for d, rec in dataset.get("sleep", {}).items() if rec.get("asleep", 0) >= 3.0}
    naps = {d: rec for d, rec in dataset.get("sleep", {}).items() if 0.5 < rec.get("asleep", 0) < 3.0}
    if nights:
        durations = [rec["asleep"] for rec in nights.values()]
        stats = describe(durations) or {}
        bed = [_minutes((rec.get("start") or "")[11:16]) for rec in nights.values()]
        bed = [b if b > 12 * 60 else b + 24 * 60 for b in bed if b is not None]
        wake = [_minutes((rec.get("end") or "")[11:16]) for rec in nights.values()]
        wake = [w for w in wake if w is not None]
        total = sum(durations) or 1.0
        weekday = [rec["asleep"] for d, rec in nights.items()
                   if date.fromisoformat(d).weekday() < 5]
        weekend = [rec["asleep"] for d, rec in nights.items()
                   if date.fromisoformat(d).weekday() >= 5]
        findings["sleep"] = {
            **stats,
            "n": len(nights),
            "lt6": sum(1 for v in durations if v < 6) / len(durations),
            "lt7": sum(1 for v in durations if v < 7) / len(durations),
            "ge8": sum(1 for v in durations if v >= 8) / len(durations),
            "deep": sum(rec["deep"] for rec in nights.values()) / len(nights),
            "rem": sum(rec["rem"] for rec in nights.values()) / len(nights),
            "core": sum(rec["core"] for rec in nights.values()) / len(nights),
            "awake": sum(rec["awake"] for rec in nights.values()) / len(nights),
            "deep_share": sum(rec["deep"] for rec in nights.values()) / total,
            "rem_share": sum(rec["rem"] for rec in nights.values()) / total,
            "bed_median": sorted(bed)[len(bed) // 2] if bed else None,
            "bed_sd": describe(bed)["sd"] if bed else None,
            "wake_median": sorted(wake)[len(wake) // 2] if wake else None,
            "weekday": sum(weekday) / len(weekday) if weekday else None,
            "weekend": sum(weekend) / len(weekend) if weekend else None,
            "naps": len(naps),
            "nap_hours": sum(rec["asleep"] for rec in naps.values()),
            "by_month": {
                month: sum(rec["asleep"] for d, rec in nights.items() if d.startswith(month))
                / max(1, sum(1 for d in nights if d.startswith(month)))
                for month in sorted({d[:7] for d in nights})
            },
        }

    # ---- monthly aggregates ------------------------------------------------
    monthly: Dict[str, Dict[str, float]] = {}
    for day, record in daily.items():
        month = day[:7]
        bucket = monthly.setdefault(month, {"days": 0})
        bucket["days"] += 1
        for key, value in record.items():
            if key.endswith("_n") or key in ("sleep_start", "sleep_end"):
                continue
            if key in METRICS or key in ("sleep_h", "deep_h", "rem_h", "core_h", "sleep_awake_h"):
                bucket.setdefault(key, []).append(value)  # type: ignore[arg-type]
    for bucket in monthly.values():
        for key in list(bucket):
            if isinstance(bucket[key], list):
                bucket[key] = sum(bucket[key]) / len(bucket[key])
    findings["monthly"] = dict(sorted(monthly.items()))

    # ---- 28 day comparison -------------------------------------------------
    def window(metric: str, start: str, length: int = 28) -> Optional[float]:
        end = (date.fromisoformat(start) + timedelta(days=length)).isoformat()
        values = [record[metric] for day, record in daily.items()
                  if start <= day < end and metric in record]
        return sum(values) / len(values) if values else None

    last_day = date.fromisoformat(days[-1])
    late_start = (last_day - timedelta(days=27)).isoformat()
    for metric in ("resting_hr", "hrv", "vo2max", "steps", "active_energy", "walk_speed", "sleep_h"):
        metric_days = [day for day, record in daily.items() if metric in record]
        if not metric_days:
            continue
        early = window(metric, min(metric_days))
        late = window(metric, late_start)
        if early is not None and late is not None:
            findings["trend_28d"][metric] = {"start": early, "end": late, "delta": late - early}

    # ---- workouts ----------------------------------------------------------
    workouts = dataset.get("workouts", [])
    real = [w for w in workouts if w.get("duration_min", 0) >= 5]
    runs = [w for w in real if w["type"] == "Running"]
    for workout in runs:
        distance = workout.get("distance") or 0.0
        if workout.get("distance_unit") in ("mi",):
            distance *= 1.609344
        workout["distance_km"] = distance
        if distance > 0.2:
            workout["pace_min_km"] = workout["duration_min"] / distance
    findings["workouts"] = {
        "total": len(workouts),
        "count": len(real),
        "hours": sum(w["duration_min"] for w in real) / 60.0,
        "by_type": Counter(w["type"] for w in real).most_common(),
        "runs": len(runs),
        "run_km": sum(w.get("distance_km", 0) for w in runs),
        "run_hours": sum(w["duration_min"] for w in runs) / 60.0,
        "run_by_month": _sum_by_month(runs, lambda w: w.get("distance_km", 0)),
        "run_pace_median": describe([w["pace_min_km"] for w in runs if w.get("pace_min_km")] or []),
        "run_hr": describe([w["statistics"].get("HeartRate", {}).get("average")
                            for w in runs if w["statistics"].get("HeartRate")] or []),
        "list": real,
    }

    # ---- activity rings ----------------------------------------------------
    activity = dataset.get("activity", [])
    if activity:
        # Only count days where the corresponding metric was actually recorded:
        # before the watch was paired, goals existed but nothing was measured.
        def scored_rows(goal_key: str, metric_key: str, value_key: str):
            rows = []
            for summary in activity:
                if not summary.get(goal_key):
                    continue
                if metric_key not in daily.get(summary["date"], {}):
                    continue
                rows.append(summary[value_key] >= summary[goal_key])
            return rows

        exercise = scored_rows("exercise_goal", "exercise_min", "exercise_min")
        stand = scored_rows("stand_goal", "stand_min", "stand_hours")
        active = scored_rows("active_goal", "active_energy", "active_energy")
        findings["rings"] = {
            "days": max(len(exercise), len(active)),
            "exercise": sum(exercise) / len(exercise) if exercise else None,
            "stand": sum(stand) / len(stand) if stand else None,
            "active": sum(active) / len(active) if active else None,
        }

    # ---- audio exposure ----------------------------------------------------
    audio = dataset.get("audio", {})
    for key in ("hp_audio", "env_audio"):
        histogram = {int(level): seconds for level, seconds in audio.get(key, {}).items()}
        if not histogram:
            continue
        total = sum(histogram.values())
        weighted = sum(level * seconds for level, seconds in histogram.items())
        ordered = sorted(histogram.items())
        findings["audio"][key] = {
            "hours_total": total / 3600.0,
            "mean": weighted / total if total else None,
            "hours_ge_80": sum(sec for level, sec in histogram.items() if level >= 80) / 3600.0,
            "hours_ge_90": sum(sec for level, sec in histogram.items() if level >= 90) / 3600.0,
            "max": ordered[-1][0] if ordered else None,
        }

    # ---- correlations ------------------------------------------------------
    def pair(a: str, b: str, shift_b_days: int = 0) -> Optional[float]:
        pairs = []
        for day, record in daily.items():
            if a not in record:
                continue
            other = (date.fromisoformat(day) + timedelta(days=shift_b_days)).isoformat()
            value = daily.get(other, {}).get(b)
            if value is not None:
                pairs.append((record[a], value))
        return pearson(pairs)

    findings["correlations"] = {
        "rhr_hrv": pair("resting_hr", "hrv"),
        "sleep_hrv": pair("sleep_h", "hrv"),
        "sleep_rhr": pair("sleep_h", "resting_hr"),
        "steps_rhr": pair("steps", "resting_hr"),
        "exercise_hrv": pair("exercise_min", "hrv"),
    }

    # ---- coverage ----------------------------------------------------------
    watch_days = sum(1 for record in daily.values() if record.get("hr_n"))
    watch_steps = [r["steps"] for r in daily.values() if r.get("hr_n") and "steps" in r]
    phone_steps = [r["steps"] for r in daily.values() if not r.get("hr_n") and "steps" in r]
    findings["coverage"] = {
        "days": len(daily),
        "days_with_heart_rate": watch_days,
        "first_watch_day": min((d for d, r in daily.items() if r.get("hr_n")), default=None),
        "metrics": {key: len([d for d, r in daily.items() if key in r]) for key in METRICS},
        # Steps/day split by device coverage: iPhone-only days (phone not always carried)
        # systematically undercount steps, so the whole-span mean underestimates habit.
        "steps_watch_mean": sum(watch_steps) / len(watch_steps) if watch_steps else None,
        "steps_phone_only_mean": sum(phone_steps) / len(phone_steps) if phone_steps else None,
    }
    findings["steps_distribution"] = _distribution(daily, "steps")
    findings["extreme_days"] = {
        "steps_top": _top(daily, "steps", 5),
        "steps_low": _top(daily, "steps", 5, reverse=True),
        "rhr_top": _top(daily, "resting_hr", 5),
        "hr_max_top": _top(daily, "hr_max", 5),
    }
    return findings


def _sum_by_month(workouts: List[Dict], selector) -> Dict[str, float]:
    result: Dict[str, float] = defaultdict(float)
    for workout in workouts:
        start = workout.get("start") or ""
        if start:
            result[start[:7]] += selector(workout)
    return dict(sorted(result.items()))


def _distribution(daily: Dict[str, Dict[str, float]], metric: str) -> Dict[str, float]:
    values = [record[metric] for record in daily.values() if metric in record]
    if not values:
        return {}
    return {
        "ge_10000": sum(1 for v in values if v >= 10000) / len(values),
        "ge_8000": sum(1 for v in values if v >= 8000) / len(values),
        "lt_5000": sum(1 for v in values if v < 5000) / len(values),
    }


def _top(daily: Dict[str, Dict[str, float]], metric: str, n: int, reverse: bool = False) -> List[List]:
    rows = [(day, record[metric]) for day, record in daily.items() if metric in record]
    rows.sort(key=lambda item: item[1], reverse=not reverse)
    return [[day, value] for day, value in rows[:n]]
