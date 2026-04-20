# m4-cognition-reflection

## 背景

M4 Critical Path の最終工程 (#5)。既存 `CognitionCycle` には reflection の
**トリガ検出** (`reflection_triggered: bool`) までは実装済だが、
**蒸留して semantic_memory に保存する実行部** は「M4+」マーカーのまま未実装。

前提として #3 (PR #45) で `MemoryStore.upsert_semantic` / `recall_semantic`
API が凍結済で、foundation (#1) で `SemanticMemoryRecord` / `ReflectionEvent`
Pydantic 型は freeze 済。本タスクはそれらを結線して「思考の沈殿」を完成させる。

## ゴール

1-tick の `CognitionCycle.step()` 内で、発火条件を満たした tick に限り:

1. 直近 episodic memory N 件を LLM で要約 (`summary_text`) に蒸留
2. `summary_text` を `embed_document` で埋め込む
3. `SemanticMemoryRecord` を組み立てて `store.upsert_semantic` で保存
4. `ReflectionEvent` を `CycleResult.reflection_event` に載せて返す

LLM / embedding は既存 client を再利用し、Ollama 未起動時は graceful degrade。
テストは LLM / embedding mock で完結し Ollama 不要。

## スコープ

### 含むもの
- `src/erre_sandbox/cognition/cycle.py` への reflection 実行ロジック追加
- 発火条件の確定: 既存条件 (importance_sum / zone entry) + **N tick ごと** (default 10)
- `CycleResult` への `reflection_event: ReflectionEvent | None` 追加
- `src/erre_sandbox/cognition/` 内での summarization prompt / parser
  (新規 `reflection.py` に分離予定、/reimagine で最終決定)
- `tests/test_cognition/test_cycle.py` への reflection パステスト追加
- `docs/architecture.md` §Cognition への追記

### 含まないもの
- `semantic_memory` テーブルや DB スキーマへの変更 (#3 で凍結済)
- `Retriever` の semantic 統合 (#3 decisions D10 で見送り決定済)
- Multi-agent orchestrator との合流 (#6 の担当)
- Ollama `/api/chat` の fallback 実装 (既存の OllamaUnavailableError ハンドリング継承)
- SCHEMA_VERSION bump (`0.2.0-m4` のまま)
- live 検証 (G-GEAR / dashboard 経由) — #6 の acceptance に含まれる

## 受け入れ条件

- [ ] N tick (default 10) 経過時に reflection が発火する unit test
- [ ] importance_sum 閾値超過 / zone 入室でも発火する既存 test を継続 PASS
- [ ] 発火時に `semantic_memory` に 1 行追加され、`origin_reflection_id` が一致
- [ ] `recall_semantic` で保存した row が top-1 で返る end-to-end unit test (mock embedding)
- [ ] LLM タイムアウト時に既存 fallback と同じ safety 動作 (cycle は壊れない)
- [ ] embedding 空時は row だけ作り vec_embeddings を skip (#3 D7 との整合)
- [ ] 既存 pytest 446 PASS 継続 / ruff クリーン
- [ ] `CycleResult` の既存 field に破壊的変更なし (新 field のみ追加)
- [ ] `reflection_event is None` のデフォルト経路が非発火 tick でちゃんと使われる
- [ ] docs/architecture.md §Cognition に反映

## 関連ドキュメント

- `.steering/20260420-m4-planning/design.md` §m4-cognition-reflection
- `.steering/20260420-m4-memory-semantic-layer/decisions.md` (D10 `Retriever` 拡張は見送り)
- `.steering/20260418-implementation-plan/MASTER-PLAN.md` §5.1
- `src/erre_sandbox/cognition/cycle.py` (拡張対象)
- `src/erre_sandbox/memory/store.py` (`upsert_semantic` / `recall_semantic`)
- `src/erre_sandbox/schemas.py` §6 (`ReflectionEvent` / `SemanticMemoryRecord`)
- `docs/architecture.md` §Cognition (更新対象)

## 運用メモ

- 破壊と構築（/reimagine）適用: **Yes**
- 理由: 発火条件の複合方式 (N tick 追加の挿入位置・ゲート論理)、
  reflection 実行の配置 (cycle.step 内 inline / CognitionCycle 外へ helper 抽出 /
  `ReflectionRunner` 新設)、`CycleResult` への拡張方式 (optional field /
  sub-object)、LLM 蒸留の prompt 戦略 (system-prompt 再利用 / reflection 専用)
  に複数案があり、公開シグネチャ (`CycleResult` field) を凍結する前に
  破壊と構築を通す価値が高い。handoff メモ `/reimagine 適用` 明記済。
