import re

import httpx
from bs4 import BeautifulSoup

from app.tracing import observe, update_span


MAX_PAGE_CHARS = 12_000
REQUEST_TIMEOUT_SECONDS = 10
USER_AGENT = "SalesResearchPOC/0.1 (+https://naniweb.com)"


class FetchPageError(RuntimeError):
    """Raised when a page cannot be fetched or converted to useful text."""


@observe(name="fetch-page", as_type="tool")
def fetch_page(url: str) -> str:
    update_span(metadata={"url": url})

    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        update_span(level="ERROR", status_message=str(exc))
        raise FetchPageError(f"Could not fetch {url}: {exc}") from exc

    text = html_to_text(response.text)
    if not text:
        update_span(level="ERROR", status_message="No readable text found")
        raise FetchPageError(f"Fetched {url}, but no readable text was found.")

    clipped = text[:MAX_PAGE_CHARS]
    update_span(
        output={"chars": len(clipped), "truncated": len(text) > MAX_PAGE_CHARS},
        metadata={"final_url": str(response.url), "status_code": response.status_code},
    )
    return clipped


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    raw_text = soup.get_text(separator=" ")
    return normalize_whitespace(raw_text)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
