from __future__ import annotations

from datetime import date
from threading import Lock
from typing import Literal
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from Backend.llm_router import invoke_structured_with_fallback, invoke_with_fallback


class BlogRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    as_of: str | None = None


class BlogSection(BaseModel):
    title: str
    brief: str
    bullets: list[str] = Field(default_factory=list)


class BlogPlan(BaseModel):
    blog_title: str
    audience: str
    needs_research: bool = False
    queries: list[str] = Field(default_factory=list)
    sections: list[BlogSection]


class ImageSpec(BaseModel):
    placeholder: str | None = None
    filename: str | None = None
    alt: str | None = None
    caption: str | None = None


class BlogResponse(BaseModel):
    topic: str
    final: str
    mode: str | None = None
    needs_research: bool | None = None
    queries: list[str] = Field(default_factory=list)
    image_specs: list[ImageSpec] = Field(default_factory=list)


StepStatus = Literal["pending", "running", "completed", "failed"]
JobStatus = Literal["queued", "running", "completed", "failed"]


class ProcessStep(BaseModel):
    key: str
    label: str
    status: StepStatus = "pending"
    detail: str | None = None


class BlogJobResponse(BaseModel):
    job_id: str
    status: JobStatus
    steps: list[ProcessStep]
    result: BlogResponse | None = None
    error: str | None = None


app = FastAPI(title="Blog Writing Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_jobs: dict[str, BlogJobResponse] = {}
_jobs_lock = Lock()


def _initial_steps() -> list[ProcessStep]:
    return [
        ProcessStep(key="plan", label="Planning outline"),
        ProcessStep(key="draft", label="Drafting sections"),
        ProcessStep(key="finalize", label="Finalizing markdown"),
    ]


def _update_job(
    job_id: str,
    *,
    status: JobStatus | None = None,
    step_key: str | None = None,
    step_status: StepStatus | None = None,
    detail: str | None = None,
    result: BlogResponse | None = None,
    error: str | None = None,
) -> None:
    with _jobs_lock:
        job = _jobs[job_id]
        if status:
            job.status = status
        if result:
            job.result = result
        if error:
            job.error = error

        if step_key:
            for step in job.steps:
                if step.key == step_key:
                    if step_status:
                        step.status = step_status
                    if detail is not None:
                        step.detail = detail
                    break


def _message_text(response) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(content)


def _fallback_plan(topic: str) -> BlogPlan:
    return BlogPlan(
        blog_title=topic,
        audience="technical readers",
        needs_research=False,
        queries=[],
        sections=[
            BlogSection(
                title="Introduction",
                brief="Set context, explain why the topic matters, and preview the argument.",
                bullets=["Define the topic", "Name the reader's practical takeaway"],
            ),
            BlogSection(
                title="Core Concepts",
                brief="Explain the main ideas clearly with technical accuracy.",
                bullets=["Use concrete examples", "Avoid unsupported claims"],
            ),
            BlogSection(
                title="Implementation Notes",
                brief="Describe how readers can apply the topic in a real project.",
                bullets=["Mention tradeoffs", "Call out common pitfalls"],
            ),
            BlogSection(
                title="Conclusion",
                brief="Summarize the post and leave readers with next steps.",
                bullets=["Recap the main point", "Suggest what to explore next"],
            ),
        ],
    )


def _build_plan(topic: str, as_of: str | None) -> BlogPlan:
    today = as_of or date.today().isoformat()
    messages = [
        SystemMessage(
            content=(
                "You are a senior technical content strategist. Create a concise, useful "
                "blog plan. Return only the requested structured output. Use current-date "
                f"context as {today} when relevant."
            )
        ),
        HumanMessage(content=f"Blog topic: {topic}"),
    ]

    try:
        plan = invoke_structured_with_fallback(BlogPlan, messages)
        return plan if plan.sections else _fallback_plan(topic)
    except Exception:
        return _fallback_plan(topic)


def _draft_section(topic: str, plan: BlogPlan, section: BlogSection, as_of: str | None) -> str:
    bullets = "\n".join(f"- {bullet}" for bullet in section.bullets)
    messages = [
        SystemMessage(
            content=(
                "You write clear, practical technical blog sections in markdown. "
                "Do not invent citations. Do not include frontmatter. Keep the tone "
                "confident, concrete, and useful."
            )
        ),
        HumanMessage(
            content=(
                f"Topic: {topic}\n"
                f"Blog title: {plan.blog_title}\n"
                f"Audience: {plan.audience}\n"
                f"As of: {as_of or date.today().isoformat()}\n\n"
                f"Write this section:\n"
                f"## {section.title}\n"
                f"Brief: {section.brief}\n"
                f"Bullets:\n{bullets or '- Cover the section thoroughly.'}\n\n"
                "Return markdown for this section only."
            )
        ),
    ]
    return _message_text(invoke_with_fallback(messages)).strip()


def _finalize_blog(topic: str, plan: BlogPlan, sections: list[str], as_of: str | None) -> str:
    draft = "\n\n".join(sections)
    messages = [
        SystemMessage(
            content=(
                "You are a technical editor. Produce one polished markdown blog post. "
                "Keep useful headings, remove repetition, preserve technical details, "
                "and add a short conclusion if needed."
            )
        ),
        HumanMessage(
            content=(
                f"Topic: {topic}\n"
                f"Title: {plan.blog_title}\n"
                f"As of: {as_of or date.today().isoformat()}\n\n"
                f"Draft sections:\n{draft}"
            )
        ),
    ]
    final = _message_text(invoke_with_fallback(messages)).strip()
    if not final.startswith("#"):
        final = f"# {plan.blog_title}\n\n{final}"
    return final


def generate_blog(topic: str, as_of: str | None = None, job_id: str | None = None) -> BlogResponse:
    if job_id:
        _update_job(
            job_id,
            status="running",
            step_key="plan",
            step_status="running",
            detail="Building outline and section briefs.",
        )

    plan = _build_plan(topic, as_of)

    if job_id:
        _update_job(
            job_id,
            step_key="plan",
            step_status="completed",
            detail=f"{len(plan.sections)} sections planned.",
        )
        _update_job(
            job_id,
            step_key="draft",
            step_status="running",
            detail="Writing section drafts with the configured model router.",
        )

    sections = [_draft_section(topic, plan, section, as_of) for section in plan.sections]

    if job_id:
        _update_job(
            job_id,
            step_key="draft",
            step_status="completed",
            detail=f"{len(sections)} sections drafted.",
        )
        _update_job(
            job_id,
            step_key="finalize",
            step_status="running",
            detail="Editing the final markdown.",
        )

    final = _finalize_blog(topic, plan, sections, as_of)
    response = BlogResponse(
        topic=topic,
        final=final,
        mode="hybrid_ollama_openrouter",
        needs_research=plan.needs_research,
        queries=plan.queries,
        image_specs=[],
    )

    if job_id:
        _update_job(
            job_id,
            status="completed",
            step_key="finalize",
            step_status="completed",
            detail="Blog ready.",
            result=response,
        )

    return response


def _run_job(job_id: str, request: BlogRequest) -> None:
    try:
        generate_blog(request.topic.strip(), request.as_of, job_id)
    except Exception as error:
        _update_job(job_id, status="failed", error=str(error))
        with _jobs_lock:
            job = _jobs[job_id]
            running_step = next((step for step in job.steps if step.status == "running"), None)
            if running_step:
                running_step.status = "failed"
                running_step.detail = str(error)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate-blog", response_model=BlogResponse)
def generate_blog_endpoint(request: BlogRequest) -> BlogResponse:
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required.")
    return generate_blog(topic, request.as_of)


@app.post("/generate-blog-jobs", response_model=BlogJobResponse)
def create_generate_blog_job(
    request: BlogRequest,
    background_tasks: BackgroundTasks,
) -> BlogJobResponse:
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required.")

    job_id = str(uuid4())
    job = BlogJobResponse(job_id=job_id, status="queued", steps=_initial_steps())
    with _jobs_lock:
        _jobs[job_id] = job

    background_tasks.add_task(_run_job, job_id, BlogRequest(topic=topic, as_of=request.as_of))
    return job


@app.get("/generate-blog-jobs/{job_id}", response_model=BlogJobResponse)
def get_generate_blog_job(job_id: str) -> BlogJobResponse:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        return job
