import json
import re

from app.models import JsonObject


def extract_json_object(text: str) -> JsonObject:
    """Parse a JSON object from model text, tolerating surrounding prose.

    Small models sometimes wrap JSON in markdown fences or add a sentence
    before it, so fall back to extracting the outermost {...} block.
    """
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError("Model did not return a JSON object.") from None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ValueError("Model returned invalid JSON.") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Model JSON must be an object.")

    return parsed
