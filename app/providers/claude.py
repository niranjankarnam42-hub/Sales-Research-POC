import os
from typing import Any

from app.providers.base import (
    LLMProvider,
    Message,
    ProviderError,
    ProviderResponse,
    ToolCall,
)
from app.tracing import observe, update_generation

DEFAULT_MODEL = "claude-3-5-sonnet-latest"
MAX_TOKENS = 2048


class ClaudeProvider(LLMProvider):
    """Cloud production mode using the Anthropic Messages API with tool use."""

    name = "claude"

    def __init__(self) -> None:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ProviderError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env to use "
                "LLM_PROVIDER=claude, or switch to LLM_PROVIDER=ollama."
            )
        self.model = os.getenv("CLAUDE_MODEL", DEFAULT_MODEL)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    @observe(name="claude-chat", as_type="generation")
    def chat(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        force_json: bool = False,
    ) -> ProviderResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": self._to_claude_messages(messages),
        }
        if tools:
            kwargs["tools"] = [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "input_schema": tool["input_schema"],
                }
                for tool in tools
            ]

        update_generation(
            model=self.model,
            input=messages,
            model_parameters={"max_tokens": MAX_TOKENS},
            metadata={"provider": "claude"},
        )

        try:
            message = self.client.messages.create(**kwargs)
        except Exception as exc:  # anthropic.APIError and friends
            update_generation(level="ERROR", status_message=str(exc))
            raise ProviderError(f"Claude API call failed: {exc}") from exc

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in message.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, input=dict(block.input))
                )

        usage = {
            "input": message.usage.input_tokens,
            "output": message.usage.output_tokens,
        }
        text = "".join(text_parts)

        update_generation(
            output={"text": text, "tool_calls": [tc.name for tc in tool_calls]},
            usage_details=usage,
        )
        return ProviderResponse(text=text, tool_calls=tool_calls, usage=usage)

    def _to_claude_messages(self, messages: list[Message]) -> list[dict]:
        out: list[dict] = []
        for msg in messages:
            role = msg["role"]
            if role == "assistant":
                content: list[dict[str, Any]] = []
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                for call in msg.get("tool_calls", []):
                    content.append(
                        {
                            "type": "tool_use",
                            "id": call.id,
                            "name": call.name,
                            "input": call.input,
                        }
                    )
                out.append({"role": "assistant", "content": content})
            elif role == "tool":
                block = {
                    "type": "tool_result",
                    "tool_use_id": msg["tool_call_id"],
                    "content": msg.get("content", ""),
                }
                # Merge consecutive tool results into one user turn, as Claude
                # expects all results for a turn in a single user message.
                if out and out[-1]["role"] == "user" and isinstance(
                    out[-1]["content"], list
                ):
                    out[-1]["content"].append(block)
                else:
                    out.append({"role": "user", "content": [block]})
            else:
                out.append({"role": "user", "content": msg.get("content", "")})
        return out
