# M7 Slice ε — Decision Log

> 5-section ADR pattern (現状 / 選択肢 / 採用 / 根拠 / 次アクション)、M8 spike
> decisions.md と同形。Plan mode + /reimagine の双案独立 dispatch を経て確定。

## D1 — ε は **2 PR shared feature branch** で land する

### 現状

requirement.md 初版は「7 commit one-PR bundle」を前提に書かれていたが、Plan
mode で /reimagine の独立双案 (initial = bundle / reimagined = micro-PR + defer)
を比較した結果、bundle 案には以下の failure mode があると判明:

- 9 ファイル 3 rationale が 1 PR review に conflate して triage 不能
- schema bump (`SessionPhase` 新設想定) が docstring fix を block する

### 選択肢

- **A** (bundle): 7 commit を 1 PR に集約、M7 ledger を 1 entry で閉じる
- **B** (5 micro-PR): R4 docstring / gateway log / boundary tests / except 拡張 /
  schema-bumping filter を完全分離 (5 PR)
- **C** (hybrid 2-PR shared branch): `feat/m7-slice-epsilon` 上で
  PR-ε-1 (no-bump hygiene) + PR-ε-2 (bump + filter) の 2 PR

### 採用

**C (hybrid)** を採用。M7 ledger は単一 slice (ε) として symmetry 維持、PR は
schema-bump-or-not で 2 分割。

- **PR-ε-1** `chore/m7-delta-followups` (no schema bump、5 commit):
  R4 H1+H2+L1 docstring / gateway WS demote / except 拡張 / boundary tests /
  ADR docs。Mac 単独で acceptance、G-GEAR 不要。
- **PR-ε-2** `feat/m7-epoch-phase-filter` (schema bump 0.7.0-m7d → 0.8.0-m7e、
  3 commit): `dialog_turns.epoch_phase` 列追加 + `aggregate()` filter +
  Godot/golden 追従。G-GEAR で run-01-epsilon を実施し δ 5/5 gate に regression
  なしを確認。

### 根拠

- bundle (A) は schema bump rationale が docstring fix を block して review
  surface が conflate
- micro-PR (B) は M7 ledger の symmetry を破壊し、ε directory の存在意義が薄れる
- hybrid (C) は M7 ledger と review surface の両方を満たす

### 次アクション

- branch `feat/m7-slice-epsilon` で commit を順次 land (本セッション継続中)
- PR-ε-1 merge 後に PR-ε-2 を起票

## D2 — R4 M2 + M5 + L2-L5 (SLF001 公開化等) は **新タスク
`m9-belief-persistence-extraction`** へ defer

### 現状

R4 M2 は `runtime._agents` / `memory._upsert_semantic_sync` / `memory._add_sync`
の SLF001 access を bootstrap.py 3 箇所 + e2e test 5 箇所で削除する提案。Plan A
は wrapper accessor 化を推奨したが、Plan B reimagine は **shallow fix** と評価
した。

事実:
- `bootstrap.py` は 641 LOC、`_maybe_persist_belief` (45 LOC) +
  `_make_relational_sink` (115 LOC closure) が composition root に同居
- 両 closure が `runtime` + `memory` + `persona_registry` + per-call `turn`
  を参照 — これは **service** の構造、composition root は wiring のみであるべき
- R4 L3 (`recent_transcript` dead param)、L4 (closure capture)、L5 (raw SQL
  access) も同じ抽出で同時に解消可能

### 選択肢

- **A**: ε 内で `WorldRuntime.get_agent_state()` + `MemoryStore.upsert_semantic_sync` /
  `add_sync` を public 化 (wrapper accessor、~30 LOC + 8 SLF001 削除)
- **B**: 新タスク `m9-belief-persistence-extraction` で
  `BeliefPersistenceService` 抽出 (~1-1.5 日、bootstrap 641→~450 LOC)
- **C**: ε で部分的 (M3 except 拡張のみ)、M2/M5/L2-L5 は B に defer

### 採用

**C を選択** (Plan B 推奨に user 承認 = 2026-04-26 hybrid Plan の AskUserQuestion
回答)。M3 (1-line except 拡張) は ε で land、M2/M5/L2-L5 は新タスク
`m9-belief-persistence-extraction` で service 抽出として処理。

### 根拠

- A の wrapper は m9 で service 抽出時に削除される作業 → review budget の無駄
- m9-LoRA で per-persona 並列 cognition cycle を回す予定であり、`_make_relational_sink`
  closure が再エントラント問題に当たる前に service 化が必要 (m9-LoRA より先に
  belief-persistence-extraction を land 推奨)
- M3 は 1-line correctness fix (`OperationalError` → `DatabaseError`) で
  屋台骨 refactor とは独立、ε で land しても m9 で削除されない

### 次アクション

- ε merge 後に `.steering/<YYYYMMDD>-m9-belief-persistence-extraction/` を
  scaffold、requirement.md に R4 M2/M5/L2-L5 を集約
- service 設計は Plan mode + /reimagine 必須 (composition root から service
  への抽出は高難度設計)

## D3 — live-fix D3 (LLM unparseable rate watch) は **新タスク
`infra-health-observability`** へ relocate

### 現状

requirement.md 初版は LLM unparseable rate を `scaling_metrics.json` の
`llm_unparseable_plan_count` / `_total_plan_calls` / `_unparseable_rate` field
として追加する提案。Plan B reimagine は **観測軸の混淆** と評価した。

事実:
- `scaling_metrics.json` は relational saturation 用 (M1 pair information gain,
  M2 late turn fraction, M3 zone KL — `.steering/20260425-m8-scaling-bottleneck-profiling/decisions.md` D1-D4)
- LLM JSON parse rate は **infrastructure health** の観測軸 (gateway health 系
  metric と同類)、relational とは threshold class も cadence も異なる
- δ run-02 で観察した MacBook reconnect storm pattern (1-2 接続/秒) も
  infrastructure 軸 (live-fix decisions.md には記載なし、profile.md 派生観察)

### 選択肢

- **A**: scaling_metrics.json に正式 field として追加 (informational only)
- **B**: PR-ε-1 commit 内で supervisor shutdown log line のみ (~10 LOC)
- **C**: 新タスク `infra-health-observability` に分離、暫定形は log line、
  必要なら別 schema (`infra_health.json`) を後で立てる

### 採用

**C を選択** (user 承認 = 2026-04-26 AskUserQuestion 回答、Recommended)。
ε scope からは外し、`infra-health-observability` 新タスクで処理。MacBook reconnect
storm も同タスクに集約予定。

### 根拠

- A は scaling_metrics の観測軸を混淆させ、M1/M2/M3 の純度を下げる
- B は ε に紛れ込ませることで scope を曖昧化
- C は観測軸を分離し、relational saturation と infra health を独立に進化させる

### 次アクション

- ε merge 後に `.steering/<YYYYMMDD>-infra-health-observability/` を scaffold
- 暫定形 (supervisor shutdown log line) を最初の commit、複数 run 横断比較が
  必要になった時点で別 schema 検討
- δ run-02 reconnect storm pattern の記録も同 dir に集約

## D4 — `EpochPhase` (既存 schemas.py:219) を **再利用**、新 `SessionPhase` は
作らない

### 現状

requirement.md 初版は「新 `SessionPhase` enum を schemas.py に追加」を提案。
Plan mode の Phase 3 (実コード Read による verify) で **3-way naming collision**
が発覚:

- `schemas.py:219::EpochPhase` (run-level: AUTONOMOUS / Q_AND_A / EVALUATION) —
  **既存**、`RunLifecycleState` も `WorldRuntime.transition_to_q_and_a` /
  `transition_to_evaluation` も完全実装済 (world/tick.py:393, 410)
- `integration/protocol.py:115::SessionPhase` (WS lifecycle:
  AWAITING_HANDSHAKE / ACTIVE / CLOSING) — **既存**
- 提案された新 `schemas.py::SessionPhase` — **重複**

`EpochPhase` の docstring (schemas.py:228-230) は protocol.py の `SessionPhase`
との衝突を明示警告している。

`evidence/scaling_metrics.py:553-557` の docstring は
"`session_phase == AUTONOMOUS`" でフィルタすると記述しているが、これは将来の
column 名であり enum 名は `EpochPhase` を再利用するべき。

### 選択肢

- **A**: 新 `SessionPhase` を schemas.py に追加 (Plan A 案、3-way collision)
- **B**: `EpochPhase` を再利用、column 名は `epoch_phase` で命名揃え
- **C**: column 名は docstring 通り `session_phase` のまま、enum 名は `EpochPhase`
  (column と enum の命名不揃い)

### 採用

**B を採用**。

- enum: 既存 `EpochPhase` を再利用、新規追加なし
- column: `dialog_turns.epoch_phase` (NULLable、default `EpochPhase.AUTONOMOUS`)
- field: `DialogTurnRecord.epoch_phase: EpochPhase = EpochPhase.AUTONOMOUS`
- aggregate filter: `iter_dialog_turns(epoch_phase=EpochPhase.AUTONOMOUS)`
- pre-migration NULL row は AUTONOMOUS として扱う (backward compat)

### 根拠

- `EpochPhase` は既に M8 ADR D3 (two-phase methodology) を意識して命名された
  正しい abstraction。重複の余地なし
- 命名揃え (enum/column/field/filter 全て `epoch_phase`) で読みやすさ向上
- 元 docstring の `session_phase` は将来 column 名の plan placeholder で、
  実装時に揃える機会
- C のような不揃いは 3-way collision を解消しないまま新たな読みにくさを生む

### 次アクション

- PR-ε-2 commit 1 で `dialog_turns.epoch_phase` 列追加 + `EpochPhase` 再利用
- `evidence/scaling_metrics.py:553-566` の docstring を `session_phase` から
  `epoch_phase` に書き換え

## D5 — Q&A epoch driver は m9-LoRA scope (ε では `EpochPhase.QA_USER` を
産出する path を作らない)

### 現状

`EpochPhase` には `Q_AND_A` 値があり、`WorldRuntime.transition_to_q_and_a()`
も実装済だが、**現状この transition を呼ぶ producer は存在しない** (CLI/UI/
researcher prompt 経路は m9 scope)。

### 選択肢

- **A**: ε で researcher prompt 経路 (Q&A driver) を最小実装し `Q_AND_A`
  産出を成立させる
- **B**: ε では `epoch_phase` を sink に通すだけ、`Q_AND_A` 産出は m9-LoRA へ。
  filter 動作は unit test (`Q_AND_A` row inject) で検証

### 採用

**B を採用**。

### 根拠

- ε scope の核は M8 D5 解消 (filter wiring) であり、Q&A driver はそれと独立な
  m9 機能
- live run-01-epsilon は autonomous-only なので filter は no-op、unit test で
  filter 機能を pin すれば run-time で active な動作は m9 で立ち上がってから
  検証して十分
- ε scope を膨らませない原則 (D2 と同じ思想)

### 次アクション

- PR-ε-2 commit 2 の filter test で `Q_AND_A` row を直接 inject する unit test
  を carry
- m9-LoRA タスクで CLI/UI 経由の researcher prompt を実装する際、
  `runtime.transition_to_q_and_a()` の caller を追加する

## D6 — δ formula calibration (C5 値) は **frozen**、ε では retune しない

### 現状

R4 H2 は docstring drift (古い `-0.30` magnitude) を指摘するが、コード中の
table 値は `-0.10` (C5 retune 後) で正しい。docstring を `-0.10` に揃える
hygiene fix と、formula 自体の retune は明確に区別する必要がある。

### 採用

ε では **docstring のみ揃える** (R4 H1+H2+L1 = PR-ε-1 commit 1)。formula 値
(`_IMPACT_*`、`_DECAY_*`、antagonism table、`BELIEF_THRESHOLD`、
`BELIEF_MIN_INTERACTIONS`) は **frozen**、ε scope の retune 候補なし。

### 根拠

- `.steering/20260426-m7-delta-live-fix/decisions.md` D1 で C5 値の "concentration
  > volume" 教訓を記録、live で 5/5 PASS 達成済
- formula 変更は ε scope (hygiene/集約) ではなく、ベンチマーク slice 相当の
  別 task (m9-LoRA か後続 slice) で扱うべき
