#!/usr/bin/env python3
"""Re-run the published Note Counter example with isolated synthetic fixtures."""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True, help="New evidence directory"
    )
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    observations = []
    sources = {
        "before": ROOT / "examples/note-counter/count_notes.py",
        "after": ROOT / "examples/note-counter-completed/count_notes.py",
    }
    with tempfile.TemporaryDirectory(
        prefix="synthetic notes ", dir=output
    ) as directory:
        fixtures = Path(directory)
        for name in ["tree", "non-markdown", "empty"]:
            (fixtures / name).mkdir()
        for name in ["a.md", "b.md", "nested/c.md", "nested/deep/d.md", "skip.txt"]:
            path = fixtures / "tree" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Synthetic fixture only.\n", encoding="utf-8")
        (fixtures / "non-markdown/skip.txt").write_text("Synthetic text.\n")
        (fixtures / "non-markdown/skip.MD").write_text("Exact lowercase matching.\n")
        (fixtures / "non-markdown/folder.md").mkdir()
        cases = [
            ("default", "tree", False, "2"),
            ("recursive", "tree", True, "4"),
            ("exclude", "non-markdown", False, "0"),
            ("exclude", "non-markdown", True, "0"),
            ("empty", "empty", False, "0"),
            ("empty", "empty", True, "0"),
        ]
        for revision, source in sources.items():
            for scenario, fixture, recursive, expected in cases:
                arguments = ["--recursive"] if recursive else []
                result = subprocess.run(
                    [sys.executable, str(source), *arguments, str(fixtures / fixture)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                # Retain outputs and exit status while removing machine-specific paths.
                stderr = result.stderr.replace(str(source), "count_notes.py").replace(
                    str(fixtures), "<fixtures>"
                )
                observations.append(
                    {
                        "revision": revision,
                        "scenario": scenario,
                        "command": " ".join(
                            [
                                "python3",
                                "count_notes.py",
                                *arguments,
                                f"<fixtures>/{fixture}",
                            ]
                        ),
                        "expected": expected,
                        "exit_code": result.returncode,
                        "stdout": result.stdout,
                        "stderr": stderr,
                        "passed": result.returncode == 0
                        and result.stdout.strip() == expected,
                    }
                )
    summaries = {}
    for revision in sources:
        results = {}
        for scenario in ["default", "recursive", "exclude", "empty"]:
            results[scenario] = all(
                item["passed"]
                for item in observations
                if item["revision"] == revision and item["scenario"] == scenario
            )
        summaries[revision] = {
            "scenarios": results,
            "passed": sum(results.values()),
            "total": len(results),
        }
    evidence = {
        "schema_version": 1,
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": "independent_cli_replay",
        "python": platform.python_version(),
        "os": platform.system(),
        "sources": {
            revision: {
                "path": source.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
            for revision, source in sources.items()
        },
        "summary": summaries,
        "observations": observations,
        "synthetic_fixtures_removed": not fixtures.exists(),
        "limitation": "Local scenarios passed; real-user value remains unvalidated.",
    }
    (output / "evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    transcript = []
    for item in observations:
        transcript.extend(
            [
                f"[{item['revision']} / {item['scenario']}] $ {item['command']}",
                f"exit={item['exit_code']}; expected={item['expected']}",
                item["stdout"].rstrip(),
                item["stderr"].rstrip(),
                "",
            ]
        )
    (output / "transcript.txt").write_text("\n".join(transcript), encoding="utf-8")
    print(json.dumps(summaries, indent=2))
    if summaries["after"]["passed"] != summaries["after"]["total"]:
        raise SystemExit("The completed example failed a local scenario.")


if __name__ == "__main__":
    main()
