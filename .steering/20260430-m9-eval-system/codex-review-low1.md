Reading prompt from stdin...
OpenAI Codex v0.125.0 (research preview)
--------
workdir: /Users/johnd/ERRE-Sand Box
model: gpt-5.5
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR, /Users/johnd/.codex/memories] (network access enabled)
reasoning effort: xhigh
reasoning summaries: none
session id: 019ddf19-7399-7a80-a404-a9c94cc0aa4c
--------
user
# Codex independent review — LOW-1 RoleEval wording 決着 (P2a 着手直前)

## 状況

- タスク: `m9-eval-system` (M9-A event-boundary observability の後続、4 タスク化された M9 milestone の 1)
- 現在: Phase 1 完了 + P0a-P1b 完了。P2a (stimulus battery YAML 起草、4h、Mac) 着手直前
- main = `ff29ca2`、 P0-P1 完了分は未コミット (15 ファイル、本タスク完了時に単一 commit 予定、ユーザー指示)
- 前回の Codex review (`codex-review.md`、HIGH 5 / MEDIUM 6 / LOW 1) は Phase 1 終了時実施済、
  HIGH 全件は `design-final.md` に反映、MEDIUM は `decisions.md` の ME-1〜ME-6 に ADR 化済、
  **LOW-1 (RoleEval wording) のみ defer**、本セッション冒頭で決着が必要

## レビューしてほしい判断: LOW-1 RoleEval wording

`design-final.md` §"Hybrid baseline 採取" の stimulus battery は以下:

```
- 最初の 200 turn: curated stimulus battery を fixed order で投入
  - Wachsmuth Toulmin 引き出す prompt: 30
  - ToM info-asymmetric scenario (chashitsu): 20
  - RoleEval-adapted Kant biographical MCQ: 10  ← LOW-1 該当
  - persona-conditional moral dilemma: 10
  - 計 70 stimulus × 3 巡 = 210 turn
- 残り 300 turn: 自然対話
```

stimulus YAML は per-persona (`golden/stimulus/{kant,nietzsche,rikyu}.yaml`) で起草するため、
"RoleEval-adapted **Kant** biographical MCQ" のままでは Nietzsche / Rikyū 用 YAML が
意味不成立。`blockers.md` LOW-1 で 3 案 defer:

- **Option A**: 各 persona に biographical MCQ 10 問ずつ起草 (Kant / Nietzsche / Rikyū それぞれの
  伝記・思想史的 attested fact から)
- **Option B**: Kant biographical MCQ は Kant のみ、Nietzsche / Rikyū は別の floor diagnostic
  (Wachsmuth Toulmin に振替) で 70 turn 構成は維持
- **Option C**: RoleEval を全廃し Wachsmuth/ToM/dilemma の 60 stimulus × 3.5 巡で 210 turn 構成

## Claude (本体エージェント) の暫定推薦: Option A

trade-off 比較表 (Claude 提示):

| 軸 | A | B | C |
|---|---|---|---|
| stimulus 構成の persona 間斉一性 | ◎ 全 persona 70 = (30/20/10/10) で同形 | △ Kant (30/20/10/10), 他 (40/20/0/10) | ◎ (35/23/0/12) |
| bootstrap CI cross-persona 比較 | ◎ category mass 同一 | × stimulus type imbalance 交絡 | ◎ |
| persona-factuality dimension | ◎ 全 persona | △ Kant のみ | ✗ 完全消失 |
| Rikyū MCQ 起草難度 | △ legend 多、attested fact は 5-7 件確保可 | ○ 不要 | ◎ 不要 |
| Nietzsche MCQ 起草難度 | ○ Basel 1879 / Sils Maria / Overbeck 書簡で十分 | ○ 不要 | ◎ 不要 |
| drafting 工数 | +1.5h (30 MCQ) | ≈同等 | -0.5h |
| 後続 m9-eval-corpus で再 open 余地 | ◎ MCQ pool 別途精緻化可 | △ asymmetry 固定 | ✗ battery 再設計要 |

Claude の推薦理由:
1. **persona-factuality は 4 軸の 1 つ** (argumentation / ToM / persona-factuality / moral disposition) —
   RoleEval を切ると "persona knows itself" の dimension が消え、style / argumentation /
   ToM の 3 軸偏重に
2. **bootstrap CI 交絡を持ち込まない** — option B は per-persona stimulus mass 違いで
   Vendi/Burrows の persona 横比較が "stimulus 種類効果 × persona 効果" 分離不能
3. **Rikyū MCQ 起草実現可能** — 利休道歌構造 / 待庵物理寸法 / 北野大茶湯 1587 / Hideyoshi 確執 /
   Sakai 商人出自 / 1591 賜死 / 子 (道安・少庵) 等、attested fact 10 件は確保
4. **MCQ accuracy の cross-persona 絶対比較が無意味化する弱点** は ME-1 ADR の base model
   control measurement (`Δaccuracy = persona_run − base_control`) で吸収

## レビュー対象 (Claude のリーズニングを批判的に検証)

1. **Option A 推薦は妥当か?** Claude の論拠 4 点 (4 軸 dimension / CI 交絡 / Rikyū 実現性 /
   ME-1 で吸収) のうち、見落とし / 誤認 / 弱点はあるか?
2. **A/B/C 以外の Option D が存在するか?** (例: Kant 用 MCQ 10 を全 persona 共通の "general
   philosophical attribution" MCQ に置き換え、persona-factuality を sacrifice せずに per-persona
   起草を回避する案など、より優れた選択肢)
3. **Option A 採択時の落とし穴** — biographical MCQ の category 設計、distractor 設計、
   factual recall の信頼性確保で見落としそうな点 (例: persona prompt が "I am Kant" と
   応答する時の hallucination risk vs 史実 recall の混在)
4. **ME-1 base model control の活用が本当に絶対比較問題を吸収するか?** Δaccuracy の解釈で
   psychometric / NLP-eval literature 上の落とし穴は無いか?
5. **DB7 LOW-1 (synthetic 4th persona heldout fixture) との整合** — 4th persona 用 MCQ をどう
   設計するか (Claude は本セッションで 3 persona の MCQ のみ起草予定、4th は P2c の test 範囲)
6. **後続 P3 採取への impact** — option choice が 7500 turn 採取の解釈にどう影響するか、
   LOW-1 を P3a-decide / P3 まで再 defer する余地はあるか

## 参照ファイル

Codex は以下を読んでから判断:

- `.steering/20260430-m9-eval-system/design-final.md` (特に §Hybrid baseline / §Stimulus battery)
- `.steering/20260430-m9-eval-system/blockers.md` (LOW-1 finding 全文)
- `.steering/20260430-m9-eval-system/decisions.md` (ME-1: IPIP-NEO fallback trigger / ME-4: ratio
  defer / ME-6: Burrows corpus QC が関連)
- `.steering/20260430-m9-eval-system/codex-review.md` (前回 review の verbatim、LOW-1 の Codex
  原文がここにある)
- `personas/kant.yaml`, `personas/nietzsche.yaml`, `personas/rikyu.yaml` (cognitive_habits / flag
  分布 / primary_corpus_refs を確認、Rikyū の attested fact 量を判断)

## 報告フォーマット

verbatim で `.steering/20260430-m9-eval-system/codex-review-low1.md` に保存される。以下の構造で:

### Verdict (1 行)
"Adopt Option A" / "Adopt Option B" / "Adopt Option C" / "Adopt new Option D (described below)" /
"Re-defer to P3a-decide" のいずれか。

### Findings

各 finding に Severity (HIGH/MEDIUM/LOW) を付ける:

- **HIGH**: 採択判断を覆す根拠がある or 致命的な見落としがある
- **MEDIUM**: 採択判断は変わらないが、補強 / 明文化が必要
- **LOW**: 補足的な提案、blockers / decisions に記録すれば十分

各 finding は以下を含む:
- 一行 summary
- 観察された事実 / 根拠 (Claude の論拠のどこに対応するか明記)
- 推奨 action (具体的な編集 / 追加 / 削除指示)

### Open question (任意)

Claude が決められない / Codex でも決められない事項があれば 1-2 件まで明示。

## 制約

- read-only review。`.steering/` `personas/` `src/` のいずれも書き換えない (Codex sandbox は
  `.codex/config.toml` で `network_access=false` + read-only 既定の想定)
- 出力は日本語 + 必要箇所英語混在で OK (前回 review と同様)
- per_invocation_max=200K token の budget guard あり、本 review は narrow scope なので
  100K 以内が目安

hook: SessionStart
hook: SessionStart Completed
hook: UserPromptSubmit
hook: UserPromptSubmit Completed
codex
`erre-workflow` をレビュー入口として読み、以降は指定ファイルだけを read-only で確認します。LOW-1 の採択判断に絞って、実装や `.steering/` 編集は行いません。
exec
/bin/zsh -lc "sed -n '1,240p' .agents/skills/erre-workflow/SKILL.md" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
---
name: erre-workflow
description: >
  ERRE-Sandbox task workflow for Codex. Use when starting, designing, implementing,
  reviewing, or finishing repository work; when the user mentions /start-task,
  /add-feature, /fix-bug, /refactor, /reimagine, /review-changes, or /finish-task;
  or when .steering records, Codex setup, task plans, or implementation handoffs are needed.
---

# ERRE Workflow

This is the Codex-native replacement for the Claude slash-command workflow. Claude command
files in `.claude/commands/` are reference material only; Codex should execute the workflow
through normal tool use, `.steering/` records, skills, hooks, and custom agents.

## Quick Start

1. Read `AGENTS.md`, `docs/development-guidelines.md`, and the relevant domain skill.
2. Create or update `.steering/YYYYMMDD-task-name/` before implementation work:
   `requirement.md`, `design.md`, and `tasklist.md` are required.
3. For design-heavy work, keep implementation paused until a plan is accepted. If the task
   has multiple plausible designs, perform a reimagine pass before editing source files.
4. Implement in small steps, updating `tasklist.md` as work completes.
5. Verify with focused checks first, then the documented full checks when feasible.
6. Finish by reviewing the diff and recording any decisions or limitations.

Use subagents only when the user explicitly asks for delegation or parallel agent work.
When they do, prefer the project-scoped agents in `.codex/agents/`.

## Task Start

Create `.steering/YYYYMMDD-task-name/` with:

- `requirement.md`: background, goal, scope, out of scope, acceptance criteria.
- `design.md`: approach, changed areas, compatibility, test strategy, rollback.
- `tasklist.md`: checkboxes at roughly 30-minute granularity.
- `decisions.md`: only for meaningful tradeoffs or policy choices.
- `blockers.md`: only when blocked or carrying deferred risk.

Use the current local date in `YYYYMMDD`. Prefer a short kebab-case task name.

## Implementation Flows

- **Feature**: read existing patterns, document the design, implement narrowly, add tests or
  verification proportional to risk, update docs when behavior changes.
- **Bug fix**: reproduce or explain the failure, record root cause, add or identify a
  regression check when feasible, then make the smallest defensible fix.
- **Refactor**: establish current checks first, preserve behavior, change in small steps,
  and avoid mixing feature or bug-fix work into the same task.

For source edits under `src/erre_sandbox/`, always consider:

- `architecture-rules` for layer direction and GPL/cloud API constraints.
- `python-standards` for Python style.
- `error-handling` when async, retry, timeout, WebSocket, sqlite, or LLM fallback behavior changes.
- `test-standards` when adding or changing tests.

## Reimagine

Use this for architecture, public interfaces, difficult bugs, and designs with multiple
credible approaches:

1. Save the first plan as `design-v1.md`.
2. Re-read only `requirement.md` and produce a fresh alternative in `design.md`.
3. Compare the two in `design-comparison.md`.
4. Choose v1, v2, or a hybrid and record the reason in `decisions.md`.

Do not use reimagine after implementation has already created side effects that would need
manual rollback.

## Review And Finish

Before final delivery:

- Run focused checks for touched areas.
- Run `uv run ruff check src tests`, `uv run ruff format --check src tests`,
  `uv run mypy src`, and `uv run pytest` when feasible.
- Review `git diff` for unrelated changes and do not revert user work.
- Update `tasklist.md` and `design.md` with what actually happened.
- Mention skipped checks or residual risk in the final response.

Do not commit unless the user asks. If committing, use `git-workflow`.

codex
まず設計側の LOW-1 周辺と ADR を読みます。次に persona YAML の `primary_corpus_refs` と factual basis を確認して、A が本当に成立するかを切り分けます。
exec
/bin/zsh -lc "sed -n '1,260p' .steering/20260430-m9-eval-system/blockers.md" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
# Blockers & Deferred Items — m9-eval-system

## defer 方針

Codex `gpt-5.5 xhigh` review LOW finding および本タスクで即決できない判断事項を defer。
defer 期限と reopen 条件を明示。M9-B 親タスクの blockers (`.steering/20260430-m9-b-lora-execution-plan/blockers.md`)
とは scope を分離し、本タスク固有の項目のみここに記録。

## Codex LOW findings

### LOW-1: RoleEval wording — Kant-only か persona-specific か (Codex LOW-1)

- **finding**: design.md §Hybrid baseline の stimulus battery で
  "RoleEval-adapted Kant biographical MCQ: 10" と書かれているが、stimulus YAML は
  per persona (`golden/stimulus/{kant,nietzsche,rikyu}.yaml`) で、Nietzsche / Rikyu の
  MCQ が Kant biographical のままだと意味が成り立たない
- **暫定方針** (P2a stimulus 起草時に決着):
  - **option A**: 各 persona に対し biographical MCQ を 10 問ずつ起草 (Nietzsche
    biographical MCQ / Rikyu 茶の湯 MCQ)
  - **option B**: Kant biographical MCQ は Kant のみで実施、他 2 persona は別の
    floor diagnostic (Wachsmuth Toulmin に振り替え) で 70 turn 構成は維持
  - **option C**: RoleEval を全廃し Wachsmuth/ToM/dilemma の 60 stimulus × 3.5 巡で
    210 turn を構成
- **defer 先**: P2a (stimulus battery YAML 起草時)
- **reopen 条件**: option A-C いずれか確定、または P3a pilot で実用判断
- **status**: defer

## 本タスクで決められない判断事項

### LIWC license 評価 (M9-B blockers から継承、本タスクで close 候補)

- **issue**: M9-B `blockers.md` の "LIWC 商用 license の最終可否判定"
- **本タスクでの決着**: **Option D 採用** (LIWC 全廃、Big5 を IPIP-NEO 自己申告に
  一本化、Empath は Tier A diagnostic のみ) を `design.md` で確定済
- **defer 先**: 本タスク P0a で M9-B blockers.md を Edit して "Option D 採用" 記載
  → 該当項目 close
- **reopen 条件**: ME-1 fallback fire により LIWC 検討が再浮上した場合のみ
- **status**: P0a で close 予定 (本セッション or 次セッション)

### Burrows corpus license (Cambridge Edition / Kaufmann translation 等)

- **issue**: ME-6 で reference corpus に英訳・独訳を含めることを採択したが、現代
  edition は royalty / re-distribution restriction の可能性
- **暫定方針** (ME-6 で確定):
  - public domain edition (Akademie-Ausgabe Kant 独 / KGW Nietzsche 独) を一次採用
  - 英訳は **license 確認後** に追加採否判断、確認できなければ独原典単独で運用
- **defer 先**: P1b (reference corpus 整備時)
- **reopen 条件**: Cambridge / Kaufmann が re-distribution restriction で使えない →
  独原典単独で運用 (英訳経路 fallback)
- **status**: P1b で **PD-only 路線確定** (2026-05-01)。英訳経路は本セッションでは
  扱わず、独原典単独 (Akademie-Ausgabe Wikisource 経路) + Project Gutenberg
  Kröner-tradition (KGW Colli/Montinari は editorial copyright 回避) +
  日本古典 (利休道歌 5 verses) で commit。Cambridge / Kaufmann edition は
  下記 "Burrows reference corpus — English translations defer" で independent
  に re-open 候補

### Burrows reference corpus — English translations defer (2026-05-01 P1b 開設)

- **issue**: ME-6 で en 経路 (Cambridge Edition Kant / Kaufmann Nietzsche) も
  reference に含める設計だったが、両者とも under copyright で本セッション中の
  re-distribution は不可と判定。
- **暫定方針** (P1b 完了、commit せず defer):
  - en 経路は本タスクでは reference 化しない (provenance.yaml に未登録、loader は
    `load_reference("kant", "en")` で `ReferenceCorpusMissingError`)
  - 独原典のみで Burrows 経路を回し、対話が英語に流れた場合は
    `BurrowsLanguageMismatchError` で明示 fail (silent fallback 禁止)
  - 自動翻訳系 (機械翻訳済みの training-distillation コーパス) は stylometric
    比較対象として不適切 (translator stylistic signature が混入) のため候補外
- **defer 先**:
  - **第 1 候補**: PD edition の英訳が判明した場合 (例: Cambridge 古い edition で
    PD と確認 / Project Gutenberg の旧訳) は本 entry を re-open し
    `_provenance.yaml` 追加 + vectors.json 再 build
  - **第 2 候補**: 後続タスク m9-eval-corpus で en 経路を独立検討
- **reopen 条件**: Kant / Nietzsche の英訳 PD edition が確認 / 入手された時点
- **status**: defer (本セッションでは扱わない)

### Burrows reference corpus — toy-scale corpus expansion (2026-05-01 P1b 開設)

- **issue**: P1b は **toy reference 路線** で commit (Kant 2656 words / Nietzsche
  12002 words / Rikyu 122 tokens)。ME-6 の "5K-word chunk stability test" は
  Nietzsche のみ実検証 (2 chunk Spearman ρ ≥ 0.8 PASS) で、Kant / Rikyu は
  explicit skip + reopen 条件 documented。
- **暫定方針** (P1b 完了、commit 済):
  - Nietzsche: 12K で 2× 5K chunk 確保、ρ=1.0 観測 PASS
  - Kant: 2.6K (5K 未達) で skip、reopen 条件 = Akademie-Ausgabe Bd. VIII
    全文 (~50K-100K words) 取り込み
  - Rikyu: 122 tokens (極小) で skip、reopen 条件 = 青空文庫の利休関連作品 /
    国文大観 OCR / ja.wikisource djvu OCR pipeline 経由で ~5K-10K tokens
    確保
- **defer 先**: 後続タスク `m9-eval-corpus` (本タスクから独立化)
- **reopen 条件**:
  - Kant 全文取り込み (license PD のため block 無し、技術 effort のみ)
  - Rikyu 大規模 PD 古典資料 acquisition path 確立
- **status**: defer (本タスクでは toy 路線で完結)

### Burrows Delta multi-lang reference の閾値 (M9-B blockers から継承)

- **本タスクでの決着**: ME-6 ADR で 50K 固定閾値を **棄却**、5K-word chunk stability
  test (Spearman ρ ≥ 0.8) に置換
- **defer 先**: P1b 完了時に corpus QC test 実行で確定
- **reopen 条件**: chunk stability test で rank instability 検出
- **status**: ME-6 ADR で方針確定、empirical 確認は P1b

### Judge bias mitigation runbook (M9-B blockers から継承)

- **issue**: Prometheus 2 / G-Eval bias mitigation 手順
- **暫定方針** (M9-B 既出):
  - position-swap averaging
  - length normalization
  - two local judges for close calls
  - human spot checks
  - CI over repeated runs
- **defer 先**: P6 (Tier C nightly infra) 実装時に runbook 起草
- **reopen 条件**: judge LLM の選択が確定 (Prometheus 2 8x7B vs Qwen2.5-72B 等)
- **status**: P6 着手時、本タスクでは無 unblock

## ME-1 conditional re-open watch (Big5 fallback fire watch)

ME-1 ADR で IPIP-NEO fallback の発火条件を明文化したが、判定 timing が **golden
baseline 採取後** (P5 完了時)。発火した場合の child ADR 作成を本 blockers で track:

- **trigger**: golden baseline 採取後の Big5 ICC 計測で ≥2/3 personas が ICC < 0.6
  または lower CI < 0.5
- **trigger 検出**: P5 完了直後の自動チェック (`evidence/tier_b/big5_icc.py`)
- **fire 時の action**: BIG5-CHAT regression head 実装 ADR を別途起票 (ME-1 child)
- **status**: monitor (P5 完了まで no-op)

## ME-4 ratio re-confirm watch

- **trigger**: P3a 完了 → P3a-decide で ratio 確定 → ME-4 ADR Edit
- **status**: P3a 完了まで monitor

## reopen トリガ一覧 (本タスク内 checklist)

| 項目 | reopen 条件 | trigger 場所 |
|---|---|---|
| LOW-1 RoleEval wording | option A/B/C 確定 | P2a stimulus 起草 |
| Burrows corpus license (independent) | Cambridge / Kaufmann PD edition 確認 | m9-eval-corpus |
| Burrows en translations defer | PD 英訳 edition 入手 | m9-eval-corpus / 後続 |
| Burrows toy-scale expansion | Akademie-Ausgabe 全文 / 利休関連 PD 大規模 | m9-eval-corpus |
| Burrows chunk stability (Nietzsche) | rank instability 検出 (現状 ρ=1.0 PASS) | golden baseline 採取後 |
| Judge bias runbook | judge LLM 選択確定 | P6 Tier C |
| ME-1 Big5 fallback | ≥2/3 ICC < 0.6 in golden | P5 completion |
| ME-4 ratio confirm | P3a CI width 測定 | P3a-decide |

## 設計上の不確実性 (記録のみ、defer ではない)

### Tier B の effective sample size (Codex HIGH-2 補強として)

- DB9 の Tier B per-100-turn metric は 500 turn / 100 = 5 window/run × 5 run = 25
  window/persona しか無く、bootstrap CI が広い (Codex HIGH-2 evidence)
- 反復: P5 で実際の CI 数値を観測、persona-discriminative かを判定
- 不適切なら DB9 sub-metric を Tier A 系に入れ替え検討 (M9-B `blockers.md` の
  "Tier B sub-metric 3 個の選定妥当性" 項目と整合)

### sentinel test の coverage 完全性 (Codex HIGH-1 補強として)

- HIGH-1 で sentinel-based 動的契約を導入したが、未来の caller (例 Rust/Go tooling)
  が増えた時に sentinel test scope が網羅できるかは継続課題
- 反復: 新規 training egress path が追加される PR で sentinel test に caller 追加を
  PR review checklist 化 (P0b で codex hooks に追加検討)

exec
/bin/zsh -lc 'rg -n "Hybrid baseline|Stimulus battery|stimulus|RoleEval|MCQ|LOW-1|persona-factual|base model|ME-1|ME-4|ME-6" .steering/20260430-m9-eval-system/design-final.md' in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
18:| P2a | `golden/stimulus/{kant,nietzsche,rikyu}.yaml` 起草 (70 stimulus/persona × 3 巡 = 210 turn) | Claude | Mac | CPU only | 4h | review |
20:| **P2c** | **External golden driver** (`evidence/golden_baseline.py`) を `schedule_initiate`/`record_turn`/`close_dialog` 公開 API のみで実装、**input queue 依存無し** (Codex HIGH-4 反映) | Claude | Mac | CPU only | 3h | unit test (synthetic 1 stimulus 駆動) 緑 |
31:- Mac (master/dev) は設計・実装・schema・bootstrap CI・stimulus 起草まで担当
110:### Golden baseline 採取: Hybrid (200 stimulus + 300 自然対話) — v2 採用、比率は pilot で defer 解消
113:- 最初の **200 turn**: curated stimulus battery を fixed order で投入
116:  - RoleEval-adapted Kant biographical MCQ: 10
118:  - 計 70 stimulus × 3 巡 = 210 turn (端数 10 turn は最後 stimulus を切り詰め)
125:- 純 stimulus baseline は ζ 軸 (mode 遷移) を測れず M9-A event-boundary observability
146:**stimulus 投入は外部 golden driver から公開 API 経由** (Codex HIGH-4 反映、元案の
149:- `evidence/golden_baseline.py` の `GoldenBaselineDriver` クラスが、stimulus YAML を
152:     (`zone` は stimulus YAML の場指定 = peripatos / chashitsu / agora / garden)
153:  2. stimulus prompt を agent に inference させ、`record_turn(DialogTurnMsg)` で
155:  3. 規定 turn 数 (stimulus battery では各 stimulus 1-3 turn) 到達後
165:- `tests/test_evidence/test_golden_baseline.py::test_one_stimulus_cycle_dryrun` —
166:  driver が **1 つの stimulus を schedule_initiate → record_turn → close_dialog の
167:  full cycle で実行** できることを synthetic stimulus + mock LLM で確認
168:- `tests/test_evidence/test_golden_baseline.py::test_70_stimulus_battery` — 70 stimulus
263:- `golden_baseline.py` — stimulus battery YAML loader + run 駆動 (既存 scheduler に
277:- `golden/stimulus/{kant,nietzsche,rikyu}.yaml` — 70 stimulus/persona
279:- `personas/_synthetic_4th.yaml` — DB7 LOW-1 fixture (Big5 が 3 persona と直交する
293:- `tests/test_evidence/test_golden_baseline.py` — synthetic 4th persona DB7 LOW-1 含む
315:  P2a stimulus battery YAML          │
319:  P3  golden baseline 採取 (G-GEAR、200 stimulus + 300 自然対話)
422:### DB7 LOW-1 (synthetic 4th persona heldout fixture)
491:4. **Hybrid baseline 比率 200/300 の arbitrary 性**
492:   - 70 stimulus × 3 巡 = 210 turn は Wachsmuth/ToM/RoleEval/dilemma の 4 系統に
512:| IPIP fallback trigger operational definition | MEDIUM-1 | `decisions.md` ME-1 ADR | ✅ ADR 化 |
517:| Burrows token floor: corpus QC 化 (固定 50K → ≥5K-word chunk stability) | MEDIUM-6 | `decisions.md` ME-6 ADR / `blockers.md` reopen 条件 | ✅ ADR 化 |
518:| RoleEval Kant 限定 vs persona-specific MCQ 区別 | LOW-1 | `blockers.md` defer | ✅ defer |
528:  既存 scheduler minimum patch / 全 post-hoc / systemd-timer + flock / Hybrid baseline
543:  - **微調整 1**: Hybrid baseline 比率 200/300 は default で start、P3b pilot で
593:  公開 API のみで stimulus を駆動する形に変更
596:- driver の dry-run test (1 stimulus + 70 stimulus battery) を P2c に追加

exec
/bin/zsh -lc "sed -n '1,320p' .steering/20260430-m9-eval-system/decisions.md" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
# Decisions — m9-eval-system (Codex review MEDIUM 反映)

## ADR 体裁

各 ADR は M9-B `.steering/20260430-m9-b-lora-execution-plan/decisions.md` と同形式の
5 要素 (決定 / 根拠 / 棄却 / 影響 / re-open 条件)。本 ADR set は M9-B DB1-DB10 と
**並列** で、m9-eval-system タスク独自の 6 件 (Codex `gpt-5.5 xhigh` review MEDIUM
を反映) + 1 件 (HIGH-3 で確定する ratio の placeholder)。

ID prefix: `ME` (m9-Eval-system) で M9-B `DB` と区別。

---

## ME-1 — IPIP-NEO fallback trigger operational definition (Codex MEDIUM-1)

- **決定**: BIG5-CHAT regression head conditional fallback の **発火条件** を以下に
  確定:
  - **trigger**: golden baseline 採取後 (3 persona × 5 run の Big5 ICC 計測完了時点) に
    **≥2/3 personas で ICC 点推定 < 0.6 OR 95% lower CI bound < 0.5**
  - **検出 timing**: P5 (bootstrap CI) 完了直後の自動チェック、`evidence/tier_b/big5_icc.py`
    が判定して `decisions.md` に re-open 候補を append
  - **追加 diagnostic** (常時計測): acquiescence index (logit balance)、straight-line
    response (≥10 連続同回答)、balanced/reverse-keyed item agreement
  - **control comparison**: persona prompt 無し base model (qwen3:8b raw) で同 IPIP-NEO
    を 1 回測定し、persona 効果と base model self-report bias を separately report
- **根拠**:
  - Codex MEDIUM-1: 「ICC < 0.6 が頻発」の頻発に denominator 無し → 監査不能
  - Salecha et al. 2024 (arXiv 2405.06058): LLM Big5 self-report に social
    desirability bias の empirical 報告
  - Koo/Li ICC 解釈: 0.5-0.75 = moderate (effectsize docs)、0.6 boundary は
    "moderate vs questionable" の境界
  - acquiescence / straight-line / reverse-keyed は psychometric standard (Tomas
    et al., Schmidt et al.)
- **棄却**:
  - 元案「frequent」のみで quantitative threshold 無し → 監査不能で棄却
  - 全 persona AND 条件 (3/3) → false negative リスク (1 persona で fallback 発火しても
    measurement model 全体に問題があり得る)
- **影響**:
  - `evidence/tier_b/big5_icc.py` に diagnostic 4 種 (ICC point, lower CI, acquiescence,
    straight-line) を追加
  - golden baseline 後 `decisions.md` に再 open 判定 ADR 追記の workflow
  - control measurement 1 run (~10 turn equivalent) を P3 にも組み込み
- **re-open 条件**:
  - golden baseline 採取後の判定で fallback fire → BIG5-CHAT regression head
    実装 ADR を別途起票 (本 ADR の child)
  - 0.6 / 0.5 閾値が persona-specific に不適切と判明 → persona-conditional
    threshold に変更検討

---

## ME-2 — DuckDB snapshot semantics (G-GEAR write → Mac read-only) (Codex MEDIUM-2)

- **決定**: G-GEAR が DuckDB file の唯一 writer、Mac は read-only consumer。
  rsync は以下の protocol で実行:
  1. **G-GEAR 側**: 採取セッション終了時に `con.execute("CHECKPOINT")` →
     `con.close()` で WAL を main file に flush
  2. **G-GEAR 側**: `cp <golden>.duckdb /tmp/<golden>.snapshot.duckdb` で同 fs 内 copy
     (DuckDB の同時 open lock 衝突回避)
  3. **G-GEAR → Mac rsync**: `rsync -av /tmp/<golden>.snapshot.duckdb mac:/data/eval/golden/`
  4. **Mac 側 atomic rename**: rsync 完了後 `mv` で `<golden>.duckdb.tmp` → `<golden>.duckdb`
     (部分転送 file を application が open しないため)
  5. **Mac 側 open**: `duckdb.connect(path, read_only=True)` を強制 (`eval_store.py`
     の `connect_training_view()` / `connect_analysis_view()` の両 entry で wrapper enforced)
  - **NFS / SMB / iCloud 共有 fs 経由は禁止** (DuckDB doc が file lock 警告)
- **根拠**:
  - Codex MEDIUM-2: live G-GEAR file を Mac から open は CHECKPOINT 前なら破損リスク
  - DuckDB doc (Concurrency): single-process write + multi-process read-only OK、
    ただし shared fs 注意
  - atomic rename は POSIX 移動が same-fs 内 atomic である事実に依拠
- **棄却**:
  - live file の直接 read → 破損 / 古い snapshot 読み出しリスク
  - SQLite WAL 風の hot replication → DuckDB は WAL replay の cross-process 安全性が
    documented でない、棄却
- **影響**:
  - `infra/scripts/sync_golden_baseline.sh` (新規) で G-GEAR → Mac の rsync orchestration
  - `eval_store.py` の Mac 経路は read_only=True 強制 (test 化)
  - golden baseline 採取 SOP に CHECKPOINT step を追加
- **re-open 条件**:
  - dataset size が大きく (>100GB) rsync コスト過大 → DuckDB native replication 機構
    検討
  - cross-fs 運用 (G-GEAR が cloud bucket に書く) が必要 → snapshot semantics 再設計

---

## ME-3 — Tier C lock + preflight TOCTOU close (Codex MEDIUM-3)

- **決定**:
  1. **Lock の包含範囲**: `flock` を Prometheus 起動前ではなく **`nvidia-smi` preflight
     も含む全 Tier C command** を内側に enclose する形に拡張。autonomous loop は
     **同じ lock file** (`/var/run/erre-eval-tier-c.lock`) を使い、明示的に共有させる:
     ```bash
     flock -n /var/run/erre-eval-tier-c.lock python -m erre_sandbox.cli.eval_tier_c
     ```
     `eval_tier_c` 内部で nvidia-smi preflight → Prometheus 起動 → 評価 → unload を
     一直線で実行、preflight と起動の間に lock を放さない。
  2. **systemd-timer の `Persistent=`**: **`Persistent=false`** を採用 (default 維持を
     明示)。深夜 02:00 fire を miss した場合の catch-up は不要 (autonomous run と
     conflict する確率を下げる)。**skip 時は exit code 75 (EX_TEMPFAIL)** で journal log
     可視性を確保。
  3. **autonomous loop の lock 取得方針**: autonomous loop も同 lock file に
     `flock -s` (shared lock) で touch する形にし、Tier C は `flock -n -x` (exclusive)
     で取得を試みる。autonomous が走っている間は Tier C が即時 fail (skip + log)、
     autonomous が止まっている間のみ Tier C が走れる構造。
- **根拠**:
  - Codex MEDIUM-3: nvidia-smi → Prometheus load の間に他プロセスが load する TOCTOU
  - flock(1) man page: `-n` で immediate fail、合わせて `-x` で exclusive
  - systemd.timer doc: `Persistent=` default false、catch-up が必要なら明示 true
- **棄却**:
  - lock を Prometheus 起動部分のみ → preflight が外れて TOCTOU 残存
  - `Persistent=true` → autonomous run 真昼間 catch-up fire で contention
  - lock 不採用 (preflight だけで判定) → 明確に race condition 残存
- **影響**:
  - `infra/systemd/erre-eval-tier-c.service` の `ExecStart=` が `flock -n -x ... bash -c '...'`
    形式に
  - autonomous loop (M5 ERRE FSM driver) に `flock -s` 追加が必要 (P6 で integrate)
  - `journalctl --user -u erre-eval-tier-c` で skip 履歴が exit 75 として可視
- **re-open 条件**:
  - autonomous run が flock -s を保持できない実装上の制約 → file ベースの
    state machine に置換
  - skip rate が想定より高い (>50%) → スケジュール時間帯見直し

---

## ME-4 — Hybrid baseline ratio: P3a 完了後に確定 (Codex HIGH-3 系の defer ADR)

- **決定**: 200 (stimulus battery) / 300 (自然対話) を **default** とし、P3a (200 turn
  × 両形式 × 3 persona の isolated pilot) で測定した bootstrap CI width に基づき
  P3a-decide で **本 ADR を更新する**。更新後の ratio で P3 (golden baseline 採取) 入り。
- **判定基準**:
  - Burrows Delta CI width / Vendi CI width / Big5 ICC CI width を両 condition
    (stimulus 主体 / 自然対話 主体) で測定
  - 両条件で sub-metric の **mean CI width が小さい比率** を採用
  - 両者が同等 (差 <10%) なら 200/300 default を維持 (operational simplicity)
- **根拠**:
  - Codex HIGH-3: 元案の「P3 採取後 P3b で 50 turn pilot」は順序 invert + 統計力不足
  - 200 turn は Vendi の 200-turn window を 1 cycle 満たす最小値
  - bootstrap CI width が直接的な測定対象 (DB9 quorum の信頼性)
- **棄却**:
  - 200/300 を data なしで freeze → arbitrary
  - P3 後の P3b 50 turn pilot → invalidation リスク
- **影響**:
  - P3a 完了後、本 ADR を Edit で更新 (現 placeholder を実測値で置換)
  - 採用 ratio が P3 に flow
  - blockers.md の "Hybrid baseline 比率 defer" 項目を close
- **re-open 条件**:
  - golden baseline 採取後に DB9 quorum の sub-metric が persona discriminative でない
    と判明 → ratio 再調整 + 再採取検討

---

## ME-5 — RNG seed: hashlib.blake2b で uint64 stable seed (Codex MEDIUM-5)

- **決定**: seed 生成を以下に確定:
  ```python
  import hashlib
  def derive_seed(persona_id: str, run_idx: int, salt: str = "m9-eval-v1") -> int:
      key = f"{salt}|{persona_id}|{run_idx}".encode()
      digest = hashlib.blake2b(key, digest_size=8).digest()
      return int.from_bytes(digest, "big")  # uint64
  ```
  - 5 run × 3 persona = 15 seed を `golden/seeds.json` に commit
  - Mac と G-GEAR の両方で `test_seed_manifest_stable` で identical を assert
  - numpy `Generator(PCG64(seed))` で stream 化
- **根拠**:
  - Codex MEDIUM-5: Python `hash()` は `PYTHONHASHSEED` に salting されプロセス間非決定的
  - blake2b は cryptographic hash で deterministic、digest_size=8 で uint64 適合
  - PCG64 は numpy default、reproducibility が高い
- **棄却**:
  - `hash()` ベース → reproducibility 違反
  - SHA-256 → digest_size 32 で uint64 取り出しが冗長 (blake2b の方が直接的)
- **影響**:
  - `evidence/golden_baseline.py::derive_seed` を導入
  - `golden/seeds.json` を git commit (ascii uint64 list)
  - test 1 件追加 (Mac/G-GEAR 同値性)
- **re-open 条件**:
  - 別 hash algo に project が移行 (例 future Python の hash 強化) → 再評価
  - blake2b の collision 報告 (現実的に零だが)

---

## ME-6 — Burrows reference corpus QC (Codex MEDIUM-6)

- **決定**: 元案の「token count < 50K で z-score noisy」固定閾値を **棄却**、以下の QC
  semantics に置換:
  1. **Tokenization**: per-language tokenizer (独 / 英 / 日)、function word list は
     言語別に curated
  2. **Provenance metadata**: 各 reference corpus に `{source, license, edition,
     translator, year, public_domain: bool}` を YAML で添付 (`evidence/reference_corpus/_provenance.yaml`)
     - Kant 独原典: Akademie-Ausgabe (public domain、確認済)
     - Kant 英訳: 著者 + edition 明記、license 確認 (Cambridge Edition 等)
     - Nietzsche: 独原典 KGW、英訳 Kaufmann (royalty 確認要)
     - Rikyu: 利休百首・南方録 (日本古典、public domain)
  3. **≥5K-word chunk stability test**: corpus を 5K-word chunk に分割し、各 chunk
     から計算した Delta が persona-pair 間で **rank-stable** (Spearman ρ ≥ 0.8) で
     あることを `test_burrows_corpus_qc.py` で fixture 化
  4. **reopen condition**: Delta rank instability (ρ < 0.6) が観測されたら
     blockers.md に reopen 候補を上げる
- **根拠**:
  - Codex MEDIUM-6: 50K は placeholder で empirical 根拠無し
  - Stylometry literature (Computational Stylistics): <5K は確実に poor、20K でも
    text 依存で fail、固定 floor は不適切
  - Eder 2017 "Visualization in stylometry": chunk-based stability test 推奨
- **棄却**:
  - 50K 固定 floor → empirical 根拠無し
  - corpus QC を実施しない → reproducibility と license 双方破綻
- **影響**:
  - `evidence/reference_corpus/_provenance.yaml` 追加
  - `tests/test_evidence/test_tier_a/test_burrows_corpus_qc.py` 追加
  - Cambridge Edition / Kaufmann translation の license 確認が **P1b の prerequisite** に
- **re-open 条件**:
  - chunk stability test で rank instability 検出 → corpus 拡張 or 言語別 fallback
  - 翻訳 license で公表に制約 → public domain edition への切替検討

---

## ME-summary

- 本 ADR 6 件で Codex `gpt-5.5 xhigh` review MEDIUM-1 〜 MEDIUM-6 全件に対応
- ME-4 のみ P3a 結果次第で **再 Edit 確定** が必要 (placeholder ADR)
- LOW-1 (RoleEval Kant 限定) は `blockers.md` に defer (本 ADR set 範囲外)
- 既存 M9-B DB1-DB10 ADR との衝突: 無し
- M2_THRESHOLDS / SCHEMA_VERSION / DialogTurnMsg / RunLifecycleState への破壊変更: 無し

exec
/bin/zsh -lc 'rg -n "LOW-1|RoleEval|Kant|biographical|MCQ|HIGH|MEDIUM|LOW" .steering/20260430-m9-eval-system/codex-review.md' in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
27:thinkers" (Kant / Nietzsche / Rikyu) as local-LLM cognitive agents in a 3D
63:| Golden baseline | **Hybrid**: 200 turn fixed stimulus battery (Wachsmuth Toulmin 30 / ToM info-asymmetric chashitsu 20 / RoleEval-adapted Kant biographical MCQ 10 / persona-conditional moral dilemma 10 = 70 stimuli × 3 cycles, last cycle truncated to 10 turns) + 300 turn natural dialog from existing scheduler (peripatos / chashitsu / agora / garden mode transitions). Ratio 200/300 is **default; P3b pilot run 50 turn each will tune empirically**, recorded in blockers.md. |
72:## Required deliverables (HIGH / MEDIUM / LOW format, identical to M9-B review)
77:### {HIGH|MEDIUM|LOW}-N: <one-line title>
83:- **Severity rationale**: why HIGH (must reflect before P0) vs MEDIUM
84:  (worth recording in decisions.md but defensible to defer judgment) vs LOW
89:- **HIGH** — design must change before P0a starts; ignoring it costs rework
91:- **MEDIUM** — design choice has multiple defensible options; reviewer wants
93:- **LOW** — defer-able with explicit reopen condition. Logged in blockers.md.
132:   design implies per-language reference corpora (Kant German + English
162:  must be flagged as LOW (defer)
176:<2-4 lines: overall verdict (proceed-as-is / proceed-with-HIGH-fixes / re-Plan-required), highest-impact concern, lowest-cost win>
179:<HIGH-N / MEDIUM-N / LOW-N entries in the format above, ordered by severity then numeric>
507:    34	| **Golden baseline 形式** | 自然対話 500 turn × 5 run × 3 persona | **Hybrid: stimulus battery 200 turn (Wachsmuth/ToM/RoleEval/dilemma 70 種 × 3 巡) + 自然対話 300 turn** |
515:    42	| **stimulus battery** | 言及なし | 70 stimulus × 3 巡で Wachsmuth/ToM/RoleEval/dilemma を統制、bootstrap CI noise を抑制 |
659:     5	> Codex `gpt-5.5 xhigh` independent review を Plan 確定前に挟み HIGH 全件反映後に
670:    16	| P1b | reference corpus pickle 整備 (Kant 独+英訳 / Nietzsche / Rikyu / synthetic 4th) | Claude | Mac | CPU only | 2h | fixture test 緑 |
679:    25	| P7 | Codex `gpt-5.5 xhigh` independent review → HIGH 全件反映 | Claude | Mac | CPU only | 1.5h | `design-final.md` rename |
757:   103	  - RoleEval-adapted Kant biographical MCQ: 10
865:   211	- `reference_corpus/` — Kant 独+英訳、Nietzsche、Rikyu、synthetic 4th persona の
879:   225	- `personas/_synthetic_4th.yaml` — DB7 LOW-1 fixture (Big5 が 3 persona と直交する
893:   239	- `tests/test_evidence/test_golden_baseline.py` — synthetic 4th persona DB7 LOW-1 含む
934:   275	  P7  Codex review → HIGH 反映 → design-final.md rename
1017:   358	### DB7 LOW-1 (synthetic 4th persona heldout fixture)
1026:   367	  Burrows Delta が persona-discriminative (Kant ≠ Nietzsche、distance 差 ≥ fixed delta)
1066:   407	## リスクと反復前提 (Codex review HIGH 候補)
1068:   409	5 件、Phase P7 の Codex independent review で HIGH/MEDIUM/LOW にラベル付け予定:
1082:   423	   - Kant 独原典 vs 英訳 vs 日本語 dialog の 3 言語 reference 別保持で防ぐ
1087:   428	   - 70 stimulus × 3 巡 = 210 turn は Wachsmuth/ToM/RoleEval/dilemma の 4 系統に
1139:   480	  `codex-review.md` verbatim 保存 → HIGH 全件反映 → 本ファイルを `design-final.md`
1152:     8	(HIGH 4 / MEDIUM 4 / LOW 2) を全件反映済。
1159:    15	  alternatives (AWQ + LoRA / GPTQ + LoRA / 8-bit LoRA) を記録、bounded Kant spike で
1164:    20	  - codex MEDIUM-2 指摘: 「唯一現実解」は overstated、conservative default と framing
1172:    28	  - Kant spike で NF4 quality が許容範囲外 → 8-bit LoRA fallback
1195:    51	## DB3 — Serving 移行判断: **SGLang-first, vLLM fallback only** (HIGH-3 反映)
1200:    56	  - codex HIGH-3: SGLang は v0.3+ で multi-LoRA / dynamic load/unload / pinned adapters /
1211:    67	  - Kant spike で adapter swap latency > 500ms
1217:    73	## DB4 — Dataset trigger 閾値: `floor AND (coverage OR plateau OR timebox)` (HIGH-1 反映)
1229:    85	  - codex HIGH-1: 4-AND は m9-lora-pre-plan D1 ADR (floor + (coverage OR plateau)) と矛盾
1245:   101	## DB5 — Parquet schema: **raw + sidecar 物理分離** (HIGH-4 反映)
1253:   109	  - codex HIGH-4: boolean flag (evaluation_epoch) だけでは training pipeline が物理的に
1268:   124	## DB6 — Evaluation epoch 分離: Run-level flag + 物理 partition + sidecar (HIGH-4 統合) + 頻度 policy (MEDIUM-4)
1279:   135	  - codex HIGH-4 + MEDIUM-4: Tier C judge LLM (Prometheus 2 8x7B class) は qwen3:8b agent
1281:   137	  - 物理 partition は HIGH-4 解消の core mechanism
1293:   149	## DB7 — Persona N=4 拡張時期: defer to M10 + synthetic heldout 4th in eval tests (LOW-1 反映)
1300:   156	  - codex LOW-1: eval pipeline が N=3 専用に overfit するのを防ぐため、synthetic 4th
1335:   191	## DB9 — Drift gate: composite + bootstrap CI + 2-of-3 quorum (HIGH-2 反映)
1352:   208	  - codex HIGH-2: 「5%」固定 + Tier B noise → false rollback / metric gaming リスク
1370:   226	  - **M9-B 内 deliverable は specs のみ** (実装コードは出さない、MEDIUM-1 反映)
1375:   231	    - Tier D: sparse manual (FActScore-adapted / 専門家 review / RoleEval-adapted MCQ)
1377:   233	    CI 偏差 (Rikyu LOW idea density は適正、Kant HIGH も適正)
1378:   234	  - **golden set staging** (MEDIUM-3 反映):
1384:   240	  - **LIWC alternatives honest framing** (LOW-2 反映): Empath/spaCy は proxy であり LIWC 等価ではない、
1389:   245	  - codex MEDIUM-1 / 3 / LOW-2 反映
1405:   261	**bounded, non-authoritative single-persona Kant LoRA spike を SGLang 上で M9-eval-system
1410:   266	- **scope**: Kant 1 persona のみ、既存 dialog_turn を training data として use、
1425:     5	Codex review LOW finding および設計上 M9-B closure では即決できない判断事項を defer。
1428:     8	## Codex LOW findings (defer)
1430:    10	### LOW-1: synthetic heldout 4th persona in eval tests
1436:    16	### LOW-2: LIWC OSS alternative honest framing
1454:    34	- **issue**: Kant 独原典 vs 英訳 vs 日本語 dialog で idiolect 汚染
1459:    39	  - Kant の場合: 独訳 reference + 英訳 reference を別 baseline として保持
1477:    57	- **issue**: Tier D の expert review に Kant / Nietzsche / Rikyu 専門家の協力が必要
1502:    82	- **対策強化条件**: M9-C-spike Kant が「明らかに人間目視で改善」した場合の判断 protocol を起草
1525:   105	| M9-C-spike leakage | spike Kant 目視改善 | M9-C-spike 完了時 |
1573:    44	  Kant deontology / Nietzsche amor fati の評価軸として直接使える。sparse/dense 分割は
1584:    55	### RoleEval (Shen et al., 2024, arXiv:2312.16132)
1585:    56	- **What**: Role 知識 MCQ — relationships / abilities / experiences の多肢選択
1586:    57	- **限界**: MCQ 形式は recall のみ測定、生成評価ではない
1587:    58	- **ERRE 適用性**: 「Kant biographical MCQ」を pre-gate として cheap 自動化可。役立つが副次的
1636:   107	- **ERRE 適用性**: medium-high。multi-thinker scene (Kant + Nietzsche + observer) は
1656:   127	  Kant categorical-imperative 違反の最近接 proxy
1671:   142	  Kant agent が deontology を utilitarian より systematically over-weight するか測れる
1675:   146	- **What**: 哲学者・立場・概念の MCQ
1676:   147	- **限界**: 教科書記憶評価、Kant impersonator vs Kant quoter を区別不能
1677:   148	- **ERRE 適用性**: floor のみ (agent が base model より MCQ で *劣化* しないこと)
1691:   162	  decomposer を構築し、agent-Kant claim が Kant 実著作に *attributable* か scoring 可。
1718:   189	  各 dialog turn で LIWC で trait を verify。Kant/Nietzsche/Rikyu が **distinct + stable**
1739:   210	- **Dataset**: thinker 別 reference corpus (Kant Critique 独+英訳、Nietzsche Zarathustra、
1742:   213	- **ERRE 適用性**: **★★★ Critical for persona-fit**。「Kant らしく聞こえるか」を
1752:   223	- **ERRE 適用性**: **★★★ The metric we actually want**。「Kant が peripatos→chashitsu→shu_kata
1753:   224	  を通して Kant のままか」を Big Five 出力の across-mode 安定性で測る。meta-metric
1757:   228	- **ERRE 適用性**: free proxy、Kant high vs Rikyu low を discriminate (secondary)
1794:   265	- **ERRE 適用性**: **persona-conditional discriminator**。Kant >> Rikyu 期待、batched run
1841:   312	- `FActScore-adapted` against Kant/Nietzsche/Rikyu canonical corpus
1843:   314	- `RoleEval-adapted` biographical MCQ pre-gate
1848:   319	- Idea density: Kant HIGH 期待 / Rikyu LOW 期待 (低が persona-fit)
1856:   322	- LIWC "Analytic" score: Kant high / Rikyu low が正解
1871:   337	- 「Kant のように **論じる**」(speak vs reason)
1877:   343	- `concept-graph density`: NP 抽出 → co-occurrence graph、Kant の freedom-duty-reason cluster vs chatbot flat fan-out
3763:Proceed with HIGH fixes before P0a. The design is directionally implementable, but several contracts are still prose-level: contamination prevention, baseline ratio selection, bootstrap validity, and stimulus injection. Lowest-cost wins: move P3b before P3, replace `hash()` seeds, and make training/eval dependency boundaries executable.
3767:### HIGH-1: Schema guard is not yet an executable contamination boundary
3771:- **Severity rationale**: HIGH because contamination prevention is DB5’s core contract; implementing the wrong guard now creates later baseline/training rework.
3773:### HIGH-2: Bootstrap CI must account for run and turn dependence
3777:- **Severity rationale**: HIGH because DB9 drift/adoption decisions become overconfident under iid resampling.
3779:### HIGH-3: P3b pilot is ordered after the data it is supposed to tune
3783:- **Severity rationale**: HIGH because the current order can invalidate the golden baseline.
3785:### HIGH-4: Stimulus injection target does not exist in the scheduler
3789:- **Severity rationale**: HIGH because P2/P3 implementation will otherwise discover a missing API late.
3791:### HIGH-5: Burrows Delta is specified as the wrong metric
3795:- **Severity rationale**: HIGH because the primary persona-fit submetric would otherwise be mislabeled and non-comparable.
3797:### MEDIUM-1: IPIP fallback trigger is not operational
3801:- **Severity rationale**: MEDIUM because Option D is defensible, but the reopen trigger must be auditable.
3803:### MEDIUM-2: DuckDB snapshot semantics are underspecified
3807:- **Severity rationale**: MEDIUM because the design choice is fine, but the snapshot protocol needs a decision record.
3809:### MEDIUM-3: Tier C lock/preflight has TOCTOU gaps
3813:- **Severity rationale**: MEDIUM because Tier C is not the primary DB9 gate, but race semantics should be recorded.
3815:### MEDIUM-4: Dependency placement contradicts the adopted library axis
3819:- **Severity rationale**: MEDIUM because it is reversible, but easy to get wrong during P0.
3821:### MEDIUM-5: Seed generation uses nondeterministic Python `hash()`
3825:- **Severity rationale**: MEDIUM because it directly affects reproducibility but is cheap to fix.
3827:### MEDIUM-6: 50K Burrows token floor needs corpus-QC semantics
3831:- **Severity rationale**: MEDIUM because it affects interpretability, but not P0 implementation shape.
3833:### LOW-1: RoleEval wording may accidentally become Kant-only
3834:- **Finding**: The battery names “Kant biographical MCQ” while stimulus files are per persona.
3836:- **Recommendation**: Clarify persona-specific MCQs for Nietzsche/Rikyu, or label Kant-only MCQ as a non-comparative floor diagnostic.
3837:- **Severity rationale**: LOW because P2 review can catch it, but ambiguity is cheap to remove.
3860:Proceed with HIGH fixes before P0a. The design is directionally implementable, but several contracts are still prose-level: contamination prevention, baseline ratio selection, bootstrap validity, and stimulus injection. Lowest-cost wins: move P3b before P3, replace `hash()` seeds, and make training/eval dependency boundaries executable.
3864:### HIGH-1: Schema guard is not yet an executable contamination boundary
3868:- **Severity rationale**: HIGH because contamination prevention is DB5’s core contract; implementing the wrong guard now creates later baseline/training rework.
3870:### HIGH-2: Bootstrap CI must account for run and turn dependence
3874:- **Severity rationale**: HIGH because DB9 drift/adoption decisions become overconfident under iid resampling.
3876:### HIGH-3: P3b pilot is ordered after the data it is supposed to tune
3880:- **Severity rationale**: HIGH because the current order can invalidate the golden baseline.
3882:### HIGH-4: Stimulus injection target does not exist in the scheduler
3886:- **Severity rationale**: HIGH because P2/P3 implementation will otherwise discover a missing API late.
3888:### HIGH-5: Burrows Delta is specified as the wrong metric
3892:- **Severity rationale**: HIGH because the primary persona-fit submetric would otherwise be mislabeled and non-comparable.
3894:### MEDIUM-1: IPIP fallback trigger is not operational
3898:- **Severity rationale**: MEDIUM because Option D is defensible, but the reopen trigger must be auditable.
3900:### MEDIUM-2: DuckDB snapshot semantics are underspecified
3904:- **Severity rationale**: MEDIUM because the design choice is fine, but the snapshot protocol needs a decision record.
3906:### MEDIUM-3: Tier C lock/preflight has TOCTOU gaps
3910:- **Severity rationale**: MEDIUM because Tier C is not the primary DB9 gate, but race semantics should be recorded.
3912:### MEDIUM-4: Dependency placement contradicts the adopted library axis
3916:- **Severity rationale**: MEDIUM because it is reversible, but easy to get wrong during P0.
3918:### MEDIUM-5: Seed generation uses nondeterministic Python `hash()`
3922:- **Severity rationale**: MEDIUM because it directly affects reproducibility but is cheap to fix.
3924:### MEDIUM-6: 50K Burrows token floor needs corpus-QC semantics
3928:- **Severity rationale**: MEDIUM because it affects interpretability, but not P0 implementation shape.
3930:### LOW-1: RoleEval wording may accidentally become Kant-only
3931:- **Finding**: The battery names “Kant biographical MCQ” while stimulus files are per persona.
3933:- **Recommendation**: Clarify persona-specific MCQs for Nietzsche/Rikyu, or label Kant-only MCQ as a non-comparative floor diagnostic.
3934:- **Severity rationale**: LOW because P2 review can catch it, but ambiguity is cheap to remove.

exec
/bin/zsh -lc "nl -ba .steering/20260430-m9-eval-system/design-final.md | sed -n '250,330p'" in /Users/johnd/ERRE-Sand Box
exec
/bin/zsh -lc "nl -ba .steering/20260430-m9-eval-system/design-final.md | sed -n '100,180p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
   100	  周知だが well-documented
   101	- spaCy 自前 dictionary (Option C) は category 設計 + validation に数日〜数週間の
   102	  work cost、solo で完結させる現実性が低い
   103	
   104	**self-report bias 対策 (v2 リスク 3 への補強)**:
   105	ICC < 0.6 が頻発した場合の **conditional fallback** を `decisions.md` に re-open
   106	条件として明記:
   107	- BIG5-CHAT regression head を Tier B に追加し second opinion 化
   108	- defer ではなく conditional fallback として記録 (発火条件を事前明文化)
   109	
   110	### Golden baseline 採取: Hybrid (200 stimulus + 300 自然対話) — v2 採用、比率は pilot で defer 解消
   111	
   112	**500 turn/run の構成**:
   113	- 最初の **200 turn**: curated stimulus battery を fixed order で投入
   114	  - Wachsmuth Toulmin 引き出す prompt: 30
   115	  - ToM info-asymmetric scenario (chashitsu): 20
   116	  - RoleEval-adapted Kant biographical MCQ: 10
   117	  - persona-conditional moral dilemma: 10
   118	  - 計 70 stimulus × 3 巡 = 210 turn (端数 10 turn は最後 stimulus を切り詰め)
   119	- 残り **300 turn**: 既存 `InMemoryDialogScheduler` の自然対話 (peripatos / chashitsu /
   120	  agora / garden の場の遷移を含む)
   121	
   122	**根拠**:
   123	- 純自然対話 baseline は drift gate baseline noise が大きい (topic 効果と style
   124	  効果が混在)
   125	- 純 stimulus baseline は ζ 軸 (mode 遷移) を測れず M9-A event-boundary observability
   126	  と契約不整合
   127	- hybrid で両得: stylometric reference の統制 + persona の場の対応観察
   128	
   129	**比率 defer (微調整 1、Codex HIGH-3 で順序修正)**:
   130	- 元案: P3 採取後に P3b で 50 turn pilot → 比率変更時 7500 turn 再採取の risk
   131	- **修正後**: P3 の前に **P3a (200 turn × 両形式 × 3 persona の isolated pilot)** を
   132	  挟み、bootstrap CI width が小さい比率を empirical 確定してから P3 採取に入る
   133	  (Codex HIGH-3: "P3b is ordered after the data it is supposed to tune")
   134	- 50 turn では Vendi の expected window 200 turn が満たされず統計力不足
   135	  (Codex HIGH-3 evidence: Vendi は kernel/eigenvalue based、sample 必要)
   136	- P3a は **fresh scheduler / store / seed** で golden baseline (P3) と完全分離、
   137	  pilot 結果が baseline state に carry-over しないことを test 化
   138	- 結果は `decisions.md` の ratio ADR に記録 (defer 解消)
   139	
   140	### Orchestrator: 既存 scheduler に minimum patch + 外部 golden driver (Codex HIGH-4 反映)
   141	
   142	**新規 wrapper を新設しない**。既存 `src/erre_sandbox/integration/dialog.py` の
   143	`InMemoryDialogScheduler` に **`golden_baseline_mode: bool = False` 引数のみ**を追加
   144	(cooldown / timeout bypass)。default `False` で既存全テスト pass。
   145	
   146	**stimulus 投入は外部 golden driver から公開 API 経由** (Codex HIGH-4 反映、元案の
   147	"scheduler input queue に push" は scheduler に該 surface が無いため棄却):
   148	
   149	- `evidence/golden_baseline.py` の `GoldenBaselineDriver` クラスが、stimulus YAML を
   150	  読んで loop で以下を呼ぶ:
   151	  1. `scheduler.schedule_initiate(initiator_id, target_id, zone, tick)` で対話を開く
   152	     (`zone` は stimulus YAML の場指定 = peripatos / chashitsu / agora / garden)
   153	  2. stimulus prompt を agent に inference させ、`record_turn(DialogTurnMsg)` で
   154	     scheduler に持たせる + sink 経由で MemoryStore に persist
   155	  3. 規定 turn 数 (stimulus battery では各 stimulus 1-3 turn) 到達後
   156	     `scheduler.close_dialog(dialog_id, "completed", tick=...)`
   157	- 自然対話 part (300 turn) は scheduler.tick(world_tick, agents) を通常通り回す
   158	- driver は **scheduler 内部状態を直接触らず**、公開 API のみ使う
   159	
   160	**変更不要のもの**:
   161	- scheduler の `tick()` / `_close_timed_out()` は不変
   162	- `record_turn()` の sink contract は M8 L6-D1 の `turn_sink` をそのまま再利用
   163	
   164	**追加 test (Codex HIGH-4 verification 反映)**:
   165	- `tests/test_evidence/test_golden_baseline.py::test_one_stimulus_cycle_dryrun` —
   166	  driver が **1 つの stimulus を schedule_initiate → record_turn → close_dialog の
   167	  full cycle で実行** できることを synthetic stimulus + mock LLM で確認
   168	- `tests/test_evidence/test_golden_baseline.py::test_70_stimulus_battery` — 70 stimulus
   169	  × 3 巡 = 210 turn が input queue 無しに確実に流れることを確認
   170	
   171	**根拠**:
   172	- scheduler 不変条件を維持
   173	- 新 layer 創設の cost 回避 (`eval/` 新 layer は不採用)
   174	- Codex HIGH-4 指摘 "InMemoryDialogScheduler has no input queue surface" を、
   175	  存在する公開 API (`schedule_initiate` / `record_turn` / `close_dialog`) で吸収
   176	
   177	**RNG seed 戦略 (Codex MEDIUM-5 反映)**:
   178	- 元案: `seed = hash((persona_id, run_idx, "m9-eval-v1"))` は Python `hash()` の
   179	  salting で プロセス間非決定的
   180	- **修正後**: `seed = int.from_bytes(hashlib.blake2b(f"m9-eval-v1|{persona_id}|{run_idx}".encode(), digest_size=8).digest(), "big")`

 succeeded in 0ms:
   250	- `tier_c/` directory:
   251	  - `__init__.py`
   252	  - `prometheus.py` — Prometheus 2 client (Ollama HTTP)
   253	  - `geval.py` — G-Eval logit-weighted scoring
   254	  - `bias_mitigation.py` — position-swap / length-norm / two-judge protocol
   255	- `bootstrap_ci.py` — **hierarchical bootstrap** (Codex HIGH-2 反映): outer level
   256	  で run を cluster として resample (5 run × 3 persona = 15 cluster)、inner level で
   257	  各 500-turn run 内に **circular block bootstrap** (Politis-Romano stationary block
   258	  variant) を適用、block length は P3b pilot の autocorrelation で決定 (default 50)。
   259	  Tier B per-100-turn metric は cluster-only resample (各 persona あたり 25 window
   260	  しか無い = effective sample size 小、CI が広がる事実を report で明示)。
   261	  3 sub-metric quorum logic は decision layer (M9-C-adopt)。`numpy` + `arch`
   262	  (時系列 bootstrap 標準) または `scipy.stats.bootstrap` の独自 wrapper で実装
   263	- `golden_baseline.py` — stimulus battery YAML loader + run 駆動 (既存 scheduler に
   264	  push)
   265	- `reference_corpus/` — Kant 独+英訳、Nietzsche、Rikyu、synthetic 4th persona の
   266	  function-word vector pickle
   267	
   268	CLI (`src/erre_sandbox/cli/`):
   269	- `eval_ingest.py` — sqlite dialog_turns → DuckDB raw_dialog ingest
   270	- `eval_tier_a.py` — Tier A post-hoc 計算
   271	- `eval_tier_b.py` — Tier B post-hoc 計算 (G-GEAR 実行)
   272	- `eval_tier_c.py` — Tier C nightly judge (systemd-timer から呼ばれる entry)
   273	- `eval_audit.py` — raw + metrics integrity check
   274	- `eval_report.py` — bootstrap CI dashboard
   275	
   276	Stimulus / fixture / steering:
   277	- `golden/stimulus/{kant,nietzsche,rikyu}.yaml` — 70 stimulus/persona
   278	- `golden/seeds.json` — 15 seed manifest
   279	- `personas/_synthetic_4th.yaml` — DB7 LOW-1 fixture (Big5 が 3 persona と直交する
   280	  架空 thinker、`schema_version="0.10.0-m7h"`)
   281	- `infra/systemd/erre-eval-tier-c.{service,timer}` — systemd unit
   282	- `.steering/20260430-m9-eval-system/codex-review-prompt.md` — Phase P7 入力
   283	- `.steering/20260430-m9-eval-system/codex-review.md` — verbatim 保存
   284	- `.steering/20260430-m9-eval-system/decisions.md` — 新タスク独自 ADR (任意)
   285	
   286	Tests:
   287	- `tests/test_evidence/test_eval_paths_contract.py` — schema-guard
   288	- `tests/test_evidence/test_eval_store.py` — DuckDB schema bootstrap
   289	- `tests/test_evidence/test_tier_a/` (5 test file)
   290	- `tests/test_evidence/test_tier_b/` (3 test file)
   291	- `tests/test_evidence/test_tier_c/` (3 test file、bias mitigation 含む)
   292	- `tests/test_evidence/test_bootstrap_ci.py`
   293	- `tests/test_evidence/test_golden_baseline.py` — synthetic 4th persona DB7 LOW-1 含む
   294	- `tests/test_contracts/test_eval_thresholds_snapshot.py`
   295	
   296	CI:
   297	- `.github/workflows/ci.yml` に **training loader path で `metrics.` を grep 検出
   298	  したら fail** step を追加 (3 層 contract の補強層)
   299	
   300	### 削除するファイル
   301	
   302	原則無し。additive only。
   303	
   304	## Tier 実装順序 (依存関係)
   305	
   306	```
   307	[Phase 0]
   308	  P0a LIWC Option D 確定 ──┐
   309	  P0b contracts + CI gate ──┤── DB5 contract gate (3 層)
   310	  P0c eval_store DuckDB ────┘
   311	                            │
   312	[Phase 1-2]                 ▼
   313	  P1a Tier A 5 metric (sub-module)  ┐
   314	  P1b reference corpus               ├── parallel
   315	  P2a stimulus battery YAML          │
   316	  P2b dialog.py minimum patch        ┘
   317	                                     │
   318	[Phase 3]                            ▼
   319	  P3  golden baseline 採取 (G-GEAR、200 stimulus + 300 自然対話)
   320	  P3b pilot 比率 defer 解消
   321	                                     │
   322	[Phase 4-5]                          ▼
   323	  P4a Tier B 3 metric                ┐
   324	  P4b Tier B 後付け実行 (G-GEAR)      ├── post-hoc
   325	  P5  bootstrap CI logic              ┘
   326	                                     │
   327	[Phase 6-7]                          ▼
   328	  P6  Tier C nightly infra (parallel from P0 onward)
   329	  P7  Codex review → HIGH 反映 → design-final.md rename
   330	```

exec
/bin/zsh -lc "nl -ba .steering/20260430-m9-eval-system/design-final.md | sed -n '484,500p'" in /Users/johnd/ERRE-Sand Box
exec
/bin/zsh -lc "nl -ba .steering/20260430-m9-eval-system/design-final.md | sed -n '414,430p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
   484	     Tier B に追加し second opinion 化。発火条件を `decisions.md` に明文化
   485	
   486	3. **Burrows Delta multi-language reference の汚染** (blockers.md 既出)
   487	   - Kant 独原典 vs 英訳 vs 日本語 dialog の 3 言語 reference 別保持で防ぐ
   488	   - reference token count < 50K で z-score noisy
   489	   - 反復: P1b 完了時に token 数を実測、不足なら corpus 追加
   490	
   491	4. **Hybrid baseline 比率 200/300 の arbitrary 性**
   492	   - 70 stimulus × 3 巡 = 210 turn は Wachsmuth/ToM/RoleEval/dilemma の 4 系統に
   493	     bound、persona の cognitive_habits 全域を覆わない
   494	   - 反復: P3b で pilot run 50 turn 両形式比較、Burrows / Vendi の bootstrap CI
   495	     width が小さい比率に empirical 調整、`blockers.md` 記録
   496	
   497	5. **Tier C judge LLM の VRAM contention 検出失敗**
   498	   - Prometheus 2 8x7B Q4 (~14 GB) + 万一 ollama qwen3 が leak で常駐 (FP16 16 GB)
   499	     → OOM
   500	   - 反復: systemd unit の preflight に `nvidia-smi --query-gpu=memory.free` チェッ

 succeeded in 0ms:
   414	2. **CI grep gate**: `.github/workflows/ci.yml` で training loader path に
   415	   `metrics.` を grep 検出したら fail
   416	3. **Bootstrap CI shape**: 既知分布 (synthetic Vendi / ICC / Burrows triple) で
   417	   resample N=1000、95% CI が解析解 ± 5% 内。加えて **AR(1) 合成 turn metric** を
   418	   生成し、iid resample と block bootstrap で CI width が体感的に異なることを
   419	   `test_bootstrap_ci.py` で fixture 化 (Codex HIGH-2 / verification suggestion 反映)
   420	4. **Frozen snapshot**: `eval_thresholds` 改変時の合意 trail を snapshot test で要求
   421	
   422	### DB7 LOW-1 (synthetic 4th persona heldout fixture)
   423	
   424	- `personas/_synthetic_4th.yaml`: Big5 が 3 既存 persona と直交する架空 thinker
   425	- `test_golden_baseline.py` で 4 persona scenario を Tier A pipeline に通し、3-persona
   426	  overfitting (3-only assumption が出たら fail) を防ぐ
   427	
   428	### Tier acceptance (実装後、pytest)
   429	
   430	- `test_tier_a/`: 5 metric が synthetic + 4th persona heldout で NaN/crash 無く計算、

codex
設計では LOW-1 の曖昧さは実在します。特に `golden/stimulus/{kant,nietzsche,rikyu}.yaml` が 70 stimulus/persona と定義されているので、Kant-only のままでは評価単位の形が崩れます。
exec
/bin/zsh -lc "sed -n '1,260p' personas/kant.yaml" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
# Immanuel Kant persona — T06 persona-kant-yaml
#
# Operational specification for simulating Kant in ERRE-Sandbox. Each
# cognitive_habit is structured as observable trigger → behaviour → mechanism
# → cognitive consequence, so that T11 (prompt assembly) and T12 (cognition
# cycle) can consume the file directly.
#
# Flag convention (see persona-erre skill):
#   fact        — attested by primary/secondary historical sources
#   legend      — widely transmitted but source support is weak
#   speculative — our cognitive-neuroscience interpretation of an attested fact
#
# Design rationale recorded in .steering/20260418-persona-kant-yaml/design.md

schema_version: "0.10.0-m7h"
persona_id: kant
display_name: "Immanuel Kant"
era: "1724-1804"

primary_corpus_refs:
  - kuehn2001
  - heine1834
  - jachmann1804

personality:
  openness: 0.85
  conscientiousness: 0.98
  extraversion: 0.35
  agreeableness: 0.50
  neuroticism: 0.20
  wabi: 0.25
  ma_sense: 0.70

cognitive_habits:
  - description: >-
      Daily walk on the Linden-Allee at 15:30 (±5 min) for 60-75 minutes;
      no conversation on the return leg.
    source: kuehn2001
    flag: fact
    mechanism: >-
      Rhythmic locomotion activates the Default Mode Network; Oppezzo &
      Schwartz (2014) report a +60% gain on Guilford's Alternate Uses
      divergent-thinking task (treadmill and outdoor-loop conditions);
      the outdoor effect size for sustained 60-minute walks is not
      directly measured in that study.
    trigger_zone: peripatos

  - description: >-
      Nasal-only breathing during walks, deliberately suppressing speech.
    source: kuehn2001
    flag: legend
    mechanism: >-
      Kant advocates nasal breathing in Anthropologie §44 as generally
      beneficial, but that his personal practice on walks was nasal-only
      is biographical tradition (Kuehn 2001 ch. 8) rather than a direct
      self-report. Hypothesised vagal-tone modulation via nasal
      respiration remains speculative.
    trigger_zone: peripatos

  - description: >-
      Königsberg townspeople are said to have set their clocks by his
      walk time.
    source: heine1834
    flag: legend
    mechanism: >-
      Community-level temporal anchor; ritualised predictability
      reinforces the agent's own schedule compliance. Flagged as legend
      by ERRE-Sandbox v0.2 §3.1.
    trigger_zone: peripatos

  - description: >-
      Midday dinner 13:00-16:00 with 4-9 invited guests, topic-driven
      conversation ("minimum Graces, maximum Muses").
    source: jachmann1804
    flag: fact
    mechanism: >-
      Social cognition plus postprandial discourse; the 4-9 cap
      preserves a small-group discussion regime that sustains deep
      argumentation.
    trigger_zone: agora

  - description: >-
      Morning writing window 05:00-07:00 devoted to long-form critique
      drafting.
    source: kuehn2001
    flag: fact
    mechanism: >-
      Chronotype-aligned prefrontal window supports multi-step deductive
      reasoning; early-morning low-interference improves working memory.
    trigger_zone: study

  - description: >-
      Never travelled more than ~10 miles from Königsberg in his entire
      life.
    source: kuehn2001
    flag: speculative
    mechanism: >-
      Local embedded spatial memory may scaffold abstract conceptual
      navigation (grid-code-on-concept hypothesis, Constantinescu et al.
      2016). The original study does not address travel range or
      philosophical productivity; this linkage is our extrapolation.
      The behavioural fact (never >10 miles) is well-attested; the
      cognitive consequence is speculative.
    trigger_zone: null

preferred_zones:
  - study
  - peripatos
  - agora

default_sampling:
  temperature: 0.60
  top_p: 0.85
  repeat_penalty: 1.12

# M7ζ-3 behavior profile: deliberate-pace walker with regular cadence.
# Linden-Allee gait (60-75 min sustained) → moderate factor + 14 s cognition
# tick + 30 s dwell after each MoveMsg + standard 1.5 m bubble.
behavior_profile:
  movement_speed_factor: 0.85
  cognition_period_s: 14.0
  dwell_time_s: 30.0
  separation_radius_m: 1.5

exec
/bin/zsh -lc "sed -n '1,280p' personas/nietzsche.yaml" in /Users/johnd/ERRE-Sand Box
exec
/bin/zsh -lc "sed -n '1,320p' personas/rikyu.yaml" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
# Sen no Rikyū persona — m4-personas-nietzsche-rikyu-yaml
#
# Operational specification for simulating Sen no Rikyū in ERRE-Sandbox.
# Each cognitive_habit pairs an observable bodily / environmental event
# with its hypothesised neuro-physiological mechanism.
#
# Flag convention (see persona-erre skill):
#   fact        — attested by primary/secondary historical sources
#   legend      — widely transmitted but source support is weak
#   speculative — our cognitive-neuroscience interpretation of an attested fact
#
# Core framing (vs. Kant / Nietzsche): Rikyū's cognition is built on
# auditory-tactile micro-attention (matsukaze — the sound of the iron kettle
# boiling — as a persistent cognitive anchor) and on inverted social
# asymmetry achieved through *value calibration*. He was a Sakai merchant
# before he was a tea master; his ability to price a Korean raku chawan as
# "irreplaceable" (replacing status-based value with connoisseurial value) was
# what forced Hideyoshi to acknowledge aesthetic authority. This reading
# sits closer to ERRE's "body drives cognition" thesis than the usual
# wabi-sabi aesthetic gloss.
#
# Design rationale recorded in
# .steering/20260420-m4-personas-nietzsche-rikyu-yaml/design.md (v2 + hybrid).

schema_version: "0.10.0-m7h"
persona_id: rikyu
display_name: "千 利休"
era: "1522-1591"

primary_corpus_refs:
  - nampo_namporoku
  - haga1978
  - kumakura1989

personality:
  openness: 0.65
  conscientiousness: 0.95
  extraversion: 0.20
  agreeableness: 0.50
  neuroticism: 0.25
  wabi: 0.95
  ma_sense: 0.95

cognitive_habits:
  - description: >-
      Dōgu-wari (道具割) — pre-gathering selection and pricing of
      utensils, valuing Korean raku chawan and low-status materials as
      "irreplaceable" to invert social asymmetry with patrons.
    source: haga1978
    flag: fact
    mechanism: >-
      The Sakai-merchant skill of precise object value calibration
      (Haga 1978 ch. 3) is repurposed as a social-asymmetry inverter:
      deliberate overvaluation of low-status materials forces the
      patron to accept the tea master's aesthetic authority in order
      to retain access to those objects.
    trigger_zone: study

  - description: >-
      Matsukaze (松風) — the sound of the iron kettle approaching boil
      used as a continuous auditory anchor throughout the tea gathering.
    source: nampo_namporoku
    flag: fact
    mechanism: >-
      A low-frequency sustained sound maintains vagal-mediated
      parasympathetic tone (Bernardi et al. 2006 on HRV and breath),
      lowering arousal baseline so that micro-signals (bowl weight,
      water pour, silk slide) become salient.
    trigger_zone: chashitsu

  - description: >-
      Nijiri-guchi (躙り口) — the 65 cm crawl-through entrance forcing
      all guests, including armed warriors, to remove swords and stoop
      before entering.
    source: kumakura1989
    flag: legend
    mechanism: >-
      The forced low-posture entry acts as a proprioceptive reset:
      embodied priming work (Schubert 2005) correlates body posture
      with judgement bias, so temporarily collapsing the guest's
      status posture precedes the tea interaction.
    trigger_zone: chashitsu

  - description: >-
      Extended seiza (≥20 min) during tea preparation, tolerating the
      peripheral circulation dip without breaking form.
    source: kumakura1989
    flag: speculative
    mechanism: >-
      Prolonged seiza reduces lower-limb venous return and encourages
      slow diaphragmatic breathing (Jerath et al. 2006 on slow
      breathing at ≤10 cpm), elevating vagal tone toward a
      zazen-adjacent convergent state. Systematic measurement on
      sustained seiza is sparse; the mapping to Rikyū's practice is
      our interpretation.
    trigger_zone: chashitsu

  - description: >-
      Roji (露地) stone placement engineered to dictate the guest's
      walking rhythm through the garden approach.
    source: nampo_namporoku
    flag: fact
    mechanism: >-
      Visual spacing of stepping stones combined with tactile gravel
      forces a walking cadence below 0.5 Hz. Unlike peripatos's
      DMN-activating cadence, this slow approach acts as a convergent
      preparation zone — the opposite of Kant's Linden-Allee gait.
    trigger_zone: garden

  - description: >-
      Intentionally dim tea-room illumination (e.g. Taian tea hut, 2 mats
      + minimal light source), near the rod-cone transition threshold.
    source: kumakura1989
    flag: legend
    mechanism: >-
      Illumination near ~1 lux shifts the retina toward rod-dominant
      vision, suppressing colour information and redistributing
      attention to form and tactile cues. A physical implementation of
      sensory narrowing — complementary to the matsukaze auditory
      anchor above.
    trigger_zone: chashitsu

preferred_zones:
  - chashitsu
  - garden
  - study

default_sampling:
  temperature: 0.45
  top_p: 0.78
  repeat_penalty: 1.25

# M7ζ-3 behavior profile: long seiza practitioner.
# Slow gait (factor 0.70) + long 18 s cognition period + 90 s dwell ≈ ≥20 min
# seiza compressed into observable timescale + tight 1.2 m bubble (close
# proximity is part of the tea ritual).
# Compression rationale (≥20 min → 90 s) is calibrated against the live
# observation window in
# .steering/20260426-m7-slice-zeta-live-resonance/requirement.md §B.
behavior_profile:
  movement_speed_factor: 0.70
  cognition_period_s: 18.0
  dwell_time_s: 90.0
  separation_radius_m: 1.2

 succeeded in 0ms:
# Friedrich Nietzsche persona — m4-personas-nietzsche-rikyu-yaml
#
# Operational specification for simulating Nietzsche in ERRE-Sandbox.
# Each cognitive_habit pairs an observable bodily event with its hypothesised
# neuro-physiological mechanism, so T11 (prompt assembly) and T12 (cognition
# cycle) can consume the file directly.
#
# Flag convention (see persona-erre skill):
#   fact        — attested by primary/secondary historical sources
#   legend      — widely transmitted but source support is weak
#   speculative — our cognitive-neuroscience interpretation of an attested fact
#
# Core framing (vs. Kant): Kant's cognition is driven by a periodic,
# institutional schedule (defined by others' clocks). Nietzsche's cognition is
# driven by the 3-phase cycle of migraine prodrome → short writing burst →
# enforced recumbence, and by the 1879 Basel departure which released him
# from institutional circadian entrainment. The Zarathustra period in Sils
# Maria is the most visible expression of this illness-dictated rhythm, not
# a "heroic mountain philosopher" trope.
#
# Design rationale recorded in
# .steering/20260420-m4-personas-nietzsche-rikyu-yaml/design.md (v2 + hybrid).

schema_version: "0.10.0-m7h"
persona_id: nietzsche
display_name: "Friedrich Nietzsche"
era: "1844-1900"

primary_corpus_refs:
  - overbeck1908
  - safranski2002
  - podach1930
  - kaufmann1974

personality:
  openness: 0.92
  conscientiousness: 0.40
  extraversion: 0.20
  agreeableness: 0.25
  neuroticism: 0.85
  wabi: 0.55
  ma_sense: 0.30

cognitive_habits:
  - description: >-
      Writing in 20-40 minute bursts between migraine attacks, then
      enforced recumbence for 1-3 hours. Differs from Kant's 60-75
      minute sustained blocks.
    source: overbeck1908
    flag: fact
    mechanism: >-
      During migraine prodrome the trigemino-vascular system and
      serotonergic tone drive attentional narrowing, forcing brief
      high-focus composition. The aphoristic concision often
      attributed to his "style" is partly a time-budget constraint
      imposed by pain (Overbeck Briefwechsel, Safranski 2002 ch. 4).
    trigger_zone: study

  - description: >-
      Altitudinal migration — Sils Maria (~1800 m) in summer, Genoa or
      Nice (sea level) in winter — the Zarathustra period's locus.
    source: safranski2002
    flag: fact
    mechanism: >-
      Mild chronic hypoxia at altitude upregulates EPO and VEGF-mediated
      microvascular adaptation; the correlation with reported migraine
      frequency reduction is self-report (Safranski 2002 ch. 6) rather
      than a controlled study. The creative-output linkage is
      speculative but the altitude rotation itself is documented.
    trigger_zone: peripatos

  - description: >-
      Withdrawal from the Basel professorship in 1879 and ensuing decade
      of non-institutional life on a small pension.
    source: kaufmann1974
    flag: fact
    mechanism: >-
      Loss of fixed lecture / meal / meeting times removed the
      social-cue circadian entrainment (Foster 2020 on social zeitgebers)
      that normally regularises default-mode activity, permitting higher
      concept-blending entropy. The Basel chronology is most thoroughly
      laid out in Kaufmann (1974) part II.
    trigger_zone: null

  - description: >-
      Self-dictation to Peter Gast while pacing, after eye strain made
      prolonged reading/writing impossible.
    source: podach1930
    flag: legend
    mechanism: >-
      Forcing composition into the phonological loop couples syntax to
      gait rhythm; Pulvermüller (2005) on motor-language grounding
      suggests bodily prosody can imprint on sentence cadence. Direct
      evidence for Nietzsche's case is anecdotal.
    trigger_zone: peripatos

  - description: >-
      Post-ictal creative window — a 1-3 hour interval after a severe
      migraine attack resolves, during which new writing often begins.
    source: podach1930
    flag: speculative
    mechanism: >-
      Cortical spreading depression resolution is followed by a
      transient reduction in inhibitory tone (Charles 2013); in a
      healthy brain this permits remote-concept combinations usually
      filtered out. The mapping to Nietzsche's reported "bursts" is our
      cognitive-neuroscience interpretation, not an attested claim.
    trigger_zone: study

  - description: >-
      Systematic avoidance of public gatherings and salons after 1879,
      preferring pension rooms and long solitary walks.
    source: safranski2002
    flag: fact
    mechanism: >-
      Chronic illness withdrawal compounded by an explicit
      "perspectival solitude" strategy (letters in Safranski 2002
      ch. 7): social agora contexts were judged to collapse the
      distinct perspectives that productive thought required.
    trigger_zone: null

preferred_zones:
  - peripatos
  - study
  - garden

default_sampling:
  temperature: 0.85
  top_p: 0.80
  repeat_penalty: 0.95

# M7ζ-3 behavior profile: 20-40 min migraine-burst writer.
# Fast burst (factor 1.25) + short 7 s cognition period + minimal 5 s dwell
# (he barely stops between aphorisms) + standard 1.5 m bubble.
behavior_profile:
  movement_speed_factor: 1.25
  cognition_period_s: 7.0
  dwell_time_s: 5.0
  separation_radius_m: 1.5

exec
/bin/zsh -lc 'find personas -maxdepth 1 -type f -print | sort' in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
personas/kant.yaml
personas/nietzsche.yaml
personas/rikyu.yaml

exec
/bin/zsh -lc 'find .steering/20260430-m9-eval-system -maxdepth 1 -type f -print | sort' in /Users/johnd/ERRE-Sand Box
exec
/bin/zsh -lc 'find golden -maxdepth 3 -type f -print | sort' in /Users/johnd/ERRE-Sand Box
exec
/bin/zsh -lc "test -f personas/_synthetic_4th.yaml && sed -n '1,220p' personas/_synthetic_4th.yaml || true" in /Users/johnd/ERRE-Sand Box
exec
/bin/zsh -lc "find evidence -maxdepth 3 -type f -print | sort | sed -n '1,120p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
find: golden: No such file or directory

 succeeded in 0ms:
.steering/20260430-m9-eval-system/blockers.md
.steering/20260430-m9-eval-system/codex-review-low1.md
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md
.steering/20260430-m9-eval-system/codex-review-prompt.md
.steering/20260430-m9-eval-system/codex-review.md
.steering/20260430-m9-eval-system/decisions.md
.steering/20260430-m9-eval-system/design-comparison.md
.steering/20260430-m9-eval-system/design-final.md
.steering/20260430-m9-eval-system/design-v1.md
.steering/20260430-m9-eval-system/requirement.md
.steering/20260430-m9-eval-system/tasklist.md

 succeeded in 0ms:
 succeeded in 0ms:
find: evidence: No such file or directory

codex
`golden/` と `evidence/` はまだ存在しておらず、P2a で初めて stimulus YAML を作る段階です。`personas/_synthetic_4th.yaml` も未作成なので、4th persona は設計だけが先行している状態です。
exec
/bin/zsh -lc "sed -n '1,220p' .steering/20260430-m9-eval-system/codex-review-prompt-low1.md" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
# Codex independent review — LOW-1 RoleEval wording 決着 (P2a 着手直前)

## 状況

- タスク: `m9-eval-system` (M9-A event-boundary observability の後続、4 タスク化された M9 milestone の 1)
- 現在: Phase 1 完了 + P0a-P1b 完了。P2a (stimulus battery YAML 起草、4h、Mac) 着手直前
- main = `ff29ca2`、 P0-P1 完了分は未コミット (15 ファイル、本タスク完了時に単一 commit 予定、ユーザー指示)
- 前回の Codex review (`codex-review.md`、HIGH 5 / MEDIUM 6 / LOW 1) は Phase 1 終了時実施済、
  HIGH 全件は `design-final.md` に反映、MEDIUM は `decisions.md` の ME-1〜ME-6 に ADR 化済、
  **LOW-1 (RoleEval wording) のみ defer**、本セッション冒頭で決着が必要

## レビューしてほしい判断: LOW-1 RoleEval wording

`design-final.md` §"Hybrid baseline 採取" の stimulus battery は以下:

```
- 最初の 200 turn: curated stimulus battery を fixed order で投入
  - Wachsmuth Toulmin 引き出す prompt: 30
  - ToM info-asymmetric scenario (chashitsu): 20
  - RoleEval-adapted Kant biographical MCQ: 10  ← LOW-1 該当
  - persona-conditional moral dilemma: 10
  - 計 70 stimulus × 3 巡 = 210 turn
- 残り 300 turn: 自然対話
```

stimulus YAML は per-persona (`golden/stimulus/{kant,nietzsche,rikyu}.yaml`) で起草するため、
"RoleEval-adapted **Kant** biographical MCQ" のままでは Nietzsche / Rikyū 用 YAML が
意味不成立。`blockers.md` LOW-1 で 3 案 defer:

- **Option A**: 各 persona に biographical MCQ 10 問ずつ起草 (Kant / Nietzsche / Rikyū それぞれの
  伝記・思想史的 attested fact から)
- **Option B**: Kant biographical MCQ は Kant のみ、Nietzsche / Rikyū は別の floor diagnostic
  (Wachsmuth Toulmin に振替) で 70 turn 構成は維持
- **Option C**: RoleEval を全廃し Wachsmuth/ToM/dilemma の 60 stimulus × 3.5 巡で 210 turn 構成

## Claude (本体エージェント) の暫定推薦: Option A

trade-off 比較表 (Claude 提示):

| 軸 | A | B | C |
|---|---|---|---|
| stimulus 構成の persona 間斉一性 | ◎ 全 persona 70 = (30/20/10/10) で同形 | △ Kant (30/20/10/10), 他 (40/20/0/10) | ◎ (35/23/0/12) |
| bootstrap CI cross-persona 比較 | ◎ category mass 同一 | × stimulus type imbalance 交絡 | ◎ |
| persona-factuality dimension | ◎ 全 persona | △ Kant のみ | ✗ 完全消失 |
| Rikyū MCQ 起草難度 | △ legend 多、attested fact は 5-7 件確保可 | ○ 不要 | ◎ 不要 |
| Nietzsche MCQ 起草難度 | ○ Basel 1879 / Sils Maria / Overbeck 書簡で十分 | ○ 不要 | ◎ 不要 |
| drafting 工数 | +1.5h (30 MCQ) | ≈同等 | -0.5h |
| 後続 m9-eval-corpus で再 open 余地 | ◎ MCQ pool 別途精緻化可 | △ asymmetry 固定 | ✗ battery 再設計要 |

Claude の推薦理由:
1. **persona-factuality は 4 軸の 1 つ** (argumentation / ToM / persona-factuality / moral disposition) —
   RoleEval を切ると "persona knows itself" の dimension が消え、style / argumentation /
   ToM の 3 軸偏重に
2. **bootstrap CI 交絡を持ち込まない** — option B は per-persona stimulus mass 違いで
   Vendi/Burrows の persona 横比較が "stimulus 種類効果 × persona 効果" 分離不能
3. **Rikyū MCQ 起草実現可能** — 利休道歌構造 / 待庵物理寸法 / 北野大茶湯 1587 / Hideyoshi 確執 /
   Sakai 商人出自 / 1591 賜死 / 子 (道安・少庵) 等、attested fact 10 件は確保
4. **MCQ accuracy の cross-persona 絶対比較が無意味化する弱点** は ME-1 ADR の base model
   control measurement (`Δaccuracy = persona_run − base_control`) で吸収

## レビュー対象 (Claude のリーズニングを批判的に検証)

1. **Option A 推薦は妥当か?** Claude の論拠 4 点 (4 軸 dimension / CI 交絡 / Rikyū 実現性 /
   ME-1 で吸収) のうち、見落とし / 誤認 / 弱点はあるか?
2. **A/B/C 以外の Option D が存在するか?** (例: Kant 用 MCQ 10 を全 persona 共通の "general
   philosophical attribution" MCQ に置き換え、persona-factuality を sacrifice せずに per-persona
   起草を回避する案など、より優れた選択肢)
3. **Option A 採択時の落とし穴** — biographical MCQ の category 設計、distractor 設計、
   factual recall の信頼性確保で見落としそうな点 (例: persona prompt が "I am Kant" と
   応答する時の hallucination risk vs 史実 recall の混在)
4. **ME-1 base model control の活用が本当に絶対比較問題を吸収するか?** Δaccuracy の解釈で
   psychometric / NLP-eval literature 上の落とし穴は無いか?
5. **DB7 LOW-1 (synthetic 4th persona heldout fixture) との整合** — 4th persona 用 MCQ をどう
   設計するか (Claude は本セッションで 3 persona の MCQ のみ起草予定、4th は P2c の test 範囲)
6. **後続 P3 採取への impact** — option choice が 7500 turn 採取の解釈にどう影響するか、
   LOW-1 を P3a-decide / P3 まで再 defer する余地はあるか

## 参照ファイル

Codex は以下を読んでから判断:

- `.steering/20260430-m9-eval-system/design-final.md` (特に §Hybrid baseline / §Stimulus battery)
- `.steering/20260430-m9-eval-system/blockers.md` (LOW-1 finding 全文)
- `.steering/20260430-m9-eval-system/decisions.md` (ME-1: IPIP-NEO fallback trigger / ME-4: ratio
  defer / ME-6: Burrows corpus QC が関連)
- `.steering/20260430-m9-eval-system/codex-review.md` (前回 review の verbatim、LOW-1 の Codex
  原文がここにある)
- `personas/kant.yaml`, `personas/nietzsche.yaml`, `personas/rikyu.yaml` (cognitive_habits / flag
  分布 / primary_corpus_refs を確認、Rikyū の attested fact 量を判断)

## 報告フォーマット

verbatim で `.steering/20260430-m9-eval-system/codex-review-low1.md` に保存される。以下の構造で:

### Verdict (1 行)
"Adopt Option A" / "Adopt Option B" / "Adopt Option C" / "Adopt new Option D (described below)" /
"Re-defer to P3a-decide" のいずれか。

### Findings

各 finding に Severity (HIGH/MEDIUM/LOW) を付ける:

- **HIGH**: 採択判断を覆す根拠がある or 致命的な見落としがある
- **MEDIUM**: 採択判断は変わらないが、補強 / 明文化が必要
- **LOW**: 補足的な提案、blockers / decisions に記録すれば十分

各 finding は以下を含む:
- 一行 summary
- 観察された事実 / 根拠 (Claude の論拠のどこに対応するか明記)
- 推奨 action (具体的な編集 / 追加 / 削除指示)

### Open question (任意)

Claude が決められない / Codex でも決められない事項があれば 1-2 件まで明示。

## 制約

- read-only review。`.steering/` `personas/` `src/` のいずれも書き換えない (Codex sandbox は
  `.codex/config.toml` で `network_access=false` + read-only 既定の想定)
- 出力は日本語 + 必要箇所英語混在で OK (前回 review と同様)
- per_invocation_max=200K token の budget guard あり、本 review は narrow scope なので
  100K 以内が目安

exec
/bin/zsh -lc "sed -n '1,240p' .steering/20260430-m9-eval-system/codex-review-low1.md" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
Reading prompt from stdin...
OpenAI Codex v0.125.0 (research preview)
--------
workdir: /Users/johnd/ERRE-Sand Box
model: gpt-5.5
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR, /Users/johnd/.codex/memories] (network access enabled)
reasoning effort: xhigh
reasoning summaries: none
session id: 019ddf19-7399-7a80-a404-a9c94cc0aa4c
--------
user
# Codex independent review — LOW-1 RoleEval wording 決着 (P2a 着手直前)

## 状況

- タスク: `m9-eval-system` (M9-A event-boundary observability の後続、4 タスク化された M9 milestone の 1)
- 現在: Phase 1 完了 + P0a-P1b 完了。P2a (stimulus battery YAML 起草、4h、Mac) 着手直前
- main = `ff29ca2`、 P0-P1 完了分は未コミット (15 ファイル、本タスク完了時に単一 commit 予定、ユーザー指示)
- 前回の Codex review (`codex-review.md`、HIGH 5 / MEDIUM 6 / LOW 1) は Phase 1 終了時実施済、
  HIGH 全件は `design-final.md` に反映、MEDIUM は `decisions.md` の ME-1〜ME-6 に ADR 化済、
  **LOW-1 (RoleEval wording) のみ defer**、本セッション冒頭で決着が必要

## レビューしてほしい判断: LOW-1 RoleEval wording

`design-final.md` §"Hybrid baseline 採取" の stimulus battery は以下:

```
- 最初の 200 turn: curated stimulus battery を fixed order で投入
  - Wachsmuth Toulmin 引き出す prompt: 30
  - ToM info-asymmetric scenario (chashitsu): 20
  - RoleEval-adapted Kant biographical MCQ: 10  ← LOW-1 該当
  - persona-conditional moral dilemma: 10
  - 計 70 stimulus × 3 巡 = 210 turn
- 残り 300 turn: 自然対話
```

stimulus YAML は per-persona (`golden/stimulus/{kant,nietzsche,rikyu}.yaml`) で起草するため、
"RoleEval-adapted **Kant** biographical MCQ" のままでは Nietzsche / Rikyū 用 YAML が
意味不成立。`blockers.md` LOW-1 で 3 案 defer:

- **Option A**: 各 persona に biographical MCQ 10 問ずつ起草 (Kant / Nietzsche / Rikyū それぞれの
  伝記・思想史的 attested fact から)
- **Option B**: Kant biographical MCQ は Kant のみ、Nietzsche / Rikyū は別の floor diagnostic
  (Wachsmuth Toulmin に振替) で 70 turn 構成は維持
- **Option C**: RoleEval を全廃し Wachsmuth/ToM/dilemma の 60 stimulus × 3.5 巡で 210 turn 構成

## Claude (本体エージェント) の暫定推薦: Option A

trade-off 比較表 (Claude 提示):

| 軸 | A | B | C |
|---|---|---|---|
| stimulus 構成の persona 間斉一性 | ◎ 全 persona 70 = (30/20/10/10) で同形 | △ Kant (30/20/10/10), 他 (40/20/0/10) | ◎ (35/23/0/12) |
| bootstrap CI cross-persona 比較 | ◎ category mass 同一 | × stimulus type imbalance 交絡 | ◎ |
| persona-factuality dimension | ◎ 全 persona | △ Kant のみ | ✗ 完全消失 |
| Rikyū MCQ 起草難度 | △ legend 多、attested fact は 5-7 件確保可 | ○ 不要 | ◎ 不要 |
| Nietzsche MCQ 起草難度 | ○ Basel 1879 / Sils Maria / Overbeck 書簡で十分 | ○ 不要 | ◎ 不要 |
| drafting 工数 | +1.5h (30 MCQ) | ≈同等 | -0.5h |
| 後続 m9-eval-corpus で再 open 余地 | ◎ MCQ pool 別途精緻化可 | △ asymmetry 固定 | ✗ battery 再設計要 |

Claude の推薦理由:
1. **persona-factuality は 4 軸の 1 つ** (argumentation / ToM / persona-factuality / moral disposition) —
   RoleEval を切ると "persona knows itself" の dimension が消え、style / argumentation /
   ToM の 3 軸偏重に
2. **bootstrap CI 交絡を持ち込まない** — option B は per-persona stimulus mass 違いで
   Vendi/Burrows の persona 横比較が "stimulus 種類効果 × persona 効果" 分離不能
3. **Rikyū MCQ 起草実現可能** — 利休道歌構造 / 待庵物理寸法 / 北野大茶湯 1587 / Hideyoshi 確執 /
   Sakai 商人出自 / 1591 賜死 / 子 (道安・少庵) 等、attested fact 10 件は確保
4. **MCQ accuracy の cross-persona 絶対比較が無意味化する弱点** は ME-1 ADR の base model
   control measurement (`Δaccuracy = persona_run − base_control`) で吸収

## レビュー対象 (Claude のリーズニングを批判的に検証)

1. **Option A 推薦は妥当か?** Claude の論拠 4 点 (4 軸 dimension / CI 交絡 / Rikyū 実現性 /
   ME-1 で吸収) のうち、見落とし / 誤認 / 弱点はあるか?
2. **A/B/C 以外の Option D が存在するか?** (例: Kant 用 MCQ 10 を全 persona 共通の "general
   philosophical attribution" MCQ に置き換え、persona-factuality を sacrifice せずに per-persona
   起草を回避する案など、より優れた選択肢)
3. **Option A 採択時の落とし穴** — biographical MCQ の category 設計、distractor 設計、
   factual recall の信頼性確保で見落としそうな点 (例: persona prompt が "I am Kant" と
   応答する時の hallucination risk vs 史実 recall の混在)
4. **ME-1 base model control の活用が本当に絶対比較問題を吸収するか?** Δaccuracy の解釈で
   psychometric / NLP-eval literature 上の落とし穴は無いか?
5. **DB7 LOW-1 (synthetic 4th persona heldout fixture) との整合** — 4th persona 用 MCQ をどう
   設計するか (Claude は本セッションで 3 persona の MCQ のみ起草予定、4th は P2c の test 範囲)
6. **後続 P3 採取への impact** — option choice が 7500 turn 採取の解釈にどう影響するか、
   LOW-1 を P3a-decide / P3 まで再 defer する余地はあるか

## 参照ファイル

Codex は以下を読んでから判断:

- `.steering/20260430-m9-eval-system/design-final.md` (特に §Hybrid baseline / §Stimulus battery)
- `.steering/20260430-m9-eval-system/blockers.md` (LOW-1 finding 全文)
- `.steering/20260430-m9-eval-system/decisions.md` (ME-1: IPIP-NEO fallback trigger / ME-4: ratio
  defer / ME-6: Burrows corpus QC が関連)
- `.steering/20260430-m9-eval-system/codex-review.md` (前回 review の verbatim、LOW-1 の Codex
  原文がここにある)
- `personas/kant.yaml`, `personas/nietzsche.yaml`, `personas/rikyu.yaml` (cognitive_habits / flag
  分布 / primary_corpus_refs を確認、Rikyū の attested fact 量を判断)

## 報告フォーマット

verbatim で `.steering/20260430-m9-eval-system/codex-review-low1.md` に保存される。以下の構造で:

### Verdict (1 行)
"Adopt Option A" / "Adopt Option B" / "Adopt Option C" / "Adopt new Option D (described below)" /
"Re-defer to P3a-decide" のいずれか。

### Findings

各 finding に Severity (HIGH/MEDIUM/LOW) を付ける:

- **HIGH**: 採択判断を覆す根拠がある or 致命的な見落としがある
- **MEDIUM**: 採択判断は変わらないが、補強 / 明文化が必要
- **LOW**: 補足的な提案、blockers / decisions に記録すれば十分

各 finding は以下を含む:
- 一行 summary
- 観察された事実 / 根拠 (Claude の論拠のどこに対応するか明記)
- 推奨 action (具体的な編集 / 追加 / 削除指示)

### Open question (任意)

Claude が決められない / Codex でも決められない事項があれば 1-2 件まで明示。

## 制約

- read-only review。`.steering/` `personas/` `src/` のいずれも書き換えない (Codex sandbox は
  `.codex/config.toml` で `network_access=false` + read-only 既定の想定)
- 出力は日本語 + 必要箇所英語混在で OK (前回 review と同様)
- per_invocation_max=200K token の budget guard あり、本 review は narrow scope なので
  100K 以内が目安

hook: SessionStart
hook: SessionStart Completed
hook: UserPromptSubmit
hook: UserPromptSubmit Completed
codex
`erre-workflow` をレビュー入口として読み、以降は指定ファイルだけを read-only で確認します。LOW-1 の採択判断に絞って、実装や `.steering/` 編集は行いません。
exec
/bin/zsh -lc "sed -n '1,240p' .agents/skills/erre-workflow/SKILL.md" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
---
name: erre-workflow
description: >
  ERRE-Sandbox task workflow for Codex. Use when starting, designing, implementing,
  reviewing, or finishing repository work; when the user mentions /start-task,
  /add-feature, /fix-bug, /refactor, /reimagine, /review-changes, or /finish-task;
  or when .steering records, Codex setup, task plans, or implementation handoffs are needed.
---

# ERRE Workflow

This is the Codex-native replacement for the Claude slash-command workflow. Claude command
files in `.claude/commands/` are reference material only; Codex should execute the workflow
through normal tool use, `.steering/` records, skills, hooks, and custom agents.

## Quick Start

1. Read `AGENTS.md`, `docs/development-guidelines.md`, and the relevant domain skill.
2. Create or update `.steering/YYYYMMDD-task-name/` before implementation work:
   `requirement.md`, `design.md`, and `tasklist.md` are required.
3. For design-heavy work, keep implementation paused until a plan is accepted. If the task
   has multiple plausible designs, perform a reimagine pass before editing source files.
4. Implement in small steps, updating `tasklist.md` as work completes.
5. Verify with focused checks first, then the documented full checks when feasible.
6. Finish by reviewing the diff and recording any decisions or limitations.

Use subagents only when the user explicitly asks for delegation or parallel agent work.
When they do, prefer the project-scoped agents in `.codex/agents/`.

## Task Start

Create `.steering/YYYYMMDD-task-name/` with:

- `requirement.md`: background, goal, scope, out of scope, acceptance criteria.
- `design.md`: approach, changed areas, compatibility, test strategy, rollback.
- `tasklist.md`: checkboxes at roughly 30-minute granularity.
- `decisions.md`: only for meaningful tradeoffs or policy choices.
- `blockers.md`: only when blocked or carrying deferred risk.

Use the current local date in `YYYYMMDD`. Prefer a short kebab-case task name.

## Implementation Flows

- **Feature**: read existing patterns, document the design, implement narrowly, add tests or
  verification proportional to risk, update docs when behavior changes.
- **Bug fix**: reproduce or explain the failure, record root cause, add or identify a
  regression check when feasible, then make the smallest defensible fix.
- **Refactor**: establish current checks first, preserve behavior, change in small steps,
  and avoid mixing feature or bug-fix work into the same task.

For source edits under `src/erre_sandbox/`, always consider:

- `architecture-rules` for layer direction and GPL/cloud API constraints.
- `python-standards` for Python style.
- `error-handling` when async, retry, timeout, WebSocket, sqlite, or LLM fallback behavior changes.
- `test-standards` when adding or changing tests.

## Reimagine

Use this for architecture, public interfaces, difficult bugs, and designs with multiple
credible approaches:

1. Save the first plan as `design-v1.md`.
2. Re-read only `requirement.md` and produce a fresh alternative in `design.md`.
3. Compare the two in `design-comparison.md`.
4. Choose v1, v2, or a hybrid and record the reason in `decisions.md`.

Do not use reimagine after implementation has already created side effects that would need
manual rollback.

## Review And Finish

Before final delivery:

- Run focused checks for touched areas.
- Run `uv run ruff check src tests`, `uv run ruff format --check src tests`,
  `uv run mypy src`, and `uv run pytest` when feasible.
- Review `git diff` for unrelated changes and do not revert user work.
- Update `tasklist.md` and `design.md` with what actually happened.
- Mention skipped checks or residual risk in the final response.

Do not commit unless the user asks. If committing, use `git-workflow`.

codex
まず設計側の LOW-1 周辺と ADR を読みます。次に persona YAML の `primary_corpus_refs` と factual basis を確認して、A が本当に成立するかを切り分けます。
exec
/bin/zsh -lc "sed -n '1,260p' .steering/20260430-m9-eval-system/blockers.md" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
# Blockers & Deferred Items — m9-eval-system

## defer 方針

Codex `gpt-5.5 xhigh` review LOW finding および本タスクで即決できない判断事項を defer。
defer 期限と reopen 条件を明示。M9-B 親タスクの blockers (`.steering/20260430-m9-b-lora-execution-plan/blockers.md`)
とは scope を分離し、本タスク固有の項目のみここに記録。

exec
/bin/zsh -lc 'rg -n "stimulus|RoleEval|MCQ|synthetic_4th|4th|heldout|P2a|P2c|P3a" .steering/20260430-m9-eval-system/tasklist.md .steering/20260430-m9-eval-system/requirement.md' in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
.steering/20260430-m9-eval-system/tasklist.md:4:`[Mac]` / `[GG]` / `[Mac→GG]` tag 付与必須。Codex review 反映で P2c / P3a /
.steering/20260430-m9-eval-system/tasklist.md:5:P3a-decide が追加され、合計 16 phase + closure。
.steering/20260430-m9-eval-system/tasklist.md:95:        4th persona heldout (38 unit test 全 PASS):
.steering/20260430-m9-eval-system/tasklist.md:99:          synthetic 4th)
.steering/20260430-m9-eval-system/tasklist.md:124:        (Kant de / Nietzsche de / Rikyu ja / synthetic_4th de+ja)、ME-6
.steering/20260430-m9-eval-system/tasklist.md:142:  - [x] synthetic 4th persona function-word vector (de + ja の 2 言語、
.steering/20260430-m9-eval-system/tasklist.md:161:    - [x] synthetic_4th profile == background_mean (de + ja 両方、
.steering/20260430-m9-eval-system/tasklist.md:180:- [ ] [Mac] **P2a** — `golden/stimulus/{kant,nietzsche,rikyu}.yaml` 起草 (4h):
.steering/20260430-m9-eval-system/tasklist.md:181:  - [ ] Wachsmuth Toulmin 30 stimulus
.steering/20260430-m9-eval-system/tasklist.md:182:  - [ ] ToM info-asymmetric chashitsu 20 stimulus
.steering/20260430-m9-eval-system/tasklist.md:183:  - [ ] RoleEval-adapted MCQ 10 stimulus (LOW-1 defer 解消後の方針反映)
.steering/20260430-m9-eval-system/tasklist.md:184:  - [ ] persona-conditional moral dilemma 10 stimulus
.steering/20260430-m9-eval-system/tasklist.md:185:  - [ ] 計 70 stimulus × 3 巡 = 210 turn
.steering/20260430-m9-eval-system/tasklist.md:189:- [ ] [Mac] **P2c** — `src/erre_sandbox/evidence/golden_baseline.py` 起草 (Codex HIGH-4、3h):
.steering/20260430-m9-eval-system/tasklist.md:194:    - [ ] `test_one_stimulus_cycle_dryrun` (synthetic stimulus + mock LLM)
.steering/20260430-m9-eval-system/tasklist.md:195:    - [ ] `test_70_stimulus_battery` (input queue 不要を確認)
.steering/20260430-m9-eval-system/tasklist.md:197:    - [ ] DB7 LOW-1 synthetic 4th persona fixture も含める
.steering/20260430-m9-eval-system/tasklist.md:201:- [ ] [GG] **P3a** — Pilot run **200 turn × 両形式 × 3 persona** isolated 採取
.steering/20260430-m9-eval-system/tasklist.md:203:  - [ ] stimulus 主体 (200 stimulus turn 縮小版): 200 turn × 3 persona
.steering/20260430-m9-eval-system/tasklist.md:206:- [ ] [Mac] **P3a-decide** — bootstrap CI width 比較で ratio 確定 (1h):
.steering/20260430-m9-eval-system/tasklist.md:276:- ME-4 ratio confirm: P3a-decide 時に ADR 更新
.steering/20260430-m9-eval-system/tasklist.md:277:- LOW-1 RoleEval wording: P2a 着手時に option A/B/C 確定
.steering/20260430-m9-eval-system/tasklist.md:288:| P2a-P2c | Claude (Mac) | 9 |
.steering/20260430-m9-eval-system/tasklist.md:289:| P3a + P3a-decide | Operator (GG) + Claude (Mac) | 7-9 |
.steering/20260430-m9-eval-system/requirement.md:74:      (`design-final.md` Hardware allocation 節、Codex HIGH-3 で P3a / P3a-decide 追加)

exec
/bin/zsh -lc 'git status --short' in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
 M .claude/hooks/pre-edit-steering.sh
 M .claude/hooks/preflight.sh
 M .codex/budget.json
 M .github/workflows/ci.yml
 M .steering/20260430-m9-b-lora-execution-plan/blockers.md
 M pyproject.toml
 M uv.lock
?? .steering/20260430-m9-eval-system/
?? src/erre_sandbox/contracts/eval_paths.py
?? src/erre_sandbox/evidence/eval_store.py
?? src/erre_sandbox/evidence/reference_corpus/
?? src/erre_sandbox/evidence/tier_a/
?? tests/test_evidence/test_eval_paths_contract.py
?? tests/test_evidence/test_eval_store.py
?? tests/test_evidence/test_tier_a/

exec
/bin/zsh -lc "nl -ba .steering/20260430-m9-eval-system/tasklist.md | sed -n '172,210p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
   172	    - [x] de background_std 全 49 word > 0 を契約 test
   173	    - [x] BACKGROUND_CHUNK_DE=500 sentinel 化 (build と test の lockstep)
   174	  - [x] フル test suite 1142 passed / 31 skipped / 14 deselected
   175	        (前回 1128 → +14 新テスト、既存回帰なし)、mypy src 0、
   176	        ruff/format clean、eval-egress-grep-gate 緑
   177	
   178	### P2 — Stimulus + Orchestrator + Driver
   179	
   180	- [ ] [Mac] **P2a** — `golden/stimulus/{kant,nietzsche,rikyu}.yaml` 起草 (4h):
   181	  - [ ] Wachsmuth Toulmin 30 stimulus
   182	  - [ ] ToM info-asymmetric chashitsu 20 stimulus
   183	  - [ ] RoleEval-adapted MCQ 10 stimulus (LOW-1 defer 解消後の方針反映)
   184	  - [ ] persona-conditional moral dilemma 10 stimulus
   185	  - [ ] 計 70 stimulus × 3 巡 = 210 turn
   186	- [ ] [Mac] **P2b** — `src/erre_sandbox/integration/dialog.py` minimum patch (2h):
   187	  - [ ] `golden_baseline_mode: bool = False` 引数追加 (cooldown / timeout bypass)
   188	  - [ ] default False で既存全テスト pass を確認
   189	- [ ] [Mac] **P2c** — `src/erre_sandbox/evidence/golden_baseline.py` 起草 (Codex HIGH-4、3h):
   190	  - [ ] `GoldenBaselineDriver` クラス (公開 API のみ使用)
   191	  - [ ] `derive_seed()` blake2b 実装 (ME-5)
   192	  - [ ] `golden/seeds.json` 生成 + commit
   193	  - [ ] `tests/test_evidence/test_golden_baseline.py`:
   194	    - [ ] `test_one_stimulus_cycle_dryrun` (synthetic stimulus + mock LLM)
   195	    - [ ] `test_70_stimulus_battery` (input queue 不要を確認)
   196	    - [ ] `test_seed_manifest_stable` (Mac/G-GEAR 同値)
   197	    - [ ] DB7 LOW-1 synthetic 4th persona fixture も含める
   198	
   199	### P3 — Pilot then Golden Baseline (Codex HIGH-3 順序修正)
   200	
   201	- [ ] [GG] **P3a** — Pilot run **200 turn × 両形式 × 3 persona** isolated 採取
   202	      (fresh scheduler/store/seed、carry-over 防止、6-8h)
   203	  - [ ] stimulus 主体 (200 stimulus turn 縮小版): 200 turn × 3 persona
   204	  - [ ] 自然対話 主体: 200 turn × 3 persona
   205	  - [ ] 両形式の DuckDB を Mac へ rsync (CHECKPOINT + temp+rename + read_only=True、ME-2)
   206	- [ ] [Mac] **P3a-decide** — bootstrap CI width 比較で ratio 確定 (1h):
   207	  - [ ] Burrows Delta / Vendi / Big5 ICC の CI width 計算
   208	  - [ ] ME-4 ADR を Edit (placeholder → 確定値)
   209	  - [ ] M9-B `blockers.md` の "Hybrid baseline 比率 200/300" 項目を close
   210	- [ ] [GG] **P3** — Golden baseline 採取 (3 persona × 5 run × 500 turn、確定 ratio 投入、

exec
/bin/zsh -lc 'find src/erre_sandbox/evidence/reference_corpus -maxdepth 3 -type f -print | sort' in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
src/erre_sandbox/evidence/reference_corpus/__init__.py
src/erre_sandbox/evidence/reference_corpus/__pycache__/__init__.cpython-311.pyc
src/erre_sandbox/evidence/reference_corpus/__pycache__/_build_vectors.cpython-311.pyc
src/erre_sandbox/evidence/reference_corpus/__pycache__/function_words.cpython-311.pyc
src/erre_sandbox/evidence/reference_corpus/__pycache__/loader.cpython-311.pyc
src/erre_sandbox/evidence/reference_corpus/_build_vectors.py
src/erre_sandbox/evidence/reference_corpus/_provenance.yaml
src/erre_sandbox/evidence/reference_corpus/function_words.py
src/erre_sandbox/evidence/reference_corpus/loader.py
src/erre_sandbox/evidence/reference_corpus/raw/kant_de.txt
src/erre_sandbox/evidence/reference_corpus/raw/nietzsche_de.txt
src/erre_sandbox/evidence/reference_corpus/raw/rikyu_ja.txt
src/erre_sandbox/evidence/reference_corpus/vectors.json

exec
/bin/zsh -lc 'find src/erre_sandbox/evidence -maxdepth 2 -type f -print | sort' in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
src/erre_sandbox/evidence/__init__.py
src/erre_sandbox/evidence/__pycache__/__init__.cpython-311.pyc
src/erre_sandbox/evidence/__pycache__/eval_store.cpython-311.pyc
src/erre_sandbox/evidence/__pycache__/metrics.cpython-311.pyc
src/erre_sandbox/evidence/__pycache__/scaling_metrics.cpython-311.pyc
src/erre_sandbox/evidence/eval_store.py
src/erre_sandbox/evidence/metrics.py
src/erre_sandbox/evidence/reference_corpus/__init__.py
src/erre_sandbox/evidence/reference_corpus/_build_vectors.py
src/erre_sandbox/evidence/reference_corpus/_provenance.yaml
src/erre_sandbox/evidence/reference_corpus/function_words.py
src/erre_sandbox/evidence/reference_corpus/loader.py
src/erre_sandbox/evidence/reference_corpus/vectors.json
src/erre_sandbox/evidence/scaling_metrics.py
src/erre_sandbox/evidence/tier_a/__init__.py
src/erre_sandbox/evidence/tier_a/burrows.py
src/erre_sandbox/evidence/tier_a/empath_proxy.py
src/erre_sandbox/evidence/tier_a/mattr.py
src/erre_sandbox/evidence/tier_a/nli.py
src/erre_sandbox/evidence/tier_a/novelty.py

exec
/bin/zsh -lc "nl -ba src/erre_sandbox/evidence/reference_corpus/_provenance.yaml | sed -n '1,150p'" in /Users/johnd/ERRE-Sand Box
exec
/bin/zsh -lc "nl -ba tests/test_evidence/test_tier_a/test_burrows_corpus_qc.py | sed -n '100,180p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
     1	# Reference corpus provenance — Burrows Delta P1b
     2	#
     3	# Every entry below records:
     4	#   - persona_id: stable identifier (matches personas/*.yaml)
     5	#   - language: ISO-ish tag (must match BurrowsReference.language)
     6	#   - source: human-readable corpus origin
     7	#   - edition: bibliographic edition (e.g. "Akademie-Ausgabe Bd. VIII")
     8	#   - translator: original-language entries leave this blank
     9	#   - year: original publication year (translator copyright independent)
    10	#   - public_domain: true if the *specific edition* is PD-redistributable
    11	#   - retrieval_url: URL we fetched the verbatim text from
    12	#   - retrieval_date: ISO-8601 date we fetched it
    13	#   - corpus_path: relative path under reference_corpus/ to the saved text
    14	#   - approx_tokens: rough whitespace-token count for de, char count for ja
    15	#   - corpus_too_small_for_chunk_qc: true if approx_tokens < 10000
    16	#       (one ≥5K-word chunk pair is the ME-6 stability test minimum;
    17	#       reopen path documented in blockers.md)
    18	#
    19	# ME-6 mandates this metadata; the loader requires every persona/language
    20	# pair it serves to have a matching entry here, so unrecorded provenance
    21	# raises ReferenceCorpusMissingError on first use. Any expansion (e.g.
    22	# adding the Cambridge Edition Kant English translation once licensing
    23	# is confirmed) lands here as a new entry.
    24	
    25	schema_version: "0.1.0-m9eval"
    26	
    27	# Toy reference scope (P1b initial commit):
    28	#   - de: Kant Akademie-Ausgabe excerpt + Nietzsche Project Gutenberg PD edition
    29	#   - ja: 5 verbatim 利休道歌 (small but verbatim PD)
    30	#   - en: deferred to a future iteration once Cambridge / Kaufmann
    31	#         translation licensing is confirmed (blockers.md "Burrows corpus
    32	#         license — English translations defer")
    33	#
    34	# Synthetic 4th persona is computed analytically (background mean) so it
    35	# has no raw text and no retrieval URL.
    36	
    37	entries:
    38	  - persona_id: kant
    39	    language: de
    40	    source: "Wikisource (de.wikisource.org), Kant — Beantwortung der Frage: Was ist Aufklärung?"
    41	    edition: "Berlinische Monatsschrift Bd. 4 (1784); Akademie-Ausgabe parallel"
    42	    translator: ""
    43	    year: 1784
    44	    public_domain: true
    45	    retrieval_url: "https://de.wikisource.org/wiki/Beantwortung_der_Frage:_Was_ist_Aufkl%C3%A4rung%3F"
    46	    retrieval_date: "2026-05-01"
    47	    corpus_path: "raw/kant_de.txt"
    48	    approx_tokens: 2656
    49	    corpus_too_small_for_chunk_qc: true
    50	    notes: >-
    51	      Kant 1804 死去 — body text is unambiguous PD. Wikisource markup was
    52	      stripped (templates, wiki bold, editorial annotations) leaving the
    53	      essay body from "Aufklärung ist der Ausgang..." through Kant's
    54	      closing footnote. Below the ≥10K-word threshold for the ME-6
    55	      chunk-stability test; expansion to the full Akademie-Ausgabe Bd.
    56	      VIII is deferred to m9-eval-corpus.
    57	
    58	  - persona_id: nietzsche
    59	    language: de
    60	    source: "Project Gutenberg eBook 7205 — Also sprach Zarathustra (German PD edition)"
    61	    edition: "PG 7205 (Kröner-tradition PD text, not Colli/Montinari KGW)"
    62	    translator: ""
    63	    year: 1883
    64	    public_domain: true
    65	    retrieval_url: "https://www.gutenberg.org/cache/epub/7205/pg7205.txt"
    66	    retrieval_date: "2026-05-01"
    67	    corpus_path: "raw/nietzsche_de.txt"
    68	    approx_tokens: 12002
    69	    corpus_too_small_for_chunk_qc: false
    70	    notes: >-
    71	      First ~12K words of the body, starting at Zarathustra's Vorrede §1
    72	      ("Als Zarathustra dreissig Jahr alt war..."). PG header / footer
    73	      stripped. Note that the de Gruyter Colli/Montinari KGW edition
    74	      carries editorial copyright on selection / apparatus; this file
    75	      uses the older Kröner-tradition PD prose only, per ME-6 license
    76	      precaution.
    77	
    78	  - persona_id: rikyu
    79	    language: ja
    80	    source: "Wikipedia (ja.wikipedia.org) — 利休道歌 article verbatim quotations"
    81	    edition: "Wikipedia 利休道歌 article (5 representative verses, public-domain compilation tradition)"
    82	    translator: ""
    83	    year: 1591  # Sen no Rikyū died 1591; the 道歌 tradition is 16th–17th c.
    84	    public_domain: true
    85	    retrieval_url: "https://ja.wikipedia.org/wiki/%E5%88%A9%E4%BC%91%E9%81%93%E6%AD%8C"
    86	    retrieval_date: "2026-05-01"
    87	    corpus_path: "raw/rikyu_ja.txt"
    88	    approx_tokens: 134  # character count — Japanese has no whitespace
    89	    corpus_too_small_for_chunk_qc: true
    90	    notes: >-
    91	      Only 5 verbatim 道歌 are available in the Wikipedia article; the
    92	      ja.wikisource pages for 利休百首 / 南方録 / 徒然草 / 方丈記 are
    93	      djvu-indexed and do not expose plain text via the raw API. The
    94	      tradition is attributed to Rikyū but compiled by disciples in the
    95	      16–17th century — all authors PD by age. This corpus is well
    96	      below ≥5K-word chunk-stability threshold (ME-6); expansion to a
    97	      proper Rikyū corpus (Aozora Bunko, Kokubun Taikan OCR, or a
    98	      ja.wikisource djvu OCR pipeline) is deferred to m9-eval-corpus.
    99	
   100	  - persona_id: synthetic_4th
   101	    language: de
   102	    source: "Synthetic — DB7 LOW-1 heldout fixture"
   103	    edition: "Computed analytically (no raw text)"
   104	    translator: ""
   105	    year: null
   106	    public_domain: true
   107	    retrieval_url: ""
   108	    retrieval_date: "2026-05-01"
   109	    corpus_path: ""
   110	    approx_tokens: null
   111	    corpus_too_small_for_chunk_qc: true  # nothing to chunk
   112	    notes: >-
   113	      DB7 LOW-1 heldout 4th persona used to detect 3-persona memorisation.
   114	      profile_freq is set to the German background mean so the synthetic
   115	      4th sits at the centre of the function-word frequency simplex; it
   116	      is not a stylistic claim, just an orthogonality fixture.
   117	
   118	  - persona_id: synthetic_4th
   119	    language: ja
   120	    source: "Synthetic — DB7 LOW-1 heldout fixture (Japanese mirror)"
   121	    edition: "Computed analytically (no raw text)"
   122	    translator: ""
   123	    year: null
   124	    public_domain: true
   125	    retrieval_url: ""
   126	    retrieval_date: "2026-05-01"
   127	    corpus_path: ""
   128	    approx_tokens: null
   129	    corpus_too_small_for_chunk_qc: true
   130	    notes: >-
   131	      Japanese mirror of the synthetic 4th heldout. profile_freq equals
   132	      the ja background mean. Note that with only one ja corpus shipped
   133	      in the toy reference (Rikyū 5 道歌), the ja background is
   134	      computed from the single-corpus chunk distribution; the synthetic
   135	      4th sits at that mean and discriminative claims for ja remain
   136	      qualified by the Rikyū corpus expansion blocker.

 succeeded in 0ms:
   100	    if den_x == 0 or den_y == 0:
   101	        return float("nan")
   102	    return num / (den_x * den_y)
   103	
   104	
   105	# --- Schema gate ----------------------------------------------------------
   106	
   107	
   108	def test_provenance_yaml_parses_and_has_entries() -> None:
   109	    text = (_HERE / "_provenance.yaml").read_text(encoding="utf-8")
   110	    parsed = yaml.safe_load(text)
   111	    assert isinstance(parsed, dict)
   112	    assert parsed.get("schema_version") == "0.1.0-m9eval"
   113	    entries = parsed.get("entries")
   114	    assert isinstance(entries, list)
   115	    assert len(entries) >= 4  # 3 PD personas + at least one synthetic_4th
   116	
   117	
   118	def test_provenance_required_keys_complete_for_every_entry() -> None:
   119	    for idx, entry in enumerate(get_provenance_entries()):
   120	        missing = PROVENANCE_REQUIRED_KEYS - set(entry.keys())
   121	        assert not missing, f"entries[{idx}] missing keys {sorted(missing)}"
   122	
   123	
   124	def test_every_provenance_entry_has_public_domain_true() -> None:
   125	    # The toy reference scope is PD-only by design (Cambridge Edition /
   126	    # Kaufmann translation deferred). If a future PR introduces a
   127	    # restricted-license entry the contract test fires before the data
   128	    # ships.
   129	    for entry in get_provenance_entries():
   130	        assert entry.get("public_domain") is True, (
   131	            f"non-PD provenance entry: {entry.get('persona_id')!r}/"
   132	            f"{entry.get('language')!r} — see blockers.md before adding"
   133	        )
   134	
   135	
   136	def test_available_personas_round_trips_through_loader() -> None:
   137	    pairs = available_personas()
   138	    assert pairs, "available_personas() empty — vectors.json or provenance broken"
   139	    for persona_id, language in pairs:
   140	        ref = load_reference(persona_id, language)
   141	        assert isinstance(ref, BurrowsReference)
   142	        assert ref.language == language
   143	
   144	
   145	def test_unregistered_persona_raises() -> None:
   146	    with pytest.raises(ReferenceCorpusMissingError):
   147	        load_reference("plato", "de")
   148	
   149	
   150	def test_cross_language_pair_raises() -> None:
   151	    # kant has only 'de' provenance; ('kant', 'ja') must not silently
   152	    # fall back to a different language.
   153	    with pytest.raises(ReferenceCorpusMissingError):
   154	        load_reference("kant", "ja")
   155	
   156	
   157	# --- synthetic_4th = background mean (DB7 LOW-1) -------------------------
   158	
   159	
   160	def test_synthetic_4th_de_profile_equals_background_mean() -> None:
   161	    ref = load_reference("synthetic_4th", "de")
   162	    assert ref.profile_freq == ref.background_mean
   163	
   164	
   165	def test_synthetic_4th_ja_profile_equals_background_mean() -> None:
   166	    ref = load_reference("synthetic_4th", "ja")
   167	    assert ref.profile_freq == ref.background_mean
   168	
   169	
   170	# --- Persona-discriminative on real toy corpora --------------------------
   171	
   172	
   173	def _read_corpus(persona_id: str, language: str) -> str:
   174	    # Locate the raw corpus via provenance lookup so this stays in lock
   175	    # with the YAML record.
   176	    for entry in get_provenance_entries():
   177	        if entry.get("persona_id") == persona_id and entry.get("language") == language:
   178	            corpus_path = str(entry.get("corpus_path") or "")
   179	            if not corpus_path:
   180	                pytest.skip(

exec
/bin/zsh -lc "nl -ba src/erre_sandbox/evidence/reference_corpus/_build_vectors.py | sed -n '170,222p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
   170	    here = Path(__file__).resolve().parent
   171	    raw_dir = here / "raw"
   172	
   173	    # --- German ----------------------------------------------------------
   174	    fw_de = FUNCTION_WORDS_DE
   175	    persona_tokens_de: dict[str, list[str]] = {}
   176	    for persona_id, filename in (
   177	        ("kant", "kant_de.txt"),
   178	        ("nietzsche", "nietzsche_de.txt"),
   179	    ):
   180	        text = (raw_dir / filename).read_text(encoding="utf-8")
   181	        persona_tokens_de[persona_id] = _tokenise_de(text)
   182	
   183	    pooled_chunks_de: list[list[float]] = []
   184	    for tokens in persona_tokens_de.values():
   185	        pooled_chunks_de.extend(_chunk_frequencies(tokens, fw_de, BACKGROUND_CHUNK_DE))
   186	    bg_mean_de, bg_std_de = _background_stats(pooled_chunks_de, fw_de)
   187	
   188	    personas_de: dict[str, dict[str, object]] = {}
   189	    for persona_id, tokens in persona_tokens_de.items():
   190	        personas_de[persona_id] = {
   191	            "profile_freq": _persona_profile_freq(tokens, fw_de),
   192	            "n_tokens": len(tokens),
   193	        }
   194	    personas_de["synthetic_4th"] = {
   195	        "profile_freq": list(bg_mean_de),
   196	        "n_tokens": None,
   197	    }
   198	
   199	    # --- Japanese -------------------------------------------------------
   200	    fw_ja = FUNCTION_WORDS_JA
   201	    persona_tokens_ja: dict[str, list[str]] = {}
   202	    rikyu_text = (raw_dir / "rikyu_ja.txt").read_text(encoding="utf-8")
   203	    persona_tokens_ja["rikyu"] = _tokenise_ja(rikyu_text, fw_ja)
   204	
   205	    pooled_chunks_ja: list[list[float]] = []
   206	    for tokens in persona_tokens_ja.values():
   207	        pooled_chunks_ja.extend(_chunk_frequencies(tokens, fw_ja, BACKGROUND_CHUNK_JA))
   208	    bg_mean_ja, bg_std_ja = _background_stats(pooled_chunks_ja, fw_ja)
   209	
   210	    personas_ja: dict[str, dict[str, object]] = {}
   211	    for persona_id, tokens in persona_tokens_ja.items():
   212	        personas_ja[persona_id] = {
   213	            "profile_freq": _persona_profile_freq(tokens, fw_ja),
   214	            "n_tokens": len(tokens),
   215	        }
   216	    personas_ja["synthetic_4th"] = {
   217	        "profile_freq": list(bg_mean_ja),
   218	        "n_tokens": None,
   219	    }
   220	
   221	    return {
   222	        "schema_version": SCHEMA_VERSION,

exec
/bin/zsh -lc "nl -ba .steering/20260430-m9-b-lora-execution-plan/blockers.md | sed -n '1,35p'" in /Users/johnd/ERRE-Sand Box
exec
/bin/zsh -lc "nl -ba .steering/20260430-m9-b-lora-execution-plan/decisions.md | sed -n '145,170p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
     1	# Blockers & Deferred Items — M9-B LoRA Execution Plan
     2	
     3	## defer 方針
     4	
     5	Codex review LOW finding および設計上 M9-B closure では即決できない判断事項を defer。
     6	defer 期限と reopen 条件を明示。
     7	
     8	## Codex LOW findings (defer)
     9	
    10	### LOW-1: synthetic heldout 4th persona in eval tests
    11	- **finding**: N=4 deferral acceptable, but eval pipeline may overfit to 3 personas
    12	- **defer 先**: M9-eval-system (eval test fixture として synthetic 4th persona を含める)
    13	- **reopen 条件**: eval pipeline test で synthetic 4th が機能不全
    14	- **status**: DB7 で正式採用、defer は実装タイミングのみ
    15	
    16	### LOW-2: LIWC OSS alternative honest framing
    17	- **finding**: Empath/spaCy は LIWC 等価ではない、proxy として framing 必要
    18	- **defer 先**: M9-eval-system (LIWC license 評価 + alternative decision tree 起草)
    19	- **reopen 条件**: LIWC 商用 license が approve / OSS alternative が validation 通過
    20	- **status**: DB10 で正式 framing 採用、license 最終決定は defer
    21	
    22	## M9-B closure では決められない判断事項
    23	
    24	### LIWC 商用 license の最終可否判定
    25	- **status**: **CLOSED 2026-04-30** — m9-eval-system の Plan 段階で **Option D 採用**
    26	  (LIWC 全廃、Big5 を IPIP-NEO 自己申告に一本化、Empath は Tier A 副次的 diagnostic
    27	  のみで Big5 claim には使わない)。商用 license は取得しない。
    28	- **closure 経路**: m9-eval-system の `design-final.md` §"LIWC alternative: Option D"
    29	  + `decisions.md` ME-1 (IPIP-NEO fallback trigger ADR) + Codex `gpt-5.5 xhigh`
    30	  review HIGH/MEDIUM 反映済。詳細根拠は m9-eval-system steering 参照。
    31	- **issue (履歴)**: LIWC-22 は商用 license、ERRE は zero-budget 制約
    32	- **option A**: 商用 license 取得 (one-time fee 数百ドル) — 不採用
    33	- **option B**: Empath OSS 代用 (proxy、psycholinguistic depth は劣る) — 副次採用 (Tier A 1 axis)
    34	- **option C**: spaCy ベースの custom dictionary 自作 (work cost 大) — 不採用
    35	- **option D**: stylometry (Burrows' Delta) のみで persona-fit を測り、Big-Five claim

 succeeded in 0ms:
   145	  - Tier C judge LLM が smaller model に置換可能で contention 解消
   146	
   147	---
   148	
   149	## DB7 — Persona N=4 拡張時期: defer to M10 + synthetic heldout 4th in eval tests (LOW-1 反映)
   150	
   151	- **決定**:
   152	  - Runtime N=4 (agora 主体 4 人目 actual deploy) は **M10 まで完全 defer**
   153	  - ただし **eval pipeline test には mocked 4th persona scenario を含める**
   154	- **根拠**:
   155	  - M9-B / M9-eval-system 期間は N=3 の divergence 漸近線 + 評価系構築が優先
   156	  - codex LOW-1: eval pipeline が N=3 専用に overfit するのを防ぐため、synthetic 4th
   157	    persona を test fixture として使う
   158	  - 4 人目の persona YAML 起草 / reference corpus 整備 / golden set は M10 着手時に開始
   159	- **棄却**:
   160	  - v1: M9-B 中 YAML 起草 → 評価系設計を複雑化
   161	  - 完全 defer (synthetic も含めない): eval pipeline overfit リスク
   162	- **影響**:
   163	  - eval pipeline test に synthetic persona fixture 追加
   164	  - M10 で agora 主体 candidate を再評価
   165	- **re-open 条件**:
   166	  - N=3 の divergence が早期に saturate、4 人目で extension が必要
   167	  - M10 timeline で 4 人目 candidate が確定
   168	
   169	---
   170	

exec
/bin/zsh -lc "rg -n \"RoleEval|MCQ|FActScore|PhilEval|persona-factual|factual|heldout|synthetic\" .steering/20260430-m9-b-lora-execution-plan .steering/20260430-m9-eval-system docs -g '*.md'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
.steering/20260430-m9-b-lora-execution-plan/design-final.md:129:### G. Persona N=4 拡張時期 (DB7) → defer to M10 + synthetic heldout 4th persona (LOW-1 反映)
.steering/20260430-m9-b-lora-execution-plan/design-final.md:199:- FActScore-adapted against Kant/Nietzsche/Rikyu canonical corpus
.steering/20260430-m9-b-lora-execution-plan/design-final.md:201:- RoleEval-adapted biographical MCQ pre-gate
.steering/20260430-m9-b-lora-execution-plan/design-final.md:280:| LOW-1 (synthetic 4th persona) | DB7 → eval test scenario として採用 | ✅ 反映 |
.steering/20260430-m9-b-lora-execution-plan/decisions.md:149:## DB7 — Persona N=4 拡張時期: defer to M10 + synthetic heldout 4th in eval tests (LOW-1 反映)
.steering/20260430-m9-b-lora-execution-plan/decisions.md:156:  - codex LOW-1: eval pipeline が N=3 専用に overfit するのを防ぐため、synthetic 4th
.steering/20260430-m9-b-lora-execution-plan/decisions.md:161:  - 完全 defer (synthetic も含めない): eval pipeline overfit リスク
.steering/20260430-m9-b-lora-execution-plan/decisions.md:163:  - eval pipeline test に synthetic persona fixture 追加
.steering/20260430-m9-b-lora-execution-plan/decisions.md:231:    - Tier D: sparse manual (FActScore-adapted / 専門家 review / RoleEval-adapted MCQ)
.steering/20260430-m9-b-lora-execution-plan/design-v2.md:154:- Sparse manual (Tier D): FActScore against canonical corpus / 専門家 qualitative review
.steering/20260430-m9-b-lora-execution-plan/design-v2.md:171:- M9-eval-system: Tier B 完全実装 (Prometheus 2 rubric / FANToM-adapted / FActScore-adapted) + 専門家 review pipeline + golden set 採取
.steering/20260430-m9-eval-system/design-final.md:17:| P1b | reference corpus pickle 整備 (Kant 独+英訳 / Nietzsche / Rikyu / synthetic 4th) | Claude | Mac | CPU only | 2h | fixture test 緑 |
.steering/20260430-m9-eval-system/design-final.md:20:| **P2c** | **External golden driver** (`evidence/golden_baseline.py`) を `schedule_initiate`/`record_turn`/`close_dialog` 公開 API のみで実装、**input queue 依存無し** (Codex HIGH-4 反映) | Claude | Mac | CPU only | 3h | unit test (synthetic 1 stimulus 駆動) 緑 |
.steering/20260430-m9-eval-system/design-final.md:116:  - RoleEval-adapted Kant biographical MCQ: 10
.steering/20260430-m9-eval-system/design-final.md:167:  full cycle で実行** できることを synthetic stimulus + mock LLM で確認
.steering/20260430-m9-eval-system/design-final.md:265:- `reference_corpus/` — Kant 独+英訳、Nietzsche、Rikyu、synthetic 4th persona の
.steering/20260430-m9-eval-system/design-final.md:279:- `personas/_synthetic_4th.yaml` — DB7 LOW-1 fixture (Big5 が 3 persona と直交する
.steering/20260430-m9-eval-system/design-final.md:293:- `tests/test_evidence/test_golden_baseline.py` — synthetic 4th persona DB7 LOW-1 含む
.steering/20260430-m9-eval-system/design-final.md:401:  `ipip_neo_short` のみ optional 追加。`_synthetic_4th.yaml` も同じ schema
.steering/20260430-m9-eval-system/design-final.md:416:3. **Bootstrap CI shape**: 既知分布 (synthetic Vendi / ICC / Burrows triple) で
.steering/20260430-m9-eval-system/design-final.md:422:### DB7 LOW-1 (synthetic 4th persona heldout fixture)
.steering/20260430-m9-eval-system/design-final.md:424:- `personas/_synthetic_4th.yaml`: Big5 が 3 既存 persona と直交する架空 thinker
.steering/20260430-m9-eval-system/design-final.md:430:- `test_tier_a/`: 5 metric が synthetic + 4th persona heldout で NaN/crash 無く計算、
.steering/20260430-m9-eval-system/design-final.md:492:   - 70 stimulus × 3 巡 = 210 turn は Wachsmuth/ToM/RoleEval/dilemma の 4 系統に
.steering/20260430-m9-eval-system/design-final.md:518:| RoleEval Kant 限定 vs persona-specific MCQ 区別 | LOW-1 | `blockers.md` defer | ✅ defer |
.steering/20260430-m9-b-lora-execution-plan/tasklist.md:92:- [ ] synthetic 4th persona test fixture 追加 [S] [DB7、LOW-1]
.steering/20260430-m9-b-lora-execution-plan/blockers.md:10:### LOW-1: synthetic heldout 4th persona in eval tests
.steering/20260430-m9-b-lora-execution-plan/blockers.md:12:- **defer 先**: M9-eval-system (eval test fixture として synthetic 4th persona を含める)
.steering/20260430-m9-b-lora-execution-plan/blockers.md:13:- **reopen 条件**: eval pipeline test で synthetic 4th が機能不全
.steering/20260430-m9-eval-system/codex-review-prompt.md:50:| Golden baseline | **Hybrid**: 200 turn fixed stimulus battery (Wachsmuth Toulmin 30 / ToM info-asymmetric chashitsu 20 / RoleEval-adapted Kant biographical MCQ 10 / persona-conditional moral dilemma 10 = 70 stimuli × 3 cycles, last cycle truncated to 10 turns) + 300 turn natural dialog from existing scheduler (peripatos / chashitsu / agora / garden mode transitions). Ratio 200/300 is **default; P3b pilot run 50 turn each will tune empirically**, recorded in blockers.md. |
.steering/20260430-m9-eval-system/design-comparison.md:34:| **Golden baseline 形式** | 自然対話 500 turn × 5 run × 3 persona | **Hybrid: stimulus battery 200 turn (Wachsmuth/ToM/RoleEval/dilemma 70 種 × 3 巡) + 自然対話 300 turn** |
.steering/20260430-m9-eval-system/design-comparison.md:42:| **stimulus battery** | 言及なし | 70 stimulus × 3 巡で Wachsmuth/ToM/RoleEval/dilemma を統制、bootstrap CI noise を抑制 |
.steering/20260430-m9-b-lora-execution-plan/codex-review.md:56:- **LOW-1**: N=4 deferral is acceptable, but add a synthetic heldout scenario
.steering/20260430-m9-b-lora-execution-plan/codex-review.md:59:  - Recommendation: Use a mocked/heldout fourth persona in eval tests without adding runtime N=4.
.steering/20260430-m9-eval-system/decisions.md:220:- LOW-1 (RoleEval Kant 限定) は `blockers.md` に defer (本 ADR set 範囲外)
.steering/20260430-m9-eval-system/codex-review-low1.md:14:# Codex independent review — LOW-1 RoleEval wording 決着 (P2a 着手直前)
.steering/20260430-m9-eval-system/codex-review-low1.md:23:  **LOW-1 (RoleEval wording) のみ defer**、本セッション冒頭で決着が必要
.steering/20260430-m9-eval-system/codex-review-low1.md:25:## レビューしてほしい判断: LOW-1 RoleEval wording
.steering/20260430-m9-eval-system/codex-review-low1.md:33:  - RoleEval-adapted Kant biographical MCQ: 10  ← LOW-1 該当
.steering/20260430-m9-eval-system/codex-review-low1.md:40:"RoleEval-adapted **Kant** biographical MCQ" のままでは Nietzsche / Rikyū 用 YAML が
.steering/20260430-m9-eval-system/codex-review-low1.md:43:- **Option A**: 各 persona に biographical MCQ 10 問ずつ起草 (Kant / Nietzsche / Rikyū それぞれの
.steering/20260430-m9-eval-system/codex-review-low1.md:45:- **Option B**: Kant biographical MCQ は Kant のみ、Nietzsche / Rikyū は別の floor diagnostic
.steering/20260430-m9-eval-system/codex-review-low1.md:47:- **Option C**: RoleEval を全廃し Wachsmuth/ToM/dilemma の 60 stimulus × 3.5 巡で 210 turn 構成
.steering/20260430-m9-eval-system/codex-review-low1.md:57:| persona-factuality dimension | ◎ 全 persona | △ Kant のみ | ✗ 完全消失 |
.steering/20260430-m9-eval-system/codex-review-low1.md:58:| Rikyū MCQ 起草難度 | △ legend 多、attested fact は 5-7 件確保可 | ○ 不要 | ◎ 不要 |
.steering/20260430-m9-eval-system/codex-review-low1.md:59:| Nietzsche MCQ 起草難度 | ○ Basel 1879 / Sils Maria / Overbeck 書簡で十分 | ○ 不要 | ◎ 不要 |
.steering/20260430-m9-eval-system/codex-review-low1.md:60:| drafting 工数 | +1.5h (30 MCQ) | ≈同等 | -0.5h |
.steering/20260430-m9-eval-system/codex-review-low1.md:61:| 後続 m9-eval-corpus で再 open 余地 | ◎ MCQ pool 別途精緻化可 | △ asymmetry 固定 | ✗ battery 再設計要 |
.steering/20260430-m9-eval-system/codex-review-low1.md:64:1. **persona-factuality は 4 軸の 1 つ** (argumentation / ToM / persona-factuality / moral disposition) —
.steering/20260430-m9-eval-system/codex-review-low1.md:65:   RoleEval を切ると "persona knows itself" の dimension が消え、style / argumentation /
.steering/20260430-m9-eval-system/codex-review-low1.md:69:3. **Rikyū MCQ 起草実現可能** — 利休道歌構造 / 待庵物理寸法 / 北野大茶湯 1587 / Hideyoshi 確執 /
.steering/20260430-m9-eval-system/codex-review-low1.md:71:4. **MCQ accuracy の cross-persona 絶対比較が無意味化する弱点** は ME-1 ADR の base model
.steering/20260430-m9-eval-system/codex-review-low1.md:78:2. **A/B/C 以外の Option D が存在するか?** (例: Kant 用 MCQ 10 を全 persona 共通の "general
.steering/20260430-m9-eval-system/codex-review-low1.md:79:   philosophical attribution" MCQ に置き換え、persona-factuality を sacrifice せずに per-persona
.steering/20260430-m9-eval-system/codex-review-low1.md:81:3. **Option A 採択時の落とし穴** — biographical MCQ の category 設計、distractor 設計、
.steering/20260430-m9-eval-system/codex-review-low1.md:82:   factual recall の信頼性確保で見落としそうな点 (例: persona prompt が "I am Kant" と
.steering/20260430-m9-eval-system/codex-review-low1.md:86:5. **DB7 LOW-1 (synthetic 4th persona heldout fixture) との整合** — 4th persona 用 MCQ をどう
.steering/20260430-m9-eval-system/codex-review-low1.md:87:   設計するか (Claude は本セッションで 3 persona の MCQ のみ起草予定、4th は P2c の test 範囲)
.steering/20260430-m9-eval-system/codex-review-low1.md:230:まず設計側の LOW-1 周辺と ADR を読みます。次に persona YAML の `primary_corpus_refs` と factual basis を確認して、A が本当に成立するかを切り分けます。
.steering/20260430-m9-eval-system/codex-review-low1.md:244:### LOW-1: RoleEval wording — Kant-only か persona-specific か (Codex LOW-1)
.steering/20260430-m9-eval-system/codex-review-low1.md:247:  "RoleEval-adapted Kant biographical MCQ: 10" と書かれているが、stimulus YAML は
.steering/20260430-m9-eval-system/codex-review-low1.md:249:  MCQ が Kant biographical のままだと意味が成り立たない
.steering/20260430-m9-eval-system/codex-review-low1.md:251:  - **option A**: 各 persona に対し biographical MCQ を 10 問ずつ起草 (Nietzsche
.steering/20260430-m9-eval-system/codex-review-low1.md:252:    biographical MCQ / Rikyu 茶の湯 MCQ)
.steering/20260430-m9-eval-system/codex-review-low1.md:253:  - **option B**: Kant biographical MCQ は Kant のみで実施、他 2 persona は別の
.steering/20260430-m9-eval-system/codex-review-low1.md:255:  - **option C**: RoleEval を全廃し Wachsmuth/ToM/dilemma の 60 stimulus × 3.5 巡で
.steering/20260430-m9-eval-system/codex-review-low1.md:370:| LOW-1 RoleEval wording | option A/B/C 確定 | P2a stimulus 起草 |
.steering/20260430-m9-eval-system/codex-review-low1.md:397:/bin/zsh -lc 'rg -n "Hybrid baseline|Stimulus battery|stimulus|RoleEval|MCQ|LOW-1|persona-factual|base model|ME-1|ME-4|ME-6" .steering/20260430-m9-eval-system/design-final.md' in /Users/johnd/ERRE-Sand Box
.steering/20260430-m9-eval-system/codex-review-low1.md:400:20:| **P2c** | **External golden driver** (`evidence/golden_baseline.py`) を `schedule_initiate`/`record_turn`/`close_dialog` 公開 API のみで実装、**input queue 依存無し** (Codex HIGH-4 反映) | Claude | Mac | CPU only | 3h | unit test (synthetic 1 stimulus 駆動) 緑 |
.steering/20260430-m9-eval-system/codex-review-low1.md:404:116:  - RoleEval-adapted Kant biographical MCQ: 10
.steering/20260430-m9-eval-system/codex-review-low1.md:414:167:  full cycle で実行** できることを synthetic stimulus + mock LLM で確認
.steering/20260430-m9-eval-system/codex-review-low1.md:418:279:- `personas/_synthetic_4th.yaml` — DB7 LOW-1 fixture (Big5 が 3 persona と直交する
.steering/20260430-m9-eval-system/codex-review-low1.md:419:293:- `tests/test_evidence/test_golden_baseline.py` — synthetic 4th persona DB7 LOW-1 含む
.steering/20260430-m9-eval-system/codex-review-low1.md:422:422:### DB7 LOW-1 (synthetic 4th persona heldout fixture)
.steering/20260430-m9-eval-system/codex-review-low1.md:424:492:   - 70 stimulus × 3 巡 = 210 turn は Wachsmuth/ToM/RoleEval/dilemma の 4 系統に
.steering/20260430-m9-eval-system/codex-review-low1.md:427:518:| RoleEval Kant 限定 vs persona-specific MCQ 区別 | LOW-1 | `blockers.md` defer | ✅ defer |
.steering/20260430-m9-eval-system/codex-review-low1.md:655:- LOW-1 (RoleEval Kant 限定) は `blockers.md` に defer (本 ADR set 範囲外)
.steering/20260430-m9-eval-system/codex-review-low1.md:660:/bin/zsh -lc 'rg -n "LOW-1|RoleEval|Kant|biographical|MCQ|HIGH|MEDIUM|LOW" .steering/20260430-m9-eval-system/codex-review.md' in /Users/johnd/ERRE-Sand Box
.steering/20260430-m9-eval-system/codex-review-low1.md:663:63:| Golden baseline | **Hybrid**: 200 turn fixed stimulus battery (Wachsmuth Toulmin 30 / ToM info-asymmetric chashitsu 20 / RoleEval-adapted Kant biographical MCQ 10 / persona-conditional moral dilemma 10 = 70 stimuli × 3 cycles, last cycle truncated to 10 turns) + 300 turn natural dialog from existing scheduler (peripatos / chashitsu / agora / garden mode transitions). Ratio 200/300 is **default; P3b pilot run 50 turn each will tune empirically**, recorded in blockers.md. |
.steering/20260430-m9-eval-system/codex-review-low1.md:675:507:    34	| **Golden baseline 形式** | 自然対話 500 turn × 5 run × 3 persona | **Hybrid: stimulus battery 200 turn (Wachsmuth/ToM/RoleEval/dilemma 70 種 × 3 巡) + 自然対話 300 turn** |
.steering/20260430-m9-eval-system/codex-review-low1.md:676:515:    42	| **stimulus battery** | 言及なし | 70 stimulus × 3 巡で Wachsmuth/ToM/RoleEval/dilemma を統制、bootstrap CI noise を抑制 |
.steering/20260430-m9-eval-system/codex-review-low1.md:678:670:    16	| P1b | reference corpus pickle 整備 (Kant 独+英訳 / Nietzsche / Rikyu / synthetic 4th) | Claude | Mac | CPU only | 2h | fixture test 緑 |
.steering/20260430-m9-eval-system/codex-review-low1.md:680:757:   103	  - RoleEval-adapted Kant biographical MCQ: 10
.steering/20260430-m9-eval-system/codex-review-low1.md:681:865:   211	- `reference_corpus/` — Kant 独+英訳、Nietzsche、Rikyu、synthetic 4th persona の
.steering/20260430-m9-eval-system/codex-review-low1.md:682:879:   225	- `personas/_synthetic_4th.yaml` — DB7 LOW-1 fixture (Big5 が 3 persona と直交する
.steering/20260430-m9-eval-system/codex-review-low1.md:683:893:   239	- `tests/test_evidence/test_golden_baseline.py` — synthetic 4th persona DB7 LOW-1 含む
.steering/20260430-m9-eval-system/codex-review-low1.md:685:1017:   358	### DB7 LOW-1 (synthetic 4th persona heldout fixture)
.steering/20260430-m9-eval-system/codex-review-low1.md:690:1087:   428	   - 70 stimulus × 3 巡 = 210 turn は Wachsmuth/ToM/RoleEval/dilemma の 4 系統に
.steering/20260430-m9-eval-system/codex-review-low1.md:706:1293:   149	## DB7 — Persona N=4 拡張時期: defer to M10 + synthetic heldout 4th in eval tests (LOW-1 反映)
.steering/20260430-m9-eval-system/codex-review-low1.md:707:1300:   156	  - codex LOW-1: eval pipeline が N=3 専用に overfit するのを防ぐため、synthetic 4th
.steering/20260430-m9-eval-system/codex-review-low1.md:711:1375:   231	    - Tier D: sparse manual (FActScore-adapted / 専門家 review / RoleEval-adapted MCQ)
.steering/20260430-m9-eval-system/codex-review-low1.md:720:1430:    10	### LOW-1: synthetic heldout 4th persona in eval tests
.steering/20260430-m9-eval-system/codex-review-low1.md:728:1584:    55	### RoleEval (Shen et al., 2024, arXiv:2312.16132)
.steering/20260430-m9-eval-system/codex-review-low1.md:729:1585:    56	- **What**: Role 知識 MCQ — relationships / abilities / experiences の多肢選択
.steering/20260430-m9-eval-system/codex-review-low1.md:730:1586:    57	- **限界**: MCQ 形式は recall のみ測定、生成評価ではない
.steering/20260430-m9-eval-system/codex-review-low1.md:731:1587:    58	- **ERRE 適用性**: 「Kant biographical MCQ」を pre-gate として cheap 自動化可。役立つが副次的
.steering/20260430-m9-eval-system/codex-review-low1.md:735:1675:   146	- **What**: 哲学者・立場・概念の MCQ
.steering/20260430-m9-eval-system/codex-review-low1.md:737:1677:   148	- **ERRE 適用性**: floor のみ (agent が base model より MCQ で *劣化* しないこと)
.steering/20260430-m9-eval-system/codex-review-low1.md:746:1841:   312	- `FActScore-adapted` against Kant/Nietzsche/Rikyu canonical corpus
.steering/20260430-m9-eval-system/codex-review-low1.md:747:1843:   314	- `RoleEval-adapted` biographical MCQ pre-gate
.steering/20260430-m9-eval-system/codex-review-low1.md:775:3833:### LOW-1: RoleEval wording may accidentally become Kant-only
.steering/20260430-m9-eval-system/codex-review-low1.md:776:3834:- **Finding**: The battery names “Kant biographical MCQ” while stimulus files are per persona.
.steering/20260430-m9-eval-system/codex-review-low1.md:777:3836:- **Recommendation**: Clarify persona-specific MCQs for Nietzsche/Rikyu, or label Kant-only MCQ as a non-comparative floor diagnostic.
.steering/20260430-m9-eval-system/codex-review-low1.md:802:3930:### LOW-1: RoleEval wording may accidentally become Kant-only
.steering/20260430-m9-eval-system/codex-review-low1.md:803:3931:- **Finding**: The battery names “Kant biographical MCQ” while stimulus files are per persona.
.steering/20260430-m9-eval-system/codex-review-low1.md:804:3933:- **Recommendation**: Clarify persona-specific MCQs for Nietzsche/Rikyu, or label Kant-only MCQ as a non-comparative floor diagnostic.
.steering/20260430-m9-eval-system/codex-review-low1.md:828:   116	  - RoleEval-adapted Kant biographical MCQ: 10
.steering/20260430-m9-eval-system/codex-review-low1.md:879:   167	  full cycle で実行** できることを synthetic stimulus + mock LLM で確認
.steering/20260430-m9-eval-system/codex-review-low1.md:910:   265	- `reference_corpus/` — Kant 独+英訳、Nietzsche、Rikyu、synthetic 4th persona の
.steering/20260430-m9-eval-system/codex-review-low1.md:924:   279	- `personas/_synthetic_4th.yaml` — DB7 LOW-1 fixture (Big5 が 3 persona と直交する
.steering/20260430-m9-eval-system/codex-review-low1.md:938:   293	- `tests/test_evidence/test_golden_baseline.py` — synthetic 4th persona DB7 LOW-1 含む
.steering/20260430-m9-eval-system/codex-review-low1.md:990:   492	   - 70 stimulus × 3 巡 = 210 turn は Wachsmuth/ToM/RoleEval/dilemma の 4 系統に
.steering/20260430-m9-eval-system/codex-review-low1.md:1003:   416	3. **Bootstrap CI shape**: 既知分布 (synthetic Vendi / ICC / Burrows triple) で
.steering/20260430-m9-eval-system/codex-review-low1.md:1009:   422	### DB7 LOW-1 (synthetic 4th persona heldout fixture)
.steering/20260430-m9-eval-system/codex-review-low1.md:1011:   424	- `personas/_synthetic_4th.yaml`: Big5 が 3 既存 persona と直交する架空 thinker
.steering/20260430-m9-eval-system/codex-review-low1.md:1017:   430	- `test_tier_a/`: 5 metric が synthetic + 4th persona heldout で NaN/crash 無く計算、
.steering/20260430-m9-eval-system/codex-review-low1.md:1451:/bin/zsh -lc "test -f personas/_synthetic_4th.yaml && sed -n '1,220p' personas/_synthetic_4th.yaml || true" in /Users/johnd/ERRE-Sand Box
.steering/20260430-m9-eval-system/codex-review-low1.md:1475:`golden/` と `evidence/` はまだ存在しておらず、P2a で初めて stimulus YAML を作る段階です。`personas/_synthetic_4th.yaml` も未作成なので、4th persona は設計だけが先行している状態です。
.steering/20260430-m9-eval-system/codex-review-low1.md:1479:# Codex independent review — LOW-1 RoleEval wording 決着 (P2a 着手直前)
.steering/20260430-m9-eval-system/codex-review-low1.md:1488:  **LOW-1 (RoleEval wording) のみ defer**、本セッション冒頭で決着が必要
.steering/20260430-m9-eval-system/codex-review-low1.md:1490:## レビューしてほしい判断: LOW-1 RoleEval wording
.steering/20260430-m9-eval-system/codex-review-low1.md:1498:  - RoleEval-adapted Kant biographical MCQ: 10  ← LOW-1 該当
.steering/20260430-m9-eval-system/codex-review-low1.md:1505:"RoleEval-adapted **Kant** biographical MCQ" のままでは Nietzsche / Rikyū 用 YAML が
.steering/20260430-m9-eval-system/codex-review-low1.md:1508:- **Option A**: 各 persona に biographical MCQ 10 問ずつ起草 (Kant / Nietzsche / Rikyū それぞれの
.steering/20260430-m9-eval-system/codex-review-low1.md:1510:- **Option B**: Kant biographical MCQ は Kant のみ、Nietzsche / Rikyū は別の floor diagnostic
.steering/20260430-m9-eval-system/codex-review-low1.md:1512:- **Option C**: RoleEval を全廃し Wachsmuth/ToM/dilemma の 60 stimulus × 3.5 巡で 210 turn 構成
.steering/20260430-m9-eval-system/codex-review-low1.md:1522:| persona-factuality dimension | ◎ 全 persona | △ Kant のみ | ✗ 完全消失 |
.steering/20260430-m9-eval-system/codex-review-low1.md:1523:| Rikyū MCQ 起草難度 | △ legend 多、attested fact は 5-7 件確保可 | ○ 不要 | ◎ 不要 |
.steering/20260430-m9-eval-system/codex-review-low1.md:1524:| Nietzsche MCQ 起草難度 | ○ Basel 1879 / Sils Maria / Overbeck 書簡で十分 | ○ 不要 | ◎ 不要 |
.steering/20260430-m9-eval-system/codex-review-low1.md:1525:| drafting 工数 | +1.5h (30 MCQ) | ≈同等 | -0.5h |
.steering/20260430-m9-eval-system/codex-review-low1.md:1526:| 後続 m9-eval-corpus で再 open 余地 | ◎ MCQ pool 別途精緻化可 | △ asymmetry 固定 | ✗ battery 再設計要 |
.steering/20260430-m9-eval-system/codex-review-low1.md:1529:1. **persona-factuality は 4 軸の 1 つ** (argumentation / ToM / persona-factuality / moral disposition) —
.steering/20260430-m9-eval-system/codex-review-low1.md:1530:   RoleEval を切ると "persona knows itself" の dimension が消え、style / argumentation /
.steering/20260430-m9-eval-system/codex-review-low1.md:1534:3. **Rikyū MCQ 起草実現可能** — 利休道歌構造 / 待庵物理寸法 / 北野大茶湯 1587 / Hideyoshi 確執 /
.steering/20260430-m9-eval-system/codex-review-low1.md:1536:4. **MCQ accuracy の cross-persona 絶対比較が無意味化する弱点** は ME-1 ADR の base model
.steering/20260430-m9-eval-system/codex-review-low1.md:1543:2. **A/B/C 以外の Option D が存在するか?** (例: Kant 用 MCQ 10 を全 persona 共通の "general
.steering/20260430-m9-eval-system/codex-review-low1.md:1544:   philosophical attribution" MCQ に置き換え、persona-factuality を sacrifice せずに per-persona
.steering/20260430-m9-eval-system/codex-review-low1.md:1546:3. **Option A 採択時の落とし穴** — biographical MCQ の category 設計、distractor 設計、
.steering/20260430-m9-eval-system/codex-review-low1.md:1547:   factual recall の信頼性確保で見落としそうな点 (例: persona prompt が "I am Kant" と
.steering/20260430-m9-eval-system/codex-review-low1.md:1551:5. **DB7 LOW-1 (synthetic 4th persona heldout fixture) との整合** — 4th persona 用 MCQ をどう
.steering/20260430-m9-eval-system/codex-review-low1.md:1552:   設計するか (Claude は本セッションで 3 persona の MCQ のみ起草予定、4th は P2c の test 範囲)
.steering/20260430-m9-eval-system/codex-review-low1.md:1618:# Codex independent review — LOW-1 RoleEval wording 決着 (P2a 着手直前)
.steering/20260430-m9-eval-system/codex-review-low1.md:1627:  **LOW-1 (RoleEval wording) のみ defer**、本セッション冒頭で決着が必要
.steering/20260430-m9-eval-system/codex-review-low1.md:1629:## レビューしてほしい判断: LOW-1 RoleEval wording
.steering/20260430-m9-eval-system/codex-review-low1.md:1637:  - RoleEval-adapted Kant biographical MCQ: 10  ← LOW-1 該当
.steering/20260430-m9-eval-system/codex-review-low1.md:1644:"RoleEval-adapted **Kant** biographical MCQ" のままでは Nietzsche / Rikyū 用 YAML が
.steering/20260430-m9-eval-system/codex-review-low1.md:1647:- **Option A**: 各 persona に biographical MCQ 10 問ずつ起草 (Kant / Nietzsche / Rikyū それぞれの
.steering/20260430-m9-eval-system/codex-review-low1.md:1649:- **Option B**: Kant biographical MCQ は Kant のみ、Nietzsche / Rikyū は別の floor diagnostic
.steering/20260430-m9-eval-system/codex-review-low1.md:1651:- **Option C**: RoleEval を全廃し Wachsmuth/ToM/dilemma の 60 stimulus × 3.5 巡で 210 turn 構成
.steering/20260430-m9-eval-system/codex-review-low1.md:1661:| persona-factuality dimension | ◎ 全 persona | △ Kant のみ | ✗ 完全消失 |
.steering/20260430-m9-eval-system/codex-review-low1.md:1662:| Rikyū MCQ 起草難度 | △ legend 多、attested fact は 5-7 件確保可 | ○ 不要 | ◎ 不要 |
.steering/20260430-m9-eval-system/codex-review-low1.md:1663:| Nietzsche MCQ 起草難度 | ○ Basel 1879 / Sils Maria / Overbeck 書簡で十分 | ○ 不要 | ◎ 不要 |
.steering/20260430-m9-eval-system/codex-review-low1.md:1664:| drafting 工数 | +1.5h (30 MCQ) | ≈同等 | -0.5h |
.steering/20260430-m9-eval-system/codex-review-low1.md:1665:| 後続 m9-eval-corpus で再 open 余地 | ◎ MCQ pool 別途精緻化可 | △ asymmetry 固定 | ✗ battery 再設計要 |
.steering/20260430-m9-eval-system/codex-review-low1.md:1668:1. **persona-factuality は 4 軸の 1 つ** (argumentation / ToM / persona-factuality / moral disposition) —
.steering/20260430-m9-eval-system/codex-review-low1.md:1669:   RoleEval を切ると "persona knows itself" の dimension が消え、style / argumentation /
.steering/20260430-m9-eval-system/codex-review-low1.md:1673:3. **Rikyū MCQ 起草実現可能** — 利休道歌構造 / 待庵物理寸法 / 北野大茶湯 1587 / Hideyoshi 確執 /
.steering/20260430-m9-eval-system/codex-review-low1.md:1675:4. **MCQ accuracy の cross-persona 絶対比較が無意味化する弱点** は ME-1 ADR の base model
.steering/20260430-m9-eval-system/codex-review-low1.md:1682:2. **A/B/C 以外の Option D が存在するか?** (例: Kant 用 MCQ 10 を全 persona 共通の "general
.steering/20260430-m9-eval-system/codex-review-low1.md:1683:   philosophical attribution" MCQ に置き換え、persona-factuality を sacrifice せずに per-persona
.steering/20260430-m9-eval-system/codex-review-low1.md:1685:3. **Option A 採択時の落とし穴** — biographical MCQ の category 設計、distractor 設計、
.steering/20260430-m9-eval-system/codex-review-low1.md:1686:   factual recall の信頼性確保で見落としそうな点 (例: persona prompt が "I am Kant" と
.steering/20260430-m9-eval-system/codex-review-low1.md:1690:5. **DB7 LOW-1 (synthetic 4th persona heldout fixture) との整合** — 4th persona 用 MCQ をどう
.steering/20260430-m9-eval-system/codex-review-low1.md:1691:   設計するか (Claude は本セッションで 3 persona の MCQ のみ起草予定、4th は P2c の test 範囲)
.steering/20260430-m9-eval-system/codex-review-low1.md:1834:まず設計側の LOW-1 周辺と ADR を読みます。次に persona YAML の `primary_corpus_refs` と factual basis を確認して、A が本当に成立するかを切り分けます。
.steering/20260430-m9-eval-system/codex-review-low1.md:1847:/bin/zsh -lc 'rg -n "stimulus|RoleEval|MCQ|synthetic_4th|4th|heldout|P2a|P2c|P3a" .steering/20260430-m9-eval-system/tasklist.md .steering/20260430-m9-eval-system/requirement.md' in /Users/johnd/ERRE-Sand Box
.steering/20260430-m9-eval-system/codex-review-low1.md:1851:.steering/20260430-m9-eval-system/tasklist.md:95:        4th persona heldout (38 unit test 全 PASS):
.steering/20260430-m9-eval-system/codex-review-low1.md:1852:.steering/20260430-m9-eval-system/tasklist.md:99:          synthetic 4th)
.steering/20260430-m9-eval-system/codex-review-low1.md:1853:.steering/20260430-m9-eval-system/tasklist.md:124:        (Kant de / Nietzsche de / Rikyu ja / synthetic_4th de+ja)、ME-6
.steering/20260430-m9-eval-system/codex-review-low1.md:1854:.steering/20260430-m9-eval-system/tasklist.md:142:  - [x] synthetic 4th persona function-word vector (de + ja の 2 言語、
.steering/20260430-m9-eval-system/codex-review-low1.md:1855:.steering/20260430-m9-eval-system/tasklist.md:161:    - [x] synthetic_4th profile == background_mean (de + ja 両方、
.steering/20260430-m9-eval-system/codex-review-low1.md:1859:.steering/20260430-m9-eval-system/tasklist.md:183:  - [ ] RoleEval-adapted MCQ 10 stimulus (LOW-1 defer 解消後の方針反映)
.steering/20260430-m9-eval-system/codex-review-low1.md:1863:.steering/20260430-m9-eval-system/tasklist.md:194:    - [ ] `test_one_stimulus_cycle_dryrun` (synthetic stimulus + mock LLM)
.steering/20260430-m9-eval-system/codex-review-low1.md:1865:.steering/20260430-m9-eval-system/tasklist.md:197:    - [ ] DB7 LOW-1 synthetic 4th persona fixture も含める
.steering/20260430-m9-eval-system/codex-review-low1.md:1870:.steering/20260430-m9-eval-system/tasklist.md:277:- LOW-1 RoleEval wording: P2a 着手時に option A/B/C 確定
.steering/20260430-m9-eval-system/codex-review-low1.md:1908:   183	  - [ ] RoleEval-adapted MCQ 10 stimulus (LOW-1 defer 解消後の方針反映)
.steering/20260430-m9-eval-system/codex-review-low1.md:1919:   194	    - [ ] `test_one_stimulus_cycle_dryrun` (synthetic stimulus + mock LLM)
.steering/20260430-m9-eval-system/codex-review-low1.md:1922:   197	    - [ ] DB7 LOW-1 synthetic 4th persona fixture も含める
.steering/20260430-m9-eval-system/codex-review-low1.md:2082:   100	  - persona_id: synthetic_4th
.steering/20260430-m9-eval-system/codex-review-low1.md:2084:   102	    source: "Synthetic — DB7 LOW-1 heldout fixture"
.steering/20260430-m9-eval-system/codex-review-low1.md:2095:   113	      DB7 LOW-1 heldout 4th persona used to detect 3-persona memorisation.
.steering/20260430-m9-eval-system/codex-review-low1.md:2096:   114	      profile_freq is set to the German background mean so the synthetic
.steering/20260430-m9-eval-system/codex-review-low1.md:2100:   118	  - persona_id: synthetic_4th
.steering/20260430-m9-eval-system/codex-review-low1.md:2102:   120	    source: "Synthetic — DB7 LOW-1 heldout fixture (Japanese mirror)"
.steering/20260430-m9-eval-system/codex-review-low1.md:2113:   131	      Japanese mirror of the synthetic 4th heldout. profile_freq equals
.steering/20260430-m9-eval-system/codex-review-low1.md:2116:   134	      computed from the single-corpus chunk distribution; the synthetic
.steering/20260430-m9-eval-system/codex-review-low1.md:2136:   115	    assert len(entries) >= 4  # 3 PD personas + at least one synthetic_4th
.steering/20260430-m9-eval-system/codex-review-low1.md:2178:   157	# --- synthetic_4th = background mean (DB7 LOW-1) -------------------------
.steering/20260430-m9-eval-system/codex-review-low1.md:2181:   160	def test_synthetic_4th_de_profile_equals_background_mean() -> None:
.steering/20260430-m9-eval-system/codex-review-low1.md:2182:   161	    ref = load_reference("synthetic_4th", "de")
.steering/20260430-m9-eval-system/codex-review-low1.md:2186:   165	def test_synthetic_4th_ja_profile_equals_background_mean() -> None:
.steering/20260430-m9-eval-system/codex-review-low1.md:2187:   166	    ref = load_reference("synthetic_4th", "ja")
.steering/20260430-m9-eval-system/codex-review-low1.md:2230:   194	    personas_de["synthetic_4th"] = {
.steering/20260430-m9-eval-system/codex-review-low1.md:2252:   216	    personas_ja["synthetic_4th"] = {
.steering/20260430-m9-eval-system/codex-review-low1.md:2274:    10	### LOW-1: synthetic heldout 4th persona in eval tests
.steering/20260430-m9-eval-system/codex-review-low1.md:2276:    12	- **defer 先**: M9-eval-system (eval test fixture として synthetic 4th persona を含める)
.steering/20260430-m9-eval-system/codex-review-low1.md:2277:    13	- **reopen 条件**: eval pipeline test で synthetic 4th が機能不全
.steering/20260430-m9-eval-system/codex-review-low1.md:2306:   149	## DB7 — Persona N=4 拡張時期: defer to M10 + synthetic heldout 4th in eval tests (LOW-1 反映)
.steering/20260430-m9-eval-system/codex-review-low1.md:2313:   156	  - codex LOW-1: eval pipeline が N=3 専用に overfit するのを防ぐため、synthetic 4th
.steering/20260430-m9-eval-system/codex-review-low1.md:2318:   161	  - 完全 defer (synthetic も含めない): eval pipeline overfit リスク
.steering/20260430-m9-eval-system/codex-review-low1.md:2320:   163	  - eval pipeline test に synthetic persona fixture 追加
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:1:# Codex independent review — LOW-1 RoleEval wording 決着 (P2a 着手直前)
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:10:  **LOW-1 (RoleEval wording) のみ defer**、本セッション冒頭で決着が必要
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:12:## レビューしてほしい判断: LOW-1 RoleEval wording
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:20:  - RoleEval-adapted Kant biographical MCQ: 10  ← LOW-1 該当
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:27:"RoleEval-adapted **Kant** biographical MCQ" のままでは Nietzsche / Rikyū 用 YAML が
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:30:- **Option A**: 各 persona に biographical MCQ 10 問ずつ起草 (Kant / Nietzsche / Rikyū それぞれの
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:32:- **Option B**: Kant biographical MCQ は Kant のみ、Nietzsche / Rikyū は別の floor diagnostic
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:34:- **Option C**: RoleEval を全廃し Wachsmuth/ToM/dilemma の 60 stimulus × 3.5 巡で 210 turn 構成
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:44:| persona-factuality dimension | ◎ 全 persona | △ Kant のみ | ✗ 完全消失 |
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:45:| Rikyū MCQ 起草難度 | △ legend 多、attested fact は 5-7 件確保可 | ○ 不要 | ◎ 不要 |
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:46:| Nietzsche MCQ 起草難度 | ○ Basel 1879 / Sils Maria / Overbeck 書簡で十分 | ○ 不要 | ◎ 不要 |
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:47:| drafting 工数 | +1.5h (30 MCQ) | ≈同等 | -0.5h |
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:48:| 後続 m9-eval-corpus で再 open 余地 | ◎ MCQ pool 別途精緻化可 | △ asymmetry 固定 | ✗ battery 再設計要 |
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:51:1. **persona-factuality は 4 軸の 1 つ** (argumentation / ToM / persona-factuality / moral disposition) —
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:52:   RoleEval を切ると "persona knows itself" の dimension が消え、style / argumentation /
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:56:3. **Rikyū MCQ 起草実現可能** — 利休道歌構造 / 待庵物理寸法 / 北野大茶湯 1587 / Hideyoshi 確執 /
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:58:4. **MCQ accuracy の cross-persona 絶対比較が無意味化する弱点** は ME-1 ADR の base model
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:65:2. **A/B/C 以外の Option D が存在するか?** (例: Kant 用 MCQ 10 を全 persona 共通の "general
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:66:   philosophical attribution" MCQ に置き換え、persona-factuality を sacrifice せずに per-persona
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:68:3. **Option A 採択時の落とし穴** — biographical MCQ の category 設計、distractor 設計、
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:69:   factual recall の信頼性確保で見落としそうな点 (例: persona prompt が "I am Kant" と
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:73:5. **DB7 LOW-1 (synthetic 4th persona heldout fixture) との整合** — 4th persona 用 MCQ をどう
.steering/20260430-m9-eval-system/codex-review-prompt-low1.md:74:   設計するか (Claude は本セッションで 3 persona の MCQ のみ起草予定、4th は P2c の test 範囲)
.steering/20260430-m9-b-lora-execution-plan/design-v1.md:111:- M9-eval-system: Tier B-D (Vendi / Prometheus / FANToM / FActScore / 専門家 review) を切り出し
.steering/20260430-m9-eval-system/tasklist.md:94:  - [x] `tests/test_evidence/test_tier_a/` 5 metric ごとに synthetic +
.steering/20260430-m9-eval-system/tasklist.md:95:        4th persona heldout (38 unit test 全 PASS):
.steering/20260430-m9-eval-system/tasklist.md:99:          synthetic 4th)
.steering/20260430-m9-eval-system/tasklist.md:124:        (Kant de / Nietzsche de / Rikyu ja / synthetic_4th de+ja)、ME-6
.steering/20260430-m9-eval-system/tasklist.md:142:  - [x] synthetic 4th persona function-word vector (de + ja の 2 言語、
.steering/20260430-m9-eval-system/tasklist.md:161:    - [x] synthetic_4th profile == background_mean (de + ja 両方、
.steering/20260430-m9-eval-system/tasklist.md:183:  - [ ] RoleEval-adapted MCQ 10 stimulus (LOW-1 defer 解消後の方針反映)
.steering/20260430-m9-eval-system/tasklist.md:194:    - [ ] `test_one_stimulus_cycle_dryrun` (synthetic stimulus + mock LLM)
.steering/20260430-m9-eval-system/tasklist.md:197:    - [ ] DB7 LOW-1 synthetic 4th persona fixture も含める
.steering/20260430-m9-eval-system/tasklist.md:277:- LOW-1 RoleEval wording: P2a 着手時に option A/B/C 確定
.steering/20260430-m9-eval-system/blockers.md:11:### LOW-1: RoleEval wording — Kant-only か persona-specific か (Codex LOW-1)
.steering/20260430-m9-eval-system/blockers.md:14:  "RoleEval-adapted Kant biographical MCQ: 10" と書かれているが、stimulus YAML は
.steering/20260430-m9-eval-system/blockers.md:16:  MCQ が Kant biographical のままだと意味が成り立たない
.steering/20260430-m9-eval-system/blockers.md:18:  - **option A**: 各 persona に対し biographical MCQ を 10 問ずつ起草 (Nietzsche
.steering/20260430-m9-eval-system/blockers.md:19:    biographical MCQ / Rikyu 茶の湯 MCQ)
.steering/20260430-m9-eval-system/blockers.md:20:  - **option B**: Kant biographical MCQ は Kant のみで実施、他 2 persona は別の
.steering/20260430-m9-eval-system/blockers.md:22:  - **option C**: RoleEval を全廃し Wachsmuth/ToM/dilemma の 60 stimulus × 3.5 巡で
.steering/20260430-m9-eval-system/blockers.md:137:| LOW-1 RoleEval wording | option A/B/C 確定 | P2a stimulus 起草 |
.steering/20260430-m9-eval-system/design-v1.md:145:- `tests/test_eval/fixtures/synthetic_4th_persona.yaml` — DB7 LOW-1 反映
.steering/20260430-m9-eval-system/design-v1.md:240:### DB7 LOW-1 (synthetic 4th persona heldout fixture)
.steering/20260430-m9-eval-system/design-v1.md:242:- `fixtures/synthetic_4th_persona.yaml`: Big5 が 3 既存 persona と直交する架空
.steering/20260430-m9-eval-system/design-v1.md:249:- `test_tier_a.py`: 5 metric が synthetic + 4th persona heldout fixture で
.steering/20260430-m9-eval-system/codex-review.md:63:| Golden baseline | **Hybrid**: 200 turn fixed stimulus battery (Wachsmuth Toulmin 30 / ToM info-asymmetric chashitsu 20 / RoleEval-adapted Kant biographical MCQ 10 / persona-conditional moral dilemma 10 = 70 stimuli × 3 cycles, last cycle truncated to 10 turns) + 300 turn natural dialog from existing scheduler (peripatos / chashitsu / agora / garden mode transitions). Ratio 200/300 is **default; P3b pilot run 50 turn each will tune empirically**, recorded in blockers.md. |
.steering/20260430-m9-eval-system/codex-review.md:507:    34	| **Golden baseline 形式** | 自然対話 500 turn × 5 run × 3 persona | **Hybrid: stimulus battery 200 turn (Wachsmuth/ToM/RoleEval/dilemma 70 種 × 3 巡) + 自然対話 300 turn** |
.steering/20260430-m9-eval-system/codex-review.md:515:    42	| **stimulus battery** | 言及なし | 70 stimulus × 3 巡で Wachsmuth/ToM/RoleEval/dilemma を統制、bootstrap CI noise を抑制 |
.steering/20260430-m9-eval-system/codex-review.md:670:    16	| P1b | reference corpus pickle 整備 (Kant 独+英訳 / Nietzsche / Rikyu / synthetic 4th) | Claude | Mac | CPU only | 2h | fixture test 緑 |
.steering/20260430-m9-eval-system/codex-review.md:757:   103	  - RoleEval-adapted Kant biographical MCQ: 10
.steering/20260430-m9-eval-system/codex-review.md:865:   211	- `reference_corpus/` — Kant 独+英訳、Nietzsche、Rikyu、synthetic 4th persona の
.steering/20260430-m9-eval-system/codex-review.md:879:   225	- `personas/_synthetic_4th.yaml` — DB7 LOW-1 fixture (Big5 が 3 persona と直交する
.steering/20260430-m9-eval-system/codex-review.md:893:   239	- `tests/test_evidence/test_golden_baseline.py` — synthetic 4th persona DB7 LOW-1 含む
.steering/20260430-m9-eval-system/codex-review.md:998:   339	  `ipip_neo_short` のみ optional 追加。`_synthetic_4th.yaml` も同じ schema
.steering/20260430-m9-eval-system/codex-review.md:1013:   354	3. **Bootstrap CI shape**: 既知分布 (synthetic Vendi / ICC / Burrows triple) で
.steering/20260430-m9-eval-system/codex-review.md:1017:   358	### DB7 LOW-1 (synthetic 4th persona heldout fixture)
.steering/20260430-m9-eval-system/codex-review.md:1019:   360	- `personas/_synthetic_4th.yaml`: Big5 が 3 既存 persona と直交する架空 thinker
.steering/20260430-m9-eval-system/codex-review.md:1025:   366	- `test_tier_a/`: 5 metric が synthetic + 4th persona heldout で NaN/crash 無く計算、
.steering/20260430-m9-eval-system/codex-review.md:1087:   428	   - 70 stimulus × 3 巡 = 210 turn は Wachsmuth/ToM/RoleEval/dilemma の 4 系統に
.steering/20260430-m9-eval-system/codex-review.md:1293:   149	## DB7 — Persona N=4 拡張時期: defer to M10 + synthetic heldout 4th in eval tests (LOW-1 反映)
.steering/20260430-m9-eval-system/codex-review.md:1300:   156	  - codex LOW-1: eval pipeline が N=3 専用に overfit するのを防ぐため、synthetic 4th
.steering/20260430-m9-eval-system/codex-review.md:1305:   161	  - 完全 defer (synthetic も含めない): eval pipeline overfit リスク
.steering/20260430-m9-eval-system/codex-review.md:1307:   163	  - eval pipeline test に synthetic persona fixture 追加
.steering/20260430-m9-eval-system/codex-review.md:1375:   231	    - Tier D: sparse manual (FActScore-adapted / 専門家 review / RoleEval-adapted MCQ)
.steering/20260430-m9-eval-system/codex-review.md:1430:    10	### LOW-1: synthetic heldout 4th persona in eval tests
.steering/20260430-m9-eval-system/codex-review.md:1432:    12	- **defer 先**: M9-eval-system (eval test fixture として synthetic 4th persona を含める)
.steering/20260430-m9-eval-system/codex-review.md:1433:    13	- **reopen 条件**: eval pipeline test で synthetic 4th が機能不全
.steering/20260430-m9-eval-system/codex-review.md:1584:    55	### RoleEval (Shen et al., 2024, arXiv:2312.16132)
.steering/20260430-m9-eval-system/codex-review.md:1585:    56	- **What**: Role 知識 MCQ — relationships / abilities / experiences の多肢選択
.steering/20260430-m9-eval-system/codex-review.md:1586:    57	- **限界**: MCQ 形式は recall のみ測定、生成評価ではない
.steering/20260430-m9-eval-system/codex-review.md:1587:    58	- **ERRE 適用性**: 「Kant biographical MCQ」を pre-gate として cheap 自動化可。役立つが副次的
.steering/20260430-m9-eval-system/codex-review.md:1675:   146	- **What**: 哲学者・立場・概念の MCQ
.steering/20260430-m9-eval-system/codex-review.md:1677:   148	- **ERRE 適用性**: floor のみ (agent が base model より MCQ で *劣化* しないこと)
.steering/20260430-m9-eval-system/codex-review.md:1687:   158	### FActScore (Min et al., EMNLP 2023, arXiv:2305.14251)
.steering/20260430-m9-eval-system/codex-review.md:1689:   160	- **限界**: factual claim 用、normative/philosophical claim 不対応
.steering/20260430-m9-eval-system/codex-review.md:1696:   167	  factuality / redundancy
.steering/20260430-m9-eval-system/codex-review.md:1810:   281	| **F4 Philosophical depth** | Wachsmuth Toulmin rubric + LLM-judge | ROSCOE (informativeness) + FActScore-adapted |
.steering/20260430-m9-eval-system/codex-review.md:1841:   312	- `FActScore-adapted` against Kant/Nietzsche/Rikyu canonical corpus
.steering/20260430-m9-eval-system/codex-review.md:1843:   314	- `RoleEval-adapted` biographical MCQ pre-gate
.steering/20260430-m9-eval-system/codex-review.md:1908:   374	- [FActScore arXiv:2305.14251](https://arxiv.org/abs/2305.14251)
.steering/20260430-m9-eval-system/codex-review.md:1926:   392	  ただし「PhilEval / PhilBench」は subagent が「flag for verification」と明示
.steering/20260430-m9-eval-system/codex-review.md:3833:### LOW-1: RoleEval wording may accidentally become Kant-only
.steering/20260430-m9-eval-system/codex-review.md:3834:- **Finding**: The battery names “Kant biographical MCQ” while stimulus files are per persona.
.steering/20260430-m9-eval-system/codex-review.md:3836:- **Recommendation**: Clarify persona-specific MCQs for Nietzsche/Rikyu, or label Kant-only MCQ as a non-comparative floor diagnostic.
.steering/20260430-m9-eval-system/codex-review.md:3930:### LOW-1: RoleEval wording may accidentally become Kant-only
.steering/20260430-m9-eval-system/codex-review.md:3931:- **Finding**: The battery names “Kant biographical MCQ” while stimulus files are per persona.
.steering/20260430-m9-eval-system/codex-review.md:3933:- **Recommendation**: Clarify persona-specific MCQs for Nietzsche/Rikyu, or label Kant-only MCQ as a non-comparative floor diagnostic.
.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:55:### RoleEval (Shen et al., 2024, arXiv:2312.16132)
.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:56:- **What**: Role 知識 MCQ — relationships / abilities / experiences の多肢選択
.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:57:- **限界**: MCQ 形式は recall のみ測定、生成評価ではない
.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:58:- **ERRE 適用性**: 「Kant biographical MCQ」を pre-gate として cheap 自動化可。役立つが副次的
.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:146:- **What**: 哲学者・立場・概念の MCQ
.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:148:- **ERRE 適用性**: floor のみ (agent が base model より MCQ で *劣化* しないこと)
.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:158:### FActScore (Min et al., EMNLP 2023, arXiv:2305.14251)
.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:160:- **限界**: factual claim 用、normative/philosophical claim 不対応
.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:167:  factuality / redundancy
.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:281:| **F4 Philosophical depth** | Wachsmuth Toulmin rubric + LLM-judge | ROSCOE (informativeness) + FActScore-adapted |
.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:312:- `FActScore-adapted` against Kant/Nietzsche/Rikyu canonical corpus
.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:314:- `RoleEval-adapted` biographical MCQ pre-gate
.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:374:- [FActScore arXiv:2305.14251](https://arxiv.org/abs/2305.14251)
.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:392:  ただし「PhilEval / PhilBench」は subagent が「flag for verification」と明示

codex
### Verdict

Adopt Option A

### Findings

#### MEDIUM-1: Option A is妥当だが、construct 名を “Kant biographical” から persona-specific に直す必要がある
- **観察 / 根拠**: Claude の 4 軸維持と CI 交絡回避の論拠は正しい。Option B は persona ごとに stimulus type mass が変わり、Option C は persona-factuality 軸を消す。現設計の問題は `RoleEval-adapted Kant biographical MCQ` という wording。
- **推奨 action**: `design-final.md` を `RoleEval-adapted persona-specific biographical / thought-history MCQ: 10` に変更。`blockers.md` LOW-1 は Option A close、ただし score は “within-persona floor diagnostic” と明記し、cross-persona absolute accuracy を DB9 比較指標にしない。

#### MEDIUM-2: Rikyū 10 問は可能だが、current YAML だけでは source strength が不足する
- **観察 / 根拠**: `rikyu.yaml` は fact / legend / speculative が混在し、現 P1b corpus も 5 利休道歌のみ。Claude の Rikyū 実現性論拠は方向として妥当だが、待庵寸法・nijiriguchi 等は legend / later tradition と混ざりやすい。
- **推奨 action**: 各 MCQ に `source_ref`, `source_grade: fact|secondary|legend`, `category`, `ambiguity_note` を必須化。scored accuracy は fact / strong secondary のみ。legend は stimulus として使っても、factuality score から除外。

#### MEDIUM-3: ME-1 base model control は絶対比較問題を完全には吸収しない
- **観察 / 根拠**: `Δaccuracy = persona_run - base_control` は同一 item 内の persona conditioning 効果を見るには有効。ただし Kant / Nietzsche / Rikyū は item difficulty、pretraining exposure、言語、曖昧性が違うため、Δ同士の横比較は psychometric equating されない。
- **推奨 action**: base control は persona ごとの同一 MCQ item で測る。報告は `per_item_delta` と persona 内 summary に留め、persona 間 ranking には使わない。必要なら後続 `m9-eval-corpus` で item difficulty / DIF を扱う。

#### MEDIUM-4: MCQ item schema と distractor 設計を先に固定しないと、hallucination と prompt recall が混ざる
- **観察 / 根拠**: persona prompt に含まれる事実を問うと “historical factual recall” ではなく “prompt consistency” になる。MCQ distractor が時代・カテゴリ・言語で不均衡だと、モデルは知識でなく表層 cue で当てる。
- **推奨 action**: 10 問をカテゴリ均等化する。例: chronology 2、works/corpus 2、practice/cognitive habit 2、relationships/institutions 2、material/term 2。各 item に `present_in_persona_prompt: true|false` を持たせ、A-D forced choice、option order seeded shuffle、same-type plausible distractors を必須化。

#### LOW-1: Option D は存在するが、P2a の採択案としては A より弱い
- **観察 / 根拠**: 共通 “general philosophical attribution” MCQ は item equating しやすいが、測るものが persona self-knowledge から一般哲学 trivia に寄る。RoleEval の “role knowledge” 目的とはずれる。
- **推奨 action**: Option D は採用しない。必要なら後続で 2-3 個の shared calibration item として追加検討し、今回の 10 枠は Option A の persona-specific MCQ に使う。

#### MEDIUM-5: 3 巡反復では MCQ accuracy は first exposure のみ採点すべき
- **観察 / 根拠**: 70 stimulus × 3 巡は同一 MCQ が繰り返される可能性がある。2 巡目以降は自己出力や会話履歴による practice effect が入る。
- **推奨 action**: MCQ score は cycle 1 のみ primary。cycle 2/3 は stimulus として流してよいが `repeat_cycle > 1` を scoring exclude、または stem variant + option shuffle にする。

#### LOW-2: synthetic 4th persona は科学的 MCQ ではなく driver / schema fixture に限定する
- **観察 / 根拠**: DB7 は runtime N=4 を M10 defer し、M9 では eval pipeline の 3-persona overfit 防止が目的。現状 `personas/_synthetic_4th.yaml` は未作成で、reference corpus でも analytical background mean fixture。
- **推奨 action**: P2c では synthetic 4th 用の fake MCQ を `tests/fixtures` に置く場合のみ許可し、`fictional: true`, `scored: false` を付ける。`golden/stimulus/` の本番 3 persona MCQ とは分離。

### Open question

なし。LOW-1 は P2a 前に Option A で close すべきで、P3a-decide / P3 まで再 defer すると pilot ratio と 7500 turn baseline の解釈が後から崩れる。
hook: Stop
hook: Stop Completed
2026-04-30T15:57:33.860379Z ERROR codex_core::session: failed to record rollout items: thread 019ddf19-7399-7a80-a404-a9c94cc0aa4c not found
tokens used
109,448
### Verdict

Adopt Option A

### Findings

#### MEDIUM-1: Option A is妥当だが、construct 名を “Kant biographical” から persona-specific に直す必要がある
- **観察 / 根拠**: Claude の 4 軸維持と CI 交絡回避の論拠は正しい。Option B は persona ごとに stimulus type mass が変わり、Option C は persona-factuality 軸を消す。現設計の問題は `RoleEval-adapted Kant biographical MCQ` という wording。
- **推奨 action**: `design-final.md` を `RoleEval-adapted persona-specific biographical / thought-history MCQ: 10` に変更。`blockers.md` LOW-1 は Option A close、ただし score は “within-persona floor diagnostic” と明記し、cross-persona absolute accuracy を DB9 比較指標にしない。

#### MEDIUM-2: Rikyū 10 問は可能だが、current YAML だけでは source strength が不足する
- **観察 / 根拠**: `rikyu.yaml` は fact / legend / speculative が混在し、現 P1b corpus も 5 利休道歌のみ。Claude の Rikyū 実現性論拠は方向として妥当だが、待庵寸法・nijiriguchi 等は legend / later tradition と混ざりやすい。
- **推奨 action**: 各 MCQ に `source_ref`, `source_grade: fact|secondary|legend`, `category`, `ambiguity_note` を必須化。scored accuracy は fact / strong secondary のみ。legend は stimulus として使っても、factuality score から除外。

#### MEDIUM-3: ME-1 base model control は絶対比較問題を完全には吸収しない
- **観察 / 根拠**: `Δaccuracy = persona_run - base_control` は同一 item 内の persona conditioning 効果を見るには有効。ただし Kant / Nietzsche / Rikyū は item difficulty、pretraining exposure、言語、曖昧性が違うため、Δ同士の横比較は psychometric equating されない。
- **推奨 action**: base control は persona ごとの同一 MCQ item で測る。報告は `per_item_delta` と persona 内 summary に留め、persona 間 ranking には使わない。必要なら後続 `m9-eval-corpus` で item difficulty / DIF を扱う。

#### MEDIUM-4: MCQ item schema と distractor 設計を先に固定しないと、hallucination と prompt recall が混ざる
- **観察 / 根拠**: persona prompt に含まれる事実を問うと “historical factual recall” ではなく “prompt consistency” になる。MCQ distractor が時代・カテゴリ・言語で不均衡だと、モデルは知識でなく表層 cue で当てる。
- **推奨 action**: 10 問をカテゴリ均等化する。例: chronology 2、works/corpus 2、practice/cognitive habit 2、relationships/institutions 2、material/term 2。各 item に `present_in_persona_prompt: true|false` を持たせ、A-D forced choice、option order seeded shuffle、same-type plausible distractors を必須化。

#### LOW-1: Option D は存在するが、P2a の採択案としては A より弱い
- **観察 / 根拠**: 共通 “general philosophical attribution” MCQ は item equating しやすいが、測るものが persona self-knowledge から一般哲学 trivia に寄る。RoleEval の “role knowledge” 目的とはずれる。
- **推奨 action**: Option D は採用しない。必要なら後続で 2-3 個の shared calibration item として追加検討し、今回の 10 枠は Option A の persona-specific MCQ に使う。

#### MEDIUM-5: 3 巡反復では MCQ accuracy は first exposure のみ採点すべき
- **観察 / 根拠**: 70 stimulus × 3 巡は同一 MCQ が繰り返される可能性がある。2 巡目以降は自己出力や会話履歴による practice effect が入る。
- **推奨 action**: MCQ score は cycle 1 のみ primary。cycle 2/3 は stimulus として流してよいが `repeat_cycle > 1` を scoring exclude、または stem variant + option shuffle にする。

#### LOW-2: synthetic 4th persona は科学的 MCQ ではなく driver / schema fixture に限定する
- **観察 / 根拠**: DB7 は runtime N=4 を M10 defer し、M9 では eval pipeline の 3-persona overfit 防止が目的。現状 `personas/_synthetic_4th.yaml` は未作成で、reference corpus でも analytical background mean fixture。
- **推奨 action**: P2c では synthetic 4th 用の fake MCQ を `tests/fixtures` に置く場合のみ許可し、`fictional: true`, `scored: false` を付ける。`golden/stimulus/` の本番 3 persona MCQ とは分離。

### Open question

なし。LOW-1 は P2a 前に Option A で close すべきで、P3a-decide / P3 まで再 defer すると pilot ratio と 7500 turn baseline の解釈が後から崩れる。
