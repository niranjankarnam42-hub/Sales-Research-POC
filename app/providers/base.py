"""Provider-agnostic types and interface for the tool-use loop.

The agent speaks one normalized message format; each provider translates it
to and from its own API. This keeps the tool-use loop identical across the
free local model and the cloud model.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# Normalized conversation messages exchanged with the agent loop:
#   {"role": "user", "content": "<text>"}
#   {"role": "assistant", "content": "<text>", "tool_calls": [ToolCall, ...]}
#   {"role": "tool", "tool_call_id": "<id>", "name": "<name>", "content": "<result>"}
Message = dict[str, Any]


class ProviderError(RuntimeError):
    """Raised when a provider is misconfigured or the API call fails."""


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class ProviderResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict[str, int] | None = None

    @property
    def wants_tool(self) -> bool:
        return bool(self.tool_calls)


class LLMProvider(ABC):
    """One chat turn with optional tool calling."""

    name: str
    model: str

    @property
    def label(self) -> str:
        return f"{self.name}:{self.model}"

    @abstractmethod
    def chat(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        force_json: bool = False,
    ) -> ProviderResponse:
        """Send one turn and return the assistant's normalized response."""
