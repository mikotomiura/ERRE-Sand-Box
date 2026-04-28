#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from _erre_common import emit_json, latest_task, read_payload, relative_path, repo_root, task_status

IMPL_PREFIX = "src/erre_sandbox/"
BANNED_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "cloud LLM API imports are forbidden in src/erre_sandbox",
        re.compile(r"^\s*(?:import\s+(?:openai|anthropic)\b|from\s+(?:openai|anthropic)\b)"),
    ),
    (
        "bpy imports are forbidden in src/erre_sandbox because Blender/GPL code is isolated",
        re.compile(r"^\s*(?:import\s+bpy\b|from\s+bpy\b)"),
    ),
    (
        "print() is forbidden in src/erre_sandbox; use logging instead",
        re.compile(r"^\s*print\s*\("),
    ),
]


def deny(reason: str) -> int:
    emit_json(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )
    return 0


def patch_targets(command: str) -> dict[str, list[str]]:
    targets: dict[str, list[str]] = {}
    current: str | None = None
    for line in command.splitlines():
        for marker in ("*** Add File: ", "*** Update File: ", "*** Delete File: "):
            if line.startswith(marker):
                current = line[len(marker) :].strip()
                targets.setdefault(current, [])
                break
        else:
            if current and line.startswith("+") and not line.startswith("+++"):
                targets[current].append(line[1:])
    return targets


def direct_targets(tool_input: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for key in ("file_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            content = tool_input.get("new_string") or tool_input.get("content") or ""
            if isinstance(content, str):
                result[value] = content.splitlines()
    edits = tool_input.get("edits")
    target = tool_input.get("file_path") or tool_input.get("path")
    if isinstance(edits, list) and isinstance(target, str):
        lines: list[str] = []
        for edit in edits:
            if isinstance(edit, dict) and isinstance(edit.get("new_string"), str):
                lines.extend(edit["new_string"].splitlines())
        result[target] = lines
    return result


def target_map(payload: dict[str, Any]) -> dict[str, list[str]]:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return {}
    command = tool_input.get("command")
    if isinstance(command, str) and "*** Begin Patch" in command:
        return patch_targets(command)
    return direct_targets(tool_input)


def is_impl_path(path: str) -> bool:
    return path.startswith(IMPL_PREFIX)


def check_banned(path: str, lines: list[str]) -> str | None:
    if not path.endswith(".py") or not is_impl_path(path):
        return None
    for line in lines:
        for label, pattern in BANNED_PATTERNS:
            if pattern.search(line):
                return f"{label}: {path}: {line.strip()}"
    return None


def main() -> int:
    payload = read_payload()
    root = repo_root(payload)
    normalized = {
        relative_path(root, path): lines for path, lines in target_map(payload).items()
    }
    if not normalized:
        return 0
    impl_targets = [path for path in normalized if is_impl_path(path)]
    if impl_targets:
        status = task_status(latest_task(root))
        if status["task"] is None:
            return deny(
                "Implementation edits require a recent .steering/YYYYMMDD-task directory "
                "with requirement.md, design.md, and tasklist.md."
            )
        if status["missing"]:
            return deny(
                f"Implementation edits require complete steering files; missing: "
                f"{', '.join(status['missing'])}."
            )
    for path, lines in normalized.items():
        violation = check_banned(path, lines)
        if violation:
            return deny(violation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
