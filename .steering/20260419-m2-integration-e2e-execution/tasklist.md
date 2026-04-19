# タスクリスト — T19 実行フェーズ

design.md の v1 採用 (reimagine 不適用) に基づき、以下の順で進める。

## Phase A: 準備・設計記録

- [x] A1. `requirement.md` 記入 (ユーザー承認済)
- [x] A2. `design.md` 記入 (ユーザー承認済)
- [ ] A3. `decisions.md` 作成 (D1-D5、Phase B 着手前の初期版)
- [ ] A4. `.gitignore` に `logs/` を追加 (未追加なら)
- [ ] A5. `git checkout -b feature/m2-integration-e2e-execution`

## Phase B: conftest.py 拡張

- [ ] B1. `FakeEmbedder` クラスを `tests/test_integration/conftest.py` に追加
      (deterministic: `hash(text) -> np.ndarray[768]`、prefix 検証用に `last_docs` / `last_queries` 属性)
- [ ] B2. `memory_store_with_fake_embedder` async fixture 追加
      (tmp_path 経由の in-memory sqlite-vec、module-scoped)
- [ ] B3. `m2_logger` fixture 追加
      (`M2_LOG_PATH` env 未設定なら no-op、設定時は jsonl 行書出し)
- [ ] B4. `uv run pytest tests/test_integration/test_gateway.py` が引き続き緑であることを確認 (回帰防止)

## Phase C: test_scenario_walking.py 点灯

- [ ] C1. `pytestmark = pytest.mark.skip(...)` 行を削除
- [ ] C2. `_client_hs()` / `_recv_envelope()` ヘルパを共有化
      (`tests/test_integration/_ws_helpers.py` 新規、test_gateway.py からも import)
- [ ] C3. `test_s_walking_step0_world_registers_kant_in_peripatos` 実装
      (AgentUpdateMsg inject → 受信 → erre_mode/zone 検証)
- [ ] C4. `test_s_walking_step1_gateway_heartbeat` 実装
      (WorldTickMsg inject → 受信 → active_agents 検証)
- [ ] C5. `test_s_walking_step2_cognition_emits_move` 実装
      (MoveMsg inject → 受信 → speed>0 検証、続いて AgentUpdateMsg erre_mode=PERIPATETIC inject → 受信)
- [ ] C6. `test_s_walking_step3_godot_avatar_moves` 実装
      (AnimationMsg(animation="walk") inject → 受信 → animation 値検証)
- [ ] C7. `uv run pytest tests/test_integration/test_scenario_walking.py -v` で 4 件 PASS

## Phase D: test_scenario_memory_write.py 点灯

- [ ] D1. `pytestmark = pytest.mark.skip(...)` 行を削除
- [ ] D2. `test_s_memory_write_steps_are_three` 実装 (sanity check のみ、FakeEmbedder 不要)
- [ ] D3. `test_s_memory_write_writes_four_episodic_one_semantic` 実装
      (memory_store_with_fake_embedder fixture 利用、4 episodic + 1 semantic 書込 → count 検証)
- [ ] D4. `test_s_memory_write_embedding_prefix_applied` 実装
      (FakeEmbedder.last_docs が `DOC_PREFIX` で始まる文字列を記録していることを確認)
- [ ] D5. `uv run pytest tests/test_integration/test_scenario_memory_write.py -v` で 3 件 PASS

## Phase E: test_scenario_tick_robustness.py 点灯

- [ ] E1. `pytestmark = pytest.mark.skip(...)` 行を削除
- [ ] E2. `test_s_tick_robustness_initial_agent_update` 実装
      (初期 AgentUpdateMsg を inject → 受信)
- [ ] E3. `test_s_tick_robustness_tolerates_missed_heartbeat` 実装
      (tick=1 と tick=3 を inject、tick=2 スキップ、ErrorMsg が出ないことを確認)
- [ ] E4. `test_s_tick_robustness_survives_reconnect` 実装
      (1st session で handshake → close → 2nd session で新 HandshakeMsg 受信、schema_version 一致、server_hs.tick=0)
- [ ] E5. `test_s_tick_robustness_memory_continuity` 実装
      (reconnect 前後で MockRuntime が同じ agent_id で AgentUpdateMsg を inject し、memory_count 増加が monotonic)
- [ ] E6. `uv run pytest tests/test_integration/test_scenario_tick_robustness.py -v` で 4 件 PASS

## Phase F: CI 検証・Layer C smoke run

- [ ] F1. `uv run pytest tests/test_integration/` で全件 PASS
- [ ] F2. `uv run pytest` 全体 (baseline 294 + 新規 11 = 305 程度、skip 数は -11)
- [ ] F3. `uv run ruff check` 緑
- [ ] F4. `uv run ruff format --check` 緑
- [ ] F5. `uv run mypy src` 緑
- [ ] F6. (G-GEAR smoke) Ollama serve 起動、`qwen3:8b` / `nomic-embed-text` 存在確認
      `ollama list | grep -E 'qwen3:8b|nomic-embed-text'`
- [ ] F7. (G-GEAR smoke) `uv run python -m erre_sandbox.integration.gateway` を
      バックグラウンド起動、`curl http://localhost:8000/health` で 200 確認、kill
- [ ] F8. Smoke run 結果を `decisions.md` D2 付記に追記

## Phase G: handoff 文書 + MASTER-PLAN sync

- [ ] G1. `handoff-to-macbook.md` 作成
      (ACC-DOCS-UPDATED / ACC-TAG-READY / Godot 30Hz 実機検証 / v0.1.0-m2 タグ を項目化)
- [ ] G2. `.steering/20260418-implementation-plan/tasklist.md` T19 行を
      `[x]` + 実行フェーズ完了 + 本タスク PR 番号併記 に更新 (commit 分離用メモ)

## Phase H: レビュー

- [ ] H1. self-review (design.md / decisions.md / handoff-to-macbook.md の整合確認)
- [ ] H2. code-reviewer subagent 起動
      (差分: tests/test_integration/ 4 ファイル + conftest.py + _ws_helpers.py)
- [ ] H3. HIGH 指摘対応 → 再実行
- [ ] H4. MEDIUM 指摘をユーザーに提示、判断仰ぎ

## Phase I: コミット・PR

- [ ] I1. `git add tests/test_integration/ .gitignore .steering/20260419-m2-integration-e2e-execution/`
- [ ] I2. commit: `feat(integration): T19 execution — skeleton tests unskipped + Layer B/C smoke`
      本文に `Refs: .steering/20260419-m2-integration-e2e-execution/`
- [ ] I3. 別 commit: `chore(steering): sync MASTER-PLAN tasklist with T19 execution completion`
- [ ] I4. `git push -u origin feature/m2-integration-e2e-execution`
- [ ] I5. `gh pr create` (base=main)
- [ ] I6. `/finish-task` で完了処理

## ロールバック

```bash
git checkout main
git branch -D feature/m2-integration-e2e-execution
# tests/test_integration/ の skip マーカーが復活するのみ、src/ への影響はゼロ
```
