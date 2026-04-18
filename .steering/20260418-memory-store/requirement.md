# T10 memory-store

## 背景

Contract Freeze (T08) により `schemas.MemoryEntry` (id / agent_id / kind / content / importance / created_at / last_recalled_at / recall_count / source_observation_id / tags) が wire 型として確定した。**埋め込みベクトルと検索スコアは意図的に MemoryEntry に含めず、memory-store (T10) の実装内部に閉じ込める**設計が採用されている (schemas.py §6 コメント)。この内部レイヤーを本タスクで初めて実装する。

記憶層は認知サイクル (T12) が毎 tick 呼び出す前提で、per-agent (top-8) + world-scope (top-3) の二層検索と、重要度 × 時間減衰 × recall 補正のランキングを提供する必要がある (docs/architecture.md §Memory Layer)。埋め込みモデルは T09 で `nomic-embed-text` (768 次元) を採用した (T09 decisions.md D2)。

また、MVP (M2) の段階では CSDG (B.5) から 2 層メモリ (ShortTerm↔Episodic / LongTerm↔Semantic) の役割分担を優先取り込みし、Procedural / Relational はスキーマ互換性だけを確保して最小実装に留める。

## ゴール

`src/erre_sandbox/memory/` 配下に以下を満たす実装を置く:

1. **`store.py`**: sqlite-vec を用いた 4 種記憶 (Episodic / Semantic / Procedural / Relational) の永続化。4 kind 分のコンテンツテーブルと共有の vec0 virtual table を持つ。`add(entry, embedding) -> id`, `get_by_id`, `list_by_agent`, `mark_recalled`, `evict_episodic_before` の最小 API を提供する。
2. **`embedding.py`**: Ollama `/api/embed` を叩く HTTP クライアント。`nomic-embed-text` 既定で 768 次元ベクトルを返す。接続不可時は `EmbeddingUnavailableError` を raise (error-handling Skill §fallback)。
3. **`retrieval.py`**: per-agent top-k (既定 8) と world-scope top-k (既定 3) を合成した `retrieve(agent_id, query, k_agent, k_world) -> list[MemoryEntry]`。スコア式は `importance * exp(-λ * age_days) * (1 + 0.2 * recall_count) * cosine_sim`、`λ` は config で可変 (既定 0.1)。副作用として `mark_recalled` を呼ぶ。
4. **tests**: `tests/test_memory/{__init__.py, test_store.py, test_embedding.py, test_retrieval.py}` で round-trip 書き込み/読み出し、4 kind 分離、埋め込み次元一致、減衰ランキング順、per-agent/world スコープ分離を検証。
5. **5 段緑維持**: `uv sync` / `ruff check` / `ruff format --check` / `mypy src` / `pytest` を全緑 (T09 時点 96 passed / 16 skipped + 今回追加で +10 前後)。

## スコープ

### 含むもの

- `src/erre_sandbox/memory/store.py` の新規実装 (sqlite-vec ラッパー、4 kind テーブル、vec0 virtual table)
- `src/erre_sandbox/memory/embedding.py` の新規実装 (Ollama `/api/embed` アダプタ、httpx ベース)
- `src/erre_sandbox/memory/retrieval.py` の新規実装 (2 層スコープ + 減衰ランキング)
- `src/erre_sandbox/memory/__init__.py` の更新 (public re-export: `MemoryStore`, `EmbeddingClient`, `Retriever`)
- `tests/test_memory/` の 4 ファイル追加 (pytest-asyncio 対応、sqlite-vec in-memory DB fixture)
- Conventional Commits で `feat(memory): T10 memory-store — sqlite-vec + 2-scope retrieval`
- 作業ブランチ `feature/memory-store` で push → PR
- CSDG 帰属の `NOTICE` 更新 (T08 で CSDG 帰属が既に追加済みなら差分なし、未なら B.7 に従い追記)

### 含まないもの

- **Reflection (記憶蒸留, evict→extract LLM 呼び出し)** → M4 `cognition-reflection` タスクで別実装。store.py には `evict_episodic_before()` までを提供、LLM 呼び出しは cognition/ 側
- **Relational memory の AgentState.relationships との同期ロジック** → T12 cognition-cycle で双方向同期設計、T10 ではテーブルスキーマのみ用意
- **Procedural memory の detect/trigger 実装** → M5 ERRE モード FSM と共に実装、T10 ではテーブルスキーマ + 素朴な `add/get` のみ
- **Qdrant / bge-m3 へのバックエンド切替** → M7 以降、`memory/` のバックエンド抽象化は M7 リファクタの範囲
- **LLM 推論呼び出し** (T11 `inference-ollama-adapter`)
- **認知サイクル・tick loop** (T12 / T13)

## 受け入れ条件

- [ ] `src/erre_sandbox/memory/{store.py, embedding.py, retrieval.py}` が作成され、`architecture-rules` の依存方向 (`memory/ → schemas.py のみ`) を守る
- [ ] `MemoryStore.add()` → `MemoryStore.get_by_id()` の round-trip で `MemoryEntry` が意味等価で復元される (4 kind すべて)
- [ ] `vec0` virtual table に 768 次元ベクトルが insert され、`vec_distance_l2` での KNN 検索が sqlite レベルで動く
- [ ] `EmbeddingClient.embed("hello")` が 768 次元の `list[float]` を返す (実 Ollama 到達または mock で)
- [ ] `Retriever.retrieve()` が `k_agent + k_world` 件以内で、減衰ランキング順にソートされた結果を返す
- [ ] `Retriever.retrieve()` が呼ばれると `recall_count` が +1 され `last_recalled_at` が更新される
- [ ] `tests/test_memory/` の新規テストがすべて pass、既存 96 tests に対する regression がない
- [ ] `ruff check` / `ruff format --check` / `mypy src` / `pytest` 全緑
- [ ] `.steering/20260418-memory-store/tasklist.md` が全チェック済み
- [ ] `.steering/_setup-progress.md` の Phase 8 で T10 が `[x]` に更新され、採用スキーマと行数が記録される
- [ ] `feature/memory-store` を push、PR 作成 (gh 導入後 or GitHub Web UI)

## 関連ドキュメント

- `.steering/20260418-implementation-plan/MASTER-PLAN.md` §4.2 (T10 行), §11 (Critical Files), 付録 B.2 / B.5 (CSDG 2 層メモリ)
- `docs/architecture.md` §Memory Layer, §4 Memory Stream, §8 拡張ポイント (将来 Qdrant 切替)
- `docs/repository-structure.md` §1 / §4 (memory/ レイヤー配置と依存方向)
- `src/erre_sandbox/schemas.py` §6 (MemoryEntry / MemoryKind — 本タスクの Contract 正典)
- `.claude/skills/architecture-rules/SKILL.md` (memory/ → schemas のみルール)
- `.claude/skills/python-standards/SKILL.md` (asyncio / Pydantic v2 / ruff ALL)
- `.claude/skills/test-standards/SKILL.md` (pytest-asyncio / conftest / 埋め込みプレフィックステスト)
- `.claude/skills/error-handling/SKILL.md` (Ollama 接続不可時の fallback)
- 外部参照: CSDG `csdg/engine/memory.py` (B.2 2 層構造、`window_size=3`, `beliefs≤10` 等の定数、付録 B.3)

## 運用メモ

- 破壊と構築 (`/reimagine`) 適用: **Yes**
- 理由: 記憶スキーマの切り方 (単一テーブル vs kind 別テーブル)、decay 式の持たせ方 (DB カラム vs 計算関数)、埋め込み統合 (vec0 同居 vs 別テーブル FK) に複数選択肢があり、設計段階で 2 案比較してから実装する価値が高い。→ `design.md §2` に v1/v2 比較と採用案を記録済み。
- タスク種類: 新機能追加 (`/add-feature` 準拠) → 本セッションでは設計段階まで、実装は次セッションで開始
