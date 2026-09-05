# Research the selected problem

Read the proposal, charter, repository guidance, and research template. Confirm the present workflow, target user, and concrete problem without silently replacing the user's selection.

Use sources that can change this decision: repository behavior and tests, available first-party feedback or telemetry, relevant competitor documentation and user-authored discussions, and applicable open-source libraries. Avoid exhaustive market research before the opening choice.

## Evidence and limits

Write exactly one `direct_user_feedback: sufficient|sparse|absent` line. Simulations and public posts do not make absent first-party feedback sufficient.

When feedback is sparse or absent, investigate useful external signals and propose local scenarios if execution can resolve the current uncertainty. Two competitors and several independent discussions across venues can help triangulation; these are sampling suggestions, never quotas. Record access limitations and proceed with evidence actually available. Do not fabricate demand or infer reach from likes or post counts.

Distinguish supported facts, inferences, assumptions, unknowns, and counterevidence. Note relevant sampling bias and deduplicate reposts. For a section with no evidence, explain the gap and next bounded step instead of leaving it blank.

## Sources

Under the generated template's `## Sources` (English) or `## 来源` (Chinese), give traceable references and the claims they support:

```text
- [repository] `src/onboarding.ts:42` — the current first action takes three steps.
- [direct-user] `support/ticket-123.md` — an actual user's reported blocker.
- [community] [Discussion](https://example.com/direct-thread) — observed workaround; accessed YYYY-MM-DD.
- [competitor] [Official docs](https://example.com/feature) — documented alternative; accessed YYYY-MM-DD.
- [local-scenario] `evidence/baseline.txt` — actual execution, with date and conditions.
```

Prefer primary sources for technical claims and direct pages rather than search-result pages. A future evidence filename is a planned output, not an observation. Do not contact users or upload local data without authorization.

For `local_scenario`, the approved plan may have an unmeasured baseline and pending results. Repository evidence can justify the experiment now; run tests only within the local grant. Write `01-research.md`, validate, and continue.
