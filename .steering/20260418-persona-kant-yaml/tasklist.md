# T06 persona-kant-yaml タスクリスト

## 準備
- [x] 関連 docs / skills を読む (persona-erre SKILL + domain-knowledge, glossary, PDF §3.1)
- [x] file-finder で既存の Kant / persona 参照を調査
- [x] `/reimagine` で v1 (documentary) → v2 (operational) 比較 → v2 採用

## 実装
- [ ] `personas/kant.yaml` を作成 (v2 設計に従う)
- [ ] `tests/test_personas.py` を作成
- [ ] `src/erre_sandbox/__init__.py` / schemas.py の追加 re-export は不要 (確認済)

## 静的解析
- [ ] `uv run ruff check src/ tests/` 警告ゼロ
- [ ] `uv run ruff format --check src/ tests/` パス
- [ ] `uv run mypy tests/` strict でパス

## テスト
- [ ] `uv run pytest` 全テストパス

## レビュー
- [ ] code-reviewer によるレビュー (YAML 内容 + テスト)
- [ ] HIGH 指摘への対応

## ドキュメント
- [ ] `decisions.md` に v2 採用理由と Kant 特有の判断 (sampling 値, 温度帯見取り図) を記録

## 完了処理
- [ ] Conventional Commits でコミット (`feat(personas): T06 persona-kant-yaml — ...`)
- [ ] `feature/persona-kant-yaml` を push し、main への PR を作成 (ユーザー承認後)
- [ ] `.steering/20260418-implementation-plan/tasklist.md` の T06 チェックを入れる
