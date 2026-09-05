# Completed Note Counter example

This is the implementation produced by the Chinese Codex 0.153.1 native trial on September 5, 2026. The unchanged [starter](../note-counter) is available for fresh trials. Both are MIT licensed under the repository license.

```sh
python3 count_notes.py /path/to/notes
python3 count_notes.py --recursive /path/to/notes
```

Default behavior counts only immediate files ending in lowercase `.md`. `--recursive` also visits nested directories. `.txt` files and directories named `*.md` are excluded. Empty directories print `0`. No additional Python packages are required.

Read the [English walkthrough](../../docs/note-counter.en.md) or [中文案例](../../docs/note-counter.zh-CN.md). Local scenarios passed; real-user value remains unvalidated. Large-tree performance, ignore patterns, cross-platform traversal differences, and improved error messages were outside this selected scope.
