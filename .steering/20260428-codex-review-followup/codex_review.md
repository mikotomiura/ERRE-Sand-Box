# Codex Review Report

Date: 2026-04-28
Repository: ERRE-Sandbox
Reviewer: Codex

## Scope

This review covered the repository architecture, documentation, Python source code, Godot scripts, tests, and project configuration.

Primary references:

- `docs/architecture.md`
- `docs/functional-design.md`
- `docs/repository-structure.md`
- `docs/development-guidelines.md`
- `docs/glossary.md`
- `README.md`
- `pyproject.toml`
- `src/erre_sandbox/`
- `godot_project/`
- `tests/`

No source files were changed during the review. This file records the findings so another coding agent, such as Claude Code, can use them as repair input.

## Verification Summary

The documented verification path is not currently green.

Commands attempted:

- `uv run ruff check`
- `uv run mypy src`
- `uv run pytest`

In the Codex sandbox, `uv run ...` could not access the local uv cache under `~/.cache/uv`, so equivalent `.venv/bin/...` commands were used for validation.

Observed results:

- `.venv/bin/ruff check` failed with 78 errors.
- `.venv/bin/ruff check src tests` failed with 18 errors.
- `.venv/bin/ruff format --check src tests` reported 8 files that would be reformatted.
- `.venv/bin/mypy src` failed with 7 errors.
- `.venv/bin/pytest` collected 1065 tests and finished with `1025 passed`, `28 skipped`, `12 failed`, and `1 error`.

The pytest failures were concentrated around Godot headless execution. The Python-side test suite otherwise appears broad and mostly healthy.

## Findings

### Finding 1: [P1] Timeout close uses stale tick

Location:

- `src/erre_sandbox/integration/dialog.py:214-225`
- Related close path: `src/erre_sandbox/integration/dialog.py:284-291`

Problem:

`_close_timed_out()` closes a dialog without passing the current world tick. `close_dialog()` then emits the `dialog_close` envelope using `dialog.last_activity_tick` and records the cooldown from that same stale tick.

Impact:

- A timeout that occurs at a later tick is reported as if it happened at the last activity tick.
- Dialog observers receive misleading event timing.
- Reopen cooldown is shortened relative to the real close time.

Observed reproduction:

After advancing the scheduler beyond the timeout threshold, the close envelope was emitted at tick `0` rather than the actual timeout tick:

```text
[('dialog_initiate', 0, None), ('dialog_close', 0, 'timeout')]
```

Suggested repair:

- Pass the current tick into the timeout close path.
- Ensure both the emitted `dialog_close` envelope and `_last_close_tick` use the actual close tick.
- Consider adding an internal helper such as `_close_dialog_at(dialog_id, reason, tick)`.

Acceptance criteria:

- A timeout close envelope uses the tick at which timeout processing runs.
- Cooldown is measured from the actual close tick.
- Add or update a test that advances beyond `TIMEOUT_TICKS` and asserts the close tick is current, not `last_activity_tick`.

### Finding 2: [P1] Verification commands are not currently green

Location:

- `README.md:56-60`

Problem:

The README documents `ruff check`, `mypy src`, and `pytest` as the standard verification path, but the repository does not currently pass that path.

Impact:

- Routine validation cannot be trusted as a release gate.
- Future agents cannot distinguish newly introduced regressions from pre-existing failures.
- CI setup, if added later, would fail immediately unless the command set or codebase is corrected.

Suggested repair:

- Decide the intended verification target: all repository files, or only `src` and `tests`.
- Fix existing lint, format, mypy, and test failures for that target.
- Update README if the intended command is narrower than the current documented command.
- Add CI once the commands are green.

Acceptance criteria:

- The documented verification commands pass locally.
- The README commands and `pyproject.toml` configuration describe the same verification boundary.
- Test failures caused by optional external tools, such as Godot, skip cleanly or run reliably.

### Finding 3: [P2] Ruff target includes non-runtime workspaces

Location:

- `pyproject.toml:76-80`

Problem:

`ruff check` with no arguments scans `.steering/` and `erre-sandbox-blender/`, producing many failures outside the main runtime package. The current `src = ["src", "tests"]` configuration does not limit the files linted by the CLI.

Impact:

- The documented `ruff check` command fails before checking only the intended runtime/test code.
- GPL-separated Blender tooling and steering artifacts are mixed into the main package lint target.
- Developers and agents receive noisy feedback that obscures real package issues.

Suggested repair:

Choose one of these approaches:

1. Keep `ruff check` as the documented command and add appropriate `extend-exclude` entries.
2. Change the documented command to `ruff check src tests` and keep non-runtime folders outside the standard gate.
3. Add separate lint commands for main package, tests, Blender package, and steering scripts if all are intended to be maintained.

Acceptance criteria:

- The documented ruff command passes after formatting/lint fixes.
- `.steering/` artifacts are not accidentally part of the main runtime quality gate unless explicitly intended.
- `erre-sandbox-blender/` remains clearly separated from `src/erre_sandbox/`.

### Finding 4: [P2] Godot tests crash instead of skipping cleanly

Location:

- `tests/test_godot_project.py:57-64`
- Shared helper: `tests/_godot_helpers.py:21-30`

Problem:

The Godot tests invoke the Godot binary directly once it is found. In the observed environment, Godot crashed while trying to open `user://logs/godot...log` during headless startup.

Impact:

- A machine without Godot skips these tests, but a machine with Godot installed can fail the full pytest suite.
- Optional integration coverage becomes less reliable than a clean skip.
- Full-suite validation is blocked by environment-specific Godot behavior.

Suggested repair:

- Add a shared Godot launch helper instead of invoking `subprocess.run(...)` directly in each test.
- Force a repo-local writable user data or log directory if supported by the installed Godot version.
- Detect known headless startup/logging crashes and skip with a clear message when Godot cannot run reliably.
- Keep direct Godot failures visible when the project itself fails after a successful engine boot.

Acceptance criteria:

- Full pytest passes or cleanly skips Godot tests on a machine where Godot cannot open its log directory.
- Godot tests still fail when the actual project boot or script behavior is wrong.
- Godot subprocess invocation is centralized in one helper.

### Finding 5: [P2] UI imports integration layer

Location:

- `src/erre_sandbox/ui/dashboard/state.py:27`
- Related package initializer: `src/erre_sandbox/integration/__init__.py:32-35`

Problem:

The dashboard state module imports `M2_THRESHOLDS` and `Thresholds` from `erre_sandbox.integration`. That package initializer also imports gateway/dialog/server-facing objects, pulling integration-layer dependencies into UI state code.

Impact:

- This violates the documented architecture boundary where `ui/` should depend on `schemas.py` only.
- Dashboard state becomes coupled to FastAPI/integration internals.
- Future changes to gateway or dialog code can affect dashboard imports unexpectedly.

Suggested repair:

- Move shared threshold definitions to a lightweight contract module, such as `schemas.py` or a dedicated constants module that is allowed by the architecture rules.
- Update dashboard code to import from that boundary-safe location.
- Avoid importing from `erre_sandbox.integration` at package level from UI code.

Acceptance criteria:

- `src/erre_sandbox/ui/` no longer imports `erre_sandbox.integration`.
- Architecture dependency checks, manual or automated, show `ui -> schemas/contracts` rather than `ui -> integration`.
- Existing dashboard behavior remains unchanged.

### Finding 6: [P3] Frame byte limit checks characters

Location:

- `src/erre_sandbox/integration/gateway.py:367-371`
- Limit definition: `src/erre_sandbox/integration/gateway.py:71-77`

Problem:

`_MAX_RAW_FRAME_BYTES` is documented and named as a byte limit, but the implementation checks `len(raw)` on a Python string. For non-ASCII input, character count and byte count differ.

Impact:

- UTF-8 payloads can exceed the intended byte budget and still be accepted.
- The gateway's raw-frame size defense is weaker than its name and comments imply.

Suggested repair:

- Enforce the limit using byte length, for example `len(raw.encode("utf-8"))`.
- Alternatively receive bytes and enforce the limit before decoding if the WebSocket framework allows it cleanly.
- Add a regression test using multibyte characters.

Acceptance criteria:

- ASCII and non-ASCII frames are both constrained by actual byte length.
- Oversized multibyte payloads are rejected before JSON parsing.
- Existing valid frame behavior is unchanged.

## Additional Architecture Notes

Positive observations:

- No `bpy` import was found under `src/erre_sandbox/`, which preserves the GPL separation rule.
- No mandatory cloud LLM API import was found in the runtime package.
- The broad architecture is coherent: `schemas.py` acts as a contract boundary, `bootstrap.py` is the composition root, and memory, inference, cognition, world, and integration concerns are mostly separated.
- Test coverage is substantial, with over a thousand tests collected.

Potential follow-up:

- `src/erre_sandbox/evidence/metrics.py` and `src/erre_sandbox/evidence/scaling_metrics.py` import `CognitionCycle` only to read `DEFAULT_TICK_SECONDS`. This pulls more runtime graph into evidence tooling than necessary. Consider moving that constant to a lighter contract or constants module if architecture cleanup continues.
- `docs/repository-structure.md` mentions `.github/workflows/ci.yml`, but no `.github` workflow file was present during review. If CI is expected, add it after the local verification path is green.

## Suggested Repair Order For Claude Code

1. Fix `DialogScheduler` timeout close tick handling and add a regression test.
2. Restore a reliable verification target: ruff, format, mypy, pytest.
3. Centralize Godot subprocess execution and make Godot tests skip cleanly when the engine cannot boot headlessly.
4. Remove the UI dependency on `erre_sandbox.integration`.
5. Enforce gateway frame limits using byte length and add a multibyte payload test.
6. Add or restore CI only after the local verification path passes.

## Recommended Prompt For Claude Code

```text
Read codex_review.md carefully. Fix the findings in priority order without broad refactors.

Constraints:
- Preserve the documented architecture boundaries.
- Do not introduce cloud LLM API dependencies.
- Do not import GPL/Blender code into src/erre_sandbox.
- Keep changes tightly scoped.
- Add regression tests for behavioral bugs.
- Make the documented verification commands pass, or update the documentation and pyproject configuration so the intended verification target is explicit and green.

Start with Finding 1, then restore the verification pipeline. After each fix, run the narrowest relevant tests first, then the full documented verification path.
```

---

# Addendum: Steering And Docs Review

Date: 2026-04-28

## Scope

This addendum reviews the current `.steering/` planning records and persistent `docs/` architecture/design documents against the current repository state.

Primary files reviewed:

- `.steering/20260428-codex-review-followup/{requirement,design,tasklist}.md`
- `.steering/20260428-m9-lora-pre-plan/{requirement,design,tasklist,decisions,blockers}.md`
- Current 2026-04-28 steering drafts for Godot/live-observability/Blender follow-ups
- `.steering/_setup-progress.md`
- `.steering/README.md`
- `docs/architecture.md`
- `docs/functional-design.md`
- `docs/repository-structure.md`
- `docs/development-guidelines.md`
- `docs/glossary.md`
- `README.md`
- `AGENTS.md`
- `CLAUDE.md`

## Findings

### Finding D1: [P1] Active follow-up implementation has only a requirement, not an executable design

Location:

- `.steering/20260428-codex-review-followup/requirement.md:19-24`
- `.steering/20260428-codex-review-followup/design.md:7-35`
- `.steering/20260428-codex-review-followup/tasklist.md:3-28`

Problem:

The active `codex-review-followup` task has a concrete requirement and is already associated with code changes in the working tree, but `design.md` and `tasklist.md` still contain untouched template placeholders such as `path/to/file1.py`, `タスク 1`, and generic test/review checklist items.

Impact:

- The plan is not executable as a steering record.
- Later agents cannot infer which findings were fixed, deferred, or deliberately scoped out.
- This violates the project rule that implementation work must be backed by concrete `requirement.md`, `design.md`, and `tasklist.md`.

Suggested repair:

- Fill `design.md` with the actual repair approach for each finding.
- Replace generic tasklist items with finding-specific checkboxes.
- Mark completed items as code changes land.
- Add `decisions.md` for any architecture-level choice, especially if a new module/layer is introduced.

Acceptance criteria:

- `design.md` lists concrete files, chosen approaches, impact, and test strategy.
- `tasklist.md` has one or more specific checkboxes per finding.
- The current code diff can be traced back to checked-off tasklist entries.

### Finding D2: [P1] The follow-up plan selects a new `contracts/` layer before the architecture has accepted it

Location:

- `.steering/20260428-codex-review-followup/requirement.md:21`
- `.steering/20260428-codex-review-followup/requirement.md:31`
- `.steering/20260428-codex-review-followup/requirement.md:64-67`
- `docs/repository-structure.md:166-187`
- `.agents/skills/architecture-rules/SKILL.md`

Problem:

The requirement states that the UI architecture violation will be solved by introducing a new `contracts/` module, but the accepted architecture currently has no `contracts/` layer. The current dependency graph names `schemas.py` as the shared boundary and does not define where a new `contracts/` package sits.

Impact:

- A fix for an architecture violation can accidentally become a new undocumented architecture violation.
- `ui -> contracts`, `integration -> contracts`, and `evidence -> contracts` dependency rules are undefined.
- Future agents may disagree on whether `contracts/` is lower than `schemas.py`, parallel to it, or an integration submodule.

Suggested repair:

- Treat `contracts/` as a real architecture decision, not an implementation detail.
- Compare at least three options: move constants to `schemas.py`, add `src/erre_sandbox/contracts/`, or keep thresholds local to the dashboard.
- If `contracts/` is adopted, update `docs/repository-structure.md`, `docs/architecture.md`, and `architecture-rules` together.

Acceptance criteria:

- The allowed dependency graph includes the new contract boundary.
- No package imports `integration` merely to access constants.
- The steering task has a `decisions.md` entry documenting the chosen boundary.

### Finding D3: [P2] F4 is simultaneously in scope, out of scope, and excluded from acceptance

Location:

- `.steering/20260428-codex-review-followup/requirement.md:24`
- `.steering/20260428-codex-review-followup/requirement.md:36`
- `.steering/20260428-codex-review-followup/requirement.md:41`
- `.steering/20260428-codex-review-followup/requirement.md:50`

Problem:

The follow-up requirement says the Godot crash finding should be reproduced and judged, but also says the F4 implementation fix is out of scope if it is deferred. The acceptance condition then allows `pytest` to pass "excluding Godot".

Impact:

- The known full-suite failure can disappear from the task without a blocker, decision, or follow-up issue.
- The repository can claim verification recovery while the documented `uv run pytest` path remains conditional.

Suggested repair:

- Choose one explicit outcome for F4 in this task: fix, skip cleanly, or defer.
- If deferred, add `blockers.md` or `decisions.md` with reproduction status, rationale, and the next task name.
- Make the acceptance condition match that outcome.

Acceptance criteria:

- `uv run pytest` either passes fully, or the Godot subset has a documented skip/defer mechanism.
- F4 has a traceable final status.

### Finding D4: [P2] Codex-facing instructions point at `.Codex`, while the actual command/skill roots are `.claude` and `.agents`

Location:

- `AGENTS.md:21-23`
- `AGENTS.md:97-99`
- `CLAUDE.md:21-23`
- `CLAUDE.md:97-99`
- `docs/repository-structure.md:82-86`

Problem:

`AGENTS.md` tells Codex to look under `.Codex/commands/`, `.Codex/agents/`, and `.Codex/skills/`. The actual repository does contain Claude Code assets under `.claude/commands/`, `.claude/agents/`, and `.claude/skills/`, and it also contains Codex-visible skill copies under `.agents/skills/`; what is missing is the `.Codex/...` root named by `AGENTS.md`.

Impact:

- Codex sessions start by checking a non-existent `.Codex/commands` directory even though the usable command definitions live under `.claude/commands`.
- The intended command/skill workflow is ambiguous across agents because Claude Code and Codex use different roots.
- The same project now has three naming conventions in play: `.Codex` in instructions, `.claude` for Claude Code assets, and `.agents` for Codex-visible skills.

Suggested repair:

- Decide whether Codex should call out to `.claude/commands` as the command source, or whether `.agents/` should become the Codex-native root.
- Update `AGENTS.md` to match the actual Codex-facing layout.
- Add a short compatibility note that `.claude/commands` / `.claude/agents` exist and that `.agents/skills` mirrors the Claude skill set for Codex.

Acceptance criteria:

- A new Codex session can find the intended commands and skills without probing a missing `.Codex` directory.
- `AGENTS.md`, `CLAUDE.md`, and `docs/repository-structure.md` no longer contradict each other.

### Finding D5: [P2] Persistent architecture docs contain stale runtime facts

Location:

- `docs/architecture.md:8-35`
- `docs/architecture.md:21`
- `docs/architecture.md:26`
- `docs/architecture.md:63-64`
- `.steering/_setup-progress.md:175-181`
- `.steering/20260418-model-pull-g-gear/decisions.md:36-52`
- `src/erre_sandbox/integration/gateway.py:728`
- `src/erre_sandbox/memory/embedding.py:43-44`

Problem:

Several architecture facts have drifted from implementation and steering decisions:

- G-GEAR setup was finalized as native Windows, while the architecture diagram still says Linux / Win+WSL2.
- Embedding is implemented as `nomic-embed-text` with 768 dimensions, while architecture still names `multilingual-e5-small (384d)` / Ruri.
- The top-level WebSocket diagram still shows `ws://g-gear.local:8000/stream`, while the live route is `/ws/observe`.
- Godot is described as 4.4 in many docs while live evidence and README discuss 4.6.

Impact:

- New implementation work can pick wrong dimensions, wrong endpoints, or wrong environment assumptions.
- Architecture docs stop being a reliable source of truth for agents.

Suggested repair:

- Add a "current implementation snapshot" section to `docs/architecture.md`.
- Preserve original research-plan assumptions only if clearly labeled as historical or planned.
- Update endpoint, embedding, Godot, and G-GEAR OS facts to match accepted steering decisions.

Acceptance criteria:

- Architecture docs distinguish current state from roadmap.
- Endpoint and embedding dimension match code.
- Environment assumptions match setup steering.

### Finding D6: [P2] `repository-structure.md` lists files and directories that do not exist

Location:

- `docs/repository-structure.md:48-51`
- `docs/repository-structure.md:82-91`
- `docs/repository-structure.md:98-101`

Problem:

The repository structure document claims several paths are present or canonical that are absent or now differently shaped:

- `src/erre_sandbox/ui/ws_client.py`, `dashboard.py`, and `godot_bridge.py` are listed, but the actual UI code lives under `src/erre_sandbox/ui/dashboard/`.
- `.github/workflows/ci.yml` is listed, but `.github/` does not exist.
- `CITATION.cff` and `CODE_OF_CONDUCT.md` are listed, but they were not present in the working tree.

Impact:

- File placement guidance is misleading.
- Agents may create duplicate modules instead of extending existing ones.
- CI and governance files appear to exist in docs but not in the repo.

Suggested repair:

- Regenerate the tree from current `find`/`rg --files` output.
- Mark planned files separately from existing files.
- Add missing governance/CI files only if they are truly intended now.

Acceptance criteria:

- Every path in the main tree either exists or is clearly labeled "planned".
- UI module layout reflects the actual dashboard package.

### Finding D7: [P2] Development guidelines claim pre-commit and CI gates that are not installed

Location:

- `docs/development-guidelines.md:22-25`
- `docs/development-guidelines.md:82-87`
- `docs/development-guidelines.md:101-104`
- `docs/architecture.md:68`
- `docs/repository-structure.md:90-91`

Problem:

The docs say ruff is enforced by pre-commit hooks and CI, but no `.pre-commit-config.yaml`, active pre-commit hook, or `.github/workflows/ci.yml` exists in the current tree. The documented checks also do not currently pass, as noted in the source review.

Impact:

- Contributors and agents overestimate the automation safety net.
- Broken lint/test state can persist while docs imply it is automatically guarded.

Suggested repair:

- Either install the promised automation or rewrite the docs as manual verification for now.
- Once the local checks are green, add CI as a separate task.

Acceptance criteria:

- Docs accurately state whether checks are manual, hook-driven, or CI-driven.
- If CI is documented, the workflow file exists.

### Finding D8: [P2] Several current 2026-04-28 steering tasks are requirement-only drafts with template designs/tasklists

Location examples:

- `.steering/20260428-godot-ws-keepalive/requirement.md:35-55`
- `.steering/20260428-godot-ws-keepalive/design.md:7-35`
- `.steering/20260428-agent-presence-visualization/requirement.md:31-49`
- `.steering/20260428-agent-presence-visualization/design.md:7-35`
- `.steering/20260428-event-boundary-observability/requirement.md:25-43`
- `.steering/20260428-world-asset-blender-pipeline/requirement.md:23-42`

Problem:

Several same-day steering directories contain useful requirements but still have default `design.md`, `tasklist.md`, and sometimes `blockers.md` templates.

Impact:

- The backlog looks more execution-ready than it is.
- Future agents may start implementation from incomplete plans.
- Cross-task dependencies, especially among Godot UI layout, presence visualization, event observability, and Blender asset work, are not resolved.

Suggested repair:

- Add a visible status marker such as `DRAFT REQUIREMENT ONLY — DO NOT EXECUTE`.
- Finalize design/tasklist only when the task is actually selected.
- For tasks sharing Godot scenes/scripts, add ordering and conflict notes.

Acceptance criteria:

- Draft tasks are clearly marked as drafts.
- Executable tasks have concrete design and tasklist files.

### Finding D9: [P3] M9 pre-plan is strong, but its tasklist and blocker file are stale

Location:

- `.steering/20260428-m9-lora-pre-plan/tasklist.md:15`
- `.steering/20260428-m9-lora-pre-plan/tasklist.md:78-79`
- `.steering/20260428-m9-lora-pre-plan/blockers.md:3-12`

Problem:

The M9 pre-plan itself is one of the better steering records: it is clearly marked as pre-plan, cites data sources, and structures five ADRs with v1/v2/hybrid choices. However, its tasklist still shows commit/PR items open even though the recent git log indicates the M9 pre-plan commit/PR has landed. `blockers.md` also remains a raw template.

Impact:

- The steering record no longer reflects final task state.
- Template blocker text adds noise to future searches.

Suggested repair:

- Mark commit/PR completion or add a note that the file was intentionally left pre-merge.
- Delete the unused `blockers.md` template or replace it with "No blockers recorded".

Acceptance criteria:

- M9 pre-plan steering status matches repository history.

### Finding D10: [P3] Glossary has mojibake in authoritative terms

Location:

- `docs/glossary.md:18`
- `docs/glossary.md:22`
- `docs/glossary.md:27`
- `docs/glossary.md:34`
- `docs/glossary.md:48`
- `docs/glossary.md:52`
- `docs/glossary.md:70`
- `docs/glossary.md:73-75`

Problem:

The glossary contains visible replacement/corrupted characters in several authoritative term definitions.

Impact:

- The "ubiquitous language" document is less trustworthy as a naming source.
- Agents may copy corrupted text into code, docs, or UI.

Suggested repair:

- Restore the glossary from a clean source or manually fix the corrupted Japanese text.
- Add a lightweight check for replacement characters in docs if this recurs.

Acceptance criteria:

- `docs/glossary.md` renders without mojibake.

## Positive Notes

- `.steering/20260428-m9-lora-pre-plan/decisions.md` is high quality as a planning artifact: it separates execution from pre-plan, cites data sources, records v1/v2/hybrid alternatives, and names review timing.
- `.steering/20260428-godot-ws-keepalive/requirement.md` is also a good requirement-level artifact: it identifies a concrete live-log symptom, current gateway/client mismatch, and measurable acceptance criteria.
- The persistent docs have accumulated many real project decisions, especially around M4/M5/M8. The main issue is not lack of documentation; it is freshness and source-of-truth boundaries.

## Suggested Repair Order

1. Finalize `.steering/20260428-codex-review-followup/design.md` and `tasklist.md` before continuing broad follow-up implementation.
2. Decide whether `contracts/` is a real new architecture layer; document it before relying on it.
3. Reconcile F4 Godot crash scope with acceptance criteria.
4. Align `AGENTS.md`, `CLAUDE.md`, `.claude/`, and `.agents/` references.
5. Refresh `docs/architecture.md` and `docs/repository-structure.md` against the actual tree.
6. Fix glossary mojibake and stale pre-commit/CI claims.
