# Contributing

Thanks for taking a look! Issues and pull requests are welcome.

## 开发环境

```bash
git clone https://github.com/your-name/healthkit-report.git
cd healthkit-report
python -m venv .venv && source .venv/bin/activate
pip install -e ".[fast,dev]"
```

## 运行测试

```bash
python -m unittest discover -s tests -v
# 或者
pytest -q
```

测试使用 `tests/fixtures/mini_export.xml`，一个手工构造的最小导出文件，
覆盖了双设备重复计步、睡眠分期、训练统计与三环数据。**不要提交真实健康数据。**

## 代码风格

- `ruff check src tests`（配置在 `pyproject.toml`）
- 类型标注尽量完整，公共函数写 docstring
- 新增指标请同时更新：`metrics.py`、`references.py`（如果可评价）、
  `docs/metrics.md`、以及一个测试

## 提交 PR

1. Fork 并开分支：`git checkout -b feat/my-metric`
2. 提交前跑一遍测试与 ruff
3. PR 描述里说明动机、数据来源与对现有报告的影响
4. 涉及报告版式的改动，请附一张渲染截图

## 翻译

报告文案目前只有中文。若你想加英文版，建议把 `render/docx.py` 中的字符串
抽到 `render/i18n.py`，用 `t(key)` 统一获取，然后提交 PR。
