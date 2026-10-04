"""Local Iter storage, independent of the installed skill and product workspace.

Like CODEX_HOME, ITER_HOME overrides a single user-level directory. This module
uses only the standard library so copied Skills need no Python installation step.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path, PureWindowsPath
from typing import Any

LEGACY_DIR_NAME = ".product-loop"


class ProductLoopError(RuntimeError):
    """Invalid Iter state, storage, or artifacts."""


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
        temporary_path.unlink(missing_ok=True)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProductLoopError(f"Cannot read JSON from {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProductLoopError(f"Expected a JSON object in {path}.")
    return payload


def contained_path(root: Path, relative: str) -> Path:
    """Managed paths cannot be absolute, traverse upwards, or follow symlinks."""
    path = Path(relative)
    if (
        path.is_absolute()
        or PureWindowsPath(relative).drive
        or ".." in path.parts
        or ".." in PureWindowsPath(relative).parts
    ):
        raise ProductLoopError(f"Path escapes storage root: {relative}")
    candidate = root / path
    for part in (candidate, *candidate.parents):
        if part == root.parent:
            break
        if part.is_symlink():
            raise ProductLoopError(f"Managed storage path is a symlink: {part}")
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ProductLoopError(f"Path escapes storage root: {relative}")
    return candidate


def directory_identity(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {"device": stat.st_dev, "inode": stat.st_ino}


class StorageContext:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.expanduser().resolve()
        configured = os.environ.get("ITER_HOME")
        home = Path(configured).expanduser() if configured else Path.home() / ".iter"
        if not home.is_absolute():
            raise ProductLoopError("ITER_HOME must be an absolute directory path.")
        self.home = home.resolve()
        if self.home.is_relative_to(self.workspace):
            raise ProductLoopError("ITER_HOME must be outside the product workspace.")
        self.workspace_id = hashlib.sha256(
            os.path.normcase(str(self.workspace)).encode("utf-8")
        ).hexdigest()
        self.root = contained_path(self.home, f"workspaces/{self.workspace_id}")
        if self.root.is_relative_to(self.workspace):
            raise ProductLoopError(
                "Iter storage must be outside the product workspace."
            )
        self.legacy = self.workspace / LEGACY_DIR_NAME

    def metadata(self, check_identity: bool = True) -> dict[str, Any] | None:
        path = contained_path(self.root, "workspace.json")
        if not path.exists():
            if (self.root / "state.json").exists():
                raise ProductLoopError(f"Missing workspace ownership metadata: {path}")
            return None
        metadata = read_json(path)
        if (
            metadata.get("version") != 1
            or metadata.get("workspace") != str(self.workspace)
            or metadata.get("workspace_id") != self.workspace_id
        ):
            raise ProductLoopError(f"Storage belongs to another workspace: {self.root}")
        if (
            check_identity
            and self.workspace.exists()
            and metadata.get("identity") != directory_identity(self.workspace)
        ):
            raise ProductLoopError(
                "Workspace directory was replaced; do not reuse its saved grants. "
                f"Inspect the existing storage first: {self.root}"
            )
        return metadata

    def new_metadata(self) -> dict[str, Any]:
        return {
            "version": 1,
            "workspace": str(self.workspace),
            "workspace_id": self.workspace_id,
            "identity": directory_identity(self.workspace),
        }

    def ensure(self) -> None:
        metadata = self.metadata()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if metadata is None:
            atomic_write_json(self.root / "workspace.json", self.new_metadata())

    def require_current(self) -> None:
        self.metadata()
        for filename, command in (
            ("migration.json", "migrate"),
            ("relocation.json", "relocate"),
        ):
            receipt = contained_path(self.root, filename)
            if receipt.exists() and not read_json(receipt).get("complete"):
                raise ProductLoopError(
                    f"Pending {command} transaction; rerun the same {command} command first."
                )
        if self.legacy.exists() or self.legacy.is_symlink():
            raise ProductLoopError(
                f"Legacy storage exists at {self.legacy}; run migrate --workspace "
                f'"{self.workspace}" before changing this cycle.'
            )


def tree_manifest(root: Path) -> dict[str, str]:
    """Inventory every regular file and directory; never follow legacy links."""
    if root.is_symlink() or not root.is_dir():
        raise ProductLoopError(f"Expected a real storage directory: {root}")
    manifest: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ProductLoopError(f"Cannot migrate a storage symlink: {path}")
        if path.is_file():
            manifest[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        elif path.is_dir():
            manifest[relative + "/"] = "directory"
        else:
            raise ProductLoopError(f"Cannot migrate a special file: {path}")
    return manifest
