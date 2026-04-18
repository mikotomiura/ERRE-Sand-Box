# 重要な設計判断 — T08 test-schemas

## 判断 1: 3 層契約ガードを採用 (v1 焦点拡張を破棄)

- **判断日時**: 2026-04-18
- **背景**: Phase C 閉幕の境界タスク。「Contract 凍結の境界」の意味を
  テストに機械的責務として実装する必要
- **選択肢**:
  - A: 焦点拡張 (tests を書き増やす、meta/golden なし)
  - B: 3 層契約ガード (Layer 1 boundary / L2 meta-invariant / L3 JSON Schema golden)
- **採用**: B (v2)
- **理由**:
  - schemas.py に新 BaseModel が追加された時も `extra="forbid"` と
    `schema_version` デフォルトが自動検証される (Layer 2)
  - Pydantic 生成 JSON Schema の drift が CI で即失敗する (Layer 3)
  - 後続 T10-T14 の開発者体験が callable factory で向上
- **トレードオフ**: 実装コスト 1.4-1.6 倍、Pydantic バージョン依存
- **詳細**: `design-comparison.md`

## 判断 2: JSON Schema golden を `tests/schema_golden/` に配置

- **判断日時**: 2026-04-18
- **背景**: golden ファイルをどこに置くか — `fixtures/` と混ぜるか?
- **選択肢**:
  - A: `fixtures/schema_reference/` — fixtures/ の一部
  - B: `tests/schema_golden/` — test-scoped (CI 参照データ)
- **採用**: B
- **理由**:
  - T07 の `fixtures/` は「wire specimen (実データ例)」の意味で確立済み
  - golden は「型定義そのもの」であり、specimen とは異なる性質
  - `tests/schema_golden/` は CI が参照する規範データとして自然な位置

## 判断 3: Callable factory + convenience fixture の二層構成

- **判断日時**: 2026-04-18
- **背景**: 後続 T10-T14 のテストで `AgentState` を多彩な variant で生成する必要
- **選択肢**:
  - A: Kant 固定の convenience fixture のみ (v1)
  - B: Callable factory のみ
  - C: factory + convenience (v2)
- **採用**: C
- **理由**:
  - 簡単なテストは `agent_state_kant` fixture で 1 行
  - variant が必要なテストは `make_agent_state(tick=42, position={...})` で任意
  - deep merge により nested dict の部分更新が可能 (code-reviewer HIGH #1 対応)

## 判断 4: ルックアップテーブル方式で `make_envelope` をディスパッチ

- **判断日時**: 2026-04-18
- **背景**: `make_envelope(kind, **overrides)` の内部実装
- **選択肢**:
  - A: if-elif チェーン (PLR0911 too-many-returns を踏む)
  - B: `_ENVELOPE_BUILDERS: dict[kind → builder]` ルックアップ
- **採用**: B
- **理由**: 新 kind 追加時に builder 関数 1 個と dict エントリ 1 行で済む
- **追加の安全網**: builder 実行後に未消費 overrides が残っていれば
  `ValueError` (code-reviewer HIGH #2 対応、typo 検知)

## 判断 5: code-reviewer HIGH 2 件 + MEDIUM 5 件に対応

- **判断日時**: 2026-04-18
- **対応内容**:
  1. **`_merge` を deep merge 化** (HIGH #1): nested dict の部分更新を可能に
  2. **`make_envelope` で未消費 overrides を検知** (HIGH #2): typo 時に silent pass しない
  3. **`_union_members` に Pydantic v2.x 前提を明記** (MEDIUM #3)
  4. **`test_control_envelope_kinds_match_fixtures` に FIXTURES_DIR 存在 assert** (MEDIUM #5)
  5. **inline `_make_agent_state` の `agent_id` を `a_kant_001` に統一** (MEDIUM #6):
     conftest factory との整合性。テストは `wall_clock` を除外して完全一致で検証
  6. **NOTICE の CSDG 参照に "not bundled with wheels" を明示** (MEDIUM #7):
     配布物で存在しないパスへの参照を避ける
  7. **parametrize テーブル外の個別 sampling テストは意図的分離**
     (MEDIUM #4 部分採用): 個別 assert の方が読みやすいため現状維持、
     ただし将来の field 追加時は `_BOUNDARY_CASES` に集約する方針

## 見送り (LOW 指摘、後続タスクで対応可)

- `make_persona_spec` の `.model_dump()` 冗長化 (LOW #8): 動作に影響なし
- `Observation` count のハードコード `>= 5` (LOW #9): 現状明示の方が可読
- golden 再生成コマンドの POSIX 前提 (LOW #10): 個人開発前提では十分
- 正規化ロジックの 2 箇所重複 (LOW #11): スクリプト化は M5 以降に検討

## 関連する後続タスク

- **T10 memory-store**: conftest の `make_agent_state` を使って memory テスト
- **T11 inference-ollama-adapter**: SamplingBase + SamplingDelta 合成の boundary table 拡張
- **T12 cognition-cycle-minimal**: AgentState 状態遷移テストで conftest factory を活用
- **T14 gateway-fastapi-ws**: `make_envelope` で handshake / agent_update の実地テスト
- **schemas.py 変更時**: schema_version bump + golden 再生成 (tests/schema_golden/README.md)

## Phase C 閉幕宣言

本 PR を以て MASTER-PLAN Phase C (Contract Freeze) を完了。以降、
`src/erre_sandbox/schemas.py` の変更は以下を伴う必要がある:

1. `SCHEMA_VERSION` の bump
2. `tests/schema_golden/*.schema.json` の再生成 (README の手順に従う)
3. discriminated union に kind 追加時は `fixtures/control_envelope/` に
   対応 JSON fixture を追加 (`test_control_envelope_kinds_match_fixtures` が強制)
4. 必要に応じて下流 persona YAML (`personas/*.yaml`) の更新

これで両機 (MacBook / G-GEAR) が Phase P 並列ビルドに安心して突入できる。
