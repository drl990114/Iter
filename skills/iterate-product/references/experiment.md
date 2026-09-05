# Define and authorize the experiment

Read the saved proposal/grants, research, selected opportunity, charter, and experiment template. Elaborate the chosen scope into one measurable, reversible experiment.

Include hypothesis, metric/target, baseline or baseline plan, acceptance and guardrails, smallest scope and non-goals, validation method, evidence collection, material risks, recovery, and stop conditions. Check existing open-source options and explain adoption costs before custom infrastructure.

## Validation choice

- `product_metric`: use observed product data appropriate to the claim. Sample and observation window depend on this experiment; there is no five-user gate.
- `local_scenario`: define reproducible tasks on the real product path, expected observations, metric target, execution conditions, and isolated data. Include relevant failures and recovery. A hypothetical persona helps design a test; it is not a participant or execution result.

Without a matching local grant, present scenarios, data scope, side effects, and recovery before asking. Continue independent read-only analysis while waiting. Reuse existing authorization within scope.

## Approval without repetition

An opening choice authorizes implementation when the user saw concrete scope, metric/acceptance, validation method, and risks and selected it on that basis. Save that decision and proposal version. Write the experiment without expanding the contract, validate, and let the saved grant satisfy approval.

If no matching implementation grant exists, present the complete decision and ask once. Record only permissions granted. Local-test permission does not approve feature edits, and implementation permission does not authorize local data operations.

When evidence requires changes to scope, target, acceptance, validation mode, or material risk, explain the revision and use `revise` with the updated proposal and applicable grants. This includes legacy cycles already in development or evaluation. Preserve earlier evidence; never change criteria merely to fit a failed result.
