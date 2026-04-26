# M7 Slice ε — Hygiene & Deferred Aggregation (post-/reimagine)

## 背景

M7 Slice δ (PR #95-#99) と M8 scaling-bottleneck-profiling (PR #100) と Godot
schema bump (#101) が main に landed (HEAD `070c0ba`、2026-04-26)。M7 関係性
ループ本体 (γ→δ) は完成し、live G-GEAR 5/5 PASS 達成済。一方で、δ post-merge
review (R4、`.steering/20260426-m7-slice-delta/decisions.md` §R4) と既知
deferred (live-fix D2/D3、M8 D5、δ C3 #3) が **集約されないまま分散** している。

ε は M7 の **最終 slice** として、これら hygiene 系 residual を 2 PR に分けて
land し、M9 (LoRA / persona-distinct silhouette) と M10-11 に綺麗な土台を
渡すことが目的。新規機能ではなく **集約 + 微改善** の slice。

**Plan mode + /reimagine を経た scope 確定** (本 dir の Plan
`/Users/johnd/.claude/plans/breezy-riding-valley.md` 参照):

1. 新 `SessionPhase` enum を作らず **既存 `EpochPhase` (schemas.py:219)** を
   再利用する (3-way naming collision 回避)
2. R4 M2 + M5 + L2-L5 (SLF001 wrapper 化と関連) は **新タスク
   `m9-belief-persistence-extraction`** で `BeliefPersistenceService` 抽出として
   処理 (ε で wrapper 入れると m9 で削除される無駄作業のため)
3. live-fix D3 (LLM unparseable rate) は **新タスク
   `infra-health-observability`** で扱う (relational saturation 軸との混淆を
   避けるため、scaling_metrics.json には入れない)

## ゴール — 2 PR shared feature branch

`feat/m7-slice-epsilon` ブランチ上で 2 PR を順次 land。M7 ledger は単一 slice
として symmetry を維持。

- **PR-ε-1** (`chore/m7-delta-followups`、no schema bump): R4 hygiene + gateway
  log demote + boundary tests。Mac 単独で acceptance、G-GEAR 不要。
- **PR-ε-2** (`feat/m7-epoch-phase-filter`、schema bump 0.7.0-m7d → 0.8.0-m7e):
  `dialog_turns.epoch_phase` 列追加 + `aggregate()` の AUTONOMOUS-only filter。
  G-GEAR で run-01-epsilon を実施し、δ acceptance 5/5 gate に regression なしを
  確認する。

## スコープ

### 含むもの

#### PR-ε-1 (no schema bump)
- R4 H1: `gateway.py:71-87` orphaned docstring を `_MAX_RAW_FRAME_BYTES` 直下に
  戻す
- R4 H2 + L1: `world/tick.py:122,129` と `_trait_antagonism.py:35` の `-0.30`
  を `-0.10` に、derived `0.15` を `0.05` に訂正、retune 注記追加
- live-fix D2: gateway `_recv_loop` の `WebSocketDisconnect` clean closure を
  `DEBUG` に降格、unit test 追加
- R4 M3: `bootstrap.py:225, 319` の `except sqlite3.OperationalError` を
  `except sqlite3.DatabaseError` (`IntegrityError` も親で catch) に拡張、
  `IntegrityError` 注入 test 追加
- R4 M1 + M4 + M6: belief boundary tests 5 件追加
  (`test_belief_promotion.py`)

#### PR-ε-2 (schema bump 0.7.0-m7d → 0.8.0-m7e)
- `dialog_turns.epoch_phase` 列追加 (NULLable、default `EpochPhase.AUTONOMOUS`)
- `_migrate_dialog_turns_schema` idempotent migration (既存 DB は ADD COLUMN)
- `MemoryStore.add_dialog_turn_sync(... epoch_phase=EpochPhase.AUTONOMOUS)` 引数追加
- `MemoryStore.iter_dialog_turns(... epoch_phase=)` filter kwarg 追加
- `evidence/scaling_metrics.py::aggregate()` の filter 有効化 + docstring 更新
- `bootstrap.py` の dialog turn sink で `runtime.run_lifecycle.epoch_phase` を
  stamp
- `SCHEMA_VERSION` bump
- Godot `CLIENT_SCHEMA_VERSION` 追従
- schema golden 再生成
- `tests/test_evidence/test_scaling_metrics.py` に filter test 2 件
- `tests/test_memory_store.py` に migration idempotent + column round-trip test

### 含まないもの (defer 先)

- **R4 M2 + M5 (SLF001 wrapper 化)** → `m9-belief-persistence-extraction`
  (`BeliefPersistenceService` 抽出として処理)
- **R4 L2-L5** (embedding query 戦略 / dead param / closure capture / test 抽象)
  → 同上
- **live-fix D3 (LLM unparseable rate watch)** → `infra-health-observability`
  (supervisor shutdown log line のみが暫定形)
- **δ formula calibration retune** (C5 値は frozen)
- **δ C3 #3 persona-distinct silhouette** → m9-lora
- **Q&A epoch driver** (`SessionPhase.QA_USER` 産出側) → m9-lora
- **M2 long-run / M1 N≥3 / agora cold zone calibration** → M9
- **MacBook reconnect storm investigation** → infra-health-observability

## 受け入れ条件 (PR-ε-1)

- [ ] R4 H1 解消: `_MAX_RAW_FRAME_BYTES` の docstring が原位置に戻り、
  `_LAYOUT_SNAPSHOT_TIMEOUT_S` の docstring が単一になっている
- [ ] R4 H2 + L1 解消: `world/tick.py:122,129` と `_trait_antagonism.py:35` の
  `-0.30` が `-0.10`、derived `0.15` が `0.05`、retune 注記入り
- [ ] live-fix D2 解消: gateway `_recv_loop` の `WebSocketDisconnect` (clean
  closure 1000) が `DEBUG` で log されるよう demote、`WebSocketDisconnect`
  単体テスト追加
- [ ] R4 M3 解消: `bootstrap.py` の except が `sqlite3.DatabaseError`
  (`OperationalError` + `IntegrityError` 親) に拡張、`IntegrityError` 注入で
  sink が raise しないことを assert する test 追加
- [ ] R4 M1 + M4 + M6 解消: belief threshold boundary、trust floor boundary、
  confidence overflow の 3 種類 boundary test 追加 (合計 5 ケース)
- [ ] `uv run pytest tests/` 全 pass
- [ ] `uv run ruff check src/ tests/` clean
- [ ] `uv run mypy src/` clean (現 strict なら strict)
- [ ] `decisions.md` に ε ADR D1-D4 を 5 節構造で記録
- [ ] code-reviewer agent で 1 round
- [ ] PR 起票 → review → merge

## 受け入れ条件 (PR-ε-2)

- [ ] `dialog_turns.epoch_phase` 列追加、`_migrate_dialog_turns_schema` が
  idempotent (2 回呼び出しで no-op) であることを test で assert
- [ ] `add_dialog_turn_sync(... epoch_phase=)` 引数追加、default が
  `EpochPhase.AUTONOMOUS` で backward compat
- [ ] `iter_dialog_turns(... epoch_phase=)` filter kwarg、None / 値ありの両 path
  test
- [ ] `evidence/scaling_metrics.py::aggregate()` が
  `epoch_phase=EpochPhase.AUTONOMOUS` で filter、docstring 更新
- [ ] `bootstrap.py` dialog turn sink で `runtime.run_lifecycle.epoch_phase`
  stamp、production runtime path で AUTONOMOUS のみ流れることを確認
- [ ] SCHEMA_VERSION bump `0.7.0-m7d → 0.8.0-m7e`、Godot CLIENT_SCHEMA_VERSION
  追従、schema golden re-bake
- [ ] pre-migration NULL row が AUTONOMOUS として扱われる (backward compat) を
  test で assert
- [ ] `uv run pytest tests/` 全 pass
- [ ] `uv run ruff check src/ tests/` clean、`uv run mypy src/` clean
- [ ] code-reviewer agent で 1 round
- [ ] G-GEAR で live run-01-epsilon (90-360s) → δ acceptance 5/5 gate に
  regression なし、`scaling_metrics.json` 出力に M1/M2/M3 が含まれる
- [ ] `run-guide-epsilon.md` 作成 (run-guide-delta.md の epsilon 版)
- [ ] PR 起票 → review → merge

## 関連ドキュメント

- `/Users/johnd/.claude/plans/breezy-riding-valley.md` — 本 ε の Plan
  (/reimagine 後の hybrid)
- `.steering/20260426-m7-slice-delta/decisions.md` §R4 — ε scope の主入力
- `.steering/20260426-m7-delta-live-fix/decisions.md` D2, D3 — gateway
  hygiene + LLM rate
- `.steering/20260425-m8-scaling-bottleneck-profiling/decisions.md` D5 —
  `epoch_phase` 統合の動機
- `.steering/20260425-m7-slice-gamma/decisions.md` §R3 — γ→δ scope の前例 mirror
- (新タスクの placeholder、ε merge 後に scaffold)
  - `.steering/<YYYYMMDD>-m9-belief-persistence-extraction/` — R4 M2/M5/L2-L5
  - `.steering/<YYYYMMDD>-infra-health-observability/` — live-fix D3 + reconnect
- `docs/architecture.md` — schema layer / wire compatibility
- `docs/development-guidelines.md` — review criteria
- CLAUDE.md — Plan mode + /reimagine 強制
