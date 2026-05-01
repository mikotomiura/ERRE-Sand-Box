# 設計 (v1)

> **Status**: v1 草案。本ファイルは `/reimagine` で `design-v1.md` に退避され、
> ゼロから v2 を再生成して比較した上で `design-final.md` に確定される。
> 第一案として「現実的でしっかり通る」案を提示。alternative は併記しない
> (それは /reimagine の役割)。

## Hardware allocation

| Phase | Subtask | Owner | Machine | VRAM/CPU | Est. Hours | Sync point |
|---|---|---|---|---|---|---|
| P0a | LIWC license decision tree close | Claude | Mac | CPU only | 1h | `blockers.md` 1 件 close |
| P0b | Parquet schema + path 規約 + contract test | Claude | Mac | CPU only | 3h | schema PR merge candidate |
| P1 | Tier A 5 metric (Burrows / MATTR / novelty / NLI / LIWC-alt) | Claude | Mac | CPU + MPS (MPNet 推論) | 6h | unit test 緑 |
| P1b | sidecar writer + training-view filter | Claude | Mac | CPU | 2h | contract_snapshot 緑 |
| P2 | `GoldenBaselineOrchestrator` + seed mgmt + cooldown bypass | Claude | Mac | CPU | 4h | dry-run 50 turn 緑 |
| P3 | golden baseline 採取 (3 persona × 5 run × 500 turn) | Operator | **G-GEAR** | RTX 4090 24GB / qwen3:8b FP16 ~16GB | **6-12h × 3 ≈ 24h wall** | Parquet artifact 受領 |
| P4 | Tier B 実装 (Vendi / IPIP-NEO loop / Big5 ICC) | Claude | Mac | CPU + 7B-Q4 借用 (~5GB MPS) | 5h | unit test + bootstrap CI 数値確認 |
| P4b | Tier B 後付け実行 (Mac 上、Q4 ローカル) | Claude | Mac | ~5GB MPS | 2-3h | sidecar 拡張 |
| P5 | bootstrap CI + 2-of-3 quorum logic (judgment 抜き) | Claude | Mac | CPU | 3h | sub-metric 3 個 ready |
| P6 | Tier C nightly infra (Prometheus 2 / G-Eval、agent 停止時) | Operator | **G-GEAR** | judge LLM (~24GB、agent 停止条件) | 4h (infra のみ、本番 run は M9-C-adopt) | runbook 草案 |
| P7 | Codex `gpt-5.5 xhigh` independent review | Claude | Mac | CPU | 1h | HIGH 全件反映、`design-final.md` 確定 |

**運用ルール**: Mac は設計・実装・schema・bootstrap CI 確認まで。G-GEAR は (a) 7500 turn
continuous run と (b) Tier C judge LLM dedicated slot のみ。VRAM contention 回避のため
両者は時間分離 (P3 の baseline 採取と P6 の Tier C は同時実行しない)。

## 実装アプローチ

### Parquet 物理分離 (DB5 HIGH-4 反映)

**別 Parquet file + path 規約 + Reader API で訓練 loader を構造的に閉じる**。

```
data/parquet/
├── raw_dialog/                     # metric-free training table
│   └── evaluation_epoch={false,true}/
│       └── persona_id=*/run_id=*/part-*.parquet
└── metrics/                        # sidecar evaluation metrics
    └── tier={A,B,C}/
        └── persona_id=*/run_id=*/part-*.parquet
```

- **raw_dialog 9 fields**: `turn_id (uuid7)` / `run_id` / `persona_id` / `agent_id` /
  `mode` / `phase` / `utterance` / `timestamp` / `reasoning_trace`
- **metrics schema**: `turn_id` (join key) / `metric_name` / `metric_value` /
  `window_size` / `computed_at` / `git_sha` / `model_versions`
- **training-view contract**: `RawDialogReader.training_view()` API は
  `evaluation_epoch=false` partition のみ open し、sidecar path を返さない。
  metric column 統合 file ではないため、loader が物理的に metric を読めない。

**根拠**: 同 file 内 partition では training loader が metric column へ
open 可能で DB5 (HIGH-4) を構造的に守れない。tier 別に file 分けるのは Tier C の
遅延書き込みが Tier A の partition rewrite を起こさないため。

### Library 選定

**pyarrow (Parquet I/O 基盤) + polars (分析 layer)** の併用。

- pyarrow: Parquet 仕様の reference 実装、schema validation 厳密 (DB5 contract test
  に必須)
- polars: lazy + 列志向で 7500 turn × N metric の bootstrap resample が高速
- pandas は primary 採用しない (大規模 lazy 不向き、依存に間接含有)

### LIWC alternative (Option C)

**spaCy + 自前 dictionary、Empath を seed として bootstrap**。

- (1) 商用 license は zero-budget 制約に反し決裁 latency 大 (棄却 A)
- (2) Empath 単独は LIWC 等価でなく Big5 claim が立たない (棄却 B 単独)
- (3) Burrows のみは Big5 を諦めることになり DB9 sub-metric `big5_stability_icc` の
  輸入経路 (IPIP-NEO 自己申告) と分離できなくなる (棄却 D)
- (4) spaCy 自前は category 設計が zero cost、Empath を seed にして 3 persona に
  必要な軸 (cognition / affect / certainty / negation / temporal / sensory /
  formality) のみ整備すれば足りる

**Honest framing** (LOW-2 反映): Big5 claim は IPIP-NEO 自己申告経路に集約し、
LIWC-alt は Tier A の continuous text trait としてのみ使う。これで `blockers.md`
LIWC license 1 件 close。

### Golden baseline 採取設計

**新規 `GoldenBaselineOrchestrator` を `eval/` 配下に追加** (`InMemoryDialogScheduler`
を直接拡張せず wrapper)。

- 500 turn continuous は `RunLifecycleState` の cooldown / timeout を bypass する
  eval-only mode が必要。scheduler 本体に分岐を増やすと autonomous loop の
  不変条件を汚すため、wrapper 経由で `EvaluationMode` flag を inject し tick
  driver / sink を交換する。
- **RNG seed 戦略**: `seed = hash((persona_id, run_idx, "m9-eval-v1"))` で
  deterministic、5 run × 3 persona = 15 seed を `seeds.json` に commit。turn 内
  sampling は `numpy.random.Generator(PCG64(seed))` で stream 化。Ollama
  temperature は persona YAML の `default_sampling` を respect。

### Tier C nightly infra

**asyncio scheduler + file-lock guard で「agent 停止時のみ」を mechanism 化**。

- cron は VRAM 状態を知らず、queue は overkill (solo project)
- `ollama ps` を polling し idle 確認 → judge LLM load → batch 完了 → unload
- `/var/run/erre-eval-tier-c.lock` で agent autonomous loop と相互排他
- M9-eval-system では infra のみ実装、本番 run (Prometheus 2 / G-Eval / FANToM /
  ROSCOE) は M9-C-adopt に移行

## 変更対象

### 修正するファイル (additive only、破壊禁止)

- `src/erre_sandbox/contracts/thresholds.py` — `TierAThresholds` / `TierBThresholds` /
  `TierCThresholds` Pydantic frozen 追加。`M2_THRESHOLDS` は不変
- `src/erre_sandbox/evidence/metrics.py` — Tier A 5 metric を既存
  `aggregate(db_path)` interface に揃えて追加 (既存 `compute_self_repetition_rate` /
  `compute_cross_persona_echo_rate` / `compute_bias_fired_rate` を defensive canary
  にそのまま reuse)
- `src/erre_sandbox/cli/baseline_metrics.py` — `--parquet-out` / `--tier {A,B,C}`
  flag 追加 (既存 JSON out は破壊しない)
- `src/erre_sandbox/integration/dialog.py` — `EvaluationMode` flag (default False)
  と sink injection point 1 つ追加。既存挙動は default で完全維持
- `personas/{kant,nietzsche,rikyu}.yaml` — `ipip_neo_short` optional field 追加
  (additive)
- `pyproject.toml` — dependency 追加 (下記 §影響範囲)

### 新規作成するファイル

`src/erre_sandbox/eval/` 配下:
- `__init__.py` — eval layer エントリ
- `parquet_io.py` — pyarrow writer/reader、raw + sidecar 物理分離 contract enforcement
- `tier_a/{burrows,mattr,novelty,nli,liwc_alt}.py` — 5 metric
- `tier_b/{vendi,ipip_neo,big5_icc}.py` — 3 metric
- `tier_c/{prometheus,geval,scheduler}.py` — judge LLM infra
- `bootstrap.py` — bootstrap CI + 2-of-3 quorum logic (decision は別 layer)
- `orchestrator.py` — `GoldenBaselineOrchestrator` (3×5×500)
- `seeds.json` — 15 seed manifest

CLI:
- `src/erre_sandbox/cli/golden_baseline.py` — 採取 CLI
- `src/erre_sandbox/cli/eval_pipeline.py` — Tier A/B post-hoc 計算 CLI

Tests:
- `tests/test_eval/test_parquet_contract.py`
- `tests/test_eval/test_tier_a.py`
- `tests/test_eval/test_tier_b.py`
- `tests/test_eval/test_bootstrap_ci.py`
- `tests/test_eval/test_orchestrator.py`
- `tests/test_eval/fixtures/synthetic_4th_persona.yaml` — DB7 LOW-1 反映

Steering:
- `.steering/20260430-m9-eval-system/codex-review-prompt.md` — Phase 1 step 3 の入力
- `.steering/20260430-m9-eval-system/codex-review.md` — verbatim 保存
- `.steering/20260430-m9-eval-system/decisions.md` — 新タスク独自 ADR (任意)

### 削除するファイル

原則無し。additive only。

## Tier 実装順序 (依存関係)

```
[parallel-OK]
  P0a LIWC option C decision    ──┐
  P0b Parquet schema + contract ──┤── DB5 contract gate
                                  │
[blocking]                        ▼
  P1  Tier A 5 metric  ◄── needs LIWC choice + Parquet writer
  P2  GoldenBaselineOrchestrator  ◄── needs Parquet writer (Tier A 並行可)
  P3  golden baseline 採取  ◄── needs P1 + P2 (G-GEAR、夜間連続)
  P4  Tier B 3 metric (post-hoc on 採取済 Parquet)
  P5  bootstrap CI logic  ◄── Tier B 出力 schema 確定後
  P6  Tier C nightly infra  ◄── 並行可、judgment 出力は M9-C-adopt
  P7  Codex review → HIGH 反映 → design-final.md
```

**DB9 sub-metric 3 個 (Vendi / Big5 ICC / Burrows Delta) ready 時期**:
- Burrows: P1 完了時 (per-turn computed)
- Vendi / Big5 ICC: P4 完了時 (per-100-turn computed)
- bootstrap CI 計算 ready: **P5 完了時 = タスク後半 (M9-C-adopt 直前)**

## 影響範囲

### 既存テストへの impact

破壊しないこと前提:
- `contract_snapshot` test (frozen `M2_THRESHOLDS` / `SCHEMA_VERSION="0.10.0-m7h"` /
  `DialogTurnMsg` / `RunLifecycleState`) — 全緑維持
- `integration/dialog.py` の `EvaluationMode` 追加は default False で既存全テスト pass
- 既存 `evidence/metrics.py` interface (`compute_*` 関数群、`aggregate(db_path)`) は
  signature 不変

### contracts/ への additive 変更

- 新規 `Tier{A,B,C}Thresholds` Pydantic frozen 追加 (`M2_THRESHOLDS` 並列、独立 snapshot)
- 既存 `M2_THRESHOLDS` snapshot は再生成しない

### pyproject.toml dependency 追加

```toml
[project.dependencies]  # 既存に追加
"pyarrow>=17,<19",
"polars>=1.5,<2",
"vendi-score>=0.0.3",
"sentence-transformers>=3,<4",
"pingouin>=0.5,<1",
"spacy>=3.7,<4",
# NLI: 既存 transformers + DeBERTa-v3-base-mnli を借用 (新規依存無し)

[dependency-groups.eval]  # 新規 group、core 依存に汚染しない
"empath>=0.89",  # LIWC-alt の seed
```

`spacy` の `en_core_web_sm` モデルは初回 `python -m spacy download en_core_web_sm`
で取得 (CI でも cache 化)。

## 既存パターンとの整合性

- **Pure-function metric pattern**: `evidence/metrics.py` の `compute_*` 関数群と
  `aggregate(db_path)` パターンを Tier A 5 metric にも踏襲
- **CLI subcommand**: 既存 `cli/{baseline_metrics,scaling_metrics,export_log}.py` の
  argparse + JSON/JSONL out パターン
- **Pydantic frozen contracts**: `contracts/thresholds.py` の `M2_THRESHOLDS` style
- **Persona YAML additive**: `schema_version="0.10.0-m7h"` 維持、既存 field 不変、
  `ipip_neo_short` のみ optional 追加
- **MemoryStore 経由**: `memory/store.py` の `iter_dialog_turns()` で turn 取得し、
  Parquet sidecar の join key として `turn_id` を使う

## テスト戦略

### Contract test (実装中、pytest)

- `test_parquet_contract.py`:
  - raw_dialog Parquet が metric column を持たないこと
  - `evaluation_epoch=false` partition のみ training loader API が露出すること
  - metrics sidecar が必ず `turn_id` を持つこと
  - tier 別 partition が混入しないこと
- `test_bootstrap_ci.py`:
  - N(μ=0, σ=1) を n=500 から 1000 resample で 95% CI が ±0.087±tol に収束
  - Vendi が orthogonal one-hot で score=N に収束
  - Big5 ICC が同一回答列で 1.0 に収束
- 既存 `tests/test_contract_snapshot/` 全緑維持

### DB7 LOW-1 (synthetic 4th persona heldout fixture)

- `fixtures/synthetic_4th_persona.yaml`: Big5 が 3 既存 persona と直交する架空
  thinker
- eval pipeline を 50 turn で走らせ、metric が NaN/crash 無く計算
- 3-persona overfitting 防止

### Tier acceptance (実装後、pytest)

- `test_tier_a.py`: 5 metric が synthetic + 4th persona heldout fixture で
  NaN/crash 無く計算
- `test_tier_b.py`: 3 metric が known distribution で expected 値
- `test_orchestrator.py`: dry-run 50 turn で seed deterministic、Parquet 出力
  構造が path 規約に従う

### Burrows multi-lang (blockers.md 暫定方針)

- per-language reference でしか比較しない契約を test 化 (cross-lang を呼ぶと例外)

### Golden baseline integrity (G-GEAR run 後、CLI)

- `python -m erre_sandbox.cli.eval_pipeline --validate data/parquet/raw_dialog/` →
  3 persona × 5 run × 500 turn = 7500 turn 完全
- `python -m erre_sandbox.cli.eval_pipeline --bootstrap-ci data/parquet/metrics/` →
  DB9 sub-metric 3 個に CI 数値、persona-discriminative 観察を `blockers.md`
  L89-93 に追記

## ロールバック計画

- **raw_dialog Parquet** = source of truth、不変。corruption 時は採取再走 (G-GEAR
  24h コスト) 以外に rebuild 経路無し → **daily snapshot を別 disk にコピー**を
  運用ルール化
- **metrics sidecar** = raw から完全再計算可能。schema 不整合や bug fix 時は
  `tier={A,B,C}/` partition を rm → CLI 再走。training loader は raw のみ参照
  のため metrics 削除に依存しない
- **bootstrap CI** = sidecar から完全再走可能。sub-metric 3 個の選定変更
  (DB9 re-open) も `eval/bootstrap.py` の input 列を差し替えるだけで rerun 可
- **`GoldenBaselineOrchestrator` の bug**: 採取済 raw が安全である property 上、
  orchestrator 修正後の再採取は失敗 run のみ run_id 単位で追加可能 (5 run の
  独立性が seed 分離で保たれている前提)
- **dependency 追加の rollback**: pyarrow / polars / vendi-score 等は core 依存に
  入るが、eval/ layer は新規追加なので `pip uninstall` + `eval/` 削除で本体機能に
  impact 無し。Empath は `[dependency-groups.eval]` で隔離済

## リスクと反復前提 (/reimagine + Codex review で潰す)

第一案で見落とすリスクが高い 5 件:

1. **block bootstrap 要否**: turn は autoregressive で iid 仮定不成立、plain
   bootstrap で起草しているが statistical validity が要再検討
2. **IPIP-NEO 自己申告 bias**: 7B-Q4 agent の acquiescence bias で Big5 ICC が
   見かけ高くなる risk、observer-judge 経路を併用しない選定根拠が薄い
3. **Parquet partition cardinality 爆発**: `tier × persona × run × turn-bucket` で
   part-file 肥大化、column group 単一 file 戦略の優劣
4. **Semantic novelty embedding 選定**: MPNet 単独は philosophical 用語に
   under-represented、persona 別 reference embedding で normalize 要否
5. **G-GEAR 24h wall 楽観値**: 1-3s/turn は楽観、ERRE 本来の cognitive habit
   込みで 5-10s/turn なら 7500 turn は 60h 超で solo cadence 圧迫、budget 前提を
   measurement first にすべき

### `/reimagine` で再検討すべき open question

1. raw + sidecar を同 Parquet 内 column group で論理分離 + reader 層で contract
   強制する方が運用簡素では
2. golden baseline を自然言語 dialog ではなく fixed prompt set への response で
   代替し 7500 turn → 1500 prompt に削減する案
3. Tier B を per-100 ではなく per-run aggregated 単発 + per-turn rolling の
   二層に再分解する案
4. LIWC-alt を Option C ではなく Empath OSS + honest framing に倒し自前 dictionary
   work を削る案
5. Tier C を asyncio ではなく systemd-timer / launchd で OS 任せにする案

### Codex 独立 review に回すべき箇所

- DB5/DB6 物理分離の Parquet 構造の代替案 (column group / 単一 file 戦略の優劣)
- bootstrap CI の statistical validity (block bootstrap 要否、effective sample size)
- IPIP-NEO 自己申告 vs observer-judge の Big5 ICC 経路選定
- spaCy 自前 dictionary を「LIWC alternative」と呼ぶ honest framing の限界
- Tier C judge LLM の VRAM contention mechanism (file-lock の race condition)
