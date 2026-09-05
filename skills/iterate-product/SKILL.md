---
name: iterate-product
description: Start or resume a product iteration by proposing 2–3 concrete improvements, carrying the user's chosen scope through research, implementation, and evaluation, and using authorized local scenarios when user feedback is unavailable. Use for product iteration planning, autonomous product improvement, or continuing a saved Iter decision.
license: MIT
---

# Run Iter

Own the iteration from a useful choice to an evidence-backed result. This is one skill with internal phases; read only the reference for the current phase.

## Start with a useful choice

1. Locate the workspace and read applicable repository instructions. Inspect the product, relevant implementation, available tests, and applicable open-source options. Without a Git root, use the user's workspace directory.
2. If `.product-loop/state.json` exists, run `status`. Resume an active cycle without replacing its objective or repeating the menu. For a terminal cycle, report the result unless the user explicitly asks to start another iteration; then present fresh choices and use `init --new-cycle` after selection, preserving the old cycle.
3. For a new open-ended iteration, do a lightweight repository review and present **2–3 concrete feature improvements** before an exhaustive market survey. Each needs a user benefit, observed problem, smallest scope, metric/acceptance, validation method, main risk, and tradeoff. Recommend one with a reason; mark unmeasured baselines and assumptions honestly.
4. If the user specified a feature, focus on it instead of inventing alternatives. An under-specified direction authorizes investigation, not an unpresented implementation scope.
5. For a new choice, explain that selection authorizes its listed implementation scope. Describe proposed local scenarios, data scope, possible changes, and recovery. Reuse authorization already given in the user's request or conversation; ask only for a missing permission or a material change. Implementation and local testing are separate grants that can be answered together.
6. After selection, initialize with the chosen proposal and only the permissions actually granted. Pass `--language en` or `--language zh-CN` to match the conversation; CLI defaults to English. Save the proposal and grants together so interruption does not cause repeated approval questions. See [state-schema.md](references/state-schema.md) for the proposal and CLI.

Do not require five users, a fixed participant count, or participant recruitment merely to start. When feedback is absent or sparse, offer isolated local scenarios and gather useful repository, competitor, or community evidence. Local scenario success leaves real-user value unverified.

## Resume and advance

Resolve `<skill-dir>` to this loaded skill's directory, not the workspace or a cached absolute path. Keep its `scripts`, `references`, and `assets` together. Use the host's available file, shell, browser, and user-question tools; a plain conversation question works without a dedicated question tool. Python 3.10+ runs the helper with no third-party packages. Use the available Python command (`python3`, `python`, or Windows `py -3`), verify its version, and quote paths. Node.js is needed only for optional installation tooling or the DeepSeek adapter. If a capability is missing, finish independent work and identify the precise remaining need.

```sh
python3 "<skill-dir>/scripts/product_loop.py" status --workspace "<workspace>"
```

Read [workflow-contract.md](references/workflow-contract.md) and the current phase guide, produce its artifact, validate, advance, and immediately continue in the same invocation:

| Stage | Phase guide | Artifact |
|---|---|---|
| `research` | [research.md](references/research.md) | `01-research.md` |
| `differentiation` | [differentiation.md](references/differentiation.md) | `02-opportunities.json` |
| `experiment` | [experiment.md](references/experiment.md) | `03-experiment.md` |
| `approval` | [experiment.md](references/experiment.md) | Recorded user authorization |
| `development` | [delivery.md](references/delivery.md) | `04-delivery.md` |
| `evaluation` | [evaluation.md](references/evaluation.md) | `05-evaluation.md` |

```sh
python3 "<skill-dir>/scripts/product_loop.py" validate --workspace "<workspace>"
python3 "<skill-dir>/scripts/product_loop.py" advance --workspace "<workspace>"
```

At `approval`, reuse the saved grant for the unchanged concrete proposal. Do not ask again simply because this phase was reached. If no matching grant exists, present the concrete decision and record the user's response before development. Simulation permission alone does not authorize implementation; implementation permission alone does not authorize local data operations.

At `evaluation`, use `advance --outcome complete|iterate|stop` with the report's verdict. A bounded follow-up may continue within the remaining round budget and authorization. At `complete` or `stopped`, report the outcome, evidence limits, and next useful action, then end the run. Completion does not authorize publication or release.

When the user cancels or rejects the iteration, use `stop --workspace "<workspace>" --rationale "<reason>" --evidence "<actual user decision>"` immediately. This works at any active phase without finishing reports or obtaining implementation permission. Preserve the existing artifacts; a later explicitly requested iteration can use `init --new-cycle`. Pausing to resume later is not cancellation. `advance --outcome` is only for evaluation.

Keep the cycle's saved report language. Old states without `language` use Chinese; new templates and `status` provide the expected headings and local-completion sentence. Reference guides are in English, but user-facing discussion and reports follow the selected language.

## Pause only for a material decision

Keep progressing through repairable validation failures, deterministic phase changes, and routine implementation choices. Preserve the user's direction even when scoring prefers another option. Research may enrich evidence without reopening approval.

Ask when scope, metric target, acceptance, validation mode, data operations, or material risk changes beyond the grant; show the actual revision and its consequences. Use `revise` rather than silently changing an approved experiment or state file. Reuse granted permissions within their recorded scope.

Pause for unavailable necessary authority/access, exhausted evidence with no executable next step, terminal results, or the round budget. Respect separate authorization for production release, pricing, permissions, destructive changes, and communication to others.

## Evidence means what it proves

- `product_metric` evaluates the agreed product outcome with appropriate observed data; it has no universal minimum participant count.
- `local_scenario` evaluates agreed tasks in the actual application or execution path, using isolated samples or copies by default. Research may contain a baseline plan and pending results; completion requires real execution evidence.
- Record failed or blocked execution and move to evaluation. Missing evidence cannot become success; it can justify `iterate` or `stop`.
- For local completion, visibly include the `local_completion_limit` sentence from `status`: **Local scenarios passed; real-user value remains unvalidated.** in English, or **本机场景验证通过；真实用户价值待验证** in Chinese. Imagined personas, passing lint, and feature delivery do not prove real-user demand.
