# 0.1.0 release preparation / 发布准备

This document contains preparation material for the initial version. Consult [GitHub Releases](https://github.com/drl990114/Iter/releases) for publication status. Repository visibility changes, tags, GitHub releases, and invitations are separate final publication steps.

以下是首个版本的可审阅发布材料，实际状态见 [GitHub Releases](https://github.com/drl990114/Iter/releases)；开放仓库、创建 tag / GitHub Release 和发送邀请属于后续发布步骤。

Version synchronization, changelog generation, candidate CI, tags, and GitHub Releases are handled by the manually triggered [Release workflow](releasing.md). The visibility and invitation checks below are first-trial preparation, outside release automation. The bilingual text below is editorial material; the first release notes are prepared under CHANGELOG's `0.1.0` heading. Add later changes under `Unreleased`; the workflow merges them into that first dated section.

版本同步、变更记录、候选 CI、tag 与 GitHub Release 由手动触发的 [Release workflow](releasing.md#中文) 完成。下方公开仓库和邀请相关检查属于首轮试用准备，独立于发布自动化；首版说明已整理到 CHANGELOG 的 `0.1.0` 下，后续补充写入 `Unreleased`，工作流会合并为一个带日期的首版条目。

## Release gates / 发布条件

- Review the complete candidate diff, license, package inventory, and bilingual walkthrough. Preserve `.product-loop/` compatibility and unrelated work.
- Run the documented local checks and review native host evidence. Record service failures as incomplete; do not advertise those cases as passing.
- Commit the reviewed candidate on a branch and run CI against that exact SHA on all configured platforms. A local pass is not a remote CI pass.
- Before making the repository public, review tracked files and Git history for material that was not intended for publication; do not publish raw host logs or private product data.
- With publication authorization, make the repository public, then verify anonymous GitHub access and install the same reviewed SHA without stored repository credentials.
- Trigger Release in `auto` mode after the reviewed source is on `main`. The first run preserves `0.1.0`, tests its generated version commit, then creates its tag and GitHub Release. Confirm the tag resolves to the tested candidate SHA in the workflow artifact.
- Test the tagged source with `skills@1.5.23 --copy` in fresh projects. Update the changelog, GitHub release, and validation matrix to the actual release status. Keep README version-neutral, with stable links to those records.
- Send only the approved invitations to the selected opt-in recipients. Track observations using the existing feedback form; this release does not publish to npm or a native marketplace.

按顺序检查完整变更与材料、本地检查和宿主证据、准确提交的三系统 CI、公开内容范围、匿名访问与安装，再创建首个 Release 和发送已批准邀请。版本与发布状态集中维护在 CHANGELOG、GitHub Release 和验证记录中；README 只保留稳定入口。

## GitHub Release draft

Title: **Iter 0.1.0 — a small bilingual product-iteration trial**

Iter helps you choose a useful next improvement, deliver the scope you approve, and review what the evidence actually establishes. This initial release includes a resumable workflow, scope-bound authorization, cancellation at any active phase, English and Chinese reports, multi-host installation, and Windows evidence-path handling.

The trial focuses on Codex and Claude Code. Please check the validation matrix for tested versions and incomplete cases. Local scenario success leaves real-user value unverified. Keep `.product-loop/` when upgrading from `run-product-loop`.

Install with `npx skills add` and `--copy`; use the tagged GitHub source for reproducibility. See the README, Note Counter walkthrough, and trial feedback form in this release. MIT licensed.

Iter 帮你选择下一步改进、交付已批准的范围，并复盘证据实际证明了什么。首个版本包含可恢复的完整流程、绑定范围的授权、任意活动阶段取消、中英文报告、多工具安装和 Windows 证据路径处理。

首轮聚焦 Codex 与 Claude Code。请先查看验证矩阵中的实际版本和未完成项目。本机场景成功仍不等于真实用户价值已验证。从旧名称升级时保留 `.product-loop/`。安装使用 `npx skills add` 和 `--copy`；完整案例和反馈入口见本次发布文档。采用 MIT 许可。

## Trial invitation drafts / 试用邀请草稿

**English**

I'm testing Iter, a small skill that helps a coding agent choose a product improvement and carry the approved scope through implementation and evidence review. Would you like to try one iteration in a disposable project using Codex or Claude Code? The Note Counter walkthrough takes you through the workflow. Feedback on installation, repeated permission questions, and where you got stuck would be especially useful. This is the first release; the validation matrix lists the current limits.

**中文**

我在小范围试用 Iter：让编程 Agent 帮你选下一步产品改进，并把已批准范围推进到实现和证据复盘。欢迎用 Codex 或 Claude Code，在一次性项目里跑一轮 Note Counter 案例。最想了解安装是否顺利、是否重复问授权，以及你在哪一步卡住。当前是首个版本，已验证范围和限制都写在验证矩阵中。

These are drafts, not sent messages. Add the actual public release and walkthrough links after publication.

以上为草稿，尚未发送；发布后补上实际可访问的版本和案例链接。

## Learn from the trial / 试用复盘

Use voluntary GitHub trial reports as the initial collection method. Do not add telemetry. Capture host/version/OS, installation outcome, first-cycle completion, repeated authorization count, time to first useful result, and willingness to try another iteration. Report denominators and missing responses explicitly. A cancelled cycle is distinct from a failed installation or a completed experiment.

Start with a small opt-in batch. Fix recurring installation, cancellation, or authorization failures before expanding. The initial trial has no fixed participant quota and no invented success target; use concrete observations and counterexamples to choose the next improvement.

先使用自愿提交的 GitHub 反馈表，不增加遥测。记录工具/版本/系统、安装结果、首轮完成、重复授权次数、首次有用结果耗时和再次使用意愿；明确分母与缺失反馈。主动取消、安装失败和实验完成分别记录。先解决反复出现的卡点，再扩大试用。

Later candidates: lighter report output for simple tasks, modularizing the helper where maintenance evidence justifies it, and additional host coverage. Public npm and marketplace distribution remain separate work.
