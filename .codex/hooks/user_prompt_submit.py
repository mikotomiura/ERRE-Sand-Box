#!/usr/bin/env python3
from __future__ import annotations

from _erre_common import emit_json, latest_task, read_payload, repo_root, task_status


def main() -> int:
    payload = read_payload()
    root = repo_root(payload)
    status = task_status(latest_task(root))
    task = status["task"]
    notes: list[str] = []
    if task is None:
        notes.append(
            "ERRE preflight: no recent .steering task found. Before implementation, use "
            "$erre-workflow to create requirement.md, design.md, and tasklist.md."
        )
    else:
        if status["missing"]:
            notes.append(
                f"ERRE preflight: {task.name} is missing {', '.join(status['missing'])}."
            )
        if status["template"]:
            notes.append(
                f"ERRE preflight: {task.name}/design.md still looks like the template."
            )
    if notes:
        emit_json(
            {
                "continue": True,
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": "\n".join(notes),
                },
            }
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
