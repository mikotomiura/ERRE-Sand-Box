# 設計 (v2 採用版) — 5 モジュール分離 + pure state + structured LLM plan

> **採用確定**: v1 の 12 弱点中、致命 3 / 高 3 を構造で解消
> 比較根拠: `design-comparison.md`
> 破棄案: `design-v1.md`

## 1. 実装アプローチ

1 tick の認知サイクルを **5 つの責務別モジュール**に分割し、orchestrator
(`cognition/cycle.py`) から個別に呼び出す。状態遷移とプロンプト組み立てと
LLM 出力パースをすべて **純粋関数** (I/O なし、副作用なし) にすることで
ユニットテスト可能性と決定論的再現を確保する。

- `state.py` — CSDG 半数式による Physical / Cognitive 更新 (pure)
- `prompting.py` — system / user プロンプト文字列組み立て (pure)
- `parse.py` — LLM 出力の JSON パース + `LLMPlan` Pydantic 型 (pure)
- `importance.py` — Observation → importance の event_type lookup (pure)
- `cycle.py` — `CognitionCycle` クラス / `CycleResult` / 8 ステップの orchestrator

## 2. モジュール構成

```
src/erre_sandbox/cognition/
├── __init__.py                # 公開 API re-export
├── state.py                   # pure: advance_physical, apply_llm_delta
├── prompting.py               # pure: build_system_prompt, build_user_prompt, format_memories
├── parse.py                   # pure: LLMPlan, parse_llm_plan
├── importance.py              # pure: estimate_importance (event_type lookup)
└── cycle.py                   # CognitionCycle, CycleResult, step()
```

### 2.1 `cognition/state.py` — 純粋関数 (~160 行)

- `StateUpdateConfig(frozen dataclass)` — decay_rate / event_weight /
  max_llm_delta / llm_weight / noise_scale の 5 パラメータ
- `advance_physical(prev: Physical, events: Sequence[Observation], *, config, rng) -> Physical`
  — CSDG 半数式の 4 要素導出 (sleep_quality / physical_energy / mood_baseline /
  cognitive_load)
- `apply_llm_delta(prev: Cognitive, llm_delta: LLMPlan, *, config, rng) -> Cognitive`
  — `base + clip(llm_delta, ±max) * weight + gauss(0, noise_scale)` を
  valence / arousal / motivation / stress に適用
- `rng: Random | None` でガウスノイズを決定論化 (テストで seed 固定可能)

### 2.2 `cognition/prompting.py` — 純粋関数 (~120 行)

- `build_system_prompt(persona, agent) -> str` — RadixAttention 最適化のため
  **共通 prefix → ペルソナ固有 → 動的 tail** の 3 段構造 (persona-erre §ルール 3)
- `format_memories(memories: Sequence[RankedMemory], max_items: int = 8) -> str`
  — strength 降順で箇条書き
- `build_user_prompt(observations, memories, recent_limit=5) -> str` — 最新観察
  + memories 要約 + JSON 出力指示を含む
- `RESPONSE_SCHEMA_HINT: Final[str]` — LLM に JSON スキーマを教える定数

### 2.3 `cognition/parse.py` — pure + Pydantic (~100 行)

- `LLMPlan(BaseModel, frozen=True)` — `thought / utterance / destination_zone /
  animation / valence_delta / arousal_delta / motivation_delta / importance_hint`
- `parse_llm_plan(text: str) -> LLMPlan | None` — JSON object 抽出 (code fence
  許容) + `LLMPlan.model_validate` + 失敗時 None
- `extra="forbid"` で LLM が余計な key を出した場合もフォールバック

### 2.4 `cognition/importance.py` — event_type lookup (~50 行)

- `_BASE_IMPORTANCE` — event_type ごとの基準 float (lookup table)
- `estimate_importance(observation) -> float` — 基準値 + intensity /
  emotional_impact による補正 → clamp `[0.0, 1.0]`

### 2.5 `cognition/cycle.py` — orchestrator (~280 行)

- `CycleResult(BaseModel, frozen=True)` — `agent_state / envelopes /
  new_memory_ids / reflection_triggered / llm_fell_back`
- `CognitionError(RuntimeError)` — Unavailable 以外の想定外エラー用 (crash-loud)
- `CognitionCycle`:
  - ClassVar: `DEFAULT_DESTINATION_SPEED=1.3`, `REFLECTION_IMPORTANCE_THRESHOLD=150.0`,
    `DEFAULT_TICK_SECONDS=10.0`
  - `__init__(*, retriever, store, embedding, llm, rng=None, update_config=None)`
  - `async step(agent_state, persona, observations, *, tick_seconds=10.0) -> CycleResult`

### 2.6 `cognition/__init__.py`

12 シンボル re-export:
`CognitionCycle / CycleResult / CognitionError / StateUpdateConfig /
advance_physical / apply_llm_delta / LLMPlan / parse_llm_plan /
estimate_importance / build_system_prompt / build_user_prompt /
format_memories`

## 3. 9 ステップ orchestrator (cycle.step の実装ロジック)

```
step(agent_state, persona, observations):

  # Step 1: Observe / Appraise — write observations as Episodic memories
  for obs in observations:
      imp  = estimate_importance(obs)
      vec  = await embedding.embed_document(obs.content_for_embed())
      mid  = await store.add(_observation_to_memory(obs, imp), vec)
      new_memory_ids.append(mid)

  # Step 2: Update Physical (pure CSDG half-step)
  new_physical = advance_physical(
      agent_state.physical, observations,
      config=self._update_config, rng=self._rng,
  )

  # Step 3: Reflection trigger detection (実行は M4+)
  importance_sum = sum(estimate_importance(o) for o in observations)
  reflective = _detect_zone_entry(observations, {Zone.PERIPATOS, Zone.CHASHITSU})
  reflection_triggered = importance_sum > THRESHOLD or reflective

  # Step 4: Retrieve memories (Unavailable は空リストで続行)
  try:
      memories = await retriever.retrieve(agent_state.agent_id, _query(observations))
  except (OllamaUnavailableError, EmbeddingUnavailableError):
      memories = []

  # Step 5-6: Prompt + LLM
  system = build_system_prompt(persona, agent_state)
  user   = build_user_prompt(observations, memories)
  sampling = compose_sampling(persona.default_sampling, agent_state.erre.sampling_overrides)
  try:
      resp = await llm.chat([ChatMessage("system", system), ChatMessage("user", user)],
                            sampling=sampling)
  except OllamaUnavailableError:
      return self._fallback(agent_state, new_memory_ids, reflection_triggered, new_physical)

  # Step 7: Parse
  plan = parse_llm_plan(resp.content)
  if plan is None:
      return self._fallback(agent_state, new_memory_ids, reflection_triggered, new_physical)

  # Step 8: Update Cognitive (pure)
  new_cognitive = apply_llm_delta(
      agent_state.cognitive, plan,
      config=self._update_config, rng=self._rng,
  )

  # Step 9: Assemble
  new_state = agent_state.model_copy(update={
      "tick": agent_state.tick + 1,
      "physical": new_physical,
      "cognitive": new_cognitive,
  })
  envelopes = [AgentUpdateMsg(tick=new_state.tick, agent_state=new_state)]
  if plan.utterance:        envelopes.append(SpeechMsg(...))
  if plan.destination_zone: envelopes.append(MoveMsg(...))
  if plan.animation:        envelopes.append(AnimationMsg(...))

  return CycleResult(
      agent_state=new_state, envelopes=envelopes,
      new_memory_ids=new_memory_ids,
      reflection_triggered=reflection_triggered,
      llm_fell_back=False,
  )
```

Fallback:
- Physical は更新済 (LLM なしで物理的時間経過は起きる)
- Cognitive は据え置き
- tick は +1 (時間は進む)
- envelopes は `AgentUpdateMsg` 1 件のみ (speech / move / animation なし)
- `llm_fell_back=True`

## 4. 依存方向の確認

```
cognition/state.py      → schemas + pydantic ✓
cognition/prompting.py  → schemas + memory (RankedMemory 型) ✓
cognition/parse.py      → schemas (Zone) + pydantic ✓
cognition/importance.py → schemas (Observation) ✓
cognition/cycle.py      → schemas + memory + inference + 同モジュール内 ✓
```

architecture-rules Skill:
- `cognition/ → inference/, memory/, schemas` OK
- `cognition/ → world/, ui/` **NG** — 実装で import しない

`grep -r "from erre_sandbox" src/erre_sandbox/cognition/` で許可される 4 種のみ:
`schemas`, `memory`, `inference`, `cognition.{state,prompting,parse,importance}`

## 5. 変更対象

### 5.1 新規作成

| ファイル | 想定行数 |
|---|---|
| `src/erre_sandbox/cognition/state.py` | ~160 |
| `src/erre_sandbox/cognition/prompting.py` | ~120 |
| `src/erre_sandbox/cognition/parse.py` | ~100 |
| `src/erre_sandbox/cognition/importance.py` | ~50 |
| `src/erre_sandbox/cognition/cycle.py` | ~280 |
| `tests/test_cognition/__init__.py` | 0 |
| `tests/test_cognition/conftest.py` | ~80 |
| `tests/test_cognition/test_state.py` | ~150 |
| `tests/test_cognition/test_prompting.py` | ~90 |
| `tests/test_cognition/test_parse.py` | ~120 |
| `tests/test_cognition/test_importance.py` | ~60 |
| `tests/test_cognition/test_cycle.py` | ~280 |

合計 新規 ~1490 行

### 5.2 修正

| ファイル | 内容 |
|---|---|
| `src/erre_sandbox/cognition/__init__.py` | docstring のみ → 12 シンボル re-export |
| `.steering/_setup-progress.md` | Phase 8 に T12 エントリ追加 |

### 5.3 削除

なし。

## 6. テスト戦略

### 6.1 `test_state.py` (pure)
- `advance_physical` の fatigue 減衰 monotonicity
- `apply_llm_delta` で `valence_delta=1.0` 時のクランプ
- RNG seed 固定でノイズが再現 (`Random(42)` → 同じ出力)
- `max_llm_delta` を超える LLM 入力が clip される
- `StateUpdateConfig` 差し替えで挙動が変わる (`decay_rate=0.0` → no decay)

### 6.2 `test_prompting.py` (pure)
- `build_system_prompt` に persona.cognitive_habits の description + flag が含まれる
- `format_memories` が strength 降順、空 list は空文字列
- `build_user_prompt` に最新観察が含まれ、古い観察は `recent_limit` で切り捨て
- 共通 prefix がペルソナ固有部分より前にある (RadixAttention 最適化確認)

### 6.3 `test_parse.py` (pure)
- 正常 JSON → `LLMPlan`
- code fence (` ```json ... ``` `) 囲み → 抽出成功
- JSON 不正 → None
- `valence_delta=1.5` → Pydantic range 違反 → None
- `extra` キー → `extra="forbid"` で None
- 空 JSON object → `thought` 未指定で None

### 6.4 `test_importance.py` (pure)
- event_type 5 種 table driven
- `PerceptionEvent(intensity=1.0)` → 基準値より高い
- `SpeechEvent(emotional_impact=-1.0)` → 基準値より高い (絶対値)

### 6.5 `test_cycle.py` (統合)
- `test_step_happy_path` — MockTransport で LLM JSON 応答、
  AgentUpdateMsg + SpeechMsg + MoveMsg が出る
- `test_step_writes_episodic_memory` — `store.list_by_agent(EPISODIC)` が増える
- `test_step_falls_back_on_ollama_error` — OllamaUnavailableError → `llm_fell_back=True`
- `test_step_falls_back_on_malformed_llm_output` — 非 JSON → `llm_fell_back=True`
- `test_step_applies_erre_sampling` — peripatetic モード → LLM に送信された
  `options.temperature` が persona.base + 0.3
- `test_step_detects_reflection_trigger` — ZoneTransition Event → `reflection_triggered=True`
- `test_step_advances_physical_even_on_fallback` — fallback path で Physical
  は更新される (LLM なしで時間は進む)

### 6.6 回帰確認

- baseline: 157 passed / 23 skipped (T11 完了時)
- 期待: +20-25 = **~180 passed**
- skip は 23 のまま

## 7. 既存パターンとの整合性

- T10 / T11 と対称: ClassVar defaults、DI (store/embedding/llm/retriever/rng)、
  Pydantic frozen 戻り値型 (`CycleResult`)、`*Error` 1 種で正規化
- python-standards / test-standards 準拠
- ruff ALL + mypy strict + pytest asyncio mode=auto
- error-handling Skill: crash-loud + 限定 fallback (Unavailable / ParseFail
  のみ、ValidationError は parse で吸収、AttributeError 等は伝播)

## 8. ロールバック計画

- 5 新規ファイル + 6 新規テストファイルのみ。`git revert` 1 コミットで復元
- LLM 出力契約 (`LLMPlan`) の変更は breaking — M4 以降で再設計時は別 PR
- CSDG 半数式の係数 (`decay_rate`, `event_weight` 等) は `StateUpdateConfig`
  差し替えのみで調整可 (コード変更不要)
