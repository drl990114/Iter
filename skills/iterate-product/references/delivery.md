# Deliver and record execution

Confirm `development` and matching implementation approval before changing product code. Read the approved experiment and repository instructions. Inspect Git changes when available and preserve unrelated work; non-Git workspaces are supported.

Implement the approved scope, reuse project components and applicable open-source libraries, and keep changes reversible. Add only instrumentation necessary for this experiment. Material changes go through revision.

Follow repository verification policy: proportionate type checks, unit tests, and lint. Do not build when repository guidance prohibits it. Record commands, outcomes, limitations, and rollback in `04-delivery.md`.

For local scenarios, confirm local authorization, use approved isolated samples/copies, and execute the actual workflow. Record scenario IDs, observations, measurements, evidence references, acceptance/guardrail outcomes, and unresolved risks through `evidence`. Save generated execution JSON in `paths.inputs_dir` and generated logs in `paths.evidence_dir`. Reference existing user evidence where it already lives. Execution evidence files must exist and remain local unless sharing was authorized; product fixtures still follow their approved data scope.

Record actual failure or a specific environment/permission blocker honestly. A blocked record grants no permission to execute tests. Failure does not lock this phase: enter evaluation with the observed record, which may justify `iterate` or `stop`. Static checks and invented interactions cannot substitute for successful product scenarios.

After implementation and necessary verification, immediately advance to evaluation, write its report, and close the cycle with the supported outcome. The user's development request already covers this routine closure; do not ask them to confirm completion or leave finished work in an active phase. Default to ending this delivery cycle; further rounds require a user request for continued iteration.
