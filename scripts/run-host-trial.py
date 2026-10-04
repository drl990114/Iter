#!/usr/bin/env python3
"""Opt-in, bounded native-host trial; never part of the offline test suite."""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=("codex", "claude"), required=True)
    parser.add_argument(
        "--executable",
        help="Optional host executable; does not change global installation",
    )
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument(
        "--skill-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "skills" / "iterate-product",
        help="Skill directory whose helper resolves storage; defaults to this checkout",
    )
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    executable = args.executable or args.host
    version = subprocess.run(
        [executable, "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    workspace = args.workspace.resolve()
    helper = args.skill_dir.resolve() / "scripts" / "product_loop.py"
    paths = json.loads(
        subprocess.run(
            [sys.executable, str(helper), "paths", "--workspace", str(workspace)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            timeout=10,
        ).stdout
    )
    if paths["migration_required"]:
        parser.error("Migrate the workspace's legacy Iter state before a native trial.")
    storage_root = Path(paths["storage_root"])
    storage_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    environment = {**os.environ, "ITER_HOME": paths["iter_home"]}
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    prompt = args.prompt_file.read_text(encoding="utf-8")
    (output / "prompt.txt").write_text(prompt, encoding="utf-8")
    if args.host == "codex":
        command = [
            executable,
            "exec",
            "--cd",
            str(workspace),
            "--skip-git-repo-check",
            "--sandbox",
            "workspace-write",
            "--add-dir",
            str(storage_root),
            "-c",
            'approval_policy="never"',
            "--ephemeral",
            "--json",
            "--output-last-message",
            str(output / "final.md"),
            "-",
        ]
    else:
        command = [
            executable,
            "--print",
            "--output-format",
            "stream-json",
            "--verbose",
            "--permission-mode",
            "acceptEdits",
            "--add-dir",
            str(storage_root),
            "--no-session-persistence",
            "--strict-mcp-config",
            "--mcp-config",
            '{"mcpServers":{}}',
            "--no-chrome",
            "--tools",
            "Bash,Read,Write,Edit,Glob,Grep,Skill",
            "--allowedTools",
            "Bash,Read,Write,Edit,Glob,Grep,Skill",
            "--max-budget-usd",
            "2",
        ]
    started = time.monotonic()
    with (
        (output / "events.jsonl").open("w", encoding="utf-8") as stdout,
        (output / "stderr.log").open("w", encoding="utf-8") as stderr,
    ):
        process = subprocess.Popen(
            command,
            cwd=workspace,
            stdin=subprocess.PIPE,
            stdout=stdout,
            stderr=stderr,
            text=True,
            encoding="utf-8",
            env=environment,
            start_new_session=os.name != "nt",
        )
        timed_out = False
        try:
            process.communicate(prompt, timeout=args.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    check=False,
                    capture_output=True,
                )
            else:
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name != "nt":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                process.wait()
    result = {
        "host": args.host,
        "version": version,
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "output": str(output),
        "storage_root": str(storage_root),
        "state_path": paths["state_path"],
        "note": "Process completion alone does not establish behavioral success. Inspect the transcript and artifacts.",
    }
    (output / "process.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result))
    if timed_out:
        raise SystemExit(124)
    if process.returncode:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
