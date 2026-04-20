# 設計 — m4-cognition-reflection (v2 再生成案)

> **status**: v2 / 再構築案 (design-v1.md を参照せずに生成)

## 実装アプローチ

「反省」は cognition cycle の中に inline で織り込むのではなく、
**`Reflector` という責務分離された collaborator** に閉じ込める。
`CognitionCycle` は各 tick で `Reflector.maybe_reflect(...)` を呼び、
結果 (`ReflectionEvent | None`) を `CycleResult` に付けて返すだけ。

これは M4 foundation 設計 §B (Temporality axis) の
「tick-driven cognition に per-agent reflection を**挿入**する」という
契約語彙に忠実な実装になる。

### 3 層構造

```
┌─────────────────────────────────────────────────────────────┐
│ CognitionCycle.step()                                        │
│   9 steps (existing, unchanged in ordering)                  │
│   ↓                                                           │
│   10. reflection_event = await self._reflector.maybe_reflect(│
│                             new_state, observations,         │
│                             importance_sum)                   │
│   ↓                                                           │
│   CycleResult(..., reflection_event=reflection_event)        │
└────────────────────────┬────────────────────────────────────┘
                         │ delegates
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Reflector (new, src/erre_sandbox/cognition/reflection.py)   │
│   - holds ReflectionPolicy (immutable rules)                 │
│   - holds per-agent _ticks_since_last_reflection (dict)      │
│   - owns LLM + Embedding + Store handles                    │
│   - maybe_reflect() decides, fetches, distils, persists     │
│   - returns ReflectionEvent | None, never raises             │
└─────────────────────────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ ReflectionPolicy (new, frozen pydantic / dataclass)         │
│   tick_interval: int = 10                                    │
│   importance_threshold: float = 1.5                          │
│   trigger_zones: frozenset[Zone] = {PERIPATOS, CHASHITSU}   │
│   episodic_window: int = 10                                  │
│   → pure function .should_fire(ticks_since, importance_sum, │
│                                zone_entered) -> bool         │
└─────────────────────────────────────────────────────────────┘
```

### 主要な設計判断

1. **Reflector を collaborator として注入**  
   `CognitionCycle.__init__` に `reflector: Reflector | None = None` を追加。
   `None` なら default Reflector をその場で構築 (MVP 用のゼロ config 経路)。
   テストでは `reflector=FakeReflector()` で完全差し替え可能。

2. **発火条件は ReflectionPolicy の pure method に外出し**  
   `CognitionCycle` 内に ClassVar 定数を書かない。policy インスタンスを
   差し込むことで test-time に tick_interval=1 など任意値に変更できる。
   既存の `REFLECTION_IMPORTANCE_THRESHOLD` ClassVar は後方互換のため残し、
   default policy からそれを参照する形で段階移行。

3. **N tick の表現は `tick % N == 0` ではなく counter**  
   Reflector が per-agent `dict[agent_id, int]` を持ち、各 `maybe_reflect`
   呼び出しで `+1`、発火時に `0` にリセット。理由: #6 で multi-agent
   orchestrator が tick 割当を独立させる可能性があり、グローバルな
   `new_state.tick % 10` は単 agent 前提になりやすい。counter なら
   agent の "episodic experience の累積" という本来の意味に直結する。

4. **`CycleResult.reflection_event: ReflectionEvent | None = None` を 1 field 追加**  
   sub-object (`ReflectionOutcome { event, fell_back }`) は作らない。
   `None` であることが「発火しなかった / 失敗した」の両方を表現。
   どちらか区別したいときは logs / `Reflector.last_failure` で追える
   (本 PR では後者は追加しない; YAGNI)。

5. **Reflector 内部で failure を握りつぶす**  
   `OllamaUnavailableError` / `EmbeddingUnavailableError` を Reflector 内で
   catch、`logger.warning` を出して `return None`。CognitionCycle の fallback
   path は reflection を一切知らない。既存 `llm_fell_back` (action 選択の
   LLM 失敗) とは独立に observe できる。

6. **prompt は `cognition/reflection.py` に完結させる**  
   `build_system_prompt` / `build_user_prompt` (action 用) は一切触らない。
   reflection 専用の `build_reflection_messages(persona, agent, episodic)`
   を新規実装し、reflection 特有の指示 (短い要約 / 第三者視点 /
   哲学的トーン) を固有 prompt として与える。

7. **summary は LLM 応答の plain text をそのまま格納**  
   JSON schema を強制しない (失敗率が上がり、reflection の主目的は保存
   可能な自然文の要約)。embedding に食わせるだけなので text であれば
   何でも良い。LLM 応答が空ならその tick は None。

8. **発火タイミングは step の末尾**  
   step 1 で書いた新 episodic も要約対象に入るよう、envelope 作成後に
   reflection を回す。LLM 2 回呼び出しのレイテンシは #6 の acceptance
   で計測するが、現 tick は 10s なので余裕。

### 既存コードとの整合性

- **既存 `_REFLECTION_ZONES` / `_detect_zone_entry`**: Reflector 側に
  policy として移植 (cycle.py からは削除)。zone 判定 helper のみ
  残す (他の用途がない場合は reflection.py に移動)。
- **既存 `REFLECTION_IMPORTANCE_THRESHOLD` ClassVar**: 互換のため残すが
  default `ReflectionPolicy.importance_threshold` にその値を引き継ぐ。
- **`CycleResult`**: 新 field 追加のみ。既存 test は変更不要。
- **`reflection_triggered: bool`**: 残す。意味は「trigger が立ったかどうか」
  (actual reflection_event の有無とは独立。LLM 失敗で event=None でも
  trigger=True になる、という観察可能性の 2 軸に分離)。

### コード配置

| ファイル | 変更 |
|---|---|
| `src/erre_sandbox/cognition/reflection.py` | **新規** — ReflectionPolicy / Reflector / build_reflection_messages |
| `src/erre_sandbox/cognition/cycle.py` | 編集 — reflector 注入 + step 末尾で呼び出し、CycleResult 拡張 |
| `src/erre_sandbox/cognition/__init__.py` | 編集 — Reflector / ReflectionPolicy を export |
| `tests/test_cognition/test_reflection.py` | **新規** — Reflector 単体テスト |
| `tests/test_cognition/test_cycle.py` | 編集 — 既存テスト継続、reflection_event 確認 1 本追加 |
| `tests/test_cognition/conftest.py` | 編集 — FakeReflector / ReflectionPolicy(test) fixture |
| `docs/architecture.md` §Cognition | 編集 — 反省層を図に追加 |

## 変更対象ファイル

### 新規作成
- `src/erre_sandbox/cognition/reflection.py`
- `tests/test_cognition/test_reflection.py`

### 修正
- `src/erre_sandbox/cognition/cycle.py`
- `src/erre_sandbox/cognition/__init__.py`
- `tests/test_cognition/test_cycle.py`
- `tests/test_cognition/conftest.py`
- `docs/architecture.md`

### 削除
なし

## 既存パターンとの整合性

- **Collaborator injection** (M2 cognition cycle が `retriever/store/embedding/llm`
  を全て injection しているのと同形式)
- **Pure policy object** (cognition/importance.py の `estimate_importance`
  と同じく「ルールは関数/dataclass」スタイル)
- **failure swallowing at boundary** (M2 `_retrieve_safely` で
  Unavailable を握り潰すのと同じパターン)
- **`__init__.py` exports for public surface** (既存 cognition パッケージの慣習)

## テスト戦略

### Reflector 単体 (`test_reflection.py`)
- `test_policy_should_fire_when_tick_interval_elapsed`
- `test_policy_should_fire_on_importance_threshold_exceeded`
- `test_policy_should_fire_on_reflective_zone_entry`
- `test_policy_should_not_fire_when_all_triggers_inactive`
- `test_reflector_persists_semantic_memory_on_success`
- `test_reflector_returns_none_on_ollama_unavailable`
- `test_reflector_returns_none_on_embedding_unavailable`
- `test_reflector_skips_when_no_episodic_memories`
- `test_reflector_resets_tick_counter_after_fire`
- `test_reflector_respects_per_agent_counter_isolation` (2 agents)
- `test_reflector_stored_record_is_recallable_via_recall_semantic`
  (受け入れ条件「recall_semantic で top-1」を端末で検証)

### CognitionCycle 統合 (`test_cycle.py`)
- `test_step_surfaces_reflection_event_when_reflector_fires` — FakeReflector で
  任意 event を返す → CycleResult に渡っている確認
- 既存テスト継続 PASS (N=446 — reflection_event デフォルト None を受け入れ)

### 既存テスト影響
- `reflection_triggered=True` を assert するテスト (zone entry / importance)
  は Reflector に移植後も policy で同条件を満たすので継続 PASS

## ロールバック計画

1 PR にまとめる。問題あれば PR revert で `cycle.py` / `schemas.py` 両方を
元に戻せる。DB スキーマは触らないため migration なし。新規 file は
revert 対象 (`reflection.py` / `test_reflection.py`)。

## 受け入れ条件との対応

| 受け入れ条件 | v2 での満たし方 |
|---|---|
| N tick で発火 | Reflector 内 per-agent counter ≥ policy.tick_interval |
| 既存条件継続 PASS | ReflectionPolicy が同条件を包含 |
| semantic_memory 行追加 | Reflector が `upsert_semantic` 呼び出し |
| recall_semantic top-1 | `test_reflector_stored_record_is_recallable_via_recall_semantic` |
| LLM timeout で cycle 壊れない | Reflector が catch し None を返す |
| embedding 空時 vec skip | #3 D7 の store 側挙動を継承 (Reflector は素直に渡すだけ) |
| 既存 446 PASS | 既存シグネチャ無破壊 + default reflector 経路 |
| CycleResult 破壊的変更なし | 新 field のみ追加 (default=None) |
| 非発火 tick で None | Reflector.maybe_reflect が None を返す |
| docs/architecture.md | reflection 層を図に追加 |

## 設計判断の履歴

- 初回案 (`design-v1.md`: inline step 10 + ClassVar policy) を生成
- `/reimagine` で意図的リセットし、v2 (Reflector collaborator +
  ReflectionPolicy pure object + per-agent counter) を再生成
- `design-comparison.md` で 13 観点比較
- **採用: v2 + hybrid (v1 の `REFLECTION_IMPORTANCE_THRESHOLD` ClassVar 互換保持のみ継承)**
- 根拠:
  1. #6 multi-agent orchestrator との接続で v1 の `tick % N` が破綻リスク、
     v2 の per-agent counter は multi-agent でそのまま通用
  2. M2 injection パターン (`retriever/store/embedding/llm` 全て inject) に忠実
  3. reflection 単体テストが 11 本書け、policy / failure-swallow / recall
     の各軸を独立に網羅できる (v1 は統合テストのみで間接)
  4. auto mode 委任による即時判断。曖昧ポイントは実装時に decisions.md
     で追記
