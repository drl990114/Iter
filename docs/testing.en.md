# Development and testing

[简体中文](testing.md) · [Current validation](validation-0.1.0.md)

Use Node.js 22.20+ and Python 3.10+. No build step is required.

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run check
npm test
npm run test:install
npm run test:python
uvx ruff@0.16.6 check skills/iterate-product/scripts scripts
uvx ruff@0.16.6 format --check skills/iterate-product/scripts scripts
```

`uvx` is optional developer tooling. Alternatively install the pinned Ruff in an isolated Python environment and run `python -m ruff`. The distributed Skill needs no Python packages. The JS test launcher detects `python3`, `python`, or Windows `py -3`.

| Check | What it establishes |
|---|---|
| `check` | JS syntax; this repository has no TypeScript sources |
| `npm test` | DSH provider lifecycle, actual npm pack/extraction, licensed resources, metadata/docs, and isolated release preparation, version selection, Git bundle restoration, conflicting refs, and failure recovery |
| `test:install` | Pinned Skills CLI installation for seven targets, simultaneous installation, old-name migration, state preservation, and executing the installed helper |
| `test:python` | External storage discovery/isolation, migration and relocation, cancellation, language and legacy compatibility, authorization/revision gates, evidence references, and state transitions |
| Ruff | Python lint and formatting |

CI covers Linux, macOS, Windows, Node 22.20.0/24, and Python 3.10/3.13 using an explicit matrix. It runs offline behavior checks after fetching development dependencies; it does not call model services, publish, or change GitHub visibility. Platform coverage is only established after the corresponding CI job succeeds.

The manually triggered [Release workflow](releasing.md#english) reuses this matrix against its exact candidate commit before publication. Release tests use temporary local Git remotes and a simulated GitHub API; they never publish a real release. A workflow `dry_run` is the remote integration rehearsal.

## Native host sessions

Copy the original [Note Counter fixture](../examples/note-counter) into a new temporary project and install the candidate there. Keep the source fixture unmodified.

```sh
iter_source="$(pwd)"
iter_trial="$(mktemp -d "${TMPDIR:-/tmp}/iter-trial.XXXXXX")" || exit 1
iter_data="$(mktemp -d "${TMPDIR:-/tmp}/iter-data.XXXXXX")" || exit 1
export ITER_HOME="$iter_data"
cp -R "$iter_source/examples/note-counter/." "$iter_trial/" || exit 1
cd "$iter_trial" || exit 1
npx skills@1.5.23 add "$iter_source" --skill iterate-product --agent codex --copy
codex
```

Choose `claude-code` and start `claude` for the other primary host. Windows can use separate temporary project and data directories, setting an absolute external `ITER_HOME` in the host environment. This override isolates trial records from personal Iter data; preserve the same value when resuming.

Before the first write, run the installed helper's `paths --workspace "<trial-workspace>"`. It creates nothing and supplies an `inputs_dir` for the proposal before initialization. Grant the host write access to that exact `storage_root` if needed. After initialization, query paths again and write generated logs to `evidence_dir`. No `.product-loop/`, proposal JSON, or workflow reports should appear in the product fixture. See [storage](storage.en.md).

Start with an open request:

```text
Use iterate-product to suggest 2–3 improvements for this Note Counter. Use only this isolated project as source evidence, and keep workflow records in its external storage_root under the configured ITER_HOME. I have not selected or authorized implementation. Do not access the network, install dependencies, change global configuration, or build. Present concrete choices and pause for selection.
```

In a separate fixture, use a selected scope:

```text
Use iterate-product to add optional --recursive support for nested .md files. Default behavior must still count only immediate .md files.
Acceptance: default unchanged, nested Markdown included with --recursive, .txt excluded, empty directory outputs 0. Metric: local scenario pass rate 100%.
I authorize implementing this scope, creating/removing isolated fixtures in this temporary project, and saving workflow inputs, execution logs, and reports in this workspace's external storage_root under the configured ITER_HOME. Preserve the evidence. Do not access real user data or the network, install dependencies, change global settings, publish, or build. Complete this iteration in English.
```

Test a pause after the proposal is recorded, then resume in a fresh session using the same workspace and `ITER_HOME`. Before implementation, revise the scope with an explicit user request and verify old grants/results are not silently reused. Cancel an active iteration and verify `stopped` without implementation approval; repeated cancellation should not add events. Repeat the selected-scope case in Chinese using the [Chinese prompts](testing.md).

After the user asks to develop, verify that implementation, necessary checks, evaluation, and transition to `complete` happen in the same run without a separate completion request. Failed or blocked work with no executable next step should reach `stopped` honestly. Default to one delivery cycle; use `iterate` only for requested continued rounds. After a terminal result, invoke the skill again or say "continue iterating": it should offer fresh choices or use the newly specified feature, then initialize the selected proposal with `init --new-cycle`, preserving history without requiring "start another iteration". An explicit request to inspect the previous result only reads it; unfinished active work resumes without being overwritten.

For storage acceptance, verify read-only discovery leaves a fresh workspace and Iter data root unchanged; two workspaces have independent records; a denied external write never creates a project fallback. In disposable legacy fixtures, migrate and inspect preserved grants/report bodies, readable old evidence references, an external backup, and removal of the old `.product-loop/` directory. Move one disposable workspace, explicitly `relocate` it, and check continuity; a second existing clone must remain separate. Retain the project and external data until reports have been reviewed, then clean up only these trial directories.

An optional local runner bounds one real host invocation and retains the prompt, process result, transcript, and errors:

```sh
python3 scripts/run-host-trial.py --host codex --workspace /path/to/isolated-trial --prompt-file /path/to/request.txt --output /path/to/new-log-directory --timeout 180
```

Run the command from the Iter checkout. Use `--host claude` for Claude; `--executable /path/to/codex` can select a compatible existing binary without replacing the global CLI. Each invocation starts a fresh model session; saved workspace state enables workflow resume. The runner uses existing account credentials; native model calls can consume account usage, and Claude invocations have a $2 ceiling. It is opt-in and excluded from CI. Review raw logs before sharing them; publish only a redacted summary.

The recorded complete cycles took several minutes. For a full selected-scope run, a larger bound such as `--timeout 600` is useful. A timeout keeps the existing workflow state for another fresh session; it does not cancel the cycle or establish success. The runner exits `124` on timeout and `1` when the host process fails, while preserving the host's actual exit status in `process.json`.

Verify actual code changes and subprocess observations, preservation of unrelated files, correct authorization reuse, and `status`/evaluation agreement. Passing exit status or skill discovery alone is insufficient. Treat API errors, model/CLI incompatibility, timeouts, and unavailable access as incomplete validation.

## Reproducible evidence replay

The [English](note-counter.en.md) and [Chinese](note-counter.zh-CN.md) walkthroughs distinguish actual CLI evidence from model-session evidence. Their one-minute replays are presentation artifacts, not recordings of a host UI or evidence of real-user value.
