"""Tools the model can invoke during the research loop.

A tool is a provider-agnostic description plus a Python callable. Providers
translate these definitions into their own tool-calling formats.
"""

from app.fetch_page import FetchPageError, fetch_page

FETCH_PAGE_TOOL = {
    "name": "fetch_page",
    "description": (
        "Fetch the visible text of a public web page. Use this to read a "
        "company's homepage, then request additional paths such as /about, "
        "/product, /pricing, or /customers when the homepage is not enough "
        "to research the company thoroughly."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Full URL to fetch, including the https:// scheme.",
            }
        },
        "required": ["url"],
    },
}

TOOLS = [FETCH_PAGE_TOOL]


def execute_tool(name: str, tool_input: dict) -> str:
    """Run a tool and return a string result for the model.

    Fetch failures are returned as text (not raised) so the model can adapt,
    for example by trying a different path when a URL is blocked.
    """
    if name == "fetch_page":
        url = tool_input.get("url")
        if not url:
            return "ERROR: fetch_page requires a 'url' argument."
        try:
            return fetch_page(url)
        except FetchPageError as exc:
            return (
                f"ERROR: {exc} "
                "Try a different URL or path (for example /about or /product)."
            )

    return f"ERROR: unknown tool '{name}'."
