from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from test_product_loop import (
    SCRIPT_PATH,
    filled_markdown,
    isolated_workspace,
    product_loop,
    selected_proposal,
)


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = isolated_workspace(self)
        self.iter_home = Path(os.environ["ITER_HOME"])
        self.root = self.workspace.parent

    def initialize(self, workspace: Path | None = None) -> dict:
        return product_loop.initialize_workspace(
            workspace or self.workspace,
            cycle_id="selected",
            proposal=selected_proposal(),
            authorize_implementation=True,
            authorize_local=True,
            authorization_evidence="User approved this scope and isolated tests",
        )

    def snapshot(self, directory: Path) -> dict[str, bytes]:
        return {
            str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob("*")
            if path.is_file() and not path.is_symlink()
        }

    def legacy_fixture(self) -> tuple[dict, dict[str, bytes]]:
        legacy = self.workspace / ".product-loop"
        cycle = "legacy"
        proposal = product_loop.normalize_proposal(selected_proposal())
        # Scope text is historical authorization, even when it names the old path.
        proposal["validation"]["data_scope"] = [
            "Only fixtures under .product-loop/fixtures in this workspace"
        ]
        state = {
            "schema_version": 1,
            "cycle_id": cycle,
            "stage": "research",
            "status": "active",
            "objective": proposal["objective"],
            "metric": copy.deepcopy(proposal["metric"]),
            "round": 1,
            "max_rounds": 3,
            "approval": {"status": "pending", "actor": None, "at": None},
            "artifacts": {
                stage: f".product-loop/cycles/{cycle}/{filename}"
                for stage, filename in product_loop.ARTIFACT_NAMES.items()
            },
            "history": [{"at": "2026-09-05T00:00:00+00:00", "event": "initialized"}],
            "created_at": "2026-09-05T00:00:00+00:00",
            "updated_at": "2026-09-05T00:00:00+00:00",
            "proposal": proposal,
            "selected_id": proposal["id"],
            "validation": {**copy.deepcopy(proposal["validation"]), "evidence": None},
        }
        product_loop.grant_authorizations(
            state, True, True, "owner", "User approved the original saved contract"
        )
        for stage, relative in state["artifacts"].items():
            destination = self.workspace / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if stage == "research":
                content = filled_markdown(
                    product_loop.required_headings("zh-CN")[stage],
                    "direct_user_feedback: absent\n"
                    "- [repository] [Observed](.product-loop/evidence/result.log)\n",
                )
            elif stage == "differentiation":
                content = '{"historical": "unchanged"}\n'
            else:
                content = f"Historical {stage}: .product-loop/fixtures stays literal.\n"
            destination.write_text(content, encoding="utf-8")
        (legacy / "evidence").mkdir()
        (legacy / "evidence/result.log").write_text(
            "Observed result\n", encoding="utf-8"
        )
        (legacy / "charter.md").write_text("Original charter\n", encoding="utf-8")
        (legacy / "decision-log.jsonl").write_text(
            '{"event":"initialized","evidence":"Original decision"}\n',
            encoding="utf-8",
        )
        revision = legacy / f"cycles/{cycle}/revisions/revision-001/03-experiment.md"
        revision.parent.mkdir(parents=True)
        revision.write_text(
            "Original revision .product-loop/fixtures\n", encoding="utf-8"
        )
        state["history"].append(
            {
                "event": "proposal_revised",
                "previous": {
                    "proposal": copy.deepcopy(proposal),
                    "artifact_snapshots": {
                        "experiment": str(revision.relative_to(self.workspace))
                    },
                },
            }
        )
        (legacy / "state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return state, self.snapshot(legacy)

    def test_absent_paths_and_status_are_read_only(self) -> None:
        before = self.snapshot(self.root)
        paths = product_loop.paths_payload(self.workspace)
        self.assertFalse(paths["exists"])
        self.assertFalse(paths["legacy_exists"])
        self.assertFalse(paths["migration_required"])
        self.assertEqual(Path(paths["iter_home"]), self.iter_home)
        self.assertEqual(
            Path(paths["storage_root"]), product_loop.state_dir(self.workspace)
        )
        self.assertEqual(
            Path(paths["state_path"]), product_loop.state_path(self.workspace)
        )
        for name in ("inputs_dir", "evidence_dir"):
            Path(paths[name]).relative_to(product_loop.state_dir(self.workspace))
        status = product_loop.status_payload(self.workspace)
        self.assertTrue(status["ok"])
        self.assertFalse(status["exists"])
        self.assertEqual(self.snapshot(self.root), before)
        self.assertFalse(self.iter_home.exists())

    def test_cli_paths_and_absent_status_do_not_create_state(self) -> None:
        for command in ("paths", "status"):
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    command,
                    "--workspace",
                    str(self.workspace),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            self.assertFalse(payload["exists"])
        self.assertFalse(self.iter_home.exists())
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_new_cycle_storage_is_external_and_uses_real_workspace_identity(
        self,
    ) -> None:
        state = self.initialize()
        self.assertEqual(state["schema_version"], 2)
        expected_key = hashlib.sha256(
            os.path.normcase(str(self.workspace.resolve())).encode("utf-8")
        ).hexdigest()
        self.assertEqual(
            product_loop.state_dir(self.workspace),
            self.iter_home / "workspaces" / expected_key,
        )
        self.assertEqual(list(self.workspace.iterdir()), [])
        for stage, relative in state["artifacts"].items():
            self.assertFalse(Path(relative).is_absolute())
            self.assertFalse(relative.startswith(".product-loop/"))
            artifact = product_loop.artifact_path(self.workspace, state, stage)
            artifact.relative_to(product_loop.state_dir(self.workspace))
            self.assertTrue(artifact.is_file())
        self.assertTrue(product_loop.status_payload(self.workspace)["exists"])

    def test_same_named_clones_do_not_share_grants_or_active_state(self) -> None:
        self.initialize()
        other = self.root / "second-checkout" / self.workspace.name
        other.mkdir(parents=True)
        self.assertNotEqual(
            product_loop.state_dir(other), product_loop.state_dir(self.workspace)
        )
        self.assertFalse(product_loop.status_payload(other)["exists"])
        product_loop.initialize_workspace(
            other, objective="Other project", metric="success"
        )
        self.assertEqual(
            product_loop.load_state(self.workspace)["objective"], "Finish setup"
        )
        self.assertEqual(product_loop.load_state(other).get("authorizations", {}), {})

    def test_workspace_symlink_alias_reuses_the_same_storage(self) -> None:
        alias = self.root / "project-alias"
        try:
            alias.symlink_to(self.workspace, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Directory symlinks unavailable: {exc}")
        self.initialize()
        self.assertEqual(
            product_loop.state_dir(alias), product_loop.state_dir(self.workspace)
        )
        self.assertEqual(
            product_loop.load_state(alias), product_loop.load_state(self.workspace)
        )

    def test_replacing_workspace_at_the_same_path_does_not_reuse_its_grants(
        self,
    ) -> None:
        self.initialize()
        before = self.snapshot(self.iter_home)
        self.workspace.rename(self.root / "original-project")
        self.workspace.mkdir()
        with self.assertRaises(product_loop.ProductLoopError):
            product_loop.status_payload(self.workspace)
        with self.assertRaises(product_loop.ProductLoopError):
            self.initialize()
        self.assertEqual(self.snapshot(self.iter_home), before)

    def test_relative_or_workspace_internal_iter_home_is_rejected_without_writes(
        self,
    ) -> None:
        for home in (
            "relative-iter",
            str(self.workspace),
            str(self.workspace / ".iter"),
        ):
            with self.subTest(home=home), patch.dict(os.environ, {"ITER_HOME": home}):
                with self.assertRaises(product_loop.ProductLoopError):
                    self.initialize()
        self.assertEqual(list(self.workspace.iterdir()), [])
        self.assertFalse(self.iter_home.exists())

    def test_external_iter_home_is_rejected_when_computed_storage_is_inside_workspace(
        self,
    ) -> None:
        workspace = self.iter_home / "workspaces"
        workspace.mkdir(parents=True)
        with self.assertRaises(product_loop.ProductLoopError):
            self.initialize(workspace)
        self.assertEqual(list(workspace.iterdir()), [])

    def test_artifact_paths_cannot_escape_external_storage(self) -> None:
        state = self.initialize()
        outside = self.root / "private.md"
        outside.write_text("Private unrelated file", encoding="utf-8")
        for path in ("../private.md", str(outside)):
            with self.subTest(path=path):
                altered = copy.deepcopy(state)
                altered["artifacts"]["research"] = path
                with self.assertRaises(product_loop.ProductLoopError):
                    product_loop.artifact_path(self.workspace, altered, "research")
        link = product_loop.state_dir(self.workspace) / "outside"
        try:
            link.symlink_to(self.root, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Directory symlinks unavailable: {exc}")
        state["artifacts"]["research"] = "outside/private.md"
        with self.assertRaises(product_loop.ProductLoopError):
            product_loop.artifact_path(self.workspace, state, "research")
        self.assertEqual(outside.read_text(encoding="utf-8"), "Private unrelated file")

    def test_revision_archive_rejects_symlinked_container_and_numbered_directory(
        self,
    ) -> None:
        state = self.initialize()
        storage = product_loop.state_dir(self.workspace)
        cycle = product_loop.artifact_path(self.workspace, state, "research").parent
        revisions = cycle / "revisions"
        outside = self.root / "unrelated-archive"
        outside.mkdir()
        before = self.snapshot(storage)
        for link in (revisions, revisions / "revision-001"):
            with self.subTest(path=link.name):
                link.parent.mkdir(parents=True, exist_ok=True)
                try:
                    link.symlink_to(outside, target_is_directory=True)
                except OSError as exc:
                    self.skipTest(f"Directory symlinks unavailable: {exc}")
                try:
                    with self.assertRaises(product_loop.ProductLoopError):
                        product_loop.archive_revision_artifacts(self.workspace, state)
                    self.assertEqual(list(outside.iterdir()), [])
                    self.assertEqual(self.snapshot(storage), before)
                finally:
                    link.unlink()

    def test_explicit_evidence_roots_resolve_and_ambiguous_bare_paths_are_rejected(
        self,
    ) -> None:
        state = self.initialize()
        storage = product_loop.state_dir(self.workspace)
        directory = product_loop.artifact_path(self.workspace, state, "research").parent
        (self.workspace / "result.log").write_text(
            "Workspace evidence", encoding="utf-8"
        )
        (storage / "result.log").write_text("Stored evidence", encoding="utf-8")
        (directory / "result.log").write_text("Report evidence", encoding="utf-8")
        (self.workspace.parent / "outside.log").write_text(
            "Outside workspace", encoding="utf-8"
        )
        (storage.parent / "outside.log").write_text("Outside storage", encoding="utf-8")
        for reference in (
            "workspace:result.log",
            "storage:result.log",
            "storage:result.log:1:2",
        ):
            with self.subTest(reference=reference):
                self.assertTrue(
                    product_loop.reference_resolves(
                        reference, self.workspace, directory
                    )
                )
        self.assertFalse(
            product_loop.reference_resolves("result.log", self.workspace, directory)
        )
        self.assertFalse(
            product_loop.reference_resolves(
                "storage:../outside.log", self.workspace, directory
            )
        )
        self.assertFalse(
            product_loop.reference_resolves(
                "workspace:../outside.log", self.workspace, directory
            )
        )

    def test_legacy_queries_preserve_files_and_require_explicit_migration_for_writes(
        self,
    ) -> None:
        _, before = self.legacy_fixture()
        paths = product_loop.paths_payload(self.workspace)
        self.assertTrue(paths["legacy_exists"])
        self.assertTrue(paths["migration_required"])
        status = product_loop.status_payload(self.workspace)
        self.assertTrue(status["migration_required"])
        for action in (
            lambda: self.initialize(),
            lambda: product_loop.stop_state(self.workspace, "Cancel", "User cancelled"),
            lambda: product_loop.authorize_state(
                self.workspace, local=True, evidence="User approved local execution"
            ),
        ):
            with self.assertRaisesRegex(product_loop.ProductLoopError, "migrat"):
                action()
        self.assertEqual(self.snapshot(self.workspace / ".product-loop"), before)
        self.assertFalse(self.iter_home.exists())

    def test_migration_preserves_contract_grants_and_original_bytes(self) -> None:
        original, before = self.legacy_fixture()
        product_loop.migrate_workspace(self.workspace)
        migrated = product_loop.load_state(self.workspace)
        storage = product_loop.state_dir(self.workspace)
        self.assertEqual(migrated["schema_version"], 2)
        self.assertEqual(product_loop.report_language(migrated), "zh-CN")
        for field in (
            "proposal",
            "authorizations",
            "metric",
            "cycle_id",
            "stage",
            "approval",
        ):
            self.assertEqual(migrated[field], original[field], field)
        self.assertEqual(
            product_loop.execution_digest(migrated),
            product_loop.execution_digest(original),
        )
        self.assertTrue(product_loop.authorization_valid(migrated, "implementation"))
        self.assertTrue(product_loop.authorization_valid(migrated, "local"))
        self.assertEqual(self.snapshot(storage / "legacy-backup"), before)
        for path, content in before.items():
            if path != "state.json":
                self.assertEqual((storage / path).read_bytes(), content, path)
        snapshot = migrated["history"][-1]["previous"]["artifact_snapshots"][
            "experiment"
        ]
        self.assertEqual(migrated["history"], original["history"])
        self.assertTrue(
            product_loop.reference_resolves(snapshot, self.workspace, storage)
        )
        self.assertFalse((self.workspace / ".product-loop").exists())
        self.assertFalse(
            product_loop.paths_payload(self.workspace)["migration_required"]
        )
        after = self.snapshot(storage)
        self.assertFalse(product_loop.migrate_workspace(self.workspace)["migrated"])
        self.assertEqual(self.snapshot(storage), after)

    def test_migration_keeps_legacy_relative_absolute_and_report_evidence_resolvable(
        self,
    ) -> None:
        self.legacy_fixture()
        old_absolute = str(self.workspace / ".product-loop/evidence/result.log")
        product_loop.migrate_workspace(self.workspace)
        state = product_loop.load_state(self.workspace)
        artifact_directory = product_loop.artifact_path(
            self.workspace, state, "research"
        ).parent
        for reference in (
            ".product-loop/evidence/result.log",
            ".product-loop/evidence/result.log:1:2",
            old_absolute,
            old_absolute + "#result",
            "../../evidence/result.log",
        ):
            with self.subTest(reference=reference):
                self.assertTrue(
                    product_loop.reference_resolves(
                        reference, self.workspace, artifact_directory
                    )
                )
        self.assertTrue(product_loop.validate_stage(self.workspace)["ok"])
        self.assertFalse(
            product_loop.reference_resolves(
                ".product-loop/evidence/missing.log", self.workspace, artifact_directory
            )
        )

    def test_migration_refuses_two_existing_states_without_overwriting_either(
        self,
    ) -> None:
        self.initialize()
        self.legacy_fixture()
        before = self.snapshot(self.root)
        with self.assertRaises(product_loop.ProductLoopError):
            product_loop.migrate_workspace(self.workspace)
        self.assertEqual(self.snapshot(self.root), before)

    def test_migrated_execution_evidence_can_complete_without_new_authorization(
        self,
    ) -> None:
        original, _ = self.legacy_fixture()
        original["stage"] = "evaluation"
        evidence = {
            "cycle_id": original["cycle_id"],
            "scope_digest": product_loop.execution_digest(original),
            "status": "passed",
            "summary": "Observed the agreed two setup steps before migration",
            "metric": {"observed": "2", "target_met": True},
            "acceptance_passed": True,
            "guardrails_passed": True,
            "unresolved_risks": [],
            "results": [
                {
                    "scenario_id": "setup",
                    "status": "passed",
                    "observed": "Two setup steps",
                    "evidence_refs": [".product-loop/evidence/result.log"],
                }
            ],
        }
        original["validation"]["evidence"] = evidence
        (self.workspace / ".product-loop/state.json").write_text(
            json.dumps(original, ensure_ascii=False), encoding="utf-8"
        )
        report = self.workspace / original["artifacts"]["evaluation"]
        report.write_text(
            filled_markdown(
                product_loop.required_headings("zh-CN")["evaluation"],
                "verdict: complete\n" + product_loop.LOCAL_COMPLETION_LIMITS["zh-CN"],
            ),
            encoding="utf-8",
        )
        report_bytes = report.read_bytes()
        product_loop.migrate_workspace(self.workspace)
        migrated = product_loop.load_state(self.workspace)
        self.assertEqual(migrated["validation"]["evidence"], evidence)
        self.assertEqual(migrated["authorizations"], original["authorizations"])
        self.assertEqual(
            product_loop.artifact_path(
                self.workspace, migrated, "evaluation"
            ).read_bytes(),
            report_bytes,
        )
        completed = product_loop.advance_state(self.workspace, outcome="complete")
        self.assertEqual(completed["stage"], "complete")
        self.assertEqual(completed["authorizations"], original["authorizations"])

    def test_migration_rejects_invalid_json_and_retains_source(self) -> None:
        self.legacy_fixture()
        state_path = self.workspace / ".product-loop/state.json"
        state_path.write_text("{unfinished", encoding="utf-8")
        before = self.snapshot(self.workspace)
        with self.assertRaises(product_loop.ProductLoopError):
            product_loop.migrate_workspace(self.workspace)
        self.assertEqual(self.snapshot(self.workspace), before)
        self.assertFalse(product_loop.state_path(self.workspace).exists())

    def test_migration_rejects_outside_artifacts_and_symlinked_evidence(self) -> None:
        self.legacy_fixture()
        legacy = self.workspace / ".product-loop"
        outside = self.root / "private.txt"
        outside.write_text("Do not migrate", encoding="utf-8")
        state_path = legacy / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["artifacts"]["research"] = str(outside)
        state_path.write_text(json.dumps(state), encoding="utf-8")
        before = self.snapshot(self.workspace)
        with self.assertRaises(product_loop.ProductLoopError):
            product_loop.migrate_workspace(self.workspace)
        self.assertEqual(self.snapshot(self.workspace), before)
        state["artifacts"]["research"] = ".product-loop/cycles/legacy/01-research.md"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        try:
            (legacy / "evidence/external.log").symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"File symlinks unavailable: {exc}")
        with self.assertRaises(product_loop.ProductLoopError):
            product_loop.migrate_workspace(self.workspace)
        self.assertTrue(state_path.is_file())
        self.assertFalse(product_loop.state_path(self.workspace).exists())
        self.assertEqual(outside.read_text(encoding="utf-8"), "Do not migrate")

    def interrupt_migration_before_cleanup(self) -> dict[str, bytes]:
        _, before = self.legacy_fixture()
        with patch.object(
            product_loop,
            "_finish_legacy_cleanup",
            side_effect=OSError("Cleanup interrupted"),
        ):
            with self.assertRaises(OSError):
                product_loop.migrate_workspace(self.workspace)
        self.assertEqual(self.snapshot(self.workspace / ".product-loop"), before)
        self.assertTrue(product_loop.state_path(self.workspace).is_file())
        return before

    def test_migration_resumes_after_receipt_is_created_before_copying(self) -> None:
        _, before = self.legacy_fixture()
        with patch.object(
            product_loop, "_prepare_migration", side_effect=OSError("Copy interrupted")
        ):
            with self.assertRaises(OSError):
                product_loop.migrate_workspace(self.workspace)
        self.assertEqual(self.snapshot(self.workspace / ".product-loop"), before)
        self.assertFalse(product_loop.state_path(self.workspace).exists())
        self.assertTrue(
            product_loop.paths_payload(self.workspace)["migration_required"]
        )
        self.assertTrue(product_loop.migrate_workspace(self.workspace)["migrated"])
        self.assertEqual(
            self.snapshot(product_loop.state_dir(self.workspace) / "legacy-backup"),
            before,
        )
        self.assertFalse((self.workspace / ".product-loop").exists())

    def test_migration_resumes_partially_published_files_with_state_committed_last(
        self,
    ) -> None:
        _, before = self.legacy_fixture()
        storage = product_loop.state_dir(self.workspace)
        rename = Path.rename
        published = []

        def interrupt_second_entry(source: Path, destination: Path) -> Path:
            if source.parent == storage / ".migration-staging":
                if published:
                    raise OSError("Publication interrupted")
                published.append(source.name)
            return rename(source, destination)

        with patch.object(
            Path, "rename", autospec=True, side_effect=interrupt_second_entry
        ):
            with self.assertRaises(OSError):
                product_loop.migrate_workspace(self.workspace)
        self.assertEqual(len(published), 1)
        self.assertNotIn("state.json", published)
        self.assertFalse(product_loop.state_path(self.workspace).exists())
        self.assertEqual(self.snapshot(self.workspace / ".product-loop"), before)
        self.assertTrue(product_loop.migrate_workspace(self.workspace)["migrated"])
        self.assertEqual(self.snapshot(storage / "legacy-backup"), before)
        self.assertFalse((storage / ".migration-staging").exists())
        self.assertFalse((self.workspace / ".product-loop").exists())

    def test_migration_retries_cleanup_after_publishing_without_changing_saved_state(
        self,
    ) -> None:
        before = self.interrupt_migration_before_cleanup()
        saved_state = product_loop.state_path(self.workspace).read_bytes()
        self.assertTrue(
            product_loop.paths_payload(self.workspace)["migration_required"]
        )
        result = product_loop.migrate_workspace(self.workspace)
        self.assertTrue(result["migrated"])
        self.assertEqual(
            product_loop.state_path(self.workspace).read_bytes(), saved_state
        )
        self.assertEqual(
            self.snapshot(product_loop.state_dir(self.workspace) / "legacy-backup"),
            before,
        )
        self.assertFalse((self.workspace / ".product-loop").exists())
        self.assertFalse(
            product_loop.paths_payload(self.workspace)["migration_required"]
        )

    def test_migration_retry_refuses_changed_legacy_source_and_preserves_both_copies(
        self,
    ) -> None:
        self.interrupt_migration_before_cleanup()
        (self.workspace / ".product-loop/evidence/result.log").write_text(
            "A new observation after interrupted migration", encoding="utf-8"
        )
        before = self.snapshot(self.root)
        with self.assertRaises(product_loop.ProductLoopError):
            product_loop.migrate_workspace(self.workspace)
        self.assertEqual(self.snapshot(self.root), before)
        self.assertTrue((self.workspace / ".product-loop/state.json").is_file())
        self.assertTrue(product_loop.state_path(self.workspace).is_file())

    def test_migration_retry_refuses_changed_published_report_before_removing_source(
        self,
    ) -> None:
        self.interrupt_migration_before_cleanup()
        report = (
            product_loop.state_dir(self.workspace) / "cycles/legacy/03-experiment.md"
        )
        report.write_text("Unexpected change to published report", encoding="utf-8")
        before = self.snapshot(self.root)
        with self.assertRaises(product_loop.ProductLoopError):
            product_loop.migrate_workspace(self.workspace)
        self.assertEqual(self.snapshot(self.root), before)
        self.assertTrue((self.workspace / ".product-loop/state.json").is_file())
        self.assertTrue(product_loop.state_path(self.workspace).is_file())

    def test_relocation_requires_explicit_action_and_preserves_grants_and_reports(
        self,
    ) -> None:
        original = self.initialize()
        old_storage = product_loop.state_dir(self.workspace)
        before = self.snapshot(old_storage)
        previous_workspace = self.workspace
        relocated = self.root / "moved-project"
        shutil.move(str(previous_workspace), relocated)
        self.assertFalse(product_loop.status_payload(relocated)["exists"])
        product_loop.relocate_workspace(relocated, previous_workspace)
        state = product_loop.load_state(relocated)
        for field in (
            "proposal",
            "authorizations",
            "metric",
            "cycle_id",
            "stage",
            "approval",
        ):
            self.assertEqual(state[field], original[field], field)
        self.assertEqual(
            product_loop.execution_digest(state),
            product_loop.execution_digest(original),
        )
        for path, content in before.items():
            if path.endswith(".md") or path == "decision-log.jsonl":
                self.assertEqual(
                    (product_loop.state_dir(relocated) / path).read_bytes(), content
                )
        self.assertFalse(old_storage.exists())
        self.assertEqual(list(relocated.iterdir()), [])

    def test_relocation_refuses_destination_conflicts_without_changes(self) -> None:
        self.initialize()
        other = self.root / "other-project"
        other.mkdir()
        self.initialize(other)
        self.workspace.rename(self.root / "moved-original")
        before = self.snapshot(self.root)
        with self.assertRaises(product_loop.ProductLoopError):
            product_loop.relocate_workspace(other, self.workspace)
        self.assertEqual(self.snapshot(self.root), before)

    def test_relocation_retains_absolute_workspace_and_storage_evidence_references(
        self,
    ) -> None:
        self.initialize()
        workspace_evidence = self.workspace / "observed.log"
        workspace_evidence.write_text("Product observation", encoding="utf-8")
        storage_evidence = product_loop.state_dir(self.workspace) / "observation.log"
        storage_evidence.write_text("Stored observation", encoding="utf-8")
        previous_workspace = self.workspace
        relocated = self.root / "moved-project"
        previous_workspace.rename(relocated)
        product_loop.relocate_workspace(relocated, previous_workspace)
        state = product_loop.load_state(relocated)
        directory = product_loop.artifact_path(relocated, state, "research").parent
        for reference in (str(workspace_evidence), str(storage_evidence)):
            with self.subTest(reference=reference):
                self.assertTrue(
                    product_loop.reference_resolves(reference, relocated, directory)
                )

    def test_relocation_resumes_after_directory_move_before_metadata_update(
        self,
    ) -> None:
        original = self.initialize()
        source_storage = product_loop.state_dir(self.workspace)
        before = self.snapshot(source_storage)
        previous_workspace = self.workspace
        relocated = self.root / "moved-project"
        previous_workspace.rename(relocated)
        destination_storage = product_loop.state_dir(relocated)
        with patch.object(
            product_loop,
            "_finish_relocation",
            side_effect=OSError("Metadata update interrupted"),
        ):
            with self.assertRaises(OSError):
                product_loop.relocate_workspace(relocated, previous_workspace)
        self.assertFalse(source_storage.exists())
        self.assertEqual(
            (destination_storage / "state.json").read_bytes(), before["state.json"]
        )
        self.assertTrue(
            product_loop.relocate_workspace(relocated, previous_workspace)["relocated"]
        )
        for path, content in before.items():
            if path != "workspace.json":
                self.assertEqual(
                    (destination_storage / path).read_bytes(), content, path
                )
        self.assertEqual(
            product_loop.load_state(relocated)["authorizations"],
            original["authorizations"],
        )
        after = self.snapshot(destination_storage)
        self.assertFalse(
            product_loop.relocate_workspace(relocated, previous_workspace)["relocated"]
        )
        self.assertEqual(self.snapshot(destination_storage), after)

    def test_relocation_resumes_after_metadata_update_before_completion_receipt(
        self,
    ) -> None:
        original = self.initialize()
        before = self.snapshot(product_loop.state_dir(self.workspace))
        previous_workspace = self.workspace
        relocated = self.root / "moved-project"
        previous_workspace.rename(relocated)
        destination_storage = product_loop.state_dir(relocated)
        write_json = product_loop.atomic_write_json

        def interrupt_completion(path: Path, payload: dict) -> None:
            if path == destination_storage / "relocation.json" and payload.get(
                "complete"
            ):
                raise OSError("Completion receipt interrupted")
            write_json(path, payload)

        with patch.object(
            product_loop, "atomic_write_json", side_effect=interrupt_completion
        ):
            with self.assertRaises(OSError):
                product_loop.relocate_workspace(relocated, previous_workspace)
        metadata = json.loads(
            (destination_storage / "workspace.json").read_text(encoding="utf-8")
        )
        receipt = json.loads(
            (destination_storage / "relocation.json").read_text(encoding="utf-8")
        )
        self.assertEqual(metadata["workspace"], str(relocated))
        self.assertFalse(receipt["complete"])
        self.assertTrue(
            product_loop.relocate_workspace(relocated, previous_workspace)["relocated"]
        )
        for path, content in before.items():
            if path != "workspace.json":
                self.assertEqual(
                    (destination_storage / path).read_bytes(), content, path
                )
        self.assertEqual(
            product_loop.load_state(relocated)["authorizations"],
            original["authorizations"],
        )

    def test_workspace_prefix_and_bare_reference_accept_the_same_symlinked_evidence(
        self,
    ) -> None:
        state = self.initialize()
        observation = self.root / "observation.log"
        observation.write_text("Referenced external observation", encoding="utf-8")
        try:
            (self.workspace / "observed.log").symlink_to(observation)
        except OSError as exc:
            self.skipTest(f"File symlinks unavailable: {exc}")
        directory = product_loop.artifact_path(self.workspace, state, "research").parent
        for reference in ("observed.log", "workspace:observed.log"):
            with self.subTest(reference=reference):
                self.assertTrue(
                    product_loop.reference_resolves(
                        reference, self.workspace, directory
                    )
                )


if __name__ == "__main__":
    unittest.main()
