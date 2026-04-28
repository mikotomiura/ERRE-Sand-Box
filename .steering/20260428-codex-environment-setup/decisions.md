# Decisions

## D1. Repo-local Codex setup only

- **Decision**: Add `.codex/` inside the repository and leave `~/.codex/` untouched.
- **Reason**: The setup should travel with ERRE-Sandbox and avoid changing the user's global
  Codex behavior across unrelated repositories.

## D2. Claude assets remain canonical for Claude only

- **Decision**: Keep `.claude/` intact and treat it as a migration/reference source for Codex.
- **Reason**: Deleting or renaming it would break existing Claude Code workflows. Codex has
  different native discovery paths, so direct reuse would be misleading.

## D3. One workflow skill instead of pseudo slash commands

- **Decision**: Add `$erre-workflow` rather than `.codex/commands`.
- **Reason**: Current Codex app/CLI exposes built-in slash commands and skills, while reusable
  repo workflows are best represented as skills under `.agents/skills`.

## D4. Hooks are guardrails, not enforcement boundaries

- **Decision**: Implement deterministic hook checks but keep review/test workflow as the final
  safety net.
- **Reason**: Codex hooks can intercept supported tool paths, but official behavior treats them
  as guardrails rather than complete security boundaries.
