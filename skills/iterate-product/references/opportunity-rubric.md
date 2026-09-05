# Opportunity Rubric

Score each factor from 1 to 5. Do not change weights inside the report.

## Positive factors

- `evidence` (20%): strength and independence of supporting evidence.
- `user_pain` (20%): severity and frequency of the user problem.
- `differentiation` (20%): credible advantage over current alternatives.
- `strategic_fit` (15%): fit with charter, capabilities, and constraints.
- `reach` (10%): relevant user population affected.
- `confidence` (10%): confidence that the hypothesis is testable and causal.
- `reversibility` (5%): ease of rollback and learning without lock-in.

## Penalties

- `effort`: implementation and operating cost.
- `risk`: user, data, security, brand, and maintenance risk.

The Python scorer applies the fixed weights and penalties. A high rank means “best next hypothesis to test,” not “proven product differentiation.”

When evidence comes only from competitor reviews or public communities, cap `confidence` at 3. Use a suitable validation contract: an authorized local scenario may test task behavior while real-user value remains unverified. Public post volume must not be used as a reach estimate, and a local scenario pass must not increase confidence in unmeasured user demand.

## Rejection conditions

Reject an opportunity when:

- it has no evidence reference;
- it describes a solution without a specific user problem;
- differentiation depends only on competitors not having a feature;
- the smallest experiment cannot produce a decision;
- material risk cannot be bounded or reversed.
