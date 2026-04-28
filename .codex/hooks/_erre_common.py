from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

TASK_RE = re.compile(r"^\d{8}-")
DESIGN_TEMPLATE_MARKERS = ("path/to/file1.py", "path/to/new_file.py")


def read_payload() -> dict[str, Any]:
    raw = ""
    try:
        raw = os.read(0, 1_000_000).decode("utf-8", errors="replace")
    except OSError:
        return {}
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def run(args: list[str], *, cwd: Path | None = None, timeout: int = 5) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def repo_root(payload: dict[str, Any] | None = None) -> Path:
    cwd_value = (payload or {}).get("cwd")
    cwd = Path(cwd_value).expanduser() if isinstance(cwd_value, str) and cwd_value else Path.cwd()
    try:
        result = run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    except (OSError, subprocess.SubprocessError):
        return cwd
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip())
    return cwd


def latest_task(root: Path, *, days: int = 8) -> Path | None:
    steering = root / ".steering"
    if not steering.is_dir():
        return None
    cutoff = dt.datetime.now().timestamp() - (days * 24 * 60 * 60)
    candidates = []
    for item in steering.iterdir():
        if not item.is_dir() or not TASK_RE.match(item.name):
            continue
        try:
            modified = item.stat().st_mtime
        except OSError:
            continue
        if modified >= cutoff:
            candidates.append((modified, item))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def task_status(task: Path | None) -> dict[str, Any]:
    if task is None:
        return {"task": None, "missing": ["requirement.md", "design.md", "tasklist.md"], "template": False}
    missing = [name for name in ("requirement.md", "design.md", "tasklist.md") if not (task / name).is_file()]
    template = False
    design = task / "design.md"
    if design.is_file():
        try:
            text = design.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        template = any(marker in text for marker in DESIGN_TEMPLATE_MARKERS)
    return {"task": task, "missing": missing, "template": template}


def relative_path(root: Path, value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()
    return path.as_posix().lstrip("./")


def emit_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def command_available(name: str) -> bool:
    return shutil.which(name) is not None
