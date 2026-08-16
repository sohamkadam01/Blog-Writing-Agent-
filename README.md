# Blog Writing Agent

An AI agent that plans, researches, and drafts full blog posts from a single topic prompt — with a FastAPI backend, a React frontend that shows live progress as the agent works, and an optional research + image-generation pipeline built with LangGraph.

## How it works

1. **Route** — the agent decides whether the topic needs live web research (`closed_book`, `hybrid`, or `open_book` mode).
2. **Research** *(optional)* — if needed, Tavily search results are pulled and synthesized into a deduplicated evidence pack.
3. **Plan** — the agent breaks the topic into a structured outline (title, audience, sections).
4. **Draft** — each section is drafted in turn by parallel workers, grounded with evidence and citations where required.
5. **Finalize** — sections are merged into a single polished Markdown post; the agent decides if diagrams/illustrations would help, generates them, and embeds them inline.

Progress for each step streams to the frontend in real time via a background job API, so the UI can show exactly what the agent is doing (planning, drafting, finalizing) rather than a generic spinner.

## Tech stack

**Backend**
- FastAPI + Pydantic
- LangChain / LangGraph for multi-agent orchestration
- Multi-provider LLM routing, split by role — see [`Backend/llm_router.py`](Backend/llm_router.py):
  - **Gemini** (`gemini-2.5-flash`) — planning / outline generation, image-prompt planning
  - **OpenRouter** (Nemotron / Llama 3.3, free tier) — research & structured reasoning
  - **Ollama** (`qwen2.5:7b`, local) — section writing / rewriting
  - **Gemini** (`gemini-2.5-flash-image`) — image generation
  - Automatic fallback across providers if one fails
- Tavily — live web search for research mode
- `google-genai` — Gemini image generation

**Frontend**
- React 19 + TypeScript + Vite
- `react-markdown` for live preview rendering
- `lucide-react` icons

## Project structure

```
Blog writing Agent/
├── Backend/
│   ├── api.py             # FastAPI app: /generate-blog, /generate-blog-jobs endpoints
│   ├── llm_router.py       # Multi-provider model routing (Gemini / OpenRouter / Ollama) + fallback logic
│   ├── BWR.ipynb            # Full LangGraph pipeline: router -> research -> plan -> draft -> images
│   ├── demo.ipynb           # Simpler single-pass planning/drafting demo
│   ├── requirements.txt
│   └── .env                # API keys (not committed)
└── Frontend/
    ├── src/
    │   ├── App.tsx          # Main UI: topic input, live job progress, markdown preview
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

Install dependencies and add your API keys to `Backend/.env`:

```env
OPENROUTER_API_KEY=your-openrouter-key
GOOGLE_API_KEY=your-google-api-key
TAVILY_API_KEY=your-tavily-key
```

Then run the API from the project root:

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
GEMINI_MODEL=gemini-2.5-flash
```

Role-based routing:
- **Planning / outline** → Gemini → OpenRouter primary → OpenRouter fallback → Ollama
- **Research / structured reasoning** → OpenRouter primary → OpenRouter fallback → Gemini → Ollama
- **Section writing / rewriting** → Ollama (local)
- **Image generation** → Gemini (`gemini-2.5-flash-image`)
- **Agent orchestration** → LangGraph coordinates the full workflow across all of the above

## License

Add a license of your choice (e.g. MIT) before publishing publicly.
