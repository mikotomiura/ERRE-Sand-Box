# 設計: M6-A-2b 繰越 backend 項目

## 実装順序 (依存関係)

1. **`_observation_content_for_embed` を 4 新型対応** — 以降 Step 1 (embed/Episodic 書き込み) が defective でなくなる。最小変更、ruff のみで済む
2. **`importance.py` / `state.py` default handling** — 4 新型の base impact / importance を定義。pure functions、test 容易
3. **Proximity firing (`world/tick.py`)** — runtime 状態 (pair distance prev) を保持し `_on_physics_tick` 末尾で evaluate
4. **Stress BiorhythmEvent (`cognition/cycle.py` Step 8)** — `CycleResult.follow_up_observations` フィールド新設。`WorldRuntime._consume_result` で `rt.pending` に追加
5. **Prompt window 5→10 + per-type limit (`cognition/prompting.py`)** — `build_user_prompt(recent_limit: int = 10)` + Proximity は最新 2 件に clamp

## 変更対象

| ファイル | 変更内容 |
|---|---|
| `src/erre_sandbox/cognition/cycle.py` | `_observation_content_for_embed()` に 4 新型分岐を追加。`CycleResult` に `follow_up_observations: list[Observation]` を追加。Step 8 後に `_detect_stress_crossing()` を呼び、結果を `follow_up_observations` に格納 |
| `src/erre_sandbox/cognition/state.py` | `_PHYSICAL_EVENT_IMPACT` に 4 新型のキーを追加 (biorhythm=0.0 / 他は微小正値) |
| `src/erre_sandbox/cognition/importance.py` | `_BASE_IMPORTANCE` に 4 新型のキーを追加 |
| `src/erre_sandbox/cognition/prompting.py` | `build_user_prompt` の `recent_limit` default を 5→10 に。Proximity 系を tail から最新 2 件に clamp するヘルパーを追加 |
| `src/erre_sandbox/world/tick.py` | `AgentRuntime` に prev-pair distance cache は置かず runtime 全体の `dict[frozenset[str], float]` を持つ。`_fire_proximity_events()` を `_on_physics_tick` 末尾に追加。`_consume_result` で `CycleResult.follow_up_observations` を `rt.pending` に追加 |
| `tests/test_world/test_proximity_events.py` (新規) | enter / leave / 複数 pair / 閾値境界 / 同 tick 複数 crossing |
| `tests/test_cognition/test_biorhythm_events.py` | stress crossing を既存ファイルに追加 (up / down / 非交差) |
| `tests/test_cognition/test_importance.py` (存在すれば追記) or 新規 | 4 新型の estimate_importance (base だけ参照) |
| `tests/test_cognition/test_state.py` (存在すれば追記) | 4 新型を含む observations で `advance_physical` が fall-through でなく設定された event_weight で動作することを確認 |
| `tests/test_cognition/test_prompting.py` or 既存 | window 10、Proximity clamp 2 件 |

## Stress BiorhythmEvent の流し方

`CycleResult.envelopes` は `list[ControlEnvelope]` — Observation は入れられない。次の 3 案を検討:

- **A. `CycleResult.follow_up_observations` 新設 + `WorldRuntime._consume_result` で rt.pending へ append** — 本採用。runtime 層に責務を閉じ込める。ユニットテストは CycleResult だけで検証可能
- **B. `ReflectionEventMsg` の様に BiorhythmEventMsg ControlEnvelope を追加** — LLM prompt に入らない (Observation ではないため build_user_prompt から見えない) ので要件を満たさない
- **C. `rt.pending` に直接 push する dependency を cycle に渡す** — 結合強過ぎ、テスト困難

→ 採用 A。既存の `_detect_biorhythm_crossings` (physical) を流用して stress 版を追加:
- `_detect_stress_crossing(prev: Cognitive, current: Cognitive, ...)` を新設
- Step 8 完了後 (new_cognitive 生成後) に呼び、結果を `CycleResult.follow_up_observations` に置く
- `WorldRuntime._consume_result` で `rt.pending.extend(res.follow_up_observations)`

## Proximity firing の実装方針

- `WorldRuntime` に `_pair_distances: dict[frozenset[str], float]` を持つ (key は agent_id 2 つの frozenset、value は前回 tick の距離)
- `_on_physics_tick` 末尾 (TemporalEvent の後) で `_fire_proximity_events()` 呼び出し
- agents が 2 未満なら早期 return (fast path)
- 全ペアに対し distance を計算、prev との比較で enter (prev >= 5, now < 5) / leave (prev < 5, now >= 5) を判定
- 2 方向に event を emit (双方の rt.pending に append)
- 閾値 5m は :data:`_PROXIMITY_THRESHOLD_M` として module 定数化

## Prompt per-type clamp

`build_user_prompt` 内で `recent = list(observations)[-recent_limit:]` の後、`recent` から Proximity を最新 2 件だけに絞る。他 3 新型は clamp しない (per-tick 発火頻度が低いため窓内で 2 を超えない)。

```python
def _clamp_proximity(recent: list[Observation], max_proximity: int = 2) -> list[Observation]:
    """Keep only the N most recent ProximityEvent; preserve order of other types."""
```

## テスト戦略

1. `uv run pytest tests/test_cognition/ tests/test_world/ -q` — 既存 730 PASS + 新規 >10 PASS
2. `uv run ruff check src/ tests/` / `ruff format --check`
3. 既存の `test_biorhythm_events.py` パターンを拡張
4. Proximity は `ManualClock` で 2 agent を近づけ→離す→2nd 近接の 3 pattern で検証

## リスクと緩和

| リスク | 緩和 |
|---|---|
| `CycleResult.follow_up_observations` 追加で既存 caller が壊れる | `default_factory=list` で backward-compat、既存 test の model_dump() も additive |
| Proximity event 発火頻度過多で prompt 肥大 | per-type clamp (2 件) で最終 defence、ただし physics 30Hz で crossing 自体は稀なはず |
| Stress は tick 遅延する自覚 | docstring で明示、既存 `_detect_biorhythm_crossings` の note と整合させる |
