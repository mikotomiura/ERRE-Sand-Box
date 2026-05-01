# Codex independent review — m9-eval-system P3a Step 1 (`cli/eval_run_golden.py`) design

> **VERBATIM** — 一切要約せず Codex `gpt-5.5 xhigh` の出力をそのまま保存。
> Invocation: 2026-05-01, model=gpt-5.5, reasoning=xhigh, tokens=228,055
> (per_invocation_max=200K policy_action=warn 個人プロジェクト規定)。
> Prompt: `codex-review-step1-prompt.md`。
> Raw log: `codex-review-step1.raw.log` (9645 lines、636KB)。

---

**HIGH**

1. **YAML-order stimulus slicing is not acceptable.**  
It collapses Kant’s pilot to Wachsmuth-only, so the “stimulus” condition no longer represents the planned 70-item mix. Vendi/Burrows CI width is prompt-genre sensitive, so category mix is not secondary here. Do not use `cycle_count=2`; it breaks the 200-vs-200 pilot symmetry.  
Patch: replace prefix slicing with deterministic stratified slicing by `category` and `expected_turn_count`, and write selected `stimulus_id`s to the run log.

2. **Make the stimulus budget focal-turn aware.**  
`GoldenBaselineDriver` alternates speaker on multi-turn stimuli ([golden_baseline.py](C:/ERRE-Sand_Box/src/erre_sandbox/evidence/golden_baseline.py:393)), so “198 turns” may not mean 198 focal persona rows. Natural is explicitly focal-speaker 200; stimulus must match that or Vendi’s 200-turn window is not actually met.  
Patch: count `turn.speaker_id == persona_id` for stimulus budget, persist interlocutor rows honestly, and assert focal row count at the end.

3. **Direct DuckDB writes are fine, but eval row loss must be fail-fast.**  
`InMemoryDialogScheduler.record_turn()` catches sink exceptions and keeps running ([dialog.py](C:/ERRE-Sand_Box/src/erre_sandbox/integration/dialog.py:213)). That is right for live runs, wrong for eval capture if DuckDB fails. Blocking is acceptable at this rate; queue/thread is unnecessary for P3a.  
Patch: run DuckDB persist first, increment counters only after success, set a `fatal_error`, call `runtime.stop()`, and abort/no-rename after `await runtime_task`.

4. **Write to a fresh temp DuckDB, not directly to `--output`.**  
`bootstrap_schema()` is idempotent, so opening an existing output silently carries rows forward. `atomic_temp_rename()` only gives atomicity if the connection wrote the temp file.  
Patch: refuse existing final output unless an explicit `--overwrite` exists; connect to `output.tmp`, checkpoint/close it, then rename.

5. **Seed the natural scheduler RNG.**  
The natural path uses proximity auto-fire probability; if `InMemoryDialogScheduler` gets default `Random()`, `run_idx` does not control admission randomness.  
Patch: `rng=random.Random(derive_seed(args.persona, args.run_idx))` for natural; use derived per-turn seeds in Ollama `options` where deterministic non-MCQ replay matters.

6. **`await runtime_task` is the right drain, with a timeout.**  
`WorldRuntime.run()` awaits `_drive_dialog_turns()`, which awaits `gather()` and then calls `record_turn()` synchronously ([tick.py](C:/ERRE-Sand_Box/src/erre_sandbox/world/tick.py:1177)). After `runtime_task` returns, sinks are drained.  
Patch: `runtime.stop(); await wait_for(runtime_task, grace_s)`; on timeout cancel and mark run failed, never checkpoint partial data as successful.

**MEDIUM**

1. **Accept small natural overshoot; do not drop rows.**  
Dropping post-budget turns corrupts transcripts and scheduler state. Stop immediately from the DuckDB sink when focal count reaches budget; report `actual_focal_turns`, and let analysis use the first 200 if strict windows are needed.

2. **Do not overload `mode` with condition without updating the contract.**  
Current raw contract reserves `mode`, and the eval-store fixture uses values like `peripatos`; current sqlite `dialog_turns` has `epoch_phase`, not `mode` ([store.py](C:/ERRE-Sand_Box/src/erre_sandbox/memory/store.py:221)).  
Patch: put condition in `run_id`; use `mode` for ERRE mode when known, or explicitly update `eval_paths.py` docs/tests if redefining it.

3. **Use startup warmup, not periodic Ollama ping.**  
`health_check()` checks `/api/tags`; it does not load/keep the model warm. httpx will reconnect if a pooled connection goes idle.  
Patch: run `health_check()` plus one cheap `chat(... num_predict=1, think=False)` before capture; skip periodic pings.

4. **Keep the stimulus prompt builder local for Step 1.**  
Refactoring `_build_dialog_system_prompt()` now touches private integration behavior for a different prompt shape. Stimulus has item/options inputs and no transcript/addressee state.  
Patch: add a CLI-local builder with a small prompt snapshot test; avoid importing private `_DIALOG_*` symbols.

5. **Natural positions do not drive scheduler admission.**  
`_iter_colocated_pairs()` checks same zone only, not distance ([dialog.py](C:/ERRE-Sand_Box/src/erre_sandbox/integration/dialog.py:361)). Agent ID reuse is safe with a fresh per-run sqlite DB; there is no global registry.  
Patch: ensure all three states have `zone=AGORA`; treat x/z placement as world-event hygiene, not dialog admission control.

**LOW**

1. **`tests/test_cli/__init__.py` is optional but consistent.**  
The repo already has `tests/__init__.py` and package markers in most test subdirs, so adding it is harmless. A flat `tests/test_cli_eval_run_golden.py` would also be fine.

2. **Make the 90-minute wall cap a CLI flag.**  
Patch: `--wall-timeout-min 90`; log timeout as a failed capture and avoid atomic rename.

3. **No pytest marker tweak appears needed.**  
`pyproject.toml` already defines `eval` under strict markers.

**Verdict**

Proceed with Step 1 after integrating the HIGH fixes. No structural redesign is needed, but the current plan has three data-validity risks: biased stimulus slicing, non-focal turn accounting, and silent row loss/fresh-file ambiguity. Fix those in the CLI before running G-GEAR pilots.
