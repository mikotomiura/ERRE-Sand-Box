"""LLM inference adapters (Ollama today, SGLang M7+) — depends on ``schemas`` only.

Public surface:

* :class:`OllamaChatClient` — Ollama ``/api/chat`` client
* :class:`ChatMessage` — role-tagged request message
* :class:`ChatResponse` — normalised, backend-agnostic response
* :class:`OllamaUnavailableError` — single unified error
* :func:`compose_sampling` — ``SamplingBase + SamplingDelta`` → clamped
  :class:`ResolvedSampling` (the only supported way to reach the adapter)
* :data:`DEFAULT_CHAT_MODEL` — model tag pulled during T09

The sampling composition is deliberately re-exported from the top level so
callers (T12 cognition cycle, T14 gateway) never touch the inner module
paths.

Layer dependency (see ``architecture-rules`` skill):

* allowed: ``erre_sandbox.schemas``, ``httpx``, ``pydantic``
* forbidden: ``memory``, ``cognition``, ``world``, ``ui``
"""

from erre_sandbox.inference.ollama_adapter import (
    DEFAULT_CHAT_MODEL,
    ChatMessage,
    ChatResponse,
    OllamaChatClient,
    OllamaUnavailableError,
)
from erre_sandbox.inference.sampling import ResolvedSampling, compose_sampling

__all__ = [
    "DEFAULT_CHAT_MODEL",
    "ChatMessage",
    "ChatResponse",
    "OllamaChatClient",
    "OllamaUnavailableError",
    "ResolvedSampling",
    "compose_sampling",
]
