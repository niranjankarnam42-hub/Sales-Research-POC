import os
from typing import Any

import httpx

from app.providers.base import (
    LLMProvider,
    Message,
    ProviderError,
    ProviderResponse,
    ToolCall,
)
from app.tracing import observe, update_generation

DEFAULT_MODEL = "qwen2.5:7b"
REQUEST_TIMEOUT_SECONDS = 120


class OllamaProvider(LLMProvider):
    """Free, local development mode using Ollama's /api/chat tool calling."""

    name = "ollama"

    def __init__(self) -> None:
        self.url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)

    @observe(name="ollama-chat", as_type="generation")
    def chat(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        force_json: bool = False,
    ) -> ProviderResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._to_ollama_messages(system, messages),
            "stream": False,
            "options": {"temperature": 0.1},
        }
        if tools:
            payload["tools"] = [self._to_ollama_tool(tool) for tool in tools]
        if force_json:
            payload["format"] = "json"

        update_generation(
            model=self.model,
            input=messages,
            model_parameters={"temperature": 0.1, "force_json": force_json},
            metadata={"provider": "ollama", "endpoint": f"{self.url}/api/chat"},
        )

        try:
            response = httpx.post(
                f"{self.url}/api/chat",
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPError as exc:
            update_generation(level="ERROR", status_message="Could not reach Ollama")
            raise ProviderError(
                "Could not reach Ollama. Make sure `ollama serve` is running."
            ) from exc

        message = body.get("message") or {}
        text = message.get("content") or ""
        tool_calls = self._parse_tool_calls(message.get("tool_calls"))

        usage = {}
        if isinstance(body.get("prompt_eval_count"), int):
            usage["input"] = body["prompt_eval_count"]
        if isinstance(body.get("eval_count"), int):
            usage["output"] = body["eval_count"]

        update_generation(
            output={"text": text, "tool_calls": [tc.name for tc in tool_calls]},
            usage_details=usage or None,
        )
        return ProviderResponse(text=text, tool_calls=tool_calls, usage=usage or None)

    def _to_ollama_messages(self, system: str, messages: list[Message]) -> list[dict]:
        out: list[dict] = [{"role": "system", "content": system}]
        for msg in messages:
            role = msg["role"]
            if role == "assistant":
                entry: dict[str, Any] = {
                    "role": "assistant",
                    "content": msg.get("content", ""),
                }
                if msg.get("tool_calls"):
                    entry["tool_calls"] = [
                        {
                            "function": {
                                "name": call.name,
                                "arguments": call.input,
                            }
                        }
                        for call in msg["tool_calls"]
                    ]
                out.append(entry)
            elif role == "tool":
                out.append({"role": "tool", "content": msg.get("content", "")})
            else:
                out.append({"role": "user", "content": msg.get("content", "")})
        return out

    def _to_ollama_tool(self, tool: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }

    def _parse_tool_calls(self, raw: Any) -> list[ToolCall]:
        if not isinstance(raw, list):
            return []
        calls: list[ToolCall] = []
        for index, item in enumerate(raw):
            function = (item or {}).get("function") or {}
            name = function.get("name")
            if not name:
                continue
            arguments = function.get("arguments")
            if not isinstance(arguments, dict):
                arguments = {}
            calls.append(ToolCall(id=f"call_{index}", name=name, input=arguments))
        return calls
