# Iter

**English** | [简体中文](README.zh-CN.md)

**Take a product improvement from “what should we do next?” through implementation, validation, and review.**

**MIT · English / 简体中文.** See the [installation guide](docs/harnesses.en.md) for tool compatibility and validation coverage.

Iter's **`iterate-product`** skill proposes 2–3 concrete improvements, delivers the scope you choose and authorize, and resumes saved work when needed. When user feedback is unavailable, it can validate authorized local scenarios while keeping real-user value marked as unverified.

## Install

```sh
npx skills add drl990114/Iter --skill iterate-product --copy
```

Run this in the target project and choose your AI coding tool. Requires Node.js 22.20+, Git, Python 3.10+, and a tool with file access and command execution. `--copy` also handles installing to multiple tools in a new project.

Remote installation requires access to the repository. To install from a local checkout:

```sh
npx skills add /absolute/path/to/Iter --skill iterate-product --copy
```

For native plugins, updates, migration, and platform-specific setup, see the [installation guide](docs/harnesses.en.md).

## Usage

Start a new session after installation and ask your coding tool to use `iterate-product`.

Reports follow the conversation language. New CLI cycles default to English; existing Chinese cycles retain their language when migrating storage.

**Explore what to build next:**

```text
Use iterate-product to propose 2–3 concrete improvements for this product. Explain the user benefit, smallest scope, acceptance criteria, and risks. Recommend one for me to choose.
```

**Deliver a feature you have already chosen:**

```text
Use iterate-product to add search history to this project, keeping at most 10 entries and supporting a clear action.
You may implement this scope and create isolated test data in a temporary directory. Verify deduplication, the entry limit, and clearing. Complete implementation, tests, and review.
```

**Resume a saved iteration:**

```text
Use iterate-product to resume the saved product iteration. Continue within the approved scope and ask only when a material decision changes.
```

Iter stores state, reports, proposal inputs, and generated evidence outside your project, under `~/.iter` by default. Each workspace has separate storage based on its resolved path. Set `ITER_HOME` to an absolute directory outside the workspace to override the base directory. The helper's read-only `paths --workspace <path>` command shows the exact locations before initialization. Your existing source files and referenced evidence stay in place.

The host needs write access to that workspace's `storage_root`; Iter does not fall back to writing workflow files into the project. Existing `.product-loop/` cycles need explicit `migrate`; moving a workspace uses `relocate`. See the [storage and migration guide](docs/storage.en.md). Saved authorization is reused for unchanged scope. Publishing, external communication, and destructive operations require authorization for those actions.

**Cancel or pause:** say “Cancel this iteration” to end the current cycle while keeping its evidence. Say “Pause here; I will resume later” to keep the cycle active. Cancellation does not undo code changes. One active cycle per workspace; simultaneous writers are not supported.

## Try a complete example

Follow the [Note Counter walkthrough](docs/note-counter.en.md), including input, selected scope, actual CLI results, and a one-minute replay. Share an optional [trial report](https://github.com/drl990114/Iter/issues/new?template=trial-feedback.yml).

## Documentation

- [Installation, compatibility, and troubleshooting](docs/harnesses.en.md)
- [Development and validation](docs/testing.en.md)
- [Storage, migration, and workspace moves](docs/storage.en.md)
- [Release workflow](docs/releasing.md#english)
- [Changelog](CHANGELOG.md) · [Releases](https://github.com/drl990114/Iter/releases) · [MIT license](LICENSE)
- [Skill workflow and resources](skills/iterate-product/)
