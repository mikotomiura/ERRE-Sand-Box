# Codex environment setup

## Background

ERRE-Sandbox already has Claude Code oriented assets under `.claude/`, and Codex-oriented
project guidance in `AGENTS.md` plus mirrored skills under `.agents/skills/`. The current
Codex setup is still incomplete because repo-local Codex config, Codex hook wiring, Codex
custom agent manifests, and a Codex-native workflow entrypoint are missing.

## Goal

Make Codex usable as a first-class implementation partner in this repository by adding
repo-local `.codex/` configuration, hook guardrails, custom agent definitions, and a single
`$erre-workflow` skill that replaces Claude slash-command execution for Codex sessions.

## Scope

- Add `.codex/config.toml`, `.codex/hooks.json`, `.codex/hooks/*.py`, and
  `.codex/agents/*.toml`.
- Add `.agents/skills/erre-workflow/SKILL.md`.
- Lighten existing `.agents/skills/*/SKILL.md` frontmatter for Codex discovery and replace
  Claude-only references where needed.
- Update `AGENTS.md` so Codex entrypoints are explicit.

## Out Of Scope

- Do not change `~/.codex/` user-level configuration.
- Do not delete or rename `.claude/`.
- Do not change runtime Python/Godot public APIs, schemas, or dependencies.
- Do not create commits unless the user asks.

## Acceptance Criteria

- [x] `.codex/config.toml` enables Codex hooks and sets the repo-local model/agent defaults.
- [x] `.codex/hooks.json` wires SessionStart, UserPromptSubmit, PreToolUse, and Stop hooks.
- [x] Hook scripts compile with `python3 -m py_compile .codex/hooks/*.py`.
- [x] PreToolUse dry-runs deny forbidden imports in `src/erre_sandbox/**` and allow
      out-of-scope Blender `bpy` usage.
- [x] Five Codex custom agents are available under `.codex/agents/`.
- [x] `$erre-workflow` is available under `.agents/skills/erre-workflow/`.
- [x] Existing `.agents/skills` frontmatter is Codex-friendly.
- [x] `AGENTS.md` names Codex-native entrypoints instead of treating `.claude/commands` as
      executable Codex slash commands.

## Operational Notes

- `/reimagine` equivalent was handled in the approved plan before implementation.
- Custom subagents are configured, but Codex should spawn them only when the user explicitly
  requests delegation or parallel agent work.
