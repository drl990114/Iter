# Releasing Iter / 发布 Iter

## 中文

把改动合入并推送到 `main` 后，在 GitHub 的 **Actions → Release → Run workflow** 保留 `mode: auto` 并运行即可。也可以在与远端一致的干净 `main` 本地目录中运行：

```sh
npm run release
```

本地命令需要已登录的 GitHub CLI，只负责触发同一个 GitHub workflow。它不上传未提交的文件；工作目录未清理、分支不是 `main` 或本地与远端不一致时会停止。

一次触发会依次完成：

1. 用 [release-it](https://github.com/release-it/release-it)、[bumper](https://github.com/release-it/bumper) 和 [Conventional Changelog](https://github.com/release-it/conventional-changelog) 确定版本、同步包/锁文件/两份插件 manifest，并生成 CHANGELOG 和发布说明。
2. 在 runner 中创建候选提交，通过 Git bundle 把同一份提交交给 Linux、macOS、Windows 的现有 CI 检查。最低 Node/Python 版本也在矩阵内，无需 build。
3. 全部检查通过后，原子推送版本提交与 `v<version>` tag，把本次矩阵结果记录到候选 SHA 的 `Release / candidate CI` 状态，再创建 GitHub Release。该状态链接回完整检查记录；含预发布后缀的版本自动标记为 Pre-release。

只有第 3 步会写入远端。普通 push/PR 只运行 CI；README 不加入版本更新范围。包和插件共用产品版本，`.product-loop` 状态结构版本独立维护。此流程不发布 npm、不改变仓库可见性，也不向其他人发送消息。

### 版本选择

| `mode` | 行为 |
|---|---|
| `auto`（默认） | 第一次发布使用已准备的 `0.1.0`；预发布版本自动递增末位。正式版本根据 Conventional Commits 推断：`fix:` 修复、`feat:` 功能、`feat!:` / `BREAKING CHANGE:` 不兼容变更 |
| `stable` | 把当前 beta/rc 提升为同一版本的正式版，不自动进入此模式 |
| `patch` / `minor` / `major` | 明确指定升级幅度；可覆盖自动判断 |

没有新提交时停止，避免重复发版；`stable` 可以直接提升已经通过验证的预发布。预先准备了更高包版本时，`auto` 沿用该版本。已经发布的 tag 不覆盖。

Conventional Commits 决定自动判断是否准确；建议 squash 合并时规范 PR 标题。发布前可在 `CHANGELOG.md` 的 `Unreleased` 下写人工说明，特别是迁移和限制；自动生成的提交记录会一并收录，历史条目保留。首次 `0.1.0` 已整理在同名段落下，发布时会合并该段落并填入日期，避免重复条目。具体版本、变更和迁移说明集中放在 CHANGELOG / GitHub Releases / 验证文档。

```sh
npm run release -- --mode stable
npm run release -- --dry-run
```

`dry_run` 也可在 GitHub 表单中勾选：完成候选生成与全套 CI，但不推送、不创建 Release。候选提交和说明保存在 workflow artifact 中，保留 7 天。

### 首次启用与失败恢复

先把 workflow 和代码合入 `main`，GitHub 才会显示手动运行入口。发布使用 GitHub 内置 token，仅发布 job 需要 `contents: write` 和 `statuses: write`，无需 npm token 或额外 PAT。仓库规则必须允许发布身份推送 `main` 与 tag；如果要求所有变更通过 PR，需先为发布身份配置符合项目政策的权限。脚本不会关闭分支保护或强推。

- **CI 失败：**没有远端版本变更，修复并推送后重新触发。
- **检查期间 `main` 前进：**停止发布旧候选，对新的 `main` 重新触发。
- **tag 推送成功、GitHub API 随后失败：**在同一次 workflow 中选择 **Re-run failed jobs**，使用保留的候选继续发布。已成功创建的同版本 Release 会直接复用，不重复升级或覆盖。
- **同名 tag 指向其他提交，或已有同名草稿/渠道冲突：**停止并报告冲突，先核对仓库状态。

跨平台单测与安装检查不代表宿主模型会话通过。首次公开试用仍需单独完成公开内容审查、仓库公开后的匿名安装验证，以及验证文档中未完成的宿主试用；参见[试用发布材料](release-0.1.0.md)。

## English

Merge and push your changes to `main`, then select **Actions → Release → Run workflow** with the default `mode: auto`. From a clean local `main` matching the remote, `npm run release` triggers the same workflow through the authenticated GitHub CLI.

Release preparation uses release-it, its bumper plugin, and Conventional Changelog. It synchronizes the package, lockfile, and both plugin manifests, combines the curated `Unreleased` notes with generated commit notes, and creates a local candidate commit. A Git bundle carries that exact commit through the existing Linux, macOS, Windows, and minimum-runtime CI matrix. No build is required.

Only after every check succeeds does the workflow atomically push the version commit and its `v<version>` tag, attach a `Release / candidate CI` status to that exact SHA linking to the completed matrix run, then create a GitHub Release. SemVer prereleases are marked as GitHub pre-releases. Ordinary pushes and PRs only run CI. README stays independent of product versions, and workflow state schema versions remain separate. npm publishing, repository visibility, and external messages are outside this workflow.

| Mode | Behavior |
|---|---|
| `auto` | First release uses the prepared `0.1.0` version. Subsequent prereleases advance their counter. Stable versions follow Conventional Commits (`fix:`, `feat:`, `feat!:` / `BREAKING CHANGE:`). A package version already ahead of the latest release is preserved. |
| `stable` | Explicitly promote the current prerelease to its stable version. |
| `patch`, `minor`, `major` | Override the automatically recommended increment. |

With no new commits, release preparation stops; stable promotion is an exception. Use Conventional Commit titles when squash-merging PRs so automatic recommendations reflect the changes. Put human-written migration notes and limitations under `Unreleased` in `CHANGELOG.md`; they will be included alongside generated notes without rewriting historical entries. The initial `0.1.0` section is already prepared; its notes are merged into one dated section on the first release.

Select `dry_run` or run `npm run release -- --dry-run` to prepare and test without publishing. Candidate artifacts are retained for seven days. `npm run release -- --mode stable` explicitly graduates a prerelease.

The workflow must first be merged into `main`. The built-in GitHub token needs `contents: write` and `statuses: write` only in the publish job; no npm token or additional PAT is required. Repository rules must allow this publishing identity to update `main` and tags. If your policy requires PRs, configure an appropriate release identity before enabling publication; the workflow does not bypass protections or force-push.

If CI fails or `main` advances, fix/update the source and trigger Release again. If the tag was pushed but the GitHub API failed, use **Re-run failed jobs** on the same workflow to publish the retained candidate without another version bump. An existing matching release is reused; conflicting tags, drafts, or release channels stop publication.

CI success does not prove native model-session behavior. The first public trial still needs the publication review, anonymous installation after making the repository public, and any outstanding host-session validation described in the [trial release packet](release-0.1.0.md).
