# dsh-healthkit-report

一个 DeepSeek Harness 插件：把 Apple 健康导出（`export.xml`）变成去重后的体检报告。

安装后，DSH 里会多出一个 `healthkit_report` 工具。

## 别人怎么用

本仓库已内置 Python 源码（`python/` 目录），别人**不需要**再装 healthkit-report 本体，
只需要两个第三方库：

```bash
python3 -m pip install python-docx XlsxWriter
```

然后在 DSH 里装插件：

   - 打开左侧 **插件** → 右上角 **添加插件**；
   - 粘贴本仓库地址或本地目录的绝对路径；
   - 安装完成后，插件列表出现「Apple 健康报告」。

## 用法

在任意会话里说：

> 帮我分析 Apple 健康数据，生成体检报告

或者直接让 agent 调用：

```text
healthkit_report action=all export=/path/to/export.xml out=out
```

## 参数

| 参数 | 说明 |
|---|---|
| `action` | `parse` / `analyze` / `report` / `all` |
| `export` | export.xml 或解压目录的绝对路径 |
| `dataset` | `parse` 产出的 dataset.json（`analyze`/`report` 用） |
| `out` | 输出路径 |
| `patient_name` | 报告上的姓名 |
| `formats` | `docx,xlsx,html` 子集 |
| `since` / `until` | 日期过滤 |
| `python` | 指定解释器（默认 `HEALTHKIT_PYTHON` 或 `python3`） |

## 如果报 `No module named 'docx'`

说明当前 `python3` 没装依赖：

```bash
python3 -m pip install python-docx XlsxWriter
```

或者在插件调用时传 `python=/path/to/python3`。

## 开发

```bash
npm pack --dry-run   # 看会打包哪些文件
```

改动 `index.js` 后需要重启 DSH 才会生效。

## License

MIT
