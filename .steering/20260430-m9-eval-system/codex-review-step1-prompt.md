# Codex independent review — m9-eval-system P3a Step 1 (`cli/eval_run_golden.py`) design

You are an independent reviewer for the ERRE-Sandbox project, invoked at the
boundary between Plan approval and implementation start (Claude `/reimagine`-
level threshold). Plan was already user-approved, but per the project's
"Claude `/reimagine` 単独で確定させず Codex `gpt-5.5 xhigh` independent review
を挟む" policy, your role is to flag structural bias residual in the single-
model design pass.

## Scope

**This review covers ONLY Step 1** (CLI 1 file + 1 unit test + .gitignore +
optional pyproject.toml tweak). Steps 2-5 (採取 / rsync / summary / PR) are
out of scope for this review and will get a separate check before Step 2.

Step 1 builds `src/erre_sandbox/cli/eval_run_golden.py` that drives the
already-merged `GoldenBaselineDriver` (P2c, PR #128 merged) against real
qwen3:8b on G-GEAR (RTX 5060 Ti 16GB / Windows 11 / Ollama 0.22) to capture
P3a pilot runs (3 persona × 2 condition × 200 turn = 6 fresh DuckDB).

## Background you should treat as given

- **Already merged (PR #128, main = 4b57a95)**:
  - `contracts/eval_paths.py` (RawTrainingRelation / sentinel test / 4-layer guard)
  - `evidence/eval_store.py` (DuckDB schema bootstrap, ALLOWED_RAW_DIALOG_KEYS=
    15 columns, `connect_training_view` / `connect_analysis_view` /
    `export_raw_only_snapshot` / `write_with_checkpoint` / `atomic_temp_rename`)
  - `evidence/tier_a/` 5 metric (Burrows z-score Delta L1 / MATTR / NLI /
    novelty / Empath proxy)
  - `evidence/reference_corpus/` (PD-only Kant de / Nietzsche de / Rikyu ja +
    synthetic 4th)
  - `evidence/golden_baseline.py` driver:
    - `GoldenBaselineDriver` dataclass (scheduler, inference_fn, seed_root,
      cycle_count). Uses `schedule_initiate` / `record_turn` / `close_dialog`
      public API only (Codex HIGH-4 reflected).
    - `derive_seed(persona, run_idx)` blake2b uint64 (ME-5).
    - `shuffled_mcq_order` per-cell PCG64 shuffle (ME-7 §1).
    - `MCQOutcome` / `StimulusOutcome` dataclasses, ME-7 §2 cycle-1-only
      scoring (legend / category_subscore_eligible=False excluded).
    - `load_stimulus_battery(persona)` loads `golden/stimulus/<persona>.yaml`,
      synthetic 4th persona is isolated to `tests/fixtures/`.
  - `golden/seeds.json` (15 uint64 seeds = 5 run × 3 persona)
  - `golden/stimulus/{kant,nietzsche,rikyu}.yaml` (70 stim/persona, schema
    in `_schema.yaml`, MCQ 11 fields per ME-7)
  - `integration/dialog.py` `InMemoryDialogScheduler` with
    `golden_baseline_mode: bool = False` minimum patch (P2b)
  - 23 driver unit test PASS, full suite 1221 passed / 31 skipped / 14
    deselected, mypy src 0, ruff/format clean, eval-egress-grep-gate green
- **Existing live-run wiring** (not eval-specific) the natural condition
  reuses headlessly:
  - `bootstrap.py` builds MemoryStore (sqlite) → EmbeddingClient → Reflector
    → CognitionCycle → WorldRuntime with InMemoryDialogScheduler +
    OllamaDialogTurnGenerator. Default `cognition_period_s=10.0`, dialog
    proximity auto-fire prob 0.25 / cooldown 30 ticks.
  - `integration/dialog_turn.py` `OllamaDialogTurnGenerator` builds prompt
    (`_build_dialog_system_prompt` / `_build_dialog_user_prompt`) including
    `_DIALOG_LANG_HINT` per persona, `_ANTI_REPEAT_INSTRUCTION` from turn 2,
    160-char hard cap, `_sanitize_utterance` filter. Failure modes (Ollama
    unreachable / empty / oversized) collapse to `return None`.
- **Persona YAML schema**: PersonaSpec(persona_id, display_name, era,
  cognitive_habits, default_sampling: SamplingBase, behavior_profile, ...).
  SamplingBase(temperature, top_p, repeat_penalty). Stimulus battery for
  kant: 70 stim, sum(expected_turn_count)=148 (wachsmuth 30 stim/66 turn,
  tom 20/52, roleeval 10/10, dilemma 10/20).

## User-confirmed design choices (won't change)

1. **natural condition focal turn budget** = focal persona の発話のみ 200 turn
   (mixed total ~400-600). Vendi 200-turn window が直接満たされる。
2. **natural condition agent set** = 3 persona 全員 (kant + nietzsche + rikyu)
   を同 reflective zone (例 AGORA) に register、proximity auto-fire 利用。
3. **cognition_period_s** = default 10s 維持 (M5/M6 baseline と整合)。
4. **single-CLI 単一 module** = `eval_run_golden.py` 1 file、`--condition`
   引数で stimulus / natural を分岐、wrapper script は使わない。

## Plan summary (full file at `.steering/20260430-m9-eval-system/`)

### File layout

| Path | 種別 | 説明 |
|---|---|---|
| `src/erre_sandbox/cli/eval_run_golden.py` | 新規 | argparse + main + capture_stimulus + capture_natural + DuckDB turn_sink + Ollama inference_fn + CHECKPOINT + atomic rename |
| `tests/test_cli/test_eval_run_golden.py` | 新規 | mock LLM unit test (`@pytest.mark.eval` で deselect) |
| `tests/test_cli/__init__.py` | 新規 (空) | package marker |
| `.gitignore` | 修正 | `data/eval/pilot/*.duckdb` / `*.log` |

### argparse

```
--persona {kant|nietzsche|rikyu}    required
--run-idx INT                        required (0..4)
--condition {stimulus|natural}       required
--turn-count INT                     default 200 (P3a target)
--cycle-count INT                    default 3 (stimulus only — P3 design integrity)
--output PATH                        required (DuckDB target)
--ollama-host                        default http://127.0.0.1:11434
--model                              default qwen3:8b
--embed-model                        default nomic-embed-text (natural only)
--memory-db                          default None (natural only, → /tmp temp sqlite)
```

### stimulus condition flow (~20-30 min wall)

1. `derive_seed(persona, run_idx)` + `assert_seed_manifest_consistent(load_seed_manifest())`.
2. fresh DuckDB at `args.output` → `bootstrap_schema(con)`.
3. Build `_make_duckdb_turn_sink(con, run_id, persona_id, mode_label="stimulus", zone, epoch_phase="autonomous")` closure that maps `DialogTurnMsg` →
   INSERT into `raw_dialog.dialog` (15 ALLOWED columns).
4. `InMemoryDialogScheduler(envelope_sink=lambda e: None, turn_sink=duckdb_sink, golden_baseline_mode=True)`.
5. `_make_stimulus_inference_fn(ollama_client, persona_spec)`:
   - System prompt: persona habits + zone hint + lang hint (mini-builder
     mirroring `dialog_turn.py::_build_dialog_system_prompt` but transcript-
     less; instead embeds stimulus prompt_text as the user message and
     formatted MCQ options).
   - MCQ → temperature=0, top_p=1, num_predict=8, stop=["\n"]. Non-MCQ →
     persona's `default_sampling` via `compose_sampling()`.
   - Failure: catch `OllamaUnavailableError`, return `""` (driver sees
     `_parse_response_option(None)` → `is_correct=False` off-format).
   - Retry: 3x exponential backoff (200ms / 800ms / 3.2s) before giving up.
6. Battery slicing for ~200 turn target:
   ```
   per_cycle_target = args.turn_count // args.cycle_count   # 200 // 3 = 66
   sliced = battery[:k] where cumsum(expected_turn_count[:k]) ≤ per_cycle_target
   driver.run_persona(persona, stimuli=sliced) with cycle_count=3
   actual_turns = 3 × cumsum(sliced)            # ≈ 198 for kant 200/3
   ```
7. `eval_store.write_with_checkpoint(con)` → `atomic_temp_rename(temp, args.output)`.

### natural condition flow (~60-90 min wall)

1. Same DuckDB seed/identity check + `bootstrap_schema(con)`.
2. Replicate bootstrap.py wiring **headlessly** (no uvicorn):
   - `MemoryStore(db_path=args.memory_db or f"/tmp/p3a_natural_{persona}_{run_idx}.db")` + `create_schema()`.
   - `EmbeddingClient(model=args.embed_model)` + `OllamaChatClient(model=args.model, endpoint=args.ollama_host)`.
   - `Reflector` + `CognitionCycle` + `WorldRuntime` (default cadences).
   - `InMemoryDialogScheduler(envelope_sink=runtime.inject_envelope, turn_sink=chained_sink)` where `chained_sink = sqlite_persist + relational_persist + duckdb_persist`.
   - `OllamaDialogTurnGenerator(llm, personas)` attached to runtime.
3. Register 3 agents (kant + nietzsche + rikyu) at distinct positions inside
   AGORA so the proximity threshold (5m) admits dialogs naturally. agent_id
   = `f"a_{persona_id}_001"`.
4. Run `runtime.run()` in one Task. Run a watchdog Task that polls
   `focal_turn_counter` (incremented inside `duckdb_persist` when speaker
   matches `args.persona`) and calls `runtime.stop()` when count ≥ args.turn_count.
   Wall hard-cap: 90 min (kill switch).
5. `write_with_checkpoint` + `atomic_temp_rename` after stop. Temp sqlite
   left in /tmp (outside repo, debugging artefact).

### DuckDB row mapping (15 ALLOWED_RAW_DIALOG_KEYS)

| col | value |
|---|---|
| `id` | `f"{run_id}:{turn.dialog_id}:{turn.turn_index}"` |
| `run_id` | `f"{persona}_{condition}_run{run_idx}"` |
| `dialog_id` | `turn.dialog_id` |
| `tick` / `turn_index` | from `turn` |
| `speaker_agent_id` / `speaker_persona_id` | resolver (natural) / driver (stimulus) |
| `addressee_*` | same |
| `utterance` | `turn.utterance` |
| `mode` | `"stimulus"` / `"natural"` |
| `zone` | scheduler dialog zone (stimulus) / runtime snapshot (natural) |
| `reasoning` | `""` |
| `epoch_phase` | `"autonomous"` |
| `created_at` | `datetime.now(UTC)` |

### Mock LLM unit test (`@pytest.mark.eval`)

- **stimulus mock**: inject `inference_fn` directly into `capture_stimulus(...)`,
  bypass argparse. Verify DuckDB row count matches `cycle_count × cumsum(sliced)`,
  seed identity guard fires, MCQ scoring reaches `_maybe_score_mcq`.
- **natural mock**: stub `DialogTurnGenerator` injected via
  `runtime.attach_dialog_generator`. ManualClock + 3 agents in AGORA; verify
  watchdog stops runtime when focal turn count reached.
- **isolation skeleton** (Step 2 finalises): ensure each invocation creates a
  fresh DuckDB file (no carry-over).

## Specific topics where I want your second opinion

### HIGH-priority for review

1. **Stimulus battery slicing semantics**: I slice in YAML order (wachsmuth
   30 first), so for kant 200 turn at cycle_count=3 the slice = first ~30
   wachsmuth (66 turn × 3 cycles ≈ 198 turn). This loses MCQ + dilemma + ToM
   coverage entirely in the pilot. Is this acceptable for ME-4 ratio decision?
   The ratio decision is bootstrap CI WIDTH on Burrows/Vendi/ICC, where
   volume + variance dominate; category mix may be secondary. But it could
   bias the comparison if `natural` condition mixes are different. Should I
   instead use a stratified slice (proportional from each category) or skip
   slicing and just run cycle_count=2 (2 × 148 = 296 turn over budget)?

2. **DuckDB direct write on the natural condition**: I plan to write raw
   turns to DuckDB live (alongside sqlite). The DuckDB writer is `con.execute("INSERT ...")`
   per turn from a synchronous turn_sink. Synchronous DuckDB write inside
   `record_turn` (called from `WorldRuntime._drive_dialog_turns` via
   `scheduler.record_turn`) is on the asyncio event loop thread — could
   block the cognition cycle. Alternatives: (a) accept blocking (small
   inserts, ~1ms each, low rate at 0.1Hz cognition); (b) buffer turns in
   memory and bulk INSERT at CHECKPOINT time (loses crash-resilience);
   (c) use a single-writer thread with queue (more complex). Which is
   right for a 200-turn pilot?

3. **CHECKPOINT atomicity vs runtime stop ordering**: After `runtime.stop()`
   the WorldRuntime exits its `run()` loop on the next scheduling boundary,
   but pending in-flight dialog turn coroutines (gathered) may complete
   AFTER `runtime.stop()` returns. If I `con.close()` while a turn_sink is
   trying to write, I lose data or hit lock errors. Sequence I plan:
   `runtime.stop()` → `await runtime_task` (blocks until run loop returns) →
   `write_with_checkpoint(con)` → `atomic_temp_rename(...)`. Is `await
   runtime_task` sufficient to drain in-flight turn_sink writes, or do I
   need an explicit "drain" step?

4. **Ollama keep-alive over 200 stimulus invocations**: The stimulus
   condition fires ~150 stimuli × 2-3 LLM calls each ≈ ~400 chat() calls
   per persona×condition. Default httpx client keeps connection pooling;
   but qwen3:8b inference is 2-5s each so the connection sits idle → idle
   timeout on either side may force frequent re-handshake. Should I
   pre-warm with a `health_check()` at the start and accept the natural
   reconnect, or add a periodic `health_check()` ping (every N turns)?

5. **focal turn watchdog precision in natural condition**: I count
   focal-speaker turns in the duckdb_sink closure and call `runtime.stop()`
   from a separate Task when count reaches budget. Race: stop() is signal,
   not synchronous shutdown. Up to ~10 extra turns can land before the
   tick scheduler honours stop. Should I:
   (a) accept overshoot (200 → ~210 turn);
   (b) tighten by skipping turns once the budget is hit (drop instead of
   write); or (c) coordinate via an asyncio.Event the dialog generator
   checks before generating?

### MEDIUM-priority

6. **mode column semantics confusion**: the existing live-run sqlite
   `dialog_turns` table has a `mode` column carrying ERRE mode name
   (`peripatetic`/`chashitsu`/...). My DuckDB mapping reuses the same
   column name `mode` for `"stimulus"`/`"natural"`. Is this contract
   collision OK, or should I split into a new column / use the existing
   `mode` for ERRE mode and store condition in a different column? The
   `ALLOWED_RAW_DIALOG_KEYS` contract is locked, so any column rename
   means schema bump.

7. **prompt builder duplication**: I plan to write a stimulus-flavoured
   mini prompt builder inside the CLI rather than refactor
   `dialog_turn.py::_build_dialog_system_prompt`. Is that the right call,
   or should I pull `_build_dialog_system_prompt` out into a shared
   builder module? Pulling out is "right" by DRY but stimulus has no
   transcript / addressee / ERRE mode, so the two builders diverge in
   inputs.

8. **persona mapping for natural condition agent_ids**: `bootstrap.py` uses
   `agent_id = f"a_{persona_id}_001"`. My CLI follows this. Is there any
   risk of collision with existing live-run sqlite data when `--memory-db`
   defaults to `/tmp/p3a_natural_*.db` (a fresh per-invocation file)?
   Confirm there's no global registry that would conflict.

### LOW-priority

9. **`__init__.py` empty file under `tests/test_cli/`**: pytest with
   conftest at repo root usually doesn't need explicit package init for
   test dirs (conftest auto-discovery). Should I omit?

10. **wall hard-cap mechanism**: My natural-condition watchdog has a 90 min
    hard cap. Is that a fixed constant or should it be a CLI flag?

## Output format

Return findings as **HIGH / MEDIUM / LOW** sections with:
- one-line summary per item
- ≤8-line analysis per item
- concrete patch suggestion (code snippet or "do this" line) per item

End with a **Verdict** paragraph: should we proceed with implementation as
planned with HIGH-fixes integrated, or is there a structural redesign
recommendation? Brevity preferred — total target ≤500 lines.

Files you should consult before responding:
- `.steering/20260430-m9-eval-system/design-final.md` (Hardware allocation
  table P3a row, §"Orchestrator")
- `.steering/20260430-m9-eval-system/decisions.md` (ME-2 / ME-4 / ME-5 / ME-7)
- `src/erre_sandbox/evidence/golden_baseline.py`
- `src/erre_sandbox/evidence/eval_store.py`
- `src/erre_sandbox/integration/dialog.py`
- `src/erre_sandbox/integration/dialog_turn.py`
- `src/erre_sandbox/bootstrap.py`
- `src/erre_sandbox/world/tick.py` (just the `_drive_dialog_turns` /
  `_run_dialog_tick` part)
- `golden/stimulus/kant.yaml` (first 50 lines for shape)
