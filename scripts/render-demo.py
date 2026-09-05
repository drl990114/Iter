#!/usr/bin/env python3
"""Render a 60-second evidence replay, not a recording of a host UI.

Developer-only dependencies: Pillow 11.3.0 and ffmpeg with libx264.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]


def scenes(language: str, evidence: dict) -> list[tuple]:
    before = evidence["summary"]["before"]["passed"]
    after = evidence["summary"]["after"]["passed"]
    total = evidence["summary"]["after"]["total"]
    checks = [item for item in evidence["observations"] if item["revision"] == "after"]
    outputs = {item["scenario"]: item["stdout"].strip() for item in checks}
    if language == "en":
        return [
            (
                "Choose a useful next step",
                [
                    "A tiny Python note counter.",
                    "A concrete, bounded improvement.",
                    "Start with the code you have.",
                ],
                "THE REQUEST",
                [
                    "Suggest 2-3 improvements.",
                    "Explain scope and acceptance.",
                    "Wait for my selection.",
                ],
            ),
            (
                "Keep the choice yours",
                [
                    "Three options, with tradeoffs.",
                    "The user chooses recursion.",
                    "Default behavior stays the same.",
                ],
                "OBSERVED OPTIONS",
                [
                    "01  Clear directory errors",
                    "02  Optional --recursive  <--",
                    "03  Case-insensitive .md",
                    "",
                    "Scope: CLI + focused tests",
                ],
            ),
            (
                "Save approval. Resume later.",
                [
                    "Implementation permission saved.",
                    "Isolated test permission saved.",
                    "The paused cycle stays active.",
                ],
                "OBSERVED PAUSE STATE",
                [
                    "stage: research",
                    "language: en",
                    "implementation: granted",
                    "local scenarios: granted",
                    "product code: unchanged",
                ],
            ),
            (
                "Make the approved change",
                [
                    "Use Python's standard library.",
                    "Keep immediate-only as default.",
                    "Add recursion behind a flag.",
                ],
                "COMPLETED IMPLEMENTATION",
                [
                    "parser.add_argument(",
                    '    "--recursive",',
                    '    action="store_true"',
                    ")",
                    'args.directory.rglob("*.md")',
                ],
            ),
            (
                "Run the actual CLI",
                [
                    f"Before: {before}/{total} scenario groups pass.",
                    f"After: {after}/{total} scenario groups pass.",
                    "Six calls per revision; logs kept.",
                ],
                "INDEPENDENT CLI REPLAY",
                [
                    f"default       -> {outputs['default']}     PASS",
                    f"--recursive   -> {outputs['recursive']}     PASS",
                    f"exclude .txt  -> {outputs['exclude']}     PASS",
                    f"empty         -> {outputs['empty']}     PASS",
                    "synthetic fixtures removed",
                ],
            ),
            (
                "Show what the evidence proves",
                [
                    "Local scenarios passed.",
                    "Real-user value is unvalidated.",
                    "Try one disposable project next.",
                ],
                "SMALL PUBLIC TRIAL / CANDIDATE",
                [
                    "Saved scope + approval",
                    "Resumable workflow",
                    "Inspectable CLI evidence",
                    "",
                    f"Iter {VERSION} / MIT",
                ],
            ),
        ]
    return [
        (
            "选一个值得做的下一步",
            [
                "从一个小型 Python 笔记计数器开始。",
                "把改进范围写具体。",
                "先看项目已有的代码和证据。",
            ],
            "原始请求",
            ["给出 2–3 个改进建议。", "说明范围与验收标准。", "等待我选择。"],
        ),
        (
            "把选择权留给你",
            [
                "三个选项，说明各自取舍。",
                "用户选择可选递归统计。",
                "保留原来的默认行为。",
            ],
            "实际给出的选项",
            [
                "01  改善目录错误提示",
                "02  可选 --recursive   ← 选定",
                "03  扩展名忽略大小写",
                "",
                "范围：CLI + 针对性测试",
            ],
        ),
        (
            "记录授权，中断后继续",
            ["实现范围已授权。", "隔离的本机场景已授权。", "暂停时保留活动周期。"],
            "英文会话的实际暂停状态",
            [
                "阶段：research",
                "报告语言：en",
                "实现授权：granted",
                "本机验证授权：granted",
                "产品代码：尚未修改",
            ],
        ),
        (
            "完成批准的改动",
            ["复用 Python 标准库。", "默认只统计第一层。", "通过参数开启递归。"],
            "实际完成的实现",
            [
                "parser.add_argument(",
                '    "--recursive",',
                '    action="store_true"',
                ")",
                'args.directory.rglob("*.md")',
            ],
        ),
        (
            "运行真实 CLI，保留证据",
            [
                f"改动前：{before}/{total} 组场景通过。",
                f"改动后：{after}/{total} 组场景通过。",
                "每个版本调用六次 CLI，保留日志。",
            ],
            "独立 CLI 复验",
            [
                f"默认统计      → {outputs['default']}     通过",
                f"递归统计      → {outputs['recursive']}     通过",
                f"排除 .txt     → {outputs['exclude']}     通过",
                f"空目录        → {outputs['empty']}     通过",
                "合成数据已清理",
            ],
        ),
        (
            "说清证据能证明什么",
            [
                "本机场景验证通过。",
                "真实用户价值待验证。",
                "下一步：在一次性项目里试一轮。",
            ],
            "小范围试用 / 候选版",
            [
                "记录范围与授权",
                "支持中断恢复",
                "CLI 结果可核验",
                "",
                f"Iter {VERSION} / MIT",
            ],
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=["en", "zh-CN"], required=True)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument(
        "--evidence", type=Path, default=ROOT / "docs/demo/evidence/evidence.json"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    for source in evidence["sources"].values():
        actual = hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest()
        if source["sha256"] != actual:
            raise SystemExit("Evidence is stale; rerun the CLI replay first.")
    if not all(evidence["summary"]["after"]["scenarios"].values()):
        raise SystemExit("Do not render a success replay from failing evidence.")
    args.output.mkdir(parents=True, exist_ok=True)
    video = args.output / f"iter-note-counter.{args.language}.mp4"
    poster = args.output / f"iter-note-counter.{args.language}.png"
    if video.exists() or poster.exists():
        raise SystemExit("Output already exists; choose a new directory.")

    def font(size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(args.font), size)

    with tempfile.TemporaryDirectory(prefix="iter-demo-frames-") as directory:
        frames = Path(directory)
        for index, (title, lines, label, code) in enumerate(
            scenes(args.language, evidence)
        ):
            canvas = Image.new("RGB", (1280, 720), "#101512")
            draw = ImageDraw.Draw(canvas)
            draw.text((64, 38), "Iter", font=font(32), fill="#d8edce")
            draw.text((158, 50), VERSION, font=font(17), fill="#7f9384")
            badge = (
                "CLI evidence replay · 60 seconds"
                if args.language == "en"
                else "CLI 证据回放 · 60 秒"
            )
            draw.text((810, 48), badge, font=font(18), fill="#a8b9ab")
            draw.line((64, 104, 1216, 104), fill="#2c382f", width=1)
            draw.text((64, 140), f"0{index + 1} / 06", font=font(22), fill="#8dbb76")
            # Explicit line breaks keep both languages legible at video resolution.
            title_lines = [title]
            if draw.textlength(title, font=font(32)) > 520:
                words = title.split()
                split = len(words) // 2
                title_lines = [" ".join(words[:split]), " ".join(words[split:])]
            for n, line in enumerate(title_lines):
                draw.text((64, 200 + n * 43), line, font=font(32), fill="#f3f5ef")
            for n, line in enumerate(lines):
                draw.text((64, 335 + n * 52), line, font=font(23), fill="#b3c1b5")
            draw.rounded_rectangle(
                (664, 155, 1216, 556), radius=18, fill="#1b241e", outline="#3c4e40"
            )
            draw.text((694, 179), label, font=font(17), fill="#8dbb76")
            draw.line((694, 215, 1186, 215), fill="#39473d")
            for n, line in enumerate(code):
                draw.text((694, 248 + n * 46), line, font=font(22), fill="#e1e9df")
            footer = (
                "Recorded observations, presented as a replay. No host UI is simulated."
                if args.language == "en"
                else "基于实际记录制作的回放；不模拟宿主界面。"
            )
            draw.text((64, 596), footer, font=font(17), fill="#819686")
            for step in range(6):
                x = 64 + step * 195
                draw.rounded_rectangle(
                    (x, 651, x + 177, 657),
                    radius=3,
                    fill="#a4cf8c" if step <= index else "#2e3b32",
                )
            canvas.save(frames / f"frame-{index:02d}.png")
        shutil.copy2(frames / "frame-04.png", poster)
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-framerate",
                "1/10",
                "-i",
                str(frames / "frame-%02d.png"),
                "-vf",
                "fps=24",
                "-t",
                "60",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(video),
            ],
            check=True,
        )
    print(video)


if __name__ == "__main__":
    main()
