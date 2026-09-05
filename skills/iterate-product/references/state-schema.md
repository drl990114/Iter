# State and CLI

CLI JSON escapes Unicode for reliable non-UTF-8 pipes, including Windows. JSON decoding restores the original text; Markdown and state files use UTF-8.

The helper is `scripts/product_loop.py` inside the loaded skill directory. It uses Python 3.10+ and the standard library. `.product-loop/state.json` remains schema version `1`, with the existing stages, artifact names, metric object, round budget, and decision log. Old states without a validation contract default to `product_metric`; a missing `language` means `zh-CN`.

The agent prepares the JSON from the user's plain-language choice. Never ask the user to fill in a state file or approve raw JSON. Keep proposal and evidence input files in the workspace so decisions remain reviewable; generated cycle artifacts are the durable execution record.

## Chosen proposal

Example: a small local workflow experiment with one selected feature. Replace this example with the scope and test the user actually selected.

```json
{
  "id": "first-task-help",
  "title": "Show a contextual first action",
  "objective": "Make the first useful action discoverable in an empty workspace",
  "scope": ["Add one contextual action to the empty workspace using existing components"],
  "acceptance": ["The action opens the existing creation flow", "The flow works with keyboard and pointer"],
  "risks": ["The action could interfere with empty-state keyboard focus"],
  "metric": {"name": "local_first_task_success_rate", "baseline": null, "target": "100%"},
  "validation": {
    "mode": "local_scenario",
    "data_policy": "isolated",
    "data_scope": ["Only a newly created temporary workspace and its fixture files"],
    "side_effects": ["Create and delete fixture files inside the temporary workspace"],
    "recovery": "Remove the temporary workspace after verifying it contains only test fixtures",
    "scenarios": [
      {
        "id": "empty-workspace",
        "steps": ["Create a temporary empty workspace", "Activate the action with keyboard and pointer", "Verify creation and clean up the temporary workspace"],
        "expected": "The existing creation flow completes in both interaction paths without focus regression"
      }
    ]
  }
}
```

The authorization boundary covers the selected ID, objective, scope, acceptance, risks, metric name/target, and validation plan. Cosmetic title edits and measured baselines do not change that boundary. A measured baseline can enrich the plan without changing its target. `local_scenario` defaults to isolated data; `user_data` must be explicit and authorized with the affected data operations and recovery described in the plan. `product_metric` retains a genuine product outcome and can omit local scenarios. Local plans must save concrete `data_scope`, `side_effects`, and `recovery`; these are part of the permission boundary. Unknown proposal fields are rejected instead of silently discarding possible scope restrictions.

## Initialize and resume

After a real user selection and both permissions, initialize and record them together:

```sh
python3 "<skill-dir>/scripts/product_loop.py" init --workspace "<workspace>" --language en --proposal "<proposal.json>" --authorize-implementation --authorize-local --actor user --authorization-evidence "User selected option A and approved its isolated local scenarios"
python3 "<skill-dir>/scripts/product_loop.py" status --workspace "<workspace>"
```

Omit either authorization flag if that permission was not granted. `--authorization-scope contract` is the default: reuse is limited to the unchanged contract. Use `--authorization-scope cycle` when the user's permission applies only to this cycle. The evidence text must accurately identify the actual user decision; these flags record permission, they do not obtain it.

Legacy `init --workspace ... --objective ... --metric ...` remains available; add `--target` for a measurable completion criterion. It does not invent a selected proposal or local authorization. Active state is resumed rather than overwritten. If the user explicitly requests another iteration after `complete`/`stopped`, use `init --new-cycle` with the new selected proposal and grants. This archives the old state and preserves old artifacts and the decision log; it is rejected for an active cycle. Do not use `--force` as a normal restart path. A legacy cycle still needs real metric evidence to complete; missing old targets require an explicit revision rather than invented success.

`--language en|zh-CN` selects report templates for a new cycle; the CLI defaults to `en`. The skill passes the conversation language explicitly. Revisions and automatic rounds retain the saved language. Language is presentation metadata outside the authorization digest; do not revise product scope to translate a report. Existing Chinese states and artifacts need no migration.

Status exposes the current phase, selected proposal, validation mode and evidence state, grants, `language`, and `local_completion_limit` (null for product metrics). Every active phase points to `iterate-product`; terminal phases have no next skill.

## Cancel an iteration

After the user explicitly cancels or rejects the iteration:

```sh
python3 "<skill-dir>/scripts/product_loop.py" stop --workspace "<workspace>" --rationale "The user decided not to pursue this feature" --evidence "User message cancelling this iteration"
```

Optional `--actor` defaults to `user`. `stop` requires a non-empty reason and actual decision evidence, moves any active stage directly to `stopped`, and records `user_stopped` without validating unfinished reports or granting permission. It preserves existing artifacts, observations, grants, and history. Calling it again on a terminal cycle returns the existing state without writing another event; a completed result stays complete. It does not undo delivered code or delete data. A temporary pause keeps the active cycle available for resume. Once stopped, `init --new-cycle` can archive that state and start the user's next selected iteration.

## Authorize later or revise

If the user later grants a missing permission for the same proposal, record it without changing scope, clearing results, or restarting phases:

```sh
python3 "<skill-dir>/scripts/product_loop.py" authorize --workspace "<workspace>" --authorize-local --actor user --authorization-evidence "User approved the saved isolated scenario plan"
```

The same command accepts `--authorize-implementation` and `--authorization-scope`. Record refusal or withdrawal of an existing grant with `--revoke-implementation` or `--revoke-local` and the actual `--authorization-evidence`; do not silently keep a revoked grant. A grant and revocation for the same permission cannot be combined. At approval, plain `advance` consumes a matching saved implementation grant. Legacy `advance --approve --actor user` remains available after an actual explicit approval. Never add `--approve` merely to repair a failed gate.

For a material change, show the revised scope/metric/acceptance/risk and record the user's decision with the new proposal:

```sh
python3 "<skill-dir>/scripts/product_loop.py" revise --workspace "<workspace>" --proposal "<revised-proposal.json>" --rationale "Replace unavailable user-conversion measurement with the explicitly approved local task experiment" --authorize-implementation --authorize-local --actor user --authorization-evidence "User approved the revised local metric and isolated tests"
```

A material revision snapshots prior artifacts under the current cycle’s `revisions/` directory and retains the prior contract in decision history, updates metric/validation consistently, invalidates mismatched grants, and clears inapplicable results. Affected current-stage and downstream artifacts are reset for the new contract so old text cannot pass unchanged. A cycle already at approval, development, or evaluation returns to experiment to update its decision packet; earlier stages continue in place. Changing the selected opportunity returns to differentiation unless research is still current, so the saved choice and opportunity artifact stay consistent. Revisions cannot silently downgrade an approved product metric. A missing grant remains pending and must not be replaced with a fabricated approval.

## Opportunities

Use `selected_id` in the opportunity JSON, matching an existing item. A single item requires explicit selection; an unselected comparison needs 2–7 items. Scoring does not change the selected ID:

```sh
python3 "<skill-dir>/scripts/product_loop.py" score --input "<opportunities.json>" --selected-id first-task-help
```

By default, `score` saves scores and ranks back to the input file atomically and also prints the result. Use `--output "<scored-opportunities.json>"` to write a separate file; do not redirect stdout over the input file.

## Executed evidence

An approved local plan can have pending baseline/results during research. Actual non-blocked local execution requires a local grant. After executing the agreed tasks, prepare a record such as:

```json
{
  "status": "passed",
  "summary": "Both interaction paths completed in the temporary workspace and cleanup succeeded",
  "metric": {"observed": "100%", "target_met": true},
  "acceptance_passed": true,
  "guardrails_passed": true,
  "unresolved_risks": [],
  "results": [
    {
      "scenario_id": "empty-workspace",
      "status": "passed",
      "observed": "Keyboard and pointer each opened and completed the existing creation flow",
      "evidence_refs": ["evidence/first-task.log"]
    }
  ]
}
```

```sh
python3 "<skill-dir>/scripts/product_loop.py" evidence --workspace "<workspace>" --input "<execution.json>"
```

References point to actual evidence, not desired outputs. Prefer workspace-relative paths for portable reports; native absolute paths, Windows drive/UNC paths, spaces, and optional `:line:column` or `#fragment` suffixes are supported. Retain the files through evaluation. A top-level `evidence_refs` list can support aggregate product metrics. The helper binds records to the current cycle and proposal digest and rejects explicitly stale bindings.

Allowed statuses are `passed`, `failed`, and `blocked`. Failed/blocked records can omit a metric; a blocked record can omit results but must explain the actual blocker. Include `acceptance_passed`, `guardrails_passed`, and `unresolved_risks` honestly even when blocked. These records can reach evaluation and justify iteration or stopping, never success without passing evidence.

Complete local validation requires passed observations covering the planned scenarios, the metric target, acceptance/guardrails, usable evidence references, and no unresolved risks. Visibly include `status.local_completion_limit`: `Local scenarios passed; real-user value remains unvalidated.` for English, or `本机场景验证通过；真实用户价值待验证` for Chinese. A sentence in an HTML comment does not count. Product metric completion must not infer real-user outcomes from simulated tasks.

## Transition and audit

```sh
python3 "<skill-dir>/scripts/product_loop.py" validate --workspace "<workspace>"
python3 "<skill-dir>/scripts/product_loop.py" advance --workspace "<workspace>"
python3 "<skill-dir>/scripts/product_loop.py" advance --workspace "<workspace>" --outcome complete
```

Evaluation must contain one matching `verdict: complete|iterate|stop`. Passing `advance --outcome` at any other phase is an error with no state change; use the separate `stop` command for cancellation. Iteration creates a new cycle with empty execution results; grants are reused only within their recorded contract/cycle scope. The default maximum is three rounds. `record --kind ... --summary ... --rationale ... --evidence ...` records additional decisions without granting authority.

Never hand-edit state to force a transition. Validation checks structure, provenance bindings, and referenced outputs; the agent must still judge whether observations and claims are truthful and sufficient.
