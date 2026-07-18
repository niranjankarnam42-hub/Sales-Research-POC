from fastapi.testclient import TestClient

import app.main as main


client = TestClient(main.app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "langfuse_enabled" in body


def test_research_returns_valid_structured_json(monkeypatch) -> None:
    def fake_generate_research_json(prompt: str) -> dict:
        assert "Cloudflare" in prompt
        return {
            "company_name": "Cloudflare",
            "website": "https://www.cloudflare.com/",
            "summary": "Cloudflare provides connectivity cloud services for security, performance, and reliability.",
            "target_customers": ["Developers", "Security teams"],
            "value_proposition": "Cloudflare helps teams protect and accelerate internet applications.",
            "recent_signals": [],
            "outreach_angles": [
                "Ask how the team handles application security and edge performance today."
            ],
            "sources": [
                {
                    "url": "https://www.cloudflare.com/",
                    "description": "Company website",
                }
            ],
        }

    monkeypatch.setattr(main, "fetch_page", lambda url: "Cloudflare website text")
    monkeypatch.setattr(main, "generate_research_json", fake_generate_research_json)
    monkeypatch.setattr(main, "get_model_name", lambda: "test-model")

    response = client.post(
        "/research",
        json={
            "company_name": "Cloudflare",
            "company_url": "https://www.cloudflare.com",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "test-model"
    assert body["research"]["company_name"] == "Cloudflare"
    assert body["research"]["target_customers"] == ["Developers", "Security teams"]


def test_research_drops_sources_with_null_url(monkeypatch) -> None:
    def fake_generate_research_json(prompt: str) -> dict:
        return {
            "company_name": "Sprinto",
            "website": "https://sprinto.com/",
            "summary": "Sprinto automates security compliance for cloud companies.",
            "target_customers": ["SaaS companies"],
            "value_proposition": "Faster compliance with less manual work.",
            "recent_signals": [],
            "outreach_angles": ["Ask about upcoming SOC 2 or ISO 27001 audits."],
            "sources": [
                {"url": None, "description": "Model returned a null URL"},
                {"url": "https://sprinto.com/", "description": "Company website"},
            ],
        }

    monkeypatch.setattr(main, "generate_research_json", fake_generate_research_json)
    monkeypatch.setattr(main, "get_model_name", lambda: "test-model")

    response = client.post("/research", json={"company_name": "Sprinto"})

    assert response.status_code == 200
    sources = response.json()["research"]["sources"]
    assert len(sources) == 1
    assert sources[0]["url"] == "https://sprinto.com/"


def test_research_rejects_invalid_model_json(monkeypatch) -> None:
    monkeypatch.setattr(main, "generate_research_json", lambda prompt: {"company_name": ""})

    response = client.post("/research", json={"company_name": "Example"})

    assert response.status_code == 502
    assert "invalid research JSON" in response.json()["detail"]
