# Workflow contract

The single skill owns `research → differentiation → experiment → approval → development → evaluation`. Evaluation chooses `complete`, `iterate`, or `stop`; `iterate` creates a new cycle and returns to research. The maximum-round budget applies.

## Durable decisions

- `.product-loop/state.json` is the only current phase pointer; cycle artifacts and the decision log preserve evidence and decisions.
- Use the helper for initialization, grants, transitions, execution records, and revisions. Never hand-edit approval, phase, metric, selection, or validation mode to pass a gate.
- A concrete user-selected proposal can authorize its listed implementation. Save the real decision and proposal version on initialization; the approval phase consumes that grant without another question.
- Implementation and local-test grants are independent. Their source is a real user message, not model-generated permission. Rejection or absence of a grant cannot become approval.
- Research and baseline measurements can add evidence. Material changes to scope, target, acceptance, validation mode, data operations, or risk require a presented revision and matching grant.
- A revision preserves previous artifacts and decisions, updates the contract consistently, and clears inapplicable results. Never silently replace an approved real-user metric with a local task metric.
- A user-requested new iteration after a terminal result uses `init --new-cycle`, preserving the previous cycle and audit log. Never overwrite an active cycle to restart it.
- Record withdrawn permissions with the authorization revocation flags; denial is not a grant.
- An explicit user cancellation or rejection ends any active phase with `stop`. Preserve artifacts and decisions, skip unfinished-report gates, and never authorize implementation merely to reach a terminal stage. A request to pause keeps the cycle active.
- Iteration clears executed results. Reuse only grants whose recorded scope still covers the current contract; honor permissions limited to one cycle.

## Proportionate gates

Research needs a traceable basis and explicit evidence limits. Counts of competitors, domains, participants, or report characters are not quality gates. Distinguish facts, inferences, assumptions, unknowns, and counterevidence.

Local research can proceed from repository evidence and an approved executable plan. Baselines and results may be pending. After authorized development, record actual execution or a concrete blocker before evaluation. Failure can justify iteration or stopping; completion requires the agreed validation contract to pass.

Validate artifacts before advancing. Repair ordinary errors without asking. A finished phase is not a reason to end the invocation, and the user never needs to invoke another stage skill.
