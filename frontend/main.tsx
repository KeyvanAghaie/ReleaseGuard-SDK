import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, ArrowDownToLine, ArrowRight, BookOpen, Check, ChevronRight,
  CircleDot, Clock3, Code2, Cpu, Fingerprint, GitBranch, Layers3, Play,
  RotateCcw, ShieldCheck, Terminal, TriangleAlert, Zap } from "lucide-react";
import "./styles.css";

type Span = {
  schema_version: string; trace_id: string; span_id: string; parent_span_id: string | null;
  name: string; kind: string; source: string; started_at: string; ended_at: string;
  duration_ms: number; status: string; error_type: string | null; model: string | null;
  usage: { input_tokens: number; output_tokens: number } | null;
  estimated_cost_usd: string | null; instrumentation_errors: string[];
};
type Result = {
  scenario: string; mode: string; notice: string; spans: Span[]; answers: string[];
  dropped_spans: number; total_tokens: number; estimated_cost_usd: string | null; duration_ms: number;
};
type Scenario = "success" | "failure" | "concurrent";
const scenarios: { id: Scenario; title: string; detail: string; icon: typeof Check }[] = [
  { id: "success", title: "Successful generation", detail: "A nested retrieval → generation trace", icon: Check },
  { id: "failure", title: "Provider timeout", detail: "See an injected error propagate", icon: TriangleAlert },
  { id: "concurrent", title: "Concurrent requests", detail: "Two requests. Two isolated traces.", icon: GitBranch },
];

function App() {
  const [scenario, setScenario] = useState<Scenario>("success");
  const [result, setResult] = useState<Result | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"trace" | "json">("trace");
  const [section, setSection] = useState<"explorer" | "guide">("explorer");
  const selected = result?.spans.find(s => s.span_id === selectedId) ?? result?.spans[0];
  const roots = result?.spans.filter(s => !s.parent_span_id) ?? [];

  async function run() {
    setRunning(true); setError(null); setResult(null); setSelectedId(null);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch("/api/demo", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario }), signal: controller.signal
      });
      if (!response.ok) throw new Error("Demo request failed (" + response.status + ").");
      const data: Result = await response.json();
      setResult(data); setSelectedId(data.spans[0]?.span_id ?? null);
    } catch (err) {
      setError(err instanceof Error && err.name === "AbortError"
        ? "The demo timed out. Please try again."
        : "Could not reach the Python API. Start the backend and try again.");
    } finally { clearTimeout(timeout); setRunning(false); }
  }

  function download() {
    if (!result) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url; link.download = "releaseguard-" + result.scenario + ".json"; link.click();
    URL.revokeObjectURL(url);
  }

  return <div className="shell">
    <aside className="sidebar">
      <a className="brand" href="/" aria-label="ReleaseGuard home"><div className="brand-icon"><Layers3 size={23} /></div><span>Release<span className="brand-light">Guard</span><small>AI ENGINEERING TOOLKIT</small></span></a>
      <div className="workspace"><span className="workspace-avatar">RG</span><div>SDK workspace<small>Public playground</small></div><span className="version">v0.1</span></div>
      <div className="nav-label">WORKSPACE</div>
      <nav aria-label="Main navigation">
        <button className={section === "explorer" ? "nav-item active" : "nav-item"} onClick={() => setSection("explorer")}><Activity size={18} />Trace explorer<span className="nav-dot" /></button>
        <button className={section === "guide" ? "nav-item active" : "nav-item"} onClick={() => setSection("guide")}><BookOpen size={18} />Quick start</button>
        <a className="nav-item" href="/docs" target="_blank" rel="noreferrer"><Code2 size={18} />API reference<ArrowRight size={14} /></a>
      </nav>
      <div className="sidebar-bottom"><div className="series"><span className="series-number">01 / 09</span><h3>Small tools.<br />Release confidence.</h3><p>The first capability in the<br />AI ReleaseGuard portfolio.</p><div className="progress"><i /></div></div><div className="local-status"><span /> No API key required<ShieldCheck size={14} /></div></div>
    </aside>

    <main>
      <header className="topbar"><div>Workspace<ChevronRight size={14} /><strong>{section === "explorer" ? "Trace explorer" : "Quick start"}</strong></div><span className="mode-pill"><span />Interactive demo</span></header>
      <div className="content">
        <div className="page-heading"><div><div className="eyebrow">RELEASEGUARD SDK / PYTHON</div><h1>{section === "explorer" ? "Every call, accounted for." : "A few lines. A clearer picture."}</h1><p>{section === "explorer" ? "Follow an AI request from context to completion." : "Add explicit instrumentation to your Python application."}</p></div><span className="python-badge"><Terminal size={16} /> Python 3.12+</span></div>

        {section === "guide" ? <section className="guide panel"><div className="panel-title"><Code2 size={18} /><h2>Instrument your first call</h2></div><p>Install the SDK from a local checkout, then wrap a sync or async function.</p><pre>{'python -m pip install -e .\n\nfrom releaseguard_sdk import ReleaseGuard\n\nguard = ReleaseGuard()\n\n@guard.observe\nasync def answer():\n    return "Hello, world"\n\nwith guard.collect() as traces:\n    await answer()\n\nfor span in traces.snapshot():\n    print(span.model_dump_json(indent=2))'}</pre><div className="guide-grid"><div><ShieldCheck /><h3>Content stays private</h3><p>Arguments, return values and exception messages are not captured. Keep names and model labels free of sensitive content.</p></div><div><Cpu /><h3>Usage is explicit</h3><p>Provide a usage adapter or call record_usage. Unknown tokens and costs remain unknown.</p></div><div><GitBranch /><h3>Context stays isolated</h3><p>Nested async spans inherit their parent. Independent requests receive independent trace IDs.</p></div></div><button className="run-button" onClick={() => setSection("explorer")}>Open trace explorer<ArrowRight size={16} /></button></section> : <>
        <div className="notice"><div className="notice-icon"><CircleDot size={18} /></div><div><strong>Real instrumentation. Replayed responses.</strong><p>Python runs live. Model responses, token counts and delays are fixed demo fixtures. No external model calls.</p></div><span className="label">REPLAY MODE</span></div>

        <section className="scenario-panel panel" aria-label="Demo scenarios"><div className="panel-title"><span className="step">1</span><h2>Choose a scenario</h2><span className="subtle">Explore the SDK in action</span></div><div className="scenario-options">
          {scenarios.map(s => <button key={s.id} aria-pressed={scenario === s.id} disabled={running} className={"scenario " + (scenario === s.id ? "chosen" : "")} onClick={() => { setScenario(s.id); setResult(null); setError(null); }}><div className="scenario-icon"><s.icon size={18} /></div><div><strong>{s.title}</strong><small>{s.detail}</small></div><span className="radio">{scenario === s.id && <span />}</span></button>)}
        </div><div className="scenario-footer"><span><ShieldCheck size={14} /> Request-local traces · No stored prompts</span><button className="run-button" onClick={run} disabled={running}>{running ? <RotateCcw className="spin" size={15} /> : <Play size={15} fill="currentColor" />}{running ? "Running Python…" : "Run scenario"}</button></div></section>

        <div role="status" aria-live="polite" className={error ? "error-banner" : "sr-only"}>{error ?? (running ? "Running scenario" : result ? "Scenario completed. " + result.spans.length + " spans recorded." : "")}</div>
        <section className="metrics" aria-label="Run metrics">
          {[{ title: "Trace duration", value: result ? result.duration_ms.toFixed(1) : "—", unit: result ? "ms" : "", icon: Clock3, note: "Longest root · includes simulated delay" },
            { title: "Recorded spans", value: result ? String(result.spans.length) : "—", unit: "", icon: GitBranch, note: result ? roots.length + " isolated trace" + (roots.length > 1 ? "s" : "") : "Nested calls, linked automatically" },
            { title: "Token usage", value: result ? (result.total_tokens ? String(result.total_tokens) : "Unknown") : "—", unit: "", icon: Cpu, note: "Fixture input + output tokens" },
            { title: "Estimated cost", value: result?.estimated_cost_usd != null ? "$" + Number(result.estimated_cost_usd).toFixed(6) : "—", unit: "", icon: Zap, note: "Illustrative USD rates · not a bill" }].map(m => <div className="metric" key={m.title}><div className="metric-label">{m.title}<m.icon size={16} /></div><div className="metric-value">{m.value}<small>{m.unit}</small></div><div className="metric-note">{m.note}</div></div>)}
        </section>

        <section className="panel trace-panel"><div className="trace-header"><div className="panel-title"><span className="step">2</span><h2>Inspect the execution</h2>{result && <span className="completion"><span />Completed</span>}</div><button className="export-button" disabled={!result} onClick={download}><ArrowDownToLine size={15} />Export JSON</button></div><div className="tabs"><button className={tab === "trace" ? "selected" : ""} onClick={() => setTab("trace")}><GitBranch size={14} />Trace waterfall</button><button className={tab === "json" ? "selected" : ""} onClick={() => setTab("json")}><Code2 size={14} />Raw JSON</button><span>schema v1.0</span></div>
          {!result ? <div className="empty"><div className="empty-illustration"><Activity size={30} /></div><h3>{running ? "Following your request…" : "Your next trace starts here"}</h3><p>{running ? "Collecting nested spans from the Python SDK." : "Choose a scenario and run it to inspect timings, usage and errors."}</p><div className="empty-flow"><span>Request</span><ArrowRight size={13} /><span>Retrieve</span><ArrowRight size={13} /><span>Generate</span></div></div> :
          tab === "json" ? <pre className="raw-json">{JSON.stringify(result, null, 2)}</pre> :
          <div className="trace-content"><div className="waterfall"><div className="waterfall-head"><span>OPERATION</span><span>DURATION</span><span>EXECUTION TIMELINE</span></div>{roots.map((root, index) => <div className="trace-group" key={root.span_id}><div className="trace-id"><Fingerprint size={13} />TRACE {index + 1}<code>{root.trace_id.slice(0, 16)}…</code></div>{result.spans.filter(s => s.trace_id === root.trace_id).map(span => {
            const offset = Math.max(0, new Date(span.started_at).getTime() - new Date(root.started_at).getTime());
            const left = Math.min(97, offset / Math.max(root.duration_ms, 1) * 100);
            const width = Math.max(2, Math.min(100 - left, span.duration_ms / Math.max(root.duration_ms, 1) * 100));
            return <button key={span.span_id} className={"span-row " + (selected?.span_id === span.span_id ? "focused" : "")} onClick={() => setSelectedId(span.span_id)}><span className={"span-name " + (span.parent_span_id ? "child" : "")}><span className={"status-dot " + span.status} />{span.name}</span><span className="duration">{span.duration_ms.toFixed(1)} ms</span><span className="track"><span className={"bar " + span.status} style={{ marginLeft: left + "%", width: width + "%" }} /></span></button>;
          })}</div>)}<div className="waterfall-note"><span className="status-dot ok" /> Success <span className="status-dot error" /> Error <span>Click a span to inspect its metadata</span></div></div>
          <aside className="span-detail"><div className="detail-eyebrow">SPAN DETAILS</div><h3>{selected?.name}</h3><span className={"status-badge " + selected?.status}>{selected?.status}</span><dl><dt>Source</dt><dd>{selected?.source}</dd><dt>Model</dt><dd>{selected?.model ?? "Not provided"}</dd><dt>Input tokens</dt><dd>{selected?.usage?.input_tokens ?? "Unknown"}</dd><dt>Output tokens</dt><dd>{selected?.usage?.output_tokens ?? "Unknown"}</dd><dt>Estimated USD</dt><dd>{selected?.estimated_cost_usd ?? "Unknown"}</dd>{selected?.error_type && <><dt>Error type</dt><dd className="error-text">{selected.error_type}</dd></>}</dl><div className="detail-privacy"><ShieldCheck size={15} />Prompt and response content are not collected.</div></aside></div>}
        </section>
        <div className="bottom-grid"><div className="code-card"><div><Code2 size={17} /><h3>One decorator. Full visibility.</h3><button onClick={() => setSection("guide")}>Quick start<ArrowRight size={14} /></button></div><pre><span className="code-muted"># Keep your application logic. Add a trace.</span>{"\n"}<span className="code-accent">@guard.observe</span>(name=<span className="code-string">"llm.generate"</span>, kind=<span className="code-string">"llm"</span>){"\n"}<span className="code-purple">async def</span> generate_answer(prompt):{"\n"}{"    "}<span className="code-purple">return await</span> provider.generate(prompt)</pre></div><div className="principles"><ShieldCheck size={22} /><h3>Built to stay out of the way.</h3><p>Original results and exceptions are preserved. Export failures are isolated. Usage is recorded only when provided.</p><span>Sync + async <span>·</span> OpenTelemetry bridge <span>·</span> Typed contracts</span></div></div>
        </>}
        <footer><span><Layers3 size={14} /> ReleaseGuard SDK <span className="footer-version">v0.1.0</span></span><span>Instrument. Understand. Release with confidence.</span></footer>
      </div>
    </main>
  </div>;
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
