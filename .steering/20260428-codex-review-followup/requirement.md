# Codex review followup — verification 緑化 + 5 finding 修正

## 背景

2026-04-28 に外部 reviewer (Codex) による全 repo review が `codex_review.md` として
提出された。私 (Claude) が finding 別に厳密ジャッジした結果、6 finding すべて妥当
(数値根拠完全一致 + architecture rule 明示違反 + コメント vs 実装乖離検出)。

特に F1 は P1 bug (timeout close stale tick → dialog_close envelope 観測の timing
誤情報 + cooldown 短縮)、F2/F3 は documented verification path (`uv run ruff check
/ mypy src / pytest`) が不通 (78/18/8/7 errors)、F5 は architecture-rules SKILL
L39 の明示違反 (ui→integration import)、F6 は frame byte limit がコメントと実装
が乖離 (precise byte check が存在しない)。

放置すると CI 整備不能 + 観測データ汚染 + DoS 防御弱体化のリスク。

## ゴール

1. F1 (P1 bug) を再現テスト + 修正
2. F2/F3 (P1+P2) で documented verification path を緑化 (ruff / format / mypy / pytest 全通過)
3. F5 (P2 architecture violation) を contracts レイヤー新設 + ui 修正で解消
4. F6 (P3 byte limit) を multibyte regression test 付きで修正
5. Additional (evidence module の CognitionCycle import 軽量化) を併せ修正
6. F4 (Godot test crash) は **deferred** に確定 — local Godot 4.6.2 で再現せず (PR #111 Phase 7 で `pytest tests/test_godot_project.py -v` 3/3 PASS)。CI 整備時 (`.steering/20260428-ci-pipeline-setup/`) に env 整備と一緒に再検討

## スコープ

### 含むもの
- `src/erre_sandbox/integration/dialog.py` の `close_dialog` API 拡張 + `_close_timed_out` 修正
- `src/erre_sandbox/integration/gateway.py` の byte length check 追加
- `src/erre_sandbox/ui/dashboard/state.py` の import 修正 + 新規 `contracts/` モジュール導入
- `pyproject.toml` の `extend-exclude` 拡張 (`.steering/`, `erre-sandbox-blender/`)
- `README.md` の verification command を `ruff check src tests` に narrow
- 残 18 ruff errors / 8 format / 7 mypy errors の実修正
- regression test 追加 (F1: timeout tick、F6: multibyte payload)
- F4 の local 再現確認 (Godot binary がある環境で headless boot 検証)

### 含まないもの
- 大規模リファクタリング (各 finding の最小修正に留める)
- `.github/workflows/ci.yml` 新設 (`.steering/20260428-ci-pipeline-setup/` で別 task として起票)
- F4 の修正実装 (deferred 確定: local 再現せず、CI 整備時に env と一緒に再検討)
- 新機能追加 / 機能拡張
- LoRA / M9 関連 (前 PR #110 で確定済、本 task 無関係)

## 受け入れ条件

- [ ] `uv run ruff check src tests` が exit 0
- [ ] `uv run ruff format --check src tests` が exit 0
- [ ] `uv run mypy src` が exit 0
- [ ] `uv run pytest` 全通過 (F4 が local 再現せず deferred 確定したため Godot test も含む)
- [ ] F1 regression test 追加: timeout tick が world_tick で出力されること
- [ ] F6 regression test 追加: 64K 全角文字 (>64KB) が reject されること
- [ ] F5 architecture rule 違反解消: `grep -r "from erre_sandbox.integration" src/erre_sandbox/ui/` が空
- [ ] code-reviewer レビュー HIGH/CRITICAL なし

## 関連ドキュメント

- `codex_review.md` (本 task の入力、root に untracked で存在)
- `.claude/skills/architecture-rules/SKILL.md` L39 (ui 依存制約)
- `src/erre_sandbox/integration/__init__.py` L25 (allowed/forbidden boundary)
- M7 ζ-3 PR #107 (separation 系の最近の変更、F1 影響範囲精査対象)

## 運用メモ
- 破壊と構築（/reimagine）適用: **Yes**
- 理由: F5 (contracts レイヤー新設) は architecture 拡張で複数案あり (schemas.py 移動 vs
  contracts/ 新設 vs integration.metrics 直接 import allowlist)。F1 修正方法も
  `close_dialog(tick=)` パラメータ追加 vs `_close_dialog_at` helper 新設の 2 案あり。
  Plan mode 内で /reimagine 必須。
