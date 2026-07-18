# Sales Research POC Hitlist

Track this project from local proof of concept to `naniweb.com/company_research`.

## Phase 1: Local API

- [x] Create project README with mission and setup
- [x] Add FastAPI app
- [x] Add `GET /health`
- [x] Add `POST /research`
- [x] Add webpage fetching with `fetch_page`
- [x] Add Ollama integration
- [x] Add strict JSON prompt
- [x] Add Pydantic response validation
- [x] Add basic tests
- [x] Verify tests pass locally

## Phase 2: Local Manual Testing

- [ ] Start Ollama
- [ ] Start FastAPI with `uvicorn app.main:app --reload`
- [ ] Test `/health`
- [ ] Test `/research` with Cloudflare
- [ ] Test `/research` with Microsoft
- [ ] Test `/research` with Stripe
- [ ] Test `/research` with Shopify
- [ ] Test behavior when no website is provided
- [ ] Test behavior when website fetch fails
- [ ] Pick best local model: `qwen2.5:7b`, `mistral:7b`, `llama3.2:3b`, or `phi4-mini:3.8b`

## Phase 3: Simple Frontend

- [x] Add `frontend/index.html`
- [x] Add `frontend/app.js`
- [x] Add `frontend/styles.css`
- [x] Create chat-style input for company name
- [x] Add optional website input
- [x] Add loading state
- [x] Render research response as readable cards
- [x] Render raw JSON for debugging
- [x] Handle API errors clearly

## Phase 3.5: Langfuse Observability

- [x] Add optional Langfuse SDK integration
- [x] Trace `/research` as a chain
- [x] Trace `fetch_page` as a tool span
- [x] Trace Ollama calls as generations
- [x] Keep app working when Langfuse keys are missing
- [x] Document Langfuse env vars in README and `.env.example`
- [ ] Create a Langfuse project and add keys to local `.env`
- [ ] Run one research request and confirm the trace appears in Langfuse

## Phase 4: Production Readiness

- [ ] Add production run command
- [ ] Add environment variable docs
- [ ] Confirm Ollama model can run on chosen AWS instance
- [ ] Keep Ollama bound to localhost only
- [ ] Keep FastAPI bound to localhost behind Nginx
- [ ] Add Nginx config for `/company_research`
- [ ] Add Nginx proxy for `/company_research/api/research`
- [ ] Add Nginx proxy for `/company_research/api/health`

## Phase 5: AWS Hosting

- [ ] Launch Ubuntu EC2 instance
- [ ] Install Python
- [ ] Install Git
- [ ] Install Nginx
- [ ] Install Ollama
- [ ] Clone repo onto EC2
- [ ] Create virtual environment
- [ ] Install `requirements.txt`
- [ ] Pull chosen Ollama model
- [ ] Run FastAPI as a background service
- [ ] Serve frontend through Nginx
- [ ] Verify app works on EC2 public IP

## Phase 6: Domain Setup

- [ ] Add Cloudflare DNS record for `naniweb.com`
- [ ] Point DNS to EC2 public IP
- [ ] Enable Cloudflare proxy
- [ ] Configure SSL mode
- [ ] Verify `https://naniweb.com/company_research`
- [ ] Confirm API works through domain
- [ ] Confirm Ollama is not publicly exposed

## Useful Commands

Run API locally:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Research test:

```bash
curl -X POST http://127.0.0.1:8000/research \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Stripe","company_url":"https://stripe.com"}' \
  | python3 -m json.tool
```

Run tests:

```bash
.venv/bin/python -m pytest
```
