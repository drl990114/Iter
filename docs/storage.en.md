# Storage, migration, and workspace moves

[简体中文](storage.md)

Iter keeps its workflow files outside your product project. The default base directory is `~/.iter`; each resolved workspace path has its own storage. State, reports, proposal/execution inputs, and generated evidence live there. Product edits and approved test fixtures still belong to their intended project or temporary directory. Existing user evidence is referenced in place.

## Find the actual paths

Run the helper from the installed Skill, replacing the placeholders:

```sh
python3 "<skill-dir>/scripts/product_loop.py" paths --workspace "<workspace>"
python3 "<skill-dir>/scripts/product_loop.py" status --workspace "<workspace>"
```

Both commands are read-only and do not create storage. `paths` returns `iter_home`, `storage_root`, `state_path`, `inputs_dir`, `evidence_dir`, `exists`, `legacy_exists`, and `migration_required`. An empty `status` returns `exists: false`. Check migration flags before starting a new cycle.

Before initialization, `inputs_dir` and `evidence_dir` are under `storage_root`. After initialization, they point into the current cycle. The agent should query paths again after initializing or starting a new round. Use these returned locations instead of guessing from the project name or manually calculating its hash.

To choose another base directory, set `ITER_HOME` to an absolute path outside the workspace in the environment used by your host:

```sh
export ITER_HOME="/absolute/external/path/iter-data"
```

In PowerShell:

```powershell
$env:ITER_HOME = 'C:\external\iter-data'
```

Keep the same value across sessions. Changing it selects a different storage location; it does not move existing records. A symlinked workspace resolves to its real path, while separate clones and Git worktrees have independent records. One active cycle per workspace remains the limit; simultaneous writers are unsupported.

## Host write access

The coding host must be able to write to the exact `storage_root` returned for this workspace, including before initialization when it creates a proposal input. Reuse an existing matching grant or use the host's normal directory-permission mechanism. The `ITER_HOME` setting itself grants no access.

When access is unavailable, Iter reports the required directory and stops dependent writes. It does not create `.product-loop/` or proposal/report/log files in the project as a fallback. The Skill installation directory and product-code permissions remain separate from workflow storage.

## Migrate an existing cycle

If `migration_required` is true, upgrade explicitly before resuming. First pause or finish every session that can still write this workspace's old `.product-loop/`, including sessions using an older installed Skill. Keep them stopped until migration completes; simultaneous writers are unsupported.

```sh
python3 "<skill-dir>/scripts/product_loop.py" migrate --workspace "<workspace>"
python3 "<skill-dir>/scripts/product_loop.py" status --workspace "<workspace>"
```

The migration validates the legacy `.product-loop/` state, retains an external backup, transfers the workflow artifacts to schema-2 storage, and removes the old workflow directory only after success. Do not delete it first or initialize an empty cycle over it. If existing external state conflicts, resolve the reported conflict instead of overwriting either copy.

Saved grants, proposal digests, report text, and language are preserved. Legacy `.product-loop/...` references and old absolute managed paths remain readable through stored path mappings. Existing evidence elsewhere in the project stays in place. Check `status` and retain the returned `backup_path` until you have verified the migrated cycle.

If migration is interrupted, keep the same workspace and `ITER_HOME` and rerun the same `migrate` command. It verifies the saved transaction, external copy, and backup before continuing cleanup. If it reports changed files or a conflict, preserve both locations for inspection; do not delete transaction files, hand-edit state, or start a replacement cycle. Pending transactions must be completed before ordinary workflow writes.

Storage migration does not approve new product work or data operations. A material change to the approved scope still uses `revise` and the applicable authorization.

## Move or rename a workspace

Pause or finish its active sessions before moving the workspace, and record its existing `storage_root` with `paths`. After moving, query `paths` for the new workspace and allow the host to move data between those two exact storage locations. This operation needs access to both locations; the new workspace's ordinary write grant alone may be insufficient. Then reconnect its records explicitly:

```sh
python3 "<skill-dir>/scripts/product_loop.py" relocate --workspace "<new-workspace>" --from "<old-workspace>"
python3 "<skill-dir>/scripts/product_loop.py" paths --workspace "<new-workspace>"
python3 "<skill-dir>/scripts/product_loop.py" status --workspace "<new-workspace>"
```

The old workspace path must no longer exist. This operation reconnects a moved project; it cannot merge two existing clones or worktrees. Inspect any target-storage conflict instead of editing state or copying grants by hand. If interrupted, rerun the same `relocate` command with the same old/new paths and `ITER_HOME`; the saved transaction is checked before ownership is completed. A location-only move preserves grants and report bodies; changed scope, data operations, or risks require `revise` before further execution.

## Evidence references and sharing

Generated logs belong in the returned `evidence_dir`; proposal/execution JSON belongs in `inputs_dir`. Use the actual absolute evidence path, or `storage:<relative-path>` relative to `storage_root`. For source files and existing user evidence, `workspace:<relative-path>` makes the workspace root explicit. Report-relative and ordinary workspace-relative references remain supported, but ambiguous references to different existing files are rejected.

Migration and relocation preserve compatibility with old managed paths without rewriting historical reports. They do not copy unrelated user evidence or prove that an evidence claim is true. Inspect the actual file under the applicable authorization.

External storage is local workflow data, not a backup service or an upload. Review reports and evidence before sharing them; they can contain source excerpts, user decisions, and local paths. Moving workflow files out of Git does not change the host or model provider's data handling.
