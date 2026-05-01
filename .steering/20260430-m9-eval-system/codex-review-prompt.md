# Codex independent review request — m9-eval-system design.md

## Reviewer profile
You are an independent reviewer (`gpt-5.5`, `xhigh` reasoning) called to do a
critical pre-implementation review of an evaluation pipeline design for the
ERRE-Sandbox project. Your role is to surface design risks the primary author
(Claude Opus, single-agent /reimagine) may have missed due to single-model bias.

You may use `web_search = "live"` to verify library / methodology claims, and you
have read access to the repository.

## Project context (1 paragraph)
ERRE-Sandbox is a solo research platform that simulates philosophical "great
thinkers" (Kant / Nietzsche / Rikyu) as local-LLM cognitive agents in a 3D
Godot space. Hardware: MacBook (master/dev, MPS) + G-GEAR (RTX 4090 24GB,
qwen3:8b FP16 ~16GB). Zero cloud-LLM-API budget. The current task
**m9-eval-system** is the implementation kickoff of a 4-tier evaluation pipeline
(per-turn / per-100-turn / nightly / sparse-manual) feeding bootstrap CI +
2-of-3 quorum drift gate (M9-B ADR DB9). Its completion criterion is to take a
3 persona × 5 run × 500 turn **golden baseline** to a state where Vendi /
Big5-ICC / Burrows-Delta have bootstrap CI ready (precondition for M9-C-adopt).

## What to review
Read these files verbatim from the repo before reviewing:

1. `.steering/20260430-m9-eval-system/design.md` — adopted hybrid design
   (v2 base + v1 reinforcement 2 + tweaks 2)
2. `.steering/20260430-m9-eval-system/design-comparison.md` — v1 vs v2 diff
   and adoption rationale
3. `.steering/20260430-m9-b-lora-execution-plan/decisions.md` — DB1-DB10 ADR set
   that constrains this task (especially DB5 raw/sidecar separation, DB6 epoch
   policy, DB9 bootstrap CI quorum, DB10 4-tier framework)
4. `.steering/20260430-m9-b-lora-execution-plan/blockers.md` — deferred items
   this task is expected to close (LIWC license, Burrows multi-lang, judge bias)
5. `.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md`
   — methodology origin (6 metric families, 30+ metrics)

DO NOT read `design-v1.md` (deliberately retired initial draft, reading it
introduces confirmation bias toward already-rejected alternatives).

## Adopted design summary (7 axes, do not re-litigate, focus on **risks within**)

| Axis | Adoption |
|---|---|
| DB5 physical separation | DuckDB single file + named schemas (`raw_dialog`, `metrics`) + training-loader API guard (`connect_training_view()` raises `EvaluationContaminationError` on `metrics.*` SELECT) + **CI grep gate** in `.github/workflows/ci.yml` blocking `metrics.` in training-loader paths. 3-layer defense. Parquet demoted to nightly export format only. |
| Library | `duckdb>=1.1` only (drop pyarrow / polars / spacy / pingouin / vendi-score; bring scipy + sentence-transformers + ollama as optional `eval` extras). |
| LIWC | **Option D**: full retirement. Big5 stability claim relies on **IPIP-NEO short-form self-report only** (Tier B, agent answers via local 7B-Q4). Empath retained as Tier A *secondary diagnostic only* (no Big5 claim). LIWC license deferral closes immediately. |
| Orchestrator | No new wrapper. Add `golden_baseline_mode: bool = False` arg + 1 sink hook to existing `src/erre_sandbox/integration/dialog.py::InMemoryDialogScheduler`. Default False → all existing tests pass. Stimulus injection done by `evidence/golden_baseline.py` pushing to scheduler input queue. |
| Tier A timing | All **post-hoc per-run CLI** (live inference unloaded, DB6 strict). Per-turn granularity preserved by storing turn-id-keyed metric rows. |
| Golden baseline | **Hybrid**: 200 turn fixed stimulus battery (Wachsmuth Toulmin 30 / ToM info-asymmetric chashitsu 20 / RoleEval-adapted Kant biographical MCQ 10 / persona-conditional moral dilemma 10 = 70 stimuli × 3 cycles, last cycle truncated to 10 turns) + 300 turn natural dialog from existing scheduler (peripatos / chashitsu / agora / garden mode transitions). Ratio 200/300 is **default; P3b pilot run 50 turn each will tune empirically**, recorded in blockers.md. |
| Tier C nightly | G-GEAR `systemd --user` timer (`erre-eval-tier-c.timer` @ 02:00) + `flock` against autonomous-loop lockfile + `nvidia-smi --query-gpu=memory.free` preflight (skip + log if < 14 GB). Mac launchd → ssh trigger explicitly **not adopted** (configuration minimization). |

Hardware allocation (P0a-P7) and dependency order are in `design.md` §Hardware
allocation and §Tier 実装順序 — please read both. Mac is the master/dev,
G-GEAR runs P3 baseline capture, P4b Tier B post-hoc, and P6 Tier C nightly.
Single-writer rule: G-GEAR writes the DuckDB file; Mac rsyncs it and opens
read-only.

## Required deliverables (HIGH / MEDIUM / LOW format, identical to M9-B review)

For each finding produce:

```
### {HIGH|MEDIUM|LOW}-N: <one-line title>
- **Finding**: what is wrong / risky / under-specified
- **Evidence**: cite specific file:line, method, paper, or library doc
  (use web_search if needed; SGLang docs / scipy block-bootstrap / IPIP-NEO
  literature / DuckDB threading model are all reasonable references)
- **Recommendation**: concrete change to design.md or test additions
- **Severity rationale**: why HIGH (must reflect before P0) vs MEDIUM
  (worth recording in decisions.md but defensible to defer judgment) vs LOW
  (defer to blockers.md with reopen condition)
```

Severity rubric:
- **HIGH** — design must change before P0a starts; ignoring it costs rework
  later or invalidates the golden baseline. Must reflect in design.md.
- **MEDIUM** — design choice has multiple defensible options; reviewer wants
  a decision recorded with rationale. Logged in decisions.md.
- **LOW** — defer-able with explicit reopen condition. Logged in blockers.md.

## Specific points to dig into (in addition to general review)

These are the 7 areas the primary author flagged as most likely to harbor
single-model bias. Please probe them deliberately, but **do not stop here** —
surface anything else you spot.

1. **3-layer schema-guard contract effectiveness vs physical Parquet separation.**
   Is DuckDB single-file + named schema + API contract + CI grep gate truly
   stronger than `data/parquet/raw_dialog/` vs `data/parquet/metrics/` separate
   files? Specifically: (a) what failure modes does grep miss that path-level
   isolation catches? (b) is the API contract stable across language migrations
   if the project ever adopts Rust/Go data tooling? (c) is DuckDB safe for the
   single-writer rule (G-GEAR writes, Mac read-only) under journal mode?

2. **Big5 measurement model: IPIP-NEO self-report only.** Is relying on agent
   self-report from a local 7B-Q4 valid given (a) acquiescence bias, (b) social
   desirability, (c) instruction-following artifacts where the agent simply
   pattern-matches the persona description back? The design includes a
   *conditional fallback* to BIG5-CHAT regression head if ICC < 0.6 frequently —
   is the trigger threshold (0.6) and "frequently" definition adequate? What
   should the operational definition of "frequently" be?

3. **Bootstrap CI statistical validity.** Plain bootstrap assumes iid samples,
   but turns within a run are autoregressive (LLM context dependence) and runs
   share the same persona. Should the design require **block bootstrap**
   (Künsch / stationary bootstrap) instead of plain resample? If yes, how to
   choose the block length given 500-turn runs? Is the effective sample size
   too small for a 95% CI per persona at n=500 turns × 5 runs = 2500?

4. **Hybrid baseline 200/300 ratio empirical determination.** P3b plans a
   50-turn pilot per format to tune the ratio. Is 50 turns sufficient
   statistical power to detect a difference in bootstrap-CI width on Burrows
   Delta and Vendi? What's the minimum pilot size that would be defensible?
   Is there a risk that the pilot itself contaminates the golden baseline by
   establishing scheduler state?

5. **Burrows Delta multi-language reference: 50K token noise floor.** The
   design implies per-language reference corpora (Kant German + English
   translation, Nietzsche, Rikyu Japanese). The blockers.md note "reference
   token count < 50K → z-score noisy" is a placeholder. Is 50K the right
   threshold? What does the stylometry literature actually require for stable
   z-score normalization on function-word frequency vectors?

6. **systemd-timer + flock + nvidia-smi preflight race conditions.** The
   autonomous-loop holds a flock; the timer fires at 02:00 and acquires the
   same flock or skips. (a) Is there a TOCTOU window between
   `nvidia-smi --query-gpu=memory.free` returning >14 GB and Prometheus 2 8x7B
   actually loading? (b) What if the autonomous loop starts at 01:59:58 — does
   the timer fire "blocked" or "skipped" and is journalctl observability
   adequate? (c) How does the design handle G-GEAR reboots or systemd unit
   regression mid-baseline-capture?

7. **Phase P0a–P7 dependency table — missed dependencies.** The Hardware
   allocation table lists 12 subtasks. Are there hidden dependencies the table
   misses? E.g.: does P3 require P5 (bootstrap CI) before any data interpretation,
   or is "ready for CI computation" enough? Does P4b on G-GEAR require synced
   `evidence/tier_b/*.py` from Mac (Mac→GG implied but not flagged)? Is the
   `[Mac→GG]` tag for P6 sufficient, or should the systemd unit creation also
   span `[Mac→GG]` more explicitly?

## Constraints to respect (cannot recommend violating these)

- DB1-DB10 ADR set (M9-B `decisions.md`) — blocked from change in this review
  cycle, can only be re-opened via the listed reopen conditions
- CLAUDE.md hard rules: zero cloud-LLM API dependency, no GPL imports in
  `src/erre_sandbox/`, no direct push to main
- Solo cadence: any recommendation requiring N-week additional research effort
  must be flagged as LOW (defer)
- M2_THRESHOLDS / SCHEMA_VERSION="0.10.0-m7h" / DialogTurnMsg / RunLifecycleState
  are frozen contracts (snapshot-tested)

## Output format

```markdown
# Codex review — m9-eval-system design.md

**Date**: 2026-04-30
**Reviewer**: Codex gpt-5.5 xhigh
**Review target**: .steering/20260430-m9-eval-system/design.md (and listed companions)

## Summary
<2-4 lines: overall verdict (proceed-as-is / proceed-with-HIGH-fixes / re-Plan-required), highest-impact concern, lowest-cost win>

## Findings
<HIGH-N / MEDIUM-N / LOW-N entries in the format above, ordered by severity then numeric>

## Cross-cutting observations
<optional: themes spanning multiple findings>

## Verification suggestions
<optional: tests / experiments the author should run during P0-P5 to falsify your concerns>
```

Be terse. Cite specific lines. Use web_search for library / methodology claims.
Do not summarize the design back to me — assume I've read it. Push hard on
single-model blind spots.
