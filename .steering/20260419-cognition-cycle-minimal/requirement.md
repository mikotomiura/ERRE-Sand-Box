# T12 cognition-cycle-minimal — requirement

- 対象タスク: MASTER-PLAN §4.2 T12
- 担当機: **G-GEAR** (この作業ディレクトリ)
- 日付: 2026-04-19
- 依存完了: T10 (memory-store) / T11 (inference-ollama-adapter)

## 1. 背景

ERRE-Sandbox MVP (M2) の核は「1 体の Kant エージェントが peripatos を歩き、
Memory Stream に記憶を書き、Godot 4.4 で描画される」(functional-design.md §4)。
T10 / T11 で memory (sqlite-vec + embedding + retrieval) と inference
(Ollama `/api/chat` + sampling compose) の 2 基盤は完成した。

**T12 は両者を orchestrate し、**"AgentState + 観察群" を受け取って
"更新後 AgentState + 出力 Envelope 群" を返す **1 tick 分の認知パイプライン**
を実装する。以降 T13 (world tick) と T14 (gateway) は T12 を call するだけで
MVP が成立する。

### 認知サイクル 8 ステップ (docs/architecture.md §Simulation Layer, CoALA + ERRE)

```
Observe → Appraise → Update Physical → Retrieve → Reflect? → Plan → Act → Speak
```

- **Observe / Appraise**: 入力 `Observation` 群に importance を付与
- **Update Physical**: CSDG 半数式で `Physical` を tick 単位で遷移
  (sleep_quality, physical_energy, mood_baseline, cognitive_load の 4 要素
  自動導出 — MASTER-PLAN B.3)
- **Retrieve**: `Retriever.retrieve(agent_id, query, k_agent=8, k_world=3)`
- **Reflect?**: `importance_sum > 150` または peripatos/chashitsu 入室時の
  トリガー判定のみ (実行は M4+ で実装)
- **Plan → Act → Speak**: LLM chat call で行動候補を生成、構造化パースして
  `ControlEnvelope` (`MoveMsg` / `SpeechMsg` / `AnimationMsg`) に変換
  + `Cognitive` の LLM delta 合成

### 既存資産との接続

| コンポーネント | 状態 | 使い方 |
|---|---|---|
| `schemas.AgentState / Observation / PersonaSpec / ERREMode / ControlEnvelope` | T05 凍結済 | 入出力型 |
| `memory.Retriever` (`retrieve` / `RankedMemory`) | T10 実装済 | Step 4 Retrieve |
| `memory.MemoryStore.add` | T10 実装済 | Step 9 Memory Write |
| `memory.EmbeddingClient.embed_document` | T10 実装済 | Memory Write 前の埋め込み |
| `inference.OllamaChatClient.chat` | T11 実装済 | Step 5 LLM 推論 |
| `inference.compose_sampling` | T11 実装済 | ERRE モード別サンプリング適用 |
| `inference.OllamaUnavailableError` | T11 実装済 | Step 5 catch → continue-current-action fallback |
| `cognition.cycle` (本タスク) | 新規 | 8 ステップ統合 |

### CSDG 半数式 (MASTER-PLAN 付録 B.3、MVP 優先 #2)

```
base      = prev * (1 - decay_rate) + event_impact * event_weight
composed  = base + clip(llm_delta, ±max_llm_delta) * llm_weight
            + gauss(0, noise_scale)
```

4 要素導出 (`Physical`):
- `sleep_quality`   ← 前 tick fatigue + stress ペナルティ + ドリフト
- `physical_energy` ← sleep_quality + 前 tick fatigue
- `mood_baseline`   ← 減衰 + ドリフト + 微小イベント impact 累積
- `cognitive_load`  ← 未解決課題 + stress + ネガティブ event 累積

値は schemas.py の Field range に対応 (`[0, 1]` / `[-1, 1]`) にクランプ。

## 2. ゴール (完了条件)

1. `src/erre_sandbox/cognition/` 配下で 1 tick の認知パイプラインを公開
   - `CognitionCycle` クラス / `step(agent_state, observations, persona) -> CycleResult`
   - `CycleResult` Pydantic モデル — `agent_state / envelopes / new_memory_ids / llm_fell_back`
2. CSDG 半数式状態遷移を **純粋関数**として切り出す (`cognition/state.py`)
   - `advance_physical(prev, events, rng=None) -> Physical`
   - `apply_llm_delta(prev, llm_delta, rng=None) -> Cognitive`
3. LLM 出力を **構造化パース**する (`cognition/parse.py`)
   - 期待形式: JSON 1 object (`Ollama` の `format: "json"` は MVP では使わず、
     プロンプトで JSON を要求して Pydantic バリデーション + フォールバック)
   - フィールド: `thought: str` / `utterance: str | null` / `destination_zone: Zone | null` /
     `animation: str | null` / `valence_delta / arousal_delta / motivation_delta` (all ∈ [-1, 1])
4. system prompt 組み立て (`cognition/prompting.py`) — ペルソナ + AgentState +
   memories + observations を文字列化 (persona-erre §ルール 3 方針)
5. `OllamaUnavailableError` / `EmbeddingUnavailableError` / `ValidationError` を
   catch し **「現在の行動を継続」フォールバック** を実装 (functional-design §エラー条件)
6. 依存方向厳守: `cognition/` は `schemas` / `memory` / `inference` のみ import 可
   (architecture-rules Skill)
7. テスト: 状態遷移の純粋関数ユニット + LLM mock での 1 サイクル統合、
   `uv run pytest` 全体緑 (baseline 157 → ~175+)
8. 静的解析: ruff / format / mypy 全緑
9. CI リグレッションなし

## 3. スコープ内

- `CognitionCycle.step()` の 1 エージェント 1 tick 実装 (9 ステップ完全)
- CSDG 半数式による Physical 遷移 (4 要素自動導出) + 決定論的 RNG 注入
- 重要度ヒューリスティック: event_type 別基準 (MVP は lookup table ベース)
- Retriever を使った 2 層検索 (既存 API そのまま)
- system prompt 組み立て (習慣 fact/legend/speculative、AgentState dump、
  memories 上位 N、観察直近 M)
- ERRE モード別サンプリングの適用 (compose_sampling 経由)
- LLM 出力の JSON パース + Pydantic バリデーション
- タイムアウト/接続エラー時の **継続行動フォールバック** (direct `continue`
  → AgentState 位置据え置き、speech なし、animation 維持)
- 新規 `MemoryEntry` の埋め込み + DB 永続化 (`EPISODIC` のみ MVP)
- 出力 `ControlEnvelope` の生成 (`AgentUpdateMsg` 必須、Move/Speech/Animation
  はオプショナル)
- 単体テスト (純粋関数 + LLM mock) と統合テスト (MockTransport + Retriever
  を実メモリストアで接続)

## 4. スコープ外

- **PIANO 5 モジュール並列** (M4+、`cognition/piano.py` として後続)
- **Reflection 本体実行** (M4+、ここではトリガー判定と log のみ)
- **ERRE モード FSM 遷移** (M5+、ここでは固定モード 1 tick のみ)
- **複数エージェント並列 `asyncio.gather`** (T13 world tick の責務)
- **30Hz tick loop** (T13)
- **WebSocket 送信** (T14 gateway)
- **Semantic / Procedural / Relational memory write** (Semantic は M4 reflection で
  生成される、MVP は `EPISODIC` のみ)
- **LoRA ペルソナ** (M9+)
- **Ollama JSON mode** (`format: "json"`) — MVP ではプロンプト指示 + 寛容な
  パーサで対応、厳密な JSON 強制は後続 PR で追加可能
- **streaming LLM** (M5+)
- **importance の LLM 評価** (MVP は event_type ヒューリスティックのみ、
  M4+ で LLM scoring に切替可)

## 5. 受け入れ条件

### 5.1 コード

- [ ] `src/erre_sandbox/cognition/state.py` — `advance_physical` / `apply_llm_delta`
      / `_clamp_unit` / `_clamp_signed` 等の純粋関数
- [ ] `src/erre_sandbox/cognition/prompting.py` — `build_system_prompt` /
      `build_user_prompt` / `format_memories` の純粋関数
- [ ] `src/erre_sandbox/cognition/parse.py` — `LLMPlan` Pydantic 型 +
      `parse_llm_plan(text) -> LLMPlan | None`
- [ ] `src/erre_sandbox/cognition/importance.py` — `estimate_importance(observation) -> float`
      の event_type lookup
- [ ] `src/erre_sandbox/cognition/cycle.py` — `CognitionCycle` クラス /
      `CycleResult` / `CognitionError` / `step()` メソッド
- [ ] `src/erre_sandbox/cognition/__init__.py` — public API re-export
- [ ] 依存方向 grep で確認: `cognition/` が `world` / `ui` を import しない
- [ ] `from __future__ import annotations` / docstring / 型ヒント完備

### 5.2 テスト

- [ ] `tests/test_cognition/__init__.py` + `conftest.py` (必要なら)
- [ ] `test_state.py`:
  - [ ] `test_advance_physical_decays_fatigue` / `test_advance_physical_sleep_quality_recovers`
  - [ ] `test_apply_llm_delta_clamps_valence` / `test_apply_llm_delta_clips_oversized_llm_delta`
  - [ ] 決定論的 RNG (seed 固定) でガウスノイズの回帰防止
- [ ] `test_prompting.py`:
  - [ ] `test_build_system_prompt_contains_persona_habits`
  - [ ] `test_format_memories_orders_by_strength`
  - [ ] `test_build_user_prompt_embeds_recent_observations`
- [ ] `test_parse.py`:
  - [ ] `test_parse_valid_json_plan`
  - [ ] `test_parse_returns_none_on_malformed_json`
  - [ ] `test_parse_extracts_code_fenced_json`
  - [ ] `test_parse_clamps_oversized_delta`
- [ ] `test_importance.py`:
  - [ ] event_type ごとに期待値 table driven
- [ ] `test_cycle.py` (統合):
  - [ ] `test_step_happy_path_emits_expected_envelopes` — MockTransport +
        in-memory store、MoveMsg / SpeechMsg / AgentUpdateMsg が全部出る
  - [ ] `test_step_writes_new_episodic_memory` — DB に entry 追加
  - [ ] `test_step_falls_back_on_ollama_unavailable` — `OllamaUnavailableError`
        を注入 → `llm_fell_back=True`、位置据え置き、crash なし
  - [ ] `test_step_falls_back_on_malformed_llm_output` — パース失敗 →
        `llm_fell_back=True`
  - [ ] `test_step_applies_erre_sampling_override` — ERRE mode を peripatetic
        にした場合、OllamaChatClient に渡った `sampling.temperature` が
        `persona.base + 0.3` に一致
- [ ] `uv run pytest` 全体緑、+15 前後 (157 → ~172)、skip は 23 のまま

### 5.3 ドキュメント

- [ ] `.steering/20260419-cognition-cycle-minimal/design.md` (v2 採用後)
- [ ] `design-v1.md` / `design-comparison.md` / `decisions.md` / `blockers.md`
      / `tasklist.md` を揃える
- [ ] `.steering/_setup-progress.md` Phase 8 に T12 エントリ追加

### 5.4 CI / コミット

- [ ] `uv run ruff check .` / `ruff format --check .` 緑
- [ ] `uv run mypy src tests` 緑
- [ ] `uv run pytest tests/` 緑、skip は baseline 23 のまま
- [ ] `feat(cognition): T12 cognition-cycle-minimal — 1-tick CoALA/ERRE pipeline`
- [ ] `Co-Authored-By: Claude Opus 4.7 (1M context)` + `Refs:`
- [ ] `feature/cognition-cycle-minimal` ブランチ → PR 作成

## 6. 想定工数

MASTER-PLAN 見積 1.5d。実装 (~750 行、5 モジュール) + テスト (~500 行) +
.steering 文書 (~1000 行)。Reimagine + レビュー対応込みで 5-6h を想定。

## 運用メモ

- 破壊と構築 (/reimagine) 適用: **Yes**
- 理由:
  - (a) これは MVP の**中核パイプライン** — 他のすべての M4+ 機能 (PIANO /
    Reflection / ERRE FSM) がこの API を継承する。決定後の手戻りコストが最大
  - (b) LLM 出力パースの方針 (JSON mode / プロンプト指示 JSON / タグ付き
    構造化テキスト / 自由テキスト + 正規表現) が複数成立し、どれが正解か自明
    でない
  - (c) CSDG 半数式を "pure function" として切り出すか "CognitionCycle
    メソッド" として内包するかの責務境界に議論の余地
  - (d) `CycleResult` の型設計 (Envelope を複数返すか、side-channel にするか、
    callback で emit するか) が公開 API
