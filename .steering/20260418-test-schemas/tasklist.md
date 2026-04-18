# T08 test-schemas タスクリスト

## 準備
- [x] 関連 docs / skills を読む (test-standards, python-standards, schemas.py)
- [x] file-finder で既存 TypeAdapter / conftest / NOTICE / CI / hypothesis を調査
- [x] `/reimagine` で v1 (焦点拡張) → v2 (3 層契約ガード) を比較し v2 採用

## 実装
- [ ] `tests/conftest.py` に factory fixture (make_agent_state / make_persona / make_envelope) + convenience (agent_state_kant)
- [ ] `tests/test_schemas.py` に Layer 1 追加
  - 境界値テスト (parametrize table)
  - discriminated union negative
  - 全 Observation event_type validate
  - round-trip (AgentState / PersonaSpec)
- [ ] `tests/test_schema_contract.py` 新設
  - Layer 2: meta-invariant (全 BaseModel の extra=forbid / schema_version default)
  - Layer 3: JSON Schema golden 比較
- [ ] `tests/schema_golden/` に 3 種 golden + README
- [ ] `NOTICE` に CSDG (MIT) 帰属を追記

## 静的解析
- [ ] `uv run ruff check src/ tests/` 警告ゼロ
- [ ] `uv run ruff format --check src/ tests/` パス
- [ ] `uv run mypy src/erre_sandbox/ tests/` strict でパス

## テスト
- [ ] `uv run pytest` 全テストパス (現状 43 → ~75 件)

## レビュー
- [ ] code-reviewer によるレビュー (3 層契約ガード + NOTICE 更新)
- [ ] HIGH 指摘への対応

## ドキュメント
- [ ] decisions.md に v2 採用理由と golden 再生成フローを記録
- [ ] `tests/schema_golden/README.md` で再生成手順を明記

## 完了処理
- [ ] Conventional Commits でコミット (`test(schemas): T08 test-schemas — Phase C 契約ガード 3 層構築 + CSDG 帰属追記`)
- [ ] `feature/test-schemas` を push し、main への PR を作成 (ユーザー承認後)
- [ ] `.steering/20260418-implementation-plan/tasklist.md` の T08 チェック
