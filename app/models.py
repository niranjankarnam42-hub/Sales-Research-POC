from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ResearchRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    company_url: HttpUrl | None = None


class RecentSignal(BaseModel):
    title: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    source_url: HttpUrl | None = None


class Source(BaseModel):
    url: HttpUrl
    description: str = Field(min_length=1)


class CompanyResearch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(min_length=1)
    website: HttpUrl | None = None
    summary: str = Field(min_length=1)
    target_customers: list[str] = Field(min_length=1)
    value_proposition: str = Field(min_length=1)
    recent_signals: list[RecentSignal] = Field(default_factory=list)
    outreach_angles: list[str] = Field(min_length=1)
    sources: list[Source] = Field(default_factory=list)


class ResearchResponse(BaseModel):
    model: str
    research: CompanyResearch


JsonObject = dict[str, Any]


def sanitize_raw_research(raw: JsonObject) -> JsonObject:
    """Drop model output that would fail validation but is safe to discard.

    Local models sometimes emit sources with a null url despite the prompt;
    a missing source is better than failing the whole request.
    """
    sources = raw.get("sources")
    if isinstance(sources, list):
        raw["sources"] = [
            source
            for source in sources
            if isinstance(source, dict) and source.get("url")
        ]
    return raw
