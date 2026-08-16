# Blog Writing Agent Backend

Run the API from the project root:

```powershell
python -m uvicorn Backend.api:app --reload --host 127.0.0.1 --port 8010
```

Health check:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8010/health
```

The React frontend calls:

```text
POST http://127.0.0.1:8010/generate-blog
POST http://127.0.0.1:8010/generate-blog-jobs
GET  http://127.0.0.1:8010/generate-blog-jobs/{job_id}
```

Keep your API keys in `Backend/.env`.

## Model routing

The backend model setup lives in `Backend/llm_router.py`.

Default routing:

```text
normal drafting/rewrite calls -> Ollama qwen2.5:7b
structured planning calls     -> OpenRouter primary, OpenRouter fallback, then Ollama
general fallback order        -> Ollama, OpenRouter primary, OpenRouter fallback
```

Before running the agent locally, make sure Ollama is running and the model is pulled:

```powershell
ollama pull qwen2.5:7b
ollama serve
```

Optional `.env` overrides:

```text
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434/v1
OPENROUTER_PRIMARY_MODEL=nvidia/nemotron-3-super-120b-a12b:free
OPENROUTER_FALLBACK_MODEL=meta-llama/llama-3.3-70b-instruct:free
```
