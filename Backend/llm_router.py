import os
from pathlib import Path
from typing import Iterable

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


def _load_backend_env() -> None:
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_backend_env()

LOCAL_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

PRIMARY_MODEL = os.getenv(
    "OPENROUTER_PRIMARY_MODEL",
    "nvidia/nemotron-3-super-120b-a12b:free",
)
FALLBACK_MODEL = os.getenv(
    "OPENROUTER_FALLBACK_MODEL",
    "meta-llama/llama-3.3-70b-instruct:free",
)
OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL",
    "https://openrouter.ai/api/v1",
)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def make_ollama_llm(model: str = LOCAL_MODEL) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
        base_url=OLLAMA_BASE_URL,
    )


def make_openrouter_llm(model: str) -> ChatOpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for OpenRouter models.")

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
    )


def make_gemini_llm(model: str = GEMINI_MODEL) -> ChatGoogleGenerativeAI:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is required for Gemini models.")

    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
    )


local_llm = make_ollama_llm()
primary_llm = make_openrouter_llm(PRIMARY_MODEL) if os.getenv("OPENROUTER_API_KEY") else None
fallback_llm = make_openrouter_llm(FALLBACK_MODEL) if os.getenv("OPENROUTER_API_KEY") else None
gemini_llm = make_gemini_llm() if os.getenv("GOOGLE_API_KEY") else None

# Default writer model. Use this for normal drafting and rewriting work (section writing/rewriting).
llm = local_llm

# Role-based aliases used across the pipeline:
#   planning_llm  -> Gemini: planning/outline generation
#   research_llm  -> OpenRouter: research/structured reasoning
#   writer_llm    -> Ollama: section writing/rewriting
planning_llm = gemini_llm
research_llm = primary_llm or fallback_llm
writer_llm = local_llm


def _first_success(models: Iterable[tuple[str, ChatOpenAI | None]], invoke):
    errors: list[str] = []
    for name, model in models:
        if model is None:
            errors.append(f"{name}: not configured")
            continue

        try:
            return invoke(model)
        except Exception as error:
            errors.append(f"{name}: {error}")

    raise RuntimeError("All configured models failed. " + "; ".join(errors))


def invoke_with_fallback(messages):
    return _first_success(
        [
            (f"Ollama {LOCAL_MODEL}", local_llm),
            (f"OpenRouter {PRIMARY_MODEL}", primary_llm),
            (f"OpenRouter {FALLBACK_MODEL}", fallback_llm),
        ],
        lambda model: model.invoke(messages),
    )


def invoke_structured_with_fallback(schema, messages):
    return _first_success(
        [
            (f"Gemini {GEMINI_MODEL}", gemini_llm),
            (f"OpenRouter {PRIMARY_MODEL}", primary_llm),
            (f"OpenRouter {FALLBACK_MODEL}", fallback_llm),
            (f"Ollama {LOCAL_MODEL}", local_llm),
        ],
        lambda model: model.with_structured_output(schema).invoke(messages),
    )


def invoke_planning_with_fallback(schema, messages):
    """Planning/outline calls: Gemini first, falls back to OpenRouter then Ollama."""
    return _first_success(
        [
            (f"Gemini {GEMINI_MODEL}", gemini_llm),
            (f"OpenRouter {PRIMARY_MODEL}", primary_llm),
            (f"OpenRouter {FALLBACK_MODEL}", fallback_llm),
            (f"Ollama {LOCAL_MODEL}", local_llm),
        ],
        lambda model: model.with_structured_output(schema).invoke(messages),
    )


def invoke_research_with_fallback(schema, messages):
    """Research/structured-reasoning calls: OpenRouter first, falls back to Gemini then Ollama."""
    return _first_success(
        [
            (f"OpenRouter {PRIMARY_MODEL}", primary_llm),
            (f"OpenRouter {FALLBACK_MODEL}", fallback_llm),
            (f"Gemini {GEMINI_MODEL}", gemini_llm),
            (f"Ollama {LOCAL_MODEL}", local_llm),
        ],
        lambda model: model.with_structured_output(schema).invoke(messages),
    )
