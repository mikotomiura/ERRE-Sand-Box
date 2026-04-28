#!/usr/bin/env python3
from __future__ import annotations

import subprocess

from _erre_common import command_available, emit_json, read_payload, repo_root, run


def summarize(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:240]
    return "no details"


def check_command(label: str, args: list[str], root) -> str | None:
    try:
        result = run(args, cwd=root, timeout=25)
    except subprocess.TimeoutExpired:
        return f"{label} timed out."
    except OSError as exc:
        return f"{label} could not start: {exc}"
    if result.returncode == 0:
        return None
    details = summarize(result.stdout) if result.stdout.strip() else summarize(result.stderr)
    return f"{label} reported issues: {details}"


def main() -> int:
    payload = read_payload()
    root = repo_root(payload)
    warnings: list[str] = []
    if (root / "src").is_dir():
        if command_available("uv"):
            warnings.extend(
                item
                for item in (
                    check_command("ruff check", ["uv", "run", "--no-sync", "ruff", "check", "src", "tests"], root),
                    check_command("mypy", ["uv", "run", "--no-sync", "mypy", "src"], root),
                )
                if item
            )
        else:
            if command_available("ruff"):
                warning = check_command("ruff check", ["ruff", "check", "src", "tests"], root)
                if warning:
                    warnings.append(warning)
            if command_available("mypy"):
                warning = check_command("mypy", ["mypy", "src"], root)
                if warning:
                    warnings.append(warning)
    if warnings:
        emit_json({"continue": True, "systemMessage": "\n".join(warnings)})
    else:
        emit_json({"continue": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
