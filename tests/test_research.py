from fastapi.testclient import TestClient

import app.agent as agent_module
import app.main as main
import app.tools as tools_module
from app.agent import run_research_agent
from app.providers.base import LLMProvider, ProviderResponse, ToolCall

client = TestClient(main.app)


VALID_RESEARCH = {
    "company_name": "Cloudflare",
    "website": "https://www.cloudflare.com/",
    "summary": "Cloudflare provides connectivity cloud services for security and performance.",
    "target_customers": ["Developers", "Security teams"],
    "value_proposition": "Protect and accelerate internet applications.",
    "recent_signals": [],
    "outreach_angles": ["Ask how they handle edge security today."],
    "sources": [{"url": "https://www.cloudflare.com/", "description": "Company website"}],
}


class ScriptedProvider(LLMProvider):
    """Returns a queued list of ProviderResponses, one per chat() call."""

    name = "fake"
    model = "scripted"

    def __init__(self, responses: list[ProviderResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def chat(self, *, system, messages, tools=None, force_json=False):
        self.calls.append({"tools": tools, "force_json": force_json})
        return self._responses.pop(0)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "langfuse_enabled" in body
    assert "provider" in body


def test_agent_runs_tool_use_loop(monkeypatch) -> None:
    fetched = []

    def fake_fetch_page(url: str) -> str:
        fetched.append(url)
        return "Cloudflare is a connectivity cloud company."

    monkeypatch.setattr(tools_module, "fetch_page", fake_fetch_page)

    provider = ScriptedProvider(
        [
            ProviderResponse(
                tool_calls=[
                    ToolCall(id="1", name="fetch_page", input={"url": "https://www.cloudflare.com"})
                ]
            ),
            ProviderResponse(text=__import__("json").dumps(VALID_RESEARCH)),
        ]
    )

    result = run_research_agent("Cloudflare", "https://www.cloudflare.com", provider=provider)

    assert fetched == ["https://www.cloudflare.com"]
    assert result["company_name"] == "Cloudflare"
    assert len(provider.calls) == 2


def test_agent_feeds_fetch_errors_back_to_model(monkeypatch) -> None:
    from app.fetch_page import FetchPageError

    def failing_fetch(url: str) -> str:
        raise FetchPageError("Could not fetch https://rubrik.com/: 403 Forbidden")

    monkeypatch.setattr(tools_module, "fetch_page", failing_fetch)

    provider = ScriptedProvider(
        [
            ProviderResponse(
                tool_calls=[ToolCall(id="1", name="fetch_page", input={"url": "https://rubrik.com"})]
            ),
            ProviderResponse(text=__import__("json").dumps({**VALID_RESEARCH, "company_name": "Rubrik"})),
        ]
    )

    result = run_research_agent("Rubrik", "https://rubrik.com", provider=provider)

    # The loop should not crash on a fetch error; it feeds the error back and
    # the model still produces a final answer.
    assert result["company_name"] == "Rubrik"


def test_research_endpoint_returns_structured_json(monkeypatch) -> None:
    monkeypatch.setattr(main, "run_research_agent", lambda *a, **k: dict(VALID_RESEARCH))

    response = client.post(
        "/research",
        json={"company_name": "Cloudflare", "company_url": "https://www.cloudflare.com"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["research"]["company_name"] == "Cloudflare"
    assert body["research"]["target_customers"] == ["Developers", "Security teams"]


def test_research_endpoint_drops_sources_with_null_url(monkeypatch) -> None:
    payload = {
        **VALID_RESEARCH,
        "company_name": "Sprinto",
        "sources": [
            {"url": None, "description": "Model returned a null URL"},
            {"url": "https://sprinto.com/", "description": "Company website"},
        ],
    }
    monkeypatch.setattr(main, "run_research_agent", lambda *a, **k: dict(payload))

    response = client.post("/research", json={"company_name": "Sprinto"})

    assert response.status_code == 200
    sources = response.json()["research"]["sources"]
    assert len(sources) == 1
    assert sources[0]["url"] == "https://sprinto.com/"


def test_research_endpoint_rejects_invalid_model_json(monkeypatch) -> None:
    monkeypatch.setattr(main, "run_research_agent", lambda *a, **k: {"company_name": ""})

    response = client.post("/research", json={"company_name": "Example"})

    assert response.status_code == 502
    assert "invalid research JSON" in response.json()["detail"]
