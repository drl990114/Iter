# Installation and compatibility

[简体中文](harnesses.md) · [Current validation](validation-0.1.0.md)

Iter distributes the entire `iterate-product/` directory using the [Agent Skills standard](https://agentskills.io/specification). All hosts use the same workflow and Python helper. The first trial focuses on Codex and Claude Code; installation compatibility is separate from a successful model session.

## Install a Skill

Requires Node.js 22.20+, Git, Python 3.10+, and a host that can read/write files and run commands. Run in the target project:

```sh
npx skills add drl990114/Iter --skill iterate-product --copy
```

Choose your host in the prompts. For explicit project installation:

```sh
npx skills add drl990114/Iter --skill iterate-product --agent codex --copy
npx skills add drl990114/Iter --skill iterate-product --agent claude-code --copy
```

Select several hosts in one command with `--agent codex claude-code`. Keep `--copy`: the tested installer's default symlink mode can skip a missing host directory in a fresh project when several distinct host roots are selected. User-facing commands follow [vercel-labs/skills](https://github.com/vercel-labs/skills) without pinning the CLI version. Installation regression tests pin `skills@1.5.23` for reproducibility.

Before the repository is public, use an accessible local checkout or authenticated repository access. The remote command installs the remote revision, not local changes. For reproducibility after release, use the GitHub URL with `/tree/v0.1.0` as the source. The tag must exist first.

Start a new host session. In Codex use `$iterate-product`; in Claude Code use `/iterate-product`. Natural-language requests mentioning `iterate-product` also work when supported by the host. The helper generates English or Chinese reports according to the selected language. Old Chinese cycles continue unchanged.

## Directories

Paths below are project roots; append `iterate-product/` and keep all resources, including `LICENSE.txt`.

| Host | Project root | Basis / evidence |
|---|---|---|
| Codex | `.agents/skills` | [Official skills guide](https://learn.chatgpt.com/docs/build-skills); installer tested |
| Claude Code | `.claude/skills` | [Official skills guide](https://code.claude.com/docs/en/skills); installer tested |
| Cursor | `.agents/skills` | [Official guide](https://prod.cursor.com/docs/skills); installer tested |
| GitHub Copilot | `.agents/skills` | [Official guide](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills); installer tested |
| Gemini CLI | `.agents/skills` | [Official guide](https://geminicli.com/docs/cli/skills/); installer tested |
| OpenCode | `.agents/skills` | [Official guide](https://opencode.ai/docs/skills/); installer tested |
| Windsurf / Cascade | `.windsurf/skills` | [Official guide](https://docs.devin.ai/desktop/cascade/skills); installer tested with copy mode |
| Cline | `.cline/skills` | [Official guide](https://docs.cline.bot/customization/skills); manual installation |
| DeepSeek Harness | `.dsh/skills` or `.agents/skills` | [Official filesystem provider](https://github.com/deepseek-ai/deepseek-harness/blob/76fda729799fe9b3848dbe2c211d4b231032b81e/packages/skill/skill-filesystem/README.md); adapter tests |

Directory references were checked September 4, 2026. Host versions can change their discovery rules. Check the installed path and the host's own skill list rather than assuming installer success proves discovery.

Personal installation adds `--global`. In the pinned installer, Codex defaults to `~/.codex/skills` and Claude Code to `~/.claude/skills`. Codex's documented shared personal directory is `~/.agents/skills`. `CODEX_HOME` and `CLAUDE_CONFIG_DIR` can affect discovery. If a skill is missing, inspect the installer output and move the complete directory to the host's documented location; remove duplicate old copies and start a new session.

## Manual and Windows installation

Without Node, copy `skills/iterate-product/` from an accessible checkout into the host root. Python and shell access are still required. Copying only `SKILL.md` is insufficient.

For a new Codex project installation in PowerShell:

```powershell
$iterSource = 'C:\path\to\Iter\skills\iterate-product'
$iterTarget = Join-Path (Get-Location) '.agents\skills\iterate-product'
if (Test-Path $iterTarget) { throw 'Inspect the existing installation before replacing it.' }
New-Item -ItemType Directory -Force (Split-Path $iterTarget) | Out-Null
Copy-Item -Recurse $iterSource $iterTarget
py -3 "$iterTarget\scripts\product_loop.py" --help
```

For Claude, use `.claude\skills\iterate-product`. The Skills CLI commands also work in PowerShell. WSL uses its own installation and home directories. Prefer workspace-relative evidence paths when sharing reports between operating systems.

## Native plugins

The repository has Codex and Claude plugin manifests but no public marketplace catalog. The Skill directory installation above is the primary trial path.

Claude can load an accessible checkout for one launch:

```sh
claude --plugin-dir /absolute/path/to/Iter
```

Then call `/iter:iterate-product`. See the [official plugin guide](https://code.claude.com/docs/en/plugins). Persistent installation needs a separately configured marketplace; do not assume adding this repository directly as a marketplace works.

For Codex, register the checkout in a local marketplace according to the [official packaging guide](https://developers.openai.com/plugins/build/plugins). Detailed local marketplace examples for both hosts are in the [Chinese guide](harnesses.md#原生插件安装). No global marketplace configuration is changed by Iter's tests.

DeepSeek can use the directory installation or its official plugin loader:

```sh
dsh plugin --profile web add 'file:/absolute/path/to/Iter'
```

Choose your existing profile. The adapter registers an independent provider and preserves the default provider. A complete DSH CLI/profile session is not implied by adapter tests. Do not run `npm install iter`: the npm package with that name belongs to another project.

## Migration

Keep `.product-loop/` and any evidence files. Install `iterate-product` first, remove the old `run-product-loop` through its original installer and scope, then start a new session. For a project installed with Skills CLI in Codex:

```sh
npx skills add drl990114/Iter --skill iterate-product --agent codex --copy
npx skills remove run-product-loop
```

The removal above targets only the old skill name across this project's hosts. Use it when migrating all project copies: `.agents/skills` can be shared, so removing only for Codex may retain a copy used by another detected host. Do not use `remove --all`, which selects unrelated skills. For a global installation add `--global` to the matching commands. Use the native plugin manager for plugin installations; do not delete plugin caches manually. Inspect local edits before replacing an installed skill. After upgrading, run the loaded helper's `status` against the existing workspace. Missing `language` is interpreted as Chinese; existing grants and evidence are preserved.

## Update, remove, and diagnose

Use the same installer and scope as the initial installation:

```sh
npx skills list --agent codex
npx skills update iterate-product
npx skills remove iterate-product --agent codex
```

Inspect the update's scope prompt. Native plugin updates require both a refreshed source and a new version in the installed cache. For local Claude development, a fresh `--plugin-dir` launch reads the supplied checkout. Codex marketplace refresh and installation commands depend on CLI version; check `codex plugin --help` and the official guide.

| Symptom | Action |
|---|---|
| Remote repository is unavailable | Confirm repository access or use the local candidate source; public trial starts after publication |
| Installed but not discovered | Check host directory, workspace, scope, version, and restart the session |
| Old or duplicated skill name | Inspect project, personal, and plugin copies; remove the old installation through its manager |
| Helper/template missing | Copy the whole skill directory |
| Python missing | Check Python 3.10+ in the host's actual shell; Windows may use `py -3` |
| Model rejects CLI version | Use a compatible CLI; a model/API failure does not establish skill behavior |
| Report cannot complete | Run `validate`; retain actual evidence and use the saved report language |
| User wants to cancel | Say so; the agent records `stop`, without approving implementation |

See [testing](testing.en.md) and [current validation](validation-0.1.0.md) for what has actually been checked.
