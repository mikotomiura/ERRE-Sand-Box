# 設計 — T08 test-schemas (再生成案 v2)

## 実装アプローチ

T08 は Contract Freeze の **正式な閉幕儀式**。単なるテスト拡張ではなく、
「新しい BaseModel が schemas.py に追加されても契約ルールが自動強制される」
「JSON Schema のドリフトが CI で検知される」「fixture の変異が衝突しない」を
機械的に保証する、3 層の契約ガードを構築する。

v2 の核心 3 点:

1. **3 層の契約ガードを構築する** — テストを (a) 単体 boundary、
   (b) 契約 meta-invariant、(c) JSON Schema drift という 3 つの責務に分け、
   ファイルも分ける。各層は schemas.py に未来の field が加わっても
   「人力による追記なし」で動くよう introspection ベースで書く
2. **Callable factory + 便利 fixture の二層構成** — 後続 T10-T14 が
   「variant を指定して任意の AgentState を作る」用途 (factory) と
   「とりあえず Kant で動かす」用途 (convenience) の両方を薄いコードで得られる
3. **JSON Schema golden を `tests/schema_golden/` に配置** — T07 の
   `fixtures/control_envelope/` (wire specimen) との役割混同を避け、
   CI 参照データとして tests 配下に置く。AgentState / PersonaSpec /
   ControlEnvelope の 3 枚

## 変更対象

### 修正するファイル
- `tests/conftest.py` — factory + convenience fixture を追加 (空 → ~60 行)
- `tests/test_schemas.py` — 境界値・union negative・round-trip を追記 (+~15 test)
- `NOTICE` — CSDG 帰属追記
- `.steering/20260418-implementation-plan/tasklist.md` — T08 チェック

### 新規作成するファイル
- `tests/test_schema_contract.py` — 3 層の契約ガード第 2-3 層 (meta + golden)
- `tests/schema_golden/agent_state.schema.json` — JSON Schema 参照データ
- `tests/schema_golden/persona_spec.schema.json` — 同上
- `tests/schema_golden/control_envelope.schema.json` — 同上
- `tests/schema_golden/README.md` — 再生成手順を明記

### 削除するファイル
- なし

## 3 層契約ガードの構造

### Layer 1: 単体 boundary (tests/test_schemas.py に追記)

境界値テストを (field_path, valid, invalid_below, invalid_above) の
parametrize テーブルで駆動。

```python
BOUNDARY_CASES = [
    ("Physical.sleep_quality", {"sleep_quality": 0.0}, {"sleep_quality": -0.01}, {"sleep_quality": 1.01}),
    ("Physical.mood_baseline", {"mood_baseline": -1.0}, {"mood_baseline": -1.01}, {"mood_baseline": 1.01}),
    ("SamplingBase.temperature", ..., ..., {"temperature": 2.01}),
    ("SamplingBase.repeat_penalty", ..., {"repeat_penalty": 0.49}, {"repeat_penalty": 2.01}),
    ("SamplingDelta.temperature", ..., {"temperature": -1.01}, {"temperature": 1.01}),
    # ... RelationshipBond / ERREMode.entered_at_tick (ge=0) 等
]
```

- **Observation** 全 5 event_type を validate dispatch
- **Discriminated union negative**: ControlEnvelope で未知 kind / missing kind / 不整合 payload
- **Round-trip**: AgentState / PersonaSpec / ControlEnvelope を `model_dump_json` → `model_validate_json` で同一性確認

### Layer 2: Meta-invariant (tests/test_schema_contract.py 新設)

schemas.py の `__all__` を introspection し、以下を全 BaseModel 派生に
一斉適用する meta-tests:

```python
from erre_sandbox import schemas
from pydantic import BaseModel

def _public_models() -> list[type[BaseModel]]:
    return [
        getattr(schemas, name)
        for name in schemas.__all__
        if isinstance(getattr(schemas, name, None), type)
        and issubclass(getattr(schemas, name), BaseModel)
    ]

@pytest.mark.parametrize("model_cls", _public_models(), ids=lambda c: c.__name__)
def test_public_model_forbids_extra(model_cls: type[BaseModel]) -> None:
    assert model_cls.model_config.get("extra") == "forbid"

@pytest.mark.parametrize("model_cls", _public_models(), ids=lambda c: c.__name__)
def test_schema_version_field_default_matches_constant(
    model_cls: type[BaseModel],
) -> None:
    if "schema_version" not in model_cls.model_fields:
        pytest.skip("model has no schema_version field")
    assert model_cls.model_fields["schema_version"].default == schemas.SCHEMA_VERSION
```

他の meta-tests:
- ControlEnvelope union メンバの `kind` Literal 値が `fixtures/control_envelope/*.json` の stem と一致
- Observation union メンバの `event_type` Literal 値が網羅されている
- 全 StrEnum の値が lower_snake_case (design.md で合意した命名規約)

### Layer 3: JSON Schema golden (tests/test_schema_contract.py に追記)

`tests/schema_golden/*.schema.json` を golden として、生成 JSON Schema を
正規化 (`json.dumps(sort_keys=True, indent=2)`) した上で文字列比較。

```python
@pytest.mark.parametrize("type_name,target", [
    ("agent_state", AgentState),
    ("persona_spec", PersonaSpec),
    ("control_envelope", ControlEnvelope),
])
def test_json_schema_matches_golden(type_name: str, target: Any) -> None:
    adapter = TypeAdapter(target)
    current = json.dumps(adapter.json_schema(), sort_keys=True, indent=2)
    golden_path = SCHEMA_GOLDEN_DIR / f"{type_name}.schema.json"
    golden = golden_path.read_text(encoding="utf-8")
    assert current == golden, (
        f"JSON Schema drift detected for {type_name}. "
        f"Regenerate with: python scripts/regenerate_schema_golden.py "
        f"(or overwrite manually)."
    )
```

Golden の再生成は README.md に明記し、今回は手動手順を記述 (スクリプト化は
優先度低)。

## conftest.py の factory 設計

```python
from collections.abc import Callable
from typing import Any

from erre_sandbox.schemas import (
    AgentState, ControlEnvelope, ERREMode, ERREModeName, HandshakeMsg,
    PersonaSpec, Position, Zone,
)
from pydantic import TypeAdapter

MakeAgentState = Callable[..., AgentState]


@pytest.fixture
def make_agent_state() -> MakeAgentState:
    """Callable factory; overrides are deep-merged into base state."""
    def _factory(**overrides: Any) -> AgentState:
        base = {
            "agent_id": "a_kant_001",
            "persona_id": "kant",
            "tick": 0,
            "position": {"x": 0.0, "y": 0.0, "z": 0.0, "zone": "study"},
            "erre": {"name": "deep_work", "entered_at_tick": 0},
        }
        base.update(overrides)
        return AgentState.model_validate(base)
    return _factory


@pytest.fixture
def agent_state_kant(make_agent_state: MakeAgentState) -> AgentState:
    """Convenience: Kant in study, deep_work mode, tick 0."""
    return make_agent_state()


@pytest.fixture
def make_envelope() -> Callable[..., ControlEnvelope]:
    """Generate any ControlEnvelope member by kind."""
    ...
```

`make_envelope` は kind 引数を受け取って per-kind factory にディスパッチ。

## NOTICE への CSDG 帰属追記

既存形式に従い、末尾に追加:

```
--- Prior-work references (not bundled) ---

This project was informed by the design of CSDG (Cognitive State Diary
Generator) by mikotomiura, MIT-licensed at
https://github.com/mikotomiura/cognitive-state-diary-generator. The
structure of HumanCondition, CharacterState, and DailyEvent in CSDG
inspired the Physical, Cognitive, and PerceptionEvent schemas in this
project; no code is reused verbatim. See
.steering/20260418-schemas-freeze/decisions.md for details.
```

## 既存パターンとの整合性

- **test-standards ルール 1**: schemas.py → test_schemas.py + test_schema_contract.py は 1 つのソースに対する 2 テストファイル (role split は許容範囲)
- **test-standards ルール 3**: conftest.py に factory を集約
- **python-standards**: 型ヒント / f-string / `from __future__ import annotations`
- **repository-structure**: `tests/schema_golden/` は既存 `tests/` 直下の新サブディレクトリ (テスト専用 CI データ)

## テスト戦略

- **Layer 1** (boundary + round-trip): ~15 件 parametrize、既存 test_schemas.py に追加
- **Layer 2** (meta-invariant): public model 数分 × 2-3 assertion = ~15 件 parametrize
- **Layer 3** (JSON Schema golden): 3 件 parametrize
- 合計テスト数は現状 43 → ~75 件

### CI drift failure の教育性

golden mismatch 時のエラーメッセージに「再生成手順」を埋め込むことで、
新しい開発者でも self-service で fix できる。

## ロールバック計画

- テスト・conftest・NOTICE・schema_golden 追加のみで schemas.py 本体は不変
- 問題があれば `git revert` で単独復元

## 懸念とその対処

| 懸念 | 対処 |
|---|---|
| Pydantic バージョン差で JSON Schema 出力が変わる | `pyproject.toml` で pydantic `>=2.7,<3` pin 済み。変更時は golden を再生成する責務を README に明記 |
| `pyproject.toml filterwarnings=["error", ...]` で新 test が警告を出す | Pydantic の deprecation が出たら ignore を pinpoint 追加。発生しなければ現状維持 |
| meta-test で private model `_EnvelopeBase` / `_ObservationBase` が除外される | `__all__` に基づくためそもそも含まれない。それらは派生モデルが持つ `model_config` を継承するため、派生モデル側でチェックされる |
| golden のメンテナンスコスト | schemas.py 変更時は必ず schema_version bump + golden 再生成という運用で相殺。README に明記 |
| StrEnum 命名規約のテスト | `lower_snake_case` は ZAZEN 等で大文字定数を持つが value は lower_snake_case。value 側を assert する |
| `make_envelope` のシグネチャ肥大 | `kind: str` で受けて内部 dispatch。余剰引数は **overrides で許容する wrapper |
| 非 BaseModel の `__all__` メンバ (`SCHEMA_VERSION`, enum 等) が introspection で型ヒット | `isinstance(attr, type) and issubclass(attr, BaseModel)` でフィルタ |

## 設計判断の履歴

- 初回案（design-v1.md）と再生成案（v2）を `design-comparison.md` で比較
- 採用: **v2（再生成案）**
- 根拠: requirement.md §ゴールの「Phase C 閉幕 (以降は schema_version
  bump 必要) を宣言可能な状態」への機械的応答には 3 層契約ガードが必須。
  meta-test による未来証明と JSON Schema golden による drift 検知は、
  v1 の焦点拡張型では得られない。後続 T10-T14 の DX 向上のため callable
  factory も採用。ハイブリッドは 3 層のどれを採用するかが曖昧になり不採用。
