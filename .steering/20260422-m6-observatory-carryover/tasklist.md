# タスクリスト

## Phase 1: 小さい fix (TDD で 1 つずつ)

- [x] T1a `cognition/cycle.py:_observation_content_for_embed()` に 4 新型分岐を追加
- [x] T1b `cognition/importance.py:_BASE_IMPORTANCE` に 4 新型のキーを追加
- [x] T1c `cognition/state.py:_PHYSICAL_EVENT_IMPACT` に 4 新型のキーを追加
- [x] T1d test 追加: importance/state の 4 新型 default handling

## Phase 2: Stress BiorhythmEvent

- [x] T2a `cognition/cycle.py` に `_detect_stress_crossing(prev, current, agent_id, tick)` 新設
- [x] T2b `CycleResult` に `follow_up_observations: list[Observation]` フィールド追加
- [x] T2c `CognitionCycle.step` Step 8 後に crossing 検出 → `CycleResult.follow_up_observations` に格納
- [x] T2d `WorldRuntime._consume_result` で `res.follow_up_observations` を `rt.pending` に append
- [x] T2e test `test_biorhythm_events.py` に stress up/down/非交差を追加

## Phase 3: Proximity firing (world/tick.py)

- [x] T3a `WorldRuntime.__init__` に `_pair_distances: dict[frozenset[str], float]` + `_PROXIMITY_THRESHOLD_M: Final[float] = 5.0`
- [x] T3b `_fire_proximity_events()` 実装 (全ペア走査、enter/leave 判定、両 agent の rt.pending に append)
- [x] T3c `_on_physics_tick` 末尾 (TemporalEvent 後) に呼び出し追加
- [x] T3d test 新規 `tests/test_world/test_proximity_events.py` — enter / leave / 複数 pair / 閾値境界 / 同 tick 複数

## Phase 4: Prompt 窓拡張 + clamp

- [x] T4a `build_user_prompt(recent_limit: int = 10)` に default 変更、docstring 更新
- [x] T4b `_clamp_proximity(recent, max_proximity=2)` ヘルパー追加
- [x] T4c test `test_prompting.py` (存在すれば) に window 10 + clamp 2 件のケース追加

## Phase 4.5 (Godot): ReasoningPanel 枠外化 + 接続状態可視化 (追加対応)

- [x] ユーザー報告を受け、Godot 側に 2 件対応を追加:
    - **(a) ReasoningPanel layout**: world と overlapping していて "worldが見えにくい" → `MainScene.tscn` を `HBoxContainer(Split)` + `SubViewportContainer(WorldView)` + `SubViewport(WorldViewport)` 構造に再編。3D content (Camera / lights / zones / avatars / SelectionManager) は SubViewport 内に移動。ReasoningPanel は HBoxContainer の右側兄弟として `custom_minimum_size=(320,0)` で置く。これで 3D render 領域とパネルが重ならない
    - **(b) 接続状態可視化**: "一切Agentが見えない" の背景に WS 未接続ケースがあるので、`WorldManager.gd` で `WebSocketClient.connection_status_changed` を購読し DebugOverlay に `[WS connected/disconnected]` プレフィックスを表示。第一 tick を受信するまで `awaiting first tick…`
- [x] `ReasoningPanel.gd._build_tree()` の自己アンカー (right-edge 420px 固定) を削除、HBoxContainer 委任に変更
- [ ] (MacBook 側で再検証必要) Godot 4.x 実機起動テスト — G-GEAR には Godot 未設置
- [ ] (Optional) FixtureHarness での headless 検証 — 既存 test_godot_peripatos は FixtureHarness 経由だが MainScene を instance しているので壊れていないはず (要 Godot 実機)

## Phase 5: 統合検証

- [x] T5a `uv run pytest -q` で既存 730 PASS + 新規 PASS 確認 (結果: 755 passed / 36 skipped / 0 failed)
- [x] T5b `uv run ruff check src/ tests/` / `ruff format --check src/ tests/` (両方 clean)
- [x] T5c `.steering/20260421-m6-observatory/tasklist.md` の該当 checkbox を cross-update
- [x] T5e G-GEAR live 検証 — 3-agent orchestrator (qwen3:8b) を 80s 稼働:
    - `GET /health` → `schema_version=0.4.0-m6`
    - `POST /api/chat` × 24、`POST /api/embed` 正常
    - `Reflection trigger` × 5 (tick 1 で Kant/Rikyu + tick 2 で 3 agents)
    - `LLM returned unparseable` × 1 (約 4%、qwen3 通常値域)
    - **Traceback / Exception × 0** — `_fire_proximity_events` / `_fire_temporal_events` / `_detect_stress_crossing` / `_clamp_proximity` / `_observation_content_for_embed` のすべてが crash ゼロで live を通過
- [ ] T5d commit + PR (feature/m6-observatory-carryover → main)
