# m9-eval-system

## 背景

- **直接の前段**: M9-B LoRA execution plan (PR #127 merged, main=`ff29ca2`) で 10 ADR
  (DB1-DB10) を v3 hybrid として確定。Codex `gpt-5.5 xhigh` の HIGH 4 件を反映し、
  vLLM full migration ではなく **SGLang-first + bounded Kant spike 並行** の第 3 の道を
  採用した。本タスクは「ADR は揃った、実装はこれから」という実装フェーズの起点。
- **位置付け**: M9 milestone は M9-A (event-boundary observability、PR #117-#124 完全
  クローズ済) に続き、M9-B → **M9-eval-system (本タスク)** + M9-C-spike (並行) →
  M9-C-adopt の順で進む。本タスクと M9-C-spike は独立進行し、M9-C-adopt で合流する。
- **問題意識**:
  1. LoRA fine-tuning の効果は「ペルソナ忠実度・心理的整合・stylometric 一致」を多軸で
     測らない限り検証できない。Tier 構造 (DB10) と sidecar metrics (DB5/DB6) の実装が
     無いまま spike を走らせると、empirical foundation 抜きの judgment になり LoRA
     採用判断 (M9-C-adopt) を支えられない。
  2. M9-C-adopt の前提条件として **Vendi / Big5 ICC / Burrows Delta の 3 sub-metric
     が bootstrap CI 計算 ready** であること (DB9 の 2-of-3 quorum 起動に必須)。
  3. golden baseline (LoRA 適用前の anchor) を採取しておかないと、後で adopt 判断に
     必要な「効果量」の絶対値が測れず、回帰検出も成立しない。

## ゴール

DB1-DB10 を破らない評価 pipeline を実装し、3 persona × 5 run × 500 turn の golden
baseline を採取して、M9-C-adopt の前提条件 (DB9 の sub-metric 3 個が bootstrap CI 計算
ready) を満たす状態にする。

## スコープ

### 含むもの

- **Tier 0** (DB5/DB6):
  - `raw_dialog` Parquet (metric-free): turn id / agent / persona / mode / utterance /
    timestamp / reasoning trace のみ。LIWC やスコア類は混入させない (contamination 防止)。
  - `metrics` sidecar Parquet: turn id を join key に Tier A/B/C のスコアを格納。
  - 両者の **物理分離**を契約として固定 (path 規約 + schema validation)。
- **Tier A** per-turn metric (DB10):
  - LIWC **alternative** (LIWC 商用は license 評価で defer/adopt 判定)
  - Burrows Delta (function word frequency vector cosine)
  - MATTR (Moving Average Type-Token Ratio、ウィンドウ 100)
  - semantic novelty (embedding 距離による直前 N turn からの離脱)
  - NLI contradiction (簡易 entailment classifier)
- **Tier B** per-100-turn metric (DB10):
  - Vendi Score (diversity)
  - IPIP-NEO 短縮版 self-report (local 7B-Q4 で agent に質問・回答させる)
  - Big5 stability (across 5 run の ICC)
- **Tier C 一部** (DB10):
  - Prometheus 2 (open judge LLM、bias mitigation あり)
  - G-Eval (chain-of-thought 評価)
  - **nightly offline** で走らせる (実時間 inference に背負わせない、DB6)
- **golden baseline 採取**: 3 persona (Kant / Nietzsche / Rikyu) × 5 run × 500 turn。
- **golden set 整備**: 100 prompt/persona の seed セット。acceptance 300/persona は別 phase。
- **evaluation pipeline 自動化**: ingest → tier 別 metric 計算 → bootstrap CI →
  dashboard。
- **bootstrap CI + 2-of-3 quorum** (DB9) の sub-metric 3 個 (Vendi / Big5 ICC /
  Burrows Delta) が計算 ready 状態に到達。
- **LIWC license 評価**を決着させ、`.steering/20260430-m9-b-lora-execution-plan/blockers.md`
  の defer 項目を 1 件 close。

### 含まないもの

- M9-C-spike (SGLang LoRA bounded Kant spike) — 別 `/start-task m9-c-spike` で並行進行。
- M9-C-adopt の判断そのもの — 本タスクは前提条件を整えるところまで。
- LoRA training pipeline 実装 — M9-D で扱う。
- acceptance 300/persona の golden set 拡張 — 別 phase に後送。
- LIWC 商用ライセンスの契約事務 (本タスクは「alternative で行くか商用採用か」の
  決着まで。契約手続きが必要なら別タスク)。
- 既存 contracts/ schema の破壊的変更 — sidecar 追加で済むなら additive のみ。

## 受け入れ条件

- [x] `design.md` 冒頭に **Hardware allocation 表** が存在し、MacBook (master/dev) と
      G-GEAR (実行機) の subtask 工数 + GPU/VRAM 要件 + 同期点が明示されている
      (`design-final.md` Hardware allocation 節、Codex HIGH-3 で P3a / P3a-decide 追加)
- [x] `design.md` (→ `design-final.md`) / `decisions.md` (ME-1〜ME-6) /
      `tasklist.md` (P0a-P7 + closure 展開、`[Mac]`/`[GG]`/`[Mac→GG]` tag 付与) の
      3 点セット完成
- [ ] DB5 (raw + sidecar 物理分離) を破る実装が無いこと (schema validation + path 規約) —
      P0b/P0c 実装で確認、Codex HIGH-1 反映で **sentinel 動的 contract** + grep gate の
      4 層 defense
- [ ] DB6 (Tier A per-turn / B per-100 / C nightly offline 頻度 policy) を守る実装 —
      P1a-P6 実装で確認
- [ ] DB9 (bootstrap CI + 2-of-3 quorum) の sub-metric 3 個 (Vendi / Big5 ICC /
      Burrows Delta) が **bootstrap CI 計算 ready** (M9-C-adopt の前提) — P5 完了時、
      Codex HIGH-2 で hierarchical bootstrap 採用
- [x] LIWC license 評価が決着 (採用/alternative のいずれか確定、`blockers.md` の
      defer 項目 1 件 close) — **Option D 確定 / 2026-04-30 P0a で M9-B
      `blockers.md` "LIWC 商用 license の最終可否判定" を CLOSED に Edit 済**
- [x] Codex `gpt-5.5 xhigh` independent review を Plan 確定前に挟み、HIGH 全件反映 /
      MEDIUM 採否を `decisions.md` に記録 / LOW を `blockers.md` に defer
      (HIGH 5 件 → `design-final.md`、MEDIUM 6 件 → `decisions.md` ME-1〜6、LOW-1 →
      `blockers.md`)
- [ ] golden baseline (3 persona × 5 run × 500 turn) が採取され、Parquet として
      永続化されている — P3 完了時 (G-GEAR overnight×2)
- [x] `tasklist.md` の各 checkbox に `[Mac]` / `[GG]` / `[Mac→GG]` tag が付与されている
- [ ] `git diff` が scope に整合 (Tier 0/A/B/C 一部 実装 + golden 採取コードのみ。
      LoRA training や M9-C-spike の混入無し) — closure 時に確認

## 関連ドキュメント

### M9-B 直接前段 (Read 必須)

- `.steering/20260430-m9-b-lora-execution-plan/design-final.md` — v3 hybrid、10 軸 確定済
- `.steering/20260430-m9-b-lora-execution-plan/decisions.md` — DB1-DB10、5 要素フォーマット
- `.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md` — 6 系統 30+ metric
- `.steering/20260430-m9-b-lora-execution-plan/blockers.md` — LIWC license / Burrows
  multi-lang / judge bias mitigation 等の defer 項目
- `.steering/20260430-m9-b-lora-execution-plan/tasklist.md` Phase B 節 (M9-eval-system tasklist)

### プロジェクト一般

- `docs/architecture.md` — Tier 構造 / sidecar / contracts/ レイヤー位置付け
- `docs/development-guidelines.md` — Parquet 規約 / pandas vs polars 方針
- `docs/glossary.md` — Tier 0/A/B/C / Vendi / Burrows Delta / IPIP-NEO 等の用語

## 運用メモ

- **タスク種別**: その他 (実装フェーズの起点で、設計判断と多面的実装を含む。
  単一 `/add-feature` 等には収まらない)
- **破壊と構築（/reimagine）適用**: **Yes**
- **理由**: 以下の architecture 判断を含むため、Plan mode 内で `/reimagine` を発動して
  初回案を意図的に破棄し、ゼロから再生成案と比較する:
  1. raw + sidecar 分離方式の物理表現 (Parquet 構造 / path 規約 / join 戦略の代替案)
  2. LIWC alternative の選定 (open dictionary / 自前構築 / multi-lang 戦略)
  3. golden baseline の採取設計 (seed 選定 / run 独立性 / contamination 分離契約)
  4. Tier C nightly offline の実行基盤 (cron / queue / cost 上限)
- **Codex independent review 必須**: M9-B で Codex web search が SGLang v0.3+ multi-LoRA を
  提示し Claude の stale 認識を補正した empirical evidence あり。Plan 確定前に
  `codex-review-prompt.md` 起草 → `codex exec --skip-git-repo-check` →
  `codex-review.md` verbatim 保存。HIGH は実装前必反映、MEDIUM は decisions.md、
  LOW は blockers.md に持ち越し可。
- **Plan mode + Opus**: 高難度設計 (Parquet schema / Tier A-D framework / golden set
  methodology / contamination 分離契約) のため Plan mode 必須、Opus で設計確定まで。
- **context 管理**: 50% 超で `/smart-compact`、Plan 承認時 30% 超なら `/clear` →
  次セッションで `design-final.md` を Read してから実装入り。
- **planning purity**: Plan 承認前に `src/` を触らない。
- **並行タスク**: M9-C-spike は別 `/start-task m9-c-spike` で起こす。両者独立、
  M9-C-adopt で合流。
