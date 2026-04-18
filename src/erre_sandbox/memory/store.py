"""sqlite-vec backed memory store with kind-specific content tables.

See ``.steering/20260418-memory-store/design.md`` §3.1. The wire type
``schemas.MemoryEntry`` is pure domain and does **not** carry an embedding;
this module attaches the embedding in a shared ``vec0`` virtual table keyed
by ``memory_id``.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import struct
from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar, Final

import sqlite_vec

from erre_sandbox.schemas import MemoryEntry, MemoryKind

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

DEFAULT_EMBED_DIM: Final[int] = 768
"""Default embedding dimension (nomic-embed-text-v1.5 produces 768-d vectors)."""

_KIND_TO_TABLE: Final[dict[MemoryKind, str]] = {
    MemoryKind.EPISODIC: "episodic_memory",
    MemoryKind.SEMANTIC: "semantic_memory",
    MemoryKind.PROCEDURAL: "procedural_memory",
    MemoryKind.RELATIONAL: "relational_memory",
}

_SHARED_COLUMNS: Final[tuple[str, ...]] = (
    "id",
    "agent_id",
    "content",
    "importance",
    "created_at",
    "last_recalled_at",
    "recall_count",
    "tags",
)


class MemoryStore:
    """Persistence layer for the 4-faculty memory model.

    The 4 memory kinds (``EPISODIC`` / ``SEMANTIC`` / ``PROCEDURAL`` /
    ``RELATIONAL``) live in their own tables with a minimal kind-specific
    schema; a single ``vec_embeddings`` virtual table stores 768-dim
    vectors keyed by ``memory_id`` and is joined at retrieval time.

    All write operations are asynchronous (``asyncio.to_thread`` wraps the
    blocking sqlite3 calls) so this store can be used inside an asyncio
    event loop without starving other coroutines.
    """

    VEC_TABLE: ClassVar[str] = "vec_embeddings"

    def __init__(
        self,
        db_path: Path | str = ":memory:",
        *,
        embed_dim: int = DEFAULT_EMBED_DIM,
    ) -> None:
        self._db_path = str(db_path)
        self._embed_dim = embed_dim
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def _ensure_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            # ``check_same_thread=False`` is required because ``asyncio.to_thread``
            # dispatches sync DB calls onto a worker pool; we serialise access
            # at the async layer (callers await before re-entering) so the
            # underlying sqlite3 library's thread-safe mode is sufficient.
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.enable_load_extension(True)  # noqa: FBT003 — sqlite3 stdlib API
            sqlite_vec.load(conn)
            conn.row_factory = sqlite3.Row
            self._conn = conn
        return self._conn

    def create_schema(self) -> None:
        """Create the 4 content tables and the shared ``vec0`` table.

        Idempotent via ``IF NOT EXISTS``; safe to call on each startup.
        """
        conn = self._ensure_conn()
        with conn:
            # Episodic: observations / perceptions — has source_observation_id.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episodic_memory (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    last_recalled_at TEXT,
                    recall_count INTEGER NOT NULL DEFAULT 0,
                    source_observation_id TEXT,
                    tags TEXT NOT NULL DEFAULT '[]'
                )
                """,
            )
            # Semantic: beliefs / themes (distilled by reflection in M4).
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    last_recalled_at TEXT,
                    recall_count INTEGER NOT NULL DEFAULT 0,
                    tags TEXT NOT NULL DEFAULT '[]'
                )
                """,
            )
            # Procedural: zone/ritual-keyed skills (rich logic deferred to M5).
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS procedural_memory (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    zone TEXT,
                    procedure_name TEXT,
                    content TEXT NOT NULL,
                    importance REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    last_recalled_at TEXT,
                    recall_count INTEGER NOT NULL DEFAULT 0,
                    tags TEXT NOT NULL DEFAULT '[]'
                )
                """,
            )
            # Relational: interaction episodes (AgentState.relationships is
            # the dynamic source of truth; this table archives the history).
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS relational_memory (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    other_agent_id TEXT,
                    content TEXT NOT NULL,
                    importance REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    last_recalled_at TEXT,
                    recall_count INTEGER NOT NULL DEFAULT 0,
                    tags TEXT NOT NULL DEFAULT '[]'
                )
                """,
            )
            # Shared vec0 virtual table.
            conn.execute(
                f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {self.VEC_TABLE}
                USING vec0(
                    memory_id TEXT PRIMARY KEY,
                    embedding float[{self._embed_dim}]
                )
                """,
            )

    async def close(self) -> None:
        if self._conn is not None:
            conn = self._conn
            self._conn = None
            await asyncio.to_thread(conn.close)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def add(
        self,
        entry: MemoryEntry,
        embedding: list[float] | None = None,
    ) -> str:
        """Insert ``entry`` into its kind-specific table.

        If ``embedding`` is provided, also insert into ``vec_embeddings``.
        Returns the entry id (passthrough for convenience).
        """
        if embedding is not None and len(embedding) != self._embed_dim:
            raise ValueError(
                f"Embedding dim {len(embedding)} != store dim {self._embed_dim}",
            )
        return await asyncio.to_thread(self._add_sync, entry, embedding)

    def _add_sync(
        self,
        entry: MemoryEntry,
        embedding: list[float] | None,
    ) -> str:
        conn = self._ensure_conn()
        with conn:
            if entry.kind is MemoryKind.EPISODIC:
                conn.execute(
                    "INSERT INTO episodic_memory("
                    "id, agent_id, content, importance, created_at, "
                    "last_recalled_at, recall_count, source_observation_id, tags"
                    ") VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        entry.id,
                        entry.agent_id,
                        entry.content,
                        entry.importance,
                        _dt_to_text(entry.created_at),
                        _dt_to_text_opt(entry.last_recalled_at),
                        entry.recall_count,
                        entry.source_observation_id,
                        json.dumps(entry.tags, ensure_ascii=False),
                    ),
                )
            elif entry.kind is MemoryKind.SEMANTIC:
                conn.execute(
                    "INSERT INTO semantic_memory("
                    "id, agent_id, content, importance, created_at, "
                    "last_recalled_at, recall_count, tags"
                    ") VALUES (?,?,?,?,?,?,?,?)",
                    (
                        entry.id,
                        entry.agent_id,
                        entry.content,
                        entry.importance,
                        _dt_to_text(entry.created_at),
                        _dt_to_text_opt(entry.last_recalled_at),
                        entry.recall_count,
                        json.dumps(entry.tags, ensure_ascii=False),
                    ),
                )
            elif entry.kind is MemoryKind.PROCEDURAL:
                conn.execute(
                    "INSERT INTO procedural_memory("
                    "id, agent_id, content, importance, created_at, "
                    "last_recalled_at, recall_count, tags"
                    ") VALUES (?,?,?,?,?,?,?,?)",
                    (
                        entry.id,
                        entry.agent_id,
                        entry.content,
                        entry.importance,
                        _dt_to_text(entry.created_at),
                        _dt_to_text_opt(entry.last_recalled_at),
                        entry.recall_count,
                        json.dumps(entry.tags, ensure_ascii=False),
                    ),
                )
            elif entry.kind is MemoryKind.RELATIONAL:
                conn.execute(
                    "INSERT INTO relational_memory("
                    "id, agent_id, content, importance, created_at, "
                    "last_recalled_at, recall_count, tags"
                    ") VALUES (?,?,?,?,?,?,?,?)",
                    (
                        entry.id,
                        entry.agent_id,
                        entry.content,
                        entry.importance,
                        _dt_to_text(entry.created_at),
                        _dt_to_text_opt(entry.last_recalled_at),
                        entry.recall_count,
                        json.dumps(entry.tags, ensure_ascii=False),
                    ),
                )
            else:  # pragma: no cover — exhaustive via MemoryKind enum
                raise ValueError(f"Unknown kind: {entry.kind}")

            if embedding is not None:
                conn.execute(
                    f"INSERT INTO {self.VEC_TABLE}(memory_id, embedding) VALUES (?, ?)",  # noqa: S608
                    (entry.id, json.dumps(embedding)),
                )
        return entry.id

    async def mark_recalled(self, memory_ids: Sequence[str]) -> None:
        """Increment ``recall_count`` and set ``last_recalled_at`` = now."""
        if not memory_ids:
            return
        await asyncio.to_thread(self._mark_recalled_sync, list(memory_ids))

    def _mark_recalled_sync(self, memory_ids: list[str]) -> None:
        conn = self._ensure_conn()
        now = _dt_to_text(datetime.now(tz=UTC))
        placeholders = ",".join("?" * len(memory_ids))
        with conn:
            for table in _KIND_TO_TABLE.values():
                conn.execute(
                    f"UPDATE {table} "  # noqa: S608 — table from fixed map
                    "SET recall_count = recall_count + 1, "
                    "    last_recalled_at = ? "
                    f"WHERE id IN ({placeholders})",
                    (now, *memory_ids),
                )

    async def evict_episodic_before(
        self,
        agent_id: str,
        created_before: datetime,
    ) -> list[MemoryEntry]:
        """Remove and return episodic entries created before ``created_before``.

        Used by the M4 reflection loop (evict → LLM extract → Semantic).
        Evicting removes rows from both ``episodic_memory`` and the shared
        ``vec_embeddings`` table atomically.
        """
        return await asyncio.to_thread(
            self._evict_episodic_sync,
            agent_id,
            created_before,
        )

    def _evict_episodic_sync(
        self,
        agent_id: str,
        created_before: datetime,
    ) -> list[MemoryEntry]:
        conn = self._ensure_conn()
        cutoff = _dt_to_text(created_before)
        with conn:
            rows = conn.execute(
                "SELECT * FROM episodic_memory "
                "WHERE agent_id = ? AND created_at < ? "
                "ORDER BY created_at ASC",
                (agent_id, cutoff),
            ).fetchall()
            if not rows:
                return []
            ids = [r["id"] for r in rows]
            placeholders = ",".join("?" * len(ids))
            conn.execute(
                f"DELETE FROM episodic_memory WHERE id IN ({placeholders})",  # noqa: S608
                ids,
            )
            conn.execute(
                f"DELETE FROM {self.VEC_TABLE} WHERE memory_id IN ({placeholders})",  # noqa: S608
                ids,
            )
        return [_row_to_memory_entry(r, MemoryKind.EPISODIC) for r in rows]

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def get_by_id(self, memory_id: str) -> MemoryEntry | None:
        return await asyncio.to_thread(self._get_by_id_sync, memory_id)

    def _get_by_id_sync(self, memory_id: str) -> MemoryEntry | None:
        conn = self._ensure_conn()
        for kind, table in _KIND_TO_TABLE.items():
            row = conn.execute(
                f"SELECT * FROM {table} WHERE id = ?",  # noqa: S608
                (memory_id,),
            ).fetchone()
            if row is not None:
                return _row_to_memory_entry(row, kind)
        return None

    async def list_by_agent(
        self,
        agent_id: str,
        kind: MemoryKind,
        *,
        limit: int = 50,
    ) -> list[MemoryEntry]:
        return await asyncio.to_thread(self._list_by_agent_sync, agent_id, kind, limit)

    def _list_by_agent_sync(
        self,
        agent_id: str,
        kind: MemoryKind,
        limit: int,
    ) -> list[MemoryEntry]:
        conn = self._ensure_conn()
        table = _KIND_TO_TABLE[kind]
        rows = conn.execute(
            f"SELECT * FROM {table} "  # noqa: S608 — table from fixed map
            "WHERE agent_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (agent_id, limit),
        ).fetchall()
        return [_row_to_memory_entry(r, kind) for r in rows]

    async def list_world_scope(
        self,
        exclude_agent_id: str,
        kind: MemoryKind,
        *,
        limit: int = 50,
    ) -> list[MemoryEntry]:
        """Return memories from *other* agents (for world-scope retrieval)."""
        return await asyncio.to_thread(
            self._list_world_scope_sync,
            exclude_agent_id,
            kind,
            limit,
        )

    def _list_world_scope_sync(
        self,
        exclude_agent_id: str,
        kind: MemoryKind,
        limit: int,
    ) -> list[MemoryEntry]:
        conn = self._ensure_conn()
        table = _KIND_TO_TABLE[kind]
        rows = conn.execute(
            f"SELECT * FROM {table} "  # noqa: S608 — table from fixed map
            "WHERE agent_id != ? "
            "ORDER BY created_at DESC LIMIT ?",
            (exclude_agent_id, limit),
        ).fetchall()
        return [_row_to_memory_entry(r, kind) for r in rows]

    async def get_embedding(self, memory_id: str) -> list[float] | None:
        """Return the stored embedding for ``memory_id`` or ``None``."""
        return await asyncio.to_thread(self._get_embedding_sync, memory_id)

    def _get_embedding_sync(self, memory_id: str) -> list[float] | None:
        conn = self._ensure_conn()
        row = conn.execute(
            f"SELECT embedding FROM {self.VEC_TABLE} WHERE memory_id = ?",  # noqa: S608
            (memory_id,),
        ).fetchone()
        if row is None:
            return None
        raw = row["embedding"]
        if isinstance(raw, bytes):
            # sqlite-vec stores float32 little-endian; decode with struct.
            count = len(raw) // 4
            return list(struct.unpack(f"<{count}f", raw))
        if isinstance(raw, str):
            return [float(x) for x in json.loads(raw)]
        raise TypeError(f"Unexpected embedding payload type: {type(raw)!r}")

    async def knn_ids(
        self,
        query_embedding: list[float],
        *,
        k: int,
        candidate_ids: Iterable[str] | None = None,
    ) -> list[tuple[str, float]]:
        """Return ``(memory_id, distance)`` pairs sorted by ascending distance.

        If ``candidate_ids`` is given, restrict the KNN scan to that id set.
        ``distance`` is the L2 distance from ``vec_distance_l2`` (lower =
        more similar). ``k`` is capped at the candidate pool size.
        """
        if len(query_embedding) != self._embed_dim:
            raise ValueError(
                f"Query dim {len(query_embedding)} != store dim {self._embed_dim}",
            )
        restrict = list(candidate_ids) if candidate_ids is not None else None
        return await asyncio.to_thread(
            self._knn_ids_sync,
            query_embedding,
            k,
            restrict,
        )

    def _knn_ids_sync(
        self,
        query_embedding: list[float],
        k: int,
        restrict: list[str] | None,
    ) -> list[tuple[str, float]]:
        conn = self._ensure_conn()
        q_json = json.dumps(query_embedding)
        if restrict is None:
            rows = conn.execute(
                f"SELECT memory_id, distance FROM {self.VEC_TABLE} "  # noqa: S608
                "WHERE embedding MATCH ? AND k = ? ORDER BY distance",
                (q_json, k),
            ).fetchall()
        elif not restrict:
            return []
        else:
            placeholders = ",".join("?" * len(restrict))
            rows = conn.execute(
                f"SELECT memory_id, distance FROM {self.VEC_TABLE} "  # noqa: S608
                f"WHERE embedding MATCH ? AND k = ? AND memory_id IN ({placeholders}) "
                "ORDER BY distance",
                (q_json, k, *restrict),
            ).fetchall()
        return [(r["memory_id"], float(r["distance"])) for r in rows]


# =============================================================================
# Row → MemoryEntry helpers
# =============================================================================


def _row_to_memory_entry(row: sqlite3.Row, kind: MemoryKind) -> MemoryEntry:
    return MemoryEntry(
        id=row["id"],
        agent_id=row["agent_id"],
        kind=kind,
        content=row["content"],
        importance=row["importance"],
        created_at=_text_to_dt(row["created_at"]),
        last_recalled_at=_text_to_dt_opt(row["last_recalled_at"]),
        recall_count=row["recall_count"],
        source_observation_id=(
            row["source_observation_id"] if kind is MemoryKind.EPISODIC else None
        ),
        tags=json.loads(row["tags"]) if row["tags"] else [],
    )


def _dt_to_text(dt: datetime) -> str:
    return dt.isoformat()


def _dt_to_text_opt(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def _text_to_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _text_to_dt_opt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


__all__ = [
    "DEFAULT_EMBED_DIM",
    "MemoryStore",
]
