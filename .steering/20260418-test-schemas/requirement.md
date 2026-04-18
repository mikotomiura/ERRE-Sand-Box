# T08 test-schemas

## 背景

MASTER-PLAN Phase C (Contract Freeze) の**最後のタスク**。T05 schemas-freeze で
スキーマを凍結、T06 で Kant persona、T07 で ControlEnvelope fixture を整備した。
Phase C 境界として、スキーマ全面の徹底テストを実施して contract を lock-in し、
Phase P (並列ビルド) で両機が安心して実装に入れる状態を作る。

現状、既存テスト 43 件 (test_schemas.py 7 / test_personas.py 10 /
test_envelope_fixtures.py 26) は smoke + fixture 中心で、以下のカバレッジが不足:

- 各フィールドの値域境界 (`_Unit` [0,1] / `_Signed` [-1,1] / `ge=0.5` 等) の網羅
- discriminated union のネガティブケース (未知 kind、missing discriminator)
- BaseModel 共通不変条件 (`extra="forbid"` が全モデルに設定、`schema_version`
  デフォルトが `SCHEMA_VERSION` と一致) の meta-test
- JSON Schema 出力の stability (schema drift の早期検知)
- AgentState / PersonaSpec / ControlEnvelope の factory fixture (後続
  T10-T14 で使い回す共通基盤)

また T05 decisions.md で見送った NOTICE への CSDG 帰属追記を本タスクで実施する。

## ゴール

- スキーマ全面の境界値・Union 網羅・round-trip 検証テストを追加
- `tests/conftest.py` に AgentState / PersonaSpec / Envelope の factory fixture
- 契約 drift 検知のための JSON Schema 安定性テスト
- NOTICE に CSDG (MIT) 帰属を追記
- `uv run pytest` が拡大したテストで全パス。ruff / mypy strict も維持
- Phase C 閉幕 (以降 schemas.py の変更は schema_version bump が必要) を宣言可能な状態

## スコープ

### 含むもの
- `tests/conftest.py` にファクトリフィクスチャ追加
  - `make_agent_state`: 最小引数で AgentState を生成
  - `make_persona`: PersonaSpec の最小インスタンス
  - `make_envelope`: kind 別 ControlEnvelope メンバを生成
- `tests/test_schemas.py` の拡張
  - 境界値テスト (_Unit / _Signed / 明示的な ge/le)
  - discriminated union の negative cases (未知 kind, missing kind, wrong payload)
  - 全 Observation event_type の validate
  - AgentState / PersonaSpec round-trip (JSON 経由)
- `tests/test_schema_contract.py` 新設 (meta-tests)
  - schemas `__all__` の全 BaseModel に `extra="forbid"` が設定されているか
  - schema_version フィールドを持つモデル (AgentState / PersonaSpec /
    `_EnvelopeBase` 継承) でデフォルトが SCHEMA_VERSION と一致
  - ControlEnvelope 全 kind が schemas.py と fixtures/ で整合
  - JSON Schema 生成の安定性 (schema_golden との比較)
- `fixtures/schema_reference/` (or別名) に JSON Schema golden
  ファイル 3 種 (AgentState / PersonaSpec / ControlEnvelope) を配置
  - 詳細は design で判断
- `NOTICE` に CSDG 帰属を追記
- `.steering/20260418-implementation-plan/tasklist.md` の T08 チェック

### 含まないもの
- pyproject.toml の `warn_return_any = true` への昇格 (T10 判断を維持)
- hypothesis 等の追加依存 (今 MVP では標準 pytest で十分)
- Observation / MemoryEntry の JSON fixture 追加 (契約の核ではない)
- T05-T07 の schemas.py / personas / fixtures の実装修正
  (T08 は検証タスクであり、欠陥発見時のみ fix は本 PR で、拡張は別 PR)
- Godot 側の contract 検証 (GDScript 実装は T16 の責務)

## 受け入れ条件

- [ ] `tests/conftest.py` に 3 種のファクトリフィクスチャが存在
- [ ] `tests/test_schemas.py` に境界値 / union negative / round-trip テスト追加
- [ ] `tests/test_schema_contract.py` 新設、meta-tests 実装
- [ ] JSON Schema golden ファイルが存在し、CI で schema drift を検知
- [ ] `NOTICE` に CSDG (https://github.com/mikotomiura/cognitive-state-diary-generator、MIT) が記載
- [ ] `uv run pytest` 全パス (現状 43 件 → +αX 件)
- [ ] `uv run ruff check src/ tests/` 警告ゼロ
- [ ] `uv run ruff format --check src/ tests/` パス
- [ ] `uv run mypy src/erre_sandbox/ tests/` strict でパス
- [ ] Conventional Commits でコミット & PR 作成
- [ ] `.steering/20260418-implementation-plan/tasklist.md` の T08 チェック入り

## 関連ドキュメント

- `src/erre_sandbox/schemas.py` 全体 (特に `__all__`)
- `tests/test_schemas.py`, `tests/test_personas.py`, `tests/test_envelope_fixtures.py`
- `.claude/skills/test-standards/SKILL.md`
- `.steering/20260418-schemas-freeze/decisions.md` (CSDG 帰属の見送り記録)
- `.steering/20260418-implementation-plan/MASTER-PLAN.md` §4.2 T08 行

## 運用メモ

- 破壊と構築（/reimagine）適用: **Yes**
- 理由: 「境界タスク」としてテスト戦略に明確な選択肢がある。
  焦点拡張型 (v1) vs meta-test + golden file 型 (v2) の 2 方向は、
  保守コスト・drift 検知・拡張性の観点で異なるトレードオフを持つ
- タスク種別: その他 (契約凍結の境界、テスト拡張 + NOTICE 更新)
- 使用するサブエージェント:
  - file-finder で既存 JSON Schema 生成箇所や CI hook の探索
  - code-reviewer で実装後のレビュー
- 注意事項:
  - pyproject `warn_return_any` 昇格判断は T10 に持ち越す (T05 decisions 判断 6 維持)
  - 本タスクで schemas.py を変更しない (変更が必要なら schema_version bump を伴う別 PR)
