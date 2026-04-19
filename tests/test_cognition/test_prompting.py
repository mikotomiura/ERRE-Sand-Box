"""Unit tests for :mod:`erre_sandbox.cognition.prompting`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from erre_sandbox.cognition.prompting import (
    RESPONSE_SCHEMA_HINT,
    build_system_prompt,
    build_user_prompt,
    format_memories,
)
from erre_sandbox.schemas import MemoryEntry, MemoryKind, Zone

if TYPE_CHECKING:
    from erre_sandbox.schemas import AgentState, PersonaSpec


@dataclass(frozen=True)
class _FakeRanked:
    entry: MemoryEntry
    strength: float
    cosine_sim: float = 0.9


def _mem(content: str, *, kind: MemoryKind = MemoryKind.EPISODIC) -> MemoryEntry:
    return MemoryEntry(
        id=f"m_{hash(content) & 0xFFFF}",
        agent_id="a_kant_001",
        kind=kind,
        content=content,
        importance=0.5,
        created_at=datetime.now(tz=UTC),
    )


def test_system_prompt_contains_persona_habits(
    make_persona_spec,
    agent_state_kant: AgentState,
) -> None:
    persona: PersonaSpec = make_persona_spec()
    prompt = build_system_prompt(persona, agent_state_kant)
    assert "15:30 daily walk" in prompt
    assert "fact" in prompt.lower()
    assert persona.display_name in prompt


def test_system_prompt_starts_with_common_prefix(
    make_persona_spec,
    agent_state_kant: AgentState,
) -> None:
    prompt = build_system_prompt(make_persona_spec(), agent_state_kant)
    # RadixAttention optimisation: common prefix must precede persona details.
    common_idx = prompt.find("ERRE-Sandbox")
    persona_idx = prompt.find("Immanuel Kant")
    assert common_idx < persona_idx


def test_format_memories_sorted_by_strength() -> None:
    memories = [
        _FakeRanked(_mem("weak memory"), strength=0.2),
        _FakeRanked(_mem("strong memory"), strength=0.9),
        _FakeRanked(_mem("mid memory"), strength=0.5),
    ]
    rendered = format_memories(memories)  # type: ignore[arg-type]
    # Strongest appears on the first line.
    first_line = rendered.splitlines()[0]
    assert "strong memory" in first_line


def test_format_memories_empty() -> None:
    out = format_memories([])
    assert "(no relevant memories)" in out


def test_build_user_prompt_embeds_recent_observations(
    perception_event,
    speech_event,
) -> None:
    prompt = build_user_prompt(
        [perception_event, speech_event],
        memories=[],
    )
    assert "library shelves" in prompt  # perception content
    assert "guten Tag" in prompt  # speech utterance
    assert RESPONSE_SCHEMA_HINT.splitlines()[0] in prompt


def test_build_user_prompt_respects_recent_limit(perception_event) -> None:
    many = [perception_event] * 10
    prompt = build_user_prompt(many, memories=[], recent_limit=3)
    # Only the last 3 perception lines should appear.
    count = prompt.count("[perception]")
    assert count == 3


def test_build_user_prompt_zone_transition_formatted(zone_entry_event) -> None:
    prompt = build_user_prompt([zone_entry_event], memories=[])
    assert "study -> peripatos" in prompt


def test_zone_value_exposed_in_system_prompt(
    make_persona_spec,
    agent_state_kant: AgentState,
) -> None:
    prompt = build_system_prompt(make_persona_spec(), agent_state_kant)
    assert Zone.STUDY.value in prompt
