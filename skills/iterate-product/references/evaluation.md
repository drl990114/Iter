# Evaluate the approved contract

Read the proposal/version, experiment, delivery, execution evidence, and relevant diff. Use independent review when available and useful; otherwise review explicitly against the original criteria. Re-run only relevant authorized checks whose evidence is missing or stale.

Compare acceptance, target, guardrails, observations, attribution limits, regressions, and operational risk. Separate technical evidence, local task evidence, and real-user outcomes. Preserve counterevidence and do not rewrite criteria to justify implementation.

## Verdicts

- `complete`: the approved contract passes, acceptance and guardrails hold, and no material unresolved risk remains. For `local_scenario`, require actual execution and visibly include `status.local_completion_limit`: **Local scenarios passed; real-user value remains unvalidated.** for English, or **本机场景验证通过；真实用户价值待验证** for Chinese. Completion concerns the agreed local experiment, not demand, retention, or willingness to pay.
- `iterate`: one concrete bounded follow-up can resolve the uncertainty within the round budget and authority. Do not create endless rounds simply because real-user data is unavailable.
- `stop`: the hypothesis fails, risk is disproportionate, evidence is insufficient with no executable next step, or the round budget is exhausted. Blocked execution can support stopping without pretending it passed.

Write `05-evaluation.md` using the generated headings in the cycle's saved language, with exactly one `verdict: complete|iterate|stop` line, evidence, counterevidence, remaining risks, and next action. Local completion also includes the exact evidence-limit sentence above. Validate, then advance using the same verdict. User cancellation before evaluation uses `stop` directly; it does not require an evaluation report.

Each new round needs new execution evidence. Reuse grants only when they still cover scope, metric, acceptance, test method, and data/risk boundaries. New material choices require a concrete revision.
