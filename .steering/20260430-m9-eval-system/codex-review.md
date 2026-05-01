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
session id: 019ddda1-a16a-7f01-8fbc-2bc4c080506c
--------
user
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

hook: SessionStart
hook: SessionStart Completed
hook: UserPromptSubmit
hook: UserPromptSubmit Completed
codex
I’ll use `$erre-workflow` for the review flow, then read only the five requested steering files with line numbers. I’ll avoid `design-v1.md` as requested and verify methodology/library claims against live sources where the design depends on them.
exec
/bin/zsh -lc "sed -n '1,220p' .agents/skills/erre-workflow/SKILL.md" in /Users/johnd/ERRE-Sand Box
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
The workflow skill only adds one review-side constraint here: no implementation and no subagents unless explicitly requested. I’m now collecting the requested file evidence with stable line numbers, then I’ll cross-check the statistical and DuckDB/systemd assumptions.
exec
/bin/zsh -lc "nl -ba docs/development-guidelines.md | sed -n '1,220p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
     1	# 開発ガイドライン
     2	
     3	## 1. コーディング規約
     4	
     5	### 命名規則
     6	- **変数・関数**: snake_case (`agent_state`, `dump_for_prompt()`)
     7	- **クラス**: PascalCase (`AgentState`, `MemoryStream`)
     8	- **定数**: UPPER_SNAKE_CASE (`DEFAULT_TEMPERATURE`, `MAX_AGENTS`)
     9	- **ファイル・モジュール**: snake_case (`ollama_adapter.py`)
    10	- **GDScript**: PascalCase (Godot 標準に従う)
    11	
    12	### 型ヒント
    13	- すべての関数に型ヒントを付与する
    14	- Pydantic v2 の `BaseModel` を積極的に活用
    15	- `from __future__ import annotations` を使用し、遅延評価を有効にする
    16	
    17	### コメント
    18	- **いつ書くか**: ロジックが自明でない場合、認知科学・論文への参照がある場合、ERRE 独自の設計判断の理由
    19	- **いつ書かないか**: 型ヒントやメソッド名で意図が明確な場合
    20	- **言語**: docstring は英語 (LLM ツール親和性優先)、インラインコメントは日英いずれも可
    21	
    22	### Lint / Format
    23	- ruff で lint + format を一元化
    24	- `pyproject.toml` の `[tool.ruff]` セクションで設定
    25	- pre-commit hook (commit 時) と GitHub Actions CI (push / PR 時) で
    26	  `uv run ruff check src tests` + `uv run ruff format --check src tests` を自動実行
    27	- 手動でも `uv run` で同コマンドを実行可能
    28	- 設定: `.pre-commit-config.yaml` (local hook、`uv run ruff` で uv.lock 固定版を呼び出す SSoT 構成) /
    29	  `.github/workflows/ci.yml` (lint / typecheck / test の 3 並列 jobs)
    30	
    31	### Python 固有
    32	- Python 3.11 を使用 (``.python-version`` で pin)
    33	- asyncio を基本とし、同期的な I/O ブロッキングは避ける
    34	- f-string を文字列フォーマットの既定とする
    35	
    36	## 2. Git ワークフロー
    37	
    38	### ブランチ戦略
    39	- **メインブランチ**: `main` (常にデプロイ可能な状態)
    40	- **作業ブランチ**: `[type]/[task-name]` 形式
    41	  - `feature/agent-cognition-cycle`
    42	  - `fix/memory-retrieval-ranking`
    43	  - `refactor/inference-adapter`
    44	  - `docs/architecture-update`
    45	  - `chore/ci-setup`
    46	
    47	### コミットメッセージ
    48	Conventional Commits 形式を採用:
    49	
    50	```
    51	[type]([scope]): [短い説明]
    52	
    53	- 変更内容 1
    54	- 変更内容 2
    55	
    56	Refs: .steering/[YYYYMMDD]-[task-name]/
    57	```
    58	
    59	**type**: feat, fix, refactor, docs, test, chore, ci
    60	**scope**: schemas, memory, cognition, inference, world, ui, godot, personas
    61	
    62	例:
    63	```
    64	feat(cognition): add DMN-inspired idle reflection window
    65	
    66	- peripatos/chashitsu 入室時に温度を上げた自由連想型内省を発火
    67	- importance 閾値未満でもトリガーされる ERRE 独自拡張
    68	
    69	Refs: .steering/20260420-reflection-window/
    70	```
    71	
    72	### PR
    73	- タイトル: Conventional Commits と同じ形式
    74	- 説明: 変更の背景・目的・テスト方法を記載
    75	- 個人プロジェクトのためレビュアー不要だが、Claude Code の `/review` を活用
    76	
    77	### タグ・リリース
    78	- Semantic Versioning: `v0.1.0` (スケルトン) → `v0.5.0` (3体MVP) → `v0.9.0` (RC) → `v1.0.0` (論文併発)
    79	- 各リリースで Zenodo DOI を自動発行
    80	- CITATION.cff で BibTeX を配信
    81	
    82	## 3. テスト方針
    83	
    84	### テストの種類
    85	
    86	| 種類 | 範囲 | フレームワーク | 実行頻度 |
    87	|---|---|---|---|
    88	| 単体テスト | 個々の関数・クラス | pytest | CI (push/PR、`pytest -m "not godot"`) + 手動 (`uv run pytest`) |
    89	| 統合テスト | モジュール間連携 (memory + cognition 等) | pytest-asyncio | CI (push/PR) + 手動 |
    90	| E2E テスト | 1体エージェントの認知サイクル完走 | pytest-asyncio | CI (push/PR) + 手動 |
    91	| 埋め込みプレフィックステスト | 検索/文書プレフィックスの正確性 | pytest | CI (push/PR) + 手動 |
    92	| Godot 連携テスト | `@pytest.mark.godot` 付与のテスト | pytest | 手動のみ (CI では `-m "not godot"` で deselect) |
    93	
    94	> **現状実装スナップショット (last verified 2026-04-28)**: pre-commit hook
    95	> (`.pre-commit-config.yaml`) と GitHub Actions CI (`.github/workflows/ci.yml`、
    96	> lint / typecheck / test の 3 並列 jobs) を導入済。Godot binary 必須テストは
    97	> `pyproject.toml` の `markers = ["godot: ..."]` 登録 + 対象テストへの
    98	> `@pytest.mark.godot` 付与で CI から `pytest -m "not godot"` により明示的に
    99	> deselect する policy。
   100	
   101	### テストの書き方
   102	- テストファイルは `tests/` 配下に `src/` のミラー構造で配置
   103	- `conftest.py` に共通フィクスチャ (AgentState のファクトリ、sqlite-vec の一時 DB 等)
   104	- 非同期テストは `@pytest.mark.asyncio` を使用
   105	- LLM 推論を伴うテストは mock で分離 (ただし統合テストでは実際の Ollama を使用可)
   106	
   107	### TDD の適用
   108	- **適用すべきケース**: schemas.py のバリデーション、memory/ の検索ロジック、ERRE モードの状態遷移
   109	- **適用しないケース**: LLM の出力に依存するテスト (非決定論的)、Godot シーンの描画、探索的プロトタイピング段階
   110	
   111	## 4. レビュー基準
   112	
   113	### 必須チェック (pre-commit / CI で自動実行、手動でも `uv run` で実行可)
   114	- [ ] `uv run ruff check src tests` が通る (pre-commit + CI lint job)
   115	- [ ] `uv run ruff format --check src tests` が通る (pre-commit + CI lint job)
   116	- [ ] `uv run mypy src` が通る (CI typecheck job)
   117	- [ ] `uv run pytest -m "not godot"` が通る (CI test job、Godot 連携除く)
   118	- [ ] 型ヒントが付与されている
   119	
   120	### 手動チェック (セルフレビュー / Claude Code `/review`)
   121	- [ ] テストが追加されている (新機能・バグ修正時)
   122	- [ ] 既存のテストを壊していない
   123	- [ ] 命名規則に従っている
   124	- [ ] 依存方向が正しい (`repository-structure.md` のレイヤー図参照)
   125	- [ ] GPL 依存を持ち込んでいない
   126	
   127	### 推奨チェック
   128	- [ ] エッジケースを考慮している
   129	- [ ] asyncio のデッドロック・リソースリークがない
   130	- [ ] VRAM 使用量への影響を考慮している (推論関連の変更時)
   131	
   132	## 5. パッケージ管理
   133	
   134	### uv の使用
   135	- `uv` を単一のパッケージ・環境・Python 管理ツールとして使用
   136	- `pyproject.toml` に依存を記述、`uv.lock` でロック
   137	- CI では `uv sync --frozen` で再現可能なインストール
   138	
   139	### 依存ライブラリの追加基準
   140	新しいライブラリを追加する前に確認:
   141	
   142	- [ ] 既存の依存で代替できないか?
   143	- [ ] ライセンスは Apache-2.0 / MIT / BSD と互換か? (GPL は本体に入れない)
   144	- [ ] メンテナンスが活発か? (直近 6 ヶ月以内にリリースがあるか)
   145	- [ ] セキュリティ脆弱性はないか?
   146	- [ ] 予算ゼロに抵触しないか? (有料ライブラリ・有料 API 依存は不可)
   147	
   148	## 6. リファクタリング指針
   149	
   150	- **いつリファクタリングすべきか**: 同じパターンが 3 箇所以上に現れたとき、モジュールの責務が曖昧になったとき
   151	- **どこまで踏み込むべきか**: 現在のタスクの範囲内。「ついでに直す」は 1 ファイル以内に留める
   152	- **リファクタリング前にやること**: テストの実行、変更前のスナップショット
   153	- **破壊と構築**: 必要なら大胆に壊して再構築する。ただしテストが通る状態を維持
   154	
   155	## 7. ドキュメンテーション
   156	
   157	### コード内ドキュメント
   158	- docstring は英語、Google スタイル
   159	- 公開 API (関数・クラス) には必ず docstring を付ける
   160	- 内部実装の詳細は docstring に書かず、必要ならインラインコメントで
   161	
   162	### プロジェクトドキュメント
   163	- `docs/` の永続ドキュメント: 日本語メイン
   164	- `README.md`: 英語主体、冒頭に「日本語」ジャンプリンク
   165	- MkDocs Material + mkdocstrings で API ドキュメント自動生成
   166	- mkdocs-static-i18n で JA/EN 言語スイッチャ
   167	
   168	### 作業記録
   169	- タスク単位の記録は `.steering/[YYYYMMDD]-[task-name]/` に配置
   170	- コミットメッセージで `.steering/` を `Refs:` として参照
   171	
   172	## 8. 禁止事項
   173	
   174	- GPL 依存ライブラリを `src/erre_sandbox/` に import する
   175	- クラウド LLM API を必須依存にする (予算ゼロ制約)
   176	- 著作権保護下のテキストをリポジトリに含める
   177	- `main` ブランチに直接 push する (作業ブランチ経由のみ)
   178	- テストを書かずに記憶検索ロジック・状態遷移ロジックを変更する
   179	- 埋め込みモデルのプレフィックス (検索クエリ: / 検索文書:) を検証テストなしに変更する

exec
/bin/zsh -lc "nl -ba .steering/20260430-m9-eval-system/design-comparison.md | sed -n '1,260p'" in /Users/johnd/ERRE-Sand Box
exec
/bin/zsh -lc "nl -ba .steering/20260430-m9-eval-system/design.md | sed -n '1,260p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
     1	# 設計案比較 — m9-eval-system
     2	
     3	`design-v1.md` (初回案) と再生成 v2 案 (現在の `design.md`) を比較。
     4	
     5	## v1 (初回案) の要旨
     6	
     7	DB5 物理分離を **別 Parquet file** で達成 (`raw_dialog/` と `metrics/` 配下を path 規約で
     8	分離)。Library は **pyarrow (I/O) + polars (分析)** の併用。LIWC は **Option C (spaCy +
     9	自前 dictionary、Empath seed)** で Big5 claim を IPIP-NEO 経路に集約。Golden baseline
    10	は **3 persona × 5 run × 500 turn の純自然対話** を新規 `GoldenBaselineOrchestrator`
    11	wrapper で採取。Tier C nightly は **asyncio scheduler + `ollama ps` polling +
    12	file-lock** で agent 停止時を mechanism 化。
    13	
    14	## v2 (再生成案) の要旨
    15	
    16	DB5 物理分離を **DuckDB 単 file の named schema (raw_dialog / metrics) + training-
    17	loader API の schema-guard** で達成、Parquet は二次的な export 形式に格下げ。
    18	Library は **DuckDB 単独** (pyarrow / polars 不要の 1-dependency)。LIWC は
    19	**Option D (Big5 claim 自体を放棄、IPIP-NEO self-report に一本化、Empath は Tier A
    20	diagnostic のみ)** で blockers.md の LIWC license defer を即時 close。Golden baseline
    21	は **fixed stimulus battery 200 turn + 自然対話 300 turn の hybrid**、既存
    22	`InMemoryDialogScheduler` に `golden_baseline_mode: bool` の minimum patch のみ
    23	(新規 wrapper 不採用)。Tier C nightly は **G-GEAR の systemd --user timer + flock**
    24	で実装 (Mac launchd → ssh trigger は補助案、必須でない)。Tier A 計算 timing は
    25	全 post-hoc (live inference 不負荷、DB6 厳守)。
    26	
    27	## 主要な差異
    28	
    29	| 観点 | v1 | v2 |
    30	|---|---|---|
    31	| **DB5 物理分離** | 別 Parquet file + path 規約 | DuckDB 単 file + named schema + training-loader API guard + CI grep gate |
    32	| **Library** | pyarrow + polars 併用 | DuckDB 単独 |
    33	| **LIWC alternative** | Option C (spaCy 自前 dict + Empath seed)、Big5 claim を IPIP-NEO に集約 | **Option D (LIWC 全廃)、Big5 を IPIP-NEO 自己申告のみに依拠、Empath は副次的** |
    34	| **Golden baseline 形式** | 自然対話 500 turn × 5 run × 3 persona | **Hybrid: stimulus battery 200 turn (Wachsmuth/ToM/RoleEval/dilemma 70 種 × 3 巡) + 自然対話 300 turn** |
    35	| **Orchestrator** | 新規 `GoldenBaselineOrchestrator` wrapper | 既存 `InMemoryDialogScheduler` に `golden_baseline_mode: bool` minimum patch、wrapper 新設なし |
    36	| **Tier A 計算 timing** | per-turn live (~50ms 制約) | 全 post-hoc per-run CLI (粒度は per-turn だが timing は post-hoc、live inference 不負荷) |
    37	| **Tier C nightly infra** | asyncio + `ollama ps` polling + file-lock | systemd --user timer (G-GEAR) + flock + nvidia-smi preflight |
    38	| **新規 file 数** | `eval/` 配下 ~16 file (parquet_io / tier_{a,b,c}/* / orchestrator / bootstrap / seeds.json + 5 CLI + 5 test + fixture) | `evidence/tier_{a,b,c}.py` 等 ~10 file (既存 `evidence/` pattern 踏襲、新 layer 不創設) |
    39	| **依存追加** | pyarrow / polars / vendi-score / sentence-transformers / pingouin / spacy + Empath | duckdb / sentence-transformers / scipy + ollama (optional `eval` group) |
    40	| **schema-guard 強度** | path 規約 (file-system 依存、grep で破れる) | API contract + CI grep gate で training loader path に `metrics.` を書けない構造 |
    41	| **blockers.md 1 件 close 方法** | spaCy 自前 dictionary 整備で Option C 確定 | **LIWC を完全放棄して Option D 確定 (work cost 最小)** |
    42	| **stimulus battery** | 言及なし | 70 stimulus × 3 巡で Wachsmuth/ToM/RoleEval/dilemma を統制、bootstrap CI noise を抑制 |
    43	| **既存資産との統合** | `eval/` 新 layer (新規創設) | `evidence/` 既存 layer 拡張 (M8 pattern 継承) |
    44	
    45	## 評価 (各案の長所・短所)
    46	
    47	### v1 の長所
    48	- **Parquet 別 file 分離** は industry-standard で「物理分離した」という直感的な
    49	  可視性が高い (将来の reviewer / collaborator にも説明しやすい)
    50	- **Tier A live per-turn** は M9 milestone の "drift gate を実行時に発火" の
    51	  semantic に直結
    52	- pyarrow + polars は ecosystem が厚く、bootstrap resample で polars lazy が
    53	  scale (将来 7500 turn → 10x で benefit)
    54	
    55	### v1 の短所
    56	- **path 規約は file-system 依存で grep で容易に破れる** (training loader が
    57	  `metrics/` を直接 open しない保証は CI 側の追加 gate なしには弱い)
    58	- 新規 layer (`eval/`) 創設は既存 `evidence/` pattern との二重化
    59	- LIWC Option C は spaCy 自前 dictionary の category 設計コストが大、honest
    60	  framing しても Big5 claim の説得力に subtle な傷
    61	- 自然対話 500 turn × 5 run の純粋 baseline は **drift gate の baseline noise が
    62	  高い** (topic 効果と style 効果が混在)
    63	- Tier A live per-turn は inference loop の latency 予算を圧迫する潜在リスク
    64	  (M9-A event-boundary observability の latency 観測値による)
    65	
    66	### v2 の長所
    67	- **DuckDB schema-guard + API contract + CI grep gate** は 3 層 defense で
    68	  contamination を構造的に困難化 (path 規約より厳格)
    69	- **1-dependency (DuckDB)** で I/O / 分析 / Parquet export を統一、依存の
    70	  organic complexity が低い
    71	- **Option D (LIWC 全廃)** は blockers.md の defer 項目を **即時 close** でき、
    72	  work cost が最小、honest framing も最も clean (Big5 を self-report で
    73	  公的に依拠する立場の方が学術的にも defensible)
    74	- **Hybrid baseline** は drift gate の baseline noise を統制、Burrows Delta /
    75	  Vendi の statistical power を高める
    76	- **既存 `InMemoryDialogScheduler` に minimum patch** は破壊リスク最小、
    77	  scheduler 不変条件を維持
    78	- **全 post-hoc 計算** は live inference 負荷ゼロで DB6 を厳守、dev cycle が
    79	  iterate しやすい (採取と計算の分離)
    80	- **systemd --user timer** は journalctl で運用可観測
    81	
    82	### v2 の短所
    83	- **DuckDB 単 file** は「物理分離」の直感的可視性が下がる (named schema は
    84	  内部表現で、外部観察者からは「同じ file の中」)
    85	- v2 自身がリスク 1 で認めている: schema-guard が training pipeline で
    86	  bypass されるリスク (CI grep で補強する前提)
    87	- **Option D** は Big5 を IPIP-NEO 自己申告**のみ**に依拠する設計判断が、
    88	  self-report bias (acquiescence、社会望ましさ) のリスクを集中させる
    89	- **Hybrid baseline の比率 (200/300)** が arbitrary、empirical 根拠なし
    90	- **systemd-timer** は Linux 限定、もし将来 G-GEAR が異 OS になった場合
    91	  (確率は低いが) migration コスト
    92	- **全 post-hoc** は live drift gate (run 中の自動 rollback 等) が原理的に
    93	  遅延 (この task scope では問題ないが、M9-C-adopt で live gate を作る時に
    94	  pipeline 再構築が要る可能性)
    95	
    96	## 推奨案
    97	
    98	**ハイブリッド (v2 ベース + v1 の補強 2 点 + 微調整 2 点)** を推奨。
    99	
   100	### 採用する v2 の判断 (4 件)
   101	
   102	1. **データ層: DuckDB 単 file + schema-guard + CI grep gate** (v2 採用)
   103	   - 理由: schema-guard + API contract の方が path 規約より厳格で、CI grep で
   104	     bypass を構造的に塞げる。Parquet は export contract に格下げで運用簡素。
   105	   - 補強: v2 自身がリスク 1 で挙げた「CI grep gate」を Phase 1 step 1 で
   106	     **必須実装** に格上げ (optional ではなく contract test と同等の地位)。
   107	
   108	2. **LIWC: Option D (Big5 を IPIP-NEO 一本化、LIWC 全廃)** (v2 採用)
   109	   - 理由: blockers.md DB10 honest framing と完全整合、license 議論自体が消滅、
   110	     work cost 最小。
   111	   - 補強: v2 自身がリスク 3 で挙げた「self-report bias」対策として、ICC < 0.6
   112	     が頻発した場合の **second opinion (BIG5-CHAT regression head)** を
   113	     `decisions.md` に re-open 条件として明記 (defer ではなく conditional fallback)。
   114	
   115	3. **Orchestrator: 既存 scheduler に `golden_baseline_mode: bool` minimum patch** (v2 採用)
   116	   - 理由: scheduler 不変条件維持、新 layer 創設の cost 回避、既存テスト破壊
   117	     リスク最小。
   118	
   119	4. **計算 timing: 全 post-hoc per-run CLI** (v2 採用)
   120	   - 理由: DB6 (per-turn は粒度であって live timing ではない) と整合、live
   121	     inference 負荷ゼロ、dev iteration が早い。
   122	
   123	### v1 の補強として残す要素 (2 件)
   124	
   125	5. **新規 metric file は `evidence/tier_{a,b,c}.py` ではなく細分化** (v1 寄せ)
   126	   - 理由: `tier_a.py` 1 file に 5 metric (Burrows / MATTR / NLI / novelty /
   127	     Empath proxy) を詰めると 1 file が 800+ 行になり review-friendly でない。
   128	   - **採用**: `evidence/tier_a/` directory + `{burrows,mattr,nli,novelty,empath_proxy}.py`
   129	     の sub-module 構造。`evidence/` 既存 pattern と整合 (`evidence/scaling_metrics.py`
   130	     は単 file だが metric 数が増える tier_a は分離合理)。
   131	
   132	6. **Hardware allocation 表は Phase 単位で詳細化** (v1 寄せ)
   133	   - 理由: v2 の 11 行 table は subtask が flat、依存関係 / 同期点が table から
   134	     読みにくい。v1 の Phase P0/P1/.../P7 区分の方が `tasklist.md` の `[Mac]` /
   135	     `[GG]` / `[Mac→GG]` tag 付与に直結する。
   136	   - **採用**: v1 形式 (Phase 列 + Subtask + Owner + Machine + VRAM + Hours +
   137	     Sync point) を採用、v2 の subtask 内訳を取り込む。
   138	
   139	### 微調整 (2 件)
   140	
   141	7. **Hybrid baseline の比率は defer**
   142	   - v2 の 200/300 (stimulus / 自然対話) は arbitrary。本タスクで pilot run
   143	     50 turn ずつで両方の bootstrap CI を測り、empirical に比率決定する条項を
   144	     `blockers.md` に追加。default は 200/300 で start。
   145	
   146	8. **Tier C nightly infra**: **systemd --user timer + flock + nvidia-smi
   147	   preflight** (v2 採用)、ただし Mac launchd → ssh trigger は **オプション**
   148	   (採用しない、systemd-timer 単独で実用十分)。
   149	   - 理由: 構成を最小化、master/agent の責務分離は将来 ablation で再検討。
   150	
   151	### v1 vs v2 の決定的な分岐の根拠
   152	
   153	最も重い分岐は **LIWC Option C vs D**。これは Big5 claim を **派生 (LIWC dictionary
   154	score → Big5 推定)** か **直接 (IPIP-NEO 質問紙 → Big5 推定)** にするかという
   155	**measurement model の根本選定**。Option D は
   156	
   157	- (a) blockers.md DB10 の "LIWC OSS proxy で Big5 claim は honest に避ける" と
   158	  完全整合
   159	- (b) LIWC license decision tree を node ごと刈り取れる (work cost zero)
   160	- (c) IPIP-NEO は psychometric literature で Big5 推定の standard で、self-report
   161	  bias は周知だが well-documented
   162	- (d) v1 Option C の spaCy 自前 dictionary は category 設計と validation に
   163	  数日〜数週間の work cost がかかり、validation を solo で完結させる現実性
   164	  が低い
   165	
   166	を満たす。Option D 採用は本タスクの blockers 1 件 close と work cost 削減の
   167	両得で、根拠の明示的な変更 (Big5 measurement model を直接 self-report に倒す)
   168	が trade-off として説得力を持つ。
   169	
   170	### ハイブリッド最終形の要旨
   171	
   172	> **DuckDB 単 file + schema-guard + CI grep gate** で DB5 を構造的に守り、
   173	> **LIWC Option D (Big5 を IPIP-NEO に一本化)** で blockers 1 件即時 close、
   174	> **既存 scheduler に minimum patch** で破壊リスク最小、**hybrid baseline
   175	> (stimulus battery + 自然対話)** で drift gate noise 抑制、**全 post-hoc
   176	> 計算** で live inference 不負荷、**systemd-timer + flock + nvidia-smi
   177	> preflight** で Tier C nightly を OS 任せ。Hardware allocation は v1 の
   178	> Phase 区分形式を採用、metric file は `evidence/tier_a/` sub-module 構造で
   179	> review-friendly に維持。

 succeeded in 0ms:
     1	# 設計 (final — ハイブリッド: v2 ベース + v1 補強 2 点 + 微調整 2 点)
     2	
     3	> **Status**: `/reimagine` 実施済 (v1 = `design-v1.md` に退避、v2 を生成、比較は
     4	> `design-comparison.md`)。本ファイルは採用案を確定したもの。
     5	> Codex `gpt-5.5 xhigh` independent review を Plan 確定前に挟み HIGH 全件反映後に
     6	> `design-final.md` に rename する予定。
     7	
     8	## Hardware allocation
     9	
    10	| Phase | Subtask | Owner | Machine | GPU/VRAM | Est. Hours | Sync point |
    11	|---|---|---|---|---|---|---|
    12	| P0a | LIWC Option D 確定 → `blockers.md` 1 件 close | Claude | Mac | CPU only | 0.5h | blockers.md commit |
    13	| P0b | `contracts/eval_paths.py` (schema-guard) + CI grep gate 必須実装 | Claude | Mac | CPU only | 1.5h | contract test 緑 |
    14	| P0c | `evidence/eval_store.py` (DuckDB connect / schema bootstrap / Parquet export) | Claude | Mac | CPU only | 2h | schema PR merge candidate |
    15	| P1a | Tier A `evidence/tier_a/{burrows,mattr,nli,novelty,empath_proxy}.py` (sub-module 構造) | Claude | Mac | CPU + MPS (MPNet) | 6h | unit test 緑 |
    16	| P1b | reference corpus pickle 整備 (Kant 独+英訳 / Nietzsche / Rikyu / synthetic 4th) | Claude | Mac | CPU only | 2h | fixture test 緑 |
    17	| P2a | `golden/stimulus/{kant,nietzsche,rikyu}.yaml` 起草 (70 stimulus/persona × 3 巡 = 210 turn) | Claude | Mac | CPU only | 4h | review |
    18	| P2b | `integration/dialog.py` への `golden_baseline_mode: bool` minimum patch + sink hook | Claude | Mac | CPU only | 2h | dry-run 50 turn 緑 |
    19	| P3 | golden baseline 採取 (3 persona × 5 run × 500 turn、200 stimulus + 300 自然対話) | Operator | **G-GEAR** | RTX 4090 24GB / qwen3:8b FP16 ~16GB | **6-12h × 3 ≈ 24h wall (overnight × 2)** | DuckDB file → Mac へ rsync |
    20	| P3b | Pilot run 50 turn 両形式で baseline noise 比較 (比率 defer 解消の根拠) | Operator | G-GEAR | 同上 | 2h | blockers.md 比率記録 |
    21	| P4a | Tier B `evidence/tier_b/{vendi,ipip_neo,big5_icc}.py` 実装 | Claude | Mac | CPU + 7B-Q4 借用 (~5GB MPS) | 5h | unit test 緑 |
    22	| P4b | Tier B 後付け実行 (採取済 raw_dialog から post-hoc) | Operator | G-GEAR | 7B-Q4 ~5GB | 2h | metrics schema 投入完了 |
    23	| P5 | bootstrap CI + 2-of-3 quorum logic (DB9、`evidence/bootstrap_ci.py`) | Claude | Mac | CPU only | 3h | sub-metric 3 個 ready |
    24	| P6 | Tier C nightly: systemd --user timer + flock + nvidia-smi preflight | Claude | Mac (作成) → G-GEAR (deploy) | 判定のみ | 4h | systemctl --user list-timers 緑 |
    25	| P7 | Codex `gpt-5.5 xhigh` independent review → HIGH 全件反映 | Claude | Mac | CPU only | 1.5h | `design-final.md` rename |
    26	
    27	**運用ルール**:
    28	- Mac (master/dev) は設計・実装・schema・bootstrap CI・stimulus 起草まで担当
    29	- G-GEAR (実行機) は (a) 7500 turn continuous baseline 採取、(b) IPIP-NEO sub-process、
    30	  (c) Tier C judge LLM nightly slot のみ
    31	- single-writer 原則: 1 マシン = 1 writer。DuckDB file は G-GEAR で書き、Mac は
    32	  rsync 後 read-only で開く
    33	- VRAM contention 回避: P3 baseline 採取と P6 Tier C nightly は時間分離 (systemd-timer
    34	  の preflight が `nvidia-smi --query-gpu=memory.free` で free < 14GB なら skip + log)
    35	
    36	## 実装アプローチ
    37	
    38	### Parquet/DB 物理表現: DuckDB 単 file + named schema + 3 層 contract (v2 採用 + v1 強化)
    39	
    40	**評価データ層は DuckDB 単 file**。training-loader API が唯一の entry point で、
    41	`metrics` schema を SELECT したら `EvaluationContaminationError` を raise。Parquet は
    42	**二次的な export 形式** (`COPY ... TO ... (FORMAT PARQUET)` で nightly 出力、
    43	downstream 分析 / 公開用)。
    44	
    45	**3 層 contract (v1 リスク 1 への補強として CI grep gate を必須化)**:
    46	
    47	1. **API contract**: `eval_store.connect_training_view()` が **唯一** の training-loader entry。
    48	   この関数は内部で `raw_dialog` schema のみ open し、`metrics` schema への access は
    49	   raise する。
    50	2. **schema-guard test**: `tests/test_evidence/test_eval_paths_contract.py` で
    51	   training loader が `metrics` schema を SELECT したら明示的 `EvaluationContaminationError`
    52	   raise を確認。
    53	3. **CI grep gate (補強)**: `.github/workflows/ci.yml` に「training loader path で
    54	   `metrics.` を grep 検出したら fail」step を追加。これにより新コードが API contract
    55	   を bypass する未来の事故を構造的に塞ぐ。
    56	
    57	**根拠 (v2 採用、v1 棄却)**:
    58	- 別 Parquet file 物理分離は path 規約 + grep だけで弱い
    59	- DuckDB 単 file + named schema + API contract + CI grep gate は **3 層 defense**
    60	  で contamination を構造的に困難化
    61	- 1-dependency (DuckDB) で I/O / 分析 / Parquet export を統一
    62	
    63	### Library 選定: DuckDB 単独 (v2 採用)
    64	
    65	採用: `duckdb>=1.1`。pyarrow / polars は採用しない。理由:
    66	- DuckDB は単 process 単 writer で sqlite と同じ運用感
    67	- Parquet export は `COPY ... TO ... (FORMAT PARQUET)` で zero-copy
    68	- Tier A pure function は DuckDB Python API で columnar 取得 → numpy で計算
    69	- 7500 turn × N metric の bootstrap resample も DuckDB 内で完結
    70	
    71	### LIWC alternative: Option D (Big5 全面 IPIP-NEO 移管、LIWC 全廃) — v2 採用
    72	
    73	**Option D 確定**:
    74	- Big5 stability ICC は **IPIP-NEO 自己申告 self-report のみ** に依拠 (Tier B、agent
    75	  に local 7B-Q4 が IPIP-NEO 短縮版 120 item を質問・回答)
    76	- stylometric 一致は Burrows Delta (Tier A)
    77	- persona-fit textual diversity は Vendi (Tier B)
    78	- Empath は **secondary diagnostic** として Tier A の psycholinguistic axis 1 つに
    79	  採用、**Big5 claim には使わない**
    80	- これで `blockers.md` の LIWC license defer が **即時 close** (Option D 採用)
    81	
    82	**根拠**:
    83	- blockers.md DB10 honest framing "LIWC OSS proxy で Big5 claim は honest に避ける"
    84	  と完全整合
    85	- LIWC license decision tree を node ごと刈り取れる (work cost zero)
    86	- IPIP-NEO は psychometric literature で Big5 推定の standard、self-report bias は
    87	  周知だが well-documented
    88	- spaCy 自前 dictionary (Option C) は category 設計 + validation に数日〜数週間の
    89	  work cost、solo で完結させる現実性が低い
    90	
    91	**self-report bias 対策 (v2 リスク 3 への補強)**:
    92	ICC < 0.6 が頻発した場合の **conditional fallback** を `decisions.md` に re-open
    93	条件として明記:
    94	- BIG5-CHAT regression head を Tier B に追加し second opinion 化
    95	- defer ではなく conditional fallback として記録 (発火条件を事前明文化)
    96	
    97	### Golden baseline 採取: Hybrid (200 stimulus + 300 自然対話) — v2 採用、比率は pilot で defer 解消
    98	
    99	**500 turn/run の構成**:
   100	- 最初の **200 turn**: curated stimulus battery を fixed order で投入
   101	  - Wachsmuth Toulmin 引き出す prompt: 30
   102	  - ToM info-asymmetric scenario (chashitsu): 20
   103	  - RoleEval-adapted Kant biographical MCQ: 10
   104	  - persona-conditional moral dilemma: 10
   105	  - 計 70 stimulus × 3 巡 = 210 turn (端数 10 turn は最後 stimulus を切り詰め)
   106	- 残り **300 turn**: 既存 `InMemoryDialogScheduler` の自然対話 (peripatos / chashitsu /
   107	  agora / garden の場の遷移を含む)
   108	
   109	**根拠**:
   110	- 純自然対話 baseline は drift gate baseline noise が大きい (topic 効果と style
   111	  効果が混在)
   112	- 純 stimulus baseline は ζ 軸 (mode 遷移) を測れず M9-A event-boundary observability
   113	  と契約不整合
   114	- hybrid で両得: stylometric reference の統制 + persona の場の対応観察
   115	
   116	**比率 defer (微調整 1)**:
   117	- default 200/300 で start
   118	- P3b で pilot run 50 turn 両形式を比較し、Burrows Delta / Vendi の bootstrap CI
   119	  width が小さい比率に **empirical** 調整
   120	- 結果は `blockers.md` に記録 (defer 解消)
   121	
   122	### Orchestrator: 既存 scheduler に minimum patch (v2 採用)
   123	
   124	**新規 wrapper を新設しない**。既存 `src/erre_sandbox/integration/dialog.py` の
   125	`InMemoryDialogScheduler` に **`golden_baseline_mode: bool = False` 引数 + 1 sink
   126	hook** を追加 (additive only)。
   127	
   128	- `golden_baseline_mode=True` で cooldown / timeout を bypass、500 turn 連続生成可
   129	- default `False` で既存全テスト pass
   130	- stimulus battery の投入は `evidence/golden_baseline.py` が stimulus YAML を読んで
   131	  scheduler の input queue に push する形式 (scheduler 本体に stimulus loader を
   132	  混入させない)
   133	
   134	**根拠**:
   135	- scheduler 不変条件を維持
   136	- 新 layer 創設の cost 回避 (`eval/` 新 layer は不採用)
   137	- 既存テスト破壊リスク最小
   138	
   139	**RNG seed 戦略**:
   140	- `seed = hash((persona_id, run_idx, "m9-eval-v1"))` で deterministic
   141	- 5 run × 3 persona = 15 seed を `golden/seeds.json` に commit
   142	- numpy `Generator(PCG64(seed))` で stream 化、Ollama temperature は persona YAML の
   143	  `default_sampling` を respect
   144	
   145	### Tier A 計算 timing: 全 post-hoc per-run CLI (v2 採用)
   146	
   147	- Tier A は live inference loop に背負わせない (DB6 厳守)
   148	- 採取後に `eval_tier_a` CLI で post-hoc 計算
   149	- 「per-turn 粒度」と「per-turn live timing」は別概念。DB6 が要求するのは粒度
   150	- MPNet embedding は sentence-transformers の synchronous `encode(batch)` で
   151	  N turn まとめ計算
   152	
   153	### Tier C nightly infra: systemd --user timer + flock + nvidia-smi preflight (v2 採用、Mac launchd ssh trigger は不採用)
   154	
   155	**G-GEAR 上で systemd --user の timer unit** を採用。
   156	
   157	- timer unit (`erre-eval-tier-c.timer`) が 02:00 に fire
   158	- service unit が flock で autonomous run の lock file を排他チェック → unlocked なら
   159	  Prometheus 2 (Q4) を起動
   160	- preflight: `nvidia-smi --query-gpu=memory.free` で free < 14GB なら skip + log
   161	- journalctl で実行履歴可観測
   162	
   163	**Mac launchd → ssh trigger は採用しない (微調整 2)**:
   164	- 構成複雑化を回避
   165	- master/agent の責務分離は将来 ablation で再検討
   166	- systemd-timer 単独で実用十分
   167	
   168	## 変更対象
   169	
   170	### 修正するファイル (additive only、破壊禁止)
   171	
   172	- `src/erre_sandbox/integration/dialog.py` — `golden_baseline_mode: bool = False` 引数
   173	  + sink hook 追加。default False で既存全テスト pass
   174	- `src/erre_sandbox/contracts/thresholds.py` — `M2_THRESHOLDS` 不変
   175	- `personas/{kant,nietzsche,rikyu}.yaml` — `ipip_neo_short` optional field 追加
   176	  (additive)
   177	- `pyproject.toml` — dependency 追加 (下記 §影響範囲)
   178	- `tests/test_integration/test_contract_snapshot.py` — 新規 `eval_thresholds` snapshot
   179	  追加 (既存 M2_THRESHOLDS snapshot は再生成しない)
   180	
   181	### 新規作成するファイル
   182	
   183	`src/erre_sandbox/contracts/`:
   184	- `eval_paths.py` — `RAW_DIALOG_SCHEMA: Final = "raw_dialog"` / `METRICS_SCHEMA: Final = "metrics"` /
   185	  schema-guard helper
   186	- `eval_thresholds.py` — DB9 quorum bound、frozen Pydantic、snapshot test ガード
   187	
   188	`src/erre_sandbox/evidence/`:
   189	- `eval_store.py` — DuckDB connection、schema bootstrap、`connect_training_view()`
   190	  唯一 entry、Parquet export
   191	- `tier_a/` directory (v1 補強 1: sub-module 構造):
   192	  - `__init__.py`
   193	  - `burrows.py` — Burrows Delta function-word vector cosine
   194	  - `mattr.py` — Moving Average Type-Token Ratio (window 100)
   195	  - `nli.py` — DeBERTa-v3-base-mnli zero-shot NLI contradiction
   196	  - `novelty.py` — MPNet embedding 距離 semantic novelty
   197	  - `empath_proxy.py` — Empath secondary diagnostic (Big5 claim には使わない)
   198	- `tier_b/` directory:
   199	  - `__init__.py`
   200	  - `vendi.py` — Vendi Score (semantic kernel)
   201	  - `ipip_neo.py` — IPIP-NEO 短縮版 agentic loop (local 7B-Q4)
   202	  - `big5_icc.py` — Big5 stability ICC (run × mode で計算)
   203	- `tier_c/` directory:
   204	  - `__init__.py`
   205	  - `prometheus.py` — Prometheus 2 client (Ollama HTTP)
   206	  - `geval.py` — G-Eval logit-weighted scoring
   207	  - `bias_mitigation.py` — position-swap / length-norm / two-judge protocol
   208	- `bootstrap_ci.py` — NumPy resample、3 sub-metric quorum logic (decision は別 layer)
   209	- `golden_baseline.py` — stimulus battery YAML loader + run 駆動 (既存 scheduler に
   210	  push)
   211	- `reference_corpus/` — Kant 独+英訳、Nietzsche、Rikyu、synthetic 4th persona の
   212	  function-word vector pickle
   213	
   214	CLI (`src/erre_sandbox/cli/`):
   215	- `eval_ingest.py` — sqlite dialog_turns → DuckDB raw_dialog ingest
   216	- `eval_tier_a.py` — Tier A post-hoc 計算
   217	- `eval_tier_b.py` — Tier B post-hoc 計算 (G-GEAR 実行)
   218	- `eval_tier_c.py` — Tier C nightly judge (systemd-timer から呼ばれる entry)
   219	- `eval_audit.py` — raw + metrics integrity check
   220	- `eval_report.py` — bootstrap CI dashboard
   221	
   222	Stimulus / fixture / steering:
   223	- `golden/stimulus/{kant,nietzsche,rikyu}.yaml` — 70 stimulus/persona
   224	- `golden/seeds.json` — 15 seed manifest
   225	- `personas/_synthetic_4th.yaml` — DB7 LOW-1 fixture (Big5 が 3 persona と直交する
   226	  架空 thinker、`schema_version="0.10.0-m7h"`)
   227	- `infra/systemd/erre-eval-tier-c.{service,timer}` — systemd unit
   228	- `.steering/20260430-m9-eval-system/codex-review-prompt.md` — Phase P7 入力
   229	- `.steering/20260430-m9-eval-system/codex-review.md` — verbatim 保存
   230	- `.steering/20260430-m9-eval-system/decisions.md` — 新タスク独自 ADR (任意)
   231	
   232	Tests:
   233	- `tests/test_evidence/test_eval_paths_contract.py` — schema-guard
   234	- `tests/test_evidence/test_eval_store.py` — DuckDB schema bootstrap
   235	- `tests/test_evidence/test_tier_a/` (5 test file)
   236	- `tests/test_evidence/test_tier_b/` (3 test file)
   237	- `tests/test_evidence/test_tier_c/` (3 test file、bias mitigation 含む)
   238	- `tests/test_evidence/test_bootstrap_ci.py`
   239	- `tests/test_evidence/test_golden_baseline.py` — synthetic 4th persona DB7 LOW-1 含む
   240	- `tests/test_contracts/test_eval_thresholds_snapshot.py`
   241	
   242	CI:
   243	- `.github/workflows/ci.yml` に **training loader path で `metrics.` を grep 検出
   244	  したら fail** step を追加 (3 層 contract の補強層)
   245	
   246	### 削除するファイル
   247	
   248	原則無し。additive only。
   249	
   250	## Tier 実装順序 (依存関係)
   251	
   252	```
   253	[Phase 0]
   254	  P0a LIWC Option D 確定 ──┐
   255	  P0b contracts + CI gate ──┤── DB5 contract gate (3 層)
   256	  P0c eval_store DuckDB ────┘
   257	                            │
   258	[Phase 1-2]                 ▼
   259	  P1a Tier A 5 metric (sub-module)  ┐
   260	  P1b reference corpus               ├── parallel

exec
/bin/zsh -lc "nl -ba .steering/20260430-m9-eval-system/design.md | sed -n '260,620p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
   260	  P1b reference corpus               ├── parallel
   261	  P2a stimulus battery YAML          │
   262	  P2b dialog.py minimum patch        ┘
   263	                                     │
   264	[Phase 3]                            ▼
   265	  P3  golden baseline 採取 (G-GEAR、200 stimulus + 300 自然対話)
   266	  P3b pilot 比率 defer 解消
   267	                                     │
   268	[Phase 4-5]                          ▼
   269	  P4a Tier B 3 metric                ┐
   270	  P4b Tier B 後付け実行 (G-GEAR)      ├── post-hoc
   271	  P5  bootstrap CI logic              ┘
   272	                                     │
   273	[Phase 6-7]                          ▼
   274	  P6  Tier C nightly infra (parallel from P0 onward)
   275	  P7  Codex review → HIGH 反映 → design-final.md rename
   276	```
   277	
   278	**DB9 sub-metric 3 個 (Vendi / Big5 ICC / Burrows Delta) ready 時期**:
   279	- Burrows: P1a 完了時 (per-turn computed)
   280	- Vendi / Big5 ICC: P4a 完了時 (per-100-turn computed)
   281	- bootstrap CI 計算 ready: **P5 完了時 = タスク後半** (M9-C-adopt 直前)
   282	
   283	## 影響範囲
   284	
   285	### 既存テストへの impact
   286	
   287	破壊しないこと前提:
   288	- `contract_snapshot` test (frozen `M2_THRESHOLDS` / `SCHEMA_VERSION="0.10.0-m7h"` /
   289	  `DialogTurnMsg` / `RunLifecycleState`) — 全緑維持
   290	- `integration/dialog.py` の `golden_baseline_mode` 追加は default False で既存全
   291	  テスト pass
   292	- 既存 `evidence/metrics.py` interface (`compute_*` 関数群、`aggregate(db_path)`) は
   293	  signature 不変
   294	
   295	### contracts/ への additive 変更
   296	
   297	- 新規 `eval_paths.py` / `eval_thresholds.py` 追加 (`M2_THRESHOLDS` 並列、独立 snapshot)
   298	- 既存 `M2_THRESHOLDS` snapshot は再生成しない
   299	
   300	### pyproject.toml dependency 追加
   301	
   302	```toml
   303	[project.dependencies]  # 既存に追加
   304	"duckdb>=1.1,<2",
   305	"sentence-transformers>=3,<4",
   306	# NLI: 既存 transformers + DeBERTa-v3-base-mnli を借用 (新規依存無し、
   307	# transformers は sentence-transformers が pull する)
   308	
   309	[project.optional-dependencies]
   310	eval = [
   311	    "scipy>=1.13,<2",   # bootstrap resample
   312	    "ollama>=0.3,<1",   # Tier C judge LLM client
   313	    "empath>=0.89",     # Empath secondary diagnostic (Big5 claim 不使用)
   314	]
   315	```
   316	
   317	`spacy` / `pyarrow` / `polars` / `pingouin` / `vendi-score` は採用しない:
   318	- spacy: Option D で不要 (LIWC alternative 自前 dictionary が消滅)
   319	- pyarrow / polars: DuckDB 単独で I/O / 分析カバー
   320	- pingouin: ICC は scipy.stats + numpy で実装可
   321	- vendi-score: 公式 lib は実装が薄く、scipy.spatial.distance + numpy で自前実装
   322	  (vendi-score は固有値分解の wrapper のみ)
   323	
   324	### filterwarnings
   325	
   326	- sentence-transformers の HuggingFace deprecation 群を **局所的に**
   327	  `filterwarnings ignore` で許可 (test 全体には影響させない、`@pytest.mark.filterwarnings`
   328	  decorator で限定)
   329	
   330	## 既存パターンとの整合性
   331	
   332	- **Pure-function metric pattern**: `evidence/metrics.py` の `compute_*` 関数群と
   333	  `aggregate(db_path)` パターンを Tier A 5 metric / Tier B 3 metric にも踏襲
   334	- **CLI subcommand**: 既存 `cli/{baseline_metrics,scaling_metrics,export_log}.py` の
   335	  argparse + JSON/JSONL out パターンを `eval_*` 6 CLI に踏襲、`schema: "<name>_v1"` 慣例
   336	- **Pydantic frozen contracts**: `contracts/thresholds.py` の frozen pattern を
   337	  `eval_thresholds.py` に踏襲 (`model_config = ConfigDict(extra="forbid", frozen=True)`)
   338	- **Persona YAML additive**: `schema_version="0.10.0-m7h"` 維持、既存 field 不変、
   339	  `ipip_neo_short` のみ optional 追加。`_synthetic_4th.yaml` も同じ schema
   340	- **MemoryStore 経由**: `memory/store.py` の `iter_dialog_turns()` で turn 取得し、
   341	  `eval_ingest` CLI で DuckDB raw_dialog schema に投入
   342	- **inference/sampling.py** の `compose_sampling()` override → IPIP-NEO 質問時に
   343	  override で deterministic (temperature=0.0) に切替
   344	
   345	## テスト戦略
   346	
   347	### Contract gate (実装中、pytest)
   348	
   349	1. **DB5 schema-guard**: `tests/test_evidence/test_eval_paths_contract.py` で
   350	   training loader が `metrics` schema を SELECT したら明示的
   351	   `EvaluationContaminationError` raise を確認
   352	2. **CI grep gate**: `.github/workflows/ci.yml` で training loader path に
   353	   `metrics.` を grep 検出したら fail
   354	3. **Bootstrap CI shape**: 既知分布 (synthetic Vendi / ICC / Burrows triple) で
   355	   resample N=1000、95% CI が解析解 ± 5% 内
   356	4. **Frozen snapshot**: `eval_thresholds` 改変時の合意 trail を snapshot test で要求
   357	
   358	### DB7 LOW-1 (synthetic 4th persona heldout fixture)
   359	
   360	- `personas/_synthetic_4th.yaml`: Big5 が 3 既存 persona と直交する架空 thinker
   361	- `test_golden_baseline.py` で 4 persona scenario を Tier A pipeline に通し、3-persona
   362	  overfitting (3-only assumption が出たら fail) を防ぐ
   363	
   364	### Tier acceptance (実装後、pytest)
   365	
   366	- `test_tier_a/`: 5 metric が synthetic + 4th persona heldout で NaN/crash 無く計算、
   367	  Burrows Delta が persona-discriminative (Kant ≠ Nietzsche、distance 差 ≥ fixed delta)
   368	- `test_tier_b/`: 3 metric が known distribution で expected 値、IPIP-NEO loop が
   369	  deterministic temperature=0 で stable
   370	- `test_tier_c/`: bias mitigation hook (position-swap / length-norm) が判定不変性を
   371	  保つかを fixture pair で確認
   372	
   373	### Burrows multi-lang (blockers.md 暫定方針)
   374	
   375	- per-language reference でしか比較しない契約を test 化 (cross-lang を呼ぶと例外)
   376	
   377	### Golden baseline integrity (G-GEAR run 後、CLI)
   378	
   379	- `python -m erre_sandbox.cli.eval_audit data/eval/golden/*.duckdb`:
   380	  - 3 persona × 5 run × 500 turn = 7500 turn 完全性確認
   381	  - metrics sidecar の `(run_id, persona_id, turn_idx)` で raw に LEFT JOIN して
   382	    miss が無いこと確認
   383	- `python -m erre_sandbox.cli.eval_report --bootstrap-ci`:
   384	  - DB9 sub-metric 3 個に CI 数値、persona-discriminative 観察を `blockers.md`
   385	    L89-93 に追記 (defer 解消)
   386	
   387	## ロールバック計画
   388	
   389	- **L0 (即時 dependency rollback)**: `pyproject.toml` の `duckdb` /
   390	  `sentence-transformers` を仮に core → optional `eval` group へ移し、
   391	  `uv sync --no-group eval` で完全 disable。core 機能は影響なし
   392	- **L1 (Tier A revert)**: `evidence/tier_a/` directory 単位で revert、
   393	  `evidence/metrics.py` (M8 baseline) は touch しないので回帰 zero
   394	- **L2 (golden baseline)**: DuckDB file は `data/eval/golden/*.duckdb` に隔離、削除のみ
   395	  で raw_dialog 全消去。export 済 parquet は別 path (`data/eval/parquet_export/`)、
   396	  retention は別 ADR
   397	- **L3 (Tier C nightly)**: `systemctl --user disable erre-eval-tier-c.timer` のみで
   398	  停止。autonomous run には影響なし
   399	- **L4 (DuckDB → Parquet 別 file 移行)**: 万一 schema-guard が contamination を
   400	  防ぎきれないと判明 (CI grep gate でも漏れ) した場合、`eval_store.py` 内部実装
   401	  のみ Parquet 別 file へ差替可能 (`contracts/eval_paths.py` の API は不変、外部
   402	  caller 影響 zero)
   403	- **L5 (golden baseline 再採取)**: 採取済 raw_dialog は `data/eval/golden/` で
   404	  immutable、bug 発見時は run_id 単位で部分 rerun (5 run の独立性が seed 分離で
   405	  保たれている前提)
   406	
   407	## リスクと反復前提 (Codex review HIGH 候補)
   408	
   409	5 件、Phase P7 の Codex independent review で HIGH/MEDIUM/LOW にラベル付け予定:
   410	
   411	1. **DuckDB schema-guard が training pipeline で bypass されるリスク**
   412	   - 物理 file 分離より弱いという指摘の余地
   413	   - 反復前提: API contract + schema-guard test + CI grep gate の 3 層 defense で
   414	     塞ぐ。L4 rollback 経路 (Parquet 別 file 移行) を予備として設計
   415	
   416	2. **Big5 を IPIP-NEO 自己申告のみに頼る妥当性 (Option D の trade-off)**
   417	   - self-report bias (acquiescence、社会望ましさ) リスクが集中
   418	   - cross-mode stability ICC は run independence 前提が壊れる可能性
   419	   - **conditional fallback**: ICC < 0.6 が頻発したら BIG5-CHAT regression head を
   420	     Tier B に追加し second opinion 化。発火条件を `decisions.md` に明文化
   421	
   422	3. **Burrows Delta multi-language reference の汚染** (blockers.md 既出)
   423	   - Kant 独原典 vs 英訳 vs 日本語 dialog の 3 言語 reference 別保持で防ぐ
   424	   - reference token count < 50K で z-score noisy
   425	   - 反復: P1b 完了時に token 数を実測、不足なら corpus 追加
   426	
   427	4. **Hybrid baseline 比率 200/300 の arbitrary 性**
   428	   - 70 stimulus × 3 巡 = 210 turn は Wachsmuth/ToM/RoleEval/dilemma の 4 系統に
   429	     bound、persona の cognitive_habits 全域を覆わない
   430	   - 反復: P3b で pilot run 50 turn 両形式比較、Burrows / Vendi の bootstrap CI
   431	     width が小さい比率に empirical 調整、`blockers.md` 記録
   432	
   433	5. **Tier C judge LLM の VRAM contention 検出失敗**
   434	   - Prometheus 2 8x7B Q4 (~14 GB) + 万一 ollama qwen3 が leak で常駐 (FP16 16 GB)
   435	     → OOM
   436	   - 反復: systemd unit の preflight に `nvidia-smi --query-gpu=memory.free` チェッ
   437	     ク、free < 14 GB なら skip + log
   438	
   439	### Codex 独立 review に回すべき箇所
   440	
   441	- DB5 物理表現の DuckDB 単 file vs 別 Parquet file 戦略の優劣 (3 層 contract の
   442	  実効性検証)
   443	- bootstrap CI の statistical validity (block bootstrap 要否、effective sample size、
   444	  turn の autocorrelation)
   445	- Big5 を IPIP-NEO self-report のみに依拠する measurement model の妥当性
   446	- Burrows Delta multi-lang reference の閾値 (50K token noise floor)
   447	- Hybrid baseline 比率の empirical 決定方法 (P3b pilot の信頼性)
   448	- systemd-timer + flock の race condition 完全性 (autonomous loop が timer fire
   449	  直後に start する境界 case)
   450	
   451	---
   452	
   453	## 設計判断の履歴
   454	
   455	- **初回案 (`design-v1.md`)**: 別 Parquet file 物理分離 / pyarrow + polars / LIWC
   456	  Option C (spaCy + 自前 dict) / 新規 wrapper Orchestrator / Tier A live per-turn /
   457	  asyncio + file-lock
   458	- **再生成案 (v2)**: DuckDB 単 file + schema-guard / DuckDB 単独 / LIWC Option D /
   459	  既存 scheduler minimum patch / 全 post-hoc / systemd-timer + flock / Hybrid baseline
   460	- **比較**: `design-comparison.md` 参照
   461	- **採用**: **ハイブリッド (v2 ベース + v1 補強 2 点 + 微調整 2 点)**
   462	- **根拠**:
   463	  - データ層は v2 (DuckDB schema-guard + CI grep gate の 3 層 defense が path 規約より
   464	    厳格)
   465	  - LIWC は v2 Option D (blockers.md 1 件 close + work cost zero + DB10 honest framing
   466	    と完全整合)
   467	  - Orchestrator は v2 minimum patch (scheduler 不変条件維持、新 layer 創設の cost 回避)
   468	  - 計算 timing は v2 全 post-hoc (DB6 厳守、live inference 不負荷)
   469	  - **v1 補強 1**: metric file 構造を `evidence/tier_a/` sub-module 化 (`tier_a.py`
   470	    単 file は 800+ 行で review-friendly でない)
   471	  - **v1 補強 2**: Hardware allocation は v1 の Phase 区分形式 (subtask flat より
   472	    依存関係 / 同期点が table から読める、`tasklist.md` の `[Mac]` / `[GG]` /
   473	    `[Mac→GG]` tag 付与に直結)
   474	  - **微調整 1**: Hybrid baseline 比率 200/300 は default で start、P3b pilot で
   475	    empirical 調整、`blockers.md` に defer 解消記録
   476	  - **微調整 2**: Tier C nightly は systemd-timer **単独**、Mac launchd → ssh
   477	    trigger は採用しない (構成最小化、master/agent 責務分離は将来 ablation で再検討)
   478	- **次工程**: Phase P0 着手前に Codex `gpt-5.5 xhigh` independent review を発動
   479	  (`codex-review-prompt.md` 起草 → `codex exec --skip-git-repo-check` →
   480	  `codex-review.md` verbatim 保存 → HIGH 全件反映 → 本ファイルを `design-final.md`
   481	  に rename して Phase P0 に入る)

exec
/bin/zsh -lc "nl -ba .steering/20260430-m9-b-lora-execution-plan/decisions.md | sed -n '1,320p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
     1	# Decisions — M9-B LoRA Execution Plan (10 ADR: DB1-DB10)
     2	
     3	## ADR 体裁
     4	
     5	各 ADR は 5 要素 (決定 / 根拠 / 棄却 / 影響 / re-open 条件) で記録。
     6	本 ADR set は m9-lora-pre-plan の D1-D5 (PR #110 merged) を **継承し、M9 実行 phase の
     7	詳細を確定** する位置づけ。Codex independent review (`codex-review.md`) で得た 10 finding
     8	(HIGH 4 / MEDIUM 4 / LOW 2) を全件反映済。
     9	
    10	---
    11	
    12	## DB1 — 量子化戦略: QLoRA NF4 default + alternatives recorded
    13	
    14	- **決定**: 学習時 quantization は **QLoRA NF4 (bnb double-quantization)** を default 採用。
    15	  alternatives (AWQ + LoRA / GPTQ + LoRA / 8-bit LoRA) を記録、bounded Kant spike で
    16	  実測 quality を検証してから default を維持・変更する。
    17	- **根拠**:
    18	  - G-GEAR 16GB + qwen3:8b (FP16 ~16GB) + 3 persona swap で base ~4-5GB 圧縮が必要
    19	  - QLoRA NF4 + double-quantization で 1-2% 性能低下、許容範囲
    20	  - codex MEDIUM-2 指摘: 「唯一現実解」は overstated、conservative default と framing
    21	- **棄却**:
    22	  - LoRA FP16: VRAM 不足
    23	  - INT8 + LoRA: NF4 の上位互換なし
    24	- **影響**:
    25	  - 学習 pipeline は HF Transformers + PEFT/unsloth (M9-C-spike で確定)
    26	  - serving は SGLang LoRA adapter format に変換 (DB3)
    27	- **re-open 条件**:
    28	  - Kant spike で NF4 quality が許容範囲外 → 8-bit LoRA fallback
    29	  - SGLang AWQ + LoRA 互換が confirmed → AWQ への serving migration 検討
    30	
    31	---
    32	
    33	## DB2 — Library 選定: defer to M9-C kickoff
    34	
    35	- **決定**: PEFT vs unsloth の選定は **M9-eval-system + M9-C-spike 完了後の M9-C-adopt 着手時**
    36	  に rank=8 統一 spike で決める。M9-B / M9-eval-system では library を確定しない。
    37	- **根拠**:
    38	  - 学習 library 選定は LoRA を実際に走らせる時点で十分
    39	  - 先行決定する benefit なし (premature optimization)
    40	  - codex review Q3 反映: 必要な時点での実測判断
    41	- **棄却**:
    42	  - v1: unsloth 即採用 → 性能 benefit 未実測のまま commit するリスク
    43	- **影響**:
    44	  - M9-C-spike では一時的に PEFT (公式・ecosystem 厚い) を使用、final 選定は別
    45	- **re-open 条件**:
    46	  - unsloth の SGLang LoRA adapter format compatibility が問題
    47	  - PEFT の学習速度が solo cadence に対し過大
    48	
    49	---
    50	
    51	## DB3 — Serving 移行判断: **SGLang-first, vLLM fallback only** (HIGH-3 反映)
    52	
    53	- **決定**: **現行 SGLang を維持し、LoRA は SGLang `--enable-lora` + `/load_lora_adapter`
    54	  で実装する**。vLLM full migration は **measured spike failure 時のみ** fallback。
    55	- **根拠**:
    56	  - codex HIGH-3: SGLang は v0.3+ で multi-LoRA / dynamic load/unload / pinned adapters /
    57	    overlap loading / `--enable-lora` を documented サポート
    58	    ([SGLang docs](https://docs.sglang.io/advanced_features/lora.html))
    59	  - 私の v1/v2 認識 (SGLang LoRA 安定性未検証) は stale だった
    60	  - vLLM full migration は M5 以降の resonance 機構 / ERRE FSM 再配線が必要、コスト過大
    61	- **棄却**:
    62	  - v1 / v2: vLLM full migration → cost 過大、SGLang stale 認識に基づく
    63	- **影響**:
    64	  - M5 resonance / ERRE FSM 配線そのまま維持 (大きな cost saving)
    65	  - LoRA adapter format は SGLang 互換に変換が必要
    66	- **re-open 条件 (vLLM fallback fire)**:
    67	  - Kant spike で adapter swap latency > 500ms
    68	  - N=3 同時 request で throughput collapse
    69	  - resonance / FSM が SGLang LoRA 経路で regression
    70	
    71	---
    72	
    73	## DB4 — Dataset trigger 閾値: `floor AND (coverage OR plateau OR timebox)` (HIGH-1 反映)
    74	
    75	- **決定**: LoRA 適用 trigger を **`floor MUST AND (coverage 300/persona OR plateau OR timebox)`**
    76	  に確定。divergence stability は **diagnostic** のみ、hard gate にしない。
    77	  - **MUST (floor)**: self_rep ≤ 0.10 AND cross_echo ≤ 0.10 (継続要件)
    78	  - **ANY ONE OF**:
    79	    - coverage: dialog_turn ≥ **300/persona** (旧 500 から緩和)
    80	    - plateau: prompting + persona YAML 拡張のみで Tier B metric が **2 連続 run で
    81	      <5% improvement** (operational definition は DB9 quorum logic に統合)
    82	    - timebox: **8 セッション** (~2 calendar weeks at solo cadence) 経過
    83	  - **diagnostic (warning only)**: divergence_ratio が ζ 36:74:16 ±10% を逸脱
    84	- **根拠**:
    85	  - codex HIGH-1: 4-AND は m9-lora-pre-plan D1 ADR (floor + (coverage OR plateau)) と矛盾
    86	  - D1 既存 ADR で 500/persona は ζ scale で実質 unreachable と warning 済
    87	    (`.steering/20260428-m9-lora-pre-plan/decisions.md:44-50`)
    88	  - timebox 追加は solo project の momentum loss 防止 (codex Q2 反映)
    89	- **棄却**:
    90	  - v1/v2 4-AND: D1 ADR と矛盾、unreachable リスク
    91	  - 500/persona: ζ scale で達成困難
    92	- **影響**:
    93	  - LoRA 適用が現実的タイミングで fire 可能
    94	  - timebox により M9 milestone delay が bounded
    95	- **re-open 条件**:
    96	  - 300/persona も実態で困難 → 再 relax (200/persona) 検討
    97	  - timebox 8 session が早すぎ・遅すぎ判明 → 調整
    98	
    99	---
   100	
   101	## DB5 — Parquet schema: **raw + sidecar 物理分離** (HIGH-4 反映)
   102	
   103	- **決定**: training data と evaluation metric を **物理的に別 table** に保存。
   104	  - **raw_dialog/**: metric-free training table。`evaluation_epoch=*/persona_id=*/run_id=*/`
   105	    partition、training は `evaluation_epoch=false/` のみ読む contract で強制。
   106	  - **metrics/**: sidecar evaluation metric table。`run_id + persona_id + turn_idx` で
   107	    raw に join。tier (A/B/C) + metric_name + metric_value + metadata schema。
   108	- **根拠**:
   109	  - codex HIGH-4: boolean flag (evaluation_epoch) だけでは training pipeline が物理的に
   110	    metric column にアクセス可能、汚染リスク (judge artifact 学習)
   111	  - 物理分離 + training-view contract で contamination を構造的に不可能にする
   112	- **棄却**:
   113	  - v1/v2: 単一 Parquet schema に metric column 統合 → contamination リスク
   114	- **影響**:
   115	  - Parquet pipeline 実装 (M9-eval-system) の複雑度が中程度増加
   116	  - training loader は明示的に `raw_dialog/evaluation_epoch=false/` のみ読む実装
   117	  - dashboard / analysis は raw + metrics を join して使用
   118	- **re-open 条件**:
   119	  - sidecar join overhead が training latency に影響大
   120	  - schema migration が必要な structural change
   121	
   122	---
   123	
   124	## DB6 — Evaluation epoch 分離: Run-level flag + 物理 partition + sidecar (HIGH-4 統合) + 頻度 policy (MEDIUM-4)
   125	
   126	- **決定**:
   127	  - `evaluation_epoch: bool` を Run config 必須化、Default `False`
   128	  - Parquet partition で物理分離 (`raw_dialog/evaluation_epoch=*/`)
   129	  - sidecar metrics table も同 partition 構造
   130	  - **頻度 policy**:
   131	    - **Tier A**: per turn (cheap, ~50ms total)
   132	    - **Tier B**: per 100 turns (Vendi / IPIP-NEO / Big5 ICC)
   133	    - **Tier C**: nightly offline batch (Prometheus 2 / G-Eval / FANToM-adapted) — autonomous run 停止時のみ実行
   134	- **根拠**:
   135	  - codex HIGH-4 + MEDIUM-4: Tier C judge LLM (Prometheus 2 8x7B class) は qwen3:8b agent
   136	    と VRAM contention、同時実行不可
   137	  - 物理 partition は HIGH-4 解消の core mechanism
   138	- **棄却**:
   139	  - v1/v2 の boolean flag 単独: contamination リスク
   140	  - Tier C を per-100-turn に走らせる案: VRAM contention で agent 停止
   141	- **影響**:
   142	  - autonomous loop に nightly batch slot 追加が必要
   143	  - dashboard は per-tier の latency profile を表示
   144	- **re-open 条件**:
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
   171	## DB8 — Adapter swap runbook: SGLang `/load_lora_adapter` first
   172	
   173	- **決定**:
   174	  - **SGLang `/load_lora_adapter` REST endpoint** で adapter dynamic load
   175	  - `--max-loras N` + `--max-lora-rank R` 起動オプション
   176	  - hot path persona は `pinned adapters` で pin
   177	  - **runbook 起草は M9-C-spike 完了後**、実測値 (latency / cold start / throughput) 込み
   178	- **根拠**:
   179	  - DB3 (SGLang-first) と整合
   180	  - SGLang docs cited by codex
   181	  - 実測値なしの runbook は無価値、spike 完了後に書く
   182	- **棄却**:
   183	  - v1/v2 vLLM LoRARequest API ラッパ路線 → DB3 で破棄
   184	- **影響**:
   185	  - M9-C-spike が runbook の前提
   186	- **re-open 条件**:
   187	  - SGLang LoRA で adapter swap が機能不全 → vLLM fallback (DB3 re-open)
   188	
   189	---
   190	
   191	## DB9 — Drift gate: composite + bootstrap CI + 2-of-3 quorum (HIGH-2 反映)
   192	
   193	- **決定**: drift gate を **統計的に厳密** に運用:
   194	  - **Primary composite per persona**: 各 persona の Tier B から 3 sub-metric:
   195	    - `vendi_score` (semantic kernel)
   196	    - `big5_stability_icc` (across-mode personality stability)
   197	    - `burrows_delta_to_reference` (persona-fit)
   198	  - **Bootstrap CI** over turns/runs: 各 sub-metric の 95% CI を計算
   199	  - **Quorum rule**:
   200	    - rollback (drift): 2-of-3 sub-metric が CI で baseline negative 方向
   201	    - adoption: 2-of-3 sub-metric が CI で baseline positive 方向
   202	  - **Single regression**: warning ログのみ、rollback しない
   203	  - **Defensive canary** (即時): self_rep > 0.15 OR cross_echo > 0.15 (any 1) → CI 待たず auto rollback
   204	  - **Initial run** (first LoRA application): floor 維持で許容 (warmup 認可)
   205	  - **Subsequent runs (≥2)**: 2-of-3 quorum で adoption / rollback 判定
   206	  - **3 連続 adoption 失敗**: LoRA 設定 (rank / dataset) を破棄、再 spike
   207	- **根拠**:
   208	  - codex HIGH-2: 「5%」固定 + Tier B noise → false rollback / metric gaming リスク
   209	  - bootstrap CI + quorum で statistical robustness
   210	  - Effect size は persona-conditional に bootstrap で決める (固定 5% を破棄)
   211	- **棄却**:
   212	  - v1 「floor 維持のみ」: 効果測定不能
   213	  - v2 「絶対 5% 改善」: noise floor が persona 依存、根拠不十分
   214	- **影響**:
   215	  - bootstrap CI 実装 (M9-eval-system)
   216	  - quorum logic 実装 (M9-C-adopt)
   217	- **re-open 条件**:
   218	  - 3 sub-metric の選定が実態で不適切 (例: vendi_score が persona に discriminative でない)
   219	  - CI 計算 cost が prohibitive
   220	
   221	---
   222	
   223	## DB10 — J 評価系 framework: 4-tier + persona-conditional + multi-channel (specs only in M9-B)
   224	
   225	- **決定**:
   226	  - **M9-B 内 deliverable は specs のみ** (実装コードは出さない、MEDIUM-1 反映)
   227	  - **4-tier 階層** (research-evaluation-metrics.md ベース):
   228	    - Tier A: per-turn cheap (LIWC/Empath / Burrows Delta / MATTR / semantic novelty / NLI)
   229	    - Tier B: per-100-turn (Vendi Score / IPIP-NEO / Big5 stability ICC)
   230	    - Tier C: per-session offline (Prometheus 2 / G-Eval / FANToM-adapted / ROSCOE)
   231	    - Tier D: sparse manual (FActScore-adapted / 専門家 review / RoleEval-adapted MCQ)
   232	  - **persona-conditional gate**: absolute value ではなく persona-baseline からの bootstrap
   233	    CI 偏差 (Rikyu LOW idea density は適正、Kant HIGH も適正)
   234	  - **golden set staging** (MEDIUM-3 反映):
   235	    - M9-eval-system: **100/persona seed**
   236	    - LoRA 採用判定: **300/persona acceptance**
   237	    - 学術発表時: **1000/persona publication-grade**
   238	  - **multi-channel honest framing**: single thinker-likeness score 採用しない、
   239	    formal benchmark = floor / proxy = exploratory / expert review = final
   240	  - **LIWC alternatives honest framing** (LOW-2 反映): Empath/spaCy は proxy であり LIWC 等価ではない、
   241	    Big-Five claim は LIWC 商用 license + validation あって初めて成立、proxy ベースの
   242	    Big-Five claim は honest に避ける
   243	- **根拠**:
   244	  - research-evaluation-metrics.md L326-349 honest gap assessment
   245	  - codex MEDIUM-1 / 3 / LOW-2 反映
   246	- **棄却**:
   247	  - v1: framework 宣言のみ、内容空白
   248	  - v2 単独: M9-B 内で Tier A 実装まで含む scope creep
   249	  - 「single thinker-likeness score」: research-evaluation-metrics.md と Codex 双方が棄却
   250	- **影響**:
   251	  - M9-eval-system が独立タスクとして大規模化
   252	  - golden set 採取に専門知識 (philosopher domain expert) が必要
   253	- **re-open 条件**:
   254	  - golden set 整備が solo cadence に対し時間的に困難
   255	  - LIWC license が approve、商用使用可
   256	
   257	---
   258	
   259	## ADR 横断: third option (codex final note 反映)
   260	
   261	**bounded, non-authoritative single-persona Kant LoRA spike を SGLang 上で M9-eval-system
   262	と並行実施する**。adoption 判断は評価系完成後の post-spike re-eval まで保留。
   263	
   264	- **目的**: 評価系構築中に LoRA 学習・adapter swap・runtime 技術リスクを早期検出
   265	- **non-authoritative**: spike の結果のみで adoption しない (評価系 gate 通過必須)
   266	- **scope**: Kant 1 persona のみ、既存 dialog_turn を training data として use、
   267	  `evaluation_epoch=false` partition のみ
   268	- **deliverable**: SGLang LoRA endpoint 動作確認 + adapter swap latency 実測 +
   269	  vLLM migration 必要性 measured 判断材料
   270	- **タスク**: 別タスク `M9-C-spike` として切り出し (新規 scaffold)

exec
/bin/zsh -lc "nl -ba .steering/20260430-m9-b-lora-execution-plan/blockers.md | sed -n '1,260p'" in /Users/johnd/ERRE-Sand Box
exec
/bin/zsh -lc "nl -ba .steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md | sed -n '1,320p'" in /Users/johnd/ERRE-Sand Box
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
    25	- **issue**: LIWC-22 は商用 license、ERRE は zero-budget 制約
    26	- **option A**: 商用 license 取得 (one-time fee 数百ドル)
    27	- **option B**: Empath OSS 代用 (proxy、psycholinguistic depth は劣る)
    28	- **option C**: spaCy ベースの custom dictionary 自作 (work cost 大)
    29	- **option D**: stylometry (Burrows' Delta) のみで persona-fit を測り、Big-Five claim を諦める
    30	- **defer 先**: M9-eval-system 着手前 (Tier A 実装の前提)
    31	- **reopen 条件**: いずれかの option が確定
    32	
    33	### Burrows' Delta multi-language strategy 詳細
    34	- **issue**: Kant 独原典 vs 英訳 vs 日本語 dialog で idiolect 汚染
    35	- **暫定方針** (DB10 で確定):
    36	  - per-language で normalize
    37	  - within-language reference corpora で比較
    38	  - cross-language Burrows' Delta は使わない
    39	  - Kant の場合: 独訳 reference + 英訳 reference を別 baseline として保持
    40	- **defer 先**: M9-eval-system (reference corpus 整備時に詳細詰め)
    41	- **reopen 条件**: dialog 言語が混在運用される (現状 EN/JA 混在の可能性)
    42	
    43	### Prometheus 2 / G-Eval bias mitigation runbook
    44	- **issue**: judge LLM bias literature (CALM 2024、Wataoka 2024 等) が示す
    45	  position / verbosity / self-preference bias を mitigation する手順が必要
    46	- **暫定方針** (codex Q4 反映):
    47	  - position-swap averaging
    48	  - length normalization
    49	  - two local judges for close calls
    50	  - human spot checks
    51	  - CI over repeated runs
    52	  - Prometheus / G-Eval 単独 gate にしない
    53	- **defer 先**: M9-eval-system (Tier C 実装時に runbook 起草)
    54	- **reopen 条件**: judge LLM の選択が確定 (Prometheus 2 8x7B vs Qwen2.5-72B 等)
    55	
    56	### 専門家 qualitative review の人 selection
    57	- **issue**: Tier D の expert review に Kant / Nietzsche / Rikyu 専門家の協力が必要
    58	- **暫定方針**:
    59	  - M9-C-adopt 直前で 3 persona × 1 専門家を確保
    60	  - 連絡先 / 関係構築は別途
    61	  - 報酬 / 公開的位置づけ (co-author 等) も決める
    62	- **defer 先**: M9-C-adopt 直前
    63	- **reopen 条件**: 評価系完成後に専門家 selection 開始
    64	
    65	### Golden set 1000/persona publication-grade の timing
    66	- **issue**: DB10 で 100/persona seed → 300 acceptance → 1000 publication staging を確定
    67	- **defer 先**: 学術発表時期決定後
    68	- **reopen 条件**: OSF 事前登録 / 投稿先決定
    69	
    70	## 設計上の不確実性 (記録のみ)
    71	
    72	### v1 棄却の機会コスト
    73	- v1「LoRA ASAP」を棄却したことで、短期 deliverable が遅延
    74	- M9 milestone の 2-3 倍延長 (M9-B / M9-eval-system / M9-C-spike / M9-C-adopt)
    75	- ただし codex Q1 で「v1 cannot prove success because J5 is floor-only」と確認、棄却妥当
    76	- **再評価条件**: M9-eval-system が予想以上に長期化 (>3 セッション) → M9-C-spike を
    77	  evaluation の前倒し材料として強化
    78	
    79	### M9-C-spike の adoption 判断 leakage リスク
    80	- spike が「成功」した場合、評価系完成前に adoption 圧力が発生する可能性
    81	- 暫定対策: spike 完了時に明示的に「non-authoritative」を文書化、評価系 gate 通過を要件化
    82	- **対策強化条件**: M9-C-spike Kant が「明らかに人間目視で改善」した場合の判断 protocol を起草
    83	
    84	### N=3 漸近線の未測定
    85	- prompting + persona YAML 拡張で N=3 がどこまで divergence するか empirical 未測定
    86	- DB4 plateau gate が fire するかどうか不明
    87	- **観測点**: M9-eval-system Tier B 実装完了直後の 2-3 run で plateau curve を観察
    88	
    89	### Tier B sub-metric 3 個の選定妥当性
    90	- DB9 で `vendi_score` / `big5_stability_icc` / `burrows_delta_to_reference` を選定
    91	- これら 3 個が persona discriminative か未検証
    92	- **再評価条件**: M9-eval-system Tier B 実装完了後の golden baseline 採取で discriminative 確認、
    93	  不適切なら sub-metric 入れ替え
    94	
    95	## reopen トリガ一覧 (運用 checklist)
    96	
    97	| 項目 | reopen 条件 | trigger 場所 |
    98	|---|---|---|
    99	| LIWC license | option A-D いずれか確定 | M9-eval-system 着手前 |
   100	| Burrows multi-lang | dialog 言語混在運用 | M9-eval-system reference corpus |
   101	| Judge bias runbook | judge LLM 確定 | M9-eval-system Tier C 実装 |
   102	| 専門家 selection | 評価系完成 | M9-C-adopt 直前 |
   103	| 1000/persona timing | 学術発表時期 | OSF 登録時 |
   104	| v1 機会コスト再評価 | M9-eval-system >3 セッション | M9-eval-system 中盤 |
   105	| M9-C-spike leakage | spike Kant 目視改善 | M9-C-spike 完了時 |
   106	| N=3 plateau curve | Tier B 実装完了 | M9-eval-system Tier B 完了直後 |
   107	| Tier B sub-metric 3 | golden baseline 採取 | M9-eval-system 終盤 |

 succeeded in 0ms:
     1	# Evaluation Metrics Survey — 思想家らしさ評価系の文献調査 (J0)
     2	
     3	## 目的
     4	
     5	M9-B の J 軸 (思想家らしさの評価系 framework) の ADR (DB10) を起草する前に、
     6	既存の evaluation metrics を 6 系統 (persona consistency / LLM-as-judge / ToM /
     7	philosophical depth / cognitive trait / diversity) に分類して網羅し、
     8	ERRE 用途への適用性を判定する。
     9	
    10	成果物は `design-v1.md` / `design-v2.md` 起草時の根拠資料。
    11	
    12	## 調査範囲と方法
    13	
    14	- 並列 3 subagent (general-purpose) で Family 1+2 / Family 3+4 / Family 5+6 を分担
    15	- Web search 中心 (Family 5+6)、Family 3+4 は subagent の知識ベース (cutoff 2026-01)
    16	- 計 30+ metric を citation 付きで列挙
    17	- 各 metric について: citation / 何を測るか / scoring / dataset / 限界 / ERRE 適用性
    18	- 各 family の synthesis (top 2 candidates) + 全体ギャップ評価
    19	
    20	## Family 1: Persona consistency / character role-play
    21	
    22	### CharacterEval (Tu et al., ACL 2024, arXiv:2401.01275)
    23	- **What**: 4 dimensions / 13 metrics — conversational ability, character consistency
    24	  (knowledge / persona / behavior), role-playing attractiveness, Big-Five back-testing
    25	- **Scoring**: CharacterRM (fine-tuned 7B reward model) on 1-5 scale; 人間相関 > GPT-4 judge
    26	- **Dataset**: 1,785 multi-turn dialogues / 23,020 turns / 77 Chinese characters
    27	- **限界**: Chinese-only; pop-fiction skew (no philosophers); RM 転移性未検証
    28	- **ERRE 適用性**: rubric **構造**を流用 (knowledge/persona/behavior 分割)、weights 流用は不可
    29	
    30	### RoleBench / RoleLLM (Wang et al., ACL Findings 2024, arXiv:2310.00746)
    31	- **What**: Role 知識 + speaking-style 模倣を GPT-4 reference で scoring
    32	- **Scoring**: ROUGE-L vs RoleGPT references + GPT-4 LLM-judge style fidelity (1-10)
    33	- **Dataset**: 168K samples / 100 roles (95 EN + 5 ZH)
    34	- **限界**: GPT-4 reference 汚染、style mimicry ≠ 思考様式
    35	- **ERRE 適用性**: fine-tune 訓練手法 (Context-Instruct) としては流用可、metric としては薄い
    36	
    37	### CharacterBench (Zhou et al., AAAI 2025, arXiv:2412.11912)
    38	- **What**: 11 granular dimensions × 6 aspects (memory / knowledge / persona / emotion /
    39	  morality / believability)、sparse/dense 区別
    40	- **Scoring**: CharacterJudge (fine-tuned judge) > GPT-4 agreement
    41	- **Dataset**: 22,859 human-annotated / 3,956 characters / bilingual
    42	- **限界**: Customizable persona focus、historical fidelity 用ではない
    43	- **ERRE 適用性**: **★★★ 最強の taxonomy match。** "morality" + "believability" は
    44	  Kant deontology / Nietzsche amor fati の評価軸として直接使える。sparse/dense 分割は
    45	  query budget 設計で empirically 価値あり
    46	
    47	### PersonaGym + PersonaScore (Samuel et al., EMNLP Findings 2025, arXiv:2407.18416)
    48	- **What**: 5 軸 — Action Justification / Expected Action / Linguistic Habits /
    49	  Persona Consistency / Toxicity Control × 150 dynamic environments
    50	- **Scoring**: PersonaScore (decision-theory grounded GPT-4 judge with rubric)
    51	- **限界**: GPT-4 judge cost + self-preference bias、shallow personas
    52	- **ERRE 適用性**: **★★★ Action Justification 軸** は「思想的深度」の現存最近接 proxy。
    53	  agent が persona に合致する **why** を説明する rubric を流用、score は流用不可
    54	
    55	### RoleEval (Shen et al., 2024, arXiv:2312.16132)
    56	- **What**: Role 知識 MCQ — relationships / abilities / experiences の多肢選択
    57	- **限界**: MCQ 形式は recall のみ測定、生成評価ではない
    58	- **ERRE 適用性**: 「Kant biographical MCQ」を pre-gate として cheap 自動化可。役立つが副次的
    59	
    60	### PersonaChat / DNLI (Zhang 2018, Welleck 2019)
    61	- **What**: 発話 vs persona profile の entailment / contradiction
    62	- **ERRE 適用性**: 既存 `cross_persona_echo_rate` の cousin。NLI head による
    63	  `persona_contradiction_rate` は cheap continuous signal として追加可
    64	
    65	## Family 2: LLM-as-judge
    66	
    67	### G-Eval (Liu et al., EMNLP 2023, arXiv:2303.16634)
    68	- **What**: rubric-defined NLG dimension (coherence / consistency / fluency etc.)
    69	- **Scoring**: form-filling + auto-CoT + **logit weighted score** (連続値、tie-breaking)
    70	- **限界**: GPT-4 self-preference bias、logit access 必要 (closed-API friction)
    71	- **ERRE 適用性**: **★★★ Top-tier**。logit-weighted scoring は連続 offensive metric の決定版。
    72	  zero-budget 制約下では local strong judge (Qwen2.5-72B / Llama-3.3-70B) で代替
    73	
    74	### Prometheus 2 (Kim et al., 2024, arXiv:2405.01535)
    75	- **What**: rubric-based direct assessment (1-5) + pairwise ranking、weight-merged 7B/8x7B
    76	- **Scoring**: Feedback Collection (100K) + Preference Collection (200K) で fine-tuned
    77	- **限界**: 7B-8x7B size が agent と VRAM 競合、rubric phrasing sensitivity
    78	- **ERRE 適用性**: **★★★ Top-tier**。open-weights / local / bias controllable。
    79	  G-Eval probability weighting と組み合わせ stability 確保
    80	
    81	### MT-Bench / Chatbot Arena (Zheng et al., NeurIPS 2023, arXiv:2306.05685)
    82	- **What**: 80-question multi-turn instruction-following + crowd Elo
    83	- **限界**: position / verbosity / self-enhancement bias 文書化、role-play 用ではない
    84	- **ERRE 適用性**: methodology (pairwise + position-swap averaging + two-judge agreement) のみ流用
    85	
    86	### Judge bias literature (CALM 2024 / Wataoka 2024 / Shi 2024 / Survey arXiv:2411.15594)
    87	- **What**: 12 bias categories quantified (position / verbosity / self-preference /
    88	  bandwagon / authority / attentional / refinement-aware)
    89	- **ERRE 適用性**: **mandatory hygiene**。(a) position-swap averaging、(b) self-judge 禁止、
    90	  (c) length penalty、(d) close calls は second non-self judge で confirm
    91	
    92	## Family 3: Theory of Mind (ToM)
    93	
    94	### ToMI (Le et al., EMNLP 2019, arXiv:1908.00998)
    95	- **What**: First/second-order false-belief tracking (Sally-Anne style)
    96	- **限界**: Templated → surface-pattern shortcut (Sap 2022 で perturbation で破綻)
    97	- **ERRE 適用性**: low-medium。floor check として可、object-location は thinker 用には浅い
    98	
    99	### BigToM (Gandhi et al., NeurIPS 2023, arXiv:2306.15448)
   100	- **What**: causal-template belief/desire/action triads + true/false belief contrast
   101	- **ERRE 適用性**: medium。contrastive minimal-pair 設計を流用 (Rikyu/guest tea-ceremony pair)
   102	
   103	### Hi-ToM (He et al., EMNLP Findings 2023, arXiv:2310.16755)
   104	- **What**: 4th-order beliefs ("A thinks B thinks C thinks…")
   105	- **Scoring**: order 別 acc — degradation curve が key signal
   106	- **限界**: GPT-4 でも order-2 超えで急落、ecological validity 議論
   107	- **ERRE 適用性**: medium-high。multi-thinker scene (Kant + Nietzsche + observer) は
   108	  inherently order-2+。acc@order-k degradation curve は clean quantitative axis
   109	
   110	### FANToM (Kim et al., EMNLP 2023, arXiv:2310.15421)
   111	- **What**: ToM in **information-asymmetric multi-party conversations**;
   112	  agent が入退室する chat で who knows what; ToM illusion probes (own knowledge と
   113	  character knowledge の混同検出)
   114	- **Scoring**: belief / answerability / info-accessibility 各種、all-or-nothing aggregate
   115	- **ERRE 適用性**: **★★★ High**。chashitsu / peripatos scene は exactly info-asymmetric multi-party。
   116	  "answerability" 軸 = 「Rikyu agent は自分が知らないことを知っているか」epistemic humility
   117	
   118	### OpenToM (Xu et al., ACL 2024, arXiv:2402.06044)
   119	- **What**: longer narratives + 明示的 personality/preference grounding;
   120	  physical AND psychological mental states (emotions / intentions)
   121	- **限界**: smaller dataset (~700 stories)、psychological label noise
   122	- **ERRE 適用性**: **★★★ High**。psychological subscore は location-belief より thinker 評価に近い
   123	
   124	### ToMBench (Chen et al., ACL 2024, arXiv:2402.15052)
   125	- **What**: 8 ToM tasks aggregated (false-belief / faux-pas / strange-stories / scalar implicature 等)、bilingual
   126	- **ERRE 適用性**: medium-high。**faux-pas** + **strange-stories** subtask は Rikyu 茶礼 etiquette 違反 /
   127	  Kant categorical-imperative 違反の最近接 proxy
   128	
   129	### Critical literature: Kosinski 2023 / Ullman 2023 / Sap 2022
   130	- **Kosinski**: GPT-3.5 が ~90% false-belief task をクリア
   131	- **Ullman 2023 (arXiv:2302.08399)**: minor perturbation (透明容器 / observer 在席) で崩壊 → pattern matching
   132	- **Sap 2022 (arXiv:2210.13312)**: SocialIQa + ToMI で GPT-3 が second-order で human ceiling 大幅下回る
   133	- **ERRE 適用性**: **mandatory methodology**。任意の ToM 数値報告は Ullman-style perturbation
   134	  robustness control 必須、さもなくば査読で discount される
   135	
   136	## Family 4: Philosophical / argumentative depth
   137	
   138	### ETHICS (Hendrycks et al., ICLR 2021, arXiv:2008.02275)
   139	- **What**: 5 frameworks (justice / deontology / virtue / utilitarian / commonsense) の moral judgment
   140	- **限界**: normative ethics を classification 化 (philosophical reasoning と矛盾)
   141	- **ERRE 適用性**: depth は low、persona-consistency probe としては medium。
   142	  Kant agent が deontology を utilitarian より systematically over-weight するか測れる
   143	  (framework-tilt vector = persona fidelity signal)
   144	
   145	### MMLU philosophy subset (Hendrycks 2021, arXiv:2009.03300)
   146	- **What**: 哲学者・立場・概念の MCQ
   147	- **限界**: 教科書記憶評価、Kant impersonator vs Kant quoter を区別不能
   148	- **ERRE 適用性**: floor のみ (agent が base model より MCQ で *劣化* しないこと)
   149	
   150	### Wachsmuth Toulmin rubric (EACL 2017)
   151	- **What**: 15-dimension argument quality (cogency / effectiveness / reasonableness)
   152	  をベースに claim / data / warrant / backing / rebuttal を抽出
   153	- **Scoring**: human Likert 1-5、LLM-judge 近似は 2024 work で moderate κ ~0.4 with experts
   154	- **限界**: Cogency annotator 一致 κ~0.4、LLM judge は verbose/hedged を好むバイアス
   155	- **ERRE 適用性**: **★★★ High**。「argument-shaped vs chatbot-shaped」の最も defensible 量的軸。
   156	  LLM-judge を agent turn に通して per-dimension score 報告
   157	
   158	### FActScore (Min et al., EMNLP 2023, arXiv:2305.14251)
   159	- **What**: long-form generation を atomic-fact 分解 → 知識ソースで verify
   160	- **限界**: factual claim 用、normative/philosophical claim 不対応
   161	- **ERRE 適用性**: medium、adaptable。canonical-source corpus (Critique of Pure Reason 等) で
   162	  decomposer を構築し、agent-Kant claim が Kant 実著作に *attributable* か scoring 可。
   163	  「scholarly fidelity」評価として運用可能、「depth」評価ではない
   164	
   165	### ROSCOE (Golovneva et al., ICLR 2023, arXiv:2212.07919)
   166	- **What**: 10+ automated metrics across semantic alignment / logical inference /
   167	  factuality / redundancy
   168	- **Scoring**: embedding + NLI based、fully automated
   169	- **限界**: math/commonsense reasoning 用にチューン、philosophical 前提は NLI 不適合
   170	- **ERRE 適用性**: **★★★ High** as scaffold。redundancy / self-consistency /
   171	  source-faithfulness sub-metric は直接流用可。**informativeness 指標**
   172	  (step k が k-1 より新情報を加えるか) は genuine non-triviality proxy
   173	
   174	### CoT Faithfulness (Lanham et al., 2023, arXiv:2307.13702)
   175	- **What**: chain-of-thought の faithfulness 測定
   176	- **ERRE 適用性**: methodology 流用、reasoning trace の self-consistency check に使用可
   177	
   178	### LongEval (Krishna et al., EACL 2023, arXiv:2301.13298)
   179	- **What**: long-form summarization の coherence / faithfulness を span-level 注釈で評価
   180	- **ERRE 適用性**: methodology 流用 (segment-level annotation > holistic)
   181	
   182	## Family 5: Cognitive / personality trait inference
   183	
   184	### Big Five via IPIP-NEO (Serapio-García et al., 2023, arXiv:2307.00184; Nature MI 2025)
   185	- **What**: OCEAN trait levels をペルソナごとに validated
   186	- **Scoring**: IPIP-NEO 300/120 items、5-point Likert、LIWC features で validation
   187	- **限界**: training-data 汚染 (questionnaire item leak)、response-style bias、prompt context drift
   188	- **ERRE 適用性**: **★★★ Strong fit**。session 開始時に IPIP-NEO-120 を 1 回、
   189	  各 dialog turn で LIWC で trait を verify。Kant/Nietzsche/Rikyu が **distinct + stable**
   190	  OCEAN profile を peripatos/chashitsu/shu_kata mode 横断で保つか直接テスト可
   191	
   192	### LIWC-22 (Boyd et al., 2022; PersonaLLM NAACL 2024)
   193	- **What**: ~100 psycholinguistic categories per turn
   194	- **Scoring**: category 頻度ベクトル × 100、Big Five 推定は published regression weight
   195	- **限界**: bag-of-words、negation 不感、English centric (Japanese / German は別 dictionary 要)、
   196	  commercial license
   197	- **ERRE 適用性**: **★★★** per-turn O(N) cheap continuous proxy。LIWC で毎 turn、
   198	  IPIP-NEO は sparse (毎 100 turn) で anchor
   199	
   200	### BIG5-CHAT / embedding-based Big Five (ACL 2025)
   201	- **What**: RoBERTa/sentence-BERT embedding 上で Big Five 回帰
   202	- **Scoring**: regression head、5 連続 score、r ~0.4-0.7
   203	- **限界**: domain shift (essay vs philosophical dialog)、labeled data 必要
   204	- **ERRE 適用性**: medium。LIWC-derived Big Five と相互チェック用 second opinion
   205	
   206	### Stylometry / Burrows' Delta (arXiv:2507.00838 2025; arXiv:2408.08946 2024)
   207	- **What**: function-word distribution / sentence-length / POS n-gram で author idiolect 一致度
   208	- **Scoring**: Burrows' Delta = z-scored function-word frequency の Manhattan distance
   209	  (低 = author に近い)、tree-based / CodeT5 classifier で 95%+ acc on 10-sentence window
   210	- **Dataset**: thinker 別 reference corpus (Kant Critique 独+英訳、Nietzsche Zarathustra、
   211	  Rikyu Nampōroku) ≥ 50k tokens
   212	- **限界**: 翻訳が idiolect を汚染、短い turn (<200 tokens) で noisy、topic と style 混同
   213	- **ERRE 適用性**: **★★★ Critical for persona-fit**。「Kant らしく聞こえるか」を
   214	  per-turn distance で直接 score。cheap (function-word vector のみ)
   215	
   216	### MBTI-from-text (arXiv:2307.16180; arXiv:2509.04461; Frontiers 2026 critique)
   217	- **限界**: MBTI 自体に construct validity 欠落、context-unstable
   218	- **ERRE 適用性**: **skip for v1**。academic credibility cost > Big Five 上乗せ情報
   219	
   220	### Personality stability under perturbation (Serapio-García §validation; arXiv:2602.01063)
   221	- **What**: trait score の test-retest stability under prompt paraphrase / temperature jitter / mode change
   222	- **Scoring**: Cronbach's α (≥0.7)、ICC (≥0.75)、test-retest r
   223	- **ERRE 適用性**: **★★★ The metric we actually want**。「Kant が peripatos→chashitsu→shu_kata
   224	  を通して Kant のままか」を Big Five 出力の across-mode 安定性で測る。meta-metric
   225	
   226	### Cognitive style (Newton 2024)
   227	- **What**: AOT / CMT / PIT / PET、LIWC "Analytic" summary score (0-100) で proxy 可
   228	- **ERRE 適用性**: free proxy、Kant high vs Rikyu low を discriminate (secondary)
   229	
   230	## Family 6: Lexical and semantic diversity
   231	
   232	### distinct-n (Li et al., NAACL 2016, arXiv:1510.03055)
   233	- **Scoring**: |unique n-grams| / |total n-grams|, n=1,2 が標準
   234	- **限界**: length-sensitive、semantic 無視、saturate fast
   235	- **ERRE 適用性**: cheap baseline、persona 別 rolling 1k-turn window
   236	
   237	### Self-BLEU (Zhu et al., SIGIR 2018, arXiv:1802.01886)
   238	- **Scoring**: 各 sentence の rest に対する mean BLEU (低 = diverse)
   239	- **限界**: O(N²)、Shaib 2024 で semantic homogenization と相関弱
   240	- **ERRE 適用性**: 200-turn window down-sample で sanity check
   241	
   242	### BERTScore homogenization (Zhang ICLR 2020 + Padmakumar 2024)
   243	- **限界**: Shaib 2024 が「barely varies across sources」で skip 推奨
   244	- **ERRE 適用性**: skip
   245	
   246	### Vendi Score (Friedman & Dieng, TMLR 2023, arXiv:2210.02410)
   247	- **What**: similarity kernel に対する effective unique sample 数
   248	- **Scoring**: VS = exp(-Σ λ_i log λ_i) (λ_i = K/n eigenvalue)、range [1, N]
   249	- **限界**: O(N²) similarity + O(N³) eigendecomp (N ≤ 2k なら manageable)、kernel 選択 load-bearing
   250	- **ERRE 適用性**: **★★★ Excellent**。persona 別の「effective unique-turn count」が単一 interpretable scalar。
   251	  kernel swap (stylometric / semantic / topical) で ablation 可
   252	
   253	### MATTR (Covington & McFall 2010)
   254	- **Scoring**: sliding window TTR の平均 (W=500 tokens)、length-stable
   255	- **ERRE 適用性**: streaming cheap、distinct-1 と相補
   256	
   257	### Semantic novelty (Padmakumar 2024 / arXiv:2507.13874 2025)
   258	- **Scoring**: novelty(t) = 1 - max_cos(emb(t), {emb(t-k)…emb(t-1)})
   259	- **ERRE 適用性**: **★★★** 「思考様式は新 idea を生むべき、loop すべきでない」claim の direct proxy。
   260	  multilingual MPNet で per-turn
   261	
   262	### Idea / propositional density CPIDR (Brown et al. 2008; Snowdon 1996)
   263	- **Scoring**: P-density = #propositions / #words × 10、adult prose typical 4.5-5.5
   264	- **限界**: English tuned、philosophical run-on で parser brittle
   265	- **ERRE 適用性**: **persona-conditional discriminator**。Kant >> Rikyu 期待、batched run
   266	
   267	### Concept-graph density (spaCy + Ehrlinger 2024)
   268	- **限界**: extraction noise が短い turn で支配的
   269	- **ERRE 適用性**: defer to v2
   270	
   271	### Repetition rate (Welleck ICLR 2020)
   272	- **ERRE 適用性**: cheap canary for degenerate persona collapse (既存 Evidence Layer 既に採用)
   273	
   274	## Synthesis (各 family 上位 2 候補)
   275	
   276	| Family | Top 1 | Top 2 |
   277	|---|---|---|
   278	| **F1 Persona consistency** | CharacterBench (taxonomy 流用) | PersonaGym Action Justification 軸 |
   279	| **F2 LLM-as-judge** | Prometheus 2 (local) | G-Eval probability-weighted (technique) |
   280	| **F3 ToM** | FANToM (info-asymmetric multi-party) | OpenToM (psychological state) |
   281	| **F4 Philosophical depth** | Wachsmuth Toulmin rubric + LLM-judge | ROSCOE (informativeness) + FActScore-adapted |
   282	| **F5 Cognitive trait** | Big Five (IPIP-NEO + LIWC-22 cross-validation) | Stylometry (Burrows' Delta to thinker reference) |
   283	| **F6 Diversity** | Vendi Score (semantic kernel) | MATTR (lexical streaming) |
   284	
   285	## ERRE 用途への落とし込み — v1 evaluation pipeline 具体提案
   286	
   287	3 persona × 1000 turn / session を想定した 3 階層:
   288	
   289	### Tier A: per-turn (cheap, 1-50ms/turn 目標)
   290	- `LIWC-22` (CPU dict、3-8ms)
   291	- `Burrows' Delta` to thinker reference corpus (function-word vector、2ms)
   292	- `MATTR` (streaming、<1ms)
   293	- `MPNet sentence embedding` (GPU、15-25ms) → `semantic novelty (t)` (<1ms)
   294	- `repetition_rate` (既存) / `cross_persona_echo_rate` (既存)
   295	- `persona_contradiction_rate` (NLI head、新規追加候補)
   296	
   297	合計: ~50ms/turn steady-state。real-time pondering budget 内
   298	
   299	### Tier B: per-100-turn (medium)
   300	- `IPIP-NEO-120` を local 7B-Q4 で実行 (30-60s amortized = 0.3-0.6s/turn 換算)
   301	- `Vendi Score` rolling 200-turn window (50-80ms when window slides、stride=1 で <1ms/turn amortized)
   302	- `personality stability across mode` (Cronbach's α / ICC)
   303	
   304	### Tier C: per-session (expensive)
   305	- `Prometheus 2` rubric assessment (CharacterBench 6-aspect taxonomy で instantiate)
   306	- `G-Eval` probability-weighted scoring on Wachsmuth Toulmin dimensions
   307	- `ROSCOE` informativeness + self-consistency on reasoning trace
   308	- `FANToM-adapted` ToM probe (chashitsu scene info-asymmetric minimal pair)
   309	- `OpenToM-adapted` psychological state probe
   310	
   311	### Tier D: sparse / manual (golden set + expert)
   312	- `FActScore-adapted` against Kant/Nietzsche/Rikyu canonical corpus
   313	- 専門家 qualitative review (人間 annotator、philosopher domain expert)
   314	- `RoleEval-adapted` biographical MCQ pre-gate
   315	
   316	## Persona-conditional metrics 注意
   317	
   318	以下は **持続的に「高ければ良い」とは言えない** = persona conditional:
   319	- Idea density: Kant HIGH 期待 / Rikyu LOW 期待 (低が persona-fit)
   320	- Allusion / citation rate: persona 別 target rate、universal max ではない

exec
/bin/zsh -lc "nl -ba .steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md | sed -n '320,430p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
   320	- Allusion / citation rate: persona 別 target rate、universal max ではない
   321	- Vendi Score 解釈: persona の「思考の幅」次第で適正値が異なる
   322	- LIWC "Analytic" score: Kant high / Rikyu low が正解
   323	
   324	→ J 軸 ADR では **persona-baseline からの偏差** を gate にすべき、絶対値 gate は誤り
   325	
   326	## 正直なギャップ評価
   327	
   328	**現状の formal benchmark で測れるもの**:
   329	- ceiling test (agent が baseline より劣化しないか)
   330	- persona-tilt test (deontological vs utilitarian 等の framework 偏り)
   331	- ToM floor (false-belief tracking、epistemic humility)
   332	- argument shape (Toulmin claim/warrant/data の存在)
   333	- diversity (lexical / semantic 反復回避)
   334	- stylometric resemblance (function word distribution)
   335	
   336	**現状の formal benchmark で測れないもの (irreducible gap)**:
   337	- 「Kant のように **論じる**」(speak vs reason)
   338	- 「思想的 originality」 (single-number 圧縮困難)
   339	- 「Nietzsche genealogy 操作」「Rikyu wabi reduction」のような **domain-specific cognitive habit**
   340	- 「philosophical movement」 (turn 間で distinction が deepen するか)
   341	
   342	**Concrete proxies for the irreducible gap (探索的)**:
   343	- `concept-graph density`: NP 抽出 → co-occurrence graph、Kant の freedom-duty-reason cluster vs chatbot flat fan-out
   344	- `allusion / citation rate`: 8-gram match against thinker corpus (persona conditional target)
   345	- `semantic novelty over base`: same-prompt base-model output と agent output の embedding distance
   346	- `disagreement productivity`: multi-thinker scene で *新 distinction* を加える turn 比率
   347	
   348	**結論: formal metric は floor、proxy は exploratory、expert review は最終。
   349	single number 化は honest に放棄し、multi-channel report する**。
   350	
   351	これを踏まえ M9-B 設計フェーズで:
   352	- DB10 (J 軸 ADR) は「Tier A-D の階層構造」を採用、「single thinker-likeness score」は棄却
   353	- gate 設計は **persona-baseline 偏差** を中心に置く
   354	
   355	## Sources (主要)
   356	
   357	- [CharacterEval arXiv:2401.01275](https://arxiv.org/abs/2401.01275)
   358	- [CharacterBench arXiv:2412.11912](https://arxiv.org/html/2412.11912.pdf)
   359	- [PersonaGym arXiv:2407.18416](https://arxiv.org/abs/2407.18416)
   360	- [RoleLLM arXiv:2310.00746](https://arxiv.org/abs/2310.00746)
   361	- [G-Eval arXiv:2303.16634](https://arxiv.org/abs/2303.16634)
   362	- [Prometheus 2 arXiv:2405.01535](https://arxiv.org/html/2405.01535v2)
   363	- [MT-Bench arXiv:2306.05685](https://arxiv.org/abs/2306.05685)
   364	- [LLM-as-Judge Survey arXiv:2411.15594](https://arxiv.org/abs/2411.15594)
   365	- [FANToM arXiv:2310.15421](https://arxiv.org/abs/2310.15421)
   366	- [OpenToM arXiv:2402.06044](https://arxiv.org/abs/2402.06044)
   367	- [BigToM arXiv:2306.15448](https://arxiv.org/abs/2306.15448)
   368	- [Hi-ToM arXiv:2310.16755](https://arxiv.org/abs/2310.16755)
   369	- [ToMBench arXiv:2402.15052](https://arxiv.org/abs/2402.15052)
   370	- [Ullman 2023 critique arXiv:2302.08399](https://arxiv.org/abs/2302.08399)
   371	- [Sap 2022 ToM limits arXiv:2210.13312](https://arxiv.org/abs/2210.13312)
   372	- [ETHICS arXiv:2008.02275](https://arxiv.org/abs/2008.02275)
   373	- [Wachsmuth Argumentation EACL 2017](https://aclanthology.org/E17-1017/)
   374	- [FActScore arXiv:2305.14251](https://arxiv.org/abs/2305.14251)
   375	- [ROSCOE arXiv:2212.07919](https://arxiv.org/abs/2212.07919)
   376	- [Lanham CoT Faithfulness arXiv:2307.13702](https://arxiv.org/abs/2307.13702)
   377	- [Serapio-García Personality Traits LLM arXiv:2307.00184](https://arxiv.org/abs/2307.00184)
   378	- [PersonaLLM NAACL 2024](https://aclanthology.org/2024.findings-naacl.229.pdf)
   379	- [BIG5-CHAT ACL 2025](https://aclanthology.org/2025.acl-long.999.pdf)
   380	- [Stylometry LLM arXiv:2507.00838](https://arxiv.org/abs/2507.00838)
   381	- [Authorship Attribution LLM arXiv:2408.08946](https://arxiv.org/pdf/2408.08946)
   382	- [Vendi Score arXiv:2210.02410](https://arxiv.org/abs/2210.02410)
   383	- [distinct-n arXiv:1510.03055](https://arxiv.org/abs/1510.03055)
   384	- [Self-BLEU arXiv:1802.01886](https://arxiv.org/pdf/1802.01886)
   385	- [Shaib Standardizing Diversity arXiv:2403.00553](https://arxiv.org/html/2403.00553v2)
   386	- [Geometry of Knowledge arXiv:2507.13874](https://arxiv.org/html/2507.13874)
   387	
   388	## 検証 caveats
   389	
   390	- Family 5+6 は WebSearch 経由、citation 高信頼
   391	- Family 3+4 は subagent training cutoff 2026-01 知識ベース、citation 信頼。
   392	  ただし「PhilEval / PhilBench」は subagent が「flag for verification」と明示
   393	- 適宜 design 起草中に追加確認可、時間制約上 J0 の枠ではここまで

codex
The local evidence shows several design assertions are load-bearing: the grep gate is only string-based, bootstrap CI is currently described as plain NumPy resampling, and “frequently” for ICC fallback is not operationalized. I’m checking the repo shape now so the recommendations fit actual paths instead of being abstract.
exec
/bin/zsh -lc "nl -ba src/erre_sandbox/integration/dialog.py | sed -n '1,260p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
     1	"""In-memory implementation of the M4 :class:`DialogScheduler` Protocol.
     2	
     3	Responsibility: admission-control and lifecycle tracking for agent-to-agent
     4	dialogs. The scheduler *also* owns the envelope emission path — when it
     5	admits an initiate or closes a dialog, it calls the injected ``sink``
     6	callable with the corresponding :class:`ControlEnvelope`, so callers do not
     7	need to route the return value back into the gateway's queue themselves.
     8	
     9	Design rationale (see
    10	``.steering/20260420-m4-multi-agent-orchestrator/design.md`` §v2):
    11	
    12	* The Protocol is frozen at M4 foundation and says ``schedule_initiate``
    13	  returns ``DialogInitiateMsg | None``; we keep that return contract but
    14	  the authoritative delivery path is the sink. Callers that build on the
    15	  Protocol API only get a signal of "was this admitted"; they MUST NOT
    16	  put the returned envelope onto a queue themselves — doing so would
    17	  duplicate the envelope delivered via the sink.
    18	* ``tick()`` is an extension method (not part of the Protocol) that drives
    19	  proximity-based auto-firing: two agents sharing a reflective zone after
    20	  the pair's cooldown has elapsed get a probabilistic initiate.
    21	* All randomness flows through an injected :class:`~random.Random` so the
    22	  auto-fire path is deterministic under test.
    23	"""
    24	
    25	from __future__ import annotations
    26	
    27	import logging
    28	import uuid
    29	from dataclasses import dataclass, field
    30	from random import Random
    31	from typing import TYPE_CHECKING, ClassVar, Final
    32	
    33	from erre_sandbox.schemas import (
    34	    AgentView,
    35	    DialogCloseMsg,
    36	    DialogInitiateMsg,
    37	    DialogTurnMsg,
    38	    Zone,
    39	)
    40	
    41	if TYPE_CHECKING:
    42	    from collections.abc import Callable, Iterable, Iterator, Sequence
    43	    from typing import Literal
    44	
    45	    from erre_sandbox.schemas import ControlEnvelope
    46	
    47	logger = logging.getLogger(__name__)
    48	
    49	
    50	@dataclass
    51	class _OpenDialog:
    52	    """In-flight dialog state carried by the scheduler's ``_open`` map."""
    53	
    54	    dialog_id: str
    55	    initiator: str
    56	    target: str
    57	    zone: Zone
    58	    opened_tick: int
    59	    last_activity_tick: int
    60	    turns: list[DialogTurnMsg] = field(default_factory=list)
    61	
    62	
    63	_REFLECTIVE_ZONES: Final[frozenset[Zone]] = frozenset(
    64	    {Zone.PERIPATOS, Zone.CHASHITSU, Zone.AGORA, Zone.GARDEN},
    65	)
    66	"""Zones where proximity-based dialog admission is allowed.
    67	
    68	``Zone.STUDY`` is intentionally excluded — the M2 persona-erre model treats
    69	the study as a private deep-work space where interrupting speech is
    70	culturally inappropriate.
    71	"""
    72	
    73	
    74	def _pair_key(a: str, b: str) -> frozenset[str]:
    75	    """Order-agnostic dialog pair identity used as a dict key."""
    76	    return frozenset({a, b})
    77	
    78	
    79	class InMemoryDialogScheduler:
    80	    """Default :class:`DialogScheduler` implementation for MVP multi-agent runs.
    81	
    82	    State lives entirely in memory; there is no persistence because M4
    83	    scoped dialog history to the transient layer (semantic summaries come
    84	    from the Reflector on a different path). If a future milestone wants
    85	    cross-run dialog transcripts, subclass and override ``record_turn`` /
    86	    ``close_dialog`` to also write to sqlite.
    87	    """
    88	
    89	    COOLDOWN_TICKS: ClassVar[int] = 30
    90	    """Ticks that must elapse after a close before the same pair may reopen."""
    91	
    92	    TIMEOUT_TICKS: ClassVar[int] = 6
    93	    """Inactivity window after which an open dialog is auto-closed."""
    94	
    95	    AUTO_FIRE_PROB_PER_TICK: ClassVar[float] = 0.25
    96	    """Probability that a qualifying co-located pair is admitted on a tick.
    97	
    98	    Keeps dialog from firing every single cognition tick when two agents
    99	    happen to share a zone; the RNG is injected so tests can force the
   100	    probability to 1.0 or 0.0 deterministically.
   101	    """
   102	
   103	    def __init__(
   104	        self,
   105	        *,
   106	        envelope_sink: Callable[[ControlEnvelope], None],
   107	        rng: Random | None = None,
   108	        turn_sink: Callable[[DialogTurnMsg], None] | None = None,
   109	    ) -> None:
   110	        self._sink = envelope_sink
   111	        self._rng = rng if rng is not None else Random()  # noqa: S311 — non-crypto
   112	        # M8 L6-D1: optional per-turn sink. When bootstrap wires it to a
   113	        # ``MemoryStore.add_dialog_turn_sync`` closure (with agent_id →
   114	        # persona_id resolution baked in), every recorded turn lands in
   115	        # sqlite for later LoRA-training export. Left None for unit tests
   116	        # and the existing lightweight fixtures that have no store.
   117	        self._turn_sink = turn_sink
   118	        self._open: dict[str, _OpenDialog] = {}
   119	        self._pair_to_id: dict[frozenset[str], str] = {}
   120	        # Bounded by C(N, 2) for N agents — M4 targets N≤3 so this cannot
   121	        # grow beyond a few entries. If a future milestone scales to N>100
   122	        # agents, cap this to an LRU dict or prune by stale age from
   123	        # ``tick()``; for now the memory footprint is irrelevant.
   124	        self._last_close_tick: dict[frozenset[str], int] = {}
   125	
   126	    # ------------------------------------------------------------------
   127	    # Protocol methods (frozen in schemas.py §7.5)
   128	    # ------------------------------------------------------------------
   129	
   130	    def schedule_initiate(
   131	        self,
   132	        initiator_id: str,
   133	        target_id: str,
   134	        zone: Zone,
   135	        tick: int,
   136	    ) -> DialogInitiateMsg | None:
   137	        """Admit or reject a new dialog.
   138	
   139	        Returns the :class:`DialogInitiateMsg` on admission for callers that
   140	        rely on the Protocol signature, BUT the envelope is already on the
   141	        way to consumers via the injected sink at the moment this method
   142	        returns. Callers must not forward the return value onto the same
   143	        envelope queue — see module docstring.
   144	        """
   145	        if initiator_id == target_id:
   146	            return None
   147	        if zone not in _REFLECTIVE_ZONES:
   148	            return None
   149	        key = _pair_key(initiator_id, target_id)
   150	        if key in self._pair_to_id:
   151	            return None
   152	        last_close = self._last_close_tick.get(key)
   153	        if last_close is not None and tick - last_close < self.COOLDOWN_TICKS:
   154	            return None
   155	
   156	        dialog_id = _allocate_dialog_id()
   157	        self._open[dialog_id] = _OpenDialog(
   158	            dialog_id=dialog_id,
   159	            initiator=initiator_id,
   160	            target=target_id,
   161	            zone=zone,
   162	            opened_tick=tick,
   163	            last_activity_tick=tick,
   164	        )
   165	        self._pair_to_id[key] = dialog_id
   166	        envelope = DialogInitiateMsg(
   167	            tick=tick,
   168	            initiator_agent_id=initiator_id,
   169	            target_agent_id=target_id,
   170	            zone=zone,
   171	        )
   172	        self._emit(envelope)
   173	        return envelope
   174	
   175	    def record_turn(self, turn: DialogTurnMsg) -> None:
   176	        """Attach ``turn`` to its dialog's transcript.
   177	
   178	        Raises ``KeyError`` when the dialog is not open — this surfaces bugs
   179	        (agents speaking into a closed dialog) rather than silently dropping.
   180	
   181	        When a ``turn_sink`` was injected at construction (M8 L6-D1), the
   182	        turn is forwarded to it after the in-memory bookkeeping so the sink
   183	        observes turns in the same order as the transcript. Sink exceptions
   184	        are caught and logged — a transient persistence failure must not
   185	        tear down the live dialog loop.
   186	        """
   187	        dialog = self._open.get(turn.dialog_id)
   188	        if dialog is None:
   189	            raise KeyError(
   190	                f"record_turn called for unknown dialog_id={turn.dialog_id!r}",
   191	            )
   192	        dialog.turns.append(turn)
   193	        dialog.last_activity_tick = turn.tick
   194	        if self._turn_sink is not None:
   195	            try:
   196	                self._turn_sink(turn)
   197	            except Exception:
   198	                logger.exception(
   199	                    "turn_sink raised for dialog_id=%s turn_index=%d; "
   200	                    "dropping row but keeping dialog alive",
   201	                    turn.dialog_id,
   202	                    turn.turn_index,
   203	                )
   204	
   205	    def close_dialog(
   206	        self,
   207	        dialog_id: str,
   208	        reason: Literal["completed", "interrupted", "timeout", "exhausted"],
   209	        *,
   210	        tick: int | None = None,
   211	    ) -> DialogCloseMsg:
   212	        """Close ``dialog_id`` and emit the envelope via the sink.
   213	
   214	        When ``tick`` is provided the close is recorded at that world tick
   215	        (``DialogCloseMsg.tick`` and the cooldown anchor both honour it).
   216	        When omitted, falls back to ``dialog.last_activity_tick`` so callers
   217	        that only see the M4-frozen Protocol surface continue to behave as
   218	        before. The keyword-only ``tick`` is the supported path for any
   219	        caller that knows the current world tick (timeout sweep, exhausted
   220	        budget, manual interrupt) — see codex review F1 (2026-04-28) for
   221	        the stale-tick regression that motivated the parameter.
   222	
   223	        Raises ``KeyError`` when the id is not currently open.
   224	        """
   225	        return self._close_dialog_at(dialog_id, reason, tick)
   226	
   227	    def _close_dialog_at(
   228	        self,
   229	        dialog_id: str,
   230	        reason: Literal["completed", "interrupted", "timeout", "exhausted"],
   231	        tick: int | None,
   232	    ) -> DialogCloseMsg:
   233	        """Apply the close operation, honouring an optional override tick."""
   234	        dialog = self._open.pop(dialog_id, None)
   235	        if dialog is None:
   236	            raise KeyError(f"close_dialog called for unknown dialog_id={dialog_id!r}")
   237	        close_tick = tick if tick is not None else dialog.last_activity_tick
   238	        key = _pair_key(dialog.initiator, dialog.target)
   239	        self._pair_to_id.pop(key, None)
   240	        self._last_close_tick[key] = close_tick
   241	        envelope = DialogCloseMsg(
   242	            tick=close_tick,
   243	            dialog_id=dialog_id,
   244	            reason=reason,
   245	        )
   246	        self._emit(envelope)
   247	        return envelope
   248	
   249	    # ------------------------------------------------------------------
   250	    # Protocol-external extensions
   251	    # ------------------------------------------------------------------
   252	
   253	    def tick(self, world_tick: int, agents: Sequence[AgentView]) -> None:
   254	        """Drive proximity-based admission + timeout close in one step.
   255	
   256	        Called by ``WorldRuntime._on_cognition_tick`` after per-agent
   257	        cognition has run. Order:
   258	
   259	        1. close any dialogs whose last_activity_tick is older than TIMEOUT
   260	        2. for each co-located pair in reflective zones, probabilistically

exec
/bin/zsh -lc "nl -ba .github/workflows/ci.yml | sed -n '1,220p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
     1	name: CI
     2	
     3	on:
     4	  push:
     5	    branches: [main]
     6	  pull_request:
     7	
     8	permissions:
     9	  contents: read
    10	
    11	# Avoid duplicate runs: feature branches go through pull_request only;
    12	# main gets push runs (post-merge). Concurrency cancels stale in-flight
    13	# runs of the same ref (PR re-pushes / consecutive main pushes).
    14	concurrency:
    15	  group: ci-${{ github.event.pull_request.number || github.ref }}
    16	  cancel-in-progress: true
    17	
    18	jobs:
    19	  lint:
    20	    name: ruff (check + format)
    21	    runs-on: ubuntu-latest
    22	    timeout-minutes: 10
    23	    steps:
    24	      - uses: actions/checkout@v4
    25	      - name: Install uv
    26	        uses: astral-sh/setup-uv@v5
    27	        with:
    28	          enable-cache: true
    29	          python-version-file: .python-version
    30	      - name: Sync dependencies
    31	        run: uv sync --frozen --all-groups
    32	      - name: ruff check
    33	        run: uv run ruff check src tests
    34	      - name: ruff format --check
    35	        run: uv run ruff format --check src tests
    36	
    37	  typecheck:
    38	    name: mypy
    39	    runs-on: ubuntu-latest
    40	    timeout-minutes: 10
    41	    steps:
    42	      - uses: actions/checkout@v4
    43	      - name: Install uv
    44	        uses: astral-sh/setup-uv@v5
    45	        with:
    46	          enable-cache: true
    47	          python-version-file: .python-version
    48	      - name: Sync dependencies
    49	        run: uv sync --frozen --all-groups
    50	      - name: mypy src
    51	        run: uv run mypy src
    52	
    53	  test:
    54	    name: pytest (non-godot)
    55	    runs-on: ubuntu-latest
    56	    timeout-minutes: 10
    57	    steps:
    58	      - uses: actions/checkout@v4
    59	      - name: Install uv
    60	        uses: astral-sh/setup-uv@v5
    61	        with:
    62	          enable-cache: true
    63	          python-version-file: .python-version
    64	      - name: Sync dependencies
    65	        run: uv sync --frozen --all-groups
    66	      - name: pytest -m "not godot"
    67	        run: uv run pytest -m "not godot"

exec
/bin/zsh -lc "rg --files src/erre_sandbox tests .github | sed -n '1,220p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
src/erre_sandbox/__main__.py
tests/test_main.py
.github/workflows/ci.yml
src/erre_sandbox/inference/ollama_adapter.py
tests/test_godot_mode_tint.py
src/erre_sandbox/inference/sampling.py
src/erre_sandbox/inference/__init__.py
src/erre_sandbox/schemas.py
tests/_godot_helpers.py
tests/test_smoke.py
tests/test_godot_peripatos.py
tests/test_schemas_m5.py
tests/test_memory/test_embedding_prefix.py
tests/test_memory/test_semantic_layer.py
tests/test_memory/test_embedding.py
tests/test_memory/test_store.py
tests/test_memory/__init__.py
tests/test_memory/test_retrieval.py
tests/test_memory/conftest.py
tests/__init__.py
tests/test_schema_contract.py
tests/test_persona_kant.py
tests/test_schemas_m7g.py
tests/test_ui/test_messages.py
tests/test_ui/test_stub.py
tests/test_ui/test_server.py
tests/test_ui/test_state.py
tests/test_ui/__init__.py
tests/test_ui/conftest.py
src/erre_sandbox/cli/baseline_metrics.py
src/erre_sandbox/cli/__init__.py
src/erre_sandbox/cli/scaling_metrics.py
src/erre_sandbox/cli/export_log.py
src/erre_sandbox/world/tick.py
src/erre_sandbox/world/zones.py
src/erre_sandbox/world/physics.py
src/erre_sandbox/world/__init__.py
src/erre_sandbox/__init__.py
tests/test_cognition/test_prompting.py
tests/test_cognition/test_trigger_pick.py
tests/test_cognition/test_biorhythm_events.py
tests/test_cognition/test_reasoning_trace.py
tests/test_cognition/test_erre_mode_events.py
tests/test_cognition/test_belief_promotion.py
tests/test_cognition/test_decision_with_affinity.py
tests/test_cognition/test_cycle.py
tests/test_cognition/test_reflection.py
tests/test_cognition/test_importance.py
tests/test_cognition/test_state.py
tests/test_cognition/__init__.py
tests/test_cognition/test_relational.py
tests/test_cognition/test_zone_bias.py
tests/test_cognition/test_cycle_erre_fsm.py
tests/test_cognition/test_parse.py
tests/test_cognition/test_reflection_envelope.py
tests/test_cognition/test_movement_speed_persona_factor.py
tests/test_cognition/conftest.py
tests/test_cognition/test_relational_simulation.py
tests/test_schemas.py
tests/test_world/test_runtime_lifecycle.py
tests/test_world/test_apply_affinity_delta.py
tests/test_world/test_physics.py
tests/test_world/test_separation_force.py
tests/test_world/test_temporal_events.py
tests/test_world/test_tick.py
tests/test_world/__init__.py
tests/test_world/test_per_agent_cognition_period.py
tests/test_world/test_affordance_events.py
tests/test_world/test_apply_belief_promotion.py
tests/test_world/test_proximity_events.py
tests/test_world/conftest.py
tests/test_world/test_zones.py
tests/test_inference/test_sampling.py
tests/test_inference/__init__.py
tests/test_inference/test_ollama_adapter.py
tests/fixtures/m4/reflection_event.json
tests/fixtures/m4/agent_spec_3agents.json
tests/fixtures/m4/semantic_memory_record.json
tests/test_bootstrap.py
tests/test_godot_dialog_bubble.py
tests/test_behavior_profile.py
src/erre_sandbox/contracts/__init__.py
src/erre_sandbox/contracts/thresholds.py
tests/test_architecture/__init__.py
tests/test_architecture/test_layer_dependencies.py
tests/conftest.py
tests/test_envelope_kind_sync.py
tests/test_schemas_m6.py
tests/test_envelope_fixtures.py
tests/schema_golden/control_envelope.schema.json
tests/schema_golden/README.md
tests/schema_golden/persona_spec.schema.json
tests/schema_golden/agent_state.schema.json
tests/test_godot_ws_client.py
tests/test_godot_project.py
tests/test_personas/test_load_all.py
tests/test_personas/__init__.py
tests/test_cli_export_log.py
tests/test_cli_baseline_metrics.py
src/erre_sandbox/erre/fsm.py
src/erre_sandbox/erre/sampling_table.py
src/erre_sandbox/erre/__init__.py
tests/test_erre/test_sampling_table.py
tests/test_erre/test_fsm.py
tests/test_erre/__init__.py
src/erre_sandbox/bootstrap.py
src/erre_sandbox/integration/dialog_turn.py
src/erre_sandbox/integration/__init__.py
src/erre_sandbox/integration/acceptance.py
src/erre_sandbox/integration/protocol.py
src/erre_sandbox/integration/dialog.py
src/erre_sandbox/integration/gateway.py
src/erre_sandbox/integration/metrics.py
src/erre_sandbox/integration/scenarios.py
src/erre_sandbox/cognition/cycle.py
src/erre_sandbox/cognition/importance.py
src/erre_sandbox/cognition/reflection.py
src/erre_sandbox/cognition/prompting.py
src/erre_sandbox/cognition/__init__.py
src/erre_sandbox/cognition/state.py
src/erre_sandbox/cognition/parse.py
src/erre_sandbox/cognition/_trait_antagonism.py
src/erre_sandbox/cognition/relational.py
src/erre_sandbox/cognition/belief.py
tests/test_integration/test_gateway.py
tests/test_integration/test_scenario_tick_robustness.py
tests/test_integration/_ws_helpers.py
tests/test_integration/conftest.py
tests/test_integration/test_world_layout_msg.py
tests/test_integration/test_slice_delta_e2e.py
tests/test_integration/test_scenario_memory_write.py
tests/test_integration/test_multi_agent_stream.py
tests/test_integration/__init__.py
src/erre_sandbox/ui/__init__.py
src/erre_sandbox/memory/embedding.py
src/erre_sandbox/memory/store.py
src/erre_sandbox/memory/__init__.py
tests/test_integration/test_dialog_orchestration_wiring.py
src/erre_sandbox/memory/retrieval.py
tests/test_integration/test_slice_gamma_e2e.py
tests/test_integration/test_dialog_sink.py
tests/test_integration/test_dialog_turn.py
tests/test_integration/test_dialog.py
tests/test_integration/test_contract_snapshot.py
tests/test_integration/test_scenario_walking.py
src/erre_sandbox/ui/dashboard/state.py
src/erre_sandbox/ui/dashboard/stub.py
src/erre_sandbox/ui/dashboard/__main__.py
src/erre_sandbox/ui/dashboard/messages.py
src/erre_sandbox/ui/dashboard/__init__.py
src/erre_sandbox/ui/dashboard/html.py
src/erre_sandbox/ui/dashboard/server.py
src/erre_sandbox/evidence/__init__.py
src/erre_sandbox/evidence/scaling_metrics.py
src/erre_sandbox/evidence/metrics.py
tests/test_evidence/__init__.py
tests/test_evidence/test_metrics.py
tests/test_evidence/test_scaling_metrics.py

exec
/bin/zsh -lc "rg -n \"training|loader|dialog_turns|iter_dialog_turns|InMemoryDialogScheduler|MemoryStore|evaluation_epoch|duckdb|metrics\\.\" src/erre_sandbox tests .github pyproject.toml" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
src/erre_sandbox/__main__.py:10:sqlite ``dialog_turns`` table as JSONL — see
src/erre_sandbox/__main__.py:123:    baseline_metrics.register(subparsers)
src/erre_sandbox/__main__.py:124:    scaling_metrics.register(subparsers)
src/erre_sandbox/__main__.py:190:            return baseline_metrics.run(args)
src/erre_sandbox/__main__.py:192:            return scaling_metrics.run(args)
tests/test_cli_export_log.py:4:``run()`` path (``MemoryStore`` creation + ``iter_dialog_turns`` + JSONL
tests/test_cli_export_log.py:17:from erre_sandbox.memory import MemoryStore
tests/test_cli_export_log.py:23:    store = MemoryStore(db_path=db_path)
tests/test_cli_export_log.py:58:    assert "dialog_turns" in out or "JSONL" in out
src/erre_sandbox/inference/ollama_adapter.py:55:    Constraining ``role`` to the three values Ollama accepts keeps callers
tests/test_schemas_m7g.py:52:    ``dialog_turns.epoch_phase`` column, M7ζ bumps for additive panel
tests/test_cognition/test_biorhythm_events.py:42:    from erre_sandbox.memory import EmbeddingClient, MemoryStore, Retriever
tests/test_cognition/test_biorhythm_events.py:174:    cognition_store: MemoryStore,
tests/test_cognition/test_biorhythm_events.py:220:    cognition_store: MemoryStore,
tests/test_cognition/test_biorhythm_events.py:256:    cognition_store: MemoryStore,
tests/test_ui/test_state.py:134:    assert metrics.sample_count == 6
tests/test_cognition/test_reasoning_trace.py:35:    from erre_sandbox.memory import EmbeddingClient, MemoryStore, Retriever
tests/test_cognition/test_reasoning_trace.py:108:    cognition_store: MemoryStore,
tests/test_cognition/test_reasoning_trace.py:153:    cognition_store: MemoryStore,
tests/test_cognition/test_reasoning_trace.py:214:    cognition_store: MemoryStore,
tests/test_cognition/test_reasoning_trace.py:246:    cognition_store: MemoryStore,
tests/test_cognition/test_erre_mode_events.py:38:    from erre_sandbox.memory import EmbeddingClient, MemoryStore, Retriever
tests/test_cognition/test_erre_mode_events.py:92:    cognition_store: MemoryStore,
tests/test_cognition/test_erre_mode_events.py:143:    cognition_store: MemoryStore,
tests/test_cognition/test_erre_mode_events.py:177:    cognition_store: MemoryStore,
tests/test_cognition/test_erre_mode_events.py:213:    cognition_store: MemoryStore,
tests/test_memory/test_semantic_layer.py:1:"""Unit tests for the m4-memory-semantic-layer API on :class:`MemoryStore`.
tests/test_memory/test_semantic_layer.py:15:from erre_sandbox.memory.store import MemoryStore
tests/test_memory/test_semantic_layer.py:31:    store = MemoryStore(db_path=":memory:")
tests/test_memory/test_semantic_layer.py:47:    store = MemoryStore(db_path=db)
tests/test_memory/test_semantic_layer.py:93:    store = MemoryStore(db_path=db)
tests/test_memory/test_semantic_layer.py:113:    store = MemoryStore(db_path=":memory:")
tests/test_memory/test_semantic_layer.py:166:    store = MemoryStore(db_path=db)
tests/test_memory/test_semantic_layer.py:184:    store = MemoryStore(db_path=db)
tests/test_memory/test_semantic_layer.py:198:    store: MemoryStore,
tests/test_memory/test_semantic_layer.py:223:    store: MemoryStore,
tests/test_memory/test_semantic_layer.py:251:    store: MemoryStore,
tests/test_memory/test_semantic_layer.py:269:    store: MemoryStore,
tests/test_memory/test_semantic_layer.py:291:    store: MemoryStore,
tests/test_memory/test_semantic_layer.py:300:    store: MemoryStore,
tests/test_memory/test_semantic_layer.py:338:    store: MemoryStore,
tests/test_memory/test_semantic_layer.py:345:    store: MemoryStore,
tests/test_memory/test_semantic_layer.py:367:    store: MemoryStore,
tests/test_memory/test_semantic_layer.py:392:    store: MemoryStore,
tests/test_memory/test_semantic_layer.py:400:    store: MemoryStore,
tests/test_cognition/test_cycle_erre_fsm.py:36:    from erre_sandbox.memory import EmbeddingClient, MemoryStore, Retriever
tests/test_cognition/test_cycle_erre_fsm.py:83:    store: MemoryStore,
tests/test_cognition/test_cycle_erre_fsm.py:106:    cognition_store: MemoryStore,
tests/test_cognition/test_cycle_erre_fsm.py:135:    cognition_store: MemoryStore,
tests/test_cognition/test_cycle_erre_fsm.py:172:    cognition_store: MemoryStore,
tests/test_cognition/test_cycle_erre_fsm.py:203:    cognition_store: MemoryStore,
tests/test_cognition/test_cycle_erre_fsm.py:238:    cognition_store: MemoryStore,
tests/test_cognition/test_cycle_erre_fsm.py:269:    cognition_store: MemoryStore,
tests/test_cognition/test_cycle_erre_fsm.py:312:    cognition_store: MemoryStore,
tests/test_cognition/test_cycle_erre_fsm.py:357:    cognition_store: MemoryStore,
tests/test_cognition/test_cycle_erre_fsm.py:406:    cognition_store: MemoryStore,
tests/test_cognition/conftest.py:5:touch a real Ollama server. The real :class:`MemoryStore` and
tests/test_cognition/conftest.py:19:from erre_sandbox.memory import EmbeddingClient, MemoryStore, Retriever
tests/test_cognition/conftest.py:133:async def cognition_store() -> AsyncIterator[MemoryStore]:
tests/test_cognition/conftest.py:134:    s = MemoryStore(db_path=":memory:")
tests/test_cognition/conftest.py:144:    cognition_store: MemoryStore,
tests/test_evidence/test_scaling_metrics.py:5:fresh on-disk MemoryStore + temp NDJSON journal so the sqlite I/O and
tests/test_evidence/test_scaling_metrics.py:36:from erre_sandbox.memory.store import MemoryStore
tests/test_evidence/test_scaling_metrics.py:374:    assert result["num_dialog_turns"] == 0
tests/test_evidence/test_scaling_metrics.py:387:    store = MemoryStore(db_path=db_path)
tests/test_evidence/test_scaling_metrics.py:417:    assert result["num_dialog_turns"] == 6
tests/test_evidence/test_scaling_metrics.py:435:    store = MemoryStore(db_path=db_path)
tests/test_evidence/test_scaling_metrics.py:478:    store = MemoryStore(db_path=db_path)
tests/test_evidence/test_scaling_metrics.py:527:    store = MemoryStore(db_path=db_path)
tests/test_evidence/test_scaling_metrics.py:573:    # Only the 6 autonomous turns drive metrics.
tests/test_evidence/test_scaling_metrics.py:574:    assert result["num_dialog_turns"] == 6
tests/test_evidence/test_scaling_metrics.py:584:    baseline_store = MemoryStore(db_path=baseline_db)
tests/test_evidence/test_scaling_metrics.py:611:    legacy DB whose ``dialog_turns`` rows pre-date the column must read
tests/test_evidence/test_scaling_metrics.py:616:    store = MemoryStore(db_path=db_path)
tests/test_evidence/test_scaling_metrics.py:627:                "INSERT INTO dialog_turns(id, dialog_id, tick, turn_index, "
tests/test_evidence/test_scaling_metrics.py:648:    assert result["num_dialog_turns"] == 6
src/erre_sandbox/cli/baseline_metrics.py:3:Reads the sqlite ``dialog_turns`` + ``bias_events`` tables populated by the
src/erre_sandbox/cli/baseline_metrics.py:35:            "bias_fired_rate from the sqlite ``dialog_turns`` + "
tests/test_cognition/test_movement_speed_persona_factor.py:23:    from erre_sandbox.memory import EmbeddingClient, MemoryStore, Retriever
tests/test_cognition/test_movement_speed_persona_factor.py:30:    store: MemoryStore,
tests/test_cognition/test_movement_speed_persona_factor.py:59:    cognition_store: MemoryStore,
src/erre_sandbox/cli/scaling_metrics.py:3:Reads the sqlite ``dialog_turns`` table populated by the M8 L6-D1 sink
src/erre_sandbox/cli/scaling_metrics.py:39:            "zone_kl_from_uniform from the sqlite ``dialog_turns`` table and "
tests/test_evidence/test_metrics.py:5:via a fresh in-memory MemoryStore so its sqlite I/O path is covered end
tests/test_evidence/test_metrics.py:21:from erre_sandbox.memory.store import MemoryStore
tests/test_evidence/test_metrics.py:145:    """End-to-end: seed dialog_turns + bias_events, aggregate, assert shape."""
tests/test_evidence/test_metrics.py:149:    store = MemoryStore(db_path=db_path)
tests/test_cognition/test_reflection_envelope.py:42:    from erre_sandbox.memory import EmbeddingClient, MemoryStore, Retriever
tests/test_cognition/test_reflection_envelope.py:65:        recent_dialog_turns: Any = (),
tests/test_cognition/test_reflection_envelope.py:67:        del agent_state, persona, observations, importance_sum, recent_dialog_turns
tests/test_cognition/test_reflection_envelope.py:80:    cognition_store: MemoryStore,
tests/test_cognition/test_reflection_envelope.py:129:    cognition_store: MemoryStore,
tests/test_memory/test_store.py:12:from erre_sandbox.memory.store import MemoryStore, _dt_to_text
tests/test_memory/test_store.py:29:    store: MemoryStore,
tests/test_memory/test_store.py:62:    store: MemoryStore,
tests/test_memory/test_store.py:71:    store: MemoryStore,
tests/test_memory/test_store.py:85:    store: MemoryStore,
tests/test_memory/test_store.py:104:    store: MemoryStore,
tests/test_memory/test_store.py:123:    store: MemoryStore,
tests/test_memory/test_store.py:154:    store: MemoryStore,
tests/test_memory/test_store.py:167:    store: MemoryStore,
tests/test_memory/test_store.py:188:    store: MemoryStore,
tests/test_memory/test_store.py:195:    store: MemoryStore,
tests/test_memory/test_store.py:235:async def test_get_by_id_missing_returns_none(store: MemoryStore) -> None:
tests/test_memory/test_store.py:245:    store: MemoryStore,
tests/test_memory/test_store.py:301:def test_add_dialog_turn_inserts_row(store: MemoryStore) -> None:
tests/test_memory/test_store.py:310:    rows = list(store.iter_dialog_turns())
tests/test_memory/test_store.py:320:def test_add_dialog_turn_is_idempotent_on_duplicate(store: MemoryStore) -> None:
tests/test_memory/test_store.py:335:    rows = list(store.iter_dialog_turns())
tests/test_memory/test_store.py:340:def test_iter_dialog_turns_filters_by_persona(store: MemoryStore) -> None:
tests/test_memory/test_store.py:357:    kant_rows = list(store.iter_dialog_turns(persona="kant"))
tests/test_memory/test_store.py:360:    rikyu_rows = list(store.iter_dialog_turns(persona="rikyu"))
tests/test_memory/test_store.py:363:    all_rows = list(store.iter_dialog_turns())
tests/test_memory/test_store.py:367:def test_iter_dialog_turns_filters_by_since(store: MemoryStore) -> None:
tests/test_memory/test_store.py:376:    assert list(store.iter_dialog_turns(since=future)) == []
tests/test_memory/test_store.py:380:    rows = list(store.iter_dialog_turns(since=past))
tests/test_memory/test_store.py:389:def test_iter_dialog_turns_excludes_persona(store: MemoryStore) -> None:
tests/test_memory/test_store.py:397:    rows = list(store.iter_dialog_turns(exclude_persona="kant"))
tests/test_memory/test_store.py:402:def test_iter_dialog_turns_limit_returns_most_recent_in_desc(
tests/test_memory/test_store.py:403:    store: MemoryStore,
tests/test_memory/test_store.py:412:    rows = list(store.iter_dialog_turns(limit=3))
tests/test_memory/test_store.py:417:def test_iter_dialog_turns_exclude_persona_and_limit_combine(
tests/test_memory/test_store.py:418:    store: MemoryStore,
tests/test_memory/test_store.py:429:    rows = list(store.iter_dialog_turns(exclude_persona="kant", limit=2))
tests/test_memory/test_store.py:435:def test_iter_dialog_turns_pushes_filter_and_limit_into_sqlite(
tests/test_memory/test_store.py:436:    store: MemoryStore,
tests/test_memory/test_store.py:458:        list(store.iter_dialog_turns(exclude_persona="kant", limit=3))
tests/test_memory/test_store.py:462:    dialog_sql = [s for s in captured if "FROM dialog_turns" in s]
tests/test_memory/test_store.py:463:    assert len(dialog_sql) == 1, f"expected one dialog_turns query, got {dialog_sql}"
tests/test_memory/test_store.py:474:def test_dialog_turn_count_by_persona_query(store: MemoryStore) -> None:
tests/test_memory/test_store.py:488:            "FROM dialog_turns GROUP BY speaker_persona_id ORDER BY turns DESC",
tests/test_memory/test_store.py:495:# M7ε — dialog_turns.epoch_phase column + migration
tests/test_memory/test_store.py:499:def test_dialog_turns_schema_has_epoch_phase_column(store: MemoryStore) -> None:
tests/test_memory/test_store.py:502:    cols = {row["name"] for row in conn.execute("PRAGMA table_info(dialog_turns)")}
tests/test_memory/test_store.py:506:def test_migrate_dialog_turns_schema_is_idempotent(store: MemoryStore) -> None:
tests/test_memory/test_store.py:507:    """Running ``_migrate_dialog_turns_schema`` twice is a no-op (M7ε D4)."""
tests/test_memory/test_store.py:510:    MemoryStore._migrate_dialog_turns_schema(conn)
tests/test_memory/test_store.py:511:    cols = {row["name"] for row in conn.execute("PRAGMA table_info(dialog_turns)")}
tests/test_memory/test_store.py:515:def test_migrate_dialog_turns_schema_adds_column_to_pre_m7e_db(
tests/test_memory/test_store.py:523:    # Build an old-shape ``dialog_turns`` table by hand (no ``epoch_phase``).
tests/test_memory/test_store.py:528:            CREATE TABLE dialog_turns (
tests/test_memory/test_store.py:544:            "INSERT INTO dialog_turns(id, dialog_id, tick, turn_index, "
tests/test_memory/test_store.py:565:    # Open via MemoryStore; create_schema() applies the migration.
tests/test_memory/test_store.py:566:    upgraded = MemoryStore(db_path=db_path)
tests/test_memory/test_store.py:570:        cols = {row["name"] for row in conn.execute("PRAGMA table_info(dialog_turns)")}
tests/test_memory/test_store.py:573:        rows = list(upgraded.iter_dialog_turns())
tests/test_memory/test_store.py:584:def test_add_dialog_turn_stamps_default_autonomous(store: MemoryStore) -> None:
tests/test_memory/test_store.py:593:    rows = list(store.iter_dialog_turns())
tests/test_memory/test_store.py:598:def test_add_dialog_turn_stamps_explicit_q_and_a(store: MemoryStore) -> None:
tests/test_memory/test_store.py:608:    rows = list(store.iter_dialog_turns())
tests/test_memory/test_store.py:613:def test_iter_dialog_turns_filters_by_epoch_phase_autonomous(
tests/test_memory/test_store.py:614:    store: MemoryStore,
tests/test_memory/test_store.py:634:            "INSERT INTO dialog_turns(id, dialog_id, tick, turn_index, "
tests/test_memory/test_store.py:653:    autonomous_rows = list(store.iter_dialog_turns(epoch_phase=EpochPhase.AUTONOMOUS))
tests/test_memory/test_store.py:657:    qa_rows = list(store.iter_dialog_turns(epoch_phase=EpochPhase.Q_AND_A))
tests/test_memory/test_store.py:662:    all_rows = list(store.iter_dialog_turns())
tests/test_memory/test_store.py:672:    store: MemoryStore,
tests/test_memory/test_store.py:691:def test_add_bias_event_inserts_row(store: MemoryStore) -> None:
tests/test_memory/test_store.py:705:def test_add_bias_event_allows_multiple_per_tick(store: MemoryStore) -> None:
tests/test_memory/test_store.py:712:def test_iter_bias_events_filters_by_persona(store: MemoryStore) -> None:
tests/test_memory/test_store.py:724:def test_iter_bias_events_filters_by_since(store: MemoryStore) -> None:
tests/test_cli_baseline_metrics.py:18:from erre_sandbox.memory import MemoryStore
tests/test_cli_baseline_metrics.py:23:    store = MemoryStore(db_path=db_path)
src/erre_sandbox/cli/export_log.py:1:"""``erre-sandbox export-log`` — dump ``dialog_turns`` to JSONL.
src/erre_sandbox/cli/export_log.py:3:Reads the sqlite ``dialog_turns`` table populated by the M8 L6-D1 sink
src/erre_sandbox/cli/export_log.py:5:rows as newline-delimited JSON. Consumed by the M9 LoRA training pipeline
src/erre_sandbox/cli/export_log.py:25:from erre_sandbox.memory import MemoryStore
src/erre_sandbox/cli/export_log.py:35:        help="Export dialog_turns log to JSONL (M8 L6-D1 precondition).",
src/erre_sandbox/cli/export_log.py:37:            "Stream the contents of the sqlite ``dialog_turns`` table as "
src/erre_sandbox/cli/export_log.py:38:            "newline-delimited JSON. Intended for M9 LoRA training-data "
src/erre_sandbox/cli/export_log.py:113:    store = MemoryStore(db_path=args.db_path)
src/erre_sandbox/cli/export_log.py:121:        for row in store.iter_dialog_turns(persona=args.persona, since=since):
tests/test_cognition/test_cycle.py:26:    from erre_sandbox.memory import EmbeddingClient, MemoryStore, Retriever
tests/test_cognition/test_cycle.py:33:    store: MemoryStore,
tests/test_cognition/test_cycle.py:51:    cognition_store: MemoryStore,
tests/test_cognition/test_cycle.py:89:    cognition_store: MemoryStore,
tests/test_cognition/test_cycle.py:123:    cognition_store: MemoryStore,
tests/test_cognition/test_cycle.py:157:    cognition_store: MemoryStore,
tests/test_cognition/test_cycle.py:189:    cognition_store: MemoryStore,
tests/test_cognition/test_cycle.py:236:    cognition_store: MemoryStore,
tests/test_cognition/test_cycle.py:266:    cognition_store: MemoryStore,
tests/test_cognition/test_cycle.py:298:    cognition_store: MemoryStore,
tests/test_cognition/test_cycle.py:331:    cognition_store: MemoryStore,
tests/test_cognition/test_cycle.py:375:    cognition_store: MemoryStore,
tests/test_memory/test_retrieval.py:28:    from erre_sandbox.memory.store import MemoryStore
tests/test_memory/test_retrieval.py:128:    store: MemoryStore,
tests/test_memory/test_retrieval.py:158:    store: MemoryStore,
tests/test_memory/test_retrieval.py:178:    store: MemoryStore,
tests/test_memory/test_retrieval.py:194:    store: MemoryStore,
src/erre_sandbox/cognition/belief.py:163:    id so the caller's :meth:`MemoryStore.upsert_semantic` overwrites
tests/test_cognition/test_reflection.py:11::class:`MemoryStore`, so the suite never touches a real Ollama server.
tests/test_cognition/test_reflection.py:36:    from erre_sandbox.memory import EmbeddingClient, MemoryStore
tests/test_cognition/test_reflection.py:96:    cognition_store: MemoryStore,
tests/test_cognition/test_reflection.py:124:    store: MemoryStore,
tests/test_cognition/test_reflection.py:146:    cognition_store: MemoryStore,
tests/test_cognition/test_reflection.py:181:    cognition_store: MemoryStore,
tests/test_cognition/test_reflection.py:221:    cognition_store: MemoryStore,
tests/test_cognition/test_reflection.py:258:    cognition_store: MemoryStore,
tests/test_cognition/test_reflection.py:297:    cognition_store: MemoryStore,
tests/test_cognition/test_reflection.py:331:    cognition_store: MemoryStore,
tests/test_cognition/test_reflection.py:366:    cognition_store: MemoryStore,
tests/test_cognition/test_reflection.py:409:    cognition_store: MemoryStore,
tests/test_cognition/test_reflection.py:451:    cognition_store: MemoryStore,
tests/test_cognition/test_reflection.py:490:    cognition_store: MemoryStore,
tests/test_cognition/test_reflection.py:533:    cognition_store: MemoryStore,
tests/test_cognition/test_reflection.py:655:        recent_dialog_turns=[peer_turn],
tests/test_cognition/test_reflection.py:685:        recent_dialog_turns=[peer_turn],
tests/test_cognition/test_reflection.py:713:        recent_dialog_turns=[peer_turn],
src/erre_sandbox/memory/retrieval.py:32:    from erre_sandbox.memory.store import MemoryStore
src/erre_sandbox/memory/retrieval.py:87:    """Composes :class:`MemoryStore` and :class:`EmbeddingClient`.
src/erre_sandbox/memory/retrieval.py:105:        store: MemoryStore,
src/erre_sandbox/cognition/cycle.py:86:    from erre_sandbox.memory import MemoryStore, RankedMemory, Retriever
src/erre_sandbox/cognition/cycle.py:226:        store: MemoryStore,
src/erre_sandbox/cognition/cycle.py:286:        # that persists events via ``MemoryStore.add_bias_event_sync``
src/erre_sandbox/cognition/cycle.py:481:            recent_dialog_turns=recent_peer_turns,
src/erre_sandbox/cognition/cycle.py:757:        Reads ``dialog_turns`` rows synchronously off the event loop via
src/erre_sandbox/cognition/cycle.py:763:        :meth:`MemoryStore.iter_dialog_turns(exclude_persona, limit)` so
src/erre_sandbox/cognition/cycle.py:766:        0.3 calls/s pace) is gone. ``iter_dialog_turns`` returns the most
src/erre_sandbox/cognition/cycle.py:771:        dicts produced by :meth:`MemoryStore.iter_dialog_turns`. The
src/erre_sandbox/cognition/cycle.py:779:                    self._store.iter_dialog_turns(
src/erre_sandbox/cognition/cycle.py:787:                "iter_dialog_turns failed for peer turns (%s); skipping reflection D1",
tests/test_memory/conftest.py:11:from erre_sandbox.memory.store import MemoryStore
tests/test_memory/conftest.py:19:async def store() -> AsyncIterator[MemoryStore]:
tests/test_memory/conftest.py:20:    """In-memory :class:`MemoryStore` with the 4 tables + vec0 ready to use."""
tests/test_memory/conftest.py:21:    s = MemoryStore(db_path=":memory:")
src/erre_sandbox/ui/dashboard/state.py:145:        if metrics.sample_count < WARMING_UP_COUNT:
src/erre_sandbox/ui/dashboard/state.py:152:            metrics.latency_p50_ms is not None
src/erre_sandbox/ui/dashboard/state.py:153:            and metrics.latency_p50_ms > self.thresholds.latency_p50_ms_max
src/erre_sandbox/ui/dashboard/state.py:159:                    current=metrics.latency_p50_ms,
src/erre_sandbox/ui/dashboard/state.py:164:            metrics.latency_p95_ms is not None
src/erre_sandbox/ui/dashboard/state.py:165:            and metrics.latency_p95_ms > self.thresholds.latency_p95_ms_max
src/erre_sandbox/ui/dashboard/state.py:171:                    current=metrics.latency_p95_ms,
src/erre_sandbox/ui/dashboard/state.py:176:            metrics.tick_jitter_sigma is not None
src/erre_sandbox/ui/dashboard/state.py:177:            and metrics.tick_jitter_sigma > self.thresholds.tick_jitter_sigma_max
src/erre_sandbox/ui/dashboard/state.py:183:                    current=metrics.tick_jitter_sigma,
src/erre_sandbox/world/tick.py:292:    """One in-flight turn request staged by :meth:`WorldRuntime._drive_dialog_turns`.
src/erre_sandbox/world/tick.py:389:        # at the end of each cognition tick via ``_drive_dialog_turns``. When
src/erre_sandbox/world/tick.py:568:        # synchronously inside ``InMemoryDialogScheduler.record_turn``.
src/erre_sandbox/world/tick.py:1082:            await self._drive_dialog_turns(self._current_world_tick())
src/erre_sandbox/world/tick.py:1098:        # :class:`InMemoryDialogScheduler`. Callers supplying a custom
src/erre_sandbox/world/tick.py:1113:        Shared by ``_run_dialog_tick``, ``_drive_dialog_turns``, and
src/erre_sandbox/world/tick.py:1131:    async def _drive_dialog_turns(self, world_tick: int) -> None:
src/erre_sandbox/world/tick.py:1136:        consults :meth:`InMemoryDialogScheduler.iter_open_dialogs` and:
src/erre_sandbox/world/tick.py:1150:           :meth:`InMemoryDialogScheduler.record_turn` (updates transcript and
src/erre_sandbox/world/tick.py:1169:        pending = self._stage_dialog_turns(
src/erre_sandbox/world/tick.py:1213:    def _stage_dialog_turns(
src/erre_sandbox/world/tick.py:1225:        :meth:`_drive_dialog_turns` then runs under ``asyncio.gather``.
src/erre_sandbox/memory/__init__.py:5:* :class:`MemoryStore` — persistence for 4 memory kinds + shared vec0 table
src/erre_sandbox/memory/__init__.py:31:from erre_sandbox.memory.store import DEFAULT_EMBED_DIM, MemoryStore
src/erre_sandbox/memory/__init__.py:44:    "MemoryStore",
src/erre_sandbox/evidence/metrics.py:23:``list[dict]`` without spinning up a MemoryStore. ``aggregate(path)`` is
src/erre_sandbox/evidence/metrics.py:225:    Reads every ``dialog_turns`` row and every ``bias_events`` row, then
src/erre_sandbox/evidence/metrics.py:235:    from erre_sandbox.memory.store import MemoryStore  # noqa: PLC0415
src/erre_sandbox/evidence/metrics.py:237:    store = MemoryStore(db_path=run_db_path)
src/erre_sandbox/evidence/metrics.py:240:        turns = list(store.iter_dialog_turns())
src/erre_sandbox/evidence/metrics.py:243:        # ``MemoryStore.close`` is async — reach through to the raw sqlite
src/erre_sandbox/cognition/reflection.py:8::meth:`MemoryStore.upsert_semantic`, and returns the corresponding
src/erre_sandbox/cognition/reflection.py:49:    from erre_sandbox.memory import EmbeddingClient, MemoryStore
src/erre_sandbox/cognition/reflection.py:136:    recent_dialog_turns: Sequence[DialogTurnMsg] = (),
src/erre_sandbox/cognition/reflection.py:149:    M7γ: when ``recent_dialog_turns`` is non-empty, a "Recent peer
src/erre_sandbox/cognition/reflection.py:178:    if recent_dialog_turns:
src/erre_sandbox/cognition/reflection.py:180:        for turn in recent_dialog_turns:
src/erre_sandbox/cognition/reflection.py:216:        store: MemoryStore,
src/erre_sandbox/cognition/reflection.py:258:        recent_dialog_turns: Sequence[DialogTurnMsg] = (),
src/erre_sandbox/cognition/reflection.py:266:        ``recent_dialog_turns`` (M7γ D1): up to three recent turns from
src/erre_sandbox/cognition/reflection.py:286:            recent_dialog_turns=recent_dialog_turns,
src/erre_sandbox/cognition/reflection.py:297:        recent_dialog_turns: Sequence[DialogTurnMsg] = (),
src/erre_sandbox/cognition/reflection.py:315:            recent_dialog_turns=recent_dialog_turns,
src/erre_sandbox/memory/store.py:56:class MemoryStore:
src/erre_sandbox/memory/store.py:208:                # training milestone. ``persona_id`` is resolved at sink time
src/erre_sandbox/memory/store.py:214:                # ``scaling_metrics.aggregate()`` can drop ``Q_AND_A`` turns
src/erre_sandbox/memory/store.py:215:                # from relational-saturation metrics. Pre-migration rows read
src/erre_sandbox/memory/store.py:218:                # ``_migrate_dialog_turns_schema`` below.
src/erre_sandbox/memory/store.py:221:                    CREATE TABLE IF NOT EXISTS dialog_turns (
src/erre_sandbox/memory/store.py:239:                    CREATE INDEX IF NOT EXISTS ix_dialog_turns_persona
src/erre_sandbox/memory/store.py:240:                    ON dialog_turns(speaker_persona_id, created_at)
src/erre_sandbox/memory/store.py:243:                self._migrate_dialog_turns_schema(conn)
src/erre_sandbox/memory/store.py:310:    def _migrate_dialog_turns_schema(conn: sqlite3.Connection) -> None:
src/erre_sandbox/memory/store.py:311:        """Idempotently ensure ``dialog_turns`` carries the M7ε ``epoch_phase`` column.
src/erre_sandbox/memory/store.py:314:        ``scaling_metrics.aggregate()`` can filter to AUTONOMOUS turns per
src/erre_sandbox/memory/store.py:324:            row["name"] for row in conn.execute("PRAGMA table_info(dialog_turns)")
src/erre_sandbox/memory/store.py:328:                "ALTER TABLE dialog_turns ADD COLUMN epoch_phase TEXT",
src/erre_sandbox/memory/store.py:834:        """Persist ``turn`` into the ``dialog_turns`` table synchronously.
src/erre_sandbox/memory/store.py:836:        Intended for the :class:`InMemoryDialogScheduler` sink which runs on
src/erre_sandbox/memory/store.py:842:        so ``scaling_metrics.aggregate()`` can drop ``Q_AND_A`` turns
src/erre_sandbox/memory/store.py:843:        from relational-saturation metrics. Defaults to ``AUTONOMOUS`` so
src/erre_sandbox/memory/store.py:859:                    "INSERT OR IGNORE INTO dialog_turns("
src/erre_sandbox/memory/store.py:902:    def iter_dialog_turns(
src/erre_sandbox/memory/store.py:916:          speaker-scoped for LoRA training-data semantics).
src/erre_sandbox/memory/store.py:977:                f"FROM dialog_turns {where} "
src/erre_sandbox/memory/store.py:1157:    "MemoryStore",
src/erre_sandbox/contracts/thresholds.py:5:narrative (``.steering/20260419-m2-integration-e2e/metrics.md``) explains the
src/erre_sandbox/integration/dialog.py:79:class InMemoryDialogScheduler:
src/erre_sandbox/integration/dialog.py:113:        # ``MemoryStore.add_dialog_turn_sync`` closure (with agent_id →
src/erre_sandbox/integration/dialog.py:115:        # sqlite for later LoRA-training export. Left None for unit tests
src/erre_sandbox/integration/dialog.py:356:    "InMemoryDialogScheduler",
src/erre_sandbox/evidence/scaling_metrics.py:28:``list[dict]`` data without spinning up a MemoryStore. ``aggregate(...)``
src/erre_sandbox/evidence/scaling_metrics.py:383:        raw = metrics.get(candidate)
src/erre_sandbox/evidence/scaling_metrics.py:554:       turns drive the relational-saturation metrics. Q&A epoch turns
src/erre_sandbox/evidence/scaling_metrics.py:559:       (see ``MemoryStore.iter_dialog_turns`` docstring).
src/erre_sandbox/evidence/scaling_metrics.py:563:    from erre_sandbox.memory.store import MemoryStore  # noqa: PLC0415
src/erre_sandbox/evidence/scaling_metrics.py:566:    store = MemoryStore(db_path=run_db_path)
src/erre_sandbox/evidence/scaling_metrics.py:570:            store.iter_dialog_turns(epoch_phase=EpochPhase.AUTONOMOUS),
src/erre_sandbox/evidence/scaling_metrics.py:573:        conn = store._conn  # noqa: SLF001 — sync close mirrors evidence.metrics.aggregate
src/erre_sandbox/evidence/scaling_metrics.py:632:        "num_dialog_turns": len(turns),
src/erre_sandbox/bootstrap.py:34:from erre_sandbox.integration.dialog import InMemoryDialogScheduler
src/erre_sandbox/bootstrap.py:37:from erre_sandbox.memory import EmbeddingClient, MemoryStore, Retriever
src/erre_sandbox/bootstrap.py:191:    memory: MemoryStore,
src/erre_sandbox/bootstrap.py:255:    memory: MemoryStore,
src/erre_sandbox/bootstrap.py:261:    :class:`InMemoryDialogScheduler.record_turn`: it inserts a
src/erre_sandbox/bootstrap.py:416:        memory = MemoryStore(db_path=cfg.db_path)
src/erre_sandbox/bootstrap.py:502:        # sqlite ``dialog_turns`` for later LoRA-training export. The closure
src/erre_sandbox/bootstrap.py:505:        # are caught inside ``InMemoryDialogScheduler.record_turn`` so a
src/erre_sandbox/bootstrap.py:522:            # turn so ``scaling_metrics.aggregate()`` can drop ``Q_AND_A``
src/erre_sandbox/bootstrap.py:552:        scheduler = InMemoryDialogScheduler(
tests/test_integration/test_slice_gamma_e2e.py:5:1. ``InMemoryDialogScheduler.record_turn`` invokes the relational sink
tests/test_integration/test_slice_gamma_e2e.py:8:   :class:`MemoryStore` and applies a bidirectional ``apply_affinity_delta``
tests/test_integration/test_slice_gamma_e2e.py:40:from erre_sandbox.integration.dialog import InMemoryDialogScheduler
tests/test_integration/test_slice_gamma_e2e.py:41:from erre_sandbox.memory import MemoryStore
tests/test_integration/test_slice_gamma_e2e.py:103:async def store() -> AsyncIterator[MemoryStore]:
tests/test_integration/test_slice_gamma_e2e.py:104:    s = MemoryStore(db_path=":memory:")
tests/test_integration/test_slice_gamma_e2e.py:117:def _open_dialog(scheduler: InMemoryDialogScheduler, *, tick: int) -> str:
tests/test_integration/test_slice_gamma_e2e.py:130:    store: MemoryStore,
tests/test_integration/test_slice_gamma_e2e.py:140:    scheduler = InMemoryDialogScheduler(
tests/test_integration/test_slice_gamma_e2e.py:240:    store: MemoryStore,
tests/test_integration/test_slice_gamma_e2e.py:256:    scheduler = InMemoryDialogScheduler(
src/erre_sandbox/integration/__init__.py:33:from erre_sandbox.integration.dialog import AgentView, InMemoryDialogScheduler
src/erre_sandbox/integration/__init__.py:67:    "InMemoryDialogScheduler",
tests/test_integration/test_slice_delta_e2e.py:43:from erre_sandbox.integration.dialog import InMemoryDialogScheduler
tests/test_integration/test_slice_delta_e2e.py:44:from erre_sandbox.memory import MemoryStore
tests/test_integration/test_slice_delta_e2e.py:95:async def store() -> AsyncIterator[MemoryStore]:
tests/test_integration/test_slice_delta_e2e.py:96:    s = MemoryStore(db_path=":memory:")
tests/test_integration/test_slice_delta_e2e.py:108:def _open_dialog(scheduler: InMemoryDialogScheduler, *, tick: int) -> str:
tests/test_integration/test_slice_delta_e2e.py:121:    store: MemoryStore,
tests/test_integration/test_slice_delta_e2e.py:131:    scheduler = InMemoryDialogScheduler(envelope_sink=captured.append, turn_sink=sink)
tests/test_integration/test_slice_delta_e2e.py:175:    store: MemoryStore,
tests/test_integration/test_slice_delta_e2e.py:184:    scheduler = InMemoryDialogScheduler(envelope_sink=lambda _: None, turn_sink=sink)
tests/test_integration/test_slice_delta_e2e.py:207:    store: MemoryStore,
tests/test_integration/test_slice_delta_e2e.py:216:    scheduler = InMemoryDialogScheduler(envelope_sink=lambda _: None, turn_sink=sink)
tests/test_integration/test_slice_delta_e2e.py:240:    store: MemoryStore,
tests/test_integration/test_slice_delta_e2e.py:254:    scheduler = InMemoryDialogScheduler(envelope_sink=lambda _: None, turn_sink=sink)
tests/test_integration/test_slice_delta_e2e.py:293:    store: MemoryStore,
tests/test_integration/test_slice_delta_e2e.py:302:    scheduler = InMemoryDialogScheduler(envelope_sink=lambda _: None, turn_sink=sink)
tests/test_integration/test_slice_delta_e2e.py:342:    store: MemoryStore,
tests/test_integration/test_slice_delta_e2e.py:369:    scheduler = InMemoryDialogScheduler(envelope_sink=lambda _: None, turn_sink=sink)
tests/test_integration/test_slice_delta_e2e.py:391:    store: MemoryStore,
tests/test_integration/test_slice_delta_e2e.py:416:    scheduler = InMemoryDialogScheduler(envelope_sink=lambda _: None, turn_sink=sink)
tests/test_integration/conftest.py:47:    MemoryStore,
tests/test_integration/conftest.py:204:) -> AsyncIterator[tuple[MemoryStore, FakeEmbedder]]:
tests/test_integration/conftest.py:205:    """In-memory :class:`MemoryStore` paired with :class:`FakeEmbedder`.
tests/test_integration/conftest.py:210:    store = MemoryStore(":memory:")
tests/test_integration/test_dialog_sink.py:1:"""End-to-end: ``InMemoryDialogScheduler`` persists turns into ``MemoryStore``.
tests/test_integration/test_dialog_sink.py:3:Covers the M8 L6-D1 sink wiring. Opens an in-memory :class:`MemoryStore`,
tests/test_integration/test_dialog_sink.py:6:asserts the sqlite ``dialog_turns`` table contains the expected rows.
tests/test_integration/test_dialog_sink.py:15:from erre_sandbox.integration.dialog import InMemoryDialogScheduler
tests/test_integration/test_dialog_sink.py:16:from erre_sandbox.memory import MemoryStore
tests/test_integration/test_dialog_sink.py:31:async def store() -> MemoryStore:
tests/test_integration/test_dialog_sink.py:32:    s = MemoryStore(db_path=":memory:")
tests/test_integration/test_dialog_sink.py:38:def _make_sink(store: MemoryStore) -> Callable[[DialogTurnMsg], None]:
tests/test_integration/test_dialog_sink.py:52:    scheduler: InMemoryDialogScheduler,
tests/test_integration/test_dialog_sink.py:70:async def test_record_turn_persists_through_sink(store: MemoryStore) -> None:
tests/test_integration/test_dialog_sink.py:72:    scheduler = InMemoryDialogScheduler(
tests/test_integration/test_dialog_sink.py:96:    rows = list(store.iter_dialog_turns())
tests/test_integration/test_dialog_sink.py:103:    store: MemoryStore,  # noqa: ARG001  # fixture used for setup side effects only
tests/test_integration/test_dialog_sink.py:111:    scheduler = InMemoryDialogScheduler(
tests/test_integration/test_dialog.py:1:"""Unit tests for :class:`~erre_sandbox.integration.dialog.InMemoryDialogScheduler`.
tests/test_integration/test_dialog.py:18:    InMemoryDialogScheduler,
tests/test_integration/test_dialog.py:62:    scheduler = InMemoryDialogScheduler(envelope_sink=sink)
tests/test_integration/test_dialog.py:79:    scheduler = InMemoryDialogScheduler(envelope_sink=sink)
tests/test_integration/test_dialog.py:97:    scheduler = InMemoryDialogScheduler(envelope_sink=sink)
tests/test_integration/test_dialog.py:105:    scheduler = InMemoryDialogScheduler(envelope_sink=sink)
tests/test_integration/test_dialog.py:111:    scheduler = InMemoryDialogScheduler(envelope_sink=sink)
tests/test_integration/test_dialog.py:120:    scheduler = InMemoryDialogScheduler(envelope_sink=sink)
tests/test_integration/test_dialog.py:131:        tick=InMemoryDialogScheduler.COOLDOWN_TICKS - 1,
tests/test_integration/test_dialog.py:138:    scheduler = InMemoryDialogScheduler(envelope_sink=sink)
tests/test_integration/test_dialog.py:147:        tick=InMemoryDialogScheduler.COOLDOWN_TICKS + 1,
tests/test_integration/test_dialog.py:159:    scheduler = InMemoryDialogScheduler(envelope_sink=sink)
tests/test_integration/test_dialog.py:177:    scheduler = InMemoryDialogScheduler(envelope_sink=sink)
tests/test_integration/test_dialog.py:192:    scheduler = InMemoryDialogScheduler(envelope_sink=sink)
tests/test_integration/test_dialog.py:211:    scheduler = InMemoryDialogScheduler(envelope_sink=sink)
tests/test_integration/test_dialog.py:223:    scheduler = InMemoryDialogScheduler(envelope_sink=sink, rng=_fire(0.0))
tests/test_integration/test_dialog.py:235:    scheduler = InMemoryDialogScheduler(envelope_sink=sink, rng=_fire(0.99))
tests/test_integration/test_dialog.py:247:    scheduler = InMemoryDialogScheduler(envelope_sink=sink, rng=_fire(0.0))
tests/test_integration/test_dialog.py:254:    scheduler = InMemoryDialogScheduler(envelope_sink=sink, rng=_fire(0.0))
tests/test_integration/test_dialog.py:267:    scheduler = InMemoryDialogScheduler(envelope_sink=sink, rng=_fire(0.99))
tests/test_integration/test_dialog.py:271:        InMemoryDialogScheduler.TIMEOUT_TICKS + 1,
tests/test_integration/test_dialog.py:285:    scheduler = InMemoryDialogScheduler(envelope_sink=sink, rng=_fire(0.0))
tests/test_integration/test_dialog.py:292:    scheduler.tick(InMemoryDialogScheduler.TIMEOUT_TICKS + 1, views_same_zone)
tests/test_integration/test_dialog.py:296:    scheduler.tick(InMemoryDialogScheduler.TIMEOUT_TICKS + 2, views_same_zone)
tests/test_integration/test_dialog.py:307:    scheduler = InMemoryDialogScheduler(envelope_sink=sink)
tests/test_integration/test_dialog.py:313:    scheduler = InMemoryDialogScheduler(envelope_sink=sink)
tests/test_integration/test_dialog.py:327:    scheduler = InMemoryDialogScheduler(envelope_sink=sink)
tests/test_integration/test_dialog.py:338:    scheduler = InMemoryDialogScheduler(envelope_sink=sink)
tests/test_integration/test_dialog.py:353:    scheduler = InMemoryDialogScheduler(envelope_sink=sink, rng=_fire(0.0))
tests/test_integration/test_dialog.py:362:    cooldown = InMemoryDialogScheduler.COOLDOWN_TICKS
tests/test_integration/test_dialog.py:385:    scheduler = InMemoryDialogScheduler(envelope_sink=sink, rng=_fire(0.99))
tests/test_integration/test_dialog.py:387:    timeout_world_tick = InMemoryDialogScheduler.TIMEOUT_TICKS + 1
tests/test_integration/test_dialog.py:403:    scheduler = InMemoryDialogScheduler(envelope_sink=sink)
tests/test_integration/test_scenario_memory_write.py:1:"""S_MEMORY_WRITE scenario — Layer B2 via MemoryStore + FakeEmbedder.
tests/test_integration/test_scenario_memory_write.py:24:    from erre_sandbox.memory import MemoryStore
tests/test_integration/test_scenario_memory_write.py:49:    memory_store_with_fake_embedder: tuple[MemoryStore, FakeEmbedder],
tests/test_integration/test_dialog_turn.py:22:from erre_sandbox.integration.dialog import InMemoryDialogScheduler
tests/test_integration/test_dialog_turn.py:205:    scheduler = InMemoryDialogScheduler(envelope_sink=emitted.append)
tests/test_integration/test_dialog_orchestration_wiring.py:4:``_drive_dialog_turns`` step called from ``_on_cognition_tick``:
tests/test_integration/test_dialog_orchestration_wiring.py:12:The tests build a real :class:`InMemoryDialogScheduler` and a fake
tests/test_integration/test_dialog_orchestration_wiring.py:14:end-to-end without the LLM. The ``_drive_dialog_turns`` method is called
tests/test_integration/test_dialog_orchestration_wiring.py:24:from erre_sandbox.integration.dialog import InMemoryDialogScheduler
tests/test_integration/test_dialog_orchestration_wiring.py:102:) -> tuple[WorldRuntime, InMemoryDialogScheduler, list[ControlEnvelope]]:
tests/test_integration/test_dialog_orchestration_wiring.py:152:    scheduler = InMemoryDialogScheduler(envelope_sink=runtime.inject_envelope)
tests/test_integration/test_dialog_orchestration_wiring.py:158:    scheduler: InMemoryDialogScheduler,
tests/test_integration/test_dialog_orchestration_wiring.py:184:async def test_drive_dialog_turns_generates_when_under_budget(
tests/test_integration/test_dialog_orchestration_wiring.py:199:    await runtime._drive_dialog_turns(world_tick=1)
tests/test_integration/test_dialog_orchestration_wiring.py:213:async def test_drive_dialog_turns_closes_with_exhausted_when_budget_hit(
tests/test_integration/test_dialog_orchestration_wiring.py:239:    await runtime._drive_dialog_turns(world_tick=10)
tests/test_integration/test_dialog_orchestration_wiring.py:257:async def test_drive_dialog_turns_speaker_alternation(
tests/test_integration/test_dialog_orchestration_wiring.py:273:    await runtime._drive_dialog_turns(world_tick=1)
tests/test_integration/test_dialog_orchestration_wiring.py:278:    await runtime._drive_dialog_turns(world_tick=2)
tests/test_integration/test_dialog_orchestration_wiring.py:283:    await runtime._drive_dialog_turns(world_tick=3)
tests/test_integration/test_dialog_orchestration_wiring.py:292:async def test_drive_dialog_turns_none_return_emits_nothing(
tests/test_integration/test_dialog_orchestration_wiring.py:310:    await runtime._drive_dialog_turns(world_tick=1)
tests/test_integration/test_dialog_orchestration_wiring.py:318:async def test_drive_dialog_turns_exception_does_not_break_siblings(
tests/test_integration/test_dialog_orchestration_wiring.py:356:    await runtime._drive_dialog_turns(world_tick=1)
tests/test_integration/test_dialog_orchestration_wiring.py:373:async def test_drive_dialog_turns_without_generator_is_noop(
tests/test_integration/test_dialog_orchestration_wiring.py:385:    await runtime._drive_dialog_turns(world_tick=1)
tests/test_integration/test_dialog_orchestration_wiring.py:395:async def test_drive_dialog_turns_without_scheduler_is_noop() -> None:
tests/test_integration/test_dialog_orchestration_wiring.py:411:    await runtime._drive_dialog_turns(world_tick=1)
tests/test_integration/test_dialog_orchestration_wiring.py:420:async def test_drive_dialog_turns_preserves_initiate_envelope(
tests/test_integration/test_dialog_orchestration_wiring.py:437:    await runtime._drive_dialog_turns(world_tick=1)
tests/test_integration/test_dialog_orchestration_wiring.py:450:async def test_drive_dialog_turns_works_after_participants_leave_zone(
tests/test_integration/test_dialog_orchestration_wiring.py:474:    await runtime._drive_dialog_turns(world_tick=1)
tests/test_integration/test_dialog_orchestration_wiring.py:518:async def test_drive_dialog_turns_budget_boundary(
tests/test_integration/test_dialog_orchestration_wiring.py:545:    await runtime._drive_dialog_turns(world_tick=10)

exec
/bin/zsh -lc "nl -ba src/erre_sandbox/integration/dialog.py | sed -n '253,380p'" in /Users/johnd/ERRE-Sand Box
exec
/bin/zsh -lc "nl -ba src/erre_sandbox/memory/store.py | sed -n '830,990p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
   253	    def tick(self, world_tick: int, agents: Sequence[AgentView]) -> None:
   254	        """Drive proximity-based admission + timeout close in one step.
   255	
   256	        Called by ``WorldRuntime._on_cognition_tick`` after per-agent
   257	        cognition has run. Order:
   258	
   259	        1. close any dialogs whose last_activity_tick is older than TIMEOUT
   260	        2. for each co-located pair in reflective zones, probabilistically
   261	           admit (if not already open and past cooldown)
   262	        """
   263	        self._close_timed_out(world_tick)
   264	        for a, b in _iter_colocated_pairs(agents):
   265	            if a.zone not in _REFLECTIVE_ZONES:
   266	                continue
   267	            key = _pair_key(a.agent_id, b.agent_id)
   268	            if key in self._pair_to_id:
   269	                continue
   270	            last_close = self._last_close_tick.get(key)
   271	            if last_close is not None and world_tick - last_close < self.COOLDOWN_TICKS:
   272	                continue
   273	            if self._rng.random() > self.AUTO_FIRE_PROB_PER_TICK:
   274	                continue
   275	            self.schedule_initiate(a.agent_id, b.agent_id, a.zone, world_tick)
   276	
   277	    def get_dialog_id(self, agent_a: str, agent_b: str) -> str | None:
   278	        """Return the open dialog id for the (a, b) pair if any, else None."""
   279	        return self._pair_to_id.get(_pair_key(agent_a, agent_b))
   280	
   281	    @property
   282	    def open_count(self) -> int:
   283	        return len(self._open)
   284	
   285	    def transcript_of(self, dialog_id: str) -> list[DialogTurnMsg]:
   286	        dialog = self._open.get(dialog_id)
   287	        return list(dialog.turns) if dialog is not None else []
   288	
   289	    def iter_open_dialogs(self) -> Iterator[tuple[str, str, str, Zone]]:
   290	        """Yield ``(dialog_id, initiator_id, target_id, zone)`` for each open dialog.
   291	
   292	        Added for ``m5-orchestrator-integration``: the per-tick turn driver in
   293	        :class:`~erre_sandbox.world.tick.WorldRuntime` needs to enumerate every
   294	        open dialog to decide budget / speaker / turn generation. Read-only
   295	        — callers must not mutate the scheduler's state via the yielded ids
   296	        except through the existing ``record_turn`` / ``close_dialog`` surface.
   297	        """
   298	        for did, dialog in self._open.items():
   299	            yield did, dialog.initiator, dialog.target, dialog.zone
   300	
   301	    # ------------------------------------------------------------------
   302	    # Internals
   303	    # ------------------------------------------------------------------
   304	
   305	    def _close_timed_out(self, world_tick: int) -> None:
   306	        expired: list[str] = [
   307	            did
   308	            for did, d in self._open.items()
   309	            if world_tick - d.last_activity_tick >= self.TIMEOUT_TICKS
   310	        ]
   311	        for did in expired:
   312	            self.close_dialog(did, reason="timeout", tick=world_tick)
   313	
   314	    def _emit(self, envelope: ControlEnvelope) -> None:
   315	        try:
   316	            self._sink(envelope)
   317	        except Exception:
   318	            # We refuse to let a sink failure desync scheduler state — log and
   319	            # continue. The sink is the gateway's responsibility; if it is
   320	            # broken that is a gateway-layer bug, not ours.
   321	            logger.exception(
   322	                "Dialog scheduler sink raised for envelope kind=%s",
   323	                envelope.kind,
   324	            )
   325	
   326	
   327	# ---------------------------------------------------------------------------
   328	# Module-private helpers
   329	# ---------------------------------------------------------------------------
   330	
   331	
   332	def _allocate_dialog_id() -> str:
   333	    return f"d_{uuid.uuid4().hex[:8]}"
   334	
   335	
   336	def _iter_colocated_pairs(
   337	    agents: Iterable[AgentView],
   338	) -> Iterator[tuple[AgentView, AgentView]]:
   339	    """Yield (a, b) pairs of distinct agents sharing the same zone.
   340	
   341	    Each unordered pair is yielded exactly once with a stable ``a.agent_id``
   342	    < ``b.agent_id`` ordering, so callers can use the first entry as the
   343	    canonical initiator without extra sorting.
   344	    """
   345	    sorted_agents = sorted(agents, key=lambda v: v.agent_id)
   346	    for i, a in enumerate(sorted_agents):
   347	        for b in sorted_agents[i + 1 :]:
   348	            if a.zone == b.zone:
   349	                yield a, b
   350	
   351	
   352	__all__ = [
   353	    # Re-exported from :mod:`erre_sandbox.schemas` for import ergonomics in
   354	    # callers that already reach into this module for the scheduler.
   355	    "AgentView",
   356	    "InMemoryDialogScheduler",
   357	]

 succeeded in 0ms:
   830	        speaker_persona_id: str,
   831	        addressee_persona_id: str,
   832	        epoch_phase: EpochPhase = EpochPhase.AUTONOMOUS,
   833	    ) -> str:
   834	        """Persist ``turn`` into the ``dialog_turns`` table synchronously.
   835	
   836	        Intended for the :class:`InMemoryDialogScheduler` sink which runs on
   837	        the event-loop thread after each :meth:`record_turn` call and must
   838	        not await. ``persona_id`` for speaker / addressee is resolved at the
   839	        call site from the bootstrap agent registry (see decisions D2).
   840	
   841	        ``epoch_phase`` (M7ε D4): tag the row with the run lifecycle phase
   842	        so ``scaling_metrics.aggregate()`` can drop ``Q_AND_A`` turns
   843	        from relational-saturation metrics. Defaults to ``AUTONOMOUS`` so
   844	        every existing call site (and every M7ε run before the m9-LoRA
   845	        Q&A driver lands) stamps autonomous without source-side changes.
   846	
   847	        Idempotent via ``INSERT OR IGNORE`` on the ``UNIQUE(dialog_id,
   848	        turn_index)`` constraint — re-emitting the same turn after a restart
   849	        is a no-op rather than a row duplication.
   850	
   851	        Returns the row id (new UUID when the row was inserted, or the
   852	        existing id when the INSERT was ignored).
   853	        """
   854	        row_id = f"dt_{turn.dialog_id}_{turn.turn_index:04d}"
   855	        with self._conn_lock:
   856	            conn = self._ensure_conn()
   857	            with conn:
   858	                conn.execute(
   859	                    "INSERT OR IGNORE INTO dialog_turns("
   860	                    "id, dialog_id, tick, turn_index, "
   861	                    "speaker_agent_id, speaker_persona_id, "
   862	                    "addressee_agent_id, addressee_persona_id, "
   863	                    "utterance, created_at, epoch_phase"
   864	                    ") VALUES (?,?,?,?,?,?,?,?,?,?,?)",
   865	                    (
   866	                        row_id,
   867	                        turn.dialog_id,
   868	                        turn.tick,
   869	                        turn.turn_index,
   870	                        turn.speaker_id,
   871	                        speaker_persona_id,
   872	                        turn.addressee_id,
   873	                        addressee_persona_id,
   874	                        turn.utterance,
   875	                        _dt_to_text(datetime.now(tz=UTC)),
   876	                        epoch_phase.value,
   877	                    ),
   878	                )
   879	        return row_id
   880	
   881	    async def add_dialog_turn(
   882	        self,
   883	        turn: DialogTurnMsg,
   884	        *,
   885	        speaker_persona_id: str,
   886	        addressee_persona_id: str,
   887	        epoch_phase: EpochPhase = EpochPhase.AUTONOMOUS,
   888	    ) -> str:
   889	        """Async wrapper over :meth:`add_dialog_turn_sync` via ``to_thread``.
   890	
   891	        Non-scheduler callers (CLI, tests, future async sinks) should prefer
   892	        this variant so the event loop is not blocked on sqlite I/O.
   893	        """
   894	        return await asyncio.to_thread(
   895	            self.add_dialog_turn_sync,
   896	            turn,
   897	            speaker_persona_id=speaker_persona_id,
   898	            addressee_persona_id=addressee_persona_id,
   899	            epoch_phase=epoch_phase,
   900	        )
   901	
   902	    def iter_dialog_turns(
   903	        self,
   904	        *,
   905	        persona: str | None = None,
   906	        exclude_persona: str | None = None,
   907	        since: datetime | None = None,
   908	        limit: int | None = None,
   909	        epoch_phase: EpochPhase | None = None,
   910	    ) -> Iterator[dict[str, object]]:
   911	        """Yield dialog turn rows as plain dicts.
   912	
   913	        Filters:
   914	
   915	        * ``persona`` — match ``speaker_persona_id = ?`` (export is
   916	          speaker-scoped for LoRA training-data semantics).
   917	        * ``exclude_persona`` — match ``speaker_persona_id != ?``. Added
   918	          for the M7δ ``_fetch_recent_peer_turns`` hot path so the SQLite
   919	          side can drop the speaker's own turns without a Python-side scan
   920	          (R3 H3 SQL push). Mutually compatible with ``persona``.
   921	        * ``since`` — match ``created_at >= since``.
   922	        * ``epoch_phase`` (M7ε D4): match ``epoch_phase = ?`` **or** NULL
   923	          when ``epoch_phase == EpochPhase.AUTONOMOUS``. Pre-migration rows
   924	          (NULL on read, m4/m6/m7γ/m7δ era) are treated as AUTONOMOUS for
   925	          backward compat — passing ``EpochPhase.AUTONOMOUS`` therefore
   926	          returns both NULL and ``"autonomous"`` rows. Other values match
   927	          exactly with no NULL fallback. ``None`` (default) skips the
   928	          filter entirely.
   929	
   930	        Ordering / size:
   931	
   932	        * Default (``limit is None``): rows are emitted **oldest first**
   933	          (``created_at ASC, turn_index ASC``). This preserves the export
   934	          CLI semantics that pre-date M7δ.
   935	        * ``limit`` set: the SQL flips to ``ORDER BY ... DESC LIMIT ?`` so
   936	          the **most recent N rows** are returned. Callers that want
   937	          chronological order should reverse the result. This shape lets
   938	          ``_fetch_recent_peer_turns`` push the recency cutoff into SQLite
   939	          (no full-table scan) while the export CLI keeps its old
   940	          unbounded ASC iteration when ``limit`` is omitted.
   941	
   942	        Returns plain dicts (not :class:`DialogTurnMsg`) so the export CLI
   943	        can emit rows that include the resolved ``speaker_persona_id`` /
   944	        ``addressee_persona_id`` / ``epoch_phase`` without having to
   945	        re-join at export time.
   946	        """
   947	        with self._conn_lock:
   948	            conn = self._ensure_conn()
   949	            clauses: list[str] = []
   950	            params: list[object] = []
   951	            if persona is not None:
   952	                clauses.append("speaker_persona_id = ?")
   953	                params.append(persona)
   954	            if exclude_persona is not None:
   955	                clauses.append("speaker_persona_id != ?")
   956	                params.append(exclude_persona)
   957	            if since is not None:
   958	                clauses.append("created_at >= ?")
   959	                params.append(_dt_to_text(since))
   960	            if epoch_phase is not None:
   961	                if epoch_phase is EpochPhase.AUTONOMOUS:
   962	                    # Pre-migration rows have NULL → backward-compat AUTONOMOUS.
   963	                    clauses.append("(epoch_phase = ? OR epoch_phase IS NULL)")
   964	                else:
   965	                    clauses.append("epoch_phase = ?")
   966	                params.append(epoch_phase.value)
   967	            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
   968	            order_dir = "DESC" if limit is not None else "ASC"
   969	            limit_sql = " LIMIT ?" if limit is not None else ""
   970	            if limit is not None:
   971	                params.append(int(limit))
   972	            sql = (
   973	                "SELECT id, dialog_id, tick, turn_index, "  # noqa: S608  # parameterized: bind vars; `where`/`order_dir`/`limit_sql` are internal-built literals
   974	                "speaker_agent_id, speaker_persona_id, "
   975	                "addressee_agent_id, addressee_persona_id, "
   976	                "utterance, created_at, epoch_phase "
   977	                f"FROM dialog_turns {where} "
   978	                f"ORDER BY created_at {order_dir}, turn_index {order_dir}"
   979	                f"{limit_sql}"
   980	            )
   981	            rows = conn.execute(sql, params).fetchall()
   982	        for row in rows:
   983	            yield dict(row)
   984	
   985	    # ------------------------------------------------------------------
   986	    # Bias fired events (M8 baseline-quality-metric)
   987	    # ------------------------------------------------------------------
   988	
   989	    def add_bias_event_sync(
   990	        self,

exec
/bin/zsh -lc "nl -ba src/erre_sandbox/bootstrap.py | sed -n '480,570p'" in /Users/johnd/ERRE-Sand Box
exec
/bin/zsh -lc "nl -ba src/erre_sandbox/cli/export_log.py | sed -n '1,180p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
   480	        # persona-resolver closure that needs the runtime; the runtime
   481	        # construction below takes the cycle. Build the reflector first
   482	        # with a forward-declaration trampoline so the resolver captures
   483	        # ``runtime`` after assignment.
   484	        reflector = Reflector(
   485	            store=memory,
   486	            embedding=embedding,
   487	            llm=inference,
   488	            persona_resolver=_resolve_persona_display_name,
   489	        )
   490	        cycle = CognitionCycle(
   491	            retriever=retriever,
   492	            store=memory,
   493	            embedding=embedding,
   494	            llm=inference,
   495	            erre_policy=DefaultERREModePolicy(),
   496	            bias_sink=_persist_bias_event,
   497	            reflector=reflector,
   498	        )
   499	        runtime = WorldRuntime(cycle=cycle)
   500	
   501	        # M8 L6-D1: per-turn sink persists every recorded dialog turn into
   502	        # sqlite ``dialog_turns`` for later LoRA-training export. The closure
   503	        # resolves ``agent_id → persona_id`` via ``runtime.agent_persona_id``
   504	        # so the wire schema stays untouched (decisions D2). Sink failures
   505	        # are caught inside ``InMemoryDialogScheduler.record_turn`` so a
   506	        # transient sqlite glitch cannot tear down the live loop.
   507	        def _persist_dialog_turn(turn: DialogTurnMsg) -> None:
   508	            speaker_pid = runtime.agent_persona_id(turn.speaker_id)
   509	            addressee_pid = runtime.agent_persona_id(turn.addressee_id)
   510	            if speaker_pid is None or addressee_pid is None:
   511	                logger.warning(
   512	                    "[bootstrap] dialog_turn sink skipped: unresolved persona for "
   513	                    "dialog_id=%s speaker=%s(%s) addressee=%s(%s)",
   514	                    turn.dialog_id,
   515	                    turn.speaker_id,
   516	                    speaker_pid,
   517	                    turn.addressee_id,
   518	                    addressee_pid,
   519	                )
   520	                return
   521	            # M7ε: stamp the live run-lifecycle epoch onto every persisted
   522	            # turn so ``scaling_metrics.aggregate()`` can drop ``Q_AND_A``
   523	            # turns from relational-saturation metrics (M8 D5 / ADR D3).
   524	            # Reading ``runtime.run_lifecycle`` at sink time makes the
   525	            # value automatically follow ``transition_to_q_and_a()`` when
   526	            # the m9-LoRA Q&A driver lands.
   527	            memory.add_dialog_turn_sync(
   528	                turn,
   529	                speaker_persona_id=speaker_pid,
   530	                addressee_persona_id=addressee_pid,
   531	                epoch_phase=runtime.run_lifecycle.epoch_phase,
   532	            )
   533	
   534	        # M7γ Commit 2: relational hook chain. After the M8 dialog-turn
   535	        # persistence, append a per-turn relational-memory INSERT and a
   536	        # bidirectional :class:`RelationshipBond` affinity update.
   537	        persona_registry = _load_persona_registry(cfg)
   538	        _persist_relational_event = _make_relational_sink(
   539	            runtime=runtime,
   540	            memory=memory,
   541	            persona_registry=persona_registry,
   542	        )
   543	
   544	        def _chained_turn_sink(turn: DialogTurnMsg) -> None:
   545	            """Run M8 dialog-turn persistence first, then γ relational hook."""
   546	            _persist_dialog_turn(turn)
   547	            _persist_relational_event(turn)
   548	
   549	        # The scheduler's envelope sink writes directly into the runtime's
   550	        # fan-out queue so dialog envelopes interleave with agent_update /
   551	        # speech / move without a second delivery path (see design.md §v2).
   552	        scheduler = InMemoryDialogScheduler(
   553	            envelope_sink=runtime.inject_envelope,
   554	            turn_sink=_chained_turn_sink,
   555	        )
   556	        runtime.attach_dialog_scheduler(scheduler)
   557	
   558	        # Dialog turn generator wiring: built from the pre-loaded persona
   559	        # registry so the generator can resolve the addressee's display_name
   560	        # at prompt-build time.
   561	        dialog_generator = OllamaDialogTurnGenerator(
   562	            llm=inference,
   563	            personas=persona_registry,
   564	        )
   565	        runtime.attach_dialog_generator(dialog_generator)
   566	        logger.info(
   567	            "[bootstrap] dialog_turn wired (%d personas in registry)",
   568	            len(persona_registry),
   569	        )
   570	

 succeeded in 0ms:
     1	"""``erre-sandbox export-log`` — dump ``dialog_turns`` to JSONL.
     2	
     3	Reads the sqlite ``dialog_turns`` table populated by the M8 L6-D1 sink
     4	(see ``.steering/20260425-m8-episodic-log-pipeline/``) and streams matching
     5	rows as newline-delimited JSON. Consumed by the M9 LoRA training pipeline
     6	and the forthcoming ``m8-baseline-quality-metric`` spike.
     7	
     8	Scope choices baked in (decisions D4):
     9	
    10	* JSONL is the only supported format. ``--format`` is still exposed so the
    11	  flag surface is stable when Parquet is added in a later milestone, but any
    12	  value other than ``jsonl`` is rejected at parse time.
    13	* Filters are AND-composed (``--persona`` and ``--since``); adding OR /
    14	  expression trees is deferred until a real use case demands it.
    15	"""
    16	
    17	from __future__ import annotations
    18	
    19	import argparse
    20	import json
    21	import sys
    22	from datetime import datetime
    23	from pathlib import Path
    24	
    25	from erre_sandbox.memory import MemoryStore
    26	
    27	SUPPORTED_FORMATS: tuple[str, ...] = ("jsonl",)
    28	"""Formats accepted by ``--format``. Parquet joins this set in the M9 LoRA task."""
    29	
    30	
    31	def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    32	    """Attach the ``export-log`` sub-command to the root argparse tree."""
    33	    parser = subparsers.add_parser(
    34	        "export-log",
    35	        help="Export dialog_turns log to JSONL (M8 L6-D1 precondition).",
    36	        description=(
    37	            "Stream the contents of the sqlite ``dialog_turns`` table as "
    38	            "newline-delimited JSON. Intended for M9 LoRA training-data "
    39	            "preparation and for baseline turn-count reporting."
    40	        ),
    41	    )
    42	    parser.add_argument(
    43	        "--db",
    44	        dest="db_path",
    45	        default="var/kant.db",
    46	        help="Path to the sqlite database (default: var/kant.db).",
    47	    )
    48	    parser.add_argument(
    49	        "--format",
    50	        default="jsonl",
    51	        choices=SUPPORTED_FORMATS,
    52	        help=(
    53	            "Output format. Only ``jsonl`` is supported in M8 — Parquet is "
    54	            "deferred to the M9 LoRA task (decisions D4)."
    55	        ),
    56	    )
    57	    parser.add_argument(
    58	        "--persona",
    59	        default=None,
    60	        help=(
    61	            "Filter by ``speaker_persona_id`` (e.g. ``kant``). "
    62	            "Omit to export every persona."
    63	        ),
    64	    )
    65	    parser.add_argument(
    66	        "--since",
    67	        default=None,
    68	        help=(
    69	            "Only include rows whose ``created_at`` is at or after this "
    70	            "ISO-8601 timestamp (e.g. ``2026-04-24T00:00:00+00:00``)."
    71	        ),
    72	    )
    73	    parser.add_argument(
    74	        "--out",
    75	        dest="out_path",
    76	        default="-",
    77	        help="Output path; use ``-`` for stdout (default).",
    78	    )
    79	
    80	
    81	def _parse_since(raw: str | None) -> datetime | None:
    82	    if raw is None:
    83	        return None
    84	    try:
    85	        return datetime.fromisoformat(raw)
    86	    except ValueError as exc:
    87	        msg = f"--since expected ISO-8601 (e.g. 2026-04-24T00:00:00+00:00), got {raw!r}"
    88	        raise SystemExit(msg) from exc
    89	
    90	
    91	def _open_output(out_path: str):  # type: ignore[no-untyped-def]
    92	    """Return (writer, close_fn) for ``out_path``; ``-`` means stdout."""
    93	    if out_path == "-":
    94	        return sys.stdout, lambda: None
    95	    handle = Path(out_path).open("w", encoding="utf-8")  # noqa: SIM115
    96	    return handle, handle.close
    97	
    98	
    99	def run(args: argparse.Namespace) -> int:
   100	    """Execute the ``export-log`` sub-command.
   101	
   102	    Returns the POSIX exit code (0 on success, non-zero on failure).
   103	    """
   104	    if args.format not in SUPPORTED_FORMATS:  # defence in depth vs. choices=
   105	        print(
   106	            f"--format {args.format!r} is not supported (choose one of "
   107	            f"{SUPPORTED_FORMATS}).",
   108	            file=sys.stderr,
   109	        )
   110	        return 2
   111	
   112	    since = _parse_since(args.since)
   113	    store = MemoryStore(db_path=args.db_path)
   114	    # Caller may hand us a fresh DB that has not had ``create_schema`` run
   115	    # yet — idempotent, so the cost of calling it here is zero when it has.
   116	    store.create_schema()
   117	
   118	    writer, close_fn = _open_output(args.out_path)
   119	    try:
   120	        row_count = 0
   121	        for row in store.iter_dialog_turns(persona=args.persona, since=since):
   122	            writer.write(json.dumps(row, ensure_ascii=False))
   123	            writer.write("\n")
   124	            row_count += 1
   125	        if hasattr(writer, "flush"):
   126	            writer.flush()
   127	    finally:
   128	        close_fn()
   129	
   130	    # Report to stderr when writing to a file so a chained caller sees the
   131	    # count without contaminating the JSONL stream on stdout.
   132	    if args.out_path != "-":
   133	        print(
   134	            f"export-log: wrote {row_count} row(s) to {args.out_path}",
   135	            file=sys.stderr,
   136	        )
   137	    return 0

web search: 
web search: DuckDB concurrency single writer multiple readers file locking read_only official documentation
web search: 
web search: Kunsch 1989 block bootstrap time series Annals of Statistics block length stationary bootstrap Politis Romano 1994
web search: 
web search: LLM personality IPIP NEO self report acquiescence social desirability bias instruction following artifacts study
web search: 
web search: intraclass correlation coefficient ICC interpretation 0.6 0.75 reliability Koo Li 2016 guidelines
web search: 
web search: Burrows Delta stylometry minimum text length number of words function words z scores corpus size stable
web search: 
web search: Eder stylometry Delta text length 5000 words authorship attribution stylometry R stylo
web search: 
web search: systemd timer Persistent OnCalendar official documentation missed runs boot
web search: 
web search: https://www.freedesktop.org/software/systemd/man/255/systemd.service.html
web search: 
web search: site:freedesktop.org/software/systemd/man systemd.timer Persistent OnCalendar latest
web search: 
web search: Vendi Score sample diversity effective number samples kernel eigenvalues TMLR 2023 formula
codex
One repo-specific issue surfaced outside the statistical questions: the planned stimulus path talks about a scheduler input queue, but the current scheduler has no such queue surface. I’m checking the project architecture rules before classifying that, since the recommendation should not invent a new layer that conflicts with ERRE’s dependency direction.
exec
/bin/zsh -lc "sed -n '1,220p' .agents/skills/architecture-rules/SKILL.md" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
---
name: architecture-rules
description: >
  レイヤー依存方向・インポート制約・GPL/クラウド API 禁止ルール。
  src/erre_sandbox/ 配下に新しいファイルを追加する・インポートを変更する・
  新しい依存ライブラリを追加する時に必須参照。
  schemas.py / inference/ / memory/ / cognition/ / world/ / ui/ / erre/
  のどのモジュールにコードを置くか判断する時、
  import 文が依存方向に違反していないか確認する時、
  pip install / uv add でライブラリを追加する時に自動召喚される。
  GPL ライブラリ (bpy 等) を src/erre_sandbox/ に import する禁止も含む。
---

# Architecture Rules

## このスキルの目的

ERRE-Sandbox のアーキテクチャは 2 拠点 (G-GEAR + MacBook) × 5 レイヤー構成。
インポートの依存方向を守ることで、将来のバックエンド差し替え (Qdrant、gRPC 等) を
最小の変更で実現できるようにする。また、GPL ライブラリとクラウド API の混入を防ぐ。

## レイヤー依存方向（絶対厳守）

```
world/ → cognition/ → inference/
                    → memory/
                          ↓
ui/ ──────────→ schemas.py ← (全モジュールが参照)
```

| モジュール | 依存先 | 依存禁止 |
|---|---|---|
| `schemas.py` | なし (最下層) | すべての src モジュール |
| `inference/` | `schemas.py` のみ | `memory/`, `cognition/`, `world/`, `ui/` |
| `memory/` | `schemas.py` のみ | `inference/`, `cognition/`, `world/`, `ui/` |
| `cognition/` | `inference/`, `memory/`, `schemas.py`, `erre/` | `world/`, `ui/` |
| `world/` | `cognition/`, `schemas.py` | `ui/`, `erre/` |
| `ui/` | `schemas.py` のみ | `inference/`, `memory/`, `cognition/`, `world/` |
| `erre/` | `schemas.py`, `inference/`, `memory/` | `cognition/`, `world/`, `ui/` |

### 依存方向の確認方法

```bash
# ui/ が inference/ を import していないか確認
grep -r "from erre_sandbox.inference" src/erre_sandbox/ui/
grep -r "from erre_sandbox.memory"    src/erre_sandbox/ui/

# schemas.py が他モジュールを import していないか確認
grep "from erre_sandbox\." src/erre_sandbox/schemas.py
```

## 絶対禁止ルール

### 禁止 1: GPL ライブラリを src/erre_sandbox/ に import

Blender の `bpy` は GPL-2+ のため、import するコードが GPL 派生物になる。
Apache-2.0 OR MIT デュアルライセンスと矛盾するため **絶対に混入させない**。

```python
# ❌ 絶対禁止
import bpy                          # GPL viral — Apache/MIT と矛盾
from bpy.types import Object        # 同上
```

将来 Blender 連携が必要になった場合 → `erre-sandbox-blender/` を別パッケージ (GPL-3) で分離。

### 禁止 2: クラウド LLM API を必須依存にする

OpenAI / Anthropic / Google の API は予算ゼロ制約に反する。

```python
# ❌ 禁止
import openai                       # 有料 API
from anthropic import Anthropic     # 有料 API
```

ローカル推論 (SGLang / Ollama / llama.cpp) のみ使用。

### 禁止 3: ui/ から inference/ / memory/ を直接 import

UI は WebSocket 経由で G-GEAR と通信する。Python の import で直接呼ばない。

```python
# ❌ 禁止 — ui/ から memory/ を直接呼ぶ
from erre_sandbox.memory.store import MemoryStore  # ui/ 内に書いてはいけない

# ✅ 正しい — WebSocket 経由
from erre_sandbox.schemas import ControlEnvelope   # スキーマのみ OK
```

### 禁止 4: schemas.py から他の src モジュールを import

`schemas.py` は最下層。循環参照を防ぐために依存なしを厳守。

```python
# ❌ 禁止
from erre_sandbox.memory.store import MemoryStore  # schemas.py 内に書いてはいけない

# ✅ 正しい — 型ヒントのみなら TYPE_CHECKING で遅延
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from erre_sandbox.memory.store import MemoryStore
```

## 新しいファイルの配置判断フロー

```
新しい .py ファイルを作る
    │
    ├─ LLM 推論関連?           → inference/
    ├─ 記憶・検索・埋め込み?   → memory/
    ├─ 認知サイクル・反省?     → cognition/
    ├─ ワールド・物理・ゾーン? → world/
    ├─ WebSocket クライアント・Godot 連携? → ui/
    ├─ ERRE パイプライン DSL?  → erre/
    └─ Pydantic スキーマ定義?  → schemas.py に追記 (ファイルは作らない)
```

## 依存ライブラリ追加の基準

新しいライブラリを `uv add` する前に全項目確認:

- [ ] 既存の依存で代替できないか?
- [ ] ライセンスは Apache-2.0 / MIT / BSD と互換か? (**GPL は本体に入れない**)
- [ ] メンテナンスが活発か? (直近 6 ヶ月以内にリリースがあるか)
- [ ] セキュリティ脆弱性はないか?
- [ ] 予算ゼロに抵触しないか? (有料 SaaS の必須依存は不可)

## チェックリスト

- [ ] 新しいファイルが正しいレイヤー (`inference/`, `memory/` 等) に置かれているか
- [ ] インポートが依存方向に違反していないか (`grep` で確認)
- [ ] `schemas.py` から他の src モジュールを import していないか
- [ ] `ui/` から `inference/` や `memory/` を直接 import していないか
- [ ] GPL ライブラリが `src/erre_sandbox/` に入っていないか
- [ ] クラウド LLM API が必須依存になっていないか
- [ ] 新しい依存のライセンスが Apache-2.0/MIT/BSD と互換か

## 補足資料

- `decision-tree.md` — 「どのモジュールに書くべきか」の判断フロー詳細版

## 関連する他の Skill

- `python-standards` — インポート順序・相対 vs 絶対インポートのルール
- `implementation-workflow` — Step B (既存パターン調査) でこの Skill を参照
- `llm-inference` — inference/ 内のモデル設定と VRAM 管理
- `persona-erre` — ペルソナ YAML 設計と ERRE モード定義
- `godot-gdscript` — Godot シーン・GDScript のコーディング規約と WebSocket 通信
- `blender-pipeline` — Blender アセットパイプラインの GPL 分離の具体的手順

exec
/bin/zsh -lc "nl -ba pyproject.toml | sed -n '1,180p'" in /Users/johnd/ERRE-Sand Box
 succeeded in 0ms:
     1	[build-system]
     2	requires = ["uv_build>=0.4,<2.0"]
     3	build-backend = "uv_build"
     4	
     5	[project]
     6	name = "erre-sandbox"
     7	version = "0.0.1"
     8	description = "Autonomous 3D Society Emerging from the Cognitive Habits of Great Thinkers"
     9	readme = "README.md"
    10	requires-python = ">=3.11,<3.12"
    11	license = "Apache-2.0 OR MIT"
    12	license-files = ["LICENSE", "LICENSE-MIT", "NOTICE"]
    13	authors = [
    14	    { name = "mikotomiura", email = "mmiura.network@gmail.com" },
    15	]
    16	keywords = ["llm", "agent", "cognitive-architecture", "godot", "research"]
    17	classifiers = [
    18	    "Development Status :: 2 - Pre-Alpha",
    19	    "Intended Audience :: Developers",
    20	    "Intended Audience :: Science/Research",
    21	    "Operating System :: POSIX :: Linux",
    22	    "Operating System :: MacOS :: MacOS X",
    23	    "Programming Language :: Python :: 3 :: Only",
    24	    "Programming Language :: Python :: 3.11",
    25	    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    26	]
    27	dependencies = [
    28	    "pydantic>=2.7,<3",
    29	    "fastapi>=0.115,<1",
    30	    "uvicorn[standard]>=0.30,<1",
    31	    "websockets>=13,<15",
    32	    "httpx>=0.27,<1",
    33	    "sqlite-vec>=0.1,<1",
    34	    "pyyaml>=6,<7",
    35	    "numpy>=2,<3",
    36	]
    37	
    38	[project.optional-dependencies]
    39	ui = [
    40	    "streamlit>=1.39,<2",
    41	]
    42	
    43	[project.scripts]
    44	erre-sandbox = "erre_sandbox.__main__:cli"
    45	
    46	[project.urls]
    47	Homepage = "https://github.com/mikotomiura/erre-sandbox"
    48	Repository = "https://github.com/mikotomiura/erre-sandbox"
    49	Issues = "https://github.com/mikotomiura/erre-sandbox/issues"
    50	
    51	[dependency-groups]
    52	lint = [
    53	    "ruff>=0.6,<1.0",
    54	]
    55	typecheck = [
    56	    "mypy>=1.11,<2",
    57	    "types-pyyaml>=6,<7",
    58	]
    59	test = [
    60	    "pytest>=8,<9",
    61	    "pytest-asyncio>=0.24,<1",
    62	]
    63	dev = [
    64	    { include-group = "lint" },
    65	    { include-group = "typecheck" },
    66	    { include-group = "test" },
    67	]
    68	
    69	[tool.uv.build-backend]
    70	module-name = "erre_sandbox"
    71	module-root = "src"
    72	
    73	# =============================================================================
    74	# ruff
    75	# =============================================================================
    76	[tool.ruff]
    77	line-length = 88
    78	target-version = "py311"
    79	src = ["src", "tests"]
    80	extend-exclude = [".venv", "docs/_pdf_derived", "godot_project", ".steering", "erre-sandbox-blender"]
    81	
    82	[tool.ruff.lint]
    83	select = ["ALL"]
    84	ignore = [
    85	    # docstring: 公開 API のみ require。全関数には要求しない
    86	    "D100", "D101", "D102", "D103", "D104", "D105", "D106", "D107",
    87	    "D203", "D213",
    88	    # mypy と責務重複するアノテーション系
    89	    "ANN001", "ANN002", "ANN003", "ANN201", "ANN202", "ANN204", "ANN205", "ANN206", "ANN401",
    90	    # ruff format と衝突
    91	    "COM812", "ISC001",
    92	    # 日本語全角文字を許容する
    93	    "RUF001", "RUF002", "RUF003",
    94	    # pytest で assert を使うため
    95	    "S101",
    96	    # 例外文字列の形式規定はプロジェクト文化に合わない
    97	    "EM101", "EM102", "TRY003", "TRY300", "TRY301",
    98	    # Pydantic BaseModel 初期化は多引数が自然
    99	    "PLR0913",
   100	    # src レイアウトで誤検知しやすい
   101	    "INP001",
   102	    # コミット済み TODO / FIXME は許容
   103	    "TD002", "TD003", "FIX002",
   104	    # 日本語 docstring / コメント混在の環境で noisy
   105	    "DOC201", "DOC202", "DOC501",
   106	    # copyright header を全ファイルに強制しない
   107	    "CPY001",
   108	]
   109	
   110	[tool.ruff.lint.per-file-ignores]
   111	# S101 は global ignore 済みだが、将来 global から外して tests のみ許容に
   112	# 切り替える時のセーフティネットとして残している。
   113	"tests/**" = ["S101", "PLR2004", "D", "ANN", "SLF001", "S311", "TC003", "ERA001", "PLC0415"]
   114	"**/__init__.py" = ["F401", "D104"]
   115	# CLI subcommands intentionally print to stdout/stderr and use argparse
   116	# Namespace at runtime rather than as a TYPE_CHECKING-only import.
   117	"src/erre_sandbox/cli/**" = ["T201", "TC003"]
   118	
   119	[tool.ruff.lint.pydocstyle]
   120	convention = "google"
   121	
   122	[tool.ruff.lint.isort]
   123	known-first-party = ["erre_sandbox"]
   124	
   125	[tool.ruff.format]
   126	quote-style = "double"
   127	indent-style = "space"
   128	docstring-code-format = true
   129	
   130	# =============================================================================
   131	# mypy — src は strict、tests は寛容
   132	# =============================================================================
   133	[tool.mypy]
   134	python_version = "3.11"
   135	strict = true
   136	warn_unused_ignores = true
   137	warn_return_any = false  # T05 完了後に true に昇格 (decisions.md 参照)
   138	plugins = ["pydantic.mypy"]
   139	exclude = ["^\\.venv/", "^build/", "^dist/"]
   140	
   141	[[tool.mypy.overrides]]
   142	module = "tests.*"
   143	disallow_untyped_defs = false
   144	disallow_incomplete_defs = false
   145	check_untyped_defs = true
   146	
   147	[[tool.mypy.overrides]]
   148	module = ["sqlite_vec.*", "streamlit.*"]
   149	ignore_missing_imports = true
   150	
   151	[tool.pydantic-mypy]
   152	init_forbid_extra = true
   153	init_typed = true
   154	warn_required_dynamic_aliases = true
   155	
   156	# =============================================================================
   157	# pytest
   158	# =============================================================================
   159	[tool.pytest.ini_options]
   160	minversion = "8.0"
   161	asyncio_mode = "auto"
   162	testpaths = ["tests"]
   163	addopts = [
   164	    "-ra",
   165	    "--strict-markers",
   166	    "--strict-config",
   167	]
   168	filterwarnings = [
   169	    "error",
   170	    "ignore::DeprecationWarning:websockets.*",
   171	    # T10 着手時に uvicorn.* / httpx.* / anyio.* の DeprecationWarning ignore を
   172	    # 必要に応じて追加する。過剰に厳しい場合は error を default に戻す判断もあり。
   173	    # pytest-asyncio 0.26.x は function-scope の event loop teardown 後に
   174	    # ループを close せず、GC タイミング次第で「次の test の setup」で
   175	    # ResourceWarning が発火する (上流 issue として報告済)。CI 緑化のため
   176	    # PytestUnraisableExceptionWarning だけ default 扱い (表示はするが fail
   177	    # しない) に下げる。pytest-asyncio >= 0.27 に上がったら本行は撤去。
   178	    "default::pytest.PytestUnraisableExceptionWarning",
   179	]
   180	markers = [

web search: 
web search: 
web search: 
web search: https://duckdb.org/docs/current/connect/concurrency.html
web search: 
web search: 'Read-only mode' in https://duckdb.org/docs/current/connect/concurrency.html
web search: 
web search: https://www.freedesktop.org/software/systemd/man/devel/systemd.timer.html
web search: 
web search: https://pmc.ncbi.nlm.nih.gov/articles/PMC4913118/
web search: 
web search: https://easystats.github.io/effectsize/reference/interpret_icc.html
web search: 
web search: https://arxiv.org/abs/2307.00184
web search: 
web search: Python hash randomization hash values salted unpredictable between processes documentation PYTHONHASHSEED
web search: 
web search: https://docs.python.org/3/reference/datamodel.html
web search: 
web search: 'salted with an unpredictable random value' in https://docs.python.org/3/reference/datamodel.html
codex
# Codex review — m9-eval-system design.md

**Date**: 2026-04-30  
**Reviewer**: Codex gpt-5.5 xhigh  
**Review target**: `.steering/20260430-m9-eval-system/design.md` and listed companions

## Summary
Proceed with HIGH fixes before P0a. The design is directionally implementable, but several contracts are still prose-level: contamination prevention, baseline ratio selection, bootstrap validity, and stimulus injection. Lowest-cost wins: move P3b before P3, replace `hash()` seeds, and make training/eval dependency boundaries executable.

## Findings

### HIGH-1: Schema guard is not yet an executable contamination boundary
- **Finding**: The design says `connect_training_view()` is the only training entry, but the current training export path already reads sqlite directly and is documented as consumed by M9 LoRA. Grep for `metrics.` misses quoted SQL, dynamic SQL, direct DuckDB connections, `read_parquet("...metrics...")`, and future Rust/Go tooling.
- **Evidence**: [design.md:47](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:47>), [design.md:53](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:53>), [export_log.py:5](</Users/johnd/ERRE-Sand Box/src/erre_sandbox/cli/export_log.py:5>), [export_log.py:121](</Users/johnd/ERRE-Sand Box/src/erre_sandbox/cli/export_log.py:121>).
- **Recommendation**: Add a behavioral CI test over every training egress command/API with sentinel `metrics` rows and assert no metric fields/values leave the process. `connect_training_view()` should return raw rows or a constrained relation, not an unrestricted DuckDB connection. If arbitrary SQL is needed, export a raw-only snapshot for training.
- **Severity rationale**: HIGH because contamination prevention is DB5’s core contract; implementing the wrong guard now creates later baseline/training rework.

### HIGH-2: Bootstrap CI must account for run and turn dependence
- **Finding**: `bootstrap_ci.py` is specified as NumPy resampling, but dialog turns are autoregressive and Tier B units are per-100-turn/window, not iid rows.
- **Evidence**: [design.md:208](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:208>), [design.md:354](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:354>), [decisions.md:198](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-b-lora-execution-plan/decisions.md:198>). SciPy’s bootstrap resamples observations as random samples ([docs](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)); time-series bootstrap methods preserve dependence with blocks ([arch docs](https://arch.readthedocs.io/en/stable/bootstrap/timeseries-bootstraps.html)).
- **Recommendation**: Specify hierarchical bootstrap: resample runs as clusters, then circular/stationary blocks within each 500-turn run. Choose block length via pilot/autocorrelation or sensitivity grid, and report Tier B CI as based on only 25 windows/persona unless widened.
- **Severity rationale**: HIGH because DB9 drift/adoption decisions become overconfident under iid resampling.

### HIGH-3: P3b pilot is ordered after the data it is supposed to tune
- **Finding**: The table runs P3 golden capture before P3b ratio tuning, so any ratio change forces a 7500-turn rerun. Also, 50 turns cannot evaluate Vendi if the expected window is 200 turns.
- **Evidence**: [design.md:19](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:19>), [design.md:20](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:20>), [design.md:118](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:118>), [research-evaluation-metrics.md:301](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:301>). Vendi is kernel/eigenvalue based over the sample ([OpenReview](https://openreview.net/forum?id=g97OHbQyk1)).
- **Recommendation**: Move P3b before P3 or freeze 200/300 and delete tuning. Minimum defensible pilot: at least 200 turns per condition per persona, fresh scheduler/store, isolated seeds, no carry-over into golden baseline.
- **Severity rationale**: HIGH because the current order can invalidate the golden baseline.

### HIGH-4: Stimulus injection target does not exist in the scheduler
- **Finding**: The design says `golden_baseline.py` pushes stimuli to the scheduler input queue, but `InMemoryDialogScheduler` has no input queue surface.
- **Evidence**: [design.md:124](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:124>), [design.md:130](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:130>), [dialog.py:103](</Users/johnd/ERRE-Sand Box/src/erre_sandbox/integration/dialog.py:103>), [dialog.py:253](</Users/johnd/ERRE-Sand Box/src/erre_sandbox/integration/dialog.py:253>).
- **Recommendation**: Define the actual additive surface before P0: either an external golden driver using public `schedule_initiate`/`record_turn`/`close_dialog`, or an explicit forced-dialog/stimulus hook with tests for the 70-stimulus battery.
- **Severity rationale**: HIGH because P2/P3 implementation will otherwise discover a missing API late.

### HIGH-5: Burrows Delta is specified as the wrong metric
- **Finding**: `burrows.py` is described as “function-word vector cosine,” but the research doc defines Burrows Delta as distance over z-scored function-word frequencies.
- **Evidence**: [design.md:193](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:193>), [research-evaluation-metrics.md:208](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:208>). Stylometry references Delta/z-score frequency workflows and 5k-word windows ([R Journal stylo](https://journal.r-project.org/articles/RJ-2016-007/)).
- **Recommendation**: Implement actual Burrows Delta, or rename the quorum submetric to Cosine Delta and update DB9 wording, thresholds, and tests.
- **Severity rationale**: HIGH because the primary persona-fit submetric would otherwise be mislabeled and non-comparable.

### MEDIUM-1: IPIP fallback trigger is not operational
- **Finding**: “ICC < 0.6 が頻発” has no denominator. LLM survey responses are known to show social desirability artifacts.
- **Evidence**: [design.md:91](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:91>), [design.md:419](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:419>); Salecha et al. report LLM social desirability bias in Big Five surveys ([arXiv](https://arxiv.org/abs/2405.06058)); Koo/Li-style ICC interpretation treats 0.5-0.75 as moderate ([effectsize docs](https://easystats.github.io/effectsize/reference/interpret_icc.html)).
- **Recommendation**: Define “frequent” as e.g. ≥2/3 personas with ICC point <0.6 or lower CI <0.5 after golden baseline. Add acquiescence/straight-line checks, balanced/reverse items, and a base-model/persona-prompt control.
- **Severity rationale**: MEDIUM because Option D is defensible, but the reopen trigger must be auditable.

### MEDIUM-2: DuckDB snapshot semantics are underspecified
- **Finding**: “G-GEAR writes, Mac rsyncs read-only” is safe only if Mac reads a closed or checkpointed copy, not the live file.
- **Evidence**: [design.md:31](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:31>). DuckDB permits multiple read-only processes but not multi-process writes and warns about file locks/shared directories ([DuckDB docs](https://duckdb.org/docs/current/connect/concurrency)).
- **Recommendation**: Require `CHECKPOINT`/close before rsync, copy to temp then rename, open Mac copy with `read_only=True`, and never analyze the live G-GEAR file over a shared filesystem.
- **Severity rationale**: MEDIUM because the design choice is fine, but the snapshot protocol needs a decision record.

### MEDIUM-3: Tier C lock/preflight has TOCTOU gaps
- **Finding**: `nvidia-smi` free-memory preflight can pass, then another process can load before Prometheus does unless the same lock is held through preflight, model load, and evaluation.
- **Evidence**: [design.md:157](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:157>), [design.md:433](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:433>). `flock -n` fails immediately if unavailable ([man page](https://man7.org/linux/man-pages/man1/flock.1.html)); `Persistent=` defaults false for timers ([systemd.timer](https://www.freedesktop.org/software/systemd/man/devel/systemd.timer.html)).
- **Recommendation**: Wrap the entire Tier C command in the flock; autonomous loop must use the same lock. Decide `Persistent=false` vs catch-up explicitly, and log skip with a distinct success exit code.
- **Severity rationale**: MEDIUM because Tier C is not the primary DB9 gate, but race semantics should be recorded.

### MEDIUM-4: Dependency placement contradicts the adopted library axis
- **Finding**: The summary says sentence-transformers is optional eval extra, but `design.md` puts it in core dependencies, which will pull heavy ML deps into normal sync/CI.
- **Evidence**: [design.md:302](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:302>), [design.md:309](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:309>), [ci.yml:31](</Users/johnd/ERRE-Sand Box/.github/workflows/ci.yml:31>).
- **Recommendation**: Keep core to `duckdb` if required; move `sentence-transformers`, `scipy`, `ollama`, `empath` under `eval`. Add eval-specific CI or marks so normal CI remains lightweight.
- **Severity rationale**: MEDIUM because it is reversible, but easy to get wrong during P0.

### MEDIUM-5: Seed generation uses nondeterministic Python `hash()`
- **Finding**: `seed = hash((persona_id, run_idx, ...))` is not stable across Python invocations.
- **Evidence**: [design.md:139](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:139>). Python documents salted hash values as unpredictable between runs ([Python docs](https://docs.python.org/3/reference/datamodel.html#object.__hash__)).
- **Recommendation**: Use `hashlib.blake2b`/SHA-256 to derive uint64 seeds, commit `golden/seeds.json`, and test exact seed manifest on Mac and G-GEAR.
- **Severity rationale**: MEDIUM because it directly affects reproducibility but is cheap to fix.

### MEDIUM-6: 50K Burrows token floor needs corpus-QC semantics
- **Finding**: “<50K noisy” is a placeholder, not a measured rule, and reference corpus provenance/licensing is not specified.
- **Evidence**: [design.md:422](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:422>), [blockers.md:33](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-b-lora-execution-plan/blockers.md:33>), [development-guidelines.md:176](</Users/johnd/ERRE-Sand Box/docs/development-guidelines.md:176>). Stylometry sample-length needs vary; <5k is often poor but 20k can still fail for some texts ([Computational Stylistics](https://computationalstylistics.github.io/projects/methodology/)).
- **Recommendation**: Replace the fixed floor with QC: per-language tokenization, public-domain/provenance metadata, ≥5k-word chunk stability tests, and a reopen condition based on Delta rank instability.
- **Severity rationale**: MEDIUM because it affects interpretability, but not P0 implementation shape.

### LOW-1: RoleEval wording may accidentally become Kant-only
- **Finding**: The battery names “Kant biographical MCQ” while stimulus files are per persona.
- **Evidence**: [design.md:103](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:103>), [design.md:223](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:223>).
- **Recommendation**: Clarify persona-specific MCQs for Nietzsche/Rikyu, or label Kant-only MCQ as a non-comparative floor diagnostic.
- **Severity rationale**: LOW because P2 review can catch it, but ambiguity is cheap to remove.

## Cross-cutting observations
The main weakness is not model choice; it is boundary specification. Convert prose contracts into tests for: training egress, baseline immutability, block-bootstrap unit selection, and scheduler stimulus execution.

## Verification suggestions
- Add a red-team contamination fixture with unique metric sentinel strings and run every training export against it.
- Simulate AR(1) turn metrics and compare iid vs block CI width in `test_bootstrap_ci.py`.
- Run a 200-turn isolated pilot before golden capture and record whether it changes 200/300.
- Add a scheduler dry-run test that executes one full 70-stimulus cycle without relying on nonexistent queues.
- Add a Mac/G-GEAR seed manifest test using stable hash output.
hook: Stop
hook: Stop Completed
2026-04-30T09:11:00.603772Z ERROR codex_core::session: failed to record rollout items: thread 019ddda1-a16a-7f01-8fbc-2bc4c080506c not found
tokens used
254,381
# Codex review — m9-eval-system design.md

**Date**: 2026-04-30  
**Reviewer**: Codex gpt-5.5 xhigh  
**Review target**: `.steering/20260430-m9-eval-system/design.md` and listed companions

## Summary
Proceed with HIGH fixes before P0a. The design is directionally implementable, but several contracts are still prose-level: contamination prevention, baseline ratio selection, bootstrap validity, and stimulus injection. Lowest-cost wins: move P3b before P3, replace `hash()` seeds, and make training/eval dependency boundaries executable.

## Findings

### HIGH-1: Schema guard is not yet an executable contamination boundary
- **Finding**: The design says `connect_training_view()` is the only training entry, but the current training export path already reads sqlite directly and is documented as consumed by M9 LoRA. Grep for `metrics.` misses quoted SQL, dynamic SQL, direct DuckDB connections, `read_parquet("...metrics...")`, and future Rust/Go tooling.
- **Evidence**: [design.md:47](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:47>), [design.md:53](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:53>), [export_log.py:5](</Users/johnd/ERRE-Sand Box/src/erre_sandbox/cli/export_log.py:5>), [export_log.py:121](</Users/johnd/ERRE-Sand Box/src/erre_sandbox/cli/export_log.py:121>).
- **Recommendation**: Add a behavioral CI test over every training egress command/API with sentinel `metrics` rows and assert no metric fields/values leave the process. `connect_training_view()` should return raw rows or a constrained relation, not an unrestricted DuckDB connection. If arbitrary SQL is needed, export a raw-only snapshot for training.
- **Severity rationale**: HIGH because contamination prevention is DB5’s core contract; implementing the wrong guard now creates later baseline/training rework.

### HIGH-2: Bootstrap CI must account for run and turn dependence
- **Finding**: `bootstrap_ci.py` is specified as NumPy resampling, but dialog turns are autoregressive and Tier B units are per-100-turn/window, not iid rows.
- **Evidence**: [design.md:208](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:208>), [design.md:354](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:354>), [decisions.md:198](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-b-lora-execution-plan/decisions.md:198>). SciPy’s bootstrap resamples observations as random samples ([docs](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)); time-series bootstrap methods preserve dependence with blocks ([arch docs](https://arch.readthedocs.io/en/stable/bootstrap/timeseries-bootstraps.html)).
- **Recommendation**: Specify hierarchical bootstrap: resample runs as clusters, then circular/stationary blocks within each 500-turn run. Choose block length via pilot/autocorrelation or sensitivity grid, and report Tier B CI as based on only 25 windows/persona unless widened.
- **Severity rationale**: HIGH because DB9 drift/adoption decisions become overconfident under iid resampling.

### HIGH-3: P3b pilot is ordered after the data it is supposed to tune
- **Finding**: The table runs P3 golden capture before P3b ratio tuning, so any ratio change forces a 7500-turn rerun. Also, 50 turns cannot evaluate Vendi if the expected window is 200 turns.
- **Evidence**: [design.md:19](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:19>), [design.md:20](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:20>), [design.md:118](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:118>), [research-evaluation-metrics.md:301](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:301>). Vendi is kernel/eigenvalue based over the sample ([OpenReview](https://openreview.net/forum?id=g97OHbQyk1)).
- **Recommendation**: Move P3b before P3 or freeze 200/300 and delete tuning. Minimum defensible pilot: at least 200 turns per condition per persona, fresh scheduler/store, isolated seeds, no carry-over into golden baseline.
- **Severity rationale**: HIGH because the current order can invalidate the golden baseline.

### HIGH-4: Stimulus injection target does not exist in the scheduler
- **Finding**: The design says `golden_baseline.py` pushes stimuli to the scheduler input queue, but `InMemoryDialogScheduler` has no input queue surface.
- **Evidence**: [design.md:124](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:124>), [design.md:130](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:130>), [dialog.py:103](</Users/johnd/ERRE-Sand Box/src/erre_sandbox/integration/dialog.py:103>), [dialog.py:253](</Users/johnd/ERRE-Sand Box/src/erre_sandbox/integration/dialog.py:253>).
- **Recommendation**: Define the actual additive surface before P0: either an external golden driver using public `schedule_initiate`/`record_turn`/`close_dialog`, or an explicit forced-dialog/stimulus hook with tests for the 70-stimulus battery.
- **Severity rationale**: HIGH because P2/P3 implementation will otherwise discover a missing API late.

### HIGH-5: Burrows Delta is specified as the wrong metric
- **Finding**: `burrows.py` is described as “function-word vector cosine,” but the research doc defines Burrows Delta as distance over z-scored function-word frequencies.
- **Evidence**: [design.md:193](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:193>), [research-evaluation-metrics.md:208](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-b-lora-execution-plan/research-evaluation-metrics.md:208>). Stylometry references Delta/z-score frequency workflows and 5k-word windows ([R Journal stylo](https://journal.r-project.org/articles/RJ-2016-007/)).
- **Recommendation**: Implement actual Burrows Delta, or rename the quorum submetric to Cosine Delta and update DB9 wording, thresholds, and tests.
- **Severity rationale**: HIGH because the primary persona-fit submetric would otherwise be mislabeled and non-comparable.

### MEDIUM-1: IPIP fallback trigger is not operational
- **Finding**: “ICC < 0.6 が頻発” has no denominator. LLM survey responses are known to show social desirability artifacts.
- **Evidence**: [design.md:91](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:91>), [design.md:419](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:419>); Salecha et al. report LLM social desirability bias in Big Five surveys ([arXiv](https://arxiv.org/abs/2405.06058)); Koo/Li-style ICC interpretation treats 0.5-0.75 as moderate ([effectsize docs](https://easystats.github.io/effectsize/reference/interpret_icc.html)).
- **Recommendation**: Define “frequent” as e.g. ≥2/3 personas with ICC point <0.6 or lower CI <0.5 after golden baseline. Add acquiescence/straight-line checks, balanced/reverse items, and a base-model/persona-prompt control.
- **Severity rationale**: MEDIUM because Option D is defensible, but the reopen trigger must be auditable.

### MEDIUM-2: DuckDB snapshot semantics are underspecified
- **Finding**: “G-GEAR writes, Mac rsyncs read-only” is safe only if Mac reads a closed or checkpointed copy, not the live file.
- **Evidence**: [design.md:31](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:31>). DuckDB permits multiple read-only processes but not multi-process writes and warns about file locks/shared directories ([DuckDB docs](https://duckdb.org/docs/current/connect/concurrency)).
- **Recommendation**: Require `CHECKPOINT`/close before rsync, copy to temp then rename, open Mac copy with `read_only=True`, and never analyze the live G-GEAR file over a shared filesystem.
- **Severity rationale**: MEDIUM because the design choice is fine, but the snapshot protocol needs a decision record.

### MEDIUM-3: Tier C lock/preflight has TOCTOU gaps
- **Finding**: `nvidia-smi` free-memory preflight can pass, then another process can load before Prometheus does unless the same lock is held through preflight, model load, and evaluation.
- **Evidence**: [design.md:157](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:157>), [design.md:433](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:433>). `flock -n` fails immediately if unavailable ([man page](https://man7.org/linux/man-pages/man1/flock.1.html)); `Persistent=` defaults false for timers ([systemd.timer](https://www.freedesktop.org/software/systemd/man/devel/systemd.timer.html)).
- **Recommendation**: Wrap the entire Tier C command in the flock; autonomous loop must use the same lock. Decide `Persistent=false` vs catch-up explicitly, and log skip with a distinct success exit code.
- **Severity rationale**: MEDIUM because Tier C is not the primary DB9 gate, but race semantics should be recorded.

### MEDIUM-4: Dependency placement contradicts the adopted library axis
- **Finding**: The summary says sentence-transformers is optional eval extra, but `design.md` puts it in core dependencies, which will pull heavy ML deps into normal sync/CI.
- **Evidence**: [design.md:302](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:302>), [design.md:309](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:309>), [ci.yml:31](</Users/johnd/ERRE-Sand Box/.github/workflows/ci.yml:31>).
- **Recommendation**: Keep core to `duckdb` if required; move `sentence-transformers`, `scipy`, `ollama`, `empath` under `eval`. Add eval-specific CI or marks so normal CI remains lightweight.
- **Severity rationale**: MEDIUM because it is reversible, but easy to get wrong during P0.

### MEDIUM-5: Seed generation uses nondeterministic Python `hash()`
- **Finding**: `seed = hash((persona_id, run_idx, ...))` is not stable across Python invocations.
- **Evidence**: [design.md:139](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:139>). Python documents salted hash values as unpredictable between runs ([Python docs](https://docs.python.org/3/reference/datamodel.html#object.__hash__)).
- **Recommendation**: Use `hashlib.blake2b`/SHA-256 to derive uint64 seeds, commit `golden/seeds.json`, and test exact seed manifest on Mac and G-GEAR.
- **Severity rationale**: MEDIUM because it directly affects reproducibility but is cheap to fix.

### MEDIUM-6: 50K Burrows token floor needs corpus-QC semantics
- **Finding**: “<50K noisy” is a placeholder, not a measured rule, and reference corpus provenance/licensing is not specified.
- **Evidence**: [design.md:422](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:422>), [blockers.md:33](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-b-lora-execution-plan/blockers.md:33>), [development-guidelines.md:176](</Users/johnd/ERRE-Sand Box/docs/development-guidelines.md:176>). Stylometry sample-length needs vary; <5k is often poor but 20k can still fail for some texts ([Computational Stylistics](https://computationalstylistics.github.io/projects/methodology/)).
- **Recommendation**: Replace the fixed floor with QC: per-language tokenization, public-domain/provenance metadata, ≥5k-word chunk stability tests, and a reopen condition based on Delta rank instability.
- **Severity rationale**: MEDIUM because it affects interpretability, but not P0 implementation shape.

### LOW-1: RoleEval wording may accidentally become Kant-only
- **Finding**: The battery names “Kant biographical MCQ” while stimulus files are per persona.
- **Evidence**: [design.md:103](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:103>), [design.md:223](</Users/johnd/ERRE-Sand Box/.steering/20260430-m9-eval-system/design.md:223>).
- **Recommendation**: Clarify persona-specific MCQs for Nietzsche/Rikyu, or label Kant-only MCQ as a non-comparative floor diagnostic.
- **Severity rationale**: LOW because P2 review can catch it, but ambiguity is cheap to remove.

## Cross-cutting observations
The main weakness is not model choice; it is boundary specification. Convert prose contracts into tests for: training egress, baseline immutability, block-bootstrap unit selection, and scheduler stimulus execution.

## Verification suggestions
- Add a red-team contamination fixture with unique metric sentinel strings and run every training export against it.
- Simulate AR(1) turn metrics and compare iid vs block CI width in `test_bootstrap_ci.py`.
- Run a 200-turn isolated pilot before golden capture and record whether it changes 200/300.
- Add a scheduler dry-run test that executes one full 70-stimulus cycle without relying on nonexistent queues.
- Add a Mac/G-GEAR seed manifest test using stable hash output.
