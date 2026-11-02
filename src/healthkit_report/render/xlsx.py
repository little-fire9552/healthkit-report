"""Excel workbook output (概览 / 每日指标 / 月度汇总 / 训练记录 / 睡眠 / 数据说明)."""

from __future__ import annotations

from datetime import date
from typing import Dict

import xlsxwriter


COLUMNS = [
    ("日期", "date", 11),
    ("步数", "steps", 9),
    ("步行+跑步 km", "walk_dist", 11),
    ("活动能量 kcal", "active_energy", 12),
    ("静息能量 kcal", "basal_energy", 12),
    ("锻炼分钟", "exercise_min", 10),
    ("站立分钟", "stand_min", 10),
    ("日照分钟", "daylight_min", 10),
    ("心率均值", "hr", 9),
    ("心率最低", "hr_min", 9),
    ("心率最高", "hr_max", 9),
    ("静息心率", "resting_hr", 9),
    ("HRV ms", "hrv", 9),
    ("步行心率", "walking_hr", 9),
    ("呼吸频率", "resp_rate", 9),
    ("血氧 %", "spo2", 8),
    ("步行速度 km/h", "walk_speed", 11),
    ("步长 cm", "step_len", 8),
    ("双支撑 %", "dbl_support", 9),
    ("不对称 %", "asymmetry", 9),
    ("稳定性 %", "steadiness", 9),
    ("VO₂max", "vo2max", 8),
    ("睡眠 h", "sleep_h", 8),
    ("深睡 h", "deep_h", 8),
    ("REM h", "rem_h", 8),
    ("耳机音量 dB", "hp_audio", 11),
    ("环境音量 dB", "env_audio", 11),
]


def build_workbook(dataset: Dict, findings: Dict, path: str, *, name: str = "") -> str:
    workbook = xlsxwriter.Workbook(path)
    header = workbook.add_format({"bold": True, "bg_color": "#1e3a5f", "font_color": "white",
                                 "border": 1, "align": "center", "valign": "vcenter",
                                 "text_wrap": True})
    cell = workbook.add_format({"border": 1, "num_format": "0.0"})
    integer = workbook.add_format({"border": 1, "num_format": "0"})
    datef = workbook.add_format({"border": 1, "num_format": "yyyy-mm-dd"})
    titlef = workbook.add_format({"bold": True, "font_size": 14})
    notef = workbook.add_format({"text_wrap": True, "valign": "top"})

    metrics = findings.get("metrics", {})
    span = findings["span"]
    meta = dataset.get("meta", {})

    # ---- overview ---------------------------------------------------------
    sheet = workbook.add_worksheet("概览")
    sheet.set_column("A:A", 24)
    sheet.set_column("B:B", 72)
    sheet.write(0, 0, "健康数据概览", titlef)
    rows = [
        ("数据来源", meta.get("source_path", "")),
        ("导出时间", meta.get("export_date") or "—"),
        ("数据区间", f"{span['first']} 至 {span['last']}（{span['days']} 天）"),
        ("记录总数", f"{meta.get('record_count', 0):,} 条"),
        ("设备优先级", " > ".join(meta.get("device_priority", []))),
    ]
    if name:
        rows.insert(0, ("姓名", name))
    for key, label in (("steps", "平均每日步数"), ("resting_hr", "平均静息心率"),
                       ("hrv", "平均 HRV（SDNN）"), ("vo2max", "VO₂max 估算")):
        if key in metrics:
            rows.append((label, f"{metrics[key]['mean']:.1f} {metrics[key].get('unit', '')}".strip()))
    sleep = findings.get("sleep", {})
    if sleep:
        rows.append(("平均睡眠", f"{sleep['mean']:.2f} 小时/夜（{sleep['n']} 夜）"))
    workouts = findings.get("workouts", {})
    if workouts:
        rows.append(("训练记录", f"{workouts['count']} 次，{workouts['hours']:.1f} 小时"))
        rows.append(("跑步", f"{workouts['runs']} 次，{workouts['run_km']:.1f} km"))
    for index, (key, value) in enumerate(rows, start=2):
        sheet.write(index, 0, key, header)
        sheet.write(index, 1, str(value), notef)

    # ---- daily ------------------------------------------------------------
    daily_sheet = workbook.add_worksheet("每日指标")
    daily_sheet.write(0, 0, "每日指标（多设备重复记录已去重）", titlef)
    for column, (label, _key, width) in enumerate(COLUMNS):
        daily_sheet.write(1, column, label, header)
        daily_sheet.set_column(column, column, width)
    daily = dataset.get("daily", {})
    for row, day in enumerate(sorted(daily), start=2):
        record = daily[day]
        daily_sheet.write_datetime(row, 0, date.fromisoformat(day), datef)
        for column, (_label, key, _width) in enumerate(COLUMNS[1:], start=1):
            value = record.get(key)
            if value is None:
                daily_sheet.write_blank(row, column, None, cell)
            elif key in ("steps", "hr_min", "hr_max"):
                daily_sheet.write_number(row, column, value, integer)
            else:
                daily_sheet.write_number(row, column, value, cell)
    daily_sheet.freeze_panes(2, 1)
    daily_sheet.autofilter(1, 0, len(daily) + 1, len(COLUMNS) - 1)
    if daily:
        chart = workbook.add_chart({"type": "line"})
        chart.add_series({
            "name": "步数",
            "categories": ["每日指标", 2, 0, len(daily) + 1, 0],
            "values": ["每日指标", 2, 1, len(daily) + 1, 1],
            "line": {"color": "#2563eb", "width": 0.75},
        })
        chart.set_title({"name": "每日步数"})
        chart.set_size({"width": 880, "height": 240})
        daily_sheet.insert_chart("AA2", chart)

    # ---- monthly ----------------------------------------------------------
    monthly_sheet = workbook.add_worksheet("月度汇总")
    monthly_columns = ["月份", "天数", "步数/日", "步行距离 km/日", "活动能量 kcal/日",
                       "锻炼分钟/日", "静息心率", "HRV ms", "睡眠 h", "步行速度 km/h"]
    keys = ["month", "days", "steps", "walk_dist", "active_energy", "exercise_min",
            "resting_hr", "hrv", "sleep_h", "walk_speed"]
    for column, (label, key) in enumerate(zip(monthly_columns, keys)):
        monthly_sheet.write(0, column, label, header)
        monthly_sheet.set_column(column, column, 14)
    for row, (month, record) in enumerate(sorted(findings.get("monthly", {}).items()), start=1):
        monthly_sheet.write(row, 0, month)
        for column, key in enumerate(keys[1:], start=1):
            value = record.get(key)
            if value is None:
                monthly_sheet.write_blank(row, column, None, cell)
            elif key == "days":
                monthly_sheet.write_number(row, column, value, integer)
            else:
                monthly_sheet.write_number(row, column, value, cell)

    # ---- workouts ---------------------------------------------------------
    workout_sheet = workbook.add_worksheet("训练记录")
    headers = ["开始时间", "类型", "时长 min", "距离 km", "活动能量 kcal", "平均心率", "最高心率",
               "配速 min/km", "步频 spm", "步幅 m", "触地时间 ms", "垂直振幅 cm", "功率 W", "来源"]
    for column, label in enumerate(headers):
        workout_sheet.write(0, column, label, header)
        workout_sheet.set_column(column, column, 12)
    for row, workout in enumerate(sorted(dataset.get("workouts", []), key=lambda w: w.get("start") or ""), start=1):
        stats = workout.get("statistics", {})
        distance = workout.get("distance") or 0.0
        energy = workout.get("energy") or 0.0
        heart = stats.get("HeartRate", {})
        steps = (stats.get("StepCount") or {}).get("sum")
        workout_sheet.write(row, 0, (workout.get("start") or "")[:16])
        workout_sheet.write(row, 1, workout.get("type", ""))
        workout_sheet.write_number(row, 2, workout.get("duration_min", 0), cell)
        workout_sheet.write_number(row, 3, distance, cell)
        workout_sheet.write_number(row, 4, energy, cell)
        for column, value in ((5, heart.get("average")), (6, heart.get("maximum"))):
            if value is None:
                workout_sheet.write_blank(row, column, None, cell)
            else:
                workout_sheet.write_number(row, column, value, cell)
        if distance > 0.2 and workout.get("type") == "Running":
            workout_sheet.write_number(row, 7, workout["duration_min"] / distance, cell)
        else:
            workout_sheet.write_blank(row, 7, None, cell)
        if steps and workout.get("duration_min"):
            workout_sheet.write_number(row, 8, steps / workout["duration_min"], cell)
        else:
            workout_sheet.write_blank(row, 8, None, cell)
        for column, key in ((9, "RunningStrideLength"), (10, "RunningGroundContactTime"),
                            (11, "RunningVerticalOscillation"), (12, "RunningPower")):
            value = (stats.get(key) or {}).get("average")
            if value is None:
                workout_sheet.write_blank(row, column, None, cell)
            else:
                workout_sheet.write_number(row, column, value, cell)
        workout_sheet.write(row, 13, workout.get("source", ""))
    workout_sheet.freeze_panes(1, 0)

    # ---- sleep ------------------------------------------------------------
    sleep_sheet = workbook.add_worksheet("睡眠")
    sleep_headers = ["夜晚(醒来日期)", "入睡", "起床", "总睡眠 h", "核心 h", "深睡 h", "REM h", "清醒 h", "卧床 h"]
    for column, label in enumerate(sleep_headers):
        sleep_sheet.write(0, column, label, header)
        sleep_sheet.set_column(column, column, 14)
    for row, (night, record) in enumerate(sorted(dataset.get("sleep", {}).items()), start=1):
        sleep_sheet.write(row, 0, night)
        sleep_sheet.write(row, 1, (record.get("start") or "")[11:16])
        sleep_sheet.write(row, 2, (record.get("end") or "")[11:16])
        for column, key in ((3, "asleep"), (4, "core"), (5, "deep"), (6, "rem"), (7, "awake"), (8, "inbed")):
            sleep_sheet.write_number(row, column, record.get(key, 0.0), cell)
    sleep_sheet.freeze_panes(1, 0)

    # ---- notes ------------------------------------------------------------
    notes_sheet = workbook.add_worksheet("数据说明")
    notes_sheet.set_column("A:A", 120)
    notes = [
        "数据处理说明",
        "",
        "1. 本表由 healthkit-report 从 Apple 健康导出的 export.xml 生成。",
        "2. 去重：同一时间窗内 iPhone 与 Apple Watch 会各写一条记录。本表按设备优先级做时间区间并集去重，"
        "只保留未被高优先级设备覆盖的时间段（详见 docs/algorithm.md）。",
        "3. 校验：去重后的每日活动能量可与系统“健身记录”三环对照，正常情况下误差 <1%。",
        "4. 心率、HRV、血氧、呼吸频率取当日均值；步数、距离、能量、时长为当日累加。",
        "5. 睡眠按醒来日期归档；跨午夜长睡眠计入醒来当天。",
        "6. 手表测量值（VO₂max、血氧、手腕温度）为估算，不能替代临床检验。",
    ]
    for row, text in enumerate(notes):
        notes_sheet.write(row, 0, text, titlef if row == 0 else notef)

    workbook.close()
    return path
