# 测试与本机试用

[English](testing.en.md) · [当前验证结果](validation-0.1.0.md)

## 自动验证

开发环境：Node.js 22.20+、Python 3.10+；无需 build。

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run check
npm test
npm run test:install
npm run test:python
uvx ruff@0.16.6 check skills/iterate-product/scripts scripts
uvx ruff@0.16.6 format --check skills/iterate-product/scripts scripts
```

| 层次 | 实际检查 | 不代表 |
|---|---|---|
| `check` | JavaScript 语法；仓库没有 TypeScript 源码 | 类型检查或模型行为 |
| `npm test` | 官方 Cordis/DSH 注册与卸载；实际 npm 打包/解包；两种插件元数据、完整资源、异地 cwd 运行 helper | 完整 DSH CLI profile 或 UI 会话 |
| `test:install` | 固定版本 skills CLI 在 7 个临时项目安装；保留其他 skill；文件逐一比对；运行已安装 helper 生成状态和模板 | 7 款产品的实际模型调用 |
| `test:python` | 外置路径发现与隔离、迁移与重关联、阶段转换、取消/重复取消、双语完成、授权/撤销、方案修订、旧状态兼容、证据路径与失败/完成 gate | 真实用户需求或产品收益 |
| Ruff | Python lint | 功能正确性 |

安装测试明确选择产品、项目作用域及 `--copy`，不触碰个人安装。Python launcher 在 JS 集成测试中自动检测；Windows 下独立单测可将 `python3` 换为 `py -3`。平台兼容代码不等于 Windows 实机验证。

CI 配置涵盖 Linux、macOS、Windows，以及 Node 22.20.0 / Python 3.10 最低版本。安装测试额外覆盖同时安装 Codex 与 Windsurf、旧名称卸载迁移及状态保留。CI 不调用模型，也不发布。真实运行状态见当前验证记录。

手动触发的 [Release workflow](releasing.md#中文) 会在发布前复用这套矩阵检查准确的候选提交。`npm test` 还覆盖真实版本工具、Git bundle 恢复、分支/tag 冲突和失败重试；使用临时本地 Git remote 与模拟 GitHub API，不创建真实发布。远端集成可通过 Release 的 `dry_run` 演练。

## 可复现的真实 skill 试用

仓库保留了一个未实现递归功能的 [Note Counter 样例](../examples/note-counter)。复制到临时目录，再安装当前本地源码。macOS/Linux 示例：

```sh
iter_source="$(pwd)"
iter_trial="$(mktemp -d "${TMPDIR:-/tmp}/iter-trial.XXXXXX")" || exit 1
iter_data="$(mktemp -d "${TMPDIR:-/tmp}/iter-data.XXXXXX")" || exit 1
export ITER_HOME="$iter_data"
cp -R "$iter_source/examples/note-counter/." "$iter_trial/" || exit 1
cd "$iter_trial" || exit 1
npx skills@1.5.23 add "$iter_source" --skill iterate-product --agent claude-code --copy
claude
```

也可以选择 `--agent codex` 后启动 `codex`，或选矩阵中的其他产品。Windows 分别创建临时项目目录与外置数据目录，在宿主环境中设置绝对路径 `ITER_HOME` 后复制样例。这个变量让试用记录与个人 Iter 数据分开；恢复会话时保持相同值。不要在真实产品目录中运行这个试用。

首次写入前，从已安装 helper 运行 `paths --workspace "<试用工作区>"`。查询不创建目录，并返回初始化前准备方案用的 `inputs_dir`。按需为宿主授予准确 `storage_root` 的写权限；初始化后再次查询，将生成日志写到 `evidence_dir`。产品样例中不应出现 `.product-loop/`、方案 JSON 或流程报告，详见[存储说明](storage.md)。

开放式请求：

```text
使用 iterate-product，为这个 Note Counter 提出下一轮迭代建议。仅使用当前临时项目作为来源证据，流程记录写入已配置 ITER_HOME 下当前工作区的外置 storage_root；尚未选定实现，不访问网络、不安装依赖、不改全局配置。
```

检查是否先给具体选择，是否正确说明没有真实用户反馈，是否保留选择权。未选定时不应冒充已授权开发。

选定范围的独立试用（可新建另一份临时样例）：

```text
使用 iterate-product，为 Note Counter 添加可选 --recursive 参数，统计嵌套目录里的 .md 文件；默认保持只统计第一层。
验收：默认结果不变、递归包含嵌套 Markdown、不包含 .txt、空目录输出 0。指标为本机场景通过率 100%。
允许修改这份样例代码，并授权在当前临时项目内创建隔离测试文件和删除测试生成的样例，以及在已配置 ITER_HOME 下当前工作区的外置 storage_root 保存流程输入、日志与迭代报告；保留证据供检查。
只能使用当前临时项目作为证据，不访问真实用户数据或网络、不安装依赖、不改全局配置、不发布、不 build。完成这一轮。
```

检查实际结果：

- 程序确实实现所选功能，执行日志来自真实 CLI，而非预写的期望结果。
- 四个场景都有观察、证据和验收结果；隔离样例按约定清理。
- 通过 helper 生成和推进 `paths.state_path` 指向的外置状态，最终与评估 verdict 一致；没有手改状态绕过 gate，项目中没有流程文件。
- 授权复用，无重复许可请求；完成报告明确“本机场景验证通过；真实用户价值待验证”。

从终态再次要求“继续”，应报告已完成；只有明确要求新一轮才创建新 cycle。主动改变范围的试用应提出具体修订；执行阻塞则记录真实 blocker，不能宣称成功。

补充行为场景：在研究、审批、开发阶段说「取消这一轮」，检查 `stop` 直接结束且历史保留；说「暂停」则应保留活动状态。分别用中英文完成一轮，检查报告语言、真实证据和局限说明。英文请求样例与有界宿主试用脚本见 [English testing guide](testing.en.md#native-host-sessions)。

存储验收应检查：新工作区只读查询不创建目录；两个工作区互不串状态；外置写入被拒绝时不回退项目。用一次性旧样例迁移，检查授权和报告正文保留、旧证据引用仍可读、外置备份存在且旧 `.product-loop/` 已移除。移动一份样例后显式 `relocate` 并检查恢复；另一个仍存在的 clone 不应被合并。新会话恢复时沿用相同 `ITER_HOME`。

保留临时项目与外置数据目录到报告检查结束，再仅清理本次创建的试用目录。模型会话使用本机既有账户，可能受服务可用性、登录或额度限制；不要把这类失败写成 skill 通过。
