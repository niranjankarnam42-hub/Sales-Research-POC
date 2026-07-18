from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.fetch_page import FetchPageError, fetch_page
from app.llm import OllamaError, generate_research_json, get_model_name
from app.models import (
    CompanyResearch,
    ResearchRequest,
    ResearchResponse,
    sanitize_raw_research,
)
from app.prompts import build_research_prompt
from app.tracing import flush_langfuse, is_langfuse_enabled, observe, update_span


load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    flush_langfuse()


app = FastAPI(title="Sales Research POC", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "langfuse_enabled": is_langfuse_enabled(),
    }


@app.post("/research", response_model=ResearchResponse)
@observe(name="research-company", as_type="chain")
def research_company(request: ResearchRequest) -> ResearchResponse:
    page_text = ""
    source_url = str(request.company_url) if request.company_url else None

    update_span(
        metadata={
            "company_name": request.company_name,
            "company_url": source_url,
            "model": get_model_name(),
        }
    )

    if source_url:
        try:
            page_text = fetch_page(source_url)
        except FetchPageError as exc:
            update_span(level="ERROR", status_message=str(exc))
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    prompt = build_research_prompt(
        company_name=request.company_name,
        company_url=source_url,
        page_text=page_text,
    )

    try:
        raw_research = sanitize_raw_research(generate_research_json(prompt))
        research = CompanyResearch.model_validate(raw_research)
    except OllamaError as exc:
        update_span(level="ERROR", status_message=str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValidationError as exc:
        update_span(level="ERROR", status_message="Invalid research JSON")
        raise HTTPException(
            status_code=502,
            detail=f"Model returned invalid research JSON: {exc.errors()}",
        ) from exc

    response = ResearchResponse(model=get_model_name(), research=research)
    update_span(output={"company_name": research.company_name, "model": response.model})
    flush_langfuse()
    return response


# Mounted last so API routes above take priority. `html=True` serves
# frontend/index.html at the root path.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
