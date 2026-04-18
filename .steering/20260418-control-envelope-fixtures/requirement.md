# T07 control-envelope-fixtures

## 背景

T05 で `ControlEnvelope` が 7 種の discriminated union (handshake /
agent_update / speech / move / animation / world_tick / error) として凍結された。
G-GEAR (Python) が送信し、MacBook の Godot (GDScript) が受信するため、
両言語から読める JSON fixture が必要。fixture は:
1. **Contract specimen**: wire 形式のリファレンスデータ
2. **Regression test data**: 将来スキーマ変更時のドリフト検知
3. **Godot developer reference**: GDScript 側の受信/パース実装の参考

また `.claude/skills/godot-gdscript/SKILL.md` に古い kind 値
(`agent_state`, `agent_move`, `speech_bubble`, `mode_change`) が残っており、
T05 schemas.py と乖離している。T06 で persona-erre Skill を同期した
のと同じ理由で、本タスクで godot-gdscript Skill も同期修正する。

## ゴール

- 全 7 種の `ControlEnvelope` kind に対し realistic な JSON fixture を作成
- Python 側の pytest で `TypeAdapter(ControlEnvelope)` による validate + round-trip を検証
- Godot developer が Python 依存なしで読める形式 + 場所 + README
- `.claude/skills/godot-gdscript/SKILL.md` の `kind` 値を T05 schemas.py と一致させる

## スコープ

### 含むもの
- `fixtures/control_envelope/` 配下に 7 種の JSON fixture
- `fixtures/control_envelope/README.md` (Godot 開発者向け)
- `tests/test_envelope_fixtures.py` で:
  - 全ファイルの `TypeAdapter(ControlEnvelope)` validate
  - ファイル名と `kind` の整合
  - 7 kind 全てが揃っている
  - round-trip (JSON → Pydantic → JSON) で欠損なし
  - `schema_version` が `SCHEMA_VERSION` と一致
- `.claude/skills/godot-gdscript/SKILL.md` の `kind` 表記を T05 と一致に修正
- `AgentUpdateMsg` fixture 内の `agent_state.persona_id` は `"kant"` を使用
  (T06 Kant persona との整合。AgentState そのものは PersonaSpec 非依存だが
  persona_id は参照)

### 含まないもの
- WebSocket 送受信の実コード (T14 gateway-fastapi-ws の責務)
- Godot 側 GDScript 実装 (T16 godot-ws-client の責務)
- セッションリプレイ (ordered message stream) の統合テスト (M2 E2E 時)
- `Observation` / `MemoryEntry` の fixture (契約の核は ControlEnvelope、他は不要)
- fixture 自動生成スクリプト (M5 以降に検討)

## 受け入れ条件

- [ ] `fixtures/control_envelope/` 配下に 7 つの `*.json` ファイル
  (handshake / agent_update / speech / move / animation / world_tick / error)
- [ ] 全ファイルが `json.loads` でパース可能
- [ ] 全ファイルが `TypeAdapter(ControlEnvelope).validate_python(...)` を通過
- [ ] round-trip: `dump → load → dump` の結果が初期 dump と意味的に一致
- [ ] `schema_version == SCHEMA_VERSION`
- [ ] ファイル名 (`speech.json`) と `kind` (`"speech"`) が一致
- [ ] `fixtures/control_envelope/README.md` で Godot 開発者に対する使い方を説明
- [ ] `.claude/skills/godot-gdscript/SKILL.md` の `kind` リスト (agent_state/agent_move/speech_bubble/mode_change) を T05 schemas.py と一致 (agent_update/move/speech/… + handshake/animation/world_tick/error) に修正
- [ ] `uv run pytest` 全パス (既存 + 新テスト)
- [ ] `uv run ruff check tests/` 警告ゼロ
- [ ] `uv run mypy tests/` strict でパス
- [ ] Conventional Commits でコミット & PR 作成

## 関連ドキュメント

- `src/erre_sandbox/schemas.py` §7 (ControlEnvelope + 7 メンバ)
- `src/erre_sandbox/schemas.py` §4 (AgentState — AgentUpdateMsg の payload 用)
- `.claude/skills/test-standards/SKILL.md`
- `.claude/skills/godot-gdscript/SKILL.md`
- `docs/architecture.md` (WebSocket 通信)
- `docs/glossary.md` (ControlEnvelope, kind)
- `.steering/20260418-schemas-freeze/design.md` (§7 ControlEnvelope 設計)
- `personas/kant.yaml` (persona_id="kant" 参照)

## 運用メモ

- 破壊と構築（/reimagine）適用: **Yes**
- 理由: fixture の「配置場所・粒度・content 深さ・documentation 戦略」は
  複数の選び方があり設計判断が入る。後続 T14 gateway / T16 godot-ws-client の
  開発者体験に直接影響するため、確証バイアス排除の価値が高い。
- タスク種別: その他 (契約 fixture 整備 + Skill 同期修正)。
- 使用するサブエージェント・コマンド:
  - /start-task, /reimagine
  - file-finder — 既存 fixtures / JSON 関連参照の調査
  - code-reviewer — fixture 内容 + テスト + Skill 修正のレビュー
