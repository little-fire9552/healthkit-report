# 把 healthkit-report 接进 DeepSeek Harness

DSH 里有三种扩展形态，先分清再动手：

| 形态 | 是什么 | 放在哪 | 生效方式 | 适合 |
|---|---|---|---|---|
| **Skill（技能）** | 一个 `SKILL.md` | `<项目>/.dsh/skills/<name>/`、`~/.dsh/skills/<name>/` 或 `.agents/skills` | 自动发现，**不用重启**（有文件监听） | 让 agent 学会用你的 CLI |
| **Bundle（插件包）** | npm 包 + `cordis.patch.yml`，可注册工具/面板 | 通过 Plugins 页面或 `plugin_manager` 装进 profile | 安装后 HMR 生效，替换代码需重启 | 给 agent 增加**新工具** |
| **MCP** | 独立进程，用 MCP 协议暴露工具 | bundle 里一段配置 | 连接后出现 `mcp__<server>__<tool>` | 已有 MCP server 想复用 |

本项目的推荐路线：**先做 Skill（5 分钟），需要“工具化”再做 Bundle（30 分钟）**。

---

## 路线 A：做成技能（已验证）

### 1. 装好 Python 包

```bash
pip install -e /path/to/healthkit-report
# 或者不安装，直接用源码：
export PYTHONPATH=/path/to/healthkit-report/src
python3 -m healthkit_report --version
```

### 2. 建目录与 SKILL.md

```
<项目根>/.dsh/skills/healthkit-report/SKILL.md
```

目录层级很关键：只识别 `<root>/<name>/SKILL.md` 或 `<root>/<name>.md`，
**嵌套的 `**/SKILL.md` 不会被发现**。

`SKILL.md` 开头必须是 YAML frontmatter，`name` 与 `description` 必填：

```markdown
---
name: healthkit-report
description: Apple 健康导出（export.xml）分析：多设备去重、指标统计、生成体检报告 DOCX/XLSX/HTML。
whenToUse: 用户提到 export.xml、Apple 健康数据、体检报告，或要分析步数/心率/睡眠/HRV 趋势时。
---

# healthkit-report

（正文：什么时候用、命令怎么跑、参数、注意事项、常见问题）
```

完整示例见 [`integrations/dsh/skill/SKILL.md`](../integrations/dsh/skill/SKILL.md)。

### 3. 放哪里

| 位置 | 作用范围 | 适用 |
|---|---|---|
| `<项目根>/.dsh/skills/` | 仅当前项目 | 随仓库分发、团队共享（推荐） |
| `<项目根>/.agents/skills/` | 仅当前项目 | 想兼容其它 agent 工具时 |
| `~/.dsh/skills/` | 该用户所有项目 | 个人全局工具 |
| `~/.agents/skills/` | 该用户所有项目 | 同上，跨工具 |

项目根的判定：最近一个包含 `.git` 的祖先目录；没有则用当前工作目录。

### 4. 验证

- 新开一个会话，问一句“用 healthkit-report 分析我的导出”，技能会出现在 agent 的工具目录里；
- 或者直接让 agent 调 `skill` 工具，名字填 `healthkit-report`；
- 也可以 `ls -R .dsh/skills` 确认文件层级。

> 实测：把 `SKILL.md` 写进 `.dsh/skills/healthkit-report/` 后，**当前会话下一轮**的技能目录就出现了它，无需重启 DSH。

### 5. 维护

- 改正文立即生效（技能正文按需重新读取），不用改版本号；
- 改 frontmatter 里的 `name` 等于换了个技能；
- 删除目录即下线；
- `disable-model-invocation: true` 可以只保留人工调用、不暴露给模型。

---

## 路线 B：做成 Bundle 插件（注册真正的工具）

Bundle 是一个 npm 包，声明 `dsh.bundle.patch` 指向自己的 patch 文件；patch 往运行中的
组合里插入一行插件。下面是本项目的最小实现。

```
healthkit-report-plugin/
├── package.json          # 声明 dsh.bundle.patch
├── cordis.patch.yml      # 插入 plugin 行
├── index.js              # 用 defineTool 注册 healthkit_report 工具
├── icon.svg              # Plugins 页面显示的图标
└── locale/{zh,en}.json   # 标题与描述
```

### 1. package.json

```json
{
  "name": "@local/healthkit-report",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "exports": {
    ".": "./index.js",
    "./locale/*.json": "./locale/*.json",
    "./icon": "./icon.svg"
  },
  "files": ["index.js", "cordis.patch.yml", "locale/*.json", "icon.svg"],
  "dsh": { "bundle": { "patch": "./cordis.patch.yml" } }
}
```

`@deepseek-ai/dsh-tools` 不用写进 `dependencies`：DSH 自带的包从安装目录解析。

### 2. cordis.patch.yml

```yaml
- insert:
    - id: healthkit-report
      name: '@local/healthkit-report'
```

### 3. index.js

```js
import { defineTool } from "@deepseek-ai/dsh-tools";
import { execFile } from "node:child_process";

const name = "tool-healthkit-report";
const inject = ["tools"];

function apply(ctx) {
  ctx.tools.register(defineTool({
    name: "healthkit_report",
    description: "解析 Apple 健康导出，去重后生成 DOCX/XLSX/HTML 报告。",
    parameters: {
      action: { type: "string", required: true, description: "parse|analyze|report|all" },
      export: { type: "string", description: "export.xml 或解压目录的绝对路径" },
      out: { type: "string", description: "输出路径" },
    },
    output: {
      schema: {
        type: "object", additionalProperties: false,
        properties: {
          ok: { type: "boolean", required: true },
          stdout: { type: "string", required: true },
          stderr: { type: "string", required: true },
        },
      },
      render: (_args, v) => [{ type: "text", text: v.stdout || v.stderr }],
    },
    async execute(args, exec) {
      const argv = ["-m", "healthkit_report", args.action, args.export, "-o", args.out || "out"];
      const { code, stdout, stderr } = await new Promise((resolve) => {
        execFile(process.env.HEALTHKIT_PYTHON || "python3", argv,
          { signal: exec?.signal, maxBuffer: 32 * 1024 * 1024 },
          (error, stdout, stderr) => resolve({ code: error ? 1 : 0, stdout, stderr }));
      });
      return { ok: code === 0, stdout, stderr };
    },
  }));
}

export { apply, inject, name };
```

完整实现（参数校验、超时、错误提示、异常动作）见
[`integrations/dsh/plugin/index.js`](../integrations/dsh/plugin/index.js)。

### 4. 安装

两种方式，任选其一：

**A. Web UI（推荐）**

1. 打开 DSH Web 的 **Plugins** 页面；
2. 选择安装本地 bundle，填该目录的**绝对路径**；
3. 安装完成后，插件列表里会出现「Apple 健康报告」，可随时启用/停用/卸载。

**B. 让 agent 调 `plugin_manager`**

需要当前 preset 是 Creator 模式（该工具默认只在 Creator 模式启用），且该调用需要
`danger-full-access` 或逐次审批：

```text
plugin_manager action=install_bundle target=/绝对路径/healthkit-report-plugin
```

### 5. 验证

1. 新会话里工具列表出现 `healthkit_report`；
2. 让它跑一次真实导出：

```text
healthkit_report action=all export=~/Downloads/apple_health_export/export.xml out=out
```

3. 检查 `out/health-report.docx` 是否生成；
4. 在 Plugins 页面确认标题、描述、图标都来自 `locale/*.json` 与 `icon.svg`。

### 6. 更新与卸载

- 改 `index.js` 后需要**重启 DSH**（替换已安装的包要重新加载 JS 模块）；
- 只改配置或 locale 时，重新安装即可；
- 卸载走 Plugins 页面的 Remove，或 `plugin_manager action=remove_bundle`。

---

## 路线 C：MCP（可选）

如果以后把 `healthkit-report` 做成一个 MCP server（stdio），bundle 可以只写配置、不含 JS：

```yaml
- insert:
    - id: healthkit-report-mcp
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: healthkit
        transport: stdio
        command: python3
        args: ["-m", "healthkit_report", "mcp"]
        failOnStartupError: true
```

安装后工具名是 `mcp__healthkit__<tool>`。本项目目前**没有**内置 MCP server，
这条路线留作扩展。

---

## 常见坑

| 现象 | 原因与处理 |
|---|---|
| 技能不出现 | 层级不对（必须是 `<root>/<name>/SKILL.md`）；frontmatter 缺 `name`/`description`；项目根判断错误 |
| 工具不出现 | patch 里 `name` 与 `package.json` 的 `name` 不一致；`dsh.bundle.patch` 路径写错；安装后没重新开会话 |
| `No module named 'healthkit_report'` | Python 解释器不对：设 `HEALTHKIT_PYTHON=/path/to/python3`，或先 `pip install -e` |
| `No module named 'docx'` | 缺依赖：`pip install python-docx XlsxWriter` |
| 改代码不生效 | Host 代码已加载进进程，需重启 DSH |
| 找不到 export.xml | iPhone：健康 App → 头像 → 导出所有健康数据，解压后取 `export.xml` |

## 检查清单

- [ ] `python3 -m healthkit_report --version` 能跑
- [ ] `.dsh/skills/healthkit-report/SKILL.md` 能被 `skill` 工具加载
- [ ] 用真实 `export.xml` 跑通 `all`，产出三份文件
- [ ] （可选）Plugins 页面能看到插件、标题/描述/图标正确
- [ ] （可选）新会话里 `healthkit_report` 工具可调用
