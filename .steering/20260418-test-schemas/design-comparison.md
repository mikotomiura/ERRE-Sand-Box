# T08 test-schemas — 設計案比較

## v1（初回案）の要旨

既存 test_schemas.py を焦点拡張し、~15 件の境界値 / union negative / round-trip
テストを追加。`tests/conftest.py` には Kant 特化の単一 fixture `agent_state_kant`
を配置。test_schema_contract.py や JSON Schema golden は作らず、全テストを
test_schemas.py に集約する **保守的焦点拡張** 設計。

## v2（再生成案）の要旨

「Contract 凍結の **正式な閉幕儀式**」として 3 層契約ガードを構築:
(L1) 単体 boundary を parametrize テーブルで駆動し test_schemas.py に追記、
(L2) `tests/test_schema_contract.py` 新設で `schemas.__all__` を introspection
して `extra="forbid"` / `schema_version default` / discriminator 値整合を
meta-test、(L3) `tests/schema_golden/*.schema.json` を golden に据えて
Pydantic 生成 JSON Schema との文字列比較で drift 検知。
conftest は callable factory (`make_agent_state(**overrides)`) + convenience
fixture (`agent_state_kant`) の二層構成。NOTICE に CSDG 帰属追記 (T05 見送り分)。

## 主要な差異

| 観点 | v1 | v2 |
|---|---|---|
| 設計思想 | 焦点拡張 (テストを書き増やす) | 3 層契約ガード (layer で責務分離、introspection で未来証明) |
| テストファイル | test_schemas.py に集約 | test_schemas.py (L1) + test_schema_contract.py (L2+L3) 分離 |
| Factory パターン | Kant 固定の単一 fixture | Callable factory + Kant convenience の二層 |
| schema drift 検知 | なし | JSON Schema golden file 比較 (drift 時は CI 失敗 + 再生成手順誘導) |
| meta-test | なし | `__all__` introspection で全 BaseModel の `extra="forbid"` / `schema_version` を自動チェック |
| 新 BaseModel 追加時の対応 | 人力でテスト追記 | meta-test が自動で新モデルを対象に含む |
| Godot 側参照データ | なし | golden JSON Schema が将来の GDScript 型生成の情報源として機能 |
| 変更規模 | conftest + test_schemas + NOTICE (3 ファイル) | + test_schema_contract + schema_golden (4 ファイル) + README (合計 9 ファイル) |
| テスト数 (概算) | 43 → 60 | 43 → 75+ (parametrize 効果で実行件数増) |
| 境界値テストの網羅性 | 個別関数で手書き | (field_path, valid, invalid_below, invalid_above) table で parametrize 駆動 |
| Pydantic バージョン依存リスク | 低 (JSON Schema を使わない) | 中 (Pydantic 2.x 間で JSON Schema 出力差があり得る。pin + 再生成手順で管理) |
| CI 失敗メッセージの教育性 | 通常の AssertionError | drift 時に「再生成手順」を組み込み self-service 化 |
| conftest 拡張性 | variant ごとに新 fixture が必要 | factory の overrides で任意 variant に対応 |
| 境界タスクとしての強度 | 弱 (人力継続が必要) | 強 (導入後は schemas.py に追加される新モデルが自動追随) |

## 評価（各案の長所・短所）

### v1 の長所
- 実装コストが最小 (1 ファイル拡張のみ)
- Pydantic バージョンに敏感でない (JSON Schema 不使用)
- 読み手が一箇所を見れば全テストを把握できる

### v1 の短所
- **「Contract 凍結の境界」として機械的保証が薄い**: 新しい BaseModel が
  schemas.py に追加されても、忘れずに人力で `extra="forbid"` を検証する
  テストを書かない限り契約違反が検知されない
- fixture が Kant 固定で variant 必要時にコピペが発生
- schema drift (field 追加・削除・rename) の検知経路がない
- test_schemas.py が 300+ 行に肥大化し役割が混ざる
- NOTICE 以外の永続資産 (golden) が残らず、将来の GDScript 型生成の
  参照が手書きに戻る

### v2 の長所
- **requirement.md §ゴール**の「Phase C 閉幕 (以降 schemas.py の変更は
  schema_version bump が必要) を宣言可能な状態」に機械的に応える
- meta-test が `__all__` introspection ベースのため、将来 schemas.py に
  新 BaseModel を追加した時も契約ルールが自動適用
- golden file が schema drift を「実装後に気付く」から「CI で即失敗」に変換
- Callable factory により後続 T10-T14 が variant を自由に作れる
- テストファイルの責務分離で認知コストが下がる
- Pydantic + `TypeAdapter(X).json_schema()` を初導入することで、
  将来 `schema_export.py` スクリプトや OpenAPI 連携が容易になる
- 境界値テストを parametrize テーブルで駆動することで、新 field 追加時の
  追記コストが「table に 1 行」に圧縮される

### v2 の短所
- 実装コストが 1.4-1.6 倍 (ファイル 4 件追加)
- Pydantic バージョンが変わると JSON Schema 出力が微妙に変わる可能性
  (対処: pyproject で pin + README に再生成手順)
- golden file の差分レビューが発生 (contract を変えた PR で)
- `tests/schema_golden/` という新 test サブディレクトリが増える

## 推奨案

**v2 を採用** — 理由:

1. **requirement.md §背景の「Phase C 閉幕の境界」要求への正面応答**:
   v1 は test を書き増やすだけで、将来 schemas.py に新モデルが足されたとき
   `extra="forbid"` を忘れても検知できない。v2 の meta-test は schemas.py
   が育っても契約ルールを機械的に守り続ける。これが「境界」という言葉の
   本質的要求

2. **後続 T10-T14 の DX (開発者体験) 向上**:
   v2 の callable factory パターンは T10 memory / T11 inference /
   T12 cognition / T13 world / T14 gateway の各 Phase P タスクで
   「Kant agent を任意状態で生成してテスト」を 1 行で書けるようにする。
   v1 の Kant 固定 fixture はここで足かせ

3. **drift 検知の非対称的価値**:
   contract 破壊は 「schemas.py を変えた PR」が気付かず merge される形で
   起きる。v1 の手動 grep は人的ミスを排除しない。v2 の golden 比較は
   「CI が強制的に失敗 → 再生成手順誘導 → 意識的な bump」の健全なループを作る

4. **T05 decisions.md「contract の固さを将来タスクで維持」との整合**:
   T05 で discriminated union や SCHEMA_VERSION 付与によって contract-first
   精神を実装した。T08 でも同じ「機械で守る」精神を貫くのが設計の一貫性

5. **v2 の短所は対処可能**:
   実装コスト 1.4-1.6 倍は Phase C の最終 0.5d として許容範囲。Pydantic
   pin + 再生成手順 README で保守フローも明確化。レビューコストは「schema を
   変えた時こそ気付いて欲しい」機会

**ハイブリッド不採用の理由**:
v1 の保守的焦点拡張と v2 の契約ガードを混ぜる場合、meta-test や golden を
部分採用すると「どの契約が機械で守られ、どれが人力か」が不明瞭になる。
3 層全部を採用するか、全部なしにするかの方が clean。
