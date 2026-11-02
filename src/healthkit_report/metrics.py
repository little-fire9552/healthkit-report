"""Metric definitions for Apple Health records.

Every HealthKit quantity type that this package understands is mapped to a
:class:`Metric` with a canonical unit and an aggregation rule. Two records with
the same time window coming from different devices are aggregated with the
de-duplication strategy described in ``docs/algorithm.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional


@dataclass(frozen=True)
class Metric:
    """One canonical metric derived from one or more HealthKit types."""

    key: str
    label_zh: str
    label_en: str
    unit: str
    agg: str = "sum"  # "sum" or "mean"
    kind: str = "quantity"  # quantity | category
    percent_from_fraction: bool = False
    digits: int = 0

    @property
    def is_sum(self) -> bool:
        return self.agg == "sum"


# --------------------------------------------------------------------------- #
# Canonical metrics
# --------------------------------------------------------------------------- #

METRICS: Dict[str, Metric] = {}
HK_TO_METRIC: Dict[str, str] = {}


def _add(hk_types: Iterable[str], metric: Metric) -> None:
    METRICS[metric.key] = metric
    for hk in hk_types:
        HK_TO_METRIC[hk] = metric.key


_add(
    ["HKQuantityTypeIdentifierStepCount"],
    Metric("steps", "步数", "Steps", "count", digits=0),
)
_add(
    ["HKQuantityTypeIdentifierDistanceWalkingRunning"],
    Metric("walk_dist", "步行+跑步距离", "Walking/running distance", "km", digits=1),
)
_add(
    ["HKQuantityTypeIdentifierDistanceCycling"],
    Metric("cycle_dist", "骑行距离", "Cycling distance", "km", digits=1),
)
_add(
    ["HKQuantityTypeIdentifierActiveEnergyBurned"],
    Metric("active_energy", "活动能量", "Active energy", "kcal", digits=0),
)
_add(
    ["HKQuantityTypeIdentifierBasalEnergyBurned"],
    Metric("basal_energy", "静息能量", "Basal energy", "kcal", digits=0),
)
_add(
    ["HKQuantityTypeIdentifierFlightsClimbed"],
    Metric("flights", "爬楼层数", "Flights climbed", "count", digits=0),
)
_add(
    ["HKQuantityTypeIdentifierAppleExerciseTime"],
    Metric("exercise_min", "锻炼时间", "Exercise minutes", "min", digits=0),
)
_add(
    ["HKQuantityTypeIdentifierAppleStandTime"],
    Metric("stand_min", "站立时间", "Stand minutes", "min", digits=0),
)
_add(
    ["HKQuantityTypeIdentifierTimeInDaylight"],
    Metric("daylight_min", "日照时间", "Time in daylight", "min", digits=0),
)
_add(
    ["HKQuantityTypeIdentifierHeartRate"],
    Metric("hr", "心率", "Heart rate", "bpm", agg="mean", digits=0),
)
_add(
    ["HKQuantityTypeIdentifierRestingHeartRate"],
    Metric("resting_hr", "静息心率", "Resting heart rate", "bpm", agg="mean", digits=0),
)
_add(
    ["HKQuantityTypeIdentifierWalkingHeartRateAverage"],
    Metric("walking_hr", "步行平均心率", "Walking heart rate", "bpm", agg="mean", digits=0),
)
_add(
    ["HKQuantityTypeIdentifierHeartRateVariabilitySDNN"],
    Metric("hrv", "HRV (SDNN)", "Heart rate variability (SDNN)", "ms", agg="mean", digits=1),
)
_add(
    ["HKQuantityTypeIdentifierHeartRateRecoveryOneMinute"],
    Metric("hr_recovery", "心率恢复", "Heart rate recovery", "bpm", agg="mean", digits=0),
)
_add(
    ["HKQuantityTypeIdentifierRespiratoryRate"],
    Metric("resp_rate", "呼吸频率", "Respiratory rate", "breaths/min", agg="mean", digits=1),
)
_add(
    ["HKQuantityTypeIdentifierOxygenSaturation"],
    Metric("spo2", "血氧饱和度", "Oxygen saturation", "%", agg="mean",
           percent_from_fraction=True, digits=1),
)
_add(
    ["HKQuantityTypeIdentifierBodyMass"],
    Metric("weight", "体重", "Body mass", "kg", agg="mean", digits=1),
)
_add(
    ["HKQuantityTypeIdentifierHeight"],
    Metric("height", "身高", "Height", "cm", agg="mean", digits=0),
)
_add(
    ["HKQuantityTypeIdentifierBodyMassIndex"],
    Metric("bmi", "BMI", "Body mass index", "kg/m2", agg="mean", digits=1),
)
_add(
    ["HKQuantityTypeIdentifierVO2Max"],
    Metric("vo2max", "最大摄氧量", "VO2 max", "mL/min/kg", agg="mean", digits=1),
)
_add(
    ["HKQuantityTypeIdentifierAppleSleepingWristTemperature"],
    Metric("wrist_temp", "手腕温度", "Sleeping wrist temperature", "degC", agg="mean", digits=2),
)
_add(
    ["HKQuantityTypeIdentifierAppleSleepingBreathingDisturbances"],
    Metric("breath_disturb", "睡眠呼吸紊乱", "Sleeping breathing disturbances", "count", agg="mean", digits=1),
)
_add(
    ["HKQuantityTypeIdentifierWalkingSpeed"],
    Metric("walk_speed", "步行速度", "Walking speed", "km/h", agg="mean", digits=2),
)
_add(
    ["HKQuantityTypeIdentifierWalkingStepLength"],
    Metric("step_len", "步长", "Walking step length", "cm", agg="mean", digits=1),
)
_add(
    ["HKQuantityTypeIdentifierWalkingDoubleSupportPercentage"],
    Metric("dbl_support", "双支撑占比", "Double support percentage", "%", agg="mean",
           percent_from_fraction=True, digits=1),
)
_add(
    ["HKQuantityTypeIdentifierWalkingAsymmetryPercentage"],
    Metric("asymmetry", "步行不对称", "Walking asymmetry", "%", agg="mean",
           percent_from_fraction=True, digits=1),
)
_add(
    ["HKQuantityTypeIdentifierAppleWalkingSteadiness"],
    Metric("steadiness", "步行稳定性", "Walking steadiness", "%", agg="mean",
           percent_from_fraction=True, digits=1),
)
_add(
    ["HKQuantityTypeIdentifierEnvironmentalAudioExposure"],
    Metric("env_audio", "环境音量", "Environmental audio level", "dB", agg="mean", digits=1),
)
_add(
    ["HKQuantityTypeIdentifierHeadphoneAudioExposure"],
    Metric("hp_audio", "耳机音量", "Headphone audio level", "dB", agg="mean", digits=1),
)
_add(
    ["HKQuantityTypeIdentifierRunningSpeed"],
    Metric("run_speed", "跑步速度", "Running speed", "km/h", agg="mean", digits=2),
)
_add(
    ["HKQuantityTypeIdentifierRunningPower"],
    Metric("run_power", "跑步功率", "Running power", "W", agg="mean", digits=0),
)
_add(
    ["HKQuantityTypeIdentifierRunningStrideLength"],
    Metric("run_stride", "跑步步幅", "Running stride length", "m", agg="mean", digits=2),
)
_add(
    ["HKQuantityTypeIdentifierRunningVerticalOscillation"],
    Metric("run_vert_osc", "垂直振幅", "Vertical oscillation", "cm", agg="mean", digits=2),
)
_add(
    ["HKQuantityTypeIdentifierRunningGroundContactTime"],
    Metric("run_gct", "触地时间", "Ground contact time", "ms", agg="mean", digits=0),
)

SLEEP_HK = "HKCategoryTypeIdentifierSleepAnalysis"

#: Sleep stages Apple writes into ``value``.
SLEEP_ASLEEP = frozenset(
    {
        "HKCategoryValueSleepAnalysisAsleep",
        "HKCategoryValueSleepAnalysisAsleepCore",
        "HKCategoryValueSleepAnalysisAsleepDeep",
        "HKCategoryValueSleepAnalysisAsleepREM",
        "HKCategoryValueSleepAnalysisAsleepUnspecified",
    }
)
SLEEP_INBED = "HKCategoryValueSleepAnalysisInBed"
SLEEP_AWAKE = "HKCategoryValueSleepAnalysisAwake"

#: Derived daily keys that look like ordinary metrics so that reports can treat
#: them uniformly.
DERIVED_METRICS: Dict[str, Metric] = {
    "sleep_h": Metric("sleep_h", "睡眠时长", "Sleep duration", "h", agg="mean", digits=2),
    "deep_h": Metric("deep_h", "深睡", "Deep sleep", "h", agg="mean", digits=2),
    "rem_h": Metric("rem_h", "REM", "REM sleep", "h", agg="mean", digits=2),
    "core_h": Metric("core_h", "核心睡眠", "Core sleep", "h", agg="mean", digits=2),
}

#: Canonical units used for sanity checks / conversion.
UNIT_ALIASES = {
    "kcal": "kcal",
    "cal": "kcal",
    "Cal": "kcal",
    "km": "km",
    "mi": "mi",
    "m": "m",
    "min": "min",
    "hr": "hr",
    "h": "hr",
    "s": "s",
    "count": "count",
    "count/min": "count/min",
    "cm": "cm",
    "m/s": "m/s",
    "km/hr": "km/hr",
    "km/h": "km/hr",
    "mi/hr": "mi/hr",
    "ms": "ms",
    "degC": "degC",
    "degF": "degF",
    "%": "%",
    "kcal/hr·kg": "kcal/hr·kg",
    "dBASPL": "dBASPL",
    "dB": "dBASPL",
    "W": "W",
    "kg": "kg",
    "lb": "lb",
    "mL/min·kg": "mL/min/kg",
}


def metric_for_hk(hk_type: str) -> Optional[Metric]:
    key = HK_TO_METRIC.get(hk_type)
    return METRICS.get(key) if key else None


def normalize_value(metric: Metric, value: float, unit: Optional[str]) -> float:
    """Convert a raw HealthKit value to the metric's canonical unit.

    HealthKit stores values in the unit declared on the record, which differs
    between apps (``Cal``/``kcal``, ``km``/``mi``, ``min``/``hr``, ``degC``/``degF``).
    Percentages are stored as fractions in some types and as 0-100 in others.
    """

    unit = UNIT_ALIASES.get(unit or "", unit)
    if metric.key in ("active_energy", "basal_energy"):
        if unit == "kcal":
            return value
        return value
    if metric.key in ("walk_dist", "cycle_dist"):
        if unit == "mi":
            return value * 1.609344
        return value
    if metric.key in ("exercise_min", "stand_min", "daylight_min"):
        if unit == "hr":
            return value * 60.0
        return value
    if metric.key in ("weight",):
        if unit == "lb":
            return value * 0.45359237
        return value
    if metric.key in ("hp_audio", "env_audio"):
        return value
    if metric.percent_from_fraction:
        # Apple stores these as 0-1 with a "%" unit; a few third-party apps write 0-100.
        return value * 100.0 if abs(value) <= 1.5 else value
    return value


def all_metrics() -> Dict[str, Metric]:
    return {**METRICS, **DERIVED_METRICS}
