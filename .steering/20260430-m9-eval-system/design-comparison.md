# 設計案比較 — m9-eval-system

`design-v1.md` (初回案) と再生成 v2 案 (現在の `design.md`) を比較。

## v1 (初回案) の要旨

DB5 物理分離を **別 Parquet file** で達成 (`raw_dialog/` と `metrics/` 配下を path 規約で
分離)。Library は **pyarrow (I/O) + polars (分析)** の併用。LIWC は **Option C (spaCy +
自前 dictionary、Empath seed)** で Big5 claim を IPIP-NEO 経路に集約。Golden baseline
は **3 persona × 5 run × 500 turn の純自然対話** を新規 `GoldenBaselineOrchestrator`
wrapper で採取。Tier C nightly は **asyncio scheduler + `ollama ps` polling +
file-lock** で agent 停止時を mechanism 化。

## v2 (再生成案) の要旨

DB5 物理分離を **DuckDB 単 file の named schema (raw_dialog / metrics) + training-
loader API の schema-guard** で達成、Parquet は二次的な export 形式に格下げ。
Library は **DuckDB 単独** (pyarrow / polars 不要の 1-dependency)。LIWC は
**Option D (Big5 claim 自体を放棄、IPIP-NEO self-report に一本化、Empath は Tier A
diagnostic のみ)** で blockers.md の LIWC license defer を即時 close。Golden baseline
は **fixed stimulus battery 200 turn + 自然対話 300 turn の hybrid**、既存
`InMemoryDialogScheduler` に `golden_baseline_mode: bool` の minimum patch のみ
(新規 wrapper 不採用)。Tier C nightly は **G-GEAR の systemd --user timer + flock**
で実装 (Mac launchd → ssh trigger は補助案、必須でない)。Tier A 計算 timing は
全 post-hoc (live inference 不負荷、DB6 厳守)。

## 主要な差異

| 観点 | v1 | v2 |
|---|---|---|
| **DB5 物理分離** | 別 Parquet file + path 規約 | DuckDB 単 file + named schema + training-loader API guard + CI grep gate |
| **Library** | pyarrow + polars 併用 | DuckDB 単独 |
| **LIWC alternative** | Option C (spaCy 自前 dict + Empath seed)、Big5 claim を IPIP-NEO に集約 | **Option D (LIWC 全廃)、Big5 を IPIP-NEO 自己申告のみに依拠、Empath は副次的** |
| **Golden baseline 形式** | 自然対話 500 turn × 5 run × 3 persona | **Hybrid: stimulus battery 200 turn (Wachsmuth/ToM/RoleEval/dilemma 70 種 × 3 巡) + 自然対話 300 turn** |
| **Orchestrator** | 新規 `GoldenBaselineOrchestrator` wrapper | 既存 `InMemoryDialogScheduler` に `golden_baseline_mode: bool` minimum patch、wrapper 新設なし |
| **Tier A 計算 timing** | per-turn live (~50ms 制約) | 全 post-hoc per-run CLI (粒度は per-turn だが timing は post-hoc、live inference 不負荷) |
| **Tier C nightly infra** | asyncio + `ollama ps` polling + file-lock | systemd --user timer (G-GEAR) + flock + nvidia-smi preflight |
| **新規 file 数** | `eval/` 配下 ~16 file (parquet_io / tier_{a,b,c}/* / orchestrator / bootstrap / seeds.json + 5 CLI + 5 test + fixture) | `evidence/tier_{a,b,c}.py` 等 ~10 file (既存 `evidence/` pattern 踏襲、新 layer 不創設) |
| **依存追加** | pyarrow / polars / vendi-score / sentence-transformers / pingouin / spacy + Empath | duckdb / sentence-transformers / scipy + ollama (optional `eval` group) |
| **schema-guard 強度** | path 規約 (file-system 依存、grep で破れる) | API contract + CI grep gate で training loader path に `metrics.` を書けない構造 |
| **blockers.md 1 件 close 方法** | spaCy 自前 dictionary 整備で Option C 確定 | **LIWC を完全放棄して Option D 確定 (work cost 最小)** |
| **stimulus battery** | 言及なし | 70 stimulus × 3 巡で Wachsmuth/ToM/RoleEval/dilemma を統制、bootstrap CI noise を抑制 |
| **既存資産との統合** | `eval/` 新 layer (新規創設) | `evidence/` 既存 layer 拡張 (M8 pattern 継承) |

## 評価 (各案の長所・短所)

### v1 の長所
- **Parquet 別 file 分離** は industry-standard で「物理分離した」という直感的な
  可視性が高い (将来の reviewer / collaborator にも説明しやすい)
- **Tier A live per-turn** は M9 milestone の "drift gate を実行時に発火" の
  semantic に直結
- pyarrow + polars は ecosystem が厚く、bootstrap resample で polars lazy が
  scale (将来 7500 turn → 10x で benefit)

### v1 の短所
- **path 規約は file-system 依存で grep で容易に破れる** (training loader が
  `metrics/` を直接 open しない保証は CI 側の追加 gate なしには弱い)
- 新規 layer (`eval/`) 創設は既存 `evidence/` pattern との二重化
- LIWC Option C は spaCy 自前 dictionary の category 設計コストが大、honest
  framing しても Big5 claim の説得力に subtle な傷
- 自然対話 500 turn × 5 run の純粋 baseline は **drift gate の baseline noise が
  高い** (topic 効果と style 効果が混在)
- Tier A live per-turn は inference loop の latency 予算を圧迫する潜在リスク
  (M9-A event-boundary observability の latency 観測値による)

### v2 の長所
- **DuckDB schema-guard + API contract + CI grep gate** は 3 層 defense で
  contamination を構造的に困難化 (path 規約より厳格)
- **1-dependency (DuckDB)** で I/O / 分析 / Parquet export を統一、依存の
  organic complexity が低い
- **Option D (LIWC 全廃)** は blockers.md の defer 項目を **即時 close** でき、
  work cost が最小、honest framing も最も clean (Big5 を self-report で
  公的に依拠する立場の方が学術的にも defensible)
- **Hybrid baseline** は drift gate の baseline noise を統制、Burrows Delta /
  Vendi の statistical power を高める
- **既存 `InMemoryDialogScheduler` に minimum patch** は破壊リスク最小、
  scheduler 不変条件を維持
- **全 post-hoc 計算** は live inference 負荷ゼロで DB6 を厳守、dev cycle が
  iterate しやすい (採取と計算の分離)
- **systemd --user timer** は journalctl で運用可観測

### v2 の短所
- **DuckDB 単 file** は「物理分離」の直感的可視性が下がる (named schema は
  内部表現で、外部観察者からは「同じ file の中」)
- v2 自身がリスク 1 で認めている: schema-guard が training pipeline で
  bypass されるリスク (CI grep で補強する前提)
- **Option D** は Big5 を IPIP-NEO 自己申告**のみ**に依拠する設計判断が、
  self-report bias (acquiescence、社会望ましさ) のリスクを集中させる
- **Hybrid baseline の比率 (200/300)** が arbitrary、empirical 根拠なし
- **systemd-timer** は Linux 限定、もし将来 G-GEAR が異 OS になった場合
  (確率は低いが) migration コスト
- **全 post-hoc** は live drift gate (run 中の自動 rollback 等) が原理的に
  遅延 (この task scope では問題ないが、M9-C-adopt で live gate を作る時に
  pipeline 再構築が要る可能性)

## 推奨案

**ハイブリッド (v2 ベース + v1 の補強 2 点 + 微調整 2 点)** を推奨。

### 採用する v2 の判断 (4 件)

1. **データ層: DuckDB 単 file + schema-guard + CI grep gate** (v2 採用)
   - 理由: schema-guard + API contract の方が path 規約より厳格で、CI grep で
     bypass を構造的に塞げる。Parquet は export contract に格下げで運用簡素。
   - 補強: v2 自身がリスク 1 で挙げた「CI grep gate」を Phase 1 step 1 で
     **必須実装** に格上げ (optional ではなく contract test と同等の地位)。

2. **LIWC: Option D (Big5 を IPIP-NEO 一本化、LIWC 全廃)** (v2 採用)
   - 理由: blockers.md DB10 honest framing と完全整合、license 議論自体が消滅、
     work cost 最小。
   - 補強: v2 自身がリスク 3 で挙げた「self-report bias」対策として、ICC < 0.6
     が頻発した場合の **second opinion (BIG5-CHAT regression head)** を
     `decisions.md` に re-open 条件として明記 (defer ではなく conditional fallback)。

3. **Orchestrator: 既存 scheduler に `golden_baseline_mode: bool` minimum patch** (v2 採用)
   - 理由: scheduler 不変条件維持、新 layer 創設の cost 回避、既存テスト破壊
     リスク最小。

4. **計算 timing: 全 post-hoc per-run CLI** (v2 採用)
   - 理由: DB6 (per-turn は粒度であって live timing ではない) と整合、live
     inference 負荷ゼロ、dev iteration が早い。

### v1 の補強として残す要素 (2 件)

5. **新規 metric file は `evidence/tier_{a,b,c}.py` ではなく細分化** (v1 寄せ)
   - 理由: `tier_a.py` 1 file に 5 metric (Burrows / MATTR / NLI / novelty /
     Empath proxy) を詰めると 1 file が 800+ 行になり review-friendly でない。
   - **採用**: `evidence/tier_a/` directory + `{burrows,mattr,nli,novelty,empath_proxy}.py`
     の sub-module 構造。`evidence/` 既存 pattern と整合 (`evidence/scaling_metrics.py`
     は単 file だが metric 数が増える tier_a は分離合理)。

6. **Hardware allocation 表は Phase 単位で詳細化** (v1 寄せ)
   - 理由: v2 の 11 行 table は subtask が flat、依存関係 / 同期点が table から
     読みにくい。v1 の Phase P0/P1/.../P7 区分の方が `tasklist.md` の `[Mac]` /
     `[GG]` / `[Mac→GG]` tag 付与に直結する。
   - **採用**: v1 形式 (Phase 列 + Subtask + Owner + Machine + VRAM + Hours +
     Sync point) を採用、v2 の subtask 内訳を取り込む。

### 微調整 (2 件)

7. **Hybrid baseline の比率は defer**
   - v2 の 200/300 (stimulus / 自然対話) は arbitrary。本タスクで pilot run
     50 turn ずつで両方の bootstrap CI を測り、empirical に比率決定する条項を
     `blockers.md` に追加。default は 200/300 で start。

8. **Tier C nightly infra**: **systemd --user timer + flock + nvidia-smi
   preflight** (v2 採用)、ただし Mac launchd → ssh trigger は **オプション**
   (採用しない、systemd-timer 単独で実用十分)。
   - 理由: 構成を最小化、master/agent の責務分離は将来 ablation で再検討。

### v1 vs v2 の決定的な分岐の根拠

最も重い分岐は **LIWC Option C vs D**。これは Big5 claim を **派生 (LIWC dictionary
score → Big5 推定)** か **直接 (IPIP-NEO 質問紙 → Big5 推定)** にするかという
**measurement model の根本選定**。Option D は

- (a) blockers.md DB10 の "LIWC OSS proxy で Big5 claim は honest に避ける" と
  完全整合
- (b) LIWC license decision tree を node ごと刈り取れる (work cost zero)
- (c) IPIP-NEO は psychometric literature で Big5 推定の standard で、self-report
  bias は周知だが well-documented
- (d) v1 Option C の spaCy 自前 dictionary は category 設計と validation に
  数日〜数週間の work cost がかかり、validation を solo で完結させる現実性
  が低い

を満たす。Option D 採用は本タスクの blockers 1 件 close と work cost 削減の
両得で、根拠の明示的な変更 (Big5 measurement model を直接 self-report に倒す)
が trade-off として説得力を持つ。

### ハイブリッド最終形の要旨

> **DuckDB 単 file + schema-guard + CI grep gate** で DB5 を構造的に守り、
> **LIWC Option D (Big5 を IPIP-NEO に一本化)** で blockers 1 件即時 close、
> **既存 scheduler に minimum patch** で破壊リスク最小、**hybrid baseline
> (stimulus battery + 自然対話)** で drift gate noise 抑制、**全 post-hoc
> 計算** で live inference 不負荷、**systemd-timer + flock + nvidia-smi
> preflight** で Tier C nightly を OS 任せ。Hardware allocation は v1 の
> Phase 区分形式を採用、metric file は `evidence/tier_a/` sub-module 構造で
> review-friendly に維持。
