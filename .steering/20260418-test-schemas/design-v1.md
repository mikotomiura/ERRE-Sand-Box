# 設計 — T08 test-schemas (初回案 v1)

## 実装アプローチ

既存の test_schemas.py / test_personas.py / test_envelope_fixtures.py を
**焦点拡張** する戦略。境界値・Union ネガティブ・round-trip をケースごとに
手書きし、conftest.py に Kant-optimised な factory fixture を追加する。
JSON Schema golden / meta-test は導入しない (実装コスト重視)。

方針の要点:
1. conftest.py に `agent_state_kant` / `persona_spec_kant` / `envelope_handshake`
   の 3 fixture を追加
2. test_schemas.py に 15 件程度の境界・union negative テストを追記
3. test_schema_contract.py は作らず、既存ファイルに集約
4. JSON Schema golden file は導入しない
5. NOTICE に CSDG 帰属を追記

## 変更対象

### 修正するファイル
- `tests/conftest.py` — fixture 追加 (空 → ~30 行)
- `tests/test_schemas.py` — 7 件 → ~22 件にテスト追加
- `NOTICE` — CSDG 帰属追記

### 新規作成するファイル
- なし (全て既存ファイル拡張)

## 既存パターンとの整合性

- test-standards ルール 1: schemas.py → tests/test_schemas.py を維持
- test-standards ルール 3: conftest.py に factory 集約
- python-standards: 型ヒント / f-string / `from __future__ import annotations`

## テスト戦略

- 上記拡充で 43 件 → ~60 件程度
- pytest --collect-only で件数確認
- カバレッジ計測は入れない (MVP)

## ロールバック計画

- 新規テスト + conftest + NOTICE 編集のみ。git revert で単純復元

## v1 の自覚している懸念点

| 懸念 | 内容 |
|---|---|
| 「Contract 凍結の境界」としては弱い | meta-test と JSON Schema golden がないため、新しい BaseModel が追加された時に自動で contract チェックされない |
| conftest fixture が Kant 特化 | 他 persona のテストを書く時に wrapper が必要になる |
| schema drift 検知がない | schemas.py の field を追加・削除しても既存テストが通れば気付けない |
| 拡張性 | test_schemas.py が肥大化し 300+ 行になる見込み |
| GDScript 側リファレンスなし | JSON Schema を generate しないため、Godot 側の型生成参考にならない |
| factory 粒度 | Kant 固定の単一 fixture だけでは variant を持てない |

これらを引きずらず、`/reimagine` で v2 を生成する。
