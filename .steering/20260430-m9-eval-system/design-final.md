# 設計 (final — ハイブリッド: v2 ベース + v1 補強 2 点 + 微調整 2 点 + Codex HIGH 5 件反映)

> **Status**: `/reimagine` 実施済 (v1 = `design-v1.md` に退避、v2 を生成、比較は
> `design-comparison.md`)。Codex `gpt-5.5 xhigh` independent review 完了
> (`codex-review.md`、HIGH 5 / MEDIUM 6 / LOW 1)、HIGH 全件を本文に反映済。
> MEDIUM は `decisions.md` に 5 要素 ADR、LOW は `blockers.md` に defer 済。
> 本ファイルは `design-final.md` への rename 候補。

## Hardware allocation

| Phase | Subtask | Owner | Machine | GPU/VRAM | Est. Hours | Sync point |
|---|---|---|---|---|---|---|
| P0a | LIWC Option D 確定 → `blockers.md` 1 件 close | Claude | Mac | CPU only | 0.5h | blockers.md commit |
| P0b | `contracts/eval_paths.py` (schema-guard) + CI grep gate 必須実装 | Claude | Mac | CPU only | 1.5h | contract test 緑 |
| P0c | `evidence/eval_store.py` (DuckDB connect / schema bootstrap / Parquet export) | Claude | Mac | CPU only | 2h | schema PR merge candidate |
| P1a | Tier A `evidence/tier_a/{burrows,mattr,nli,novelty,empath_proxy}.py` (sub-module 構造) | Claude | Mac | CPU + MPS (MPNet) | 6h | unit test 緑 |
| P1b | reference corpus pickle 整備 (Kant 独+英訳 / Nietzsche / Rikyu / synthetic 4th) | Claude | Mac | CPU only | 2h | fixture test 緑 |
| P2a | `golden/stimulus/{kant,nietzsche,rikyu}.yaml` 起草 (70 stimulus/persona × 3 巡 = 210 turn) | Claude | Mac | CPU only | 4h | review |
| P2b | `integration/dialog.py` への `golden_baseline_mode: bool` minimum patch + sink hook | Claude | Mac | CPU only | 2h | dry-run 50 turn 緑 |
| **P2c** | **External golden driver** (`evidence/golden_baseline.py`) を `schedule_initiate`/`record_turn`/`close_dialog` 公開 API のみで実装、**input queue 依存無し** (Codex HIGH-4 反映) | Claude | Mac | CPU only | 3h | unit test (synthetic 1 stimulus 駆動) 緑 |
| **P3a** | **Pilot run 200 turn × 両形式 × 3 persona の isolated 採取** (fresh scheduler/store/seed、golden baseline と完全分離、Codex HIGH-3 反映) | Operator | **G-GEAR** | 同上 | 6-8h | bootstrap CI width が両形式で測定可能、ratio 確定 |
| **P3a-decide** | P3a 結果から 200/300 ratio を確定 or 改訂、`blockers.md` ratio defer を close (Codex HIGH-3 反映) | Claude | Mac | CPU only | 1h | ratio 確定の ADR を `decisions.md` に記録 |
| P3 | golden baseline 採取 (3 persona × 5 run × 500 turn、確定 ratio で投入) | Operator | **G-GEAR** | RTX 4090 24GB / qwen3:8b FP16 ~16GB | **6-12h × 3 ≈ 24h wall (overnight × 2)** | DuckDB file → Mac へ rsync (CHECKPOINT 後、temp+rename rsync、`read_only=True`) |
| P4a | Tier B `evidence/tier_b/{vendi,ipip_neo,big5_icc}.py` 実装 | Claude | Mac | CPU + 7B-Q4 借用 (~5GB MPS) | 5h | unit test 緑 |
| P4b | Tier B 後付け実行 (採取済 raw_dialog から post-hoc) | Operator | G-GEAR | 7B-Q4 ~5GB | 2h | metrics schema 投入完了 |
| P5 | bootstrap CI + 2-of-3 quorum logic (DB9、`evidence/bootstrap_ci.py`) | Claude | Mac | CPU only | 3h | sub-metric 3 個 ready |
| P6 | Tier C nightly: systemd --user timer + flock + nvidia-smi preflight | Claude | Mac (作成) → G-GEAR (deploy) | 判定のみ | 4h | systemctl --user list-timers 緑 |
| P7 | Codex `gpt-5.5 xhigh` independent review → HIGH 全件反映 | Claude | Mac | CPU only | 1.5h | `design-final.md` rename |

**運用ルール**:
- Mac (master/dev) は設計・実装・schema・bootstrap CI・stimulus 起草まで担当
- G-GEAR (実行機) は (a) 7500 turn continuous baseline 採取、(b) IPIP-NEO sub-process、
  (c) Tier C judge LLM nightly slot のみ
- single-writer 原則: 1 マシン = 1 writer。DuckDB file は G-GEAR で書き、Mac は
  rsync 後 read-only で開く
- VRAM contention 回避: P3 baseline 採取と P6 Tier C nightly は時間分離 (systemd-timer
  の preflight が `nvidia-smi --query-gpu=memory.free` で free < 14GB なら skip + log)

## 実装アプローチ

### Parquet/DB 物理表現: DuckDB 単 file + named schema + 3 層 contract (v2 採用 + v1 強化)

**評価データ層は DuckDB 単 file**。training-loader API が唯一の entry point で、
`metrics` schema を SELECT したら `EvaluationContaminationError` を raise。Parquet は
**二次的な export 形式** (`COPY ... TO ... (FORMAT PARQUET)` で nightly 出力、
downstream 分析 / 公開用)。

**3 層 contract (Codex HIGH-1 反映で executable boundary に格上げ)**:

1. **API contract**: `eval_store.connect_training_view()` が **唯一** の training-loader
   entry。返り値は **生 DuckDB connection ではなく `RawTrainingRelation`** (raw_dialog
   schema のみを expose する constrained relation、任意 SQL 実行不可)。任意 SQL が
   必要な caller には `eval_store.export_raw_only_snapshot(out_path)` で raw-only
   Parquet snapshot を取らせ、SQL は snapshot 上で実行させる経路に分離する。
2. **Behavioral CI test (sentinel-based)**: `tests/test_evidence/test_eval_paths_contract.py`
   で **sentinel metric rows** (一意な文字列値、例 `"M9_EVAL_SENTINEL_*"`) を埋めた
   eval store fixture を作り、**全 training egress 経路** (`connect_training_view()` /
   `export_raw_only_snapshot()` / 既存 `cli/export_log.py` 等) を通した出力に
   sentinel が現れないことを assert する。grep ベースの CI gate (補強) より
   sentinel ベースの動的契約の方が dynamic SQL / quoted SQL / `read_parquet(...)`
   を含む真の egress を捕捉できる (Codex HIGH-1)。
3. **CI grep gate (補強層、staticな安全網)**: `.github/workflows/ci.yml` に
   「training loader path で `metrics.` を grep 検出したら fail」step を追加。
   静的な checker としての役割で、sentinel test を一義的な真の boundary とする。
4. **既存 `src/erre_sandbox/cli/export_log.py` の egress 整合**: 現状 sqlite を
   直接 read している既存 egress も sentinel test 範囲に含め、必要なら
   `RawTrainingRelation` 経由に migrate する (P0c で判定、必要時 minimum patch)。

**根拠 (v2 採用、Codex HIGH-1 補強)**:
- 別 Parquet file 物理分離は path 規約 + grep だけで弱い
- DuckDB 単 file + named schema + **constrained relation API** + **sentinel CI test**
  + grep gate は **4 層 defense** で contamination を構造的に困難化
- 1-dependency (DuckDB) で I/O / 分析 / Parquet export を統一
- Codex HIGH-1 の "grep is not enough" 指摘を sentinel 動的契約で塞ぐ

### Library 選定: DuckDB 単独 (v2 採用)

採用: `duckdb>=1.1`。pyarrow / polars は採用しない。理由:
- DuckDB は単 process 単 writer で sqlite と同じ運用感
- Parquet export は `COPY ... TO ... (FORMAT PARQUET)` で zero-copy
- Tier A pure function は DuckDB Python API で columnar 取得 → numpy で計算
- 7500 turn × N metric の bootstrap resample も DuckDB 内で完結

### LIWC alternative: Option D (Big5 全面 IPIP-NEO 移管、LIWC 全廃) — v2 採用

**Option D 確定**:
- Big5 stability ICC は **IPIP-NEO 自己申告 self-report のみ** に依拠 (Tier B、agent
  に local 7B-Q4 が IPIP-NEO 短縮版 120 item を質問・回答)
- stylometric 一致は Burrows Delta (Tier A)
- persona-fit textual diversity は Vendi (Tier B)
- Empath は **secondary diagnostic** として Tier A の psycholinguistic axis 1 つに
  採用、**Big5 claim には使わない**
- これで `blockers.md` の LIWC license defer が **即時 close** (Option D 採用)

**根拠**:
- blockers.md DB10 honest framing "LIWC OSS proxy で Big5 claim は honest に避ける"
  と完全整合
- LIWC license decision tree を node ごと刈り取れる (work cost zero)
- IPIP-NEO は psychometric literature で Big5 推定の standard、self-report bias は
  周知だが well-documented
- spaCy 自前 dictionary (Option C) は category 設計 + validation に数日〜数週間の
  work cost、solo で完結させる現実性が低い

**self-report bias 対策 (v2 リスク 3 への補強)**:
ICC < 0.6 が頻発した場合の **conditional fallback** を `decisions.md` に re-open
条件として明記:
- BIG5-CHAT regression head を Tier B に追加し second opinion 化
- defer ではなく conditional fallback として記録 (発火条件を事前明文化)

### Golden baseline 採取: Hybrid (200 stimulus + 300 自然対話) — v2 採用、比率は pilot で defer 解消

**500 turn/run の構成**:
- 最初の **200 turn**: curated stimulus battery を fixed order で投入
  - Wachsmuth Toulmin 引き出す prompt: 30
  - ToM info-asymmetric scenario (chashitsu): 20
  - RoleEval-adapted **persona-specific biographical / thought-history MCQ**: 10
    (within-persona floor diagnostic、cross-persona absolute accuracy は DB9 比較指標に
    使わない。詳細 ADR は `decisions.md` ME-7、Codex review reflection は
    `codex-review-low1.md`)
  - persona-conditional moral dilemma: 10
  - 計 70 stimulus × 3 巡 = 210 turn (端数 10 turn は最後 stimulus を切り詰め)
- 残り **300 turn**: 既存 `InMemoryDialogScheduler` の自然対話 (peripatos / chashitsu /
  agora / garden の場の遷移を含む)

**根拠**:
- 純自然対話 baseline は drift gate baseline noise が大きい (topic 効果と style
  効果が混在)
- 純 stimulus baseline は ζ 軸 (mode 遷移) を測れず M9-A event-boundary observability
  と契約不整合
- hybrid で両得: stylometric reference の統制 + persona の場の対応観察

**比率 defer (微調整 1、Codex HIGH-3 で順序修正)**:
- 元案: P3 採取後に P3b で 50 turn pilot → 比率変更時 7500 turn 再採取の risk
- **修正後**: P3 の前に **P3a (200 turn × 両形式 × 3 persona の isolated pilot)** を
  挟み、bootstrap CI width が小さい比率を empirical 確定してから P3 採取に入る
  (Codex HIGH-3: "P3b is ordered after the data it is supposed to tune")
- 50 turn では Vendi の expected window 200 turn が満たされず統計力不足
  (Codex HIGH-3 evidence: Vendi は kernel/eigenvalue based、sample 必要)
- P3a は **fresh scheduler / store / seed** で golden baseline (P3) と完全分離、
  pilot 結果が baseline state に carry-over しないことを test 化
- 結果は `decisions.md` の ratio ADR に記録 (defer 解消)

### Orchestrator: 既存 scheduler に minimum patch + 外部 golden driver (Codex HIGH-4 反映)

**新規 wrapper を新設しない**。既存 `src/erre_sandbox/integration/dialog.py` の
`InMemoryDialogScheduler` に **`golden_baseline_mode: bool = False` 引数のみ**を追加
(cooldown / timeout bypass)。default `False` で既存全テスト pass。

**stimulus 投入は外部 golden driver から公開 API 経由** (Codex HIGH-4 反映、元案の
"scheduler input queue に push" は scheduler に該 surface が無いため棄却):

- `evidence/golden_baseline.py` の `GoldenBaselineDriver` クラスが、stimulus YAML を
  読んで loop で以下を呼ぶ:
  1. `scheduler.schedule_initiate(initiator_id, target_id, zone, tick)` で対話を開く
     (`zone` は stimulus YAML の場指定 = peripatos / chashitsu / agora / garden)
  2. stimulus prompt を agent に inference させ、`record_turn(DialogTurnMsg)` で
     scheduler に持たせる + sink 経由で MemoryStore に persist
  3. 規定 turn 数 (stimulus battery では各 stimulus 1-3 turn) 到達後
     `scheduler.close_dialog(dialog_id, "completed", tick=...)`
- 自然対話 part (300 turn) は scheduler.tick(world_tick, agents) を通常通り回す
- driver は **scheduler 内部状態を直接触らず**、公開 API のみ使う

**変更不要のもの**:
- scheduler の `tick()` / `_close_timed_out()` は不変
- `record_turn()` の sink contract は M8 L6-D1 の `turn_sink` をそのまま再利用

**追加 test (Codex HIGH-4 verification 反映)**:
- `tests/test_evidence/test_golden_baseline.py::test_one_stimulus_cycle_dryrun` —
  driver が **1 つの stimulus を schedule_initiate → record_turn → close_dialog の
  full cycle で実行** できることを synthetic stimulus + mock LLM で確認
- `tests/test_evidence/test_golden_baseline.py::test_70_stimulus_battery` — 70 stimulus
  × 3 巡 = 210 turn が input queue 無しに確実に流れることを確認

**根拠**:
- scheduler 不変条件を維持
- 新 layer 創設の cost 回避 (`eval/` 新 layer は不採用)
- Codex HIGH-4 指摘 "InMemoryDialogScheduler has no input queue surface" を、
  存在する公開 API (`schedule_initiate` / `record_turn` / `close_dialog`) で吸収

**RNG seed 戦略 (Codex MEDIUM-5 反映)**:
- 元案: `seed = hash((persona_id, run_idx, "m9-eval-v1"))` は Python `hash()` の
  salting で プロセス間非決定的
- **修正後**: `seed = int.from_bytes(hashlib.blake2b(f"m9-eval-v1|{persona_id}|{run_idx}".encode(), digest_size=8).digest(), "big")`
  でプロセス間 stable な uint64 seed
- 5 run × 3 persona = 15 seed を `golden/seeds.json` に commit、Mac と G-GEAR 両方で
  identical となることを `test_seed_manifest_stable` で assert
- numpy `Generator(PCG64(seed))` で stream 化、Ollama temperature は persona YAML の
  `default_sampling` を respect

### Tier A 計算 timing: 全 post-hoc per-run CLI (v2 採用)

- Tier A は live inference loop に背負わせない (DB6 厳守)
- 採取後に `eval_tier_a` CLI で post-hoc 計算
- 「per-turn 粒度」と「per-turn live timing」は別概念。DB6 が要求するのは粒度
- MPNet embedding は sentence-transformers の synchronous `encode(batch)` で
  N turn まとめ計算

### Tier C nightly infra: systemd --user timer + flock + nvidia-smi preflight (v2 採用、Mac launchd ssh trigger は不採用)

**G-GEAR 上で systemd --user の timer unit** を採用。

- timer unit (`erre-eval-tier-c.timer`) が 02:00 に fire
- service unit が flock で autonomous run の lock file を排他チェック → unlocked なら
  Prometheus 2 (Q4) を起動
- preflight: `nvidia-smi --query-gpu=memory.free` で free < 14GB なら skip + log
- journalctl で実行履歴可観測

**Mac launchd → ssh trigger は採用しない (微調整 2)**:
- 構成複雑化を回避
- master/agent の責務分離は将来 ablation で再検討
- systemd-timer 単独で実用十分

## 変更対象

### 修正するファイル (additive only、破壊禁止)

- `src/erre_sandbox/integration/dialog.py` — `golden_baseline_mode: bool = False` 引数
  + sink hook 追加。default False で既存全テスト pass
- `src/erre_sandbox/contracts/thresholds.py` — `M2_THRESHOLDS` 不変
- `personas/{kant,nietzsche,rikyu}.yaml` — `ipip_neo_short` optional field 追加
  (additive)
- `pyproject.toml` — dependency 追加 (下記 §影響範囲)
- `tests/test_integration/test_contract_snapshot.py` — 新規 `eval_thresholds` snapshot
  追加 (既存 M2_THRESHOLDS snapshot は再生成しない)

### 新規作成するファイル

`src/erre_sandbox/contracts/`:
- `eval_paths.py` — `RAW_DIALOG_SCHEMA: Final = "raw_dialog"` / `METRICS_SCHEMA: Final = "metrics"` /
  schema-guard helper
- `eval_thresholds.py` — DB9 quorum bound、frozen Pydantic、snapshot test ガード

`src/erre_sandbox/evidence/`:
- `eval_store.py` — DuckDB connection、schema bootstrap、`connect_training_view()`
  唯一 entry、Parquet export
- `tier_a/` directory (v1 補強 1: sub-module 構造):
  - `__init__.py`
  - `burrows.py` — **Burrows Delta** = z-scored function-word frequency vector の
    L1 (Manhattan) 距離。reference corpus で各 function word の mean / std を取得 →
    test text の同 function word 頻度を z-score → reference の z-score との差の
    絶対値の和。元案の "function-word vector cosine" は cosine distance であって
    Delta 規格と異なる (Codex HIGH-5)。stylometry literature (R Journal stylo 2016,
    R Eder/Rybicki/Kestemont) に準拠
  - `mattr.py` — Moving Average Type-Token Ratio (window 100)
  - `nli.py` — DeBERTa-v3-base-mnli zero-shot NLI contradiction
  - `novelty.py` — MPNet embedding 距離 semantic novelty
  - `empath_proxy.py` — Empath secondary diagnostic (Big5 claim には使わない)
- `tier_b/` directory:
  - `__init__.py`
  - `vendi.py` — Vendi Score (semantic kernel)
  - `ipip_neo.py` — IPIP-NEO 短縮版 agentic loop (local 7B-Q4)
  - `big5_icc.py` — Big5 stability ICC (run × mode で計算)
- `tier_c/` directory:
  - `__init__.py`
  - `prometheus.py` — Prometheus 2 client (Ollama HTTP)
  - `geval.py` — G-Eval logit-weighted scoring
  - `bias_mitigation.py` — position-swap / length-norm / two-judge protocol
- `bootstrap_ci.py` — **hierarchical bootstrap** (Codex HIGH-2 反映): outer level
  で run を cluster として resample (5 run × 3 persona = 15 cluster)、inner level で
  各 500-turn run 内に **circular block bootstrap** (Politis-Romano stationary block
  variant) を適用、block length は P3b pilot の autocorrelation で決定 (default 50)。
  Tier B per-100-turn metric は cluster-only resample (各 persona あたり 25 window
  しか無い = effective sample size 小、CI が広がる事実を report で明示)。
  3 sub-metric quorum logic は decision layer (M9-C-adopt)。`numpy` + `arch`
  (時系列 bootstrap 標準) または `scipy.stats.bootstrap` の独自 wrapper で実装
- `golden_baseline.py` — stimulus battery YAML loader + run 駆動 (既存 scheduler に
  push)
- `reference_corpus/` — Kant 独+英訳、Nietzsche、Rikyu、synthetic 4th persona の
  function-word vector pickle

CLI (`src/erre_sandbox/cli/`):
- `eval_ingest.py` — sqlite dialog_turns → DuckDB raw_dialog ingest
- `eval_tier_a.py` — Tier A post-hoc 計算
- `eval_tier_b.py` — Tier B post-hoc 計算 (G-GEAR 実行)
- `eval_tier_c.py` — Tier C nightly judge (systemd-timer から呼ばれる entry)
- `eval_audit.py` — raw + metrics integrity check
- `eval_report.py` — bootstrap CI dashboard

Stimulus / fixture / steering:
- `golden/stimulus/{kant,nietzsche,rikyu}.yaml` — 70 stimulus/persona
- `golden/seeds.json` — 15 seed manifest
- `personas/_synthetic_4th.yaml` — DB7 LOW-1 fixture (Big5 が 3 persona と直交する
  架空 thinker、`schema_version="0.10.0-m7h"`)
- `infra/systemd/erre-eval-tier-c.{service,timer}` — systemd unit
- `.steering/20260430-m9-eval-system/codex-review-prompt.md` — Phase P7 入力
- `.steering/20260430-m9-eval-system/codex-review.md` — verbatim 保存
- `.steering/20260430-m9-eval-system/decisions.md` — 新タスク独自 ADR (任意)

Tests:
- `tests/test_evidence/test_eval_paths_contract.py` — schema-guard
- `tests/test_evidence/test_eval_store.py` — DuckDB schema bootstrap
- `tests/test_evidence/test_tier_a/` (5 test file)
- `tests/test_evidence/test_tier_b/` (3 test file)
- `tests/test_evidence/test_tier_c/` (3 test file、bias mitigation 含む)
- `tests/test_evidence/test_bootstrap_ci.py`
- `tests/test_evidence/test_golden_baseline.py` — synthetic 4th persona DB7 LOW-1 含む
- `tests/test_contracts/test_eval_thresholds_snapshot.py`

CI:
- `.github/workflows/ci.yml` に **training loader path で `metrics.` を grep 検出
  したら fail** step を追加 (3 層 contract の補強層)

### 削除するファイル

原則無し。additive only。

## Tier 実装順序 (依存関係)

```
[Phase 0]
  P0a LIWC Option D 確定 ──┐
  P0b contracts + CI gate ──┤── DB5 contract gate (3 層)
  P0c eval_store DuckDB ────┘
                            │
[Phase 1-2]                 ▼
  P1a Tier A 5 metric (sub-module)  ┐
  P1b reference corpus               ├── parallel
  P2a stimulus battery YAML          │
  P2b dialog.py minimum patch        ┘
                                     │
[Phase 3]                            ▼
  P3  golden baseline 採取 (G-GEAR、200 stimulus + 300 自然対話)
  P3b pilot 比率 defer 解消
                                     │
[Phase 4-5]                          ▼
  P4a Tier B 3 metric                ┐
  P4b Tier B 後付け実行 (G-GEAR)      ├── post-hoc
  P5  bootstrap CI logic              ┘
                                     │
[Phase 6-7]                          ▼
  P6  Tier C nightly infra (parallel from P0 onward)
  P7  Codex review → HIGH 反映 → design-final.md rename
```

**DB9 sub-metric 3 個 (Vendi / Big5 ICC / Burrows Delta) ready 時期**:
- Burrows: P1a 完了時 (per-turn computed)
- Vendi / Big5 ICC: P4a 完了時 (per-100-turn computed)
- bootstrap CI 計算 ready: **P5 完了時 = タスク後半** (M9-C-adopt 直前)

## 影響範囲

### 既存テストへの impact

破壊しないこと前提:
- `contract_snapshot` test (frozen `M2_THRESHOLDS` / `SCHEMA_VERSION="0.10.0-m7h"` /
  `DialogTurnMsg` / `RunLifecycleState`) — 全緑維持
- `integration/dialog.py` の `golden_baseline_mode` 追加は default False で既存全
  テスト pass
- 既存 `evidence/metrics.py` interface (`compute_*` 関数群、`aggregate(db_path)`) は
  signature 不変

### contracts/ への additive 変更

- 新規 `eval_paths.py` / `eval_thresholds.py` 追加 (`M2_THRESHOLDS` 並列、独立 snapshot)
- 既存 `M2_THRESHOLDS` snapshot は再生成しない

### pyproject.toml dependency 追加 (Codex MEDIUM-4 反映 — heavy ML deps を eval extras 隔離)

```toml
[project.dependencies]  # 既存に追加 — core はlightweight に保つ
"duckdb>=1.1,<2",

[project.optional-dependencies]
eval = [
    "scipy>=1.13,<2",                # bootstrap resample / stats
    "sentence-transformers>=3,<4",   # MPNet semantic novelty (heavy ML dep を eval 隔離)
    "ollama>=0.3,<1",                # Tier C judge LLM client
    "empath>=0.89",                  # Empath secondary diagnostic (Big5 claim 不使用)
    "arch>=7,<8",                    # 時系列 bootstrap 標準 (block bootstrap helper、HIGH-2)
]
```

CI 設計:
- 通常 CI (lint / typecheck / test) は `uv sync --no-group eval` で実行 → heavy ML
  deps を pull せず軽量を維持
- eval 関連 test は別 job (`uv sync --extra eval` + `pytest -m eval`) で実行
- `tests/test_evidence/` は `@pytest.mark.eval` で deselect 可能にする

NLI: DeBERTa-v3-base-mnli は `sentence-transformers` が pull する `transformers` を
通じて利用 (eval extras 内で完結)。

`spacy` / `pyarrow` / `polars` / `pingouin` / `vendi-score` は採用しない:
- spacy: Option D で不要 (LIWC alternative 自前 dictionary が消滅)
- pyarrow / polars: DuckDB 単独で I/O / 分析カバー
- pingouin: ICC は scipy.stats + numpy で実装可
- vendi-score: 公式 lib は実装が薄く、scipy.spatial.distance + numpy で自前実装
  (vendi-score は固有値分解の wrapper のみ)

### filterwarnings

- sentence-transformers の HuggingFace deprecation 群を **局所的に**
  `filterwarnings ignore` で許可 (test 全体には影響させない、`@pytest.mark.filterwarnings`
  decorator で限定)

## 既存パターンとの整合性

- **Pure-function metric pattern**: `evidence/metrics.py` の `compute_*` 関数群と
  `aggregate(db_path)` パターンを Tier A 5 metric / Tier B 3 metric にも踏襲
- **CLI subcommand**: 既存 `cli/{baseline_metrics,scaling_metrics,export_log}.py` の
  argparse + JSON/JSONL out パターンを `eval_*` 6 CLI に踏襲、`schema: "<name>_v1"` 慣例
- **Pydantic frozen contracts**: `contracts/thresholds.py` の frozen pattern を
  `eval_thresholds.py` に踏襲 (`model_config = ConfigDict(extra="forbid", frozen=True)`)
- **Persona YAML additive**: `schema_version="0.10.0-m7h"` 維持、既存 field 不変、
  `ipip_neo_short` のみ optional 追加。`_synthetic_4th.yaml` も同じ schema
- **MemoryStore 経由**: `memory/store.py` の `iter_dialog_turns()` で turn 取得し、
  `eval_ingest` CLI で DuckDB raw_dialog schema に投入
- **inference/sampling.py** の `compose_sampling()` override → IPIP-NEO 質問時に
  override で deterministic (temperature=0.0) に切替

## テスト戦略

### Contract gate (実装中、pytest)

1. **DB5 schema-guard**: `tests/test_evidence/test_eval_paths_contract.py` で
   training loader が `metrics` schema を SELECT したら明示的
   `EvaluationContaminationError` raise を確認
2. **CI grep gate**: `.github/workflows/ci.yml` で training loader path に
   `metrics.` を grep 検出したら fail
3. **Bootstrap CI shape**: 既知分布 (synthetic Vendi / ICC / Burrows triple) で
   resample N=1000、95% CI が解析解 ± 5% 内。加えて **AR(1) 合成 turn metric** を
   生成し、iid resample と block bootstrap で CI width が体感的に異なることを
   `test_bootstrap_ci.py` で fixture 化 (Codex HIGH-2 / verification suggestion 反映)
4. **Frozen snapshot**: `eval_thresholds` 改変時の合意 trail を snapshot test で要求

### DB7 LOW-1 (synthetic 4th persona heldout fixture)

- `personas/_synthetic_4th.yaml`: Big5 が 3 既存 persona と直交する架空 thinker
- `test_golden_baseline.py` で 4 persona scenario を Tier A pipeline に通し、3-persona
  overfitting (3-only assumption が出たら fail) を防ぐ

### Tier acceptance (実装後、pytest)

- `test_tier_a/`: 5 metric が synthetic + 4th persona heldout で NaN/crash 無く計算、
  Burrows Delta が persona-discriminative (Kant ≠ Nietzsche、distance 差 ≥ fixed delta)
- `test_tier_b/`: 3 metric が known distribution で expected 値、IPIP-NEO loop が
  deterministic temperature=0 で stable
- `test_tier_c/`: bias mitigation hook (position-swap / length-norm) が判定不変性を
  保つかを fixture pair で確認

### Burrows multi-lang (blockers.md 暫定方針)

- per-language reference でしか比較しない契約を test 化 (cross-lang を呼ぶと例外)

### Golden baseline integrity (G-GEAR run 後、CLI)

- `python -m erre_sandbox.cli.eval_audit data/eval/golden/*.duckdb`:
  - 3 persona × 5 run × 500 turn = 7500 turn 完全性確認
  - metrics sidecar の `(run_id, persona_id, turn_idx)` で raw に LEFT JOIN して
    miss が無いこと確認
- `python -m erre_sandbox.cli.eval_report --bootstrap-ci`:
  - DB9 sub-metric 3 個に CI 数値、persona-discriminative 観察を `blockers.md`
    L89-93 に追記 (defer 解消)

## ロールバック計画

- **L0 (即時 dependency rollback)**: `pyproject.toml` の `duckdb` /
  `sentence-transformers` を仮に core → optional `eval` group へ移し、
  `uv sync --no-group eval` で完全 disable。core 機能は影響なし
- **L1 (Tier A revert)**: `evidence/tier_a/` directory 単位で revert、
  `evidence/metrics.py` (M8 baseline) は touch しないので回帰 zero
- **L2 (golden baseline)**: DuckDB file は `data/eval/golden/*.duckdb` に隔離、削除のみ
  で raw_dialog 全消去。export 済 parquet は別 path (`data/eval/parquet_export/`)、
  retention は別 ADR
- **L3 (Tier C nightly)**: `systemctl --user disable erre-eval-tier-c.timer` のみで
  停止。autonomous run には影響なし
- **L4 (DuckDB → Parquet 別 file 移行)**: 万一 schema-guard が contamination を
  防ぎきれないと判明 (CI grep gate でも漏れ) した場合、`eval_store.py` 内部実装
  のみ Parquet 別 file へ差替可能 (`contracts/eval_paths.py` の API は不変、外部
  caller 影響 zero)
- **L5 (golden baseline 再採取)**: 採取済 raw_dialog は `data/eval/golden/` で
  immutable、bug 発見時は run_id 単位で部分 rerun (5 run の独立性が seed 分離で
  保たれている前提)

## リスクと反復前提 (Codex review 完了、結果反映済)

元 5 件 + Codex 追加分。Codex `gpt-5.5 xhigh` review 完了 (`codex-review.md`):

1. **DuckDB schema-guard が training pipeline で bypass されるリスク**
   - 物理 file 分離より弱いという指摘の余地
   - 反復前提: API contract + schema-guard test + CI grep gate の 3 層 defense で
     塞ぐ。L4 rollback 経路 (Parquet 別 file 移行) を予備として設計

2. **Big5 を IPIP-NEO 自己申告のみに頼る妥当性 (Option D の trade-off)**
   - self-report bias (acquiescence、社会望ましさ) リスクが集中
   - cross-mode stability ICC は run independence 前提が壊れる可能性
   - **conditional fallback**: ICC < 0.6 が頻発したら BIG5-CHAT regression head を
     Tier B に追加し second opinion 化。発火条件を `decisions.md` に明文化

3. **Burrows Delta multi-language reference の汚染** (blockers.md 既出)
   - Kant 独原典 vs 英訳 vs 日本語 dialog の 3 言語 reference 別保持で防ぐ
   - reference token count < 50K で z-score noisy
   - 反復: P1b 完了時に token 数を実測、不足なら corpus 追加

4. **Hybrid baseline 比率 200/300 の arbitrary 性**
   - 70 stimulus × 3 巡 = 210 turn は Wachsmuth/ToM/RoleEval/dilemma の 4 系統に
     bound、persona の cognitive_habits 全域を覆わない
   - 反復: P3b で pilot run 50 turn 両形式比較、Burrows / Vendi の bootstrap CI
     width が小さい比率に empirical 調整、`blockers.md` 記録

5. **Tier C judge LLM の VRAM contention 検出失敗**
   - Prometheus 2 8x7B Q4 (~14 GB) + 万一 ollama qwen3 が leak で常駐 (FP16 16 GB)
     → OOM
   - 反復: systemd unit の preflight に `nvidia-smi --query-gpu=memory.free` チェッ
     ク、free < 14 GB なら skip + log

### Codex 独立 review 結果サマリ (詳細は `codex-review.md` 全文 verbatim)

| 項目 | Severity | 反映先 | Status |
|---|---|---|---|
| Schema guard executable boundary (sentinel test + constrained relation) | HIGH-1 | design.md §DuckDB / `tests/test_evidence/test_eval_paths_contract.py` | ✅ 反映済 |
| Hierarchical bootstrap (cluster runs + circular blocks) | HIGH-2 | design.md §bootstrap_ci.py / test_bootstrap_ci.py | ✅ 反映済 |
| Pilot ordering: P3a を P3 前に移動、200 turn × 両形式 isolated | HIGH-3 | design.md Hardware allocation table | ✅ 反映済 |
| Stimulus injection は公開 API 経由 (input queue 不存在) | HIGH-4 | design.md §Orchestrator / `evidence/golden_baseline.py` | ✅ 反映済 |
| Burrows Delta = z-scored function-word L1 (cosine ではない) | HIGH-5 | design.md §burrows.py 定義 | ✅ 反映済 |
| IPIP fallback trigger operational definition | MEDIUM-1 | `decisions.md` ME-1 ADR | ✅ ADR 化 |
| DuckDB snapshot semantics (CHECKPOINT + temp+rename + read_only) | MEDIUM-2 | design.md Hardware allocation P3 + `decisions.md` ME-2 | ✅ 反映済 |
| Tier C lock TOCTOU + Persistent= 決定 | MEDIUM-3 | `decisions.md` ME-3 ADR | ✅ ADR 化 |
| Dependency placement: heavy ML deps を eval extras 隔離 | MEDIUM-4 | design.md §pyproject.toml | ✅ 反映済 |
| RNG seed: hashlib.blake2b で uint64、`hash()` 棄却 | MEDIUM-5 | design.md §RNG seed 戦略 | ✅ 反映済 |
| Burrows token floor: corpus QC 化 (固定 50K → ≥5K-word chunk stability) | MEDIUM-6 | `decisions.md` ME-6 ADR / `blockers.md` reopen 条件 | ✅ ADR 化 |
| RoleEval Kant 限定 vs persona-specific MCQ 区別 | LOW-1 | `blockers.md` defer | ✅ defer |

---

## 設計判断の履歴

- **初回案 (`design-v1.md`)**: 別 Parquet file 物理分離 / pyarrow + polars / LIWC
  Option C (spaCy + 自前 dict) / 新規 wrapper Orchestrator / Tier A live per-turn /
  asyncio + file-lock
- **再生成案 (v2)**: DuckDB 単 file + schema-guard / DuckDB 単独 / LIWC Option D /
  既存 scheduler minimum patch / 全 post-hoc / systemd-timer + flock / Hybrid baseline
- **比較**: `design-comparison.md` 参照
- **採用**: **ハイブリッド (v2 ベース + v1 補強 2 点 + 微調整 2 点)**
- **根拠**:
  - データ層は v2 (DuckDB schema-guard + CI grep gate の 3 層 defense が path 規約より
    厳格)
  - LIWC は v2 Option D (blockers.md 1 件 close + work cost zero + DB10 honest framing
    と完全整合)
  - Orchestrator は v2 minimum patch (scheduler 不変条件維持、新 layer 創設の cost 回避)
  - 計算 timing は v2 全 post-hoc (DB6 厳守、live inference 不負荷)
  - **v1 補強 1**: metric file 構造を `evidence/tier_a/` sub-module 化 (`tier_a.py`
    単 file は 800+ 行で review-friendly でない)
  - **v1 補強 2**: Hardware allocation は v1 の Phase 区分形式 (subtask flat より
    依存関係 / 同期点が table から読める、`tasklist.md` の `[Mac]` / `[GG]` /
    `[Mac→GG]` tag 付与に直結)
  - **微調整 1**: Hybrid baseline 比率 200/300 は default で start、P3b pilot で
    empirical 調整、`blockers.md` に defer 解消記録
  - **微調整 2**: Tier C nightly は systemd-timer **単独**、Mac launchd → ssh
    trigger は採用しない (構成最小化、master/agent 責務分離は将来 ablation で再検討)
- **Codex review 完了 (2026-04-30)**: HIGH 5 / MEDIUM 6 / LOW 1。HIGH 全件を本文に
  反映、MEDIUM は `decisions.md` に 5 要素 ADR、LOW は `blockers.md` に defer。
  本ファイルを `design-final.md` に rename して Phase P0 に入る。
- **次工程**: P0a (LIWC Option D 確定 → blockers close) → P0b (`contracts/eval_paths.py`
  + sentinel CI test) → P0c (`evidence/eval_store.py` の `RawTrainingRelation`) →
  P1a (Tier A sub-module、Burrows は z-score Delta で実装) → P2c (external golden
  driver) → P3a (200 turn isolated pilot) → P3a-decide (ratio 確定) → P3 (golden
  baseline 採取) の依存順。

## Codex review HIGH 反映履歴

### 2026-04-30 — Codex `gpt-5.5 xhigh` (`codex-review.md`)

**Summary verdict**: "Proceed with HIGH fixes before P0a. Lowest-cost wins:
move P3b before P3, replace `hash()` seeds, and make training/eval dependency
boundaries executable."

**HIGH-1 反映** — Schema guard executable boundary:
- `connect_training_view()` の返り値を **`RawTrainingRelation`** (constrained
  relation) に変更、生 DuckDB connection を返さない
- 任意 SQL を必要とする caller には `export_raw_only_snapshot(out_path)` で
  raw-only Parquet snapshot を取らせる
- `tests/test_evidence/test_eval_paths_contract.py` に **sentinel metric rows**
  ("M9_EVAL_SENTINEL_*" 文字列) を埋めた fixture を追加、全 training egress 経路
  (含む既存 `cli/export_log.py`) を sentinel test 範囲に含める
- CI grep gate は補強層 (静的) として維持、sentinel test を真の boundary に格上げ

**HIGH-2 反映** — Hierarchical bootstrap:
- `bootstrap_ci.py` を hierarchical bootstrap (outer: run cluster resample / inner:
  circular block bootstrap) に specify
- block length は P3a pilot の autocorrelation で empirical 決定 (default 50)
- Tier B per-100-turn metric は cluster-only resample (effective sample size 25
  window/persona と report で明示)
- `test_bootstrap_ci.py` に AR(1) 合成 turn metric fixture を追加、iid vs block CI
  width の差を test 化

**HIGH-3 反映** — Pilot ordering:
- 元 P3 (golden 採取) → P3b (50 turn pilot) の順を **P3a (200 turn × 両形式 ×
  3 persona isolated pilot) → P3a-decide (ratio ADR) → P3 (golden 採取)** に修正
- 50 turn では Vendi の 200 turn window 不足、最小 200 turn/condition/persona
- P3a は fresh scheduler / store / seed で完全分離、carry-over 防止 test 化

**HIGH-4 反映** — Stimulus injection without input queue:
- `InMemoryDialogScheduler` に input queue surface が無い事実を確認
  (`schedule_initiate` / `record_turn` / `close_dialog` / `tick` のみ公開)
- 元案の "scheduler input queue に push" を棄却、外部 `GoldenBaselineDriver` が
  公開 API のみで stimulus を駆動する形に変更
- scheduler への patch は `golden_baseline_mode: bool = False` のみに縮小
  (cooldown/timeout bypass)、turn_sink は既存 M8 L6-D1 の sink を再利用
- driver の dry-run test (1 stimulus + 70 stimulus battery) を P2c に追加

**HIGH-5 反映** — Burrows Delta correction:
- `evidence/tier_a/burrows.py` の定義を "function-word vector cosine" から
  **"z-scored function-word frequency vector の L1 (Manhattan) 距離"** に修正
- stylometry literature (R Journal stylo 2016, Eder/Rybicki/Kestemont) 準拠
- DB9 quorum sub-metric の名称は "Burrows Delta" のまま (M9-B `decisions.md`
  DB9 と整合)、内部実装を Delta 規格に合わせる

**MEDIUM 6 件は `decisions.md` (新規) に 5 要素 ADR として記録、LOW 1 件は
`blockers.md` (新規、m9-eval-system 配下) に defer。** 詳細はそれぞれの file。

### Codex review 適用後の design 整合性 check
- DB1-DB10 の M9-B ADR との衝突: 無し
- Codex review が指摘した既存 contract (M2_THRESHOLDS / SCHEMA_VERSION /
  DialogTurnMsg / RunLifecycleState) への変更: 無し
- planning purity: `src/` の touch 無し (本反映は steering 文書のみ)
