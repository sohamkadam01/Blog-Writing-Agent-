import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  CalendarDays,
  CheckCircle2,
  Circle,
  Clipboard,
  Download,
  FileText,
  Loader2,
  PenLine,
  Search,
  Sparkles,
  XCircle,
} from "lucide-react";

type BlogResponse = {
  topic: string;
  final: string;
  mode?: string | null;
  needs_research?: boolean | null;
  queries: string[];
  image_specs: Array<{
    placeholder?: string;
    filename?: string;
    alt?: string;
    caption?: string;
  }>;
};

type ProcessStep = {
  key: string;
  label: string;
  status: "pending" | "running" | "completed" | "failed";
  detail?: string | null;
};

type BlogJobResponse = {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  steps: ProcessStep[];
  result?: BlogResponse | null;
  error?: string | null;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8010";

const starterTopics = [
  "Self Attention in Transformer Architecture",
  "Building a RAG pipeline with evaluation",
  "Latest AI coding agents and developer workflows",
];

export function App() {
  const [topic, setTopic] = useState(starterTopics[0]);
  const [asOf, setAsOf] = useState("");
  const [blog, setBlog] = useState<BlogResponse | null>(null);
  const [error, setError] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [view, setView] = useState<"preview" | "markdown">("preview");
  const [job, setJob] = useState<BlogJobResponse | null>(null);

  const wordCount = useMemo(() => {
    if (!blog?.final) return 0;
    return blog.final.trim().split(/\s+/).filter(Boolean).length;
  }, [blog]);

  const activeStep = job?.steps.find((step) => step.status === "running")
    ?? job?.steps.find((step) => step.status === "failed")
    ?? job?.steps.find((step) => step.status === "pending")
    ?? job?.steps.at(-1);

  async function generateBlog() {
    const cleanedTopic = topic.trim();
    if (!cleanedTopic) {
      setError("Enter a blog topic first.");
      return;
    }

    setIsGenerating(true);
    setError("");
    setBlog(null);
    setJob(null);

    try {
      const response = await fetch(`${API_BASE}/generate-blog-jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: cleanedTopic,
          as_of: asOf || undefined,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "The backend could not generate the blog.");
      }

      setJob(data);

      let currentJob = data as BlogJobResponse;
      while (currentJob.status === "queued" || currentJob.status === "running") {
        await new Promise((resolve) => window.setTimeout(resolve, 1500));

        const jobResponse = await fetch(`${API_BASE}/generate-blog-jobs/${currentJob.job_id}`);
        const nextJob = await jobResponse.json();
        if (!jobResponse.ok) {
          throw new Error(nextJob.detail ?? "Could not read job progress from the backend.");
        }

        currentJob = nextJob;
        setJob(nextJob);
      }

      if (currentJob.status === "failed") {
        throw new Error(currentJob.error ?? "The backend could not generate the blog.");
      }

      if (!currentJob.result) {
        throw new Error("The backend completed the job without returning a blog.");
      }

      setBlog(currentJob.result);
      setView("preview");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Something went wrong.");
    } finally {
      setIsGenerating(false);
    }
  }

  async function copyMarkdown() {
    if (blog?.final) {
      await navigator.clipboard.writeText(blog.final);
    }
  }

  function downloadMarkdown() {
    if (!blog?.final) return;

    const blob = new Blob([blog.final], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${blog.topic.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="app-shell">
      <aside className="control-panel" aria-label="Blog controls">
        <div className="brand">
          <div className="brand-mark">
            <PenLine size={22} />
          </div>
          <div>
            <h1>Blog Writing Agent</h1>
            <p>Plan, research, draft, and package technical posts.</p>
          </div>
        </div>

        <section className="compose-panel">
          <label htmlFor="topic">Topic</label>
          <textarea
            id="topic"
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            placeholder="What should the agent write about?"
          />

          <div className="date-row">
            <label htmlFor="as-of">
              <CalendarDays size={16} />
              As of
            </label>
            <input
              id="as-of"
              type="date"
              value={asOf}
              onChange={(event) => setAsOf(event.target.value)}
            />
          </div>

          <button className="primary-action" onClick={generateBlog} disabled={isGenerating}>
            {isGenerating ? <Loader2 className="spin" size={18} /> : <Sparkles size={18} />}
            {isGenerating ? "Generating" : "Generate blog"}
          </button>

          {error && <p className="error-message">{error}</p>}
        </section>

        {job && (
          <section className="process-panel" aria-label="Generation progress">
            <h2>Agent Process</h2>
            <div className="process-list">
              {job.steps.map((step) => (
                <div className={`process-step ${step.status}`} key={step.key}>
                  <span className="step-icon">
                    {step.status === "completed" && <CheckCircle2 size={17} />}
                    {step.status === "running" && <Loader2 className="spin" size={17} />}
                    {step.status === "failed" && <XCircle size={17} />}
                    {step.status === "pending" && <Circle size={17} />}
                  </span>
                  <span>
                    <strong>{step.label}</strong>
                    {step.detail && <small>{step.detail}</small>}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="starter-panel" aria-label="Starter topics">
          <h2>Starter Topics</h2>
          <div className="topic-list">
            {starterTopics.map((item) => (
              <button key={item} onClick={() => setTopic(item)}>
                {item}
              </button>
            ))}
          </div>
        </section>

        <section className="status-panel">
          <div>
            <span>Backend</span>
            <strong>{API_BASE}</strong>
          </div>
          <div>
            <span>Research</span>
            <strong>{blog?.needs_research ? "Enabled" : "Auto"}</strong>
          </div>
        </section>
      </aside>

      <section className="workspace">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">Draft Workspace</p>
            <h2>{blog?.topic ?? "Your generated blog will appear here"}</h2>
          </div>

          <div className="actions">
            <button
              className={view === "preview" ? "active" : ""}
              onClick={() => setView("preview")}
              disabled={!blog}
            >
              <FileText size={17} />
              Preview
            </button>
            <button
              className={view === "markdown" ? "active" : ""}
              onClick={() => setView("markdown")}
              disabled={!blog}
            >
              <Search size={17} />
              Markdown
            </button>
            <button onClick={copyMarkdown} disabled={!blog}>
              <Clipboard size={17} />
              Copy
            </button>
            <button onClick={downloadMarkdown} disabled={!blog}>
              <Download size={17} />
              Export
            </button>
          </div>
        </header>

        {blog ? (
          <>
            <div className="metric-strip">
              <div>
                <span>Mode</span>
                <strong>{blog.mode ?? "closed_book"}</strong>
              </div>
              <div>
                <span>Words</span>
                <strong>{wordCount.toLocaleString()}</strong>
              </div>
              <div>
                <span>Queries</span>
                <strong>{blog.queries.length}</strong>
              </div>
              <div>
                <span>Images</span>
                <strong>{blog.image_specs.length}</strong>
              </div>
            </div>

            <div className="output-area">
              {view === "preview" ? (
                <article className="markdown-preview">
                  <ReactMarkdown>{blog.final}</ReactMarkdown>
                </article>
              ) : (
                <pre className="markdown-source">{blog.final}</pre>
              )}
            </div>
          </>
        ) : job ? (
          <div className={`progress-state ${job.status}`}>
            <div className="progress-state-header">
              {job.status === "failed" ? (
                <XCircle size={34} />
              ) : (
                <Loader2 className="spin" size={34} />
              )}
              <div>
                <p className="eyebrow">Agent Status</p>
                <h2>
                  {job.status === "failed"
                    ? "Generation failed"
                    : activeStep?.label ?? "Generating blog"}
                </h2>
              </div>
            </div>

            {job.status === "failed" && (
              <p className="large-error">{job.error ?? error ?? "The backend could not generate the blog."}</p>
            )}

            {job.status !== "failed" && activeStep?.detail && (
              <p className="progress-detail">{activeStep.detail}</p>
            )}

            <div className="wide-process-list">
              {job.steps.map((step) => (
                <div className={`process-step ${step.status}`} key={step.key}>
                  <span className="step-icon">
                    {step.status === "completed" && <CheckCircle2 size={18} />}
                    {step.status === "running" && <Loader2 className="spin" size={18} />}
                    {step.status === "failed" && <XCircle size={18} />}
                    {step.status === "pending" && <Circle size={18} />}
                  </span>
                  <span>
                    <strong>{step.label}</strong>
                    {step.detail && <small>{step.detail}</small>}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="empty-state">
            <Sparkles size={36} />
            <h2>Ready for a technical draft</h2>
            <p>
              Enter a topic, choose an optional date context, and the agent will generate a
              structured markdown blog through your backend workflow.
            </p>
          </div>
        )}
      </section>
    </main>
  );
}
