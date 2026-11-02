---
name: healthkit-report
description: Apple 健康导出（export.xml）分析：多设备去重、指标统计、生成体检报告 DOCX/XLSX/HTML。当用户提到 Apple Watch / iPhone 健康数据、健康导出、体检报告、静息心率/HRV/睡眠/步数趋势时使用。
whenToUse: 用户提供或提到 apple_health_export、export.xml、Apple 健康数据、体检报告，或要求分析步数/心率/睡眠/HRV 趋势时。
---

# healthkit-report

把 Apple 健康导出（`export.xml`）变成去重后的数据集与体检报告。
本技能对应的源码：`/Users/a0/Documents/deepseek-harness/default-workspace/healthkit-report`。

## 第 0 步：找到能用的 Python（每次先跑这段）

```bash
REPO=/Users/a0/Documents/deepseek-harness/default-workspace/healthkit-report
PY=$(ls -d "$HOME"/.dsh/dsh-runtimes/*/dependencies/python/bin/python3 2>/dev/null | head -1)
[ -z "$PY" ] && PY=$(command -v python3)
PYTHONPATH="$REPO/src" "$PY" -m healthkit_report --version || \
  echo "缺少依赖：pip install python-docx XlsxWriter lxml"
```

只有这条命令打印出版本号，才继续往下。后续命令都用同一个 `$PY` 和 `PYTHONPATH="$REPO/src"`。

## 一条命令出全部结果

```bash
PYTHONPATH="$REPO/src" "$PY" -m healthkit_report all "<export.xml 或解压目录>" -o out --name "<用户姓名>"
```

产出：`out/health-report.docx`、`out/health-report.xlsx`、`out/health-report.html`。

## 分步执行（需要复用中间结果时）

```bash
PYTHONPATH="$REPO/src" "$PY" -m healthkit_report parse   export.xml -o dataset.json
PYTHONPATH="$REPO/src" "$PY" -m healthkit_report analyze dataset.json -o findings.json
PYTHONPATH="$REPO/src" "$PY" -m healthkit_report report  dataset.json -o out --name 张三
```

## 关键参数

| 参数 | 说明 |
|---|---|
| `-o/--out` | 输出目录 |
| `--since/--until` | 日期过滤，如 `--since 2025-01-01` |
| `--name` | 报告上的姓名（可省略） |
| `--formats` | `docx,xlsx,html` 子集 |
| `--priority` | 设备优先级，默认 `Watch iPhone iPad Mac iPod` |

## 用 Python API 做二次分析

```python
from healthkit_report import parse_export, analyze
dataset = parse_export("export.xml")
f = analyze(dataset)
f["metrics"]["steps"]["mean"]          # 日均步数
f["trend_28d"]["resting_hr"]["delta"]  # 最近 28 天静息心率变化
```

## 使用要点

- **不要直接对 XML 求和**：iPhone 与 Apple Watch 会重复记录同一段活动，必须用本工具的区间并集去重。
- 若某段时间只有 iPhone 数据，则没有心率/HRV/睡眠，跨年比较需要说明。
- 报告是数据回顾，不是诊断；涉及症状建议就医，不要下医学结论。
- 生成后先打开 `health-report.html` 快速核对关键数字，再交付 DOCX。

## 常见问题

- **找不到 export.xml**：`ls ~/Downloads | grep -i apple_health`，或让用户重新在「健康 App → 头像 → 导出所有健康数据」导出并解压。
- **`No module named 'docx'`**：当前 Python 缺依赖，换 `$PY` 或用装了依赖的解释器。
- **解析很慢**：`pip install lxml` 可提速 5–10 倍。
- **源码目录被移动**：更新本文件里的 `REPO` 路径。
