# Design

## Approach

Use Codex's native discovery points instead of copying the Claude Code runtime model:

- `AGENTS.md` remains the repository-level instruction entrypoint.
- `.agents/skills/` remains the Codex skill root, with a new `erre-workflow` skill for
  task lifecycle operations formerly represented by Claude slash commands.
- `.codex/config.toml`, `.codex/hooks.json`, `.codex/hooks/*.py`, and `.codex/agents/*.toml`
  provide repo-local Codex behavior once the project is trusted.

## Changed Areas

- Codex configuration and hook scripts under `.codex/`.
- Codex custom agent manifests under `.codex/agents/`.
- Codex skill discovery under `.agents/skills/`.
- Repository guidance in `AGENTS.md`.
- Task record under `.steering/20260428-codex-environment-setup/`.

## Hook Design

- `SessionStart` returns JSON additional context with branch, recent task, git dirtiness,
  and TODO counts.
- `UserPromptSubmit` returns non-blocking additional context when no recent `.steering`
  task exists or the current design is still a template.
- `PreToolUse` inspects `apply_patch` / edit tool inputs, requires a recent valid steering
  task before edits to `src/erre_sandbox/**`, and denies forbidden additions of cloud LLM
  imports, `bpy`, and `print()`.
- `Stop` runs lightweight `uv run --no-sync ruff check src tests` and `uv run --no-sync mypy src`
  checks with short timeouts and reports warnings via JSON `systemMessage`.

## Agent Design

Five project-scoped agents are enough for the current workflow: explorer, reviewer,
test runner, security checker, and impact analyzer. They are read-only except where the
role requires command execution for tests. The main agent keeps orchestration authority.

## Skill Design

`erre-workflow` is concise and instruction-only. It maps Claude slash-command workflows to
Codex-native prompts and files, preserving `.steering/` rigor without pretending that
`.claude/commands/*.md` are Codex slash commands.

## Test Strategy

- Compile hook scripts.
- Dry-run hook JSON samples for deny/pass behavior.
- Check Codex config diagnostics with `codex --debug-config`.
- Run ruff format/check, mypy, and pytest where feasible.

## Rollback

Remove `.codex/`, `.agents/skills/erre-workflow/`, and revert `AGENTS.md` plus the small
frontmatter cleanups in `.agents/skills/*/SKILL.md`. No runtime code or schema migration is
involved.
