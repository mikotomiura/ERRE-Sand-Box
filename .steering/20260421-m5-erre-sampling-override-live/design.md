# 設計 — m5-erre-sampling-override-live

## 実装アプローチ

**単純な 2 段階:**

1. persona-erre Skill §ルール 2 の 8 モード × 3 パラメータ delta を Python
   の `Final Mapping[ERREModeName, SamplingDelta]` 定数としてコード化する。
2. `cycle.py::_maybe_apply_erre_fsm` の遷移時に、新 `ERREMode` の
   `sampling_overrides` に上記テーブルのエントリを渡す。

既存の 3 箇所 (`cycle.py` / `reflection.py` / `ollama_adapter.py`) の
`compose_sampling(base, agent.erre.sampling_overrides)` は無変更。
delta が 0.0 から実値に変わるだけで、clamp 付き加算ロジックはそのまま機能する。

### 設計上の選択

- **保管場所**: `erre/sampling_table.py` (architecture-rules §レイヤー表で
  `erre/ → schemas.py` のみ依存、`cognition/ → erre/` も許容)
- **定数形式**: `MappingProxyType` で包んで read-only 化 (外側 dict の
  mutation を防止)。内側の `SamplingDelta` インスタンスは Pydantic v2 が
  `ERREMode` 構築時にバリデートして新インスタンスを作るため、原本が
  変更される心配はない
- **`DEEP_WORK` の扱い**: persona-erre Skill のテーブル上はすべて 0.0。
  `SamplingDelta()` (全デフォルト) で明示的に表現
- **`GARDEN` zone** → `PERIPATETIC` mode (既存 `ZONE_TO_DEFAULT_ERRE_MODE`
  に準拠、Skill §ルール 5 では `ri_create` だが FSM 側で peripatetic に
  折り返している)。本タスクは mode → delta のみ扱うので影響なし
- **テーブル値の source of truth**: persona-erre Skill SKILL.md §ルール 2。
  `sampling_table.py` の docstring に対応表 + skill へのリンクを明記し、
  今後の drift を防止

## 変更対象

### 新規作成するファイル

- `src/erre_sandbox/erre/sampling_table.py` — 8 モードの `SamplingDelta`
  定数マップ `SAMPLING_DELTA_BY_MODE`
- `tests/test_erre/test_sampling_table.py` — 値一致・clamp 境界・immutability

### 修正するファイル

- `src/erre_sandbox/erre/__init__.py` — `SAMPLING_DELTA_BY_MODE` を re-export
- `src/erre_sandbox/cognition/cycle.py` — FSM hook (L377 付近) で
  `sampling_overrides=SAMPLING_DELTA_BY_MODE[candidate]` を渡す + import 追加
- `tests/test_cognition/test_cycle_erre_fsm.py` — FSM 遷移時に
  `sampling_overrides` がテーブル値と一致することを追加テスト

### 削除するファイル

なし

## 影響範囲

### コード

- `cognition/cycle.py` の FSM hook 1 行 + import 1 行
- `erre/__init__.py` の export 1 行
- 既存 `compose_sampling` 呼び出し 3 箇所は完全に無変更

### 挙動

- **FSM 有効時**: モード遷移が実際にサンプリング温度等を変える (期待通り)
- **FSM 無効時 (デフォルト `erre_policy=None`)**: 変更なし、`AgentState`
  初期化時の `sampling_overrides=SamplingDelta()` (全 0.0) のまま
  (M4 互換)
- **reflection 経路**: `reflection.py` も同じ `agent.erre.sampling_overrides`
  を参照するため、FSM 遷移後は reflection にも delta が反映される (設計上
  想定される副作用、回帰テストで確認)

### DB / スキーマ / wire

すべて無変更。`SamplingDelta` スキーマ定義は M5 contracts freeze (PR #56) で
固定済、本タスクは同スキーマのインスタンス値を変えるだけ。

## 既存パターンとの整合性

- **定数マップ形式**: `erre/fsm.py` の
  `ZONE_TO_DEFAULT_ERRE_MODE: Final[Mapping[Zone, ERREModeName]]` と
  同じ pattern (Final + Mapping + module-level constant)
- **`MappingProxyType` 使用**: `erre/fsm.py` では plain dict だが、本定数は
  外部公開される唯一の真実なので proxy で read-only 化。他の
  module-level Pydantic インスタンス群 (`integration/metrics.py` の
  `_INITIAL_METRICS` 等) と同じく immutable に寄せる方針
- **テストファイル配置**: `tests/test_erre/` 既存 (`test_fsm.py`) に
  兄弟として `test_sampling_table.py` を追加、`src` ミラー構造に沿う
- **FSM hook 拡張**: `cycle.py::_maybe_apply_erre_fsm` の `candidate is None
  or candidate == agent_state.erre.name` guard を残し、遷移成立時のみ
  新 ERREMode を構築する既存ロジックに 1 kwarg 足すのみ
- **compose_sampling**: `inference/sampling.py` の clamp 付き加算ロジックは
  そのまま活用、delta の field range (-1.0..1.0) とも整合

## テスト戦略

### 単体テスト (`tests/test_erre/test_sampling_table.py`)

- `test_all_eight_modes_present`: 全 `ERREModeName` メンバがキーとして存在
- `test_delta_values_match_skill_table`:
  - `PERIPATETIC = (+0.3, +0.05, -0.1)`
  - `CHASHITSU = (-0.2, -0.05, +0.1)`
  - `ZAZEN = (-0.3, -0.1, 0.0)`
  - `SHU_KATA = (-0.2, -0.05, +0.2)`
  - `HA_DEVIATE = (+0.1, +0.05, -0.1)`
  - `RI_CREATE = (+0.2, +0.1, -0.2)`
  - `DEEP_WORK = (0.0, 0.0, 0.0)`
  - `SHALLOW = (-0.1, -0.05, 0.0)`
- `test_deep_work_is_zero_delta`: 上記のサブセットを明示的に
- `test_compose_clamp_does_not_violate_ranges_for_any_mode`:
  base が `SamplingBase.temperature=2.0, top_p=1.0, repeat_penalty=2.0`
  および `0.0 / 0.01 / 0.5` でも、compose 結果が `ResolvedSampling` の
  range 内に収まること (parametrize で 8 modes × 2 extreme bases)
- `test_mapping_is_read_only`: `SAMPLING_DELTA_BY_MODE[PERIPATETIC] = ...`
  が `TypeError` を投げる (`MappingProxyType`)
- `test_each_delta_satisfies_field_constraints`: 各 delta の全フィールドが
  `SamplingDelta` の declared range (-1.0..1.0) 内

### 統合テスト (`tests/test_cognition/test_cycle_erre_fsm.py` に追加)

- `test_cycle_erre_policy_populates_sampling_overrides_from_table`:
  FSM が `CHASHITSU` を返したとき
  `result.agent_state.erre.sampling_overrides` が
  `SAMPLING_DELTA_BY_MODE[CHASHITSU]` と等しい (同値比較)
  - 同時に、pre-transition の `agent.erre.sampling_overrides == SamplingDelta()`
    (default) から変化していることを確認
- 既存 `test_cycle_erre_policy_returning_current_is_treated_as_noop` は
  `sampling_overrides` 不変のまま (no-op path) を確認するため、アサーションに
  `result.agent_state.erre.sampling_overrides == agent.erre.sampling_overrides`
  を追加

### 回帰

- `uv run pytest -q` で 既存 549 + 新規 ~7 tests が PASS
- 新規テストは決定論的 (LLM mock、外部 I/O なし)

### TDD 適用

- `test_sampling_table.py` → Red → `sampling_table.py` 実装 → Green
- `test_cycle_erre_fsm.py` の追加 test → Red → `cycle.py` wire → Green

## ロールバック計画

段階的な revert が可能:

1. **軽度の問題 (サンプリング値が不適切)**: `sampling_table.py` の定数のみ
   修正、スキーマ / 配線は無変更
2. **挙動的な問題 (FSM 遷移でテスト失敗)**: `cycle.py` の kwarg 追加行のみ
   revert すれば M5 world-zone-triggers 完了時点 (PR #58) の挙動に戻る
3. **feature flag 不要**: 新テーブル値はすべて `SamplingDelta` の field range
   内、`compose_sampling` の clamp が安全ネット
4. **緊急時**: `git revert <commit>` で PR 単位で戻せる、他 sub-task と
   衝突なし
