#!/usr/bin/env python3
from __future__ import annotations

from _erre_common import emit_json, latest_task, read_payload, repo_root, run, task_status


def first_line(text: str) -> str:
    return text.strip().splitlines()[0] if text.strip() else "N/A"


def count_todos(root) -> str:
    try:
        result = run(["rg", "-n", "TODO|FIXME|HACK", "src", "tests"], cwd=root, timeout=5)
    except Exception:
        return "unknown"
    if result.returncode not in (0, 1):
        return "unknown"
    return str(len([line for line in result.stdout.splitlines() if line.strip()]))


def main() -> int:
    payload = read_payload()
    root = repo_root(payload)
    branch = first_line(run(["git", "branch", "--show-current"], cwd=root).stdout)
    last_commit = first_line(run(["git", "log", "-1", "--oneline"], cwd=root).stdout)
    dirty = len([line for line in run(["git", "status", "--short"], cwd=root).stdout.splitlines() if line.strip()])
    status = task_status(latest_task(root))
    task = status["task"]
    task_name = task.name if task else "NONE"
    file_count = 3 - len(status["missing"])
    template_note = " template-design" if status["template"] else ""
    missing_note = f" missing={','.join(status['missing'])}" if status["missing"] else ""
    context = "\n".join(
        [
            "ERRE Codex context:",
            f"- branch: {branch}",
            f"- last_commit: {last_commit}",
            f"- git_dirty_files: {dirty}",
            f"- active_task: {task_name} ({file_count}/3){template_note}{missing_note}",
            f"- todo_markers: {count_todos(root)}",
            "- workflow: use $erre-workflow for task start/design/review/finish flows.",
        ]
    )
    emit_json(
        {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            },
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
