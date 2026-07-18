import json
import os
import re
from typing import Any

import httpx

from app.models import JsonObject
from app.tracing import observe, update_generation


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = "qwen2.5:7b"
REQUEST_TIMEOUT_SECONDS = 120


class OllamaError(RuntimeError):
    """Raised when Ollama is unavailable or returns unusable content."""


def get_model_name() -> str:
    return os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)


@observe(name="ollama-generate", as_type="generation")
def generate_research_json(prompt: str) -> JsonObject:
    model = get_model_name()
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
        },
    }

    update_generation(
        model=model,
        input=prompt,
        model_parameters={"temperature": 0.1, "format": "json"},
        metadata={"provider": "ollama", "endpoint": f"{OLLAMA_URL}/api/generate"},
    )

    try:
        response = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
    except httpx.HTTPError as exc:
        update_generation(
            level="ERROR",
            status_message="Could not reach Ollama",
        )
        raise OllamaError(
            "Could not reach Ollama. Make sure `ollama serve` is running."
        ) from exc
    except json.JSONDecodeError as exc:
        update_generation(
            level="ERROR",
            status_message="Ollama returned a non-JSON HTTP response",
        )
        raise OllamaError("Ollama returned a non-JSON HTTP response.") from exc

    generated_text = body.get("response")
    if not isinstance(generated_text, str):
        update_generation(
            level="ERROR",
            status_message="Ollama response did not include generated text",
        )
        raise OllamaError("Ollama response did not include generated text.")

    usage_details = {}
    if isinstance(body.get("prompt_eval_count"), int):
        usage_details["input"] = body["prompt_eval_count"]
    if isinstance(body.get("eval_count"), int):
        usage_details["output"] = body["eval_count"]

    parsed = parse_json_object(generated_text)
    update_generation(
        output=parsed,
        usage_details=usage_details or None,
    )
    return parsed


def parse_json_object(text: str) -> JsonObject:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise OllamaError("Model did not return a JSON object.") from None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise OllamaError("Model returned invalid JSON.") from exc

    if not isinstance(parsed, dict):
        raise OllamaError("Model JSON must be an object.")

    return parsed
