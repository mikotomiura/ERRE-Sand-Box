# 設計 — T07 control-envelope-fixtures (再生成案 v2)

## 実装アプローチ

`fixtures/control_envelope/` を **「first-class な契約リポジトリ」** として設計する。
pytest のサブフォルダ扱いではなく、`personas/` と並ぶ top-level のドメイン資産に
格上げし、Python 側テスト・Godot 側実装・将来のドキュメント生成の 3 者が
対等にアクセスできる場所にする。
v2 の核心は 4 点:

1. **Top-level location** — `fixtures/control_envelope/` に配置する。
   `personas/` と同様、言語中立で 1 プロジェクト資産としての地位を与える
2. **Coherent scenario content** — 7 つの fixture は "Kant agent が peripatos に
   入り、歩行しつつ Kantian fragment を発話し、world tick が進む" という
   一貫シナリオのスナップショット群として記述する。
   values は realistic (kant / peripatos / tick 42 / 実際のドイツ語引用)
3. **Godot-first README** — `fixtures/control_envelope/README.md` で
   ファイルの目的・GDScript 側の受信パターン・Python 側の validate パターン・
   schema_version bump 時の更新規則を解説
4. **Parametrized pytest** — 1 ファイル 1 テスト ID で可視化し、
   どの fixture が壊れたか一目でわかる出力にする

## 変更対象

### 修正するファイル
- `.claude/skills/godot-gdscript/SKILL.md` — 古い `kind` 値 4 件を
  実際の 7 kind と一致させ、fixture リポジトリへのリンクを追加

### 新規作成するファイル
- `fixtures/control_envelope/README.md` — Godot-first ガイド
- `fixtures/control_envelope/handshake.json`
- `fixtures/control_envelope/agent_update.json`
- `fixtures/control_envelope/speech.json`
- `fixtures/control_envelope/move.json`
- `fixtures/control_envelope/animation.json`
- `fixtures/control_envelope/world_tick.json`
- `fixtures/control_envelope/error.json`
- `tests/test_envelope_fixtures.py`

### 削除するファイル
- なし

## Coherent scenario の設計

全 fixture は以下のひとつのシーンの異なる瞬間を表す:

> 2026-04-18T12:00:00Z、tick=42。エージェント `a_kant_001` (persona_id=`kant`)
> は書斎 (study) から peripatos に入り、Linden-Allee を歩いている。
> DMN 活性化が起き、`peripatetic` ERRE モードに遷移済 (entered_at_tick=40)。
> walk アニメーションが loop 再生中。発話として "Der bestirnte Himmel über
> mir..." の断片を口にする。world_tick は同時刻。error はハンドシェイク後の
> 演示として unknown_kind を例示。

この物語的一貫性により:
- Godot 開発者が JSON を並べて読むと 1 シーンが立ち上がる
- 実運用時の実データに最も近い「リハーサル用意」となる
- 整合性 (同一 tick, 同一 agent_id, 同一 wall_clock) がテストで検証できる

### 各 fixture の役割

| ファイル | 役割 | realism の軸 |
|---|---|---|
| handshake.json | 接続確立時の最初の交換 | `peer: "g-gear"`、7 kind の capabilities |
| agent_update.json | Kant の 1-tick スナップショット | 全サブモデル (Physical / Cognitive / ERREMode) が Kant の伝記に整合 |
| speech.json | Kant の典型的発話 | 実際のドイツ語 (Kritik praktischen Vernunft の結語断片) |
| move.json | peripatos 内の locomotion 意図 | target position が Linden-Allee 方向 |
| animation.json | walk アニメ loop=true | agent_id と loop フラグ |
| world_tick.json | 同時刻のハートビート | active_agents=1 |
| error.json | observability 用の例示 | code と detail が説明的 |

## README.md の構成 (Godot-first)

```markdown
# ControlEnvelope JSON fixtures

## このディレクトリの目的

ERRE-Sandbox の wire contract (`ControlEnvelope`) の正式な仕様例示。
Python 側 (G-GEAR) が送信し、Godot 側 (MacBook) が受信する全 7 種の
メッセージ形式を、realistic な値で具体化した specimen 群。

## 構造

各ファイルは `kind` 識別子ごとに 1 対 1 対応:

- handshake.json — 接続確立時の schema negotiation
- agent_update.json — エージェント 1 体の全状態スナップショット
- speech.json — 発話テキスト
- move.json — locomotion 意図
- animation.json — アニメーション指令
- world_tick.json — 全体時計のハートビート
- error.json — 構造化エラー

## GDScript 側の消費例

...JSON.parse_string + match kind のサンプル (godot-gdscript Skill 参照)

## Python 側の消費例

...TypeAdapter(ControlEnvelope).validate_json() のサンプル

## 更新ルール

schema_version が bump されたら全 fixture を再生成すること。
`tests/test_envelope_fixtures.py` が schema mismatch を CI で検出する。

## 正式な型定義

`src/erre_sandbox/schemas.py` §7 が唯一の真実。
このディレクトリは specimen であり、矛盾する場合は schemas.py が勝つ。
```

## テスト戦略 (tests/test_envelope_fixtures.py)

```python
FIXTURES_DIR = REPO_ROOT / "fixtures" / "control_envelope"
ALL_KINDS = frozenset({"handshake", "agent_update", "speech", "move",
                       "animation", "world_tick", "error"})

def _fixture_paths() -> list[Path]:
    return sorted(FIXTURES_DIR.glob("*.json"))

def test_all_seven_kinds_have_fixture() -> None:
    stems = {p.stem for p in _fixture_paths()}
    assert stems == ALL_KINDS, f"missing kinds: {ALL_KINDS - stems}"

@pytest.mark.parametrize("fixture_path", _fixture_paths(), ids=lambda p: p.stem)
def test_fixture_validates_and_kind_matches_filename(
    fixture_path: Path,
) -> None:
    raw_text = fixture_path.read_text(encoding="utf-8")
    data = json.loads(raw_text)
    envelope = TypeAdapter(ControlEnvelope).validate_python(data)
    assert envelope.kind == fixture_path.stem

@pytest.mark.parametrize("fixture_path", _fixture_paths(), ids=lambda p: p.stem)
def test_fixture_round_trip_semantically_stable(fixture_path: Path) -> None:
    adapter = TypeAdapter(ControlEnvelope)
    original = adapter.validate_python(json.loads(fixture_path.read_text()))
    re_serialized = adapter.dump_python(original, mode="json")
    re_loaded = adapter.validate_python(re_serialized)
    assert re_loaded == original

@pytest.mark.parametrize("fixture_path", _fixture_paths(), ids=lambda p: p.stem)
def test_fixture_schema_version_matches(fixture_path: Path) -> None:
    data = json.loads(fixture_path.read_text())
    assert data["schema_version"] == SCHEMA_VERSION

def test_agent_update_refers_to_kant_persona() -> None:
    data = json.loads((FIXTURES_DIR / "agent_update.json").read_text())
    assert data["agent_state"]["persona_id"] == "kant"
```

## godot-gdscript Skill 修正

ルール 3 "ControlEnvelope の処理" のサンプルコードで:
- `"agent_state"` → `"agent_update"`
- `"agent_move"` → `"move"`
- `"speech_bubble"` → `"speech"`
- `"mode_change"` → 削除 (ERRE モード遷移は `Observation.event_type="erre_mode_shift"`
  であり、ControlEnvelope.kind には存在しない)
- 追加: `"handshake"`, `"animation"`, `"world_tick"`, `"error"`

さらに末尾に以下の注記を追加:

> **wire fixture の参照先**: `fixtures/control_envelope/*.json` に各 kind の
> realistic な JSON specimen がある。GDScript 実装前に読むこと。

## 既存パターンとの整合性

- **`personas/` との並列性**: top-level `fixtures/` は `personas/` と同じく
  "言語中立なドメイン資産" の位置に置かれる (repository-structure.md §2 に
  沿い、新 top-level dir 追加を記録する)
- **test-standards**: pytest.mark.parametrize で ID 可視化。型ヒント完備
- **python-standards**: テスト側 `from __future__ import annotations`, f-string
- **architecture-rules**: fixture は schemas.py のみに依存 (schemas 以外の
  src import なし)
- **repository-structure.md §6 禁止パターン**: "src の外にビジネスロジックを
  置く" に抵触しない (fixture は データ・specimen であり logic ではない)

## ロールバック計画

- 新規 7 JSON + 1 README + 1 Python test + 1 Skill 編集 + 1 pyproject 変更 (後述)。
  いずれも単独で git revert 可能。

## pyproject.toml への追加 (lean)

ruff 側でデフォルト excludes に `docs/_pdf_derived` / `godot_project` が既にある。
`fixtures/` は Python ファイルを含まないため exclude 不要。

## 懸念とその対処

| 懸念 | 対処 |
|---|---|
| top-level `fixtures/` 追加が repository-structure.md に未記載 | 本 PR で repository-structure.md §1 のツリー図に追記、§2 の責務表に「`fixtures/` — 契約 specimen (wire contract)」を 1 行追加 |
| agent_update.json が 40+ 行 で他の 5-15 行と長さ不均衡 | 仕様上 AgentState 全体を内包するため不可避。README で「長いのは本質的」と説明 |
| README が Godot サンプルを含むが GDScript 実装は未存在 | サンプルは擬似コードであり、 T16 godot-ws-client 着手時の参考として機能する (contract-first の精神) |
| `fixtures/control_envelope/` を将来 `fixtures/observation/` や `fixtures/memory/` に拡張するか | 本 PR ではスコープ外。将来追加時に `fixtures/` の階層を `{domain}/` で割る現方針を踏襲すればよい |
| schema_version bump 時の fixture 一括更新 | `test_fixture_schema_version_matches` が CI で落ちるため検知可能。修正スクリプトは M5 以降 |
| realistic speech に Kant の実文を使うと著作権? | Kant は 18 世紀で public domain。Kuehn 2001 は Cambridge UP 著作物のため本文引用は避け、Kant 原典の German 断片 (Kritik praktischen Vernunft 結語) のみ使用 |

## 設計判断の履歴

- 初回案（design-v1.md）と再生成案（v2）を `design-comparison.md` で比較
- 採用: **v2（再生成案）**
- 根拠: requirement.md §背景・§スコープが明示的に `fixtures/control_envelope/`
  + README を要求。T06 で確立した「top-level ドメイン資産」方針 (`personas/`)
  との一貫性を維持し、Contract-First 精神を Godot 側へも浸透させる。
  realistic coherent scenario (Kant が peripatos を歩行する 1 シーン) により
  T16 godot-ws-client 着手時の実体験を提供できる。ハイブリッドは中途半端に
  なるため不採用。
