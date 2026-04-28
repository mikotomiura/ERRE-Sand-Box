# タスクリスト

## 準備
- [x] codex_review.md 全件 verdict ジャッジ済 (6 valid + 1 棄却)
- [x] file-finder + impact-analyzer 相当を Explore agent 並列で実施
- [x] architecture-rules SKILL L39 確認済 (ui→schemas のみ)
- [x] dialog.py / gateway.py / metrics.py / store.py 影響範囲 read 済

## 実装 (Phase 1-7)

### Phase 1: F1 (timeout close stale tick)
- [x] regression test 3 件 RED 確認 (`tests/test_integration/test_dialog.py`)
- [x] `dialog.py:close_dialog` に `*, tick: int | None = None` 追加 + `_close_dialog_at` helper 抽出
- [x] `_close_timed_out` で `tick=world_tick` 渡す
- [x] `world/tick.py:1247` (exhausted) で `tick=world_tick` 渡す
- [x] `schemas.py:1239` Protocol に optional 拡張 + docstring "non-breaking" 注記
- [x] GREEN 確認 (24/24 in test_dialog.py)

### Phase 2: F6 (frame byte limit)
- [x] regression test 1 件 RED 確認 (`tests/test_integration/test_gateway.py`)
- [x] `gateway.py:_parse_envelope` に byte length check 追加 + コメント整合
- [x] GREEN 確認 (22/22 + boundary test 追加で 23/23)

### Phase 3: F5 (ui→integration architecture)
- [x] architecture invariant test 2 件 (`tests/test_architecture/test_layer_dependencies.py`)
- [x] `src/erre_sandbox/contracts/__init__.py` 新規
- [x] `src/erre_sandbox/contracts/thresholds.py` 新規 (mechanical move)
- [x] `src/erre_sandbox/integration/metrics.py` を shim に短縮
- [x] `src/erre_sandbox/ui/dashboard/state.py:27` を `from erre_sandbox.contracts import ...` に切替
- [x] `.claude/skills/architecture-rules/SKILL.md` テーブル更新 (contracts/ レイヤー追加)
- [x] 既存 test_contract_snapshot.py 通過確認 (shim 経由)

### Phase 4-5: lint + mypy 緑化
- [x] `pyproject.toml:80` extend-exclude に `.steering`, `erre-sandbox-blender` 追加
- [x] `ruff check src tests --fix` で 12 件 auto-fix
- [x] 手動 6 件: S608 noqa×2 (memory/store.py:973,1084), ARG001 noqa×2 (test_dialog_sink.py), PLC0415 noqa×1 (evidence/metrics.py:235), TC001 TYPE_CHECKING (test_runtime_lifecycle.py)
- [x] `ruff format src tests` で 8 ファイル auto-fix
- [x] mypy 7 件: cycle.py:793,798 (isinstance narrowing), evidence/metrics.py 5 件 (dict generic + isinstance narrowing)

### Phase 6: README narrow
- [x] `README.md` L58 を `ruff check src tests` に narrow (EN + JA 2 箇所)
- [x] `ruff format --check src tests` も追記

### Phase 7: F4 判定
- [x] `which godot` → `/opt/homebrew/bin/godot` (4.6.2.stable.official) 検出
- [x] `pytest tests/test_godot_project.py -v`: 3/3 PASS (local 再現せず)
- [x] **判定**: deferred (環境依存、別 task で扱う)

## テスト
- [x] 単体テスト追加 (F1: 3件, F6: 2件, F5: 2件 architecture invariant)
- [x] regression test すべて GREEN
- [x] 既存テスト regression なし (1044 passed, 28 skipped, exit 0)

## レビュー (Phase 8)
- [x] code-reviewer による diff レビュー
- [x] HIGH 1 件対応 (test_layer_dependencies.py docstring に「dynamic import 対象外」明記)
- [x] MEDIUM 2 件対応 (F6 boundary test 追加 + by_dialog 型整合修正)
- [x] LOW 1 件対応 (`_close_dialog_at` docstring 追加)
- [x] LOW 1 件 deferred (cognition/cycle.py float→int 切り捨ては defensive で意図通り)

## ドキュメント (Phase 9)
- [x] decisions.md 起草 (D1-D6, hybrid 採用根拠)
- [x] tasklist.md (本ファイル) 最終化
- [ ] docs/ の更新は不要 (architecture-rules SKILL 内で完結)

## 完了処理 (Phase 10)
- [x] 受け入れ条件 grep 検証
  - `uv run ruff check src tests`: PASS ✓
  - `uv run ruff format --check src tests`: PASS ✓
  - `uv run mypy src`: PASS (53 source files) ✓
  - `uv run pytest`: 1044 passed, 28 skipped, exit 0 ✓
  - F1 regression: 3 件追加 ✓
  - F6 regression: 2 件追加 (multibyte + boundary) ✓
  - `grep -r "from erre_sandbox.integration" src/erre_sandbox/ui/`: empty ✓
  - code-reviewer HIGH なし (対応済) ✓
- [ ] git commit (conventional commits 分割: `fix(integration)` + `refactor(architecture)` + `chore(lint)`)
- [ ] git push -u origin fix/codex-review-followup
- [ ] gh pr create
