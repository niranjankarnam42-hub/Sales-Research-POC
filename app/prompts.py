from textwrap import dedent

RESEARCH_SCHEMA = dedent(
    """
    {
      "company_name": "string",
      "website": "https://example.com or null",
      "summary": "2-4 sentence company summary",
      "target_customers": ["customer segment"],
      "value_proposition": "short description of the value proposition",
      "recent_signals": [
        {
          "title": "signal title",
          "evidence": "why this signal matters",
          "source_url": "https://example.com or null"
        }
      ],
      "outreach_angles": ["specific sales outreach angle"],
      "sources": [
        {
          "url": "https://example.com",
          "description": "what this source was used for"
        }
      ]
    }
    """
).strip()


def build_system_prompt() -> str:
    return dedent(
        f"""
        You are a sales research assistant. Your job is to research a company
        and produce structured outreach intelligence.

        You have a tool, fetch_page, that returns the visible text of a public
        web page. Use it to gather evidence:
        - Start with the company's homepage.
        - If the homepage is not enough, request additional pages such as
          /about, /product, /pricing, /solutions, /customers, or /blog.
        - If a page is blocked or empty, try a different path.
        Make multiple tool calls as needed before answering.

        When you have enough evidence, stop calling tools and return the final
        research as a SINGLE JSON object, with no markdown and no extra text.

        Required JSON shape:
        {RESEARCH_SCHEMA}

        Rules:
        - Base the research on fetched page content wherever possible.
        - Use null for unknown optional URL values in "website" and "source_url".
        - In "sources", every entry must have a real URL string. If you have no
          real source URL, return an empty sources array instead. Only cite URLs
          you actually fetched.
        - Include at least one target customer and at least one outreach angle.
        - Do not invent recent news. If you found no recent signals, return an
          empty recent_signals array.
        """
    ).strip()


def build_user_prompt(company_name: str, company_url: str | None) -> str:
    if company_url:
        start = f"Start by fetching the homepage: {company_url}"
        website_line = f"Website: {company_url}"
    else:
        start = (
            "No website was provided. Infer the most likely official website "
            "and fetch it. If you cannot find one, research from what you know."
        )
        website_line = "Website: not provided"

    return dedent(
        f"""
        Research this company and produce the structured JSON.

        Company name: {company_name}
        {website_line}

        {start}
        """
    ).strip()
