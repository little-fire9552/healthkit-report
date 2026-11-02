"""Reference ranges, grading rules and follow-up advice.

Values are editorial defaults for healthy adults, not clinical cut-offs.  Every
row cites the source it comes from so users can check and override them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

NORMAL = "正常"
LOW = "偏低"
HIGH = "偏高"
ATTENTION = "需关注"
CRITICAL = "临界"
UNDETECTED = "未检测"

#: Grade → severity used for colouring and sorting.
SEVERITY = {
    NORMAL: 0,
    "参考": 0,
    UNDETECTED: -1,
    "正常偏高": 1,
    "正常偏低": 1,
    "不规律": 1,
    CRITICAL: 1,
    LOW: 2,
    HIGH: 2,
    ATTENTION: 2,
    "不足": 2,
    "偏慢": 2,
    "需注意": 2,
}


@dataclass
class Reference:
    key: str
    label_zh: str
    label_en: str
    group: str
    unit: str = ""
    low: Optional[float] = None
    high: Optional[float] = None
    text: str = "—"
    source: str = ""
    caution_high: Optional[float] = None
    caution_low: Optional[float] = None
    low_label: str = LOW
    high_label: str = HIGH
    advice: str = ""
    digits: int = 0
    note: str = ""

    def grade(self, value: Optional[float]) -> str:
        if value is None:
            return UNDETECTED
        if self.low is not None and value < self.low:
            return self.low_label
        if self.high is not None and value > self.high:
            return self.high_label
        if self.caution_high is not None and value > self.caution_high:
            return "正常偏高"
        if self.caution_low is not None and value < self.caution_low:
            return "正常偏低"
        return NORMAL


GROUPS = ["一般情况", "生命体征", "心血管功能", "心肺适能", "睡眠", "活动与生活方式", "听力", "步态与运动功能"]

#: 25th percentile of V̇O2max (mL·kg⁻¹·min⁻¹) from the FRIEND treadmill cohort,
#: keyed by sex and the lower bound of each age decade (Kaminsky et al., 2015).
FRIEND_P25: Dict[tuple, float] = {
    ("男", 20): 40.1, ("男", 30): 35.9, ("男", 40): 31.9,
    ("男", 50): 27.1, ("男", 60): 23.7, ("男", 70): 20.4,
    ("女", 20): 30.5, ("女", 30): 25.3, ("女", 40): 22.1,
    ("女", 50): 19.9, ("女", 60): 17.2, ("女", 70): 15.6,
}


def friend_p25(sex: str, age: Optional[int]) -> Optional[float]:
    """FRIEND 25th-percentile V̇O2max for a sex/age pair (None if unknown)."""

    if sex not in ("男", "女") or age is None:
        return None
    decade = 20 + max(0, min(5, (age - 20) // 10)) * 10
    return FRIEND_P25.get((sex, decade))


def default_references(sex: str = "", age: Optional[int] = None) -> List[Reference]:
    """The reference table shipped with the package.

    Sex- and age-dependent rows (waist circumference, V̇O2max) are personalised
    when ``sex``/``age`` are supplied; otherwise neutral defaults are kept.
    """

    vo2_low, vo2_text = 40.1, "成人第 25 百分位 40.1"
    percentile = friend_p25(sex, age)
    if percentile is not None:
        vo2_low = percentile
        vo2_text = f"同龄{sex}性第 25 百分位 {percentile:.1f}"
    waist_high, waist_text = (85, "女 <85 cm") if sex == "女" else (90, "男 <90 cm")

    return [
        Reference(
            "height", "身高", "Height", "一般情况", "cm", text="—", source="—", digits=0,
        ),
        Reference(
            "weight", "体重", "Body mass", "一般情况", "kg",
            low=18.5 * 1.83 ** 2, high=23.9 * 1.83 ** 2, text="按 BMI 18.5–23.9 折算",
            source="中国成人 BMI 分类", digits=1,
            advice="维持即可；若增重超过 BMI 24 需干预。",
        ),
        Reference(
            "bmi", "体质指数 BMI", "Body mass index", "一般情况", "",
            low=18.5, high=23.9, text="18.5–23.9", source="WS/T 428-2013（中国）", digits=1,
            advice="保持在 18.5–23.9 之间。",
        ),
        Reference("waist", "腰围", "Waist circumference", "一般情况", "cm",
                  high=waist_high, text=waist_text,
                  source="中国成人中心性肥胖标准", digits=0),
        Reference(
            "resting_hr", "静息心率", "Resting heart rate", "生命体征", "bpm",
            low=60, high=100, text="60–100 次/分", source="成人静息心率常用区间", digits=0,
            caution_high=65, advice="有氧训练可进一步降低静息心率。",
        ),
        Reference(
            "hr", "平均心率（全天）", "Average heart rate", "生命体征", "bpm",
            low=60, high=100, text="60–100 次/分", source="—", digits=0,
        ),
        Reference(
            "spo2", "血氧饱和度", "Oxygen saturation", "生命体征", "%",
            low=95, high=100, text="95–100%", source="临床常用界值", low_label=ATTENTION, digits=1,
            advice="若持续低于 94% 并伴气促，建议就医。",
        ),
        Reference(
            "resp_rate", "呼吸频率", "Respiratory rate", "生命体征", "次/分",
            low=12, high=20, text="12–20 次/分", source="—", digits=1,
        ),
        Reference("bp", "血压", "Blood pressure", "生命体征", "mmHg", text="<120/80", source="—",
                  note="手表不测血压，需用袖带式血压计"),
        Reference("temp", "体温", "Body temperature", "生命体征", "℃", text="36.0–37.2",
                  source="—", note="手腕温度不等于核心体温"),
        Reference(
            "hrv", "HRV（SDNN）", "HRV (SDNN)", "心血管功能", "ms",
            text="无统一界值，看个体趋势", source="—", digits=1,
        ),
        Reference(
            "hr_recovery", "心率恢复（1 分钟）", "Heart-rate recovery", "心血管功能", "bpm",
            low=12, text="≥12 次/分", source="常用界值", digits=0, low_label=ATTENTION,
        ),
        Reference(
            "walking_hr", "步行平均心率", "Walking heart rate", "心血管功能", "bpm",
            text="—", source="—", digits=0,
        ),
        Reference(
            "vo2max", "VO₂max 估算", "VO₂ max estimate", "心肺适能", "mL/min/kg",
            low=vo2_low, text=vo2_text, source="FRIEND / Apple 心肺适能",
            digits=1, advice="每周 3 次 30 分钟低强度有氧，8 周后复测。",
        ),
        Reference(
            "sleep_h", "平均睡眠时长", "Sleep duration", "睡眠", "小时",
            low=7, high=9, text="7–9 小时", source="AASM 成人推荐", low_label="不足", digits=2,
            advice="固定起床时间，目标 7.5 小时。",
        ),
        Reference(
            "deep_share", "深睡占比", "Deep sleep share", "睡眠", "%",
            low=13, high=23, text="13–23%", source="成人睡眠结构参考", digits=0,
        ),
        Reference(
            "rem_share", "REM 占比", "REM share", "睡眠", "%",
            low=20, high=25, text="20–25%", source="成人睡眠结构参考", digits=0,
        ),
        Reference(
            "bed_time", "入睡时间（中位）", "Median bedtime", "睡眠", "",
            text="—", source="—", note="规律性比时长更值得关注",
        ),
        Reference(
            "steps", "日均步数", "Daily steps", "活动与生活方式", "步",
            low=7000, text="≥7,000–10,000 步", source="公共健康建议", digits=0,
            low_label="不足", advice="把久坐日补到 6,000 步以上。",
        ),
        Reference(
            "exercise_min", "日均锻炼时间", "Exercise minutes", "活动与生活方式", "分钟",
            low=30, text="≥30 分钟", source="WHO 150 分钟/周", digits=0, low_label=CRITICAL,
            advice="每周 ≥150 分钟中等强度活动。",
        ),
        Reference("stand_min", "日均站立时间", "Stand minutes", "活动与生活方式", "分钟",
                  text="—", source="—", digits=0),
        Reference("active_energy", "日均活动能量", "Active energy", "活动与生活方式", "kcal",
                  text="—", source="—", digits=0),
        Reference(
            "daylight_min", "日均日照时间", "Time in daylight", "活动与生活方式", "分钟",
            low=30, text="≥30 分钟", source="—", digits=0,
        ),
        Reference(
            "hp_audio", "耳机日均音量", "Headphone level", "听力", "dB",
            high=80, text="长期 <80 dB", source="WHO-ITU 安全听音", digits=1,
            advice="在 iPhone 中把耳机音量上限设为 80 dB。",
        ),
        Reference(
            "audio_exposure", "高音量累计暴露", "Loud exposure", "听力", "",
            text="80 dB ≤40 小时/周", source="WHO-ITU", note="累计 ≥80 dB 与 ≥90 dB 时长",
            advice="避免在嘈杂环境中用大音量盖过噪声。",
        ),
        Reference(
            "walk_speed", "步行速度", "Walking speed", "步态与运动功能", "km/h",
            low=4.3, high=5.2, text="4.3–5.2 km/h", source="成人步行速度参考", low_label="偏慢",
            digits=2, advice="每天 10 分钟快走（能说话但不能唱歌）。",
        ),
        Reference("step_len", "步长", "Step length", "步态与运动功能", "cm", text="—", source="—",
                  digits=1),
        Reference("dbl_support", "双支撑占比", "Double support", "步态与运动功能", "%",
                  text="越低越高效", source="—", digits=1),
        Reference(
            "asymmetry", "步行不对称", "Walking asymmetry", "步态与运动功能", "%",
            high=5, text="<5%", source="临床常用界值", digits=1,
        ),
        Reference(
            "steadiness", "步行稳定性", "Walking steadiness", "步态与运动功能", "%",
            low=80, text="≥80%", source="Apple 步行稳定性分级", digits=0,
        ),
        Reference("run_pace", "跑步配速", "Running pace", "步态与运动功能", "/km",
                  text="—", source="—"),
        Reference("run_cadence", "跑步步频", "Running cadence", "步态与运动功能", "步/分",
                  text="—", source="—", digits=0),
    ]


def profile_from_dataset(dataset: Dict) -> Dict:
    """Best-effort profile (age/sex) from HealthKit ``Me`` plus a stored weight."""
    me = dataset.get("meta", {}).get("me", {})
    dob = me.get("HKCharacteristicTypeIdentifierDateOfBirth")
    age = None
    if dob:
        try:
            born = date.fromisoformat(dob)
            today = date.today()
            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        except ValueError:
            age = None
    sex_raw = me.get("HKCharacteristicTypeIdentifierBiologicalSex", "")
    sex = {"HKBiologicalSexMale": "男", "HKBiologicalSexFemale": "女"}.get(sex_raw, "未填写")
    weight = None
    height = None
    # Latest measurement wins: earlier records may be stale (e.g. height 167 -> 168).
    for day in sorted(dataset.get("daily", {})):
        record = dataset["daily"][day]
        if "weight" in record:
            weight = record["weight"]
        if "height" in record:
            height = record["height"]
    return {
        "name": "",
        "sex": sex,
        "age": age,
        "birth_date": dob,
        "height_cm": height,
        "weight_kg": weight,
    }
