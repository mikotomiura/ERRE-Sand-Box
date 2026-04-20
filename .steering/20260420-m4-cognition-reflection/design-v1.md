# 設計 — m4-cognition-reflection (v1 草案)

> **status**: v1 (/reimagine で破棄予定)

## 実装アプローチ

`CognitionCycle.step()` の終盤に新 step 「10. Reflection execution」を追加し、
既存の 9 step を壊さず上乗せする。既存の `reflection_triggered` 検出ロジック
は再利用し、発火条件に「N tick ごと」を OR 合流させる。LLM 蒸留と
埋め込みは inline で行う (新 helper 抽出はしない)。

### 変更点サマリ

1. `CognitionCycle` 定数追加:
   - `REFLECTION_TICK_INTERVAL: ClassVar[int] = 10`
   - `REFLECTION_EPISODIC_WINDOW: ClassVar[int] = 10`
2. `CycleResult` に field 追加:
   - `reflection_event: ReflectionEvent | None = None`
3. 発火条件 (`_detect_reflection_trigger`) を拡張:

   ```python
   triggered = (
       importance_sum > THRESHOLD
       or entered_reflective_zone
       or (tick > 0 and tick % REFLECTION_TICK_INTERVAL == 0)
   )
   ```

4. step の step 9 の後に step 10 を追加:
   - episodic を直近 N 件 `list_by_agent` で取得
   - reflection 用 prompt を `prompting.py` に新 function で追加
   - `self._llm.chat` で蒸留
   - `self._embedding.embed_document(summary)` で埋め込み
   - `SemanticMemoryRecord` + `ReflectionEvent` 構築
   - `self._store.upsert_semantic(record)`
5. LLM / embedding 失敗時は `reflection_event=None` で続行 (cycle 全体は壊さない)
6. `tests/test_cognition/test_cycle.py` に test 3 本追加
   (N-tick 発火 / semantic 保存確認 / LLM unavailable 時)
7. `docs/architecture.md` §Cognition に step 10 追記

### コード配置

- `src/erre_sandbox/cognition/cycle.py` — step 10 本体 + constants
- `src/erre_sandbox/cognition/prompting.py` — `build_reflection_prompt`
- `src/erre_sandbox/cognition/parse.py` — 変更なし (summary はプレーン text)

## 変更対象ファイル

- `src/erre_sandbox/cognition/cycle.py`
- `src/erre_sandbox/cognition/prompting.py`
- `tests/test_cognition/test_cycle.py`
- `docs/architecture.md`

## 影響範囲

- `CycleResult.reflection_event` の追加 (後方互換: default `None`)
- `reflection_triggered` の意味が拡張 (tick 周期も発火源になる)
- 既存 `test_cycle.py` の reflection-triggered テストは tick=0 前提のため影響なし
  (tick=0 では tick % 10 == 0 だが `tick > 0` ガードで除外)

## テスト戦略

既存 mock (`make_chat_client` / `make_embedding_client` / `cognition_store`)
を使い Ollama 不要で完結。

- `test_reflection_fires_every_n_ticks`: tick=10 で発火、tick=9 で非発火
- `test_reflection_writes_semantic_memory`: 発火時に `semantic_memory` に row 追加
- `test_reflection_gracefully_skips_on_llm_error`: LLM 404 時に cycle は継続、
  `reflection_event=None`
- `test_reflection_embedding_attached`: `recall_semantic` で top-1 hit

## ロールバック計画

1 PR で変更、問題あれば PR revert。schema / DB は触らないので migration なし。

## 未解決の論点 (/reimagine で検討したい)

1. **reflection の実行位置**: step 10 inline / cycle.step 外に抽出 / 専用
   `ReflectionRunner` 新設 — どれが責務分離として妥当か
2. **発火条件の OR 合流 vs 階層化**: 全条件 OR で 1 tick に複数発火源が
   重なる時の扱い (dedup 不要?)
3. **CycleResult の拡張形状**: `reflection_event: ReflectionEvent | None` 1 field か、
   新 sub-object `ReflectionOutcome` を作るか
4. **prompt 戦略**: 既存 `build_system_prompt` の再利用か reflection 専用か
5. **summary の parse**: LLM 応答を生 text のまま `summary_text` にするか、
   JSON schema を強制するか
6. **LLM / embedding 失敗時の観測性**: `llm_fell_back` と別の flag
   (`reflection_fell_back`) を追加するか
7. **episodic の選び方**: created_at 降順 limit N / tick を横切らない window /
   importance でフィルタ
