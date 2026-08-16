# Blog Writing Agent

An AI agent that plans, researches, and drafts full blog posts from a single topic prompt — with a FastAPI backend and a React frontend that shows live progress as the agent works.

## How it works

1. **Plan** — the agent breaks the topic into a structured outline (title, audience, sections) and decides whether it needs live research.
2. **Draft** — each section is drafted in turn, optionally grounded with research queries.
3. **Finalize** — sections are assembled into a single polished Markdown post with image placeholders/specs for illustrations.

Progress for each of these steps streams to the frontend in real time via a background job API, so the UI can show exactly what the agent is doing (planning, drafting, finalizing) rather than a generic spinner.

## Tech stack

**Backend**
- FastAPI + Pydantic
- LangChain / LangGraph for orchestration
- Model routing across Ollama (local) and OpenRouter (cloud), with automatic fallback — see [`Backend/llm_router.py`](Backend/llm_router.py)

**Frontend**
- React 19 + TypeScript + Vite
- `react-markdown` for live preview rendering
- `lucide-react` icons

## Project structure

```
Blog writing Agent/
├── Backend/
│   ├── api.py            # FastAPI app: /generate-blog, /generate-blog-jobs endpoints
│   ├── llm_router.py      # Model routing + fallback logic (Ollama / OpenRouter)
│   ├── requirements.txt
│   └── .env               # API keys (not committed)
└── Frontend/
    ├── src/
    │   ├── App.tsx         # Main UI: topic input, live job progress, markdown preview
    │   ├── main.tsx
    │   └── styles.css
    ├── package.json
    └── vite.config.ts
```

## Getting started

### 1. Backend

Make sure [Ollama](https://ollama.com) is installed and running, then pull the default model:

```powershell
ollama pull qwen2.5:7b
ollama serve
```

Install dependencies and add your API keys to `Backend/.env`, then run the API from the project root:

```powershell
pip install -r Backend/requirements.txt
python -m uvicorn Backend.api:app --reload --host 127.0.0.1 --port 8010
```

Health check:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8010/health
```

### 2. Frontend

```powershell
cd Frontend
npm install
npm run dev
```

The app expects the backend at `http://127.0.0.1:8010` by default (override with `VITE_API_BASE_URL`).

## API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/generate-blog` | Generate a blog post synchronously |
| `POST` | `/generate-blog-jobs` | Kick off an async job |
| `GET` | `/generate-blog-jobs/{job_id}` | Poll job status/progress and fetch the result |

### Model routing

Configurable via `Backend/.env`:

```env
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434/v1
OPENROUTER_PRIMARY_MODEL=nvidia/nemotron-3-super-120b-a12b:free
OPENROUTER_FALLBACK_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

Default routing:
- Drafting/rewrite calls → Ollama (`qwen2.5:7b`)
- Structured planning calls → OpenRouter primary → OpenRouter fallback → Ollama
- General fallback order → Ollama → OpenRouter primary → OpenRouter fallback

## License

Add a license of your choice (e.g. MIT) before publishing publicly.
