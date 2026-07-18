# Sales Research POC

Build a local-first sales research API that fetches a company's public web page, asks an Ollama model to analyze it, and returns validated structured JSON.

## Mission

Create a narrow FastAPI proof of concept that works for one real company before adding a frontend, deployment, or paid model provider.

## Stack

- FastAPI for the API.
- Ollama for local LLM inference.
- `fetch_page` for public web page retrieval and cleanup.
- Pydantic for request and response validation.
- Optional Langfuse tracing for LLM observability.

Claude API support can be added later, but it is not required for version 1.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama serve
uvicorn app.main:app --reload
```

The default local model is `qwen2.5:7b`. Override it with:

```bash
export OLLAMA_MODEL=mistral:7b
```

## Langfuse Tracing (Optional)

Tracing is off unless both keys are set. Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Then fill in values from [Langfuse Cloud](https://cloud.langfuse.com) (or your self-hosted host):

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

Restart uvicorn. Each `/research` call creates a trace with:

- `research-company` chain
- `fetch-page` tool span (when a URL is provided)
- `ollama-generate` generation (model, prompt, output, token counts when available)

`GET /health` reports `"langfuse_enabled": true` when credentials are loaded.

## Try It

```bash
curl -X POST http://127.0.0.1:8000/research \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Cloudflare","company_url":"https://www.cloudflare.com"}'
```

## Response Shape

The API returns JSON with:

- `company_name`
- `website`
- `summary`
- `target_customers`
- `value_proposition`
- `recent_signals`
- `outreach_angles`
- `sources`

## Version 1 Done

- `GET /health` returns OK.
- `POST /research` accepts one company and optional website URL.
- The app fetches the website when provided.
- Ollama returns structured JSON.
- The API validates that JSON before returning it.