# M7 Slice δ — Decision Log

## Plan-mode hybrid (post /reimagine)

Recorded in ``design-final.md``. Adopted picks (from v1 + v2 cross-comparison):

| Axis | Adopted | Note |
|---|---|---|
| 1a decay | v1 (neuroticism 0.02-0.08) | Observability priority over v2's agreeableness |
| 1b impact | v2 (structural features) | JP lex dropped — brittle without MeCab |
| 1c weight | v1 (extraversion 0.5-1.5) | Wider range = more contrast |
| 2 negative | v1 antagonism table | Trait-distance fails empirically at N=3 (computed) |
| 3 belief | v2 (typed enum + simulation-derived threshold) | Cleaner for m8 Critics |
| 4 SQL | v2 (extend only, no wrapper) | YAGNI |
| 5 zone | v2 (no DB migration; AgentState-resident) | v1 over-engineered |
| C3 #3 | defer to ε | Cost undersized; bundle stays in 15h envelope |

## C5 calibration retune

The first-pass C3 tunables (impact 0.6/0.4, antagonism -0.30) saturated
the recurrence in 1-2 turns, defeating the belief-promotion threshold.
The C5 simulation regression test
(``tests/test_cognition/test_relational_simulation.py``) caught this and
drove the retune to:

* ``_IMPACT_ADDRESSEE_WEIGHT``: 0.6 → 0.08
* ``_IMPACT_LENGTH_WEIGHT``: 0.4 → 0.04
* antagonism magnitude: -0.30 → -0.10

Result: saturating dyads cross |affinity|>0.45 between turns 6-12, inside
the live G-GEAR window. See ``observation.md`` for per-pair simulation
values.

## C7 — Godot GUT scope

The design-final mentioned "Godot GUT — `ReasoningPanel` 'last in <zone>'
rendering fixture" but the project has no GUT runner configured. C7
shipped the GDScript change without a GUT-side test. The wire-level
guarantee is provided by C1's ``test_relationship_bond_round_trip_with_zone``
in pytest plus the regenerated agent_state JSON schema golden file. If
GUT is later set up (m9-lora candidate), a focused
``ReasoningPanelTest.gd`` should pin the format.

## C3 #3 — Persona-distinct silhouette deferral

User-confirmed via AskUserQuestion in Plan mode. Deferred to ε (M9-lora
will revisit visual differentiation alongside persona voice work). γ's
C3 trinity remains at 2/3 closed (Relationships UI + visual capsule).

## Bundle scope drift

None. All 8 commits landed within the design-final scope. No mid-flight
addition or deletion. Bundle total trended ~12.9h actual against the
14.4h estimate (slight under-shoot, mostly from C5's simulation test
revealing the calibration issue early so retune was cheap).

## Pre-existing flake annotation

``tests/test_memory/test_store.py::test_concurrent_add_does_not_raise_systemerror``
intermittently shows in the full suite as failing or as the recipient of
an ``unraisableexception`` warning attribution. This is a pre-existing
socket-leak issue (introduced before δ; reproducible on
``main`` HEAD) and has no relation to any δ commit. Standalone the test
passes; in the full suite it occasionally claims a warning that pytest's
``unraisableexception`` plugin attributes to the next-running test.
Cleanup is L6 backlog scope.

## Live G-GEAR run-01 verdict (2026-04-26)

**4/5 PASS, 1 δ-residual.** Gates 1, 3, 4, 5 land cleanly on a 122s
``kant,nietzsche,rikyu`` run with ``ERRE_ZONE_BIAS_P=0.1``. Gate 2
(``belief_promotions`` non-empty) misses because peak |affinity| only
reaches 0.358 in 17 dialog_turns (≈2.8 turns/dyad), short of the
0.45 threshold and well under the C5-predicted 6-9 turn crossing window.

Per ``run-guide-delta.md`` Step 7, observation.md does **not** relax the
gate. The diagnosis + remediation candidates (option A: longer run /
B: impact retune / C: threshold lower / defer-to-ε) are recorded in
``.steering/20260426-m7-delta-live-fix/``. The cheapest probe — re-run
at ``--duration 360`` — is the recommended first step before any code
change.

Side-observation: gateway logs ``WebSocketDisconnect (code 1000)`` as
``ERROR`` from ``_recv_loop`` inside ``TaskGroup`` on every clean
MacBook disconnect. Cosmetic only; bundled into the live-fix task as
a separate residual.

## R4 — Post-merge review (MacBook、2026-04-26)

> γ decisions.md §R3 と同じ枠で δ merged 範囲 (PR #95、commit 17d2802、+2869/-126
> across 29 files in src/erre_sandbox + tests/) を code-reviewer agent (Opus) で
> review。ε scope の確定材料。
>
> Already-tracked residual (再掲しない): gateway WS log noise (live-fix D2)、
> LLM unparseable plan watch (live-fix D3)、session_phase filter (M8 D5)、
> persona-distinct silhouette (本 decisions C3 #3)。

### HIGH (ε で決着)

**H1 — Orphaned docstring on `_MAX_RAW_FRAME_BYTES` (gateway.py:71-87)**

δ で `_LAYOUT_SNAPSHOT_TIMEOUT_S` を `_MAX_RAW_FRAME_BYTES` の直後に挿入したが、
旧 docstring (lines 82-87) が間に残り、`_MAX_RAW_FRAME_BYTES` から切り離された
free-floating string expression になった。`_MAX_RAW_FRAME_BYTES` は
undocumented、`_LAYOUT_SNAPSHOT_TIMEOUT_S` は二重 docstring (最初だけ有効)。

- 影響: runtime 影響なし (no-op string expr) だが `help()` / mkdocstrings は
  間違った constant に rationale を attach。今後の onboarding で誤読される。
- Fix: lines 82-87 を `_MAX_RAW_FRAME_BYTES` 直下 (line 71 の下) に移動、
  `_LAYOUT_SNAPSHOT_TIMEOUT_S` の前の blank line を保持。

**H2 — Stale `-0.30` antagonism magnitude in docstrings (world/tick.py:122,129 +
_trait_antagonism.py:35)**

C5 retune で antagonism table 値を `-0.30 → -0.10` に変更したが docstring 3 箇所
が古い。さらに導出値も `-0.10 * 0.5 = 0.05` であって `0.15` ではない:

- `world/tick.py:122` "_-0.30 magnitude (kant<->nietzsche)_"
- `world/tick.py:129` "_A -0.30 antagonism delta therefore raises emotional_conflict by 0.15_"
- `_trait_antagonism.py:35` "_-0.30 is the calibrated magnitude_"

コード自体は table の `-0.10` を消費して正しく動作。docstring のみ drift。

- 影響: ε Plan agent が emotional_conflict cycle を retune するときの mental
  model が壊れる。documentation drift in the same file as live constants は HIGH
  扱いが妥当。
- Fix: 3 箇所すべてを `-0.10` に揃え、derived `0.15 → 0.05` に訂正、
  "_value as of C5 retune; see observation.md_" 注記を追加。

### MEDIUM (ε に組み込む)

**M1 — `maybe_promote_belief` の boundary test 欠損**

`test_belief_promotion.py` は `affinity=0.30` (well below) と `BELIEF_THRESHOLD-0.01`
(just below) は cover するが `affinity == BELIEF_THRESHOLD` ちょうどが無い。gate
は strict less-than (`abs(bond.affinity) < threshold`) なので exact boundary は
pass する契約。同様に `ichigo_ichie_count == BELIEF_MIN_INTERACTIONS` も exact
boundary 欠損。

- Fix: parametrised に `(BELIEF_THRESHOLD, BELIEF_MIN_INTERACTIONS, True)` と
  `(BELIEF_THRESHOLD - 0.001, BELIEF_MIN_INTERACTIONS, False)` を追加。

**M2 — `_maybe_persist_belief` / `_make_relational_sink` が `runtime._agents`
にアクセス (bootstrap.py:206,224,318)**

R3 L3 で「テスト側は LOW」だった `_agents` access が δ で **production bootstrap
の hot path** に escalate (毎 dialog turn で発火)。WorldRuntime の内部 dict
refactor (M9 sharding 等) で silent breakage の risk。3 箇所 SLF001 suppression。

- Fix: `WorldRuntime.get_agent_state(agent_id) -> AgentState | None` を public
  にする (read pattern は既 public の `get_bond_affinity` / `get_agent_zone` と
  同形)。同様に `MemoryStore.upsert_semantic_sync` / `add_sync` を public 化。
  composition root から SLF001 を 3 箇所削除。

**M3 — `_maybe_persist_belief` の except scope 狭すぎ (bootstrap.py:222-231)**

`_upsert_semantic_sync` は `sqlite3.IntegrityError` (CHECK 違反) や
`DatabaseError` (corruption) も raise しうる。`except sqlite3.OperationalError`
だけでは sink chain を crash させる。

- Fix: `except sqlite3.DatabaseError` (`OperationalError` と `IntegrityError`
  の親) に拡張。fire-and-forget sink contract に整合。

**M4 — `_classify_belief` boundary at exactly `_TRUST_FLOOR` 未テスト**

`affinity >= _TRUST_FLOOR` (trust)、`affinity <= -_TRUST_FLOOR` (clash) の境界
`0.70` / `-0.70` ちょうどが parametrised に無い。`>=` を `>` に flip した時
silent regression。

- Fix: `(0.70, "trust")`、`(-0.70, "clash")` を `test_belief_kind_classification`
  に追加。

**M5 — `test_slice_delta_e2e.py` も `runtime._agents` を 5 箇所で叩く (lines
157-158, 199-200, 230)**

M2 の test 側 mirror。M2 で public accessor を land したら同時に migrate。

- Fix: M2 と bundle、`runtime.get_agent_state(_agent_id("kant"))` に置換。

**M6 — `_compute_confidence` の overflow path に explicit テスト無し**

`min(1.0, ...)` の clamp は code には在るが、現行 test
`test_confidence_scales_with_magnitude_and_interactions` は `BELIEF_MIN_INTERACTIONS*2`
+ `affinity=0.95` で `1.9 → min(1.0, 1.9) = 1.0` を **incidental** に通っているのみ。

- Fix: `test_confidence_clamps_at_one` を追加 (`interactions=100`, `affinity=1.0`)。

### LOW (m9-lora 以降)

**L1 — `_trait_antagonism.py` module-level docstring に "-0.30 is the calibrated
magnitude"**

H2 と部分的に重複だが module-level の段落。H2 fix 時に同時に揃える。

**L2 — `SemanticMemoryRecord.embedding` defaults to `[]` for belief promotions
(belief.py:199)**

vec table 未投入なので `recall_semantic` 経由では belief row が見えない。意図的
だが、m8-affinity-dynamics Critic が Python `recall_semantic` path で query する
場合は WHERE belief_kind IS NOT NULL に切り替える必要。schema 注記を docstring
に追加すべき。

**L3 — `recent_transcript` parameter on `compute_affinity_delta` is consumed
only via `del` (relational.py:201)**

δ+ extension 用 reservation。dead code。`mypy --strict` も ruff も flag しない
が、m8-affinity-dynamics で trend modifier 実装時に `del` を外して実消費する。

**L4 — `_make_relational_sink` closure captures `persona_registry` dict by
reference**

現状 registry は bootstrap で 1 回構築のみ、mutation なし。dynamic persona-load
が来た時のために `dict(persona_registry)` shallow copy 防御は defensive。

**L5 — `test_slice_delta_e2e.py` が `store._ensure_conn()` を直接 query
(lines 274, 323)**

raw SQLite access が MemoryStore 抽象を bypass。schema change で SQL レベルで
break。`MemoryStore.list_semantic_by_agent(... where_belief_kind_not_null=True)`
が clean だが test scaffolding は LOW。

### Confirmations (no action)

| # | 観点 | 結論 |
|---|---|---|
| C1 | Layer 境界 (cognition / world / memory / schemas) | clean、bpy / cloud API import なし |
| C2 | 半数式 `next = prev*(1-decay) + impact*weight` | CSDG faithful、clamp 二段 (delta + result) 正しい |
| C3 | 双方向 delta が persona 結合で非対称 | 各側独立 (decay∝neuroticism、weight∝extraversion) で正しい |
| C4 | belief deterministic-id upsert (`belief_<a>__<b>`) | collision-free、INSERT OR REPLACE で max 2 rows / dyad |
| C5 | emotional_conflict write (×0.5) + decay (-0.02/tick) cycle | self-consistent、12 turn で ~0.6 まで accumulate (test 確認済) |
| C6 | `iter_dialog_turns(exclude_persona, limit)` SQL push (R3 H3) | 解消、index `ix_dialog_turns_persona` で cover、export CLI と両立 |
| C7 | `_LAYOUT_SNAPSHOT_TIMEOUT_S=2.0` fallback | TimeoutError → empty WorldLayoutMsg、Godot BoundaryLayer graceful (R3 M5 解消) |
| C8 | SCHEMA_VERSION `0.6.0-m7g → 0.7.0-m7d` | 全 field default 安全、`_migrate_semantic_schema` idempotent |
| C9 | Reflector `persona_resolver` injection (R3 M3) | 解消、unit test の None default も維持 |
| C10 | `_decision_with_affinity` sort key `(abs(affinity), tick)` (R3 M2) | 解消、Godot ReasoningPanel 並びと整合 |

### Summary

| Severity | Count | 主な item |
|---|---|---|
| HIGH | 2 | docstring drift のみ (logic change なし、5 分 patch) |
| MEDIUM | 6 | boundary test (M1, M4)、public accessor refactor (M2, M5)、catch scope (M3)、overflow test (M6) |
| LOW | 5 | docstring align (L1)、embedding query 戦略 (L2)、dead param (L3)、closure capture (L4)、test 抽象 (L5) |
| Confirmations | 10 | layer / formula / asymmetric delta / upsert / conflict cycle / SQL push / timeout fallback / schema migration / reflection / sort key |

### 結論: **Slice ε scope は H1+H2 (5 分) → M2+M5 bundle (8 SLF001 削除) → M1+M4+M6
(boundary 強化) → M3 (catch 拡張) を主軸**

それに既知 deferred (gateway WS log noise / session_phase D5 / persona-distinct
silhouette / LLM unparseable rate watch) を集約 → Plan mode + Opus + /reimagine
で 3-5 axis に整理する。L1-L5 は m9-lora バックログへ。
