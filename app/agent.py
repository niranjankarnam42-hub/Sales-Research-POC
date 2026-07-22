"""The research agent: a request/execute/feed-back tool-use loop.

The model is not handed page text up front. It decides when to call
fetch_page, we execute the tool and feed the result back, and it can request
more pages (/about, /pricing, ...) until it has enough to emit the final
structured JSON. This loop is provider-agnostic.
"""

from app.json_utils import extract_json_object
from app.models import JsonObject
from app.prompts import build_system_prompt, build_user_prompt
from app.providers import LLMProvider, get_provider
from app.providers.base import Message
from app.tools import TOOLS, execute_tool
from app.tracing import observe, update_span

MAX_STEPS = 6


class AgentError(RuntimeError):
    """Raised when the agent cannot produce a valid research object."""


@observe(name="research-agent", as_type="chain")
def run_research_agent(
    company_name: str,
    company_url: str | None,
    provider: LLMProvider | None = None,
) -> JsonObject:
    provider = provider or get_provider()

    system = build_system_prompt()
    messages: list[Message] = [
        {"role": "user", "content": build_user_prompt(company_name, company_url)}
    ]

    update_span(
        metadata={
            "company_name": company_name,
            "company_url": company_url,
            "provider": provider.label,
        }
    )

    tool_calls_made = 0

    for step in range(MAX_STEPS):
        final_turn = step == MAX_STEPS - 1
        response = provider.chat(
            system=system,
            messages=messages,
            tools=None if final_turn else TOOLS,
            force_json=final_turn,
        )

        if response.wants_tool and not final_turn:
            messages.append(
                {
                    "role": "assistant",
                    "content": response.text,
                    "tool_calls": response.tool_calls,
                }
            )
            for call in response.tool_calls:
                tool_calls_made += 1
                result = execute_tool(call.name, call.input)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.name,
                        "content": result,
                    }
                )
            continue

        try:
            research = extract_json_object(response.text)
        except ValueError:
            if final_turn:
                update_span(level="ERROR", status_message="No valid JSON produced")
                raise AgentError(
                    "The model did not return valid research JSON."
                ) from None
            # Nudge the model to emit JSON on the next turn.
            messages.append(
                {
                    "role": "assistant",
                    "content": response.text,
                    "tool_calls": [],
                }
            )
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Return the final research now as a single JSON object "
                        "matching the required schema. No other text."
                    ),
                }
            )
            continue

        update_span(
            output={"tool_calls_made": tool_calls_made, "steps": step + 1}
        )
        return research

    update_span(level="ERROR", status_message="Exceeded max steps")
    raise AgentError("The research agent exceeded its step budget.")
