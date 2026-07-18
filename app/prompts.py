from textwrap import dedent


def build_research_prompt(
    company_name: str,
    company_url: str | None,
    page_text: str,
) -> str:
    website = company_url or "Not provided"
    context = page_text or "No website text was provided. Use only the company name."

    return dedent(
        f"""
        You are a sales research assistant. Return only valid JSON with no markdown,
        no comments, and no extra text.

        Research the company using the provided context.

        Company name: {company_name}
        Website: {website}

        Required JSON shape:
        {{
          "company_name": "string",
          "website": "https://example.com or null",
          "summary": "2-4 sentence company summary",
          "target_customers": ["customer segment"],
          "value_proposition": "short description of the value proposition",
          "recent_signals": [
            {{
              "title": "signal title",
              "evidence": "why this signal matters",
              "source_url": "https://example.com or null"
            }}
          ],
          "outreach_angles": ["specific sales outreach angle"],
          "sources": [
            {{
              "url": "https://example.com",
              "description": "what this source was used for"
            }}
          ]
        }}

        Rules:
        - Use null for unknown optional URL values in "website" and "source_url".
        - In "sources", every entry must have a real URL string. If you have no
          real source URL, return an empty sources array instead.
        - Include at least one target customer.
        - Include at least one outreach angle.
        - Do not invent recent news. If no recent signals are present in the context,
          return an empty recent_signals array.
        - If a website URL was provided, include it in sources.

        Context:
        {context}
        """
    ).strip()
