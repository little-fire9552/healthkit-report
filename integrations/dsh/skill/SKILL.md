---
name: healthkit-report
description: Apple 健康导出（export.xml）分析：多设备去重、指标统计、生成体检报告 DOCX/XLSX/HTML。当用户提到 Apple Watch / iPhone 健康数据、健康导出、体检报告、静息心率/HRV/睡眠/步数趋势时使用。
whenToUse: 用户提供或提到 apple_health_export、export.xml、Apple 健康数据、体检报告，或要求分析步数/心率/睡眠/HRV 趋势时。
---

# healthkit-report

把 Apple 健康导出（`export.xml`）变成去重后的数据集与体检报告。

## 先确认工具可用

```bash
command -v healthkit-report || python3 -m healthkit_report --version
```

如果提示找不到包，先安装（本地源码）：

```bash
pip install -e ~/Documents/deepseek-harness/default-workspace/healthkit-report
```

## 一条命令出全部结果

```bash
healthkit-report all "<导出的 export.xml 或解压目录>" -o out --name "<用户姓名>"
```

产出：`out/health-report.docx`、`out/health-report.xlsx`、`out/health-report.html`。

## 分步执行（需要复用中间结果时）

```bash
healthkit-report parse   export.xml -o dataset.json      # 解析 + 去重
healthkit-report analyze dataset.json -o findings.json   # 统计
healthkit-report report  dataset.json -o out --name 张三  # 出报告
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
f["metrics"]["steps"]["mean"]        # 日均步数
f["trend_28d"]["resting_hr"]["delta"]  # 最近 28 天静息心率变化
```

## 使用要点

- **不要直接对 XML 求和**：iPhone 与 Apple Watch 会重复记录同一段活动，必须用本工具的区间并集去重。
- 2026-01-31 之前若只有 iPhone 数据，则没有心率/HRV/睡眠，跨年比较需要说明。
- 报告是数据回顾，不是诊断；涉及症状建议就医，不要下医学结论。
- 生成后先打开 `health-report.html` 快速核对关键数字，再交付 DOCX/PDF。

## 常见问题

- **找不到 export.xml**：`ls ~/Downloads | grep -i apple_health`，或让用户重新在「健康 App → 头像 → 导出所有健康数据」导出并解压。
- **解析很慢**：`pip install lxml` 可提速 5–10 倍。
- **中文单位显示异常**：确认系统字体（PingFang SC）可用；DOCX 渲染由 Word/Pages 负责。
