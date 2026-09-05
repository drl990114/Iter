#!/usr/bin/env python3
"""Deterministic state and quality gates for the Iter skills."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any
from urllib.parse import urlparse

STATE_DIR_NAME = ".product-loop"
STATE_FILE_NAME = "state.json"
SCHEMA_VERSION = 1
TEMPLATE_MARKER = "<!-- product-loop:fill -->"
LOCAL_COMPLETION_LIMIT = "本机场景验证通过；真实用户价值待验证"
REPORT_LANGUAGES = {"en", "zh-CN"}
LOCAL_COMPLETION_LIMITS = {
    "en": "Local scenarios passed; real-user value remains unvalidated.",
    "zh-CN": LOCAL_COMPLETION_LIMIT,
}
TERMINAL_STAGES = {"complete", "stopped"}
NEXT_STAGE = {
    "research": "differentiation",
    "differentiation": "experiment",
    "experiment": "approval",
    "development": "evaluation",
}
STAGE_SKILLS = {
    "research": "iterate-product",
    "differentiation": "iterate-product",
    "experiment": "iterate-product",
    "approval": "iterate-product",
    "development": "iterate-product",
    "evaluation": "iterate-product",
    "complete": None,
    "stopped": None,
}
ARTIFACT_NAMES = {
    "research": "01-research.md",
    "differentiation": "02-opportunities.json",
    "experiment": "03-experiment.md",
    "development": "04-delivery.md",
    "evaluation": "05-evaluation.md",
}
TEMPLATE_NAMES = {
    "research": "research-template.md",
    "differentiation": "opportunities-template.json",
    "experiment": "experiment-template.md",
    "development": "delivery-template.md",
    "evaluation": "evaluation-template.md",
}
REQUIRED_HEADINGS = {
    "research": [
        "# 产品空间调研",
        "## 产品现状",
        "## 需求证据覆盖",
        "## 用户问题证据",
        "## 外部需求信号",
        "## 竞品与替代方案",
        "## 事实、推断与未知",
        "## 来源",
    ],
    "experiment": [
        "# 产品实验",
        "## 机会与证据",
        "## 假设与指标",
        "## 最小范围与非目标",
        "## 验收与埋点",
        "## 风险、回滚与停止条件",
        "## 开源方案评估",
        "## 待批准决策",
    ],
    "development": [
        "# 交付记录",
        "## 实现范围",
        "## 变更文件",
        "## 验证证据",
        "## 回滚方式",
        "## 偏差与剩余风险",
    ],
    "evaluation": [
        "# 产品实验评估",
        "## 原始假设与标准",
        "## 技术与产品证据",
        "## 反证与混杂因素",
        "## 风险与维护成本",
        "## 决策",
        "## 下一步",
    ],
}
ENGLISH_HEADINGS = {
    "research": [
        "# Product research",
        "## Current product",
        "## Evidence coverage",
        "## User problem evidence",
        "## External demand signals",
        "## Competitors and alternatives",
        "## Facts, inferences, and unknowns",
        "## Sources",
    ],
    "experiment": [
        "# Product experiment",
        "## Opportunity and evidence",
        "## Hypothesis and metrics",
        "## Minimum scope and non-goals",
        "## Acceptance and instrumentation",
        "## Risks, recovery, and stop conditions",
        "## Open-source assessment",
        "## Authorization decisions",
    ],
    "development": [
        "# Delivery record",
        "## Implemented scope",
        "## Changed files",
        "## Validation evidence",
        "## Recovery",
        "## Deviations and remaining risks",
    ],
    "evaluation": [
        "# Product experiment evaluation",
        "## Original hypothesis and criteria",
        "## Technical and product evidence",
        "## Counterevidence and confounders",
        "## Risks and maintenance costs",
        "## Decision",
        "## Next steps",
    ],
}
VALIDATION_MODES = {"product_metric", "local_scenario"}
EXECUTION_STATUSES = {"passed", "failed", "blocked"}
OPPORTUNITY_FIELDS = {
    "id",
    "title",
    "target_user",
    "problem",
    "evidence_refs",
    "hypothesis",
    "alternative_gap",
    "counterargument",
    "smallest_experiment",
    "risks",
    "scores",
}
POSITIVE_SCORE_WEIGHTS = {
    "evidence": 0.20,
    "user_pain": 0.20,
    "differentiation": 0.20,
    "strategic_fit": 0.15,
    "reach": 0.10,
    "confidence": 0.10,
    "reversibility": 0.05,
}
PENALTY_SCORE_WEIGHTS = {
    "effort": 0.08,
    "risk": 0.12,
}


class ProductLoopError(RuntimeError):
    """Raised for invalid Iter state or artifacts."""


def report_language(state: dict[str, Any]) -> str:
    # States written before bilingual reports always used Chinese templates.
    return state.get("language", "zh-CN")


def required_headings(language: str) -> dict[str, list[str]]:
    return ENGLISH_HEADINGS if language == "en" else REQUIRED_HEADINGS


def require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProductLoopError(f"{field} must be a non-empty string.")
    return value.strip()


def require_text_list(value: Any, field: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ProductLoopError(
            f"{field} must be {'an' if allow_empty else 'a non-empty'} array."
        )
    return [require_text(item, field) for item in value]


def reject_unknown_fields(
    payload: dict[str, Any], allowed: set[str], field: str
) -> None:
    unknown = sorted(payload.keys() - allowed)
    if unknown:
        raise ProductLoopError(f"Unknown {field} fields: {', '.join(unknown)}")


def normalize_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(proposal, dict):
        raise ProductLoopError("proposal must be an object.")
    reject_unknown_fields(
        proposal,
        {
            "id",
            "title",
            "objective",
            "scope",
            "acceptance",
            "risks",
            "metric",
            "validation",
        },
        "proposal",
    )
    normalized: dict[str, Any] = {
        field: require_text(proposal.get(field), f"proposal.{field}")
        for field in ("id", "title", "objective")
    }
    for field in ("scope", "acceptance", "risks"):
        normalized[field] = require_text_list(
            proposal.get(field), f"proposal.{field}", allow_empty=field == "risks"
        )
    metric = proposal.get("metric")
    if not isinstance(metric, dict):
        raise ProductLoopError("proposal.metric must be an object.")
    reject_unknown_fields(metric, {"name", "baseline", "target"}, "metric")
    normalized["metric"] = {
        "name": require_text(metric.get("name"), "proposal.metric.name"),
        "baseline": metric.get("baseline"),
        "target": require_text(metric.get("target"), "proposal.metric.target"),
    }
    validation = proposal.get("validation")
    if (
        not isinstance(validation, dict)
        or validation.get("mode") not in VALIDATION_MODES
    ):
        raise ProductLoopError(
            "proposal.validation.mode must be product_metric or local_scenario."
        )
    reject_unknown_fields(
        validation,
        {"mode", "data_policy", "data_scope", "side_effects", "recovery", "scenarios"},
        "validation",
    )
    data_policy = validation.get("data_policy", "isolated")
    if data_policy not in {"isolated", "user_data"}:
        raise ProductLoopError("validation.data_policy must be isolated or user_data.")
    scenarios = validation.get("scenarios", [])
    if not isinstance(scenarios, list):
        raise ProductLoopError("validation.scenarios must be an array.")
    if validation["mode"] == "local_scenario" and not scenarios:
        raise ProductLoopError("local_scenario requires an executable scenario plan.")
    local = validation["mode"] == "local_scenario"
    data_scope = require_text_list(
        validation.get("data_scope", []), "validation.data_scope", allow_empty=not local
    )
    side_effects = require_text_list(
        validation.get("side_effects") if local else validation.get("side_effects", []),
        "validation.side_effects",
        allow_empty=True,
    )
    recovery = validation.get("recovery")
    if local or recovery is not None:
        recovery = require_text(recovery, "validation.recovery")
    normalized_scenarios = []
    seen_ids: set[str] = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise ProductLoopError("Each validation scenario must be an object.")
        reject_unknown_fields(scenario, {"id", "steps", "expected"}, "scenario")
        scenario_id = require_text(scenario.get("id"), "scenario.id")
        if scenario_id in seen_ids:
            raise ProductLoopError(f"Duplicate scenario id: {scenario_id}")
        seen_ids.add(scenario_id)
        normalized_scenarios.append(
            {
                "id": scenario_id,
                "steps": require_text_list(scenario.get("steps"), "scenario.steps"),
                "expected": require_text(scenario.get("expected"), "scenario.expected"),
            }
        )
    normalized["validation"] = {
        "mode": validation["mode"],
        "data_policy": data_policy,
        "data_scope": data_scope,
        "side_effects": side_effects,
        "recovery": recovery,
        "scenarios": normalized_scenarios,
    }
    return normalized


def proposal_digest(proposal: dict[str, Any]) -> str:
    # Measuring an unknown baseline does not change the authorized target or scope.
    bound = {
        **{key: value for key, value in proposal.items() if key != "title"},
        "metric": {k: v for k, v in proposal["metric"].items() if k != "baseline"},
    }
    serialized = json.dumps(
        bound, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def validation_plan(state: dict[str, Any]) -> dict[str, Any]:
    return state.get(
        "validation", {"mode": "product_metric", "scenarios": [], "evidence": None}
    )


def execution_digest(state: dict[str, Any]) -> str:
    if state.get("proposal"):
        return proposal_digest(state["proposal"])
    legacy_contract = {
        "objective": state["objective"],
        "metric": {
            key: value for key, value in state["metric"].items() if key != "baseline"
        },
        "mode": "product_metric",
    }
    serialized = json.dumps(
        legacy_contract, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def authorization_valid(state: dict[str, Any], kind: str) -> bool:
    proposal = state.get("proposal")
    authorization = state.get("authorizations", {}).get(kind)
    return bool(
        proposal
        and authorization
        and authorization.get("scope_digest") == proposal_digest(proposal)
        and authorization.get("status", "granted") == "granted"
        and authorization.get("actor")
        and authorization.get("evidence")
        and (
            authorization.get("scope", "contract") == "contract"
            or authorization.get("cycle_id") == state["cycle_id"]
        )
    )


def grant_authorizations(
    state: dict[str, Any],
    implementation: bool,
    local: bool,
    actor: str,
    evidence: str | None,
    scope: str = "contract",
) -> None:
    if not implementation and not local:
        return
    actor = require_text(actor, "Authorization actor")
    evidence = require_text(evidence, "Authorization evidence")
    if scope not in {"contract", "cycle"}:
        raise ProductLoopError("Authorization scope must be contract or cycle.")
    if not state.get("proposal"):
        raise ProductLoopError("Scope authorization requires a selected proposal.")
    if local and validation_plan(state)["mode"] != "local_scenario":
        raise ProductLoopError("Local authorization requires local_scenario mode.")
    authorization = {
        "status": "granted",
        "actor": actor,
        "at": utc_now(),
        "evidence": evidence,
        "scope_digest": proposal_digest(state["proposal"]),
        "scope": scope,
        "cycle_id": state["cycle_id"],
    }
    authorizations = state.setdefault("authorizations", {})
    if implementation:
        authorizations["implementation"] = dict(authorization)
    if local:
        authorizations["local"] = dict(authorization)


def install_proposal(state: dict[str, Any], proposal: dict[str, Any]) -> None:
    state["proposal"] = proposal
    state["selected_id"] = proposal["id"]
    state["objective"] = proposal["objective"]
    state["metric"] = dict(proposal["metric"])
    state["validation"] = {**proposal["validation"], "evidence": None}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_workspace(path: str | Path) -> Path:
    workspace = Path(path).expanduser().resolve()
    if not workspace.exists() or not workspace.is_dir():
        raise ProductLoopError(
            f"Workspace does not exist or is not a directory: {workspace}"
        )
    return workspace


def normalize_cycle_id(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()
    if not normalized:
        raise ProductLoopError("Cycle id must contain at least one letter or digit.")
    if len(normalized) > 80:
        raise ProductLoopError("Cycle id must be 80 characters or fewer.")
    return normalized


def default_cycle_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def unused_cycle_id(workspace: Path, cycle_id: str) -> str:
    """Keep interrupted or archived cycle artifacts out of a new round."""
    candidate = cycle_id
    suffix = 2
    while (state_dir(workspace) / "cycles" / candidate).exists():
        ending = f"-{suffix}"
        candidate = f"{cycle_id[: 80 - len(ending)].rstrip('-')}{ending}"
        suffix += 1
    return candidate


def state_dir(workspace: Path) -> Path:
    return workspace / STATE_DIR_NAME


def state_path(workspace: Path) -> Path:
    return state_dir(workspace) / STATE_FILE_NAME


def asset_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "assets"


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProductLoopError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ProductLoopError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProductLoopError(f"Expected a JSON object in {path}.")
    return payload


def validate_state_shape(state: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "cycle_id",
        "stage",
        "status",
        "objective",
        "metric",
        "round",
        "max_rounds",
        "approval",
        "artifacts",
        "history",
    }
    missing = sorted(required - state.keys())
    if missing:
        raise ProductLoopError(
            f"State is missing required fields: {', '.join(missing)}"
        )
    if state["schema_version"] != SCHEMA_VERSION:
        raise ProductLoopError(
            f"Unsupported state schema version: {state['schema_version']}"
        )
    if (
        not isinstance(report_language(state), str)
        or report_language(state) not in REPORT_LANGUAGES
    ):
        raise ProductLoopError("Report language must be en or zh-CN.")
    if state["stage"] not in STAGE_SKILLS:
        raise ProductLoopError(f"Unknown stage: {state['stage']}")
    if not isinstance(state["round"], int) or not isinstance(state["max_rounds"], int):
        raise ProductLoopError("round and max_rounds must be integers.")
    if state["round"] < 1 or state["max_rounds"] < 1:
        raise ProductLoopError("round and max_rounds must be positive.")
    if "proposal" in state:
        normalized = normalize_proposal(state["proposal"])
        if state.get("selected_id") != state["proposal"]["id"]:
            raise ProductLoopError("selected_id must match the selected proposal.")
        if (
            state["objective"] != normalized["objective"]
            or state["metric"] != normalized["metric"]
        ):
            raise ProductLoopError(
                "Objective or metric differs from the selected proposal; use revise."
            )
        if any(
            state.get("validation", {}).get(key) != value
            for key, value in normalized["validation"].items()
        ):
            raise ProductLoopError(
                "Validation plan differs from the selected proposal; use revise."
            )
    if "validation" in state and (
        not isinstance(state["validation"], dict)
        or state["validation"].get("mode") not in VALIDATION_MODES
    ):
        raise ProductLoopError(
            "State validation mode must be product_metric or local_scenario."
        )


def load_state(workspace: Path) -> dict[str, Any]:
    state = read_json(state_path(workspace))
    validate_state_shape(state)
    return state


def save_state(workspace: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = utc_now()
    validate_state_shape(state)
    atomic_write_json(state_path(workspace), state)


def append_decision(workspace: Path, payload: dict[str, Any]) -> None:
    path = state_dir(workspace) / "decision-log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"at": utc_now(), **payload}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def render_template(
    name: str, replacements: dict[str, Any], language: str = "zh-CN"
) -> str:
    if name == "charter-template.md" and language == "zh-CN":
        name = "charter-template.zh-CN.md"
    elif name != "charter-template.md" and name.endswith(".md") and language == "en":
        name = name.removesuffix(".md") + ".en.md"
    path = asset_dir() / name
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ProductLoopError(f"Missing Iter asset: {path}") from exc
    for key, value in replacements.items():
        rendered = "" if value is None else str(value)
        content = content.replace("{{" + key + "}}", rendered)
    return content


def artifact_mapping(cycle_id: str) -> dict[str, str]:
    return {
        stage: f"{STATE_DIR_NAME}/cycles/{cycle_id}/{name}"
        for stage, name in ARTIFACT_NAMES.items()
    }


def create_cycle_templates(
    workspace: Path, state: dict[str, Any], reset_from: str | None = None
) -> None:
    cycle_id = state["cycle_id"]
    cycle_dir = state_dir(workspace) / "cycles" / cycle_id
    cycle_dir.mkdir(parents=True, exist_ok=True)
    replacements = {
        "CYCLE_ID": cycle_id,
        "OBJECTIVE": state["objective"],
        "METRIC": state["metric"]["name"],
        "BASELINE": state["metric"].get("baseline"),
        "TARGET": state["metric"].get("target"),
        "ROUND": state["round"],
    }
    stages = list(TEMPLATE_NAMES)
    reset_stages = set(stages[stages.index(reset_from) :]) if reset_from else set()
    for stage, template_name in TEMPLATE_NAMES.items():
        destination = cycle_dir / ARTIFACT_NAMES[stage]
        if destination.exists() and stage not in reset_stages:
            continue
        atomic_write_text(
            destination,
            render_template(template_name, replacements, report_language(state)),
        )


def initialize_workspace(
    workspace: Path,
    objective: str | None = None,
    metric: str | None = None,
    baseline: str | None = None,
    target: str | None = None,
    cycle_id: str | None = None,
    max_rounds: int = 3,
    force: bool = False,
    proposal: dict[str, Any] | None = None,
    authorize_implementation: bool = False,
    authorize_local: bool = False,
    actor: str = "user",
    authorization_evidence: str | None = None,
    authorization_scope: str = "contract",
    new_cycle: bool = False,
    language: str = "en",
) -> dict[str, Any]:
    if not isinstance(language, str) or language not in REPORT_LANGUAGES:
        raise ProductLoopError("Report language must be en or zh-CN.")
    selected = normalize_proposal(proposal) if proposal is not None else None
    if selected:
        require_text(authorization_evidence, "Selection evidence")
        require_text(actor, "Selection actor")
        if objective is not None and objective.strip() != selected["objective"]:
            raise ProductLoopError("--objective conflicts with the selected proposal.")
        if metric is not None and metric.strip() != selected["metric"]["name"]:
            raise ProductLoopError("--metric conflicts with the selected proposal.")
        objective, metric = selected["objective"], selected["metric"]["name"]
        baseline, target = selected["metric"]["baseline"], selected["metric"]["target"]
    objective = require_text(objective, "Objective")
    metric = require_text(metric, "Metric")
    if max_rounds < 1:
        raise ProductLoopError("max_rounds must be positive.")
    path = state_path(workspace)
    previous_state = None
    if new_cycle:
        if force:
            raise ProductLoopError("--new-cycle and --force cannot be combined.")
        if not path.exists():
            raise ProductLoopError("--new-cycle requires an existing terminal cycle.")
        previous_state = load_state(workspace)
        if previous_state["stage"] not in TERMINAL_STAGES:
            raise ProductLoopError(
                "--new-cycle requires the current cycle to be complete or stopped."
            )
    if path.exists() and not force and not new_cycle:
        raise ProductLoopError(
            f"Iter already exists at {path}; use status instead of reinitializing."
        )

    chosen_cycle_id = normalize_cycle_id(cycle_id or default_cycle_id())
    if new_cycle:
        if cycle_id and (state_dir(workspace) / "cycles" / chosen_cycle_id).exists():
            raise ProductLoopError("A new cycle must use a new cycle id.")
        if not cycle_id:
            root_cycle_id = chosen_cycle_id
            suffix = 2
            while (state_dir(workspace) / "cycles" / chosen_cycle_id).exists():
                chosen_cycle_id = f"{root_cycle_id}-{suffix}"
                suffix += 1
    now = utc_now()
    state: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "language": language,
        "cycle_id": chosen_cycle_id,
        "stage": "research",
        "status": "active",
        "objective": objective.strip(),
        "metric": {
            "name": metric.strip(),
            "baseline": baseline,
            "target": target,
        },
        "round": 1,
        "max_rounds": max_rounds,
        "approval": {
            "status": "pending",
            "actor": None,
            "at": None,
        },
        "artifacts": artifact_mapping(chosen_cycle_id),
        "history": [
            {
                "at": now,
                "event": "initialized",
                "stage": "research",
            }
        ],
        "created_at": now,
        "updated_at": now,
    }
    if selected:
        install_proposal(state, selected)
        state["selection"] = {
            "actor": actor.strip(),
            "at": now,
            "evidence": authorization_evidence,
        }
        state["history"][0]["proposal"] = selected
    grant_authorizations(
        state,
        authorize_implementation,
        authorize_local,
        actor,
        authorization_evidence,
        authorization_scope,
    )
    if selected:
        state["history"][0]["authorizations"] = dict(state.get("authorizations", {}))
        state["history"][0]["selection"] = state["selection"]

    root = state_dir(workspace)
    root.mkdir(parents=True, exist_ok=True)
    charter_path = root / "charter.md"
    if previous_state is not None:
        archive_directory = root / "cycles" / previous_state["cycle_id"]
        archived_state = archive_directory / "terminal-state.json"
        atomic_write_json(archived_state, previous_state)
        if charter_path.is_file():
            atomic_write_text(
                archive_directory / "charter.md",
                charter_path.read_text(encoding="utf-8"),
            )
        state["history"][0]["previous_cycle_id"] = previous_state["cycle_id"]
        state["history"][0]["previous_state"] = str(
            archived_state.relative_to(workspace)
        )
    if not charter_path.exists() or force or new_cycle:
        atomic_write_text(
            charter_path,
            render_template(
                "charter-template.md",
                {
                    "OBJECTIVE": state["objective"],
                    "METRIC": state["metric"]["name"],
                    "BASELINE": baseline,
                    "TARGET": target,
                    "MAX_ROUNDS": max_rounds,
                },
                language,
            ),
        )
    (root / "decision-log.jsonl").touch(exist_ok=True)
    create_cycle_templates(workspace, state)
    save_state(workspace, state)
    append_decision(
        workspace,
        {
            "event": "initialized",
            "cycle_id": chosen_cycle_id,
            "objective": state["objective"],
            "metric": state["metric"],
        },
    )
    return state


def artifact_path(workspace: Path, state: dict[str, Any], stage: str) -> Path:
    resolved_workspace = workspace.resolve()
    relative = state["artifacts"].get(stage)
    if not isinstance(relative, str):
        raise ProductLoopError(f"No artifact is configured for stage: {stage}")
    candidate = (resolved_workspace / relative).resolve()
    try:
        candidate.relative_to(resolved_workspace)
    except ValueError as exc:
        raise ProductLoopError(f"Artifact escapes workspace: {candidate}") from exc
    return candidate


def reference_resolves(
    reference: str, workspace: Path, artifact_directory: Path
) -> bool:
    reference = reference.strip().strip("<>")
    windows_absolute = PureWindowsPath(reference).is_absolute()
    if not windows_absolute:
        parsed = urlparse(reference)
        if parsed.scheme in {"http", "https"}:
            return bool(parsed.netloc)
        if parsed.scheme and not re.search(r":\d+(?::\d+)?$", reference):
            return False
    reference = reference.split("#", 1)[0]
    reference = re.sub(r":\d+(?::\d+)?$", "", reference)
    if not reference:
        return False
    path = Path(reference).expanduser()
    if path.is_absolute() or windows_absolute:
        return path.is_file()
    return (workspace / path).is_file() or (artifact_directory / path).is_file()


def source_references(line: str) -> list[str]:
    references = re.findall(r"\]\(([^)]+)\)", line)
    references.extend(re.findall(r"`([^`]+)`", line))
    references.extend(re.findall(r"https?://[^\s)]+", line))
    unlabelled = re.sub(r"^\s*-\s+(?:\[[^\]]+\]\s*)?", "", line).strip()
    references.append(unlabelled.split(" — ", 1)[0])
    return references


def validate_markdown(
    path: Path, stage: str, workspace: Path | None = None, language: str = "zh-CN"
) -> list[str]:
    errors: list[str] = []
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [f"Missing artifact: {path}"]
    if TEMPLATE_MARKER in content:
        errors.append("Artifact still contains template markers.")
    headings = required_headings(language)[stage]
    for heading in headings:
        if heading not in content:
            errors.append(f"Missing required heading: {heading}")
        elif heading.startswith("## "):
            body = content.split(heading, 1)[1]
            body = re.split(r"(?m)^#{1,2} ", body, maxsplit=1)[0]
            body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL).strip()
            if not body:
                errors.append(f"Required section is empty: {heading}")
    if stage == "research":
        source_section = content.split(headings[-1], 1)[-1]
        source_lines = [
            line
            for line in source_section.splitlines()
            if line.lstrip().startswith("- ")
        ]
        if not any(
            reference_resolves(reference, workspace or path.parent, path.parent)
            for line in source_lines
            for reference in source_references(line)
        ):
            errors.append(
                "Research must include at least one traceable source URL or existing file."
            )
        feedback_matches = re.findall(
            r"(?im)^\s*direct_user_feedback\s*[:：]\s*(sufficient|sparse|absent)\s*$",
            content,
        )
        if len(feedback_matches) != 1:
            errors.append(
                "Research must contain exactly one "
                "`direct_user_feedback: sufficient|sparse|absent`."
            )
    if stage == "evaluation":
        verdicts = re.findall(
            r"(?im)^\s*(?:verdict|结论)\s*[:：]\s*(complete|iterate|stop)\s*$",
            content,
        )
        if len(verdicts) != 1:
            errors.append(
                "Evaluation must contain exactly one `verdict: complete|iterate|stop`."
            )
    return errors


def require_score(value: Any, field: str, opportunity_id: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise ProductLoopError(
            f"Opportunity {opportunity_id} score `{field}` must be an integer from 1 to 5."
        )
    return value


def validate_opportunity_payload(
    payload: dict[str, Any], require_rank: bool, selected_id: str | None = None
) -> list[dict[str, Any]]:
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        raise ProductLoopError("`opportunities` must be an array.")
    if not 1 <= len(opportunities) <= 7:
        raise ProductLoopError("Provide between 1 and 7 opportunities.")
    payload_selected_id = payload.get("selected_id")
    if selected_id and payload_selected_id and selected_id != payload_selected_id:
        raise ProductLoopError(
            "Opportunity selection conflicts with the saved selected_id."
        )
    selected_id = selected_id or payload_selected_id
    if selected_id is not None:
        selected_id = require_text(selected_id, "selected_id")
    if len(opportunities) == 1 and not selected_id:
        raise ProductLoopError("A single opportunity requires an explicit selected_id.")
    seen_ids: set[str] = set()
    for index, item in enumerate(opportunities):
        if not isinstance(item, dict):
            raise ProductLoopError(f"Opportunity at index {index} must be an object.")
        missing = sorted(OPPORTUNITY_FIELDS - item.keys())
        if missing:
            raise ProductLoopError(
                f"Opportunity at index {index} is missing: {', '.join(missing)}"
            )
        opportunity_id = item["id"]
        if not isinstance(opportunity_id, str) or not opportunity_id.strip():
            raise ProductLoopError(f"Opportunity at index {index} has an invalid id.")
        if opportunity_id in seen_ids:
            raise ProductLoopError(f"Duplicate opportunity id: {opportunity_id}")
        seen_ids.add(opportunity_id)
        evidence_refs = item["evidence_refs"]
        if not isinstance(evidence_refs, list) or not evidence_refs:
            raise ProductLoopError(
                f"Opportunity {opportunity_id} must include evidence_refs."
            )
        scores = item["scores"]
        if not isinstance(scores, dict):
            raise ProductLoopError(
                f"Opportunity {opportunity_id} scores must be an object."
            )
        for field in (*POSITIVE_SCORE_WEIGHTS, *PENALTY_SCORE_WEIGHTS):
            require_score(scores.get(field), field, opportunity_id)
        if require_rank:
            if not isinstance(item.get("rank"), int):
                raise ProductLoopError(
                    f"Opportunity {opportunity_id} must be ranked by the score command."
                )
            weighted_score = item.get("weighted_score")
            if isinstance(weighted_score, bool) or not isinstance(
                weighted_score, (int, float)
            ):
                raise ProductLoopError(
                    f"Opportunity {opportunity_id} needs a numeric weighted_score."
                )
    if selected_id is not None and selected_id not in seen_ids:
        raise ProductLoopError("selected_id must identify an existing opportunity.")
    return opportunities


def evidence_errors(workspace: Path, state: dict[str, Any], evidence: Any) -> list[str]:
    if not isinstance(evidence, dict):
        return [
            "Record execution evidence before advancing; a planned scenario is not a result."
        ]
    errors: list[str] = []
    if evidence.get("cycle_id") != state["cycle_id"]:
        errors.append("Execution evidence belongs to a different cycle.")
    if evidence.get("scope_digest") != execution_digest(state):
        errors.append("Execution evidence does not match the current proposal scope.")
    if evidence.get("status") not in EXECUTION_STATUSES:
        errors.append("Evidence status must be passed, failed, or blocked.")
    try:
        require_text(evidence.get("summary"), "Evidence summary")
        require_text_list(
            evidence.get("unresolved_risks"),
            "Evidence unresolved_risks",
            allow_empty=True,
        )
    except ProductLoopError as exc:
        errors.append(str(exc))
    for field in ("acceptance_passed", "guardrails_passed"):
        if not isinstance(evidence.get(field), bool):
            errors.append(f"Evidence {field} must be a boolean.")
    metric = evidence.get("metric")
    if evidence.get("status") == "passed" or metric is not None:
        if not isinstance(metric, dict):
            errors.append("Passed evidence requires an observed metric and target_met.")
        else:
            try:
                require_text(metric.get("observed"), "Evidence metric.observed")
            except ProductLoopError as exc:
                errors.append(str(exc))
            if not isinstance(metric.get("target_met"), bool):
                errors.append("Evidence metric.target_met must be a boolean.")

    artifact_directory = artifact_path(workspace, state, "evaluation").parent
    all_refs: list[str] = []

    def check_refs(refs: Any, context: str, required: bool) -> None:
        try:
            parsed = require_text_list(
                refs, f"{context} evidence_refs", allow_empty=not required
            )
        except ProductLoopError as exc:
            errors.append(str(exc))
            return
        for reference in parsed:
            if not reference_resolves(reference, workspace, artifact_directory):
                errors.append(f"Unresolvable evidence reference: {reference}")
        all_refs.extend(parsed)

    check_refs(evidence.get("evidence_refs", []), "Execution", required=False)
    results = evidence.get("results", [])
    if not isinstance(results, list):
        errors.append("Evidence results must be an array.")
        results = []
    planned = {item["id"] for item in validation_plan(state).get("scenarios", [])}
    observed_ids: set[str] = set()
    passed_ids: set[str] = set()
    for result in results:
        if not isinstance(result, dict):
            errors.append("Each execution result must be an object.")
            continue
        scenario_id = result.get("scenario_id")
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            errors.append("Execution result requires scenario_id.")
            continue
        if scenario_id in observed_ids:
            errors.append(f"Duplicate result for scenario: {scenario_id}")
        observed_ids.add(scenario_id)
        if planned and scenario_id not in planned:
            errors.append(f"Result references an unplanned scenario: {scenario_id}")
        result_status = result.get("status")
        if result_status not in EXECUTION_STATUSES:
            errors.append(f"Invalid execution status for scenario: {scenario_id}")
        if evidence.get("status") == "passed" and result_status != "passed":
            errors.append(
                "Passed execution cannot contain failed or blocked scenario results."
            )
        try:
            require_text(
                result.get("observed"), f"Scenario {scenario_id} observed result"
            )
        except ProductLoopError as exc:
            errors.append(str(exc))
        check_refs(
            result.get("evidence_refs", []),
            scenario_id,
            required=result_status != "blocked",
        )
        if result_status == "passed":
            passed_ids.add(scenario_id)
    if evidence.get("status") != "blocked" and not all_refs:
        errors.append(
            "Executed evidence requires at least one traceable result reference."
        )
    if evidence.get("status") == "passed" and planned - passed_ids:
        errors.append(
            "Passed evidence must include a passed result for every planned scenario."
        )
    if (
        validation_plan(state)["mode"] == "local_scenario"
        and evidence.get("status") == "failed"
        and not results
    ):
        errors.append(
            "Failed local execution must record the attempted scenario result."
        )
    return errors


def completion_errors(state: dict[str, Any]) -> list[str]:
    evidence = validation_plan(state).get("evidence")
    if not isinstance(evidence, dict):
        return ["Completion requires execution evidence."]
    errors = []
    if (
        state["metric"].get("target") is None
        or not str(state["metric"].get("target")).strip()
    ):
        errors.append(
            "Completion requires an explicitly agreed metric target; use revise to define it."
        )
    if evidence.get("status") != "passed":
        errors.append("Failed or blocked execution cannot complete the cycle.")
    metric = evidence.get("metric")
    if not isinstance(metric, dict) or metric.get("target_met") is not True:
        errors.append(
            "Completion requires evidence that the approved metric target was met."
        )
    if evidence.get("acceptance_passed") is not True:
        errors.append("Completion requires all approved acceptance criteria to pass.")
    if evidence.get("guardrails_passed") is not True:
        errors.append("Completion requires all guardrails to pass.")
    if evidence.get("unresolved_risks") != []:
        errors.append("Completion cannot leave unresolved risks.")
    return errors


def execution_requires_authorization(evidence: Any) -> bool:
    """A blocker can document partial execution; inspect its actual observations."""
    if not isinstance(evidence, dict) or evidence.get("status") != "blocked":
        return True
    if evidence.get("metric") is not None:
        return True
    results = evidence.get("results", [])
    return isinstance(results, list) and any(
        isinstance(result, dict) and result.get("status") in {"passed", "failed"}
        for result in results
    )


def record_evidence(workspace: Path, payload: dict[str, Any]) -> dict[str, Any]:
    state = load_state(workspace)
    if state["stage"] not in {"development", "evaluation"}:
        raise ProductLoopError(
            "Record execution evidence during development or evaluation."
        )
    if not state.get("proposal") and validation_plan(state)["mode"] != "product_metric":
        raise ProductLoopError(
            "Use revise --proposal before switching a legacy metric to local scenarios."
        )
    digest = execution_digest(state)
    if payload.get("cycle_id", state["cycle_id"]) != state["cycle_id"]:
        raise ProductLoopError("Execution evidence belongs to a different cycle.")
    if payload.get("scope_digest", digest) != digest:
        raise ProductLoopError(
            "Execution evidence belongs to a different proposal scope."
        )
    implementation_authorized = (
        authorization_valid(state, "implementation")
        if state.get("proposal")
        else state["approval"].get("status") == "approved"
    )
    requires_authorization = execution_requires_authorization(payload)
    if requires_authorization and not implementation_authorized:
        raise ProductLoopError(
            "Execution evidence requires current implementation authorization."
        )
    if (
        validation_plan(state)["mode"] == "local_scenario"
        and requires_authorization
        and not authorization_valid(state, "local")
    ):
        raise ProductLoopError(
            "Local scenario execution requires current local authorization."
        )
    evidence = {
        **payload,
        "cycle_id": state["cycle_id"],
        "scope_digest": digest,
        "recorded_at": utc_now(),
    }
    errors = evidence_errors(workspace, state, evidence)
    if errors:
        raise ProductLoopError("; ".join(errors))
    previous = validation_plan(state).get("evidence")
    state.setdefault("validation", {"mode": "product_metric", "scenarios": []})[
        "evidence"
    ] = evidence
    return transition(
        workspace,
        state,
        state["stage"],
        "execution_recorded",
        {
            "execution_status": evidence["status"],
            "previous_evidence": previous,
            "evidence": evidence,
        },
    )


def authorize_state(
    workspace: Path,
    implementation: bool = False,
    local: bool = False,
    actor: str = "user",
    evidence: str | None = None,
    scope: str = "contract",
    revoke_implementation: bool = False,
    revoke_local: bool = False,
) -> dict[str, Any]:
    state = load_state(workspace)
    if state["stage"] in TERMINAL_STAGES:
        raise ProductLoopError("Cannot authorize a terminal cycle.")
    if (
        not implementation
        and not local
        and not revoke_implementation
        and not revoke_local
    ):
        raise ProductLoopError("Choose at least one authorization to record.")
    if (implementation and revoke_implementation) or (local and revoke_local):
        raise ProductLoopError(
            "Cannot grant and revoke the same authorization together."
        )
    if not state.get("proposal"):
        raise ProductLoopError("Scoped authorization requires a selected proposal.")
    actor = require_text(actor, "Authorization actor")
    evidence = require_text(evidence, "Authorization evidence")
    previous_authorizations = dict(state.get("authorizations", {}))
    grant_authorizations(state, implementation, local, actor, evidence, scope)
    for kind, revoke in (
        ("implementation", revoke_implementation),
        ("local", revoke_local),
    ):
        if revoke:
            state.setdefault("authorizations", {})[kind] = {
                "status": "revoked",
                "actor": actor,
                "at": utc_now(),
                "evidence": evidence,
                "scope_digest": proposal_digest(state["proposal"]),
                "cycle_id": state["cycle_id"],
            }
    return transition(
        workspace,
        state,
        state["stage"],
        "scope_authorized",
        {
            "actor": actor,
            "implementation": implementation,
            "local": local,
            "revoke_implementation": revoke_implementation,
            "revoke_local": revoke_local,
            "previous_authorizations": previous_authorizations,
            "scope": scope,
            "authorization_evidence": evidence,
            "scope_digest": proposal_digest(state["proposal"]),
        },
    )


def archive_revision_artifacts(
    workspace: Path, state: dict[str, Any]
) -> dict[str, str]:
    cycle_directory = artifact_path(workspace, state, "research").parent
    revision_number = 1
    while (cycle_directory / "revisions" / f"revision-{revision_number:03}").exists():
        revision_number += 1
    directory = cycle_directory / "revisions" / f"revision-{revision_number:03}"
    snapshots: dict[str, str] = {}
    for stage, name in ARTIFACT_NAMES.items():
        source = artifact_path(workspace, state, stage)
        if source.is_file():
            destination = directory / name
            atomic_write_text(destination, source.read_text(encoding="utf-8"))
            snapshots[stage] = str(destination.relative_to(workspace.resolve()))
    return snapshots


def revise_state(
    workspace: Path,
    proposal: dict[str, Any],
    rationale: str,
    authorize_implementation: bool = False,
    authorize_local: bool = False,
    actor: str = "user",
    authorization_evidence: str | None = None,
    authorization_scope: str = "contract",
) -> dict[str, Any]:
    state = load_state(workspace)
    if state["stage"] in TERMINAL_STAGES:
        raise ProductLoopError(
            "Cannot revise a terminal cycle; start a new cycle explicitly."
        )
    rationale = require_text(rationale, "Revision rationale")
    authorization_evidence = require_text(
        authorization_evidence, "Revision authorization evidence"
    )
    actor = require_text(actor, "Revision actor")
    normalized = normalize_proposal(proposal)
    previous = {
        "proposal": state.get("proposal"),
        "objective": state["objective"],
        "metric": state["metric"],
        "validation": validation_plan(state),
        "approval": state["approval"],
        "authorizations": dict(state.get("authorizations", {})),
        "selected_id": state.get("selected_id"),
    }
    old_digest = proposal_digest(state["proposal"]) if state.get("proposal") else None
    changed = old_digest != proposal_digest(normalized)
    old_evidence = validation_plan(state).get("evidence")
    install_proposal(state, normalized)
    state["selection"] = {
        "actor": actor,
        "at": utc_now(),
        "evidence": authorization_evidence,
    }
    if changed:
        state["authorizations"] = {}
        state["approval"] = {"status": "pending", "actor": None, "at": None}
    else:
        # Baseline-only clarification keeps the contract and its applicable evidence.
        state["validation"]["evidence"] = old_evidence
    grant_authorizations(
        state,
        authorize_implementation,
        authorize_local,
        actor,
        authorization_evidence,
        authorization_scope,
    )
    if changed:
        previous["artifact_snapshots"] = archive_revision_artifacts(workspace, state)
    destination = state["stage"]
    if changed and destination in {"approval", "development", "evaluation"}:
        destination = "experiment"
    if (
        changed
        and previous["selected_id"]
        and previous["selected_id"] != normalized["id"]
        and destination != "research"
    ):
        destination = "differentiation"
    if changed:
        create_cycle_templates(workspace, state, reset_from=destination)
    return transition(
        workspace,
        state,
        destination,
        "proposal_revised",
        {
            "actor": actor,
            "rationale": rationale,
            "authorization_evidence": authorization_evidence,
            "previous": previous,
            "proposal": normalized,
            "scope_changed": changed,
        },
    )


def validate_stage(
    workspace: Path, state: dict[str, Any] | None = None
) -> dict[str, Any]:
    current = state or load_state(workspace)
    stage = current["stage"]
    errors: list[str] = []
    artifact: str | None = None
    if stage in TERMINAL_STAGES:
        return {"ok": True, "stage": stage, "artifact": None, "errors": []}
    if stage == "approval":
        if current.get("proposal"):
            if not authorization_valid(current, "implementation"):
                errors.append(
                    "The current implementation scope has not been authorized."
                )
        elif current["approval"].get("status") != "approved":
            errors.append("Explicit human approval has not been recorded.")
    elif stage == "differentiation":
        path = artifact_path(workspace, current, stage)
        artifact = str(path)
        try:
            validate_opportunity_payload(
                read_json(path),
                require_rank=True,
                selected_id=current.get("selected_id"),
            )
        except ProductLoopError as exc:
            errors.append(str(exc))
    else:
        path = artifact_path(workspace, current, stage)
        artifact = str(path)
        errors.extend(
            validate_markdown(path, stage, workspace, report_language(current))
        )
    if (
        validation_plan(current)["mode"] == "local_scenario"
        and stage not in TERMINAL_STAGES
    ):
        if not current.get("proposal"):
            errors.append("Local scenarios require an explicit approved proposal.")
        elif (
            stage in {"development", "evaluation"}
            and execution_requires_authorization(
                validation_plan(current).get("evidence")
            )
            and not authorization_valid(current, "local")
        ):
            errors.append(
                "Local scenarios require separate authorization for the current scope."
            )
    if stage in {"development", "evaluation"}:
        if (
            current.get("proposal")
            and not authorization_valid(current, "implementation")
            and execution_requires_authorization(
                validation_plan(current).get("evidence")
            )
        ):
            errors.append("The current implementation scope has not been authorized.")
        errors.extend(
            evidence_errors(
                workspace, current, validation_plan(current).get("evidence")
            )
        )
        if (
            stage == "evaluation"
            and not errors
            and evaluation_verdict(path) == "complete"
        ):
            errors.extend(completion_errors(current))
            if validation_plan(current)["mode"] == "local_scenario":
                visible_report = re.sub(
                    r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.DOTALL
                )
                limit = LOCAL_COMPLETION_LIMITS[report_language(current)]
                if limit not in visible_report:
                    errors.append(f"Local completion must state: {limit}")
    return {
        "ok": not errors,
        "stage": stage,
        "artifact": artifact,
        "errors": errors,
    }


def transition(
    workspace: Path,
    state: dict[str, Any],
    destination: str,
    event: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = state["stage"]
    state["stage"] = destination
    state["status"] = "active" if destination not in TERMINAL_STAGES else destination
    history_event = {
        "at": utc_now(),
        "event": event,
        "from": source,
        "to": destination,
    }
    if details:
        history_event.update(details)
    state["history"].append(history_event)
    save_state(workspace, state)
    append_decision(
        workspace,
        {
            "event": event,
            "cycle_id": state["cycle_id"],
            "from": source,
            "to": destination,
            **(details or {}),
        },
    )
    return state


def evaluation_verdict(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    matches = re.findall(
        r"(?im)^\s*(?:verdict|结论)\s*[:：]\s*(complete|iterate|stop)\s*$",
        content,
    )
    if len(matches) != 1:
        raise ProductLoopError(
            "Evaluation must contain exactly one verdict before advancing."
        )
    return matches[0].lower()


def stop_state(
    workspace: Path, rationale: str, evidence: str, actor: str = "user"
) -> dict[str, Any]:
    rationale = require_text(rationale, "Stop rationale")
    evidence = require_text(evidence, "Stop evidence")
    actor = require_text(actor, "Stop actor")
    state = load_state(workspace)
    if state["stage"] in TERMINAL_STAGES:
        return state
    return transition(
        workspace,
        state,
        "stopped",
        "user_stopped",
        {"actor": actor, "rationale": rationale, "evidence": evidence},
    )


def advance_state(
    workspace: Path,
    approve: bool = False,
    actor: str = "user",
    outcome: str | None = None,
    authorization_evidence: str | None = None,
    authorization_scope: str = "contract",
) -> dict[str, Any]:
    state = load_state(workspace)
    stage = state["stage"]
    if stage in TERMINAL_STAGES:
        raise ProductLoopError(f"Cannot advance terminal stage: {stage}")
    if outcome is not None and stage != "evaluation":
        raise ProductLoopError(
            "--outcome is only valid during evaluation; use stop to cancel an active cycle."
        )

    if stage == "approval":
        if state.get("proposal") and authorization_valid(state, "implementation"):
            actor = state["authorizations"]["implementation"]["actor"]
        elif not approve:
            raise ProductLoopError(
                "Approval requires `--approve` after explicit user authorization."
            )
        elif state.get("proposal"):
            grant_authorizations(
                state, True, False, actor, authorization_evidence, authorization_scope
            )
        if not actor.strip():
            raise ProductLoopError("Approval actor cannot be empty.")
        now = utc_now()
        state["approval"] = {
            "status": "approved",
            "actor": actor.strip(),
            "at": now,
        }
        if state.get("proposal"):
            state["approval"]["scope_digest"] = proposal_digest(state["proposal"])
        return transition(
            workspace,
            state,
            "development",
            "approved",
            {"actor": actor.strip()},
        )

    result = validate_stage(workspace, state)
    if not result["ok"]:
        raise ProductLoopError("; ".join(result["errors"]))

    if stage == "evaluation":
        if outcome not in {"complete", "iterate", "stop"}:
            raise ProductLoopError(
                "Evaluation advance requires --outcome complete|iterate|stop."
            )
        report_outcome = evaluation_verdict(
            artifact_path(workspace, state, "evaluation")
        )
        if report_outcome != outcome:
            raise ProductLoopError(
                f"Outcome `{outcome}` does not match report verdict `{report_outcome}`."
            )
        if outcome == "complete":
            state["completion"] = {
                "basis": validation_plan(state)["mode"],
                "real_user_value": "unvalidated"
                if validation_plan(state)["mode"] == "local_scenario"
                else "measured",
            }
            return transition(workspace, state, "complete", "cycle_completed")
        if outcome == "stop":
            return transition(workspace, state, "stopped", "cycle_stopped")
        if state["round"] >= state["max_rounds"]:
            return transition(
                workspace,
                state,
                "stopped",
                "round_budget_exhausted",
                {"max_rounds": state["max_rounds"]},
            )
        next_round = state["round"] + 1
        root_id = re.sub(r"-r\d+$", "", state["cycle_id"])
        round_suffix = f"-r{next_round}"
        next_cycle_id = unused_cycle_id(
            workspace,
            normalize_cycle_id(
                f"{root_id[: 80 - len(round_suffix)].rstrip('-')}{round_suffix}"
            ),
        )
        source_cycle_id = state["cycle_id"]
        previous_evidence = validation_plan(state).get("evidence")
        state["round"] = next_round
        state["cycle_id"] = next_cycle_id
        state["approval"] = {
            "status": "pending",
            "actor": None,
            "at": None,
        }
        state["artifacts"] = artifact_mapping(next_cycle_id)
        if "validation" in state:
            state["validation"] = {**state["validation"], "evidence": None}
        if "authorizations" in state:
            state["authorizations"] = {
                kind: authorization
                for kind, authorization in state["authorizations"].items()
                if authorization_valid(state, kind)
            }
        state.pop("completion", None)
        create_cycle_templates(workspace, state)
        return transition(
            workspace,
            state,
            "research",
            "iteration_started",
            {
                "previous_cycle_id": source_cycle_id,
                "round": next_round,
                "previous_evidence": previous_evidence,
            },
        )

    destination = NEXT_STAGE.get(stage)
    if destination is None:
        raise ProductLoopError(f"No transition is configured from stage: {stage}")
    return transition(workspace, state, destination, "stage_advanced")


def score_payload(
    payload: dict[str, Any], selected_id: str | None = None
) -> dict[str, Any]:
    opportunities = validate_opportunity_payload(
        payload, require_rank=False, selected_id=selected_id
    )
    if selected_id:
        payload = {**payload, "selected_id": selected_id}
    scored: list[dict[str, Any]] = []
    for original in opportunities:
        item = dict(original)
        scores = item["scores"]
        positive = sum(
            require_score(scores[field], field, item["id"]) * weight
            for field, weight in POSITIVE_SCORE_WEIGHTS.items()
        )
        penalty = sum(
            (require_score(scores[field], field, item["id"]) - 1) * weight
            for field, weight in PENALTY_SCORE_WEIGHTS.items()
        )
        normalized = max(0.0, min(100.0, (positive - penalty) / 5 * 100))
        item["weighted_score"] = round(normalized, 1)
        scored.append(item)
    scored.sort(key=lambda item: (-item["weighted_score"], item["id"]))
    for rank, item in enumerate(scored, start=1):
        item["rank"] = rank
        item["recommended"] = rank == 1 and item["weighted_score"] >= 60
    return {
        **payload,
        "rubric_version": "1.0",
        "scored_at": utc_now(),
        "opportunities": scored,
    }


def score_file(
    input_path: Path, output_path: Path | None = None, selected_id: str | None = None
) -> dict[str, Any]:
    payload = read_json(input_path)
    scored = score_payload(payload, selected_id=selected_id)
    atomic_write_json(output_path or input_path, scored)
    return scored


def status_payload(workspace: Path) -> dict[str, Any]:
    state = load_state(workspace)
    stage = state["stage"]
    artifact = None
    if stage in ARTIFACT_NAMES:
        artifact = str(artifact_path(workspace, state, stage))
    return {
        "ok": True,
        "workspace": str(workspace),
        "cycle_id": state["cycle_id"],
        "stage": stage,
        "status": state["status"],
        "language": report_language(state),
        "round": state["round"],
        "max_rounds": state["max_rounds"],
        "objective": state["objective"],
        "metric": state["metric"],
        "next_skill": STAGE_SKILLS[stage],
        "next_phase": None if stage in TERMINAL_STAGES else stage,
        "expected_artifact": artifact,
        "approval": state["approval"],
        "selected_id": state.get("selected_id"),
        "proposal": state.get("proposal"),
        "scope_digest": execution_digest(state),
        "validation": validation_plan(state),
        "authorizations": state.get("authorizations", {}),
        "completion": state.get("completion"),
        "local_completion_limit": LOCAL_COMPLETION_LIMITS[report_language(state)]
        if validation_plan(state)["mode"] == "local_scenario"
        else None,
    }


def print_json(payload: dict[str, Any]) -> None:
    # Escapes keep structured output valid in non-UTF-8 Windows pipes too.
    # Workspace files remain UTF-8 and JSON consumers recover the original text.
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage an evidence-gated Iter workspace."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize .product-loop state.")
    init_parser.add_argument("--workspace", required=True)
    init_parser.add_argument("--objective")
    init_parser.add_argument("--metric")
    init_parser.add_argument("--proposal")
    init_parser.add_argument("--baseline")
    init_parser.add_argument("--target")
    init_parser.add_argument("--cycle-id")
    init_parser.add_argument("--max-rounds", type=int, default=3)
    init_parser.add_argument("--force", action="store_true")
    init_parser.add_argument("--new-cycle", action="store_true")
    init_parser.add_argument(
        "--language", choices=sorted(REPORT_LANGUAGES), default="en"
    )

    def authorization_arguments(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--authorize-implementation", action="store_true")
        command_parser.add_argument("--authorize-local", action="store_true")
        command_parser.add_argument("--actor", default="user")
        command_parser.add_argument("--authorization-evidence")
        command_parser.add_argument(
            "--authorization-scope", choices=("contract", "cycle"), default="contract"
        )

    authorization_arguments(init_parser)

    authorize_parser = subparsers.add_parser(
        "authorize",
        help="Record explicit scoped authorization without revising the plan.",
    )
    authorize_parser.add_argument("--workspace", required=True)
    authorization_arguments(authorize_parser)
    authorize_parser.add_argument("--revoke-implementation", action="store_true")
    authorize_parser.add_argument("--revoke-local", action="store_true")

    revise_parser = subparsers.add_parser(
        "revise", help="Record an explicitly authorized proposal revision."
    )
    revise_parser.add_argument("--workspace", required=True)
    revise_parser.add_argument("--proposal", required=True)
    revise_parser.add_argument("--rationale", required=True)
    authorization_arguments(revise_parser)

    evidence_parser = subparsers.add_parser(
        "evidence", help="Record observed execution results or a concrete blocker."
    )
    evidence_parser.add_argument("--workspace", required=True)
    evidence_parser.add_argument("--input", required=True)

    for name in ("status", "validate"):
        command_parser = subparsers.add_parser(name)
        command_parser.add_argument("--workspace", required=True)

    stop_parser = subparsers.add_parser("stop", help="Record the user's cancellation.")
    stop_parser.add_argument("--workspace", required=True)
    stop_parser.add_argument("--rationale", required=True)
    stop_parser.add_argument("--evidence", required=True)
    stop_parser.add_argument("--actor", default="user")

    advance_parser = subparsers.add_parser("advance")
    advance_parser.add_argument("--workspace", required=True)
    advance_parser.add_argument("--approve", action="store_true")
    advance_parser.add_argument("--actor", default="user")
    advance_parser.add_argument("--authorization-evidence")
    advance_parser.add_argument(
        "--authorization-scope", choices=("contract", "cycle"), default="contract"
    )
    advance_parser.add_argument("--outcome", choices=("complete", "iterate", "stop"))

    score_parser = subparsers.add_parser("score")
    score_parser.add_argument("--input", required=True)
    score_parser.add_argument("--output")
    score_parser.add_argument("--selected-id")

    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("--workspace", required=True)
    record_parser.add_argument("--kind", required=True)
    record_parser.add_argument("--summary", required=True)
    record_parser.add_argument("--rationale", required=True)
    record_parser.add_argument("--evidence", action="append", default=[])
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "score":
        output = Path(args.output).expanduser().resolve() if args.output else None
        scored = score_file(
            Path(args.input).expanduser().resolve(), output, args.selected_id
        )
        return {
            "ok": True,
            "output": str(output or Path(args.input).expanduser().resolve()),
            "opportunities": len(scored["opportunities"]),
            "recommended": next(
                (item["id"] for item in scored["opportunities"] if item["recommended"]),
                None,
            ),
        }

    workspace = normalize_workspace(args.workspace)
    if args.command == "init":
        state = initialize_workspace(
            workspace=workspace,
            objective=args.objective,
            metric=args.metric,
            baseline=args.baseline,
            target=args.target,
            cycle_id=args.cycle_id,
            max_rounds=args.max_rounds,
            force=args.force,
            proposal=read_json(Path(args.proposal).expanduser().resolve())
            if args.proposal
            else None,
            authorize_implementation=args.authorize_implementation,
            authorize_local=args.authorize_local,
            actor=args.actor,
            authorization_evidence=args.authorization_evidence,
            authorization_scope=args.authorization_scope,
            new_cycle=args.new_cycle,
            language=args.language,
        )
        return {"ok": True, "state": state, "workspace": str(workspace)}
    if args.command == "status":
        return status_payload(workspace)
    if args.command == "validate":
        return validate_stage(workspace)
    if args.command == "stop":
        return {
            "ok": True,
            "state": stop_state(workspace, args.rationale, args.evidence, args.actor),
        }
    if args.command == "authorize":
        state = authorize_state(
            workspace,
            args.authorize_implementation,
            args.authorize_local,
            args.actor,
            args.authorization_evidence,
            args.authorization_scope,
            args.revoke_implementation,
            args.revoke_local,
        )
        return {"ok": True, "state": state}
    if args.command == "revise":
        state = revise_state(
            workspace,
            read_json(Path(args.proposal).expanduser().resolve()),
            args.rationale,
            args.authorize_implementation,
            args.authorize_local,
            args.actor,
            args.authorization_evidence,
            args.authorization_scope,
        )
        return {"ok": True, "state": state}
    if args.command == "evidence":
        state = record_evidence(
            workspace, read_json(Path(args.input).expanduser().resolve())
        )
        return {"ok": True, "state": state}
    if args.command == "advance":
        state = advance_state(
            workspace,
            approve=args.approve,
            actor=args.actor,
            outcome=args.outcome,
            authorization_evidence=args.authorization_evidence,
            authorization_scope=args.authorization_scope,
        )
        return {"ok": True, "state": state}
    if args.command == "record":
        state = load_state(workspace)
        append_decision(
            workspace,
            {
                "event": "decision_recorded",
                "cycle_id": state["cycle_id"],
                "kind": args.kind,
                "summary": args.summary,
                "rationale": args.rationale,
                "evidence": args.evidence,
            },
        )
        return {"ok": True, "recorded": args.kind}
    raise ProductLoopError(f"Unsupported command: {args.command}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = run(args)
    except ProductLoopError as exc:
        print_json({"ok": False, "error": str(exc)})
        return 2
    print_json(result)
    if args.command == "validate" and not result["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
