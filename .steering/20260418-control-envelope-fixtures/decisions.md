# 重要な設計判断 — T07 control-envelope-fixtures

## 判断 1: `fixtures/` を top-level 配置 (v1 pytest-centric を破棄)

- **判断日時**: 2026-04-18
- **背景**: 初回案 (v1) は pytest 慣習に従い `tests/fixtures/control_envelope/` に配置
- **選択肢**:
  - A: `tests/fixtures/control_envelope/` (pytest-centric)
  - B: `fixtures/control_envelope/` (top-level、`personas/` と並列)
- **採用**: B (v2)
- **理由**:
  - requirement.md §スコープが明示的に `fixtures/control_envelope/` を指定
  - 「両言語から読める / Godot developer が Python 依存なしで読める」要件に応えるには top-level が自然
  - T06 で確立した「top-level ドメイン資産 (`personas/`)」パターンと一貫
  - Contract-First 精神を Godot 側へも浸透させる
- **トレードオフ**: repo ルートの cognitive load が増える (新 top-level dir)。`repository-structure.md` の更新が必要
- **見直しタイミング**: 将来 `fixtures/observation/` / `fixtures/memory/` 等が増えた時、命名階層の見直し
- **詳細**: `design-comparison.md`

## 判断 2: Coherent scenario で 7 fixture を束ねる

- **判断日時**: 2026-04-18
- **背景**: minimal-validator-passing (v1) では Godot 側の実データ検証に弱い
- **採用**: tick=42 の 1 瞬間、Kant (`a_kant_001`) が peripatos で歩行する一貫シーンのスナップショット群
- **理由**: Godot 開発者が 7 ファイルを並べて読むと 1 シーンが立ち上がり、T16 godot-ws-client 着手時の実体験となる
- **結果**: 全 fixture で `sent_at` / `tick` (handshake 除く) / `agent_id` (ある場合) が同一値。test_shared_invariants_across_fixtures で担保

## 判断 3: `peripatetic` モードの sampling_overrides = (+0.3, +0.05, -0.1)

- **判断日時**: 2026-04-18
- **背景**: `agent_update.json` の ERRE mode sampling_overrides 値
- **選択肢**: Kant の SamplingBase (0.60) に対するこの delta が意図通りか
- **計算**:
  - base temperature 0.60 + peripatetic delta 0.30 = 0.90 (DMN 発散思考を促進)
  - base top_p 0.85 + 0.05 = 0.90
  - base repeat_penalty 1.12 + (-0.10) = 1.02
- **採用**: persona-erre Skill のモード早見表 `peripatetic: +0.3 / +0.05 / -0.1` をそのまま適用
- **理由**: fixture は規範的 reference なので Skill 定義値を使う。Skill 側は Oppezzo & Schwartz 2014 の "+60% divergent thinking" に根拠
- **影響範囲**: T11/T12 で実装する合成関数 `SamplingBase + SamplingDelta → clamped float` が、この fixture を正解データとして参照

## 判断 4: Kant 発話に *Beschluss* 冒頭文の後半句を使う

- **判断日時**: 2026-04-18
- **背景**: speech.json に何を入れるかは Kant らしさを演出する鍵
- **選択肢**:
  - A: プレースホルダー ("Hello world" 等)
  - B: Kant 原典の German 断片
- **採用**: B — *Kritik der praktischen Vernunft* (1788) の *Beschluss* 冒頭:
  "Der bestirnte Himmel über mir und das moralische Gesetz in mir."
- **理由**: 公有 (public domain) で確実、Kant を象徴する最も有名な断片の 1 つ、Godot 開発者が speech bubble 表示を調整する時の現実的サンプルになる
- **見直しタイミング**: persona を差し替える時 (fixture は Kant に紐づくため fixture も差し替え)
- **注意**: README には正確に「*Beschluss* の冒頭文の後半句」と記述 (code-reviewer HIGH #1 修正)

## 判断 5: code-reviewer の HIGH 指摘への対応

- **判断日時**: 2026-04-18
- **対応内容**:
  1. **歴史的正確性** (HIGH #1): README の `"famous closing line"` を
     `"fragment of the Beschluss (conclusion)"` に訂正。正確には Beschluss は
     結論章であり、冒頭文の後半句が最も引用される
  2. **EXPECTED_KINDS の動的抽出** (HIGH #2): テスト側で kind 一覧を
     ハードコードせず、`get_args(ControlEnvelope)` で union メンバから
     `model_fields["kind"].default` を抽出して構築。新 kind 追加時に
     テストが自動追随する

## 判断 6: MEDIUM 指摘への対応

- **handshake tick=0 の注記**: README で "tick=42 (except handshake.json: session start)" と明示
- **sampling_overrides 値の decision 記録**: 判断 3 として明文化
- **`validate_python(json.loads(...))` → `validate_json(bytes)`**: 実際の
  WebSocket 受信パスに近い。bytes → Pydantic の一気通貫を検証
- **repository-structure.md 責務の一般化**: `control_envelope/` をハードコードせず
  「schemas.py の discriminated union ごとにサブディレクトリ」という generic 表現に
- **error.json detail の意図明示**: README で "`mode_change` is deliberately invalid" と注記

## 見送り (LOW 指摘、後続で対応可)

- **`_fixture_paths()` の重複呼び出し**: 今回 `_FIXTURE_PATHS` モジュール定数化で解決済み (MEDIUM 転用)
- **Godot `Time` API の正確なメソッドチェーン**: T16 godot-ws-client 着手時に確認
- **SKILL.md の `mode_change` 旧名言及**: error.json detail への相互参照は明示済。SKILL.md 側の補足は T16 で

## 関連する後続タスク

- **T08 test-schemas**: conftest.py に agent_state factory fixture を追加。
  本 fixture ファイルを conftest.py のフィクスチャとしても再利用できる
- **T11 inference-ollama-adapter**: SamplingBase + SamplingDelta の合成関数を実装し、
  本 fixture を正解データとして参照
- **T14 gateway-fastapi-ws**: 本 fixture を WebSocket 初期応答のテストデータに使う
- **T16 godot-ws-client**: GDScript 側が本 fixture を JSON.parse_string で読み込んで
  ハンドラーを実装する。README のサンプルコードが出発点
