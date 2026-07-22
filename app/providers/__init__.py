"""LLM provider abstraction.

The provider is chosen at runtime via the LLM_PROVIDER env var:
- "ollama" (default): free, local development mode.
- "claude": cloud production mode via the Anthropic API.
"""

import os

from app.providers.base import LLMProvider, ProviderError, ProviderResponse, ToolCall


def get_provider() -> LLMProvider:
    name = os.getenv("LLM_PROVIDER", "ollama").strip().lower()

    if name == "ollama":
        from app.providers.ollama import OllamaProvider

        return OllamaProvider()

    if name in {"claude", "anthropic"}:
        from app.providers.claude import ClaudeProvider

        return ClaudeProvider()

    raise ProviderError(
        f"Unknown LLM_PROVIDER '{name}'. Use 'ollama' or 'claude'."
    )


__all__ = [
    "LLMProvider",
    "ProviderError",
    "ProviderResponse",
    "ToolCall",
    "get_provider",
]
