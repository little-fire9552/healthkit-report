# healthkit-report · DSH 插件

安装后在 DSH 中提供 `healthkit_report` 工具。

## 前置

```bash
python3 -m pip install -e /path/to/healthkit-report
python3 -m healthkit_report --version
```

如果用的解释器不同，安装插件后设置环境变量 `HEALTHKIT_PYTHON=/path/to/python3`。

## 安装

在 DSH Web 的 **Plugins** 页面选择安装本地 bundle，填本目录的绝对路径；
或让 Creator 模式的 agent 调用：

```text
plugin_manager action=install_bundle target=/absolute/path/to/healthkit-report-plugin
```

## 使用

```text
healthkit_report action=all   export=/path/to/export.xml out=out
healthkit_report action=parse export=/path/to/export.xml out=dataset.json
healthkit_report action=report dataset=/path/to/dataset.json out=out formats=docx,html
```

## 更新

改 `index.js` 后重启 DSH；只改 `locale/*.json` 或 `cordis.patch.yml` 时重新安装即可。
