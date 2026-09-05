# 0.1.0 validation and limits / 验证与限制

Recorded September 5, 2026 for the initial `0.1.0` version. These observations record the tested scope; the GitHub Release and its exact candidate CI run establish publication status. Native session snapshots below have their own recorded source hashes.

记录日期：2026-09-05，面向首个 `0.1.0` 版本。本文保留各项实际验证的范围；发布状态以 GitHub Release 及准确候选提交的 CI 为准。宿主会话使用的源码快照另有哈希记录。

## Evidence levels / 证据层级

“Installed” means complete resources were placed in the expected directory and the helper ran. “Discovered” means the actual host listed or read this installed Skill. “Session completed” requires inspecting the model's behavior, product changes, saved state, and evidence. None proves real-user value.

安装通过、宿主发现通过、完整会话通过分别记录。安装目录正确与 helper 可运行不能替代模型行为验证，模型行为验证也不能替代真实用户价值。

| Host | Installation | Discovery | Native session | Version / date |
|---|---|---|---|---|
| Codex | Passed | Passed | English/Chinese completed cycles, suggestions, resume, and cancellation passed; revision behavior observed with a process timeout | 0.153.1, macOS, 2026-09-05 |
| Claude Code | Passed | Passed in both language attempts | Incomplete: repeated API HTTP 500 errors, bounded timeouts; no product changes | 2.1.92, macOS, 2026-09-05 |
| Cursor, GitHub Copilot, Gemini CLI, OpenCode, Windsurf | Passed with Skills CLI copy mode | Not run | Not run | skills 1.5.23, macOS, 2026-09-05 |
| DeepSeek Harness | Adapter lifecycle and packaged resources passed | Adapter-level only | Not run | Packages pinned in package-lock.json, 2026-09-05 |
| Cline | Manual instructions only | Not run | Not run | No native claim |

## Automated local checks / 本地自动检查

Node 24.14.1 and the minimum supported Node 22.20.0, Python 3.10.10, Ruff 0.16.6, macOS. Both Node versions passed the JS syntax, package, install, and Python test commands. No build.

- 47 Python tests: cancellation at research/approval/development, terminal idempotence, archive preservation, new-cycle creation, English and Chinese completion, missing/hidden evidence limits, stale grants, missing execution evidence, revisions, evidence references, and Chinese JSON round trips through ASCII-only pipes.
- Seven individual install targets plus simultaneous Codex/Windsurf installation in a fresh directory and old-name migration. Includes paths with spaces, executing the installed helper, and preserving other Skills and `.product-loop/`.
- Twelve package/DSH, distribution, and release tests, including preparing the initial `0.1.0` from a single root commit, retaining one changelog section, restoring the exact candidate, and retrying publication failures. JS syntax, Python lint, and formatting also passed.
- Standalone Skill and both native plugin manifests validate. Root and standalone MIT license copies match.
- The CI workflow passes actionlint 1.7.12. This validates workflow syntax and references, not remote job execution.
- Independent Note Counter CLI replay: starter 1/4 scenario groups, completed implementation 4/4; six calls per revision. See the [exact observations](demo/evidence/evidence.json).

Windows drive, UNC, spaces, fragments, and line-suffix parsing are covered by branch-level unit tests. Native filesystem assertions execute on the OS running the suite. macOS success does not establish Windows filesystem or host behavior.

Windows 盘符、UNC、空格、片段及行号解析已有分支测试；本次本地运行仍是 macOS，不能作为 Windows 实机证明。

## CI evidence / CI 证据

The [CI run before the initial-history rewrite](https://github.com/drl990114/Iter/actions/runs/33950924407) passed all four jobs on September 5, 2026: Linux with Node 22.20.0 / Python 3.10 and Node 24 / Python 3.13, plus macOS and Windows with Node 24 / Python 3.10. This includes real Windows-runner filesystem assertions. Packaged YAML is parsed structurally and checked with both LF and CRLF line endings.

Check [CI on main](https://github.com/drl990114/Iter/actions/workflows/ci.yml) for the exact current commit. Release separately tests its generated candidate on the same matrix before publishing. An earlier green run does not certify a later commit or native model sessions.

历史整理前的 CI 已在四组环境通过，包含 Windows runner 上的文件系统检查。当前提交结果见 CI 列表；实际发布候选仍需在相同矩阵全绿后才会发布。宿主模型会话证据独立记录。

## Native sessions / 真实宿主会话

These are developer-authored isolated scenarios using installed project Skills and the user's configured providers, not recruited-user feedback. Raw logs stay outside the repository; the [redacted record](demo/native-sessions.json) retains prompts, versions, outcomes, source hashes, and relevant state observations.

| Codex case | Observed result | Process timing |
|---|---|---|
| English open request | Three concrete options; waited for selection; no product changes | Completed in 91.97 s |
| English selection and pause | Both grants saved; stage `research`; product code unchanged | Completed in 182.29 s |
| Fresh-session English resume | Reused the exact original grants, no repeated authorization question; reached `complete`, five scenarios passed, English evidence-limit sentence retained | First attempt interrupted at 420 s in development; next invocation completed in 530.38 s |
| Chinese selected scope | Reached `complete`; four scenario groups and seven CLI calls; retained evidence and Chinese evidence-limit sentence; fixtures cleaned | Completed in 368.73 s |
| Unapproved scope revision | Old grants cleared, earlier files preserved, concrete revised scope and separate approval question presented; no implementation | Earlier attempts timed out at 180/300 s. Final model turn completed, but process hit its 240 s deadline; qualified behavior evidence, not an unqualified process pass |
| Cancellation after revision | Reached `stopped` directly from research without approval or phase completion; 30 retained file hashes unchanged | Completed in 156.18 s |

These timings are individual observations under the configured provider, not performance percentiles. Native Skill snapshots and final candidate hashes are recorded separately. After the snapshots, the final helper added malformed-language guards and ASCII-safe JSON output; optional frontmatter metadata was removed for validator compatibility. The final helper also revalidated both native evaluation reports against their actual execution evidence without mutating the completed cycles.

以上耗时是单次观察，不是性能分位数。英文周期通过新会话恢复完成，原始两类授权未变、重复授权询问为 0。修订的授权失效与具体审批说明已观察到，但进程超时仍需复测；不能统一计作完整进程通过。最终 helper 已再次检查两份真实评估报告及其执行证据。

The existing global Codex 0.144.5 could not use the configured `gpt-6-astra` model (HTTP 400 requesting a newer CLI). The compatible app-bundled 0.153.1 binary was used without changing global settings. This is a version/model compatibility limit, not an installation pass failure.

Claude Code 2.1.92 discovered `iterate-product`, but English and Chinese calls repeatedly returned HTTP 500. They were stopped at 180 and 75 seconds respectively. All five Claude behavior cases remain unverified; retry them when the configured service is available. Do not advertise Claude full-session support based on discovery alone.

真实会话仅使用隔离样例，不等于外部用户反馈。Claude 两种语言均因服务错误未完成；恢复服务后仍需重跑开放式建议、指定功能、中断恢复、范围修订与取消。

## Pending publication gates / 后续发布条件

- CI against the exact release SHA: Linux/macOS/Windows, Node 22.20/24 and Python 3.10/3.13. The Release workflow enforces this for every generated candidate; use its run as the publication evidence.
- Native Windows and Linux sessions; more host/model combinations; Claude behavior cases after service recovery.
- A clean process exit for the native revision case; retain its current timeout and completed-turn evidence when comparing the retry.
- Public repository access and anonymous installation from the README command after visibility changes.
- Authorized tag and GitHub Release creation, followed by tagged-source installation verification and opt-in invitations.

See the [reviewable release packet](release-0.1.0.md). A local candidate must not be presented as passing these gates.

## Known limits / 已知限制

One active cycle per workspace; simultaneous writers are unsupported. Cancellation preserves changes and evidence; it does not revert implementation. `language` is fixed per cycle; old states without it use Chinese. Evidence file existence and report structure are validated, not the truth of claims inside them. Agents must inspect actual results. Whole-cycle reports can take several minutes even for this tiny example; the one-minute video is a presentation replay. No npm or public marketplace distribution is included.

每个工作区只有一个活动周期，不支持同时写入。取消保留代码与记录，不自动回滚。旧状态继续使用中文。文件存在和报告格式不能证明内容真实；必须检查实际结果。小案例的完整流程也可能耗时数分钟，演示时长不代表实际完成耗时。npm 和公开 marketplace 分发不在本次范围内。
