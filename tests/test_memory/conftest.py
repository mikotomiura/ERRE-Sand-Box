"""Fixtures for memory-subsystem tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from erre_sandbox.memory.store import MemoryStore
from erre_sandbox.schemas import MemoryEntry, MemoryKind

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable


@pytest.fixture
async def store() -> AsyncIterator[MemoryStore]:
    """In-memory :class:`MemoryStore` with the 4 tables + vec0 ready to use."""
    s = MemoryStore(db_path=":memory:")
    s.create_schema()
    try:
        yield s
    finally:
        await s.close()


@pytest.fixture
def make_entry() -> Callable[..., MemoryEntry]:
    """Factory returning a default :class:`MemoryEntry` for tests."""

    def _make(
        *,
        agent_id: str = "kant",
        kind: MemoryKind = MemoryKind.EPISODIC,
        content: str = "peripatos を歩く",
        importance: float = 0.5,
        created_at: datetime | None = None,
        recall_count: int = 0,
        source_observation_id: str | None = None,
        tags: list[str] | None = None,
    ) -> MemoryEntry:
        return MemoryEntry(
            id=str(uuid4()),
            agent_id=agent_id,
            kind=kind,
            content=content,
            importance=importance,
            created_at=created_at or datetime.now(tz=UTC),
            last_recalled_at=None,
            recall_count=recall_count,
            source_observation_id=source_observation_id,
            tags=tags or [],
        )

    return _make


@pytest.fixture
def unit_embedding() -> list[float]:
    """A deterministic length-768 vector for tests that don't need semantics."""
    return [0.01] * 768
