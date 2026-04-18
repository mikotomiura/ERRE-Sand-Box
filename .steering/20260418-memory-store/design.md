# 設計

## 1. 実装アプローチ (採用版)

**kind 別テーブル + 共有 vec0 + 計算関数としての decay** を採用する。

- sqlite-vec の `vec0` virtual table を embedding 用に 1 つだけ作り、4 種類の kind ごとに content テーブルを分離する
- `(memory_id, embedding)` を vec0 に格納、content テーブルと `memory_id` で join
- decay はカラムに持たず、`retrieval.py` 内で `(importance, age_days, recall_count, cosine_sim)` から算出する関数として毎回計算
- Episodic / Semantic は MVP で実運用、Procedural / Relational は最小スキーマと `add/get` のみ

## 2. 破壊と構築 (Reimagine)

### 2.1 初回案 v1: 単一テーブル + embedding カラム同居

```sql
CREATE TABLE memory_entries (
  id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  kind TEXT NOT NULL,         -- Episodic / Semantic / Procedural / Relational
  content TEXT NOT NULL,
  importance REAL,
  created_at TEXT,
  last_recalled_at TEXT,
  recall_count INTEGER DEFAULT 0,
  source_observation_id TEXT,
  tags TEXT,                  -- JSON
  strength REAL,              -- 事前計算・定期更新
  embedding BLOB              -- 768 次元 float32
);
```

**弱点**:
- W1: 4 kind の検索パターンが違う (Episodic=近似検索、Semantic=構造検索、Procedural=key lookup、Relational=AgentState 複製) のに単一テーブルで妥協する
- W2: `strength` を DB カラムにすると更新漏れで rot (CSDG の半数式と同じ罠)
- W3: `embedding` を生 BLOB で持つと vec0 の近似検索が使えない (sqlite-vec の強みを捨てる)
- W4: Semantic memory の belief/theme はしばしば短文 + 構造化フィールドが欲しくなるが、content: TEXT で縛ると将来の struct 化が breaking change
- W5: Relational を単一テーブルに入れると AgentState.relationships と 2 SoT になる (Park et al. 2023 の推奨に反する)

### 2.2 再生成案 v2: kind 別テーブル + 共有 vec0 + 計算関数 decay

```sql
-- 4 kind の content テーブル (schema は kind 固有に最小化)
CREATE TABLE episodic_memory (
  id TEXT PRIMARY KEY, agent_id TEXT, content TEXT,
  importance REAL, created_at TEXT, last_recalled_at TEXT,
  recall_count INTEGER DEFAULT 0,
  source_observation_id TEXT, tags TEXT
);
CREATE TABLE semantic_memory (
  id TEXT PRIMARY KEY, agent_id TEXT,
  content TEXT,                     -- 短文の belief / theme
  importance REAL, created_at TEXT, last_recalled_at TEXT,
  recall_count INTEGER DEFAULT 0, tags TEXT
);
CREATE TABLE procedural_memory (
  id TEXT PRIMARY KEY, agent_id TEXT,
  zone TEXT,                        -- Zone enum
  procedure_name TEXT,              -- ritual name
  content TEXT,
  importance REAL, created_at TEXT, last_recalled_at TEXT,
  recall_count INTEGER DEFAULT 0, tags TEXT
);
CREATE TABLE relational_memory (
  id TEXT PRIMARY KEY, agent_id TEXT,
  other_agent_id TEXT,              -- FK semantic
  content TEXT,                     -- 具体エピソード (Relational memory は AgentState.relationships と異なる層)
  importance REAL, created_at TEXT, last_recalled_at TEXT,
  recall_count INTEGER DEFAULT 0, tags TEXT
);

-- 共有 vec0 virtual table (sqlite-vec)
CREATE VIRTUAL TABLE vec_embeddings USING vec0(
  memory_id TEXT PRIMARY KEY,
  embedding float[768]
);
```

**強み**:
- S1: kind ごとに最小かつ固有のスキーマ (将来の belief struct 化や zone key lookup が加えやすい)
- S2: `strength` は関数計算 (`retrieval.py::score()`)、DB に持たないので rot しない
- S3: `vec0` virtual table + `vec_distance_l2` で sqlite-vec の KNN を活用できる
- S4: Relational memory は AgentState.relationships (dynamic) と並走する「過去エピソード保存」層と明確化 → 2 SoT 矛盾を回避
- S5: kind 別で行数プロファイルが取りやすく、将来 Qdrant 移行時に Episodic だけ先に切替など段階的移行できる

**トレードオフ**:
- T1: 4 テーブル + 1 vec0 = 5 DDL → 初期セットアップが長い (mitigation: `create_schema()` 関数を 1 つ作って atomically 実行)
- T2: `list_by_agent(kind=None)` は UNION ALL 必要 → `list_by_agent(kind=X)` を primary API にし、混在検索は retrieval 層で合成する設計に倒す

### 2.3 判定

**v2 を採用**。決定根拠は `decisions.md` D1。

## 3. モジュール構成

### 3.1 `src/erre_sandbox/memory/store.py`

```python
# 公開 API
class MemoryStore:
    def __init__(self, db_path: Path | str = ":memory:") -> None: ...
    def create_schema(self) -> None: ...                                    # 初期化
    async def add(self, entry: MemoryEntry, embedding: list[float] | None) -> str: ...
    async def get_by_id(self, memory_id: str) -> MemoryEntry | None: ...
    async def list_by_agent(
        self, agent_id: str, kind: MemoryKind, limit: int = 50,
    ) -> list[MemoryEntry]: ...
    async def mark_recalled(self, memory_ids: list[str]) -> None: ...       # recall_count++, last_recalled_at=now
    async def evict_episodic_before(
        self, agent_id: str, tick_cutoff: int,
    ) -> list[MemoryEntry]: ...                                             # M4 reflection で使用
    async def close(self) -> None: ...
```

### 3.2 `src/erre_sandbox/memory/embedding.py`

```python
# 検索用と保存用で異なるプレフィックスを付与する (nomic-embed-text-v1.5 規約)。
# test-standards Skill §ルール 6 により、QUERY_PREFIX != DOC_PREFIX 検証は CI 必須。
QUERY_PREFIX: Final[str] = "search_query: "
DOC_PREFIX: Final[str]   = "search_document: "


class EmbeddingClient:
    DEFAULT_MODEL: ClassVar[str] = "nomic-embed-text"
    DEFAULT_DIM: ClassVar[int] = 768
    DEFAULT_ENDPOINT: ClassVar[str] = "http://127.0.0.1:11434"

    def __init__(self, model: str | None = None, endpoint: str | None = None) -> None: ...

    # 低レベル: プレフィックス無しで embed (明示利用のみ)
    async def embed(self, text: str) -> list[float]: ...

    # 高レベル: ユースケース別にプレフィックス付与 (Retriever から呼ぶ既定 API)
    async def embed_query(self, text: str) -> list[float]: ...     # QUERY_PREFIX 付与
    async def embed_document(self, text: str) -> list[float]: ...  # DOC_PREFIX 付与

    async def embed_many(
        self, texts: list[str], *, kind: Literal["query", "document"],
    ) -> list[list[float]]: ...
    async def close(self) -> None: ...


class EmbeddingUnavailableError(RuntimeError):
    """Raised when Ollama /api/embed is unreachable or returns malformed payload."""
```

### 3.3 `src/erre_sandbox/memory/retrieval.py`

```python
class Retriever:
    def __init__(
        self,
        store: MemoryStore,
        embedding: EmbeddingClient,
        *,
        decay_lambda: float = 0.1,   # half-life ≈ 7 days
        recall_boost: float = 0.2,
    ) -> None: ...

    async def retrieve(
        self,
        agent_id: str,
        query: str,
        *,
        k_agent: int = 8,
        k_world: int = 3,
        kinds: Sequence[MemoryKind] = (MemoryKind.EPISODIC, MemoryKind.SEMANTIC),
    ) -> list[MemoryEntry]: ...


def score(
    *, importance: float, age_days: float, recall_count: int, cosine_sim: float,
    decay_lambda: float = 0.1, recall_boost: float = 0.2,
) -> float:
    """strength = importance * exp(-λ * age_days) * (1 + β * recall_count) * cosine_sim"""
```

### 3.4 `src/erre_sandbox/memory/__init__.py`

```python
"""Memory subsystem (sqlite-vec backed) — depends on ``schemas`` only."""

from erre_sandbox.memory.embedding import EmbeddingClient, EmbeddingUnavailableError
from erre_sandbox.memory.retrieval import Retriever, score
from erre_sandbox.memory.store import MemoryStore

__all__ = [
    "EmbeddingClient",
    "EmbeddingUnavailableError",
    "MemoryStore",
    "Retriever",
    "score",
]
```

## 4. 変更対象

### 4.1 新規作成するファイル

- `src/erre_sandbox/memory/store.py` — 本タスクのコア (推定 300-400 行)
- `src/erre_sandbox/memory/embedding.py` — Ollama アダプタ + QUERY/DOC プレフィックス (推定 120-160 行)
- `src/erre_sandbox/memory/retrieval.py` — 2 層検索 + decay (推定 150-200 行)
- `tests/test_memory/__init__.py` (空)
- `tests/test_memory/conftest.py` — `in_memory_store` fixture, `fake_embedding` fixture
- `tests/test_memory/test_store.py` — round-trip, 4 kind 分離, vec0 KNN
- `tests/test_memory/test_embedding.py` — mock httpx で 768 次元 + プレフィックス送信検証
- `tests/test_memory/test_embedding_prefix.py` — プレフィックス一致テスト (test-standards §ルール 6 で CI 必須、削除禁止)
- `tests/test_memory/test_retrieval.py` — 減衰ランキング順、スコープ分離、recall_count 副作用

### 4.2 修正するファイル

- `src/erre_sandbox/memory/__init__.py` — 3 モジュールの public re-export に差し替え
- `.steering/_setup-progress.md` — Phase 8 の T10 を `[x]` に更新、採用スキーマと行数を記録

### 4.3 削除するファイル

なし。

## 5. 影響範囲

- `schemas.py` への変更は **ゼロ** (MemoryEntry は Contract 凍結済み)
- `inference/`, `cognition/`, `world/`, `ui/`, `erre/` に対する import 変更は **ゼロ** (まだ使用者なし、T11+ で順次呼び出される)
- `pyproject.toml` の依存は sqlite-vec と httpx が既に存在 (T04 で追加済み、`uv sync` ログで確認)
- テスト追加により `pytest` 件数が +10 前後 (96 → ~106)

## 6. 既存パターンとの整合性

- `architecture-rules` の依存方向厳守 (`memory/ → schemas.py のみ`)
- `python-standards`: `from __future__ import annotations`、snake_case、docstring 必須 (ruff ALL)
- `test-standards`: `pytest-asyncio` (`asyncio_mode=auto`)、`tests/test_memory/` ミラー構造、`conftest.py` で in-memory DB fixture
- `error-handling`: `EmbeddingUnavailableError` は raise、呼び出し側 (cognition/T12) で「embedding 無しで content 文字列検索に fallback」を実装
- `git-workflow`: Conventional Commits `feat(memory): ...`、`Refs: .steering/20260418-memory-store/` を本文に

## 7. テスト戦略

- **test_store.py** (単体):
  - `test_add_get_roundtrip_each_kind`: 4 kind 分について add → get_by_id の意味等価
  - `test_vec_embedding_knn`: 2 件 add、query ベクトルで KNN top-1 が正しい近傍を返す
  - `test_list_by_agent_scopes`: agent_id フィルタ、kind フィルタ、limit 正常動作
  - `test_mark_recalled_increments_counter`: recall_count++, last_recalled_at 更新
  - `test_evict_episodic_before_returns_and_removes`: tick_cutoff 前の Episodic のみ抽出、他 kind は残る
- **test_embedding.py** (単体 + mock):
  - `test_embed_returns_expected_dim`: httpx mock で 768 次元 float 列を返す
  - `test_embed_unreachable_raises`: Ollama ダウン時に `EmbeddingUnavailableError`
  - `test_embed_query_prepends_prefix`: `embed_query(text)` の送信 payload が `QUERY_PREFIX + text` 化
  - `test_embed_document_prepends_prefix`: `embed_document(text)` の送信 payload が `DOC_PREFIX + text` 化
- **test_embedding_prefix.py** (統合、test-standards §ルール 6 必須):
  - `test_query_and_doc_prefix_are_different`: `QUERY_PREFIX != DOC_PREFIX` を assert
  - `test_semantic_similarity_with_correct_prefix`: 関連 doc と無関連 doc の cosine_sim 差 ≥ 0.3
  - **このテストは削除・無効化禁止** (プレフィックスミスマッチは recall 5-15 ポイント劣化の典型)
- **test_retrieval.py** (統合):
  - `test_retrieve_decay_ranking`: 古い高 importance と 新しい低 importance の順序検証
  - `test_retrieve_agent_vs_world_split`: per-agent 8 + world 3 の件数分離
  - `test_retrieve_updates_recall_count`: retrieve の副作用
- **regression**: `uv run pytest` 全体が 96 passed を維持、memory 系テスト群が +10 前後加算

## 8. ロールバック計画

- DB 破壊時: `:memory:` 運用が中心なのでリセットは instance 再作成で十分。将来の永続 DB は `erre.db` を削除して `create_schema()` から再構築
- コード rollback: `git revert` 1 コミット分で完結 (T10 は 3 ファイル新規追加のみ、影響範囲最小)
- Embedding モデル変更 (将来 bge-m3 等): `EmbeddingClient.DEFAULT_MODEL` と `DEFAULT_DIM`、vec0 virtual table の `embedding float[N]` を書き換え → マイグレーション手順は `decisions.md` D3 に後続タスクで記録
