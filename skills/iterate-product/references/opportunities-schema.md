# Opportunities Schema

Present 2–3 opportunities for an open-ended choice. A single explicitly selected opportunity is valid; legacy reports with up to 7 remain supported. `selected_id` must name an item in the list and preserve the user decision independently of rank.

```json
{
  "cycle_id": "activation",
  "selected_id": "guided-first-success",
  "opportunities": [
    {
      "id": "guided-first-success",
      "title": "Guide users to a first successful outcome",
      "target_user": "New users without an existing workflow",
      "problem": "Users cannot identify the first useful action",
      "evidence_refs": [
        "01-research.md#用户问题证据"
      ],
      "hypothesis": "If the product recommends one contextual action, activation rises",
      "alternative_gap": "Generic onboarding does not use current project state",
      "counterargument": "The issue may be acquisition quality rather than onboarding",
      "smallest_experiment": "One contextual recommendation with instrumentation",
      "risks": [
        "Recommendations may feel intrusive"
      ],
      "scores": {
        "evidence": 4,
        "user_pain": 4,
        "differentiation": 3,
        "strategic_fit": 5,
        "reach": 4,
        "confidence": 3,
        "reversibility": 5,
        "effort": 2,
        "risk": 2
      }
    }
  ]
}
```

Every score must be an integer from 1 to 5. Run the scorer to add `weighted_score`, `rank`, and `recommended`.

For a single selected item use `score --input <file> --selected-id <id>` or put `selected_id` in the JSON. A selected opportunity does not need to have the highest score.
