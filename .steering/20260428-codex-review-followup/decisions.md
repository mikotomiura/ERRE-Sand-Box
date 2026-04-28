# 重要な設計判断

採用方針: 全 finding で `/reimagine` の v1 + v2 + 第3案 を起草、hybrid を採用。
plan ファイル: `/Users/johnd/.claude/plans/indexed-growing-moth.md` (本タスク承認済)。

---

## D1. F1 (timeout close stale tick) — close_dialog kwarg + helper hybrid

- **判断日時**: 2026-04-28
- **背景**: `_close_timed_out(world_tick)` が current tick を持っているのに
  `close_dialog(did, reason="timeout")` で渡さず、`dialog.last_activity_tick`
  が `DialogCloseMsg.tick` と `_last_close_tick` の両方に書き込まれていた。
  exhausted (`world/tick.py:1247`) も同様。
- **選択肢**:
  - **v1 (optional param)**: `close_dialog(dialog_id, reason, tick: int | None = None)`
    後方互換、Protocol も optional 拡張で済む。再発リスクあり。
  - **v2 (required keyword-only)**: `close_dialog(..., *, tick: int)` 全 caller
    に明示要求、再発防止強い。M4 frozen Protocol を破る。
  - **第3案 (helper layer)**: `_close_dialog_at(...tick)` を主、`close_dialog`
    薄ラッパー。Protocol 不変だが exhausted 経路に届かない。
- **採用**: **hybrid (v1 optional + 第3案 helper 抽出)**
  - `close_dialog` に `*, tick: int | None = None` を keyword-only optional 拡張
  - `_close_dialog_at(dialog_id, reason, tick)` helper を抽出
  - `_close_timed_out` と `world/tick.py:1247` (exhausted) で `tick=world_tick` 渡す
  - `schemas.py:1239` Protocol に同 optional 拡張 + docstring に
    "M4 frozen + 2026-04-28 codex F1 non-breaking optional extension" を明記
- **理由**: v2 は M4 frozen docstring と衝突、第3案単独では exhausted 経路 (Protocol
  caller) に届かない。v1 + helper の組合せで Protocol 非破壊 + 全 caller 明示 +
  内部ロジック一元化を同時に実現。
- **トレードオフ**: `tick` を省略する legacy caller の挙動は不変のため、再発リスク
  ゼロではない。docstring で明示指定を推奨。
- **影響範囲**: `dialog.py`、`world/tick.py:1247`、`schemas.py:1239`、
  `test_dialog.py` (3 件 regression test 追加)
- **見直しタイミング**: 別 caller が追加された際、tick 省略のまま使われていないか
  code-reviewer で監視。
- **次アクション**: `tasklist.md` Phase 1 完了。

---

## D2. F5 (ui→integration) — contracts/ 新設 + shim hybrid

- **判断日時**: 2026-04-28
- **背景**: `ui/dashboard/state.py:27` が `from erre_sandbox.integration import
  M2_THRESHOLDS, Thresholds` で `architecture-rules` SKILL L39 (`ui → schemas
  のみ`) に違反。`integration/__init__.py` 経由で gateway/dialog の重い import
  graph を ui に持ち込む副作用あり。
- **選択肢**:
  - **v1 (sub-path import)**: `from erre_sandbox.integration.metrics import ...`
    に切替 + SKILL allowlist 拡張。物理は治るが規範違反は残る。
  - **v2 (contracts/ 新設)**: 新レイヤー `src/erre_sandbox/contracts/` で
    Thresholds + M2_THRESHOLDS を hosting、SKILL に明示追加。長期的に正面突破。
  - **第3案 (schemas.py 統合)**: Thresholds を schemas.py に追加。SKILL を
    1 文字も変えずに合法化。schemas.py の責務拡大 + snapshot test 破壊リスク。
- **採用**: **hybrid (v2 contracts/ + v1 sub-path on the way)**
  - 新規 `src/erre_sandbox/contracts/__init__.py` + `contracts/thresholds.py`
    (mechanical move from integration/metrics.py)
  - `integration/metrics.py` を `from erre_sandbox.contracts.thresholds import ...`
    の shim に短縮 (`__all__` 維持で `from erre_sandbox.integration import ...`
    既存テスト無破壊)
  - `ui/dashboard/state.py:27` を `from erre_sandbox.contracts import ...` に切替
  - `architecture-rules` SKILL L24-40 のテーブルに `contracts/` 行追加、
    `ui/` 依存先を `schemas.py + contracts/` に拡張
  - `tests/test_architecture/test_layer_dependencies.py` (新規) に grep
    invariant 2 件 (`ui ↛ integration`、`contracts ↛ heavy layers`)
- **理由**: v1 は規範違反残り、第3案は schemas.py 責務拡大 + snapshot test 破壊
  リスク。v2 を主、shim で v1 の互換性も担保し、二重化で破壊しない。
- **トレードオフ**: shim 維持コスト (将来 `integration.metrics` を完全削除する
  際は呼び出し元 grep + 一括書き換えが必要)。
- **影響範囲**: `contracts/` package 新設、`integration/metrics.py` 内容空洞化、
  `ui/dashboard/state.py:27`、`architecture-rules` SKILL、`tests/test_architecture/`
  新規ディレクトリ
- **見直しタイミング**: 次の全 repo audit で `from erre_sandbox.integration` を
  ui/ 配下で検出した時点で grep test が fail、即時是正。`contracts/` に他の
  軽量定数 (`DEFAULT_TICK_SECONDS` 等、Codex Additional finding) を追加検討。
- **次アクション**: `tasklist.md` Phase 3 完了。

---

## D3. F6 (frame byte limit) — char check 後に byte check 追加

- **判断日時**: 2026-04-28
- **背景**: `gateway.py:367-371` のコメントが「precise byte check on near-limit
  frames」と謳うが、実装に byte check が存在しない。64K 全角 (3byte/char) =
  192KB が char check (codepoints) を通過する。
- **選択肢**:
  - **v1 (char + byte 二段)**: char check で ASCII 大半を最速 reject、byte check
    で multibyte safety を保証。
  - **v2 (byte only)**: char check を削除して byte check に統一。コードシンプル
    だが ASCII frame ごとに encode() コピーが発生。
- **採用**: **v1 (二段)** — コメントの当初意図に整合
  - `len(raw) > _MAX_RAW_FRAME_BYTES` で cheap path
  - `len(raw.encode("utf-8")) > _MAX_RAW_FRAME_BYTES` で multibyte safety
  - regression test 2 件: oversize multibyte (codex 指摘) + boundary case
    (bytes ぴったり許容、code-reviewer M2 指摘で追加)
- **理由**: コメントが既に「two-stage」を約束しており、コードと意図を整合させる
  のが正解。ε filter で日本語 utterance を頻繁に扱うため byte check 必要。
- **トレードオフ**: char check 後の byte check で encode() 1 回コピー。CJK 比率
  が高い run では hot path 化する可能性 (code-reviewer M1)、現状維持で十分。
- **影響範囲**: `gateway.py:_parse_envelope`、`test_gateway.py` (2 件 regression)
- **見直しタイミング**: live profiler で encode() が CPU top に出たら最適化検討
- **次アクション**: `tasklist.md` Phase 2 完了。

---

## D4. F2/F3 (verification path) — README narrow + extend-exclude 拡張

- **判断日時**: 2026-04-28
- **背景**: README L56-60 が `uv run ruff check / mypy src / pytest` を
  documented verification path として宣言するが、`ruff check` (no args) が
  `.steering/`、`erre-sandbox-blender/` を scan して 78 errors。
- **選択肢**:
  - **v1 (extend-exclude 拡張)**: pyproject に `.steering`, `erre-sandbox-blender`
    追加、README は変更なし。`ruff check` (no args) で緑。
  - **v2 (README narrow)**: README を `ruff check src tests` に narrow、
    pyproject 不変。意図された target を明示。
  - **hybrid (両方)**: pyproject extend-exclude 拡張 **and** README narrow。
    将来 `ruff check` (no args) が誤って scan しても safe net、README は意図
    明示。
- **採用**: **hybrid (両方)**
  - `pyproject.toml:80` extend-exclude に `.steering`, `erre-sandbox-blender` 追加
  - `README.md` L56-61 を `uv run ruff check src tests` + `uv run ruff format
    --check src tests` に narrow (EN + JA 2 箇所)
  - 残 18 ruff (12 auto-fix + 6 手動: S608 noqa×2、ARG001 noqa×2、PLC0415
    noqa×1、TC001 TYPE_CHECKING)
  - 残 8 format (全 auto-fix)
  - 残 7 mypy (cycle.py 2 件 isinstance narrowing、evidence/metrics.py 5 件
    dict generic + isinstance narrowing)
- **理由**: 単 v1 だと README の `mypy src` / `pytest` と表記不揃い、単 v2 だと
  将来の `.steering` artifact ノイズが残る。両方で defense-in-depth。
- **トレードオフ**: pyproject 修正 + README 修正の 2 箇所メンテ。
- **影響範囲**: `pyproject.toml:80`、`README.md` (2 箇所)、20+ ファイル lint/mypy
  修正
- **見直しタイミング**: CI 整備時 (`.github/workflows/ci.yml`) に再検討
- **次アクション**: `tasklist.md` Phase 4-5 完了。

---

## D5. F4 (Godot test crash) — local 再現せず deferred

- **判断日時**: 2026-04-28
- **背景**: codex 環境で Godot headless boot が log dir 問題で crash → pytest
  fail (`test_godot_project_boots_headless`)。本 task で local 再現確認後に判断。
- **選択肢**:
  - **v1 (修正)**: `tests/_godot_helpers.py` に `--user-dir` で repo-local
    一時 dir 指定 + 既知 crash detection で skip。
  - **v2 (deferred)**: local 再現せず → 環境依存、修正不要。
- **採用**: **v2 (deferred)**
  - `which godot` → `/opt/homebrew/bin/godot` (4.6.2.stable.official)
  - `pytest tests/test_godot_project.py -v`: 3/3 PASS
  - codex 環境 (Linux sandbox? containerized?) 固有の log dir 権限問題と推測
- **理由**: local で再現せず、修正の必要性根拠が弱い。env-specific 修正は別 task
  で扱うべき (例: `m10-ci-godot-headless` 起票時に再検討)。
- **トレードオフ**: codex 環境では今後も fail し続ける可能性。
- **影響範囲**: なし (修正なし)
- **見直しタイミング**: CI に Godot を含める時点 (M10+) で env 整備と一緒に対応
- **次アクション**: 別 task で起票するか、codex を local Mac 等で実行
  (環境依存問題の特定が先)。

---

## D6. Codex Additional findings — evidence/CognitionCycle import (棄却)

- **判断日時**: 2026-04-28
- **背景**: codex Additional に `evidence/metrics.py` が `CognitionCycle` を
  `DEFAULT_TICK_SECONDS` のためだけに import している指摘。
- **選択肢**:
  - **v1 (移転)**: `DEFAULT_TICK_SECONDS` を `contracts/timing.py` に移転して
    evidence の import 重量を下げる。
  - **v2 (棄却)**: 実は class attribute access (`CognitionCycle.DEFAULT_TICK_SECONDS`)
    で軽量、import は class graph load を強制しない。問題なし。
- **採用**: **v2 (棄却)**
- **理由**: import コスト調査で実害なし。`contracts/` レイヤーは F5 で新設済、
  将来 `DEFAULT_TICK_SECONDS` を相互参照する new module が出た時に移転検討。
- **次アクション**: `decisions.md` D2 (F5) で `contracts/` 拡張を明記、本件は
  no-action。
