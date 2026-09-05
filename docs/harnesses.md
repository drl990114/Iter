# Harness 适配与排障

[English](harnesses.en.md) · [当前版本验证](validation-0.1.0.md)

首个版本为 `0.1.0`，发布状态见 [GitHub Releases](https://github.com/drl990114/Iter/releases)。远程命令需要仓库访问权限且不会安装本地未发布改动。试用候选版时以当前本地源码路径作为安装来源。首轮重点验证 Codex 与 Claude Code。

快速安装见 [中文 README](../README.zh-CN.md) 或 [English README](../README.md)。本页提供[手动安装](#手动安装)、[原生 Skill 安装](#原生-skill-安装)、[原生插件安装](#原生插件安装)、[Windows 安装](#windows-安装)及更新排障参考。Iter 按 [Agent Skills 标准](https://agentskills.io/specification) 分发完整的 `iterate-product/`，各平台共用同一份流程和 Python helper。

## 目录与调用依据

下表按 2026-09-04 访问的官方文档整理，列出推荐的手动安装位置及主要兼容目录；**每个根目录下面还需要 `iterate-product/`**。安装器实际选择的路径见下一节。

| Harness | 项目技能根目录 | 个人技能根目录 | 调用与官方依据 |
|---|---|---|---|
| Codex | `.agents/skills` | `~/.agents/skills` | `$iterate-product`；[官方技能文档](https://learn.chatgpt.com/docs/build-skills) |
| Claude Code | `.claude/skills` | `~/.claude/skills` | `/iterate-product`；插件为 `/iter:iterate-product`；[官方技能文档](https://code.claude.com/docs/en/skills) |
| Cursor | `.agents/skills` 或 `.cursor/skills` | `~/.agents/skills` 或 `~/.cursor/skills` | `/iterate-product`；[官方文档](https://prod.cursor.com/docs/skills) |
| GitHub Copilot | `.github/skills`、`.agents/skills` 或 `.claude/skills` | `~/.copilot/skills` 或 `~/.agents/skills` | 自然语言指定；[官方文档](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) |
| Gemini CLI | `.gemini/skills` 或 `.agents/skills` | `~/.gemini/skills` 或 `~/.agents/skills` | 自然语言指定；`/skills list`、`/skills reload`；[官方文档](https://geminicli.com/docs/cli/skills/) |
| OpenCode | `.opencode/skills`、`.agents/skills` 或 `.claude/skills` | `~/.config/opencode/skills`、`~/.agents/skills` 或 `~/.claude/skills` | 自然语言触发 skill 工具；[官方文档](https://opencode.ai/docs/skills/) |
| Windsurf / Cascade | `.windsurf/skills` | `~/.codeium/windsurf/skills` | `@iterate-product`；[官方文档](https://docs.devin.ai/desktop/cascade/skills) |
| Cline | `.cline/skills`；兼容 `.clinerules/skills`、`.claude/skills` | `~/.cline/skills` | `/iterate-product` 或自然语言指定；[官方文档](https://docs.cline.bot/customization/skills) |
| DeepSeek Harness | `.dsh/skills` 或 `.agents/skills` | `~/.dsh/skills` 或 `~/.agents/skills` | `/iterate-product`；[官方加载器](https://github.com/deepseek-ai/deepseek-harness/blob/76fda729799fe9b3848dbe2c211d4b231032b81e/packages/skill/skill-filesystem/README.md) |

Windsurf 的 Cascade 文档现位于 Devin Desktop 文档站；这里保留专属目录，避免将新版本的共享目录支持套用到旧版本。该表针对 Cascade，不代替 Devin Local Agent 的配置。

## Skills CLI 的实际目录

面向用户的命令采用不固定 CLI 版本的 `npx skills`；本仓库的安装回归测试固定 `skills@1.5.23`，便于复现结果。以下来自该测试版本的开源 agent 映射；个人目录列是默认值，环境变量可能改变它。

| `--agent` | 项目目录 | `--global` 的默认目录 |
|---|---|---|
| `codex` | `.agents/skills` | `~/.codex/skills` |
| `claude-code` | `.claude/skills` | `~/.claude/skills` |
| `cursor` | `.agents/skills` | `~/.cursor/skills` |
| `github-copilot` | `.agents/skills` | `~/.copilot/skills` |
| `gemini-cli` | `.agents/skills` | `~/.gemini/skills` |
| `opencode` | `.agents/skills` | `~/.config/opencode/skills` |
| `windsurf` | `.windsurf/skills` | `~/.codeium/windsurf/skills` |

安装器映射与宿主最新推荐目录并不总相同：Codex 的安装器个人目录默认是 `~/.codex/skills`，官方推荐个人目录为 `~/.agents/skills`。先看安装输出；宿主未发现时，可改用官方路径手动安装完整目录，处理好旧副本后再开新会话。`CODEX_HOME`、`CLAUDE_CONFIG_DIR` 等自定义配置也会影响部分安装位置。

Cline 的安装器映射使用 `.agents/skills`，当前 Cline 官方文档列出的技能目录没有它，所以本文采用 `.cline/skills` [手动安装](#手动安装)。不能只因安装器报告成功，就认定对应宿主已经发现 Skill。

查看安装器结果：

```sh
npx skills list --agent codex
npx skills list --global --agent codex
```

可用产品标识和安装选项见 [vercel-labs/skills](https://github.com/vercel-labs/skills)。本仓库只对表中的 7 个 agent 跑了项目目录安装测试；个人安装映射来自源码核对，不是逐个启动宿主后的验证结果。

## 手动安装

没有 Node，或希望自己管理 Skill 文件时，下载或克隆仓库，将**整个** `skills/iterate-product/` 目录复制到 harness 的技能目录。必须包含 `scripts/`、`references/`、`assets/`，只复制 `SKILL.md` 无法完整运行。

例如，在目标项目给 Cline 安装；先将源码路径换成你的实际路径：

```sh
mkdir -p .cline/skills
test ! -e .cline/skills/iterate-product && test ! -L .cline/skills/iterate-product && cp -R "/absolute/path/to/Iter/skills/iterate-product" .cline/skills/iterate-product
```

Cline 当前官方路径与 `skills --agent cline` 的目录映射不同，因此这里采用官方路径。[Cline 官方文档](https://docs.cline.bot/customization/skills)

其他工具常用的项目目标目录：

| Harness | 复制后的目录 |
|---|---|
| Codex / Cursor / Copilot / Gemini CLI / OpenCode | `.agents/skills/iterate-product/` |
| Claude Code | `.claude/skills/iterate-product/` |
| Windsurf / Cascade | `.windsurf/skills/iterate-product/` |
| Cline | `.cline/skills/iterate-product/` |
| DeepSeek Harness | `.dsh/skills/iterate-product/` |

个人目录与兼容路径见[完整目录表](#目录与调用依据)，PowerShell 命令见 [Windows 安装](#windows-安装)。复制前检查目标是否已存在；更新时保留本地改动，并替换完整目录。


## 原生 Skill 安装

### Gemini CLI 原生 Skill 安装

不使用 Skills CLI 时，可以直接在目标项目运行：

```sh
gemini skills install https://github.com/drl990114/Iter.git --path skills/iterate-product --scope workspace
gemini skills list
```

个人安装将 `--scope workspace` 换成 `--scope user`。已打开的会话可执行 `/skills reload`，再提出“使用 iterate-product …”。本地源码也可作为安装来源；选项见 [Gemini CLI 官方文档](https://geminicli.com/docs/cli/skills/)。

### GitHub Copilot 原生 Skill 安装

GitHub CLI 2.90.0+ 提供预览阶段的 `gh skill`，也可以直接安装：

```sh
gh skill preview drl990114/Iter iterate-product
gh skill install drl990114/Iter iterate-product
```

默认安装到当前项目的 Copilot 目录，个人安装增加 `--scope user`。通过此方式安装后，用 `gh skill update iterate-product` 更新。该入口按 [GitHub 官方文档](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills#managing-skills-with-github-cli)列出，本仓库的自动安装测试使用 Skills CLI。


## 原生插件安装

插件与目录版共用同一份 Skill。插件适合希望用 harness 自带管理器启用、更新和卸载的用户；单纯在项目里使用时，Skills CLI 步骤更少。

**目前仓库包含插件 manifest，但没有可直接通过仓库地址添加的 marketplace 清单。**因此下面使用独立的本地 marketplace；不能跳过配置，直接执行 `codex plugin marketplace add drl990114/Iter` 或 `claude plugin marketplace add drl990114/Iter`。

### 准备插件源码

以下 macOS / Linux 命令使用新的 `~/iter-plugins` 目录。Codex 和 Claude Code 可以共用这份源码；已有安装请直接看[更新与卸载](#插件更新与卸载)。

```sh
mkdir -p "$HOME/iter-plugins/plugins"
git clone https://github.com/drl990114/Iter.git "$HOME/iter-plugins/plugins/iter"
```

如果使用尚未推送的本地源码，把当前仓库复制到上述 `plugins/iter` 位置，保留隐藏的插件 manifest。Windows 的路径、复制和 marketplace 配置见 [Windows 安装](#windows-安装)。

### Codex 插件

在 `~/iter-plugins/.agents/plugins/marketplace.json` 新建以下文件。这里 `iter-local` 是 marketplace 名，`iter` 是插件名，`source.path` 相对 `~/iter-plugins`。

```sh
mkdir -p "$HOME/iter-plugins/.agents/plugins"
```

```json
{
  "name": "iter-local",
  "interface": { "displayName": "Iter Local" },
  "plugins": [
    {
      "name": "iter",
      "source": { "source": "local", "path": "./plugins/iter" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    }
  ]
}
```

然后在终端安装：

```sh
codex plugin marketplace add "$HOME/iter-plugins"
codex plugin list
codex plugin add iter@iter-local
```

在使用同一配置目录的 Codex CLI / 桌面端开启新任务，搜索 `iterate-product` 或输入 `$iterate-product`。不同版本的技能列表可能显示插件前缀，以实际选择器为准。IDE 扩展使用 Skill 目录安装，见[手动安装](#手动安装)。

已有 personal marketplace 的用户可沿用原注册来源，不必新建 `iter-local`；先执行 `codex plugin list` 确认实际标识，再安装或更新。默认 personal marketplace 不需要额外执行 `marketplace add`。配置规范见 [OpenAI 官方插件文档](https://developers.openai.com/plugins/build/plugins)。

### Claude Code 插件

**立即试用**：在目标项目目录启动 Claude Code，加载准备好的源码：

```sh
claude --plugin-dir "$HOME/iter-plugins/plugins/iter"
```

然后输入 `/iter:iterate-product`。`--plugin-dir` 只用于这次启动；后续启动需要继续传入该参数。[官方本地加载说明](https://code.claude.com/docs/en/plugins)

**持久安装**：新建 `~/iter-plugins/.claude-plugin/marketplace.json`：

```sh
mkdir -p "$HOME/iter-plugins/.claude-plugin"
```

```json
{
  "name": "iter-local",
  "owner": { "name": "dongruilin" },
  "plugins": [
    { "name": "iter", "source": "./plugins/iter" }
  ]
}
```

```sh
claude plugin marketplace add "$HOME/iter-plugins"
claude plugin install iter@iter-local --scope user
```

只供当前项目使用时，在目标项目执行最后一行并选择 `--scope project`（共享项目配置）或 `--scope local`（仅自己使用）。项目配置引用的本地 marketplace 路径需要每个成员各自准备；团队分发应另外维护可访问的 Git marketplace。会话内也可以通过 `/plugin` 管理。重启后调用 `/iter:iterate-product`。[官方 marketplace 与作用域说明](https://code.claude.com/docs/en/plugin-marketplaces)

### DeepSeek Harness 插件

准备好 DeepSeek Harness 及其要求的 Node.js / pnpm 后，添加到所用 profile：

```sh
dsh plugin --profile web add "file:$HOME/iter-plugins/plugins/iter"
```

把 `web` 换成你的 profile。也可以使用任意源码路径：

```sh
dsh plugin --profile web add "file:/absolute/path/to/Iter"
```

在该 profile 的新会话输入 `/iterate-product`。适配器复用官方 `@deepseek-ai/dsh-skill-filesystem@0.0.1-rc.3`，不需要 build。也可复制完整 Skill 到 `.dsh/skills/iterate-product`，详见 [Harness 适配](#deepseek-harness)。


## Windows 安装

### Skills CLI

安装 Node.js 22.20+、Git 和 Python 3.10+ 后，README 中的 `npx skills add drl990114/Iter --skill iterate-product --copy` 命令同样可以在 PowerShell 执行。在目标项目运行，例如：

```powershell
npx skills add drl990114/Iter --skill iterate-product --copy
```

helper 可用 `py -3`、`python` 或 `python3`，以实际安装的 Python 3.10+ 为准。

### 手动复制

把源码路径换成实际目录；以下在目标项目中给 Cline 安装，目标已有文件时停止，避免把新目录嵌套进旧目录：

```powershell
$iterSkillSource = 'C:\src\Iter\skills\iterate-product'
$iterSkillTarget = Join-Path (Get-Location) '.cline\skills\iterate-product'
if (Test-Path -LiteralPath $iterSkillTarget) { throw "目标已存在：$iterSkillTarget" }
New-Item -ItemType Directory -Force -Path (Split-Path $iterSkillTarget) | Out-Null
Copy-Item -LiteralPath $iterSkillSource -Destination $iterSkillTarget -Recurse
```

其他 harness 替换目标路径即可。个人安装把目标根目录设为上一节对应的用户路径，例如 `Join-Path $env:USERPROFILE '.claude\skills\iterate-product'`。复制整个目录后，重新打开会话检查发现结果。

### 原生插件

准备新的本地 marketplace 目录：

```powershell
$iterMarketRoot = Join-Path $env:USERPROFILE 'iter-plugins'
$iterPluginSource = Join-Path $iterMarketRoot 'plugins\iter'
New-Item -ItemType Directory -Force -Path (Split-Path $iterPluginSource) | Out-Null
git clone https://github.com/drl990114/Iter.git $iterPluginSource
```

Codex：在 `$iterMarketRoot\.agents\plugins\marketplace.json` 保存上文 [Codex 插件](#codex-插件)中的 JSON，再执行：

```powershell
codex plugin marketplace add $iterMarketRoot
codex plugin add iter@iter-local
```

Claude Code：可直接 `claude --plugin-dir $iterPluginSource`；持久安装则在 `$iterMarketRoot\.claude-plugin\marketplace.json` 保存上文 [Claude Code 插件](#claude-code-插件)中的 JSON，再执行：

```powershell
claude plugin marketplace add $iterMarketRoot
claude plugin install iter@iter-local --scope user
```

JSON 中的相对路径继续使用 `./plugins/iter`。使用 WSL 时，在 WSL 的 home 和工具环境中安装，不要假设 Windows 用户目录的安装自动生效。以上是命令适配说明，本轮未做 Windows 实机验证。

## DeepSeek Harness

原生插件通过 [`index.mjs`](../index.mjs) 和 [`cordis.patch.yml`](../cordis.patch.yml) 加载，使用官方 `@deepseek-ai/dsh-skill-filesystem@0.0.1-rc.3` 注册独立的 `iter` provider，与默认 provider 共存，不配置模型或 API key。

目录安装无需 npm 包适配器：复制整个 `skills/iterate-product` 到工作区 `.dsh/skills/iterate-product` 或 `.agents/skills/iterate-product`。个人安装默认使用 `~/.dsh/skills` 或 `~/.agents/skills`，自定义根目录分别由 `DSH_HOME` 和 `DSH_AGENTS_HOME` 控制。

默认 filesystem provider 只发现技能根目录的直接子目录。因此不要把整个 Iter 仓库放进 `.dsh/skills/Iter/`，让真正的 Skill 多嵌套两层。源码与配置以[官方实现](https://github.com/deepseek-ai/deepseek-harness/blob/76fda729799fe9b3848dbe2c211d4b231032b81e/packages/skill/skill-filesystem/README.md)为准。

## 旧名称迁移

保留目标项目的 `.product-loop/` 和证据文件。先安装 `iterate-product`，再按旧副本的原安装方式与作用域移除 `run-product-loop`。Skills CLI 项目安装的 Codex 示例：

```sh
npx skills add drl990114/Iter --skill iterate-product --agent codex --copy
npx skills remove run-product-loop
```

上述卸载仅移除当前项目所有工具中的旧名称，适用于一起迁移项目副本；共享 `.agents/skills` 时，只指定 Codex 可能因其他工具仍使用而保留旧副本。不要使用会选中其他技能的 `remove --all`。个人安装匹配 `--global`；插件安装用原插件管理器处理。替换前检查安装副本内的本地修改，不直接清理插件缓存。重新打开会话并运行实际加载 helper 的 `status`，核对旧周期与授权保留。缺少 `language` 的旧状态继续按中文解释，无需手动迁移。

## 插件更新与卸载

本文使用的 `iter-local` 是**本地路径 marketplace**，更新分两步：先更新 `plugins/iter` 源码，再让 harness 刷新安装副本。不要把 `git pull` 成功等同于插件缓存已更新。

### Codex

先运行 `codex plugin list` 确认来源，再执行 `codex plugin add iter@iter-local`。本机 CLI `0.144.5` 的命令名为 `add`，不是 `install`。

如果版本未变化，缓存可能仍复用旧内容。本地开发时可请 Codex 使用内置 `plugin-creator` 的更新流程，对**已登记的源码目录**刷新 cachebuster 并重新安装；正式分发应维护有区别的版本。不要只改展示名，也不要直接修改缓存目录。更新后开启新任务。

`codex plugin marketplace upgrade` 用于刷新 Git marketplace 快照。本文的本地市场应直接更新本地源码；若将来改用 Git marketplace，再升级对应的市场并重新添加插件。卸载使用 `codex plugin remove iter@iter-local`。命令与市场格式见 [OpenAI 官方文档](https://developers.openai.com/plugins/build/plugins)。

### Claude Code

更新源码后，执行 `claude plugin marketplace update iter-local`，再执行 `claude plugin update iter@iter-local --scope user`。项目或本地作用域应分别改为 `--scope project` 或 `--scope local`，重启后确认。开发中若要立即验证当前文件，可继续使用 `claude --plugin-dir /absolute/path/to/Iter`。

持久插件同样需要正确的版本管理。卸载为 `claude plugin uninstall iter@iter-local --scope user`；作用域要匹配安装记录。命令见 [Claude Code 插件参考](https://code.claude.com/docs/en/plugins-reference)。

### DeepSeek Harness

在同一 profile 中通过 `dsh plugin --profile web remove iter` 卸载，然后用原文件来源重新 `add`。有多个 profile 时，对使用该插件的 profile 分别处理。安装器/provider 的验证不代替完整 DSH CLI 会话验证。

## 安装后检查与排障

先确认 harness 能列出 `iterate-product`，再让 agent 从**实际加载目录**运行：

```sh
python3 "/actual/loaded/path/iterate-product/scripts/product_loop.py" --help
```

这可以检查 Python 和 helper 是否可用，但不会执行产品迭代。运行真实场景的方法见 [测试说明](testing.md)。

| 现象 | 排查与处理 |
|---|---|
| GitHub 安装找不到 `iterate-product` | 查看远端是否包含新名称；未推送的源码使用 `add /absolute/path/to/Iter ...` |
| 安装成功但宿主找不到 | 检查实际目录、agent 标识、当前工作区、作用域与宿主版本；再开新会话 |
| 仍然显示 `run-product-loop` | 检查旧目录版和旧插件缓存；按本页「旧名称迁移」说明移除旧安装副本 |
| 同一个 Skill 出现两次 | 检查插件版、项目目录和个人目录；保留一个预期来源 |
| Codex / Claude 提示找不到 marketplace | 仓库根目录没有 marketplace；按[原生插件安装](#原生插件安装)在独立目录创建对应清单，再添加该目录 |
| `iter@iter-local` 不存在 | 确认配置已添加、marketplace 名是 `iter-local`、`source` 指向包含插件 manifest 的 `plugins/iter` |
| 模板或脚本缺失 | 重新复制完整 Skill，保留相对目录结构 |
| Python 找不到或版本过低 | 安装 Python 3.10+；让 harness 的实际 shell 能找到它，Windows 可用 `py -3` |
| 远程环境不能发现本机安装 | 在远程执行环境安装，或将项目 Skill 随代码共享 |
| 插件更新后仍用旧流程 | 检查版本、市场来源、安装副本及是否已重开会话 |
| 找到 Skill 但无法执行 shell | 当前宿主必须提供命令执行能力，才能运行 Python 状态机 |

目录发现、安装副本、真实模型行为和产品结果是不同层次的验证。本机已有结果见 [审查记录](review-2026-09-04.md)，不能据此推断其他系统或新名称的模型会话也已通过。
