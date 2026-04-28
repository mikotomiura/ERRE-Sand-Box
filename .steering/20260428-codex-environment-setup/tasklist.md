# Tasklist

## Setup

- [x] Read relevant project docs and existing Claude/Codex assets.
- [x] Create `.steering/20260428-codex-environment-setup/` records.

## Implementation

- [x] Add repo-local `.codex/config.toml`.
- [x] Add Codex hook wiring and hook scripts.
- [x] Add Codex custom agent TOML files.
- [x] Add `$erre-workflow` skill.
- [x] Lighten existing `.agents/skills` frontmatter and Claude-only references.
- [x] Update `AGENTS.md` to name Codex-native entrypoints.

## Verification

- [x] Compile hook scripts.
- [x] Dry-run PreToolUse hook scenarios.
- [x] Run Codex config diagnostics or local equivalent.
- [x] Run `uv run ruff check src tests`.
- [x] Run `uv run ruff format --check src tests`.
- [x] Run `uv run mypy src`.
- [x] Run `uv run pytest` with clean process exit. (Resolved by PR #113 ci-pipeline-setup; see blockers.md.)

## Finish

- [x] Review final diff.
- [x] Record remaining limitations if any.
