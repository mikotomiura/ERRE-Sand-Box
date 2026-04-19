"""Integration tests for :class:`CognitionCycle.step`."""

from __future__ import annotations

import json
from random import Random
from typing import TYPE_CHECKING, Any

import pytest

from erre_sandbox.cognition import CognitionCycle, CycleResult
from erre_sandbox.schemas import (
    AgentState,
    AgentUpdateMsg,
    ERREModeName,
    MemoryKind,
    MoveMsg,
    SpeechMsg,
    Zone,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from erre_sandbox.inference.ollama_adapter import OllamaChatClient
    from erre_sandbox.memory import EmbeddingClient, MemoryStore, Retriever
    from erre_sandbox.schemas import PerceptionEvent, PersonaSpec, ZoneTransitionEvent


def _build_cycle(
    *,
    retriever: Retriever,
    store: MemoryStore,
    embedding: EmbeddingClient,
    llm: OllamaChatClient,
) -> CognitionCycle:
    return CognitionCycle(
        retriever=retriever,
        store=store,
        embedding=embedding,
        llm=llm,
        rng=Random(0),
    )


async def test_step_happy_path_emits_envelopes(
    make_agent_state,
    make_persona_spec,
    make_chat_client: Callable[..., OllamaChatClient],
    make_embedding_client: Callable[[], EmbeddingClient],
    cognition_store: MemoryStore,
    cognition_retriever: Retriever,
    perception_event: PerceptionEvent,
) -> None:
    persona: PersonaSpec = make_persona_spec()
    agent: AgentState = make_agent_state()
    embedding = make_embedding_client()
    llm = make_chat_client()  # returns DEFAULT_PLAN
    try:
        cycle = _build_cycle(
            retriever=cognition_retriever,
            store=cognition_store,
            embedding=embedding,
            llm=llm,
        )
        result = await cycle.step(agent, persona, [perception_event])
    finally:
        await embedding.close()
        await llm.close()

    assert isinstance(result, CycleResult)
    assert not result.llm_fell_back
    kinds = [e.kind for e in result.envelopes]
    assert "agent_update" in kinds
    assert "speech" in kinds
    assert "move" in kinds
    assert "animation" in kinds

    # AgentUpdateMsg must always be present and tick bumped.
    agent_update = next(e for e in result.envelopes if isinstance(e, AgentUpdateMsg))
    assert agent_update.agent_state.tick == agent.tick + 1


async def test_step_writes_episodic_memory(
    make_agent_state,
    make_persona_spec,
    make_chat_client: Callable[..., OllamaChatClient],
    make_embedding_client: Callable[[], EmbeddingClient],
    cognition_store: MemoryStore,
    cognition_retriever: Retriever,
    perception_event: PerceptionEvent,
) -> None:
    embedding = make_embedding_client()
    llm = make_chat_client()
    try:
        cycle = _build_cycle(
            retriever=cognition_retriever,
            store=cognition_store,
            embedding=embedding,
            llm=llm,
        )
        result = await cycle.step(
            make_agent_state(),
            make_persona_spec(),
            [perception_event],
        )
        assert len(result.new_memory_ids) == 1
        stored = await cognition_store.list_by_agent(
            agent_id="a_kant_001",
            kind=MemoryKind.EPISODIC,
        )
        assert len(stored) == 1
    finally:
        await embedding.close()
        await llm.close()


async def test_step_falls_back_on_ollama_error(
    make_agent_state,
    make_persona_spec,
    make_chat_client: Callable[..., OllamaChatClient],
    make_embedding_client: Callable[[], EmbeddingClient],
    cognition_store: MemoryStore,
    cognition_retriever: Retriever,
    perception_event: PerceptionEvent,
) -> None:
    import httpx  # noqa: PLC0415

    embedding = make_embedding_client()
    llm = make_chat_client(raise_exc=httpx.ConnectError("no route"))
    try:
        cycle = _build_cycle(
            retriever=cognition_retriever,
            store=cognition_store,
            embedding=embedding,
            llm=llm,
        )
        result = await cycle.step(
            make_agent_state(),
            make_persona_spec(),
            [perception_event],
        )
    finally:
        await embedding.close()
        await llm.close()

    assert result.llm_fell_back
    kinds = [e.kind for e in result.envelopes]
    assert kinds == ["agent_update"]


async def test_step_falls_back_on_malformed_llm_output(
    make_agent_state,
    make_persona_spec,
    make_chat_client: Callable[..., OllamaChatClient],
    make_embedding_client: Callable[[], EmbeddingClient],
    cognition_store: MemoryStore,
    cognition_retriever: Retriever,
    perception_event: PerceptionEvent,
) -> None:
    embedding = make_embedding_client()
    llm = make_chat_client(content="I cannot produce JSON right now.")
    try:
        cycle = _build_cycle(
            retriever=cognition_retriever,
            store=cognition_store,
            embedding=embedding,
            llm=llm,
        )
        result = await cycle.step(
            make_agent_state(),
            make_persona_spec(),
            [perception_event],
        )
    finally:
        await embedding.close()
        await llm.close()

    assert result.llm_fell_back
    assert len(result.envelopes) == 1
    assert isinstance(result.envelopes[0], AgentUpdateMsg)


async def test_step_applies_erre_sampling_override(
    make_agent_state,
    make_persona_spec,
    make_chat_client: Callable[..., OllamaChatClient],
    make_embedding_client: Callable[[], EmbeddingClient],
    cognition_store: MemoryStore,
    cognition_retriever: Retriever,
    perception_event: PerceptionEvent,
) -> None:
    embedding = make_embedding_client()
    captured: list[dict[str, Any]] = []
    llm = make_chat_client(captured=captured)
    persona: PersonaSpec = make_persona_spec(
        default_sampling={"temperature": 0.6, "top_p": 0.85, "repeat_penalty": 1.12},
    )
    agent: AgentState = make_agent_state(
        erre={
            "name": ERREModeName.PERIPATETIC.value,
            "entered_at_tick": 0,
            # peripatetic overrides per persona-erre §ルール 2.
            "sampling_overrides": {
                "temperature": 0.3,
                "top_p": 0.05,
                "repeat_penalty": -0.1,
            },
        },
        position={"x": 0.0, "y": 0.0, "z": 0.0, "zone": "peripatos"},
    )
    try:
        cycle = _build_cycle(
            retriever=cognition_retriever,
            store=cognition_store,
            embedding=embedding,
            llm=llm,
        )
        await cycle.step(agent, persona, [perception_event])
    finally:
        await embedding.close()
        await llm.close()

    assert captured, "LLM was never invoked"
    options = captured[0]["options"]
    # 0.6 + 0.3 = 0.9 (within the clamp band).
    assert options["temperature"] == pytest.approx(0.9)
    assert options["top_p"] == pytest.approx(0.9)


async def test_step_detects_reflection_trigger_on_peripatos_entry(
    make_agent_state,
    make_persona_spec,
    make_chat_client: Callable[..., OllamaChatClient],
    make_embedding_client: Callable[[], EmbeddingClient],
    cognition_store: MemoryStore,
    cognition_retriever: Retriever,
    zone_entry_event: ZoneTransitionEvent,
) -> None:
    embedding = make_embedding_client()
    llm = make_chat_client()
    try:
        cycle = _build_cycle(
            retriever=cognition_retriever,
            store=cognition_store,
            embedding=embedding,
            llm=llm,
        )
        result = await cycle.step(
            make_agent_state(),
            make_persona_spec(),
            [zone_entry_event],
        )
    finally:
        await embedding.close()
        await llm.close()

    assert result.reflection_triggered is True


async def test_step_advances_physical_even_on_fallback(
    make_agent_state,
    make_persona_spec,
    make_chat_client: Callable[..., OllamaChatClient],
    make_embedding_client: Callable[[], EmbeddingClient],
    cognition_store: MemoryStore,
    cognition_retriever: Retriever,
) -> None:
    """Physical decays with time even if the LLM call fails."""
    import httpx  # noqa: PLC0415

    embedding = make_embedding_client()
    llm = make_chat_client(raise_exc=httpx.ConnectError("fail"))
    prev = make_agent_state(
        physical={"mood_baseline": 0.8},
    )
    try:
        cycle = _build_cycle(
            retriever=cognition_retriever,
            store=cognition_store,
            embedding=embedding,
            llm=llm,
        )
        result = await cycle.step(prev, make_persona_spec(), [])
    finally:
        await embedding.close()
        await llm.close()

    assert result.llm_fell_back
    assert result.agent_state.physical.mood_baseline < 0.8


async def test_move_msg_targets_destination_zone(
    make_agent_state,
    make_persona_spec,
    make_chat_client: Callable[..., OllamaChatClient],
    make_embedding_client: Callable[[], EmbeddingClient],
    cognition_store: MemoryStore,
    cognition_retriever: Retriever,
    perception_event: PerceptionEvent,
) -> None:
    embedding = make_embedding_client()
    # DEFAULT_PLAN destination_zone = "peripatos"
    llm = make_chat_client()
    try:
        cycle = _build_cycle(
            retriever=cognition_retriever,
            store=cognition_store,
            embedding=embedding,
            llm=llm,
        )
        result = await cycle.step(
            make_agent_state(),
            make_persona_spec(),
            [perception_event],
        )
    finally:
        await embedding.close()
        await llm.close()

    move = next(e for e in result.envelopes if isinstance(e, MoveMsg))
    assert move.target.zone is Zone.PERIPATOS
    assert move.speed == CognitionCycle.DEFAULT_DESTINATION_SPEED


async def test_speech_msg_carries_utterance(
    make_agent_state,
    make_persona_spec,
    make_chat_client: Callable[..., OllamaChatClient],
    make_embedding_client: Callable[[], EmbeddingClient],
    cognition_store: MemoryStore,
    cognition_retriever: Retriever,
    perception_event: PerceptionEvent,
) -> None:
    custom = {
        "thought": "quiet thought",
        "utterance": "こんにちは",
        "destination_zone": None,
        "animation": None,
        "valence_delta": 0.0,
        "arousal_delta": 0.0,
        "motivation_delta": 0.0,
        "importance_hint": 0.5,
    }
    embedding = make_embedding_client()
    llm = make_chat_client(content=json.dumps(custom))
    try:
        cycle = _build_cycle(
            retriever=cognition_retriever,
            store=cognition_store,
            embedding=embedding,
            llm=llm,
        )
        result = await cycle.step(
            make_agent_state(),
            make_persona_spec(),
            [perception_event],
        )
    finally:
        await embedding.close()
        await llm.close()

    speech = next(e for e in result.envelopes if isinstance(e, SpeechMsg))
    assert speech.utterance == "こんにちは"
    # No Move/Animation envelopes this time.
    assert not any(e.kind == "move" for e in result.envelopes)
    assert not any(e.kind == "animation" for e in result.envelopes)


async def test_step_continues_on_embedding_unavailable(
    make_agent_state,
    make_persona_spec,
    make_chat_client: Callable[..., OllamaChatClient],
    make_embedding_client: Callable[..., EmbeddingClient],
    cognition_store: MemoryStore,
    cognition_retriever: Retriever,
    perception_event: PerceptionEvent,
) -> None:
    """Embedding outage → memory is stored without a vector, cycle completes."""
    import httpx  # noqa: PLC0415

    embedding = make_embedding_client(raise_exc=httpx.ConnectError("embed down"))
    llm = make_chat_client()
    try:
        cycle = _build_cycle(
            retriever=cognition_retriever,
            store=cognition_store,
            embedding=embedding,
            llm=llm,
        )
        result = await cycle.step(
            make_agent_state(),
            make_persona_spec(),
            [perception_event],
        )
    finally:
        await embedding.close()
        await llm.close()

    # Memory was still written (without a vector).
    assert len(result.new_memory_ids) == 1
    stored = await cognition_store.list_by_agent(
        agent_id="a_kant_001",
        kind=MemoryKind.EPISODIC,
    )
    assert len(stored) == 1
    # LLM path still ran — embedding failure is not a fallback trigger.
    assert not result.llm_fell_back
