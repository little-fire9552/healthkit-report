# 让别人也能用你的插件（小白版）

## 先搞清楚一件事

你的东西分两半，**两个都要给到别人**，少一个就用不了：

| 部分 | 是什么 | 别人怎么装 |
|---|---|---|
| **插件**（5 个小文件） | 遥控器：在 DSH 里加一个 `healthkit_report` 工具 | DSH 左侧「插件」→「添加插件」 |
| **Python 程序** | 发动机：真正读数据、算指标、写报告的代码 | 一条 `pip install` 命令 |

另外提醒：**不要把任何人的健康数据打进包里**。插件目录里只有代码，没有 `export.xml`、没有报告。

---

## 方式一：用 GitHub（不用注册新账号，推荐）

### 第 1 步：把 Python 程序推上去

如果还没推过，在 `healthkit-report` 目录里：

```bash
git remote add origin https://github.com/<你的用户名>/healthkit-report.git
git push -u origin main
```

别人安装：

```bash
pip install git+https://github.com/<你的用户名>/healthkit-report
```

### 第 2 步：给插件单独建一个仓库

插件必须是一个**独立仓库**（仓库根目录就是 `package.json`），因为 DSH 安装时会按仓库根目录的包来装。

1. 在 GitHub 上新建仓库 `dsh-healthkit-report`（空仓库，不要勾选 README）；
2. 在插件目录里执行：

```bash
cd healthkit-report-plugin
git init -b main
git add -A
git commit -m "feat: DSH plugin for healthkit-report"
git remote add origin https://github.com/<你的用户名>/dsh-healthkit-report.git
git push -u origin main
```

别人安装：

> 打开 DSH 左侧 **插件** → 右上角 **添加插件** → 粘贴
> `https://github.com/<你的用户名>/dsh-healthkit-report` → 安装

---

## 方式二：发到 npm（别人只要输入一个名字）

好处：别人在「添加插件」里输入 `dsh-healthkit-report` 就行，不用贴链接。
代价：需要装 Node.js（自带 npm），并注册一个 npm 账号。

`dsh-healthkit-report` 这个名字我查过，npm 上还没人用。

```bash
# 只需要第一次
npm login

cd healthkit-report-plugin
npm publish
```

以后更新版本：

```bash
# 先把 package.json 里的 version 改大一点，比如 0.1.1
npm publish
```

> 注意：你截图里「安装源」选的是中国大陆镜像。npm 官方源发布后，镜像通常几分钟到几小时同步；
> 刚发完就搜不到属于正常现象。

---

## 别人装完之后怎么确认

1. 插件列表里出现「Apple 健康报告」（图标是蓝色心跳）；
2. 新开一个会话，工具列表里有 `healthkit_report`；
3. 让它跑一次：

```text
healthkit_report action=all export=/路径/export.xml out=out
```

看到 `out/health-report.docx` 生成就成功了。

---

## 发布前检查清单

- [ ] `package.json` 里的 `name` 是 `dsh-healthkit-report`
- [ ] `cordis.patch.yml` 里的 `name` 和它**一模一样**（差一个字母就装不上）
- [ ] `version` 每次发布都要变大
- [ ] `repository.url` 改成你自己的 GitHub 地址
- [ ] 目录里没有 `export.xml`、`dataset.json`、任何人的报告
- [ ] `LICENSE` 存在（MIT）

---

## 常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| 别人装完工具不出现 | 两个 `name` 不一致，或 patch 路径写错 | 对照检查清单 |
| 报 `No module named 'healthkit_report'` | 对方没装 Python 程序 | `pip install git+https://...` |
| 报 `No module named 'docx'` | Python 缺依赖 | `python3 -m pip install python-docx XlsxWriter` |
| GitHub 安装失败 | 仓库没公开，或网络问题 | 确认仓库是 Public |
| npm 提示名字被占用 | 名字冲突 | 换一个名字，**两处一起改** |

---

## 更省事的做法

如果你不想维护两个仓库，也可以只发 npm，让 Python 程序从 GitHub 装；
或者只发 GitHub，把插件放进 Python 仓库的 `integrations/dsh/plugin/`，
然后用带子目录的地址安装（需要 pnpm 支持 `#path:`，不保证所有版本都可以）。

对小白来说，**两个独立仓库 + 两条安装命令**是最不容易出错的组合。
