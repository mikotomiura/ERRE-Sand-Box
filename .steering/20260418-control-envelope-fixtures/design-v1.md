# 設計 — T07 control-envelope-fixtures (初回案 v1)

## 実装アプローチ

**「pytest 中心のテスト fixture」** として設計する。pytest 慣習に従い
`tests/fixtures/control_envelope/` 配下に 7 種の JSON を配置し、
`tests/test_envelope_fixtures.py` が glob で読み込んで
`TypeAdapter(ControlEnvelope)` で validate + round-trip を検証する。

方針の要点:
1. 配置: pytest のコンベンション `tests/fixtures/` 配下
2. 命名: `{kind}.json` 形式 (7 ファイル)
3. 生成法: 手書き。`test_schemas.py` のインライン辞書を JSON 化した保守的な値
4. 内容: 最小限の validator 通過内容。リアリズムより schema 準拠優先
5. Godot 側は相対パスで `tests/fixtures/control_envelope/*.json` を直接参照
6. テスト: validate + filename-kind 一致 + round-trip + schema_version

## 変更対象

### 修正するファイル
- `.claude/skills/godot-gdscript/SKILL.md` — 古い `kind` 値を T05 と一致させる

### 新規作成するファイル
- `tests/fixtures/control_envelope/handshake.json`
- `tests/fixtures/control_envelope/agent_update.json`
- `tests/fixtures/control_envelope/speech.json`
- `tests/fixtures/control_envelope/move.json`
- `tests/fixtures/control_envelope/animation.json`
- `tests/fixtures/control_envelope/world_tick.json`
- `tests/fixtures/control_envelope/error.json`
- `tests/test_envelope_fixtures.py`

## 各 fixture の内容 (v1 — minimal)

- minimal-validator-passing な値のみ
- `agent_update.json` に `agent_state` を丸ごと埋める (~40 行)
- その他は 10 行以下

## テスト戦略 (tests/test_envelope_fixtures.py)

```python
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "control_envelope"
ALL_KINDS = {"handshake", "agent_update", "speech", "move",
             "animation", "world_tick", "error"}

def test_all_kinds_have_fixture() -> None:
    filenames = {p.stem for p in FIXTURES_DIR.glob("*.json")}
    assert filenames == ALL_KINDS

def test_fixture_filename_matches_kind(): ...
def test_fixture_validates_as_control_envelope(): ...
def test_fixture_round_trip_stable(): ...
def test_fixture_schema_version_matches(): ...
```

## godot-gdscript Skill 修正

SKILL.md ルール 3 の誤った kind 値:
- `"agent_state"` → `"agent_update"`
- `"agent_move"` → `"move"`
- `"speech_bubble"` → `"speech"`
- `"mode_change"` → 削除 (ERRE モードは Observation.event_type="erre_mode_shift" で表現)
- 追加: `handshake`, `animation`, `world_tick`, `error`

## 既存パターンとの整合性

- repository-structure.md §1 は `tests/` を `src/` ミラーと規定。
  `tests/fixtures/` は src 対応なし独立 dir として許容
- test-standards: pytest + TypeAdapter で validate
- python-standards: テスト側は型ヒント完備 + f-string
- architecture-rules: fixture は schema.py 以外の src 依存なし

## ロールバック計画

- 新規 JSON + Python テスト + Skill テキスト編集のみ。git revert で戻せる

## v1 の自覚している懸念点

| 懸念 | 内容 |
|---|---|
| Godot developer には見えにくい | `tests/fixtures/` は「テスト用データ」の位置づけ。Godot 開発者が「contract specimen」として参照する文脈が弱い |
| README なし | Godot 側の「これは wire format のリファレンス」導線がない |
| Realism 不足 | minimal な値しかなく、Godot UI レンダリング検証に弱い |
| Scenario 欠如 | 各 fixture が独立。「エージェントが peripatos に入って歩き始め発話」のような時系列を示せない |
| AgentState が冗長 | agent_update.json に AgentState 全体を埋めて 40+ 行。他は 10 行以下で不均衡 |
| 拡張性 | 後続の Observation / MemoryEntry fixture の位置が不明 |

これらを引きずらず、`/reimagine` でゼロから再設計し比較する。
