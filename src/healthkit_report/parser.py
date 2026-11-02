"""Streaming parser for Apple Health ``export.xml`` with multi-device de-duplication.

The exported archive contains one ``Record`` per sample **per source**.  When an
iPhone and an Apple Watch both count the same walk, the raw file double counts.
Apple's own apps show a de-duplicated number, which this module reproduces by
merging time intervals per metric and per day, preferring the device with the
highest priority (Watch > iPhone > third-party apps by default).

See ``docs/algorithm.md`` for the reasoning and the trade-offs.
"""

from __future__ import annotations

import hashlib
import json
import os
from bisect import bisect_left
from datetime import datetime
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .metrics import (
    HK_TO_METRIC,
    METRICS,
    SLEEP_ASLEEP,
    SLEEP_AWAKE,
    SLEEP_HK,
    SLEEP_INBED,
    Metric,
    normalize_value,
)

SCHEMA_VERSION = 1

try:  # pragma: no cover - optional accelerator
    from lxml import etree as _etree
    _HAVE_LXML = True
except Exception:  # pragma: no cover
    import xml.etree.ElementTree as _etree
    _HAVE_LXML = False


def iter_elements(source, tags: Sequence[str]) -> Iterable[object]:
    """Yield top-level elements with the given tags, clearing memory as we go.

    ``source`` may be a path or an open binary file.  Uses ``lxml`` when
    available (5-10x faster) and falls back to the standard library.
    """
    tag = tags[0] if len(tags) == 1 else tuple(tags)
    context = _etree.iterparse(source, events=("end",), tag=tag, huge_tree=True) if _HAVE_LXML \
        else _etree.iterparse(source, events=("end",))
    for _, el in context:
        yield el
        parent = el.getparent() if hasattr(el, "getparent") else None
        if _HAVE_LXML and parent is not None and parent.tag != "HealthData":
            # Nested records (inside a Workout) are cleared but their siblings
            # must stay intact so workout statistics survive.
            el.clear()
            continue
        el.clear()
        if parent is not None:
            while el.getprevious() is not None:
                del parent[0]


def _ts(value: str) -> float:
    return datetime.fromisoformat(value).timestamp()


def _day(value: str) -> str:
    return value[:10]


class DevicePriority:
    """Rank data sources so overlapping records can be resolved deterministically."""

    def __init__(self, patterns: Optional[Sequence[str]] = None) -> None:
        self.patterns = list(patterns or ["Watch", "iPhone", "iPad", "Mac", "iPod"])

    def rank(self, source: str) -> int:
        for index, pattern in enumerate(self.patterns):
            if pattern.lower() in (source or "").lower():
                return len(self.patterns) - index
        return 0


class _Coverage:
    """Union of time intervals, backed by two parallel sorted lists."""

    __slots__ = ("starts", "ends")

    def __init__(self) -> None:
        self.starts: List[float] = []
        self.ends: List[float] = []

    def covered(self, start: float, end: float) -> float:
        if end <= start:
            return 0.0
        idx = bisect_left(self.starts, start) - 1
        idx = max(idx, 0)
        total = 0.0
        while idx < len(self.starts):
            s, e = self.starts[idx], self.ends[idx]
            if s >= end:
                break
            lo, hi = max(s, start), min(e, end)
            if hi > lo:
                total += hi - lo
            idx += 1
        return total

    def add(self, start: float, end: float) -> None:
        if end <= start:
            return
        idx = bisect_left(self.starts, start)
        # merge with the previous interval when they touch
        if idx > 0 and self.ends[idx - 1] >= start:
            idx -= 1
            start = min(start, self.starts[idx])
            end = max(end, self.ends[idx])
            del self.starts[idx]
            del self.ends[idx]
        while idx < len(self.starts) and self.starts[idx] <= end:
            end = max(end, self.ends[idx])
            del self.starts[idx]
            del self.ends[idx]
        self.starts.insert(idx, start)
        self.ends.insert(idx, end)


def _parse_record(el, priority: DevicePriority, into: Dict, meta: Dict) -> None:
    attrs = el.attrib
    hk_type = attrs.get("type", "")
    source = attrs.get("sourceName", "")
    start = attrs.get("startDate")
    if not start:
        return
    end = attrs.get("endDate", start)
    meta["counts"][hk_type] = meta["counts"].get(hk_type, 0) + 1

    if hk_type == SLEEP_HK:
        into["sleep_raw"].append((start, end, attrs.get("value", ""), priority.rank(source)))
        return

    metric = METRICS.get(HK_TO_METRIC.get(hk_type, ""))
    if metric is None:
        return
    raw = attrs.get("value")
    if raw is None:
        return
    try:
        value = normalize_value(metric, float(raw), attrs.get("unit"))
    except ValueError:
        return

    day = _day(start)
    into["records"].setdefault(metric.key, {}).setdefault(day, []).append(
        (_ts(start), _ts(end), value, priority.rank(source), start[11:13])
    )
    if metric.key in ("hp_audio", "env_audio"):
        seconds = max(0.0, _ts(end) - _ts(start))
        buckets = into["audio"].setdefault(metric.key, {})
        level = int(value)  # floor: a 79.9 dB sample is not an 80 dB sample
        buckets[level] = buckets.get(level, 0.0) + seconds

    bucket = into["meta_source"].setdefault(metric.key, {})
    bucket[source] = bucket.get(source, 0) + 1


def _parse_workout(el) -> Optional[Dict]:
    attrs = el.attrib
    duration = float(attrs.get("duration", 0) or 0)
    unit = attrs.get("durationUnit", "min")
    duration_min = duration * 60.0 if unit in ("hr", "h") else duration
    workout = {
        "type": attrs.get("workoutActivityType", "").replace("HKWorkoutActivityType", ""),
        "start": attrs.get("startDate"),
        "end": attrs.get("endDate"),
        "duration_min": duration_min,
        "distance": float(attrs.get("totalDistance", 0) or 0),
        "distance_unit": attrs.get("totalDistanceUnit", ""),
        "energy": float(attrs.get("totalEnergyBurned", 0) or 0),
        "energy_unit": attrs.get("totalEnergyBurnedUnit", ""),
        "source": attrs.get("sourceName", ""),
        "statistics": {},
    }
    for child in el:
        if child.tag == "WorkoutStatistics":
            stat_type = child.get("type", "").replace("HKQuantityTypeIdentifier", "")
            workout["statistics"][stat_type] = {
                key: float(child.get(key))
                for key in ("sum", "average", "minimum", "maximum")
                if child.get(key) is not None
            }
    for key, target in (("DistanceWalkingRunning", "distance"), ("DistanceCycling", "distance"),
                        ("ActiveEnergyBurned", "energy")):
        stat = workout["statistics"].get(key)
        if stat and stat.get("sum") and not workout[target]:
            workout[target] = stat["sum"]
            if key.startswith("Distance"):
                workout["distance_unit"] = "km"
    return workout


def _parse_activity(el) -> Dict:
    attrs = el.attrib
    return {
        "date": (attrs.get("dateComponents") or "")[:10],
        "active_energy": float(attrs.get("activeEnergyBurned", 0) or 0),
        "active_goal": float(attrs.get("activeEnergyBurnedGoal", 0) or 0),
        "exercise_min": float(attrs.get("appleExerciseTime", 0) or 0),
        "exercise_goal": float(attrs.get("appleExerciseTimeGoal", 0) or 0),
        "stand_hours": float(attrs.get("appleStandHours", 0) or 0),
        "stand_goal": float(attrs.get("appleStandHoursGoal", 0) or 0),
    }


def _finalize_daily(raw: Dict[str, Dict[str, list]]) -> Tuple[Dict[str, Dict[str, float]], Dict]:
    """Collapse per-day record lists into one value per metric (plus hourly HR)."""
    daily: Dict[str, Dict[str, float]] = {}
    hourly_acc: Dict[str, Dict[str, list]] = {}
    for key, by_day in raw.items():
        metric: Metric = METRICS[key]
        for day, records in by_day.items():
            target = daily.setdefault(day, {})
            if metric.is_sum:
                cover = _Coverage()
                total = 0.0
                for start, end, value, rank, _hour in sorted(records, key=lambda r: (-r[3], r[0])):
                    end = max(end, start + 1.0)
                    already = cover.covered(start, end)
                    fraction = max(0.0, 1.0 - already / (end - start))
                    total += value * fraction
                    cover.add(start, end)
                target[key] = total
            else:
                # For rates/levels one sample per minute is enough; the best
                # device wins so a third-party app cannot bias the mean.
                seen: Dict[int, Tuple[float, str]] = {}
                for start, end, value, rank, hour in sorted(records, key=lambda r: (-r[3], r[0])):
                    minute = int(round(start / 60.0))
                    if minute not in seen:
                        seen[minute] = (value, hour)
                values = [v for v, _h in seen.values()]
                if not values:
                    continue
                target[key] = sum(values) / len(values)
                target[key + "_n"] = len(values)
                if key == "hr":
                    for value, hour in seen.values():
                        acc = hourly_acc.setdefault(hour, [0.0, 0])
                        acc[0] += value
                        acc[1] += 1
                    ordered = sorted(values)
                    target["hr_min"] = ordered[0]
                    target["hr_max"] = ordered[-1]
                    target["hr_p10"] = ordered[max(0, int(len(ordered) * 0.1))]
                    target["hr_p90"] = ordered[min(len(ordered) - 1, int(len(ordered) * 0.9))]
    hourly = {hour: acc[0] / acc[1] for hour, acc in sorted(hourly_acc.items()) if acc[1]}
    return daily, hourly


def _finalize_sleep(sleep_raw: List[Tuple[str, str, str, int]]) -> Dict[str, Dict[str, float]]:
    """One sleep record per night, attributed to the wake-up date."""
    per_night: Dict[str, Dict[int, Dict[str, float]]] = {}
    for start, end, value, rank in sleep_raw:
        night = _day(end)
        bucket = per_night.setdefault(night, {}).setdefault(
            rank,
            {"inbed": 0.0, "awake": 0.0, "core": 0.0, "deep": 0.0, "rem": 0.0,
             "asleep": 0.0, "start": None, "end": None},
        )
        try:
            hours = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() / 3600.0
        except ValueError:
            continue
        if value == SLEEP_INBED:
            bucket["inbed"] += hours
        elif value == SLEEP_AWAKE:
            bucket["awake"] += hours
        elif value in SLEEP_ASLEEP:
            bucket["asleep"] += hours
            if value.endswith("Core"):
                bucket["core"] += hours
            elif value.endswith("Deep"):
                bucket["deep"] += hours
            elif value.endswith("REM"):
                bucket["rem"] += hours
            if bucket["start"] is None or start < bucket["start"]:
                bucket["start"] = start
            if bucket["end"] is None or end > bucket["end"]:
                bucket["end"] = end

    sleep: Dict[str, Dict[str, float]] = {}
    for night, by_source in per_night.items():
        best_rank = max(by_source, key=lambda r: (by_source[r]["asleep"], r))
        record = dict(by_source[best_rank])
        record["source_priority"] = best_rank
        sleep[night] = record
    return sleep


def parse_export(
    path: str,
    *,
    since: Optional[str] = None,
    until: Optional[str] = None,
    device_priority: Optional[Sequence[str]] = None,
    progress: Optional[Callable[[int], None]] = None,
) -> Dict:
    """Parse an Apple Health export into a JSON-serialisable dataset.

    Parameters
    ----------
    path:
        ``export.xml`` (or an unzipped ``apple_health_export`` directory).
    since / until:
        Inclusive ``YYYY-MM-DD`` bounds applied to the record start date.
    device_priority:
        Substrings ranked best-first, e.g. ``["Watch", "iPhone"]``.
    progress:
        Optional callback receiving the number of parsed records.
    """
    if os.path.isdir(path):
        candidate = os.path.join(path, "export.xml")
        if not os.path.exists(candidate):
            candidate = os.path.join(path, "导出.xml")
        path = candidate
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    priority = DevicePriority(device_priority)
    meta: Dict = {
        "export_date": None,
        "me": {},
        "record_count": 0,
        "counts": {},
    }
    into: Dict = {"records": {}, "sleep_raw": [], "meta_source": {}, "audio": {}}
    workouts: List[Dict] = []
    activity: List[Dict] = []
    devices: Dict[str, int] = {}

    handle = open(path, "rb")
    for el in iter_elements(handle, ("Record", "Workout", "ActivitySummary", "Me", "ExportDate")):
        tag = el.tag
        if tag == "Record":
            meta["record_count"] += 1
            start = el.get("startDate") or ""
            if (since and start[:10] < since) or (until and start[:10] > until):
                continue
            device = el.get("device") or ""
            if device:
                devices[device] = devices.get(device, 0) + 1
            _parse_record(el, priority, into, meta)
            if progress and meta["record_count"] % 50000 == 0:
                progress(meta["record_count"])
        elif tag == "Workout":
            start = el.get("startDate") or ""
            if (since and start[:10] < since) or (until and start[:10] > until):
                continue
            workout = _parse_workout(el)
            if workout:
                workouts.append(workout)
        elif tag == "ActivitySummary":
            summary = _parse_activity(el)
            if (not since or summary["date"] >= since) and (not until or summary["date"] <= until):
                activity.append(summary)
        elif tag == "Me":
            meta["me"] = dict(el.attrib)
        elif tag == "ExportDate":
            meta["export_date"] = el.get("value")
    handle.close()

    daily, hourly = _finalize_daily(into["records"])
    sleep = _finalize_sleep(into["sleep_raw"])
    for night, record in sleep.items():
        if record["asleep"] <= 0.5:  # a handful of minutes is a nap or bad data
            continue
        day = daily.setdefault(night, {})
        day["sleep_h"] = record["asleep"]
        day["deep_h"] = record["deep"]
        day["rem_h"] = record["rem"]
        day["core_h"] = record["core"]
        day["sleep_awake_h"] = record["awake"]
        if record["start"]:
            day["sleep_start"] = record["start"][11:16]
        if record["end"]:
            day["sleep_end"] = record["end"][11:16]

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    dataset = {
        "schema": SCHEMA_VERSION,
        "meta": {
            "source_path": os.path.abspath(path),
            "source_sha256": digest.hexdigest(),
            "source_bytes": os.path.getsize(path),
            "parsed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "export_date": meta["export_date"],
            "me": meta["me"],
            "record_count": meta["record_count"],
            "type_counts": dict(sorted(meta["counts"].items(), key=lambda kv: -kv[1])),
            "sources": {k: dict(sorted(v.items(), key=lambda kv: -kv[1])[:8])
                        for k, v in into["meta_source"].items()},
            "devices": dict(sorted(devices.items(), key=lambda kv: -kv[1])[:12]),
            "device_priority": priority.patterns,
            "since": since,
            "until": until,
        },
        "daily": {day: daily[day] for day in sorted(daily)},
        "hourly": {"hr": hourly},
        "sleep": sleep,
        "workouts": workouts,
        "activity": activity,
        "audio": {k: {str(level): round(sec) for level, sec in sorted(v.items())}
                  for k, v in into["audio"].items()},
    }
    return dataset


def save_dataset(dataset: Dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(dataset, handle, ensure_ascii=False, indent=1)


def load_dataset(path: str) -> Dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
