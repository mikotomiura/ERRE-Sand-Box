# T12 cognition-cycle-minimal — タスクリスト

採用設計 v2 に基づく。各タスクは 30 分以内が目安。

## Step A/B/C ✓ (完了)
- [x] Explore agent でコンテキスト収集
- [x] persona-erre / error-handling / architecture-rules / llm-inference Skill
- [x] memory / inference の公開 API 確認
- [x] requirement.md 記述
- [x] design-v1.md (素直案 + 12 弱点)
- [x] /reimagine → v2 再生成 → design-comparison → v2 採用
- [x] design.md に v2 記録

## Step D ✓
- [x] tasklist.md 分解 (本ファイル)

## Step E: 実装

### E-1: cognition/importance.py
- [ ] `_BASE_IMPORTANCE` event_type lookup dict
- [ ] `estimate_importance(observation) -> float`
- [ ] `__all__`

### E-2: cognition/parse.py
- [ ] `LLMPlan(BaseModel, frozen=True)` 8 フィールド
- [ ] `parse_llm_plan(text: str) -> LLMPlan | None`
- [ ] JSON object 抽出 (code fence 対応)
- [ ] `__all__`

### E-3: cognition/state.py
- [ ] `StateUpdateConfig(frozen dataclass)` + `DEFAULT_CONFIG`
- [ ] `_clamp_unit` / `_clamp_signed` / `_clip` / `_noise(rng)` helpers
- [ ] `advance_physical(prev, events, *, config, rng) -> Physical`
      (4 要素導出)
- [ ] `apply_llm_delta(prev, plan, *, config, rng) -> Cognitive`
      (valence / arousal / motivation / stress)
- [ ] `__all__`

### E-4: cognition/prompting.py
- [ ] `RESPONSE_SCHEMA_HINT` 定数 (JSON スキーマ説明)
- [ ] `_COMMON_PREFIX` (RadixAttention 用)
- [ ] `build_system_prompt(persona, agent) -> str`
- [ ] `format_memories(memories, max_items=8) -> str`
- [ ] `build_user_prompt(observations, memories, recent_limit=5) -> str`
- [ ] `__all__`

### E-5: cognition/cycle.py
- [ ] `CycleResult(BaseModel, frozen=True)`
- [ ] `CognitionError(RuntimeError)`
- [ ] `CognitionCycle` クラス:
      - [ ] ClassVar: `DEFAULT_DESTINATION_SPEED`, `REFLECTION_IMPORTANCE_THRESHOLD`,
            `DEFAULT_TICK_SECONDS`
      - [ ] `__init__(*, retriever, store, embedding, llm, rng, update_config)`
      - [ ] `_observation_to_memory(obs, importance) -> MemoryEntry`
      - [ ] `_content_for_embed(obs) -> str`
      - [ ] `_build_retrieval_query(observations, agent) -> str`
      - [ ] `_detect_zone_entry(observations, zones) -> bool`
      - [ ] `_fallback(agent, mids, reflective, physical) -> CycleResult`
      - [ ] `async step(agent_state, persona, observations, *, tick_seconds) -> CycleResult`

### E-6: cognition/__init__.py 差し替え
- [ ] docstring + 12 シンボル re-export + `__all__`

### E-7: tests/test_cognition/ 新規
- [ ] `tests/test_cognition/__init__.py` (空)
- [ ] `tests/test_cognition/conftest.py` — LLM/embedding mock helper, store 共有
- [ ] `test_importance.py` (5+ tests, event_type table driven)
- [ ] `test_parse.py` (6 tests, JSON / code fence / invalid / clamp)
- [ ] `test_state.py` (5+ tests, RNG 決定論 + クランプ + monotonicity)
- [ ] `test_prompting.py` (4 tests, habits / memories / observations / prefix 順)
- [ ] `test_cycle.py` (7 tests, happy path + fallback + reflection + sampling)

## Step F: テストと検証
- [ ] `uv run pytest tests/test_cognition -v` (新規 ~27 件、全 pass)
- [ ] `uv run pytest tests/` 全体緑 (157 → ~180, skip 23 維持)
- [ ] `uv run ruff check .` 緑
- [ ] `uv run ruff format --check .` 緑
- [ ] `uv run mypy src tests` 緑
- [ ] 依存方向: `grep -r "from erre_sandbox" src/erre_sandbox/cognition/`
      で `schemas / memory / inference / cognition.*` のみ

## Step G: code-reviewer (Opus)
- [ ] code-reviewer 起動
- [ ] HIGH → 即修正 / MEDIUM → 判断 / LOW → blockers.md

## Step H: security-checker (軽量)
- [ ] LLM 出力パースの信頼性 (JSON injection / DoS on parse)
- [ ] system prompt に機微情報が残らないか
- [ ] security-checker 起動 (150 行以内)

## Step I: ドキュメント更新
- [ ] `.steering/_setup-progress.md` Phase 8 に T12 エントリ追加
- [ ] `docs/glossary.md` / `docs/functional-design.md` 更新判断
- [ ] `decisions.md` 作成 (8+ 件)
- [ ] `blockers.md` (LOW 懸案記録)

## Step J: コミット・PR
- [ ] `feat(cognition): T12 cognition-cycle-minimal — 1-tick CoALA/ERRE pipeline
      (pure state + structured LLMPlan + 9-step orchestrator)`
- [ ] `Co-Authored-By: Claude Opus 4.7 (1M context)` + `Refs:` 付与
- [ ] `git push -u origin feature/cognition-cycle-minimal`
- [ ] `gh pr create` (G-GEAR に gh 2.90.0 あり)

## ブロッカー候補
- Ollama JSON 応答が安定しない (プロンプトで指示しても散文返答) →
  `format: "json"` adapter 拡張を後続タスクに送る (BL で記録)
- `advance_physical` の 4 要素導出パラメータが MVP では暫定値、実測で tune する
  機会が必要 → M4 reflection 実装時に再校正
- `Observation.content_for_embed()` という概念が schemas にない → cycle.py 内
  の private helper で event_type 別にテキスト生成
