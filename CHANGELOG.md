# Changelog

## Unreleased

## 0.1.0

Initial release, prepared for publication through the manual [Release workflow](docs/releasing.md). The tag and GitHub Release record the actual publication date.

### Features

- One portable `iterate-product` Skill takes a chosen improvement through research, scope approval, implementation, and evidence review. Saved cycles support interruption and resumption.
- Separate implementation and local-testing grants remain bound to the approved scope and are reused until that scope changes.
- Cancel from any active phase with `stop`, including a rejected proposal. Preserve artifacts, authorization, and audit history; start another cycle after cancellation.
- Generate English or Simplified Chinese reports with `init --language en|zh-CN`. Validate evidence limitations, current authorization, and actual execution evidence before completing a local scenario.
- Accept Windows drive and UNC evidence paths, spaces, and line references. Preserve Chinese JSON output through non-UTF-8 pipes.
- Install complete resources across supported hosts with `npx skills add` and `--copy`. Include Codex and Claude plugin manifests, a DeepSeek Harness adapter, and MIT licensing for both the repository and standalone Skill.
- Provide cross-platform CI, bilingual installation and testing guides, the Note Counter walkthrough and demo, and trial feedback forms.
- Trigger Release manually to synchronize package and plugin versions, generate notes, test the exact release candidate, and publish its tag and GitHub Release. README installation instructions remain independent of product and installer versions.

### Compatibility and limits

Development snapshots used the name `run-product-loop`. Keep `.product-loop/` and evidence when installing `iterate-product`; old states without a language remain Chinese. Follow the [English migration guide](docs/harnesses.en.md#migration) or [中文迁移指南](docs/harnesses.md#旧名称迁移).

Installation, host discovery, model-session behavior, and real-user value are separate evidence levels. See the [validation record](docs/validation-0.1.0.md), including the incomplete Claude service checks. One active cycle per workspace; concurrent writers are unsupported. Cancellation preserves changes and does not undo implementation. npm and public marketplace distribution are outside this release.

### 中文

首个版本提供单一 `iterate-product` 入口，覆盖方案选择、研究、范围授权、实现与证据复盘。支持授权复用、中断恢复、任意活动阶段取消、中英文报告、Windows 证据路径、多工具安装和独立 Skill 的 MIT 许可；附带跨平台 CI、双语 Note Counter 案例、演示与反馈入口。

后续只需手动触发 Release，工作流会同步版本、生成发布说明、验证准确候选提交并创建 tag 与 GitHub Release。README 的安装命令不绑定产品或安装器版本。

从内部旧名称迁移时保留 `.product-loop/` 与证据。安装通过不代表完整宿主会话通过，本地验证不代表真实用户价值；Claude 服务错误导致的未完成项目、单活动周期和取消不回滚等限制见验证记录。
