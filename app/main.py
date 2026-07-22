from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.agent import AgentError, run_research_agent
from app.models import (
    CompanyResearch,
    ResearchRequest,
    ResearchResponse,
    sanitize_raw_research,
)
from app.providers import ProviderError, get_provider
from app.tracing import flush_langfuse, is_langfuse_enabled, observe, update_span

load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    flush_langfuse()


app = FastAPI(title="Sales Research POC", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str | bool]:
    try:
        provider_label = get_provider().label
    except ProviderError as exc:
        provider_label = f"unavailable ({exc})"

    return {
        "status": "ok",
        "provider": provider_label,
        "langfuse_enabled": is_langfuse_enabled(),
    }


@app.post("/research", response_model=ResearchResponse)
@observe(name="research-company", as_type="chain")
def research_company(request: ResearchRequest) -> ResearchResponse:
    source_url = str(request.company_url) if request.company_url else None

    try:
        provider = get_provider()
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        raw_research = sanitize_raw_research(
            run_research_agent(request.company_name, source_url, provider=provider)
        )
        research = CompanyResearch.model_validate(raw_research)
    except ProviderError as exc:
        update_span(level="ERROR", status_message=str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except AgentError as exc:
        update_span(level="ERROR", status_message=str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValidationError as exc:
        update_span(level="ERROR", status_message="Invalid research JSON")
        raise HTTPException(
            status_code=502,
            detail=f"Model returned invalid research JSON: {exc.errors()}",
        ) from exc

    response = ResearchResponse(model=provider.label, research=research)
    update_span(output={"company_name": research.company_name, "model": response.model})
    flush_langfuse()
    return response


# Mounted last so API routes above take priority. `html=True` serves
# frontend/index.html at the root path.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
