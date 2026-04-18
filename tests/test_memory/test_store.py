"""Unit tests for :mod:`erre_sandbox.memory.store`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from erre_sandbox.schemas import MemoryKind

if TYPE_CHECKING:
    from collections.abc import Callable

    from erre_sandbox.memory.store import MemoryStore
    from erre_sandbox.schemas import MemoryEntry


# ---------------------------------------------------------------------------
# Round-trip per kind
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", list(MemoryKind))
async def test_add_get_roundtrip_each_kind(
    store: MemoryStore,
    make_entry: Callable[..., MemoryEntry],
    unit_embedding: list[float],
    kind: MemoryKind,
) -> None:
    entry = make_entry(
        kind=kind,
        content=f"content for {kind.value}",
        importance=0.4,
        tags=["alpha", "beta"],
        source_observation_id="obs-1" if kind is MemoryKind.EPISODIC else None,
    )

    returned_id = await store.add(entry, embedding=unit_embedding)
    assert returned_id == entry.id

    fetched = await store.get_by_id(entry.id)
    assert fetched is not None
    assert fetched.id == entry.id
    assert fetched.kind is kind
    assert fetched.agent_id == entry.agent_id
    assert fetched.content == entry.content
    assert fetched.importance == pytest.approx(entry.importance)
    assert fetched.recall_count == 0
    assert fetched.last_recalled_at is None
    assert fetched.tags == ["alpha", "beta"]
    if kind is MemoryKind.EPISODIC:
        assert fetched.source_observation_id == "obs-1"
    else:
        assert fetched.source_observation_id is None


async def test_add_without_embedding_does_not_insert_vec(
    store: MemoryStore,
    make_entry: Callable[..., MemoryEntry],
) -> None:
    entry = make_entry(kind=MemoryKind.EPISODIC)
    await store.add(entry, embedding=None)
    assert await store.get_embedding(entry.id) is None


async def test_add_rejects_wrong_dim(
    store: MemoryStore,
    make_entry: Callable[..., MemoryEntry],
) -> None:
    entry = make_entry()
    with pytest.raises(ValueError, match="Embedding dim"):
        await store.add(entry, embedding=[0.1] * 10)


# ---------------------------------------------------------------------------
# vec0 KNN
# ---------------------------------------------------------------------------


async def test_vec_knn_returns_closest_first(
    store: MemoryStore,
    make_entry: Callable[..., MemoryEntry],
) -> None:
    close = make_entry(kind=MemoryKind.EPISODIC, content="close")
    far = make_entry(kind=MemoryKind.EPISODIC, content="far")
    close_vec = [1.0] + [0.0] * 767
    far_vec = [0.0, 1.0] + [0.0] * 766
    query = [0.99, 0.01] + [0.0] * 766

    await store.add(close, embedding=close_vec)
    await store.add(far, embedding=far_vec)

    hits = await store.knn_ids(query, k=2)
    assert len(hits) == 2
    assert hits[0][0] == close.id
    assert hits[0][1] <= hits[1][1]


async def test_vec_knn_respects_candidate_restriction(
    store: MemoryStore,
    make_entry: Callable[..., MemoryEntry],
    unit_embedding: list[float],
) -> None:
    e1 = make_entry(content="one")
    e2 = make_entry(content="two")
    await store.add(e1, embedding=unit_embedding)
    await store.add(e2, embedding=unit_embedding)

    hits = await store.knn_ids(unit_embedding, k=2, candidate_ids=[e1.id])
    assert [mid for mid, _ in hits] == [e1.id]


# ---------------------------------------------------------------------------
# List / mark_recalled / evict
# ---------------------------------------------------------------------------


async def test_list_by_agent_filters_and_orders(
    store: MemoryStore,
    make_entry: Callable[..., MemoryEntry],
) -> None:
    now = datetime.now(tz=UTC)
    old = make_entry(
        agent_id="kant",
        kind=MemoryKind.EPISODIC,
        content="old",
        created_at=now - timedelta(days=2),
    )
    new = make_entry(
        agent_id="kant",
        kind=MemoryKind.EPISODIC,
        content="new",
        created_at=now,
    )
    other = make_entry(
        agent_id="nietzsche",
        kind=MemoryKind.EPISODIC,
        content="other",
        created_at=now,
    )
    for e in (old, new, other):
        await store.add(e, embedding=None)

    results = await store.list_by_agent("kant", MemoryKind.EPISODIC)
    assert [r.content for r in results] == ["new", "old"]
    assert all(r.agent_id == "kant" for r in results)


async def test_list_world_scope_excludes_self(
    store: MemoryStore,
    make_entry: Callable[..., MemoryEntry],
) -> None:
    mine = make_entry(agent_id="kant", content="mine")
    theirs = make_entry(agent_id="nietzsche", content="theirs")
    await store.add(mine, embedding=None)
    await store.add(theirs, embedding=None)

    results = await store.list_world_scope("kant", MemoryKind.EPISODIC)
    assert [r.agent_id for r in results] == ["nietzsche"]


async def test_mark_recalled_updates_all_tables(
    store: MemoryStore,
    make_entry: Callable[..., MemoryEntry],
) -> None:
    ep = make_entry(kind=MemoryKind.EPISODIC, content="ep")
    se = make_entry(kind=MemoryKind.SEMANTIC, content="se")
    await store.add(ep, embedding=None)
    await store.add(se, embedding=None)

    await store.mark_recalled([ep.id, se.id])

    ep_after = await store.get_by_id(ep.id)
    se_after = await store.get_by_id(se.id)
    assert ep_after is not None
    assert se_after is not None
    assert ep_after.recall_count == 1
    assert se_after.recall_count == 1
    assert ep_after.last_recalled_at is not None
    assert se_after.last_recalled_at is not None


async def test_mark_recalled_noop_on_empty(
    store: MemoryStore,
) -> None:
    # Should not raise.
    await store.mark_recalled([])


async def test_evict_episodic_before_returns_and_deletes(
    store: MemoryStore,
    make_entry: Callable[..., MemoryEntry],
    unit_embedding: list[float],
) -> None:
    now = datetime.now(tz=UTC)
    old = make_entry(
        agent_id="kant",
        kind=MemoryKind.EPISODIC,
        content="old",
        created_at=now - timedelta(hours=2),
    )
    fresh = make_entry(
        agent_id="kant",
        kind=MemoryKind.EPISODIC,
        content="fresh",
        created_at=now,
    )
    semantic = make_entry(
        agent_id="kant",
        kind=MemoryKind.SEMANTIC,
        content="should not be evicted",
        created_at=now - timedelta(hours=3),
    )
    for e in (old, fresh, semantic):
        await store.add(e, embedding=unit_embedding)

    evicted = await store.evict_episodic_before(
        "kant",
        created_before=now - timedelta(hours=1),
    )
    assert [e.id for e in evicted] == [old.id]

    # ``old`` should be gone from both content and vec tables.
    assert await store.get_by_id(old.id) is None
    assert await store.get_embedding(old.id) is None
    # ``fresh`` (episodic, newer) and ``semantic`` must survive.
    assert await store.get_by_id(fresh.id) is not None
    assert await store.get_by_id(semantic.id) is not None


async def test_get_by_id_missing_returns_none(store: MemoryStore) -> None:
    assert await store.get_by_id("does-not-exist") is None
