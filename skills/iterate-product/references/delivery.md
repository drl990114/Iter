# Deliver and record execution

Confirm `development` and matching implementation approval before changing product code. Read the approved experiment and repository instructions. Inspect Git changes when available and preserve unrelated work; non-Git workspaces are supported.

Implement the approved scope, reuse project components and applicable open-source libraries, and keep changes reversible. Add only instrumentation necessary for this experiment. Material changes go through revision.

Follow repository verification policy: proportionate type checks, unit tests, and lint. Do not build when repository guidance prohibits it. Record commands, outcomes, limitations, and rollback in `04-delivery.md`.

For local scenarios, confirm local authorization, use approved isolated samples/copies, and execute the actual workflow. Record scenario IDs, observations, measurements, evidence references, acceptance/guardrail outcomes, and unresolved risks through `evidence`. Execution evidence files must exist and remain local unless sharing was authorized.

Record actual failure or a specific environment/permission blocker honestly. A blocked record grants no permission to execute tests. Failure does not lock this phase: enter evaluation with the observed record, which may justify `iterate` or `stop`. Static checks and invented interactions cannot substitute for successful product scenarios.
