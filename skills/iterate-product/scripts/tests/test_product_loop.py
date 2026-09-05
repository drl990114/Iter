from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "product_loop.py"
SKILL_PATH = Path(__file__).resolve().parents[2] / "SKILL.md"
SPEC = importlib.util.spec_from_file_location("product_loop", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
product_loop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(product_loop)


def filled_markdown(
    headings: list[str],
    extra: str = "",
    body: str = "本节说明已核实的范围、结果与限制。",
) -> str:
    sections = []
    for heading in headings:
        sections.append(f"{heading}\n\n{body}")
    return "\n\n".join(sections) + "\n" + extra


def opportunity(identifier: str, score: int) -> dict:
    return {
        "id": identifier,
        "title": f"Opportunity {identifier}",
        "target_user": "A specific user segment",
        "problem": "A repeated and evidenced user problem",
        "evidence_refs": ["01-research.md#用户问题证据"],
        "hypothesis": "A falsifiable behavior change",
        "alternative_gap": "Existing alternatives leave this job incomplete",
        "counterargument": "The observed pain may not be frequent enough",
        "smallest_experiment": "A reversible, instrumented thin slice",
        "risks": ["Selection bias"],
        "scores": {
            "evidence": score,
            "user_pain": score,
            "differentiation": score,
            "strategic_fit": score,
            "reach": score,
            "confidence": score,
            "reversibility": score,
            "effort": 2,
            "risk": 2,
        },
    }


def product_metric_evidence(workspace: Path, status: str = "passed") -> dict:
    payload = {
        "status": status,
        "summary": "Measured activation from the approved product cohort"
        if status == "passed"
        else "Product metric data is unavailable",
        "acceptance_passed": status == "passed",
        "guardrails_passed": status == "passed",
        "unresolved_risks": []
        if status == "passed"
        else ["Product outcome is unverified"],
    }
    if status == "passed":
        (workspace / "metric.csv").write_text(
            "activated,total,rate\n38,100,0.38\n", encoding="utf-8"
        )
        payload["metric"] = {"observed": "0.38", "target_met": True}
        payload["evidence_refs"] = ["metric.csv"]
    return payload


class ProductLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name)
        product_loop.initialize_workspace(
            workspace=self.workspace,
            objective="Improve activation",
            metric="activation_rate",
            baseline="0.30",
            target="0.36",
            cycle_id="activation",
            max_rounds=2,
            language="zh-CN",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_orchestrator_runs_until_a_real_decision_boundary(self) -> None:
        instructions = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("name: iterate-product", instructions)
        self.assertEqual(
            {skill for skill in product_loop.STAGE_SKILLS.values() if skill},
            {"iterate-product"},
        )

    def test_init_creates_state_and_unfilled_template_fails_gate(self) -> None:
        status = product_loop.status_payload(self.workspace)
        self.assertEqual(status["stage"], "research")
        self.assertEqual(status["next_skill"], "iterate-product")
        self.assertEqual(status["validation"]["mode"], "product_metric")
        validation = product_loop.validate_stage(self.workspace)
        self.assertFalse(validation["ok"])
        self.assertIn("template markers", " ".join(validation["errors"]))

    def test_short_research_without_direct_feedback_uses_traceable_source(self) -> None:
        state = product_loop.load_state(self.workspace)
        research_path = product_loop.artifact_path(self.workspace, state, "research")
        (self.workspace / "README.md").write_text(
            "Product capabilities", encoding="utf-8"
        )
        sufficient_research = filled_markdown(
            product_loop.REQUIRED_HEADINGS["research"],
            extra=(
                "\ndirect_user_feedback: absent\n- [repository] [Product](README.md)\n"
            ),
        )
        research_path.write_text(sufficient_research, encoding="utf-8")
        validation = product_loop.validate_stage(self.workspace)
        self.assertTrue(validation["ok"], validation["errors"])

        missing_source = filled_markdown(
            product_loop.REQUIRED_HEADINGS["research"],
            extra=(
                "\ndirect_user_feedback: absent\n- [repository] [Missing](missing.md)\n"
            ),
        )
        research_path.write_text(missing_source, encoding="utf-8")
        validation = product_loop.validate_stage(self.workspace)
        self.assertFalse(validation["ok"])
        self.assertIn("traceable source", " ".join(validation["errors"]))

        research_path.write_text(
            sufficient_research.replace(
                "## 用户问题证据\n\n本节说明已核实的范围、结果与限制。",
                "## 用户问题证据\n",
            ),
            encoding="utf-8",
        )
        self.assertIn(
            "Required section is empty",
            " ".join(product_loop.validate_stage(self.workspace)["errors"]),
        )

    def test_score_orders_opportunities_deterministically(self) -> None:
        payload = {
            "cycle_id": "activation",
            "opportunities": [
                opportunity("low", 2),
                opportunity("high", 5),
                opportunity("medium", 3),
            ],
        }
        scored = product_loop.score_payload(payload)
        self.assertEqual(
            [item["id"] for item in scored["opportunities"]],
            ["high", "medium", "low"],
        )
        self.assertEqual(scored["opportunities"][0]["rank"], 1)
        self.assertTrue(scored["opportunities"][0]["recommended"])

    def test_full_cycle_requires_approval_and_can_complete(self) -> None:
        state = product_loop.load_state(self.workspace)
        research_path = product_loop.artifact_path(self.workspace, state, "research")
        research = filled_markdown(
            product_loop.REQUIRED_HEADINGS["research"],
            extra=(
                "\ndirect_user_feedback: sufficient\n"
                "- [repository] /repo/src/product.ts\n"
                "- [direct-user] https://example.com/primary-source\n"
            ),
        )
        research_path.write_text(research, encoding="utf-8")
        product_loop.advance_state(self.workspace)

        state = product_loop.load_state(self.workspace)
        opportunities_path = product_loop.artifact_path(
            self.workspace, state, "differentiation"
        )
        opportunities_path.write_text(
            json.dumps(
                {
                    "cycle_id": "activation",
                    "opportunities": [
                        opportunity("a", 5),
                        opportunity("b", 4),
                        opportunity("c", 3),
                    ],
                }
            ),
            encoding="utf-8",
        )
        product_loop.score_file(opportunities_path)
        product_loop.advance_state(self.workspace)

        state = product_loop.load_state(self.workspace)
        experiment_path = product_loop.artifact_path(
            self.workspace, state, "experiment"
        )
        experiment_path.write_text(
            filled_markdown(product_loop.REQUIRED_HEADINGS["experiment"]),
            encoding="utf-8",
        )
        product_loop.advance_state(self.workspace)
        with self.assertRaises(product_loop.ProductLoopError):
            product_loop.advance_state(self.workspace)
        product_loop.advance_state(self.workspace, approve=True, actor="owner")
        product_loop.record_evidence(
            self.workspace, product_metric_evidence(self.workspace)
        )

        state = product_loop.load_state(self.workspace)
        delivery_path = product_loop.artifact_path(self.workspace, state, "development")
        delivery_path.write_text(
            filled_markdown(product_loop.REQUIRED_HEADINGS["development"]),
            encoding="utf-8",
        )
        product_loop.advance_state(self.workspace)

        state = product_loop.load_state(self.workspace)
        evaluation_path = product_loop.artifact_path(
            self.workspace, state, "evaluation"
        )
        evaluation_path.write_text(
            filled_markdown(
                product_loop.REQUIRED_HEADINGS["evaluation"],
                extra="\nverdict: complete\n",
            ),
            encoding="utf-8",
        )
        final_state = product_loop.advance_state(self.workspace, outcome="complete")
        self.assertEqual(final_state["stage"], "complete")

    def test_iteration_resets_approval_and_stops_at_round_budget(self) -> None:
        state = product_loop.load_state(self.workspace)
        state["stage"] = "evaluation"
        state["approval"] = {
            "status": "approved",
            "actor": "owner",
            "at": product_loop.utc_now(),
        }
        evaluation_path = product_loop.artifact_path(
            self.workspace, state, "evaluation"
        )
        evaluation_path.write_text(
            filled_markdown(
                product_loop.REQUIRED_HEADINGS["evaluation"],
                extra="\nverdict: iterate\n",
            ),
            encoding="utf-8",
        )
        product_loop.save_state(self.workspace, state)
        product_loop.record_evidence(
            self.workspace, product_metric_evidence(self.workspace, "blocked")
        )
        next_state = product_loop.advance_state(self.workspace, outcome="iterate")
        self.assertEqual(next_state["stage"], "research")
        self.assertEqual(next_state["round"], 2)
        self.assertEqual(next_state["approval"]["status"], "pending")

        next_state["stage"] = "evaluation"
        next_evaluation = product_loop.artifact_path(
            self.workspace, next_state, "evaluation"
        )
        next_evaluation.write_text(
            filled_markdown(
                product_loop.REQUIRED_HEADINGS["evaluation"],
                extra="\nverdict: iterate\n",
            ),
            encoding="utf-8",
        )
        product_loop.save_state(self.workspace, next_state)
        product_loop.record_evidence(
            self.workspace, product_metric_evidence(self.workspace, "blocked")
        )
        stopped = product_loop.advance_state(self.workspace, outcome="iterate")
        self.assertEqual(stopped["stage"], "stopped")

    def test_legacy_state_cannot_complete_without_observed_product_metric(self) -> None:
        original = product_loop.state_path(self.workspace).read_bytes()
        self.assertEqual(
            product_loop.status_payload(self.workspace)["validation"]["mode"],
            "product_metric",
        )
        self.assertEqual(product_loop.state_path(self.workspace).read_bytes(), original)
        state = product_loop.load_state(self.workspace)
        state["stage"] = "evaluation"
        state["approval"] = {
            "status": "approved",
            "actor": "owner",
            "at": product_loop.utc_now(),
        }
        product_loop.save_state(self.workspace, state)
        product_loop.artifact_path(self.workspace, state, "evaluation").write_text(
            filled_markdown(
                product_loop.REQUIRED_HEADINGS["evaluation"], "verdict: complete\n"
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            product_loop.ProductLoopError, "execution evidence"
        ):
            product_loop.advance_state(self.workspace, outcome="complete")
        product_loop.record_evidence(
            self.workspace, product_metric_evidence(self.workspace)
        )
        self.assertEqual(
            product_loop.advance_state(self.workspace, outcome="complete")[
                "completion"
            ]["basis"],
            "product_metric",
        )

    def test_legacy_metric_change_invalidates_prior_evidence(self) -> None:
        state = product_loop.load_state(self.workspace)
        state["stage"] = "evaluation"
        state["approval"] = {
            "status": "approved",
            "actor": "owner",
            "at": product_loop.utc_now(),
        }
        product_loop.save_state(self.workspace, state)
        state = product_loop.record_evidence(
            self.workspace, product_metric_evidence(self.workspace)
        )
        state["metric"]["target"] = "0.50"
        product_loop.save_state(self.workspace, state)
        product_loop.artifact_path(self.workspace, state, "evaluation").write_text(
            filled_markdown(
                product_loop.REQUIRED_HEADINGS["evaluation"], "verdict: complete\n"
            ),
            encoding="utf-8",
        )
        self.assertIn(
            "current proposal scope",
            " ".join(product_loop.validate_stage(self.workspace)["errors"]),
        )


def selected_proposal(mode: str = "local_scenario") -> dict:
    return {
        "id": "activation",
        "title": "Improve the first run",
        "objective": "Finish setup",
        "scope": ["Simplify the existing setup flow"],
        "acceptance": ["An isolated sample finishes setup in two steps"],
        "risks": ["Keep existing saved preferences recoverable"],
        "metric": {"name": "setup_steps", "baseline": None, "target": "2"},
        "validation": {
            "mode": mode,
            "data_policy": "isolated",
            "data_scope": ["Temporary test profile under the workspace"],
            "side_effects": ["Create isolated sample preferences"],
            "recovery": "Remove only the temporary test profile",
            "scenarios": [
                {
                    "id": "setup",
                    "steps": ["Open an isolated profile", "Finish setup"],
                    "expected": "Two steps",
                }
            ],
        },
    }


class SelectedProposalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name)
        (self.workspace / "README.md").write_text(
            "Existing setup behavior", encoding="utf-8"
        )
        (self.workspace / "result.txt").write_text(
            "Observed two setup steps", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def initialize(
        self,
        implementation: bool = True,
        local: bool = True,
        scope: str = "contract",
        mode: str = "local_scenario",
        language: str = "zh-CN",
    ) -> dict:
        return product_loop.initialize_workspace(
            self.workspace,
            cycle_id="selected",
            max_rounds=2,
            proposal=selected_proposal(mode),
            authorize_implementation=implementation,
            authorize_local=local,
            actor="owner",
            authorization_evidence="User selected the listed scope and permissions",
            authorization_scope=scope,
            language=language,
        )

    def write_artifact(self, stage: str, extra: str = "") -> None:
        state = product_loop.load_state(self.workspace)
        language = product_loop.report_language(state)
        product_loop.artifact_path(self.workspace, state, stage).write_text(
            filled_markdown(
                product_loop.required_headings(language)[stage],
                extra,
                "Verified scope, observations, and limitations."
                if language == "en"
                else "本节说明已核实的范围、结果与限制。",
            ),
            encoding="utf-8",
        )

    def approval(self) -> dict:
        self.write_artifact(
            "research",
            "direct_user_feedback: absent\n- [repository] [Readme](README.md)\n",
        )
        product_loop.advance_state(self.workspace)
        state = product_loop.load_state(self.workspace)
        product_loop.atomic_write_json(
            product_loop.artifact_path(self.workspace, state, "differentiation"),
            product_loop.score_payload(
                {"opportunities": [opportunity("activation", 4)]},
                selected_id="activation",
            ),
        )
        product_loop.advance_state(self.workspace)
        self.write_artifact("experiment")
        return product_loop.advance_state(self.workspace)

    def development(self) -> dict:
        self.approval()
        return product_loop.advance_state(self.workspace)

    def evidence(self, status: str = "passed") -> dict:
        passed = status == "passed"
        payload = {
            "status": status,
            "summary": "Observed execution"
            if status != "blocked"
            else "Browser unavailable; no scenario executed",
            "acceptance_passed": passed,
            "guardrails_passed": passed,
            "unresolved_risks": [] if passed else ["Execution has not passed"],
        }
        if status != "blocked":
            payload["metric"] = {
                "observed": "2" if passed else "4",
                "target_met": passed,
            }
            payload["results"] = [
                {
                    "scenario_id": "setup",
                    "status": status,
                    "observed": "2 steps" if passed else "4 steps",
                    "evidence_refs": ["result.txt"],
                }
            ]
        return payload

    def test_init_saves_selection_and_independent_authorizations_atomically(
        self,
    ) -> None:
        state = self.initialize(local=False)
        self.assertEqual(state["selected_id"], "activation")
        self.assertTrue(product_loop.authorization_valid(state, "implementation"))
        self.assertFalse(product_loop.authorization_valid(state, "local"))
        self.assertEqual(state["schema_version"], 1)
        self.assertIsNone(state["metric"]["baseline"])
        self.assertEqual(state, product_loop.load_state(self.workspace))

    def test_invalid_init_authorization_does_not_create_workspace_state(self) -> None:
        with self.assertRaises(product_loop.ProductLoopError):
            product_loop.initialize_workspace(
                self.workspace,
                proposal=selected_proposal(),
                authorize_implementation=True,
            )
        self.assertFalse(product_loop.state_path(self.workspace).exists())

    def test_research_plan_advances_without_results_or_local_permission(self) -> None:
        self.initialize(local=False)
        self.write_artifact(
            "research",
            "direct_user_feedback: absent\n- [repository] [Readme](README.md)\n",
        )
        self.assertTrue(product_loop.validate_stage(self.workspace)["ok"])
        self.assertEqual(
            product_loop.advance_state(self.workspace)["stage"], "differentiation"
        )

    def test_selected_scope_advances_without_duplicate_approval(self) -> None:
        self.initialize()
        state = self.development()
        self.assertEqual(state["stage"], "development")
        self.assertEqual(state["approval"]["actor"], "owner")
        self.write_artifact("development")
        self.assertFalse(product_loop.validate_stage(self.workspace)["ok"])

    def test_local_permission_does_not_authorize_implementation(self) -> None:
        self.initialize(implementation=False)
        state = product_loop.load_state(self.workspace)
        state["stage"] = "approval"
        product_loop.save_state(self.workspace, state)
        with self.assertRaises(product_loop.ProductLoopError):
            product_loop.advance_state(self.workspace)

    def test_authorize_later_preserves_stage_and_existing_results(self) -> None:
        self.initialize(local=False)
        self.development()
        with self.assertRaises(product_loop.ProductLoopError):
            product_loop.record_evidence(self.workspace, self.evidence())
        state = product_loop.authorize_state(
            self.workspace,
            local=True,
            evidence="User approved isolated scenario execution",
        )
        self.assertEqual(state["stage"], "development")
        state = product_loop.record_evidence(self.workspace, self.evidence())
        evidence = state["validation"]["evidence"]
        state = product_loop.authorize_state(
            self.workspace, local=True, evidence="User reaffirmed permission"
        )
        self.assertEqual(state["validation"]["evidence"], evidence)

    def test_local_complete_reports_real_user_value_unvalidated(self) -> None:
        self.initialize()
        self.development()
        product_loop.record_evidence(self.workspace, self.evidence())
        self.write_artifact("development")
        product_loop.advance_state(self.workspace)
        self.write_artifact(
            "evaluation", "verdict: complete\n本机场景验证通过；真实用户价值待验证\n"
        )
        state = product_loop.advance_state(self.workspace, outcome="complete")
        self.assertEqual(
            state["completion"],
            {"basis": "local_scenario", "real_user_value": "unvalidated"},
        )

    def test_local_completion_requires_visible_evidence_limit(self) -> None:
        self.initialize()
        self.development()
        product_loop.record_evidence(self.workspace, self.evidence())
        self.write_artifact("development")
        product_loop.advance_state(self.workspace)
        for extra in (
            "verdict: complete\n",
            "verdict: complete\n<!-- 本机场景验证通过；真实用户价值待验证 -->\n",
        ):
            with self.subTest(extra=extra):
                self.write_artifact("evaluation", extra)
                with self.assertRaisesRegex(
                    product_loop.ProductLoopError, "真实用户价值待验证"
                ):
                    product_loop.advance_state(self.workspace, outcome="complete")

    def test_blocked_record_cannot_hide_unauthorized_executed_scenarios(self) -> None:
        self.initialize(local=False)
        self.development()
        for result_status in ("passed", "failed"):
            with self.subTest(result_status=result_status):
                payload = self.evidence(result_status)
                payload["status"] = "blocked"
                payload.pop("metric")
                with self.assertRaisesRegex(
                    product_loop.ProductLoopError, "local authorization"
                ):
                    product_loop.record_evidence(self.workspace, payload)

    def test_blocked_record_cannot_hide_unauthorized_measured_metric(self) -> None:
        self.initialize(local=False)
        self.development()
        payload = self.evidence("blocked")
        payload["metric"] = {"observed": "2", "target_met": True}
        with self.assertRaisesRegex(
            product_loop.ProductLoopError, "local authorization"
        ):
            product_loop.record_evidence(self.workspace, payload)

    def test_partial_execution_blocker_requires_both_current_grants(self) -> None:
        self.initialize()
        self.development()
        payload = self.evidence("failed")
        payload["status"] = "blocked"
        product_loop.record_evidence(self.workspace, payload)
        self.write_artifact("development")
        self.assertTrue(product_loop.validate_stage(self.workspace)["ok"])
        product_loop.authorize_state(
            self.workspace,
            revoke_implementation=True,
            evidence="User withdrew implementation permission",
        )
        with self.assertRaisesRegex(
            product_loop.ProductLoopError, "implementation authorization"
        ):
            product_loop.record_evidence(self.workspace, payload)
        self.assertFalse(product_loop.validate_stage(self.workspace)["ok"])
        product_loop.record_evidence(self.workspace, self.evidence("blocked"))
        self.assertTrue(product_loop.validate_stage(self.workspace)["ok"])

    def test_null_metric_blocker_rejects_completion_without_crashing(self) -> None:
        self.initialize()
        self.development()
        payload = self.evidence("blocked")
        payload["metric"] = None
        product_loop.record_evidence(self.workspace, payload)
        self.write_artifact("development")
        product_loop.advance_state(self.workspace)
        self.write_artifact(
            "evaluation", "verdict: complete\n本机场景验证通过；真实用户价值待验证\n"
        )
        with self.assertRaisesRegex(
            product_loop.ProductLoopError, "Failed or blocked execution"
        ):
            product_loop.advance_state(self.workspace, outcome="complete")

    def test_complete_requires_target_acceptance_guardrails_and_resolved_risks(
        self,
    ) -> None:
        self.initialize()
        self.development()
        self.write_artifact("development")
        product_loop.record_evidence(self.workspace, self.evidence())
        product_loop.advance_state(self.workspace)
        self.write_artifact(
            "evaluation", "verdict: complete\n本机场景验证通过；真实用户价值待验证\n"
        )
        for field, value in [
            ("acceptance_passed", False),
            ("guardrails_passed", False),
            ("unresolved_risks", ["Unresolved risk"]),
            ("metric", {"observed": "4", "target_met": False}),
        ]:
            with self.subTest(field=field):
                evidence = self.evidence()
                evidence[field] = value
                product_loop.record_evidence(self.workspace, evidence)
                with self.assertRaises(product_loop.ProductLoopError):
                    product_loop.advance_state(self.workspace, outcome="complete")

    def test_blocked_without_local_authorization_can_stop_but_not_complete(
        self,
    ) -> None:
        self.initialize(local=False)
        self.development()
        product_loop.record_evidence(self.workspace, self.evidence("blocked"))
        self.write_artifact("development")
        product_loop.advance_state(self.workspace)
        self.write_artifact("evaluation", "verdict: complete\n")
        with self.assertRaises(product_loop.ProductLoopError):
            product_loop.advance_state(self.workspace, outcome="complete")
        self.write_artifact("evaluation", "verdict: stop\n")
        self.assertEqual(
            product_loop.advance_state(self.workspace, outcome="stop")["stage"],
            "stopped",
        )

    def test_failed_execution_can_reach_evaluation(self) -> None:
        self.initialize()
        self.development()
        product_loop.record_evidence(self.workspace, self.evidence("failed"))
        self.write_artifact("development")
        self.assertEqual(
            product_loop.advance_state(self.workspace)["stage"], "evaluation"
        )

    def test_missing_and_stale_execution_references_are_rejected(self) -> None:
        self.initialize()
        self.development()
        evidence = self.evidence()
        evidence["results"][0]["evidence_refs"] = ["does-not-exist.txt"]
        with self.assertRaisesRegex(product_loop.ProductLoopError, "Unresolvable"):
            product_loop.record_evidence(self.workspace, evidence)
        evidence = self.evidence()
        evidence["cycle_id"] = "previous"
        with self.assertRaisesRegex(product_loop.ProductLoopError, "different cycle"):
            product_loop.record_evidence(self.workspace, evidence)
        evidence = self.evidence()
        evidence["scope_digest"] = "previous"
        with self.assertRaisesRegex(
            product_loop.ProductLoopError, "different proposal"
        ):
            product_loop.record_evidence(self.workspace, evidence)

    def test_passed_evidence_cannot_omit_planned_scenario(self) -> None:
        self.initialize()
        self.development()
        evidence = self.evidence()
        evidence["results"] = []
        evidence["evidence_refs"] = ["result.txt"]
        with self.assertRaisesRegex(
            product_loop.ProductLoopError, "every planned scenario"
        ):
            product_loop.record_evidence(self.workspace, evidence)

    def test_revision_invalidates_old_results_and_authorizations_with_history(
        self,
    ) -> None:
        self.initialize()
        self.development()
        product_loop.record_evidence(self.workspace, self.evidence())
        revised = selected_proposal("product_metric")
        revised["metric"] = {
            "name": "activation_rate",
            "baseline": None,
            "target": "40%",
        }
        state = product_loop.revise_state(
            self.workspace,
            revised,
            "User changed the agreed measurement",
            authorization_evidence="User approved the revised metric",
        )
        self.assertEqual(state["stage"], "experiment")
        self.assertEqual(state["validation"]["mode"], "product_metric")
        self.assertIsNone(state["validation"]["evidence"])
        self.assertFalse(product_loop.authorization_valid(state, "implementation"))
        self.assertEqual(
            state["history"][-1]["previous"]["validation"]["mode"], "local_scenario"
        )
        self.assertEqual(
            state["history"][-1]["previous"]["validation"]["evidence"]["status"],
            "passed",
        )

    def test_baseline_clarification_keeps_authorization_and_observations(self) -> None:
        self.initialize()
        self.development()
        state = product_loop.record_evidence(self.workspace, self.evidence())
        original_evidence = state["validation"]["evidence"]
        revised = selected_proposal()
        revised["metric"]["baseline"] = "4"
        revised["title"] = "A clearer setup experience"
        state = product_loop.revise_state(
            self.workspace,
            revised,
            "Measured previously unknown baseline",
            authorization_evidence="The selected plan included measuring this baseline",
        )
        self.assertEqual(state["stage"], "development")
        self.assertTrue(product_loop.authorization_valid(state, "implementation"))
        self.assertEqual(state["validation"]["evidence"], original_evidence)

    def test_next_round_clears_evidence_and_reuses_only_contract_authorization(
        self,
    ) -> None:
        self.initialize()
        self.development()
        product_loop.authorize_state(
            self.workspace,
            local=True,
            evidence="Local permission is limited to this cycle",
            scope="cycle",
        )
        product_loop.record_evidence(self.workspace, self.evidence("failed"))
        self.write_artifact("development")
        product_loop.advance_state(self.workspace)
        self.write_artifact("evaluation", "verdict: iterate\n")
        state = product_loop.advance_state(self.workspace, outcome="iterate")
        self.assertEqual(state["stage"], "research")
        self.assertIsNone(state["validation"]["evidence"])
        self.assertTrue(product_loop.authorization_valid(state, "implementation"))
        self.assertFalse(product_loop.authorization_valid(state, "local"))
        self.assertEqual(state["history"][-1]["previous_evidence"]["status"], "failed")

    def test_iteration_preserves_existing_cycle_artifacts_and_uses_fresh_templates(
        self,
    ) -> None:
        self.initialize()
        self.development()
        product_loop.record_evidence(self.workspace, self.evidence("blocked"))
        self.write_artifact("development")
        product_loop.advance_state(self.workspace)
        self.write_artifact("evaluation", "verdict: iterate\n")
        previous_directory = (
            product_loop.state_dir(self.workspace) / "cycles" / "selected-r2"
        )
        previous_directory.mkdir()
        previous_research = previous_directory / "01-research.md"
        previous_research.write_text("Previous cycle research", encoding="utf-8")
        state = product_loop.advance_state(self.workspace, outcome="iterate")
        self.assertNotEqual(state["cycle_id"], "selected-r2")
        self.assertEqual(
            previous_research.read_text(encoding="utf-8"), "Previous cycle research"
        )
        self.assertIn(
            product_loop.TEMPLATE_MARKER,
            product_loop.artifact_path(self.workspace, state, "research").read_text(
                encoding="utf-8"
            ),
        )

    def test_opportunity_counts_and_explicit_selection(self) -> None:
        for count in (2, 3, 7):
            self.assertEqual(
                len(
                    product_loop.score_payload(
                        {
                            "opportunities": [
                                opportunity(str(i), 3) for i in range(count)
                            ]
                        }
                    )["opportunities"]
                ),
                count,
            )
        single = {"opportunities": [opportunity("chosen", 3)]}
        with self.assertRaisesRegex(
            product_loop.ProductLoopError, "explicit selected_id"
        ):
            product_loop.score_payload(single)
        self.assertEqual(
            product_loop.score_payload(single, selected_id="chosen")["selected_id"],
            "chosen",
        )
        with self.assertRaisesRegex(
            product_loop.ProductLoopError, "existing opportunity"
        ):
            product_loop.score_payload(single, selected_id="different")

    def test_cli_init_proposal_and_score_selection(self) -> None:
        proposal_path = self.workspace / "proposal.json"
        proposal_path.write_text(json.dumps(selected_proposal()), encoding="utf-8")
        parser = product_loop.build_parser()
        args = parser.parse_args(
            [
                "init",
                "--workspace",
                str(self.workspace),
                "--proposal",
                str(proposal_path),
                "--authorize-implementation",
                "--authorization-evidence",
                "User chose the scope",
            ]
        )
        result = product_loop.run(args)
        self.assertEqual(result["state"]["objective"], "Finish setup")
        self.assertTrue(
            product_loop.authorization_valid(result["state"], "implementation")
        )
        self.assertFalse(product_loop.authorization_valid(result["state"], "local"))

    def test_local_data_and_recovery_scope_are_bound_and_unknown_fields_rejected(
        self,
    ) -> None:
        state = self.initialize()
        original_digest = product_loop.proposal_digest(state["proposal"])
        for key, value in [
            ("data_scope", ["User's actual saved preferences"]),
            ("side_effects", ["Modify a real saved preference"]),
            ("recovery", "Restore the user's backup"),
        ]:
            with self.subTest(key=key):
                changed = selected_proposal()
                changed["validation"][key] = value
                self.assertNotEqual(
                    product_loop.proposal_digest(
                        product_loop.normalize_proposal(changed)
                    ),
                    original_digest,
                )
        for key in ("data_scope", "side_effects", "recovery"):
            with self.subTest(missing=key):
                invalid = selected_proposal()
                del invalid["validation"][key]
                with self.assertRaises(product_loop.ProductLoopError):
                    product_loop.normalize_proposal(invalid)
        invalid = selected_proposal()
        invalid["validation"]["unrecognized_data_access"] = "all documents"
        with self.assertRaisesRegex(
            product_loop.ProductLoopError, "Unknown validation fields"
        ):
            product_loop.normalize_proposal(invalid)

    def test_revision_archives_prior_artifacts_and_invalidates_current_templates(
        self,
    ) -> None:
        self.initialize()
        self.development()
        state = product_loop.load_state(self.workspace)
        experiment_path = product_loop.artifact_path(
            self.workspace, state, "experiment"
        )
        old_experiment = experiment_path.read_text(encoding="utf-8")
        revised = selected_proposal()
        revised["metric"]["target"] = "1"
        state = product_loop.revise_state(
            self.workspace,
            revised,
            "User chose a stricter target",
            authorize_implementation=True,
            authorize_local=True,
            authorization_evidence="User approved the revised target and local test",
        )
        archived = (
            self.workspace
            / state["history"][-1]["previous"]["artifact_snapshots"]["experiment"]
        )
        self.assertEqual(archived.read_text(encoding="utf-8"), old_experiment)
        self.assertIn(
            product_loop.TEMPLATE_MARKER, experiment_path.read_text(encoding="utf-8")
        )
        with self.assertRaisesRegex(product_loop.ProductLoopError, "template markers"):
            product_loop.advance_state(self.workspace)

    def test_changed_selected_option_returns_to_differentiation(self) -> None:
        self.initialize()
        self.development()
        revised = selected_proposal()
        revised["id"] = "different-option"
        state = product_loop.revise_state(
            self.workspace,
            revised,
            "User selected another proposed feature",
            authorization_evidence="User chose the other option",
        )
        self.assertEqual(state["stage"], "differentiation")
        self.assertFalse(product_loop.validate_stage(self.workspace)["ok"])

    def test_revoked_implementation_can_record_blocker_and_stop(self) -> None:
        self.initialize()
        self.development()
        product_loop.authorize_state(
            self.workspace,
            revoke_implementation=True,
            revoke_local=True,
            evidence="User withdrew implementation and local execution permission",
        )
        state = product_loop.load_state(self.workspace)
        self.assertFalse(product_loop.authorization_valid(state, "implementation"))
        self.assertFalse(product_loop.authorization_valid(state, "local"))
        with self.assertRaises(product_loop.ProductLoopError):
            product_loop.record_evidence(self.workspace, self.evidence())
        product_loop.record_evidence(self.workspace, self.evidence("blocked"))
        self.write_artifact("development")
        product_loop.advance_state(self.workspace)
        self.write_artifact("evaluation", "verdict: stop\n")
        self.assertEqual(
            product_loop.advance_state(self.workspace, outcome="stop")["stage"],
            "stopped",
        )

    def test_new_cycle_requires_terminal_state_and_preserves_history(self) -> None:
        self.initialize()
        previous_bytes = product_loop.state_path(self.workspace).read_bytes()
        with self.assertRaisesRegex(
            product_loop.ProductLoopError, "complete or stopped"
        ):
            product_loop.initialize_workspace(
                self.workspace,
                proposal=selected_proposal(),
                authorization_evidence="User chose a next proposal",
                new_cycle=True,
            )
        self.assertEqual(
            product_loop.state_path(self.workspace).read_bytes(), previous_bytes
        )
        state = product_loop.load_state(self.workspace)
        state["stage"] = "complete"
        state["status"] = "complete"
        product_loop.save_state(self.workspace, state)
        old_log = (
            product_loop.state_dir(self.workspace) / "decision-log.jsonl"
        ).read_text(encoding="utf-8")
        next_proposal = selected_proposal()
        next_proposal["id"] = "new-feature"
        state = product_loop.initialize_workspace(
            self.workspace,
            proposal=next_proposal,
            cycle_id="next",
            authorization_evidence="User chose this next feature",
            new_cycle=True,
        )
        archived = self.workspace / state["history"][0]["previous_state"]
        self.assertEqual(product_loop.read_json(archived)["cycle_id"], "selected")
        self.assertEqual(state["selected_id"], "new-feature")
        self.assertFalse(product_loop.authorization_valid(state, "implementation"))
        self.assertFalse(product_loop.authorization_valid(state, "local"))
        self.assertTrue(
            (product_loop.state_dir(self.workspace) / "decision-log.jsonl")
            .read_text(encoding="utf-8")
            .startswith(old_log)
        )


class PublicTrialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = SelectedProposalTests()
        self.fixture.setUp()
        self.workspace = self.fixture.workspace

    def tearDown(self) -> None:
        self.fixture.tearDown()

    def snapshot(self) -> dict[str, bytes]:
        return {
            str(path.relative_to(self.workspace)): path.read_bytes()
            for path in product_loop.state_dir(self.workspace).rglob("*")
            if path.is_file()
        }

    def test_cli_cancels_rejected_approval_and_preserves_it_for_next_cycle(
        self,
    ) -> None:
        self.fixture.initialize(implementation=False, local=False)
        previous = self.fixture.approval()
        artifacts = {
            stage: product_loop.artifact_path(
                self.workspace, previous, stage
            ).read_bytes()
            for stage in product_loop.ARTIFACT_NAMES
        }
        command = [
            sys.executable,
            str(SCRIPT_PATH),
            "stop",
            "--workspace",
            str(self.workspace),
            "--rationale",
            "Do not implement this proposal",
            "--evidence",
            "The user rejected this iteration",
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        state = json.loads(result.stdout)["state"]
        self.assertEqual(state["stage"], "stopped")
        self.assertEqual(state["history"][-1]["from"], "approval")
        self.assertEqual(state.get("authorizations"), previous.get("authorizations"))
        stopped_snapshot = self.snapshot()
        subprocess.run(command, capture_output=True, check=True)
        self.assertEqual(self.snapshot(), stopped_snapshot)
        new = product_loop.initialize_workspace(
            self.workspace,
            proposal=selected_proposal(),
            new_cycle=True,
            cycle_id="next",
            authorization_evidence="The user selected a new iteration",
        )
        archived = product_loop.read_json(
            self.workspace / new["history"][0]["previous_state"]
        )
        self.assertEqual(archived, state)
        for stage, content in artifacts.items():
            self.assertEqual(
                product_loop.artifact_path(self.workspace, state, stage).read_bytes(),
                content,
            )

    def test_chinese_cli_round_trips_through_non_utf8_pipes(self) -> None:
        command = [sys.executable, str(SCRIPT_PATH)]
        environment = {**os.environ, "PYTHONIOENCODING": "ascii"}
        initialized = subprocess.run(
            [
                *command,
                "init",
                "--workspace",
                str(self.workspace),
                "--language",
                "zh-CN",
                "--objective",
                "中文目标",
                "--metric",
                "完成率",
            ],
            capture_output=True,
            check=True,
            env=environment,
        )
        state = json.loads(initialized.stdout.decode("ascii"))["state"]
        self.assertEqual(state["objective"], "中文目标")
        status = subprocess.run(
            [*command, "status", "--workspace", str(self.workspace)],
            capture_output=True,
            check=True,
            env=environment,
        )
        self.assertEqual(
            json.loads(status.stdout.decode("ascii"))["objective"], "中文目标"
        )
        stopped = subprocess.run(
            [
                *command,
                "stop",
                "--workspace",
                str(self.workspace),
                "--rationale",
                "取消当前方案",
                "--evidence",
                "用户拒绝",
            ],
            capture_output=True,
            check=True,
            env=environment,
        )
        final = json.loads(stopped.stdout.decode("ascii"))["state"]
        self.assertEqual(final["stage"], "stopped")
        self.assertEqual(final["history"][-1]["evidence"], "用户拒绝")
        self.assertIn(
            "中文目标",
            product_loop.state_path(self.workspace).read_text(encoding="utf-8"),
        )

    def test_stop_works_before_research_and_after_executed_development(self) -> None:
        self.fixture.initialize()
        state = product_loop.stop_state(self.workspace, "Cancel", "User cancelled")
        self.assertEqual(state["stage"], "stopped")
        product_loop.initialize_workspace(
            self.workspace,
            proposal=selected_proposal(),
            new_cycle=True,
            authorize_implementation=True,
            authorize_local=True,
            authorization_evidence="User selected another scope and its isolated tests",
            language="zh-CN",
        )
        self.fixture.development()
        before = product_loop.record_evidence(self.workspace, self.fixture.evidence())
        state = product_loop.stop_state(
            self.workspace, "Cancel after testing", "User cancelled"
        )
        self.assertEqual(
            state["validation"]["evidence"], before["validation"]["evidence"]
        )
        self.assertEqual(state["authorizations"], before["authorizations"])
        self.assertNotIn("completion", state)

    def test_stop_requires_a_real_decision_and_does_not_change_completed_result(
        self,
    ) -> None:
        self.fixture.initialize(language="en")
        before = self.snapshot()
        for rationale, evidence in [("", "User cancelled"), ("Cancel", " ")]:
            with self.assertRaises(product_loop.ProductLoopError):
                product_loop.stop_state(self.workspace, rationale, evidence)
        self.assertEqual(self.snapshot(), before)
        self.fixture.development()
        product_loop.record_evidence(self.workspace, self.fixture.evidence())
        self.fixture.write_artifact("development")
        product_loop.advance_state(self.workspace)
        self.fixture.write_artifact(
            "evaluation",
            "verdict: complete\n" + product_loop.LOCAL_COMPLETION_LIMITS["en"],
        )
        product_loop.advance_state(self.workspace, outcome="complete")
        completed = self.snapshot()
        self.assertEqual(
            product_loop.stop_state(self.workspace, "Cancel", "User requested stop")[
                "stage"
            ],
            "complete",
        )
        self.assertEqual(self.snapshot(), completed)

    def test_outcome_outside_evaluation_never_advances_or_grants_authorization(
        self,
    ) -> None:
        self.fixture.initialize()
        for stage in ("research", "approval", "development"):
            if stage == "approval":
                self.fixture.approval()
            elif stage == "development":
                product_loop.advance_state(self.workspace)
            before = self.snapshot()
            for outcome in ("complete", "iterate", "stop"):
                with self.subTest(stage=stage, outcome=outcome):
                    with self.assertRaisesRegex(
                        product_loop.ProductLoopError, "only valid during evaluation"
                    ):
                        product_loop.advance_state(
                            self.workspace, outcome=outcome, approve=True
                        )
                    self.assertEqual(self.snapshot(), before)

    def test_english_default_and_chinese_legacy_state_keep_authorization_identity(
        self,
    ) -> None:
        state = product_loop.initialize_workspace(
            self.workspace,
            proposal=selected_proposal(),
            authorization_evidence="User selected this scope",
            authorize_implementation=True,
        )
        self.assertEqual(state["language"], "en")
        self.assertIn(
            "# Product research",
            product_loop.artifact_path(self.workspace, state, "research").read_text(
                encoding="utf-8"
            ),
        )
        original_digest = product_loop.execution_digest(state)
        del state["language"]
        product_loop.save_state(self.workspace, state)
        legacy = product_loop.status_payload(self.workspace)
        self.assertEqual(legacy["language"], "zh-CN")
        self.assertEqual(legacy["scope_digest"], original_digest)
        self.assertTrue(product_loop.authorization_valid(state, "implementation"))

    def test_english_cycle_retains_evidence_and_revision_gates(self) -> None:
        self.fixture.initialize(language="en")
        self.fixture.development()
        self.fixture.write_artifact("development")
        self.assertFalse(product_loop.validate_stage(self.workspace)["ok"])
        payload = self.fixture.evidence()
        payload["scope_digest"] = "stale-contract"
        with self.assertRaisesRegex(
            product_loop.ProductLoopError, "different proposal scope"
        ):
            product_loop.record_evidence(self.workspace, payload)
        product_loop.record_evidence(self.workspace, self.fixture.evidence())
        product_loop.advance_state(self.workspace)
        limit = product_loop.LOCAL_COMPLETION_LIMITS["en"]
        for omitted in ("", f"<!-- {limit} -->", product_loop.LOCAL_COMPLETION_LIMIT):
            self.fixture.write_artifact("evaluation", "verdict: complete\n" + omitted)
            with self.assertRaisesRegex(
                product_loop.ProductLoopError, "Local completion must state"
            ):
                product_loop.advance_state(self.workspace, outcome="complete")
        self.fixture.write_artifact("evaluation", "verdict: complete\n" + limit)
        self.assertTrue(product_loop.validate_stage(self.workspace)["ok"])
        revised = selected_proposal()
        revised["metric"]["target"] = "1"
        state = product_loop.revise_state(
            self.workspace,
            revised,
            "User chose a stricter target",
            authorization_evidence="User selected the stricter target; no new implementation grant",
        )
        self.assertEqual(state["language"], "en")
        self.assertEqual(state["stage"], "experiment")
        self.assertFalse(product_loop.authorization_valid(state, "implementation"))
        self.assertIsNone(state["validation"]["evidence"])
        self.assertIn(
            "# Product experiment",
            product_loop.artifact_path(self.workspace, state, "experiment").read_text(
                encoding="utf-8"
            ),
        )

    def test_english_iteration_preserves_language_and_clears_results(self) -> None:
        self.fixture.initialize(language="en")
        self.fixture.development()
        product_loop.record_evidence(self.workspace, self.fixture.evidence("failed"))
        self.fixture.write_artifact("development")
        product_loop.advance_state(self.workspace)
        self.fixture.write_artifact("evaluation", "verdict: iterate\n")
        state = product_loop.advance_state(self.workspace, outcome="iterate")
        self.assertEqual(state["language"], "en")
        self.assertIsNone(state["validation"]["evidence"])
        self.assertIn(
            "# Product research",
            product_loop.artifact_path(self.workspace, state, "research").read_text(
                encoding="utf-8"
            ),
        )

    def test_cli_language_choice_and_invalid_language_have_no_partial_state(
        self,
    ) -> None:
        command = [
            sys.executable,
            str(SCRIPT_PATH),
            "init",
            "--workspace",
            str(self.workspace),
            "--objective",
            "Trial",
            "--metric",
            "success",
        ]
        invalid = subprocess.run(
            [*command, "--language", "fr"], capture_output=True, check=False
        )
        self.assertEqual(invalid.returncode, 2)
        self.assertFalse(product_loop.state_path(self.workspace).exists())
        result = subprocess.run(
            [*command, "--language", "zh-CN"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(json.loads(result.stdout)["state"]["language"], "zh-CN")

    def test_existing_evidence_paths_support_spaces_lines_and_fragments(self) -> None:
        path = self.workspace / "test evidence.log"
        path.write_text("Observed result", encoding="utf-8")
        for reference in (
            str(path),
            str(path) + ":1",
            str(path) + ":1:2",
            "test evidence.log#result",
            "test evidence.log:1:2",
        ):
            with self.subTest(reference=reference):
                self.assertTrue(
                    product_loop.reference_resolves(
                        reference, self.workspace, self.workspace
                    )
                )
        self.assertFalse(
            product_loop.reference_resolves(
                str(path) + ".missing", self.workspace, self.workspace
            )
        )
        for reference in (
            "mailto:tester@example.com",
            "file:///tmp/evidence.log",
            "https://",
        ):
            self.assertFalse(
                product_loop.reference_resolves(
                    reference, self.workspace, self.workspace
                )
            )
        self.assertTrue(
            product_loop.reference_resolves(
                "https://example.com/results", self.workspace, self.workspace
            )
        )

    def test_windows_drive_and_unc_reach_file_validation(self) -> None:
        # Pure path parsing runs everywhere; the existing-file test above uses
        # real native drive paths when this suite runs on Windows CI.
        references = [
            r"C:\Users\tester\test evidence.log",
            "C:/Users/tester/test evidence.log",
            r"\\server\share\test evidence.log",
        ]
        for reference in references:
            for suffix in ("", ":12", ":12:4", "#result"):
                with self.subTest(reference=reference, suffix=suffix):
                    for exists in (True, False):
                        with patch.object(
                            Path, "is_file", return_value=exists
                        ) as is_file:
                            self.assertEqual(
                                product_loop.reference_resolves(
                                    reference + suffix, self.workspace, self.workspace
                                ),
                                exists,
                            )
                            is_file.assert_called_once_with()
        if os.name == "nt":
            self.assertTrue(
                product_loop.reference_resolves(
                    str(self.workspace / "README.md"), self.workspace, self.workspace
                )
            )


if __name__ == "__main__":
    unittest.main()
