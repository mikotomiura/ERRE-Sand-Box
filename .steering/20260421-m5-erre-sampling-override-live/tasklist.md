# タスクリスト — m5-erre-sampling-override-live

## 準備

- [x] persona-erre Skill §ルール 2 を再読 (delta テーブルの source)
- [x] `src/erre_sandbox/erre/fsm.py` の `ZONE_TO_DEFAULT_ERRE_MODE` pattern 確認
- [x] `cycle.py::_maybe_apply_erre_fsm` (L331-385) の hook ロジック確認
- [x] `compose_sampling` の 3 呼び出し箇所 (cycle/reflection/ollama_adapter) 確認
- [x] `feature/m5-erre-sampling-override-live` branch 作成 (origin/main rebase 済)

## 実装

### Step 1: TDD — test_sampling_table 赤で作成

- [x] `tests/test_erre/test_sampling_table.py` 新規作成 (6 test groups,
      43 parametrized cases)
- [x] `uv run pytest tests/test_erre/test_sampling_table.py` が ImportError
      で赤であることを確認

### Step 2: `erre/sampling_table.py` 実装

- [x] `src/erre_sandbox/erre/sampling_table.py` 新規作成
      (`SAMPLING_DELTA_BY_MODE` + `MappingProxyType`)
- [x] `src/erre_sandbox/erre/__init__.py` に re-export 追加
- [x] `uv run pytest tests/test_erre/test_sampling_table.py` 43/43 緑

### Step 3: TDD — test_cycle_erre_fsm 拡張

- [x] 2 tests 追加:
      `test_cycle_erre_policy_populates_sampling_overrides_from_table` /
      `test_cycle_erre_policy_noop_preserves_sampling_overrides`
- [x] 1 failed (populates) / 1 passed (noop) の混在赤を確認

### Step 4: `cycle.py` の FSM hook を拡張

- [x] `from erre_sandbox.erre import SAMPLING_DELTA_BY_MODE` 追加
- [x] `_maybe_apply_erre_fsm` の `ERREMode(...)` に
      `sampling_overrides=SAMPLING_DELTA_BY_MODE[candidate]` 追加
- [x] docstring 更新 (Step 5 LLM call との因果を 1 文追記)
- [x] `uv run pytest tests/test_cognition/test_cycle_erre_fsm.py` 全緑

## テスト

- [x] `uv run pytest -q` → 594 passed, 31 skipped (0 failed)
- [x] `uv run ruff check src tests` PASS
- [x] `uv run ruff format --check src tests` PASS (auto-fix 後)
- [x] `uv run mypy src/erre_sandbox` → 0 errors

## レビュー

- [x] `code-reviewer` subagent: HIGH なし / MEDIUM 2 件 / LOW 2 件
- [x] MEDIUM 2 件 (fail-open vs fail-fast / SamplingDelta frozen 化) は
      `decisions.md` §判断 1・2 に記録 (スコープ外として受容)
- [x] LOW 1 件 (SamplingBase 0.0 の clamp コメント) はテストに追記済
- [x] LOW 1 件 (非ゼロ delta agent での no-op test) は `decisions.md` §判断 3 に記録
- [x] `impact-analyzer`: スキップ (limited scope、code-reviewer で十分)

## ドキュメント

- [x] `docs/functional-design.md` に `m5-erre-sampling-override-live` の
      結果を M5 section に追記
- [x] `docs/glossary.md`: 新用語なし (既存 "ERRE モード" の範囲内)
- [x] `decisions.md` 作成 (判断 1-4)

## 完了処理

- [x] 全 steering ファイル最終化
- [ ] `git commit` (Conventional Commits):
      `feat(erre): apply ERRE mode sampling delta table on FSM transition`
- [ ] `git push -u origin feature/m5-erre-sampling-override-live`
- [ ] PR 作成 → self-review → merge

## 制約・リマインダ

- `main` 直 push 禁止
- persona-erre Skill §ルール 2 の値と完全一致 (drift 防止)
- architecture-rules §レイヤー表準拠 (`erre/ → schemas.py` のみ依存、
  `cognition/ → erre/` は許容)
- 既存 549 test に回帰なし
- FSM 無効 (erre_policy=None) の既存挙動を byte-identical に維持
