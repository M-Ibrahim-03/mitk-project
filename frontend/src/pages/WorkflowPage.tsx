import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import { Link } from "react-router-dom";

import { getRun, subscribeToRun, type RunStatus, type WorkflowEvent, type WorkflowSnapshot } from "../api";

type WorkflowPageProps = { runId: string };
type NodeStatus = "waiting" | "active" | "complete" | "blocked" | "failed";

const nodeDefinitions = [
  { id: "user", label: "User request", type: "user", watches: ["request_received"] },
  { id: "agent", label: "AI agent", type: "agent", watches: ["agent_planning", "tool_call_prepared"] },
  { id: "veil", label: "Veil privacy layer", type: "veil", watches: ["privacy_scan", "egress_gate"] },
  { id: "tool", label: "Helpdesk tool", type: "tool", watches: ["helpdesk", "tool_response"] },
  { id: "restore", label: "Veil restoration", type: "veil", watches: ["response_restore"] },
  { id: "answer", label: "Agent answer", type: "agent", watches: ["agent_response"] },
] as const;

function mergeEvents(current: WorkflowEvent[], incoming: WorkflowEvent[]) {
  const byId = new Map(current.map((event) => [event.event_id, event]));
  incoming.forEach((event) => byId.set(event.event_id, event));
  return [...byId.values()].sort((left, right) => left.event_id - right.event_id);
}

function latestEvent(events: WorkflowEvent[], stage: string) {
  return [...events].reverse().find((event) => event.stage === stage && event.status !== "active");
}

function nodeStatus(events: WorkflowEvent[], watches: readonly string[]): NodeStatus {
  const latest = [...events].reverse().find((event) => watches.includes(event.stage));
  if (!latest) return "waiting";
  if (latest.status === "blocked" || latest.status === "failed") return latest.status;
  if (latest.status === "active") return "active";
  return latest.status === "complete" ? "complete" : "waiting";
}

function objectValue(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function pretty(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value, null, 2) ?? "";
}

function HighlightedData({ value }: { value: unknown }) {
  const formatted = pretty(value);
  const parts = formatted.split(/(\[\[[A-Z_]+:V[A-F0-9]+\]\])/g);
  return (
    <pre className="evidence-data">
      {parts.map((part, index) =>
        /^\[\[[A-Z_]+:V[A-F0-9]+\]\]$/.test(part) ? (
          <mark className="token-highlight" key={`${part}-${index}`}>{part}</mark>
        ) : part,
      )}
    </pre>
  );
}

function Evidence({ label, value, tone = "neutral" }: { label: string; value: unknown; tone?: string }) {
  if (value === undefined || value === null) return null;
  return (
    <div className={`evidence-panel evidence-panel--${tone}`}>
      <span className="evidence-label">{label}</span>
      <HighlightedData value={value} />
    </div>
  );
}

function RunNode({
  index,
  label,
  type,
  status,
  connectsToNext = false,
  connectorLabel,
  children,
}: {
  index: number;
  label: string;
  type: string;
  status: NodeStatus;
  connectsToNext?: boolean;
  connectorLabel?: string;
  children: React.ReactNode;
}) {
  const prefersReducedMotion = useReducedMotion();
  const badge = status === "complete" ? "✓" : status === "blocked" ? "×" : status === "failed" ? "!" : index.toString().padStart(2, "0");
  const side = index % 2 === 1 ? "left" : "right";
  const routePath = side === "left"
    ? "M 72 35 C 96 35, 100 88, 40 100"
    : "M 28 35 C 4 35, 0 88, 60 100";
  return (
    <li aria-label={`${label}, ${status}`} className={`flow-node flow-node--${type} flow-node--${status} flow-node--${side}`}>
      <article className="flow-node__card">
        <header className="flow-node__header">
          <div className="flow-node__identity">
            <motion.div
              animate={status === "active" && !prefersReducedMotion ? { scale: [1, 1.08, 1] } : { scale: 1 }}
              className="flow-node__circle"
              transition={{ duration: 1.25, repeat: status === "active" && !prefersReducedMotion ? Infinity : 0 }}
            >
              <span>{badge}</span>
              {status === "active" && <span aria-hidden="true" className="flow-node__pulse" />}
            </motion.div>
            <div className="flow-node__heading">
              <span className="flow-node__stage">STEP {index.toString().padStart(2, "0")} <i /> {type.toUpperCase()}</span>
              <h2>{label}</h2>
            </div>
          </div>
          <span className="node-status"><i aria-hidden="true" />{status}</span>
        </header>
        {children}
      </article>
      {connectsToNext && (
        <span
          aria-hidden="true"
          className={`flow-connector flow-connector--${side}${status === "complete" ? " flow-connector--flowing" : status === "blocked" || status === "failed" ? " flow-connector--blocked" : ""}`}
          data-testid="workflow-connector"
        >
          <svg className="flow-connector__svg" preserveAspectRatio="none" viewBox="0 0 100 100">
            <defs>
              <marker id={`workflow-arrow-${index}`} markerHeight="8" markerUnits="strokeWidth" markerWidth="8" orient="auto" refX="7" refY="4" viewBox="0 0 8 8">
                <path className="flow-connector__arrowhead" d="M 0 0 L 8 4 L 0 8 z" />
              </marker>
            </defs>
            <path className="flow-connector__path" d={routePath} markerEnd={`url(#workflow-arrow-${index})`} />
            <path className="flow-connector__signal" d={routePath} />
          </svg>
          {connectorLabel && <span className="flow-connector__label">{connectorLabel}</span>}
        </span>
      )}
    </li>
  );
}

function RunEvidence({ events, snapshot }: { events: WorkflowEvent[]; snapshot: WorkflowSnapshot | null }) {
  const event = (stage: string) => latestEvent(events, stage);
  const requestArtifact = objectValue(event("request_received")?.artifact);
  const agentArtifact = objectValue(event("tool_call_prepared")?.artifact);
  const protectedPrompt = objectValue(event("model_input_protection")?.artifact)?.protected_prompt;
  const modelAnswer = event("agent_model_answer")?.artifact;
  const scanArtifact = objectValue(event("privacy_scan")?.artifact);
  const sanitizedPayload = scanArtifact?.sanitized_payload;
  const detections = Array.isArray(scanArtifact?.detections) ? scanArtifact.detections : [];
  const helpdeskPayload = event("helpdesk")?.artifact ?? null;
  const tokenizedResponse = event("tool_response")?.artifact;
  const modelToolContext = event("model_tool_context")?.artifact;
  const restoredResponse = event("response_restore")?.artifact;
  const audit = snapshot?.audit;
  const egress = event("egress_gate");
  const agentAnswer = event("agent_response")?.artifact;
  const fallback = event("agent_fallback");

  return (
    <ol aria-label="Workflow steps" className="workflow-steps">
      <RunNode index={1} label="User request" type="user" status={nodeStatus(events, nodeDefinitions[0].watches)} connectsToNext connectorLabel="MESSAGE">
        <p className="node-explanation">The original message enters the local agent.</p>
        <Evidence label="ORIGINAL MESSAGE · STAYS LOCAL" value={requestArtifact?.message} tone="original" />
      </RunNode>

      <RunNode index={2} label="AI agent" type="agent" status={nodeStatus(events, nodeDefinitions[1].watches)} connectsToNext connectorLabel="TOOL CALL">
        <p className="node-explanation">{fallback ? "Gemini was unavailable, so the deterministic local agent continued this same run." : snapshot?.agent_mode === "gemini" ? "Gemini sees Veil's tokenized prompt and proposes a call; Veil still validates it." : "The offline agent decides which helpdesk action fits."}</p>
        {snapshot?.agent_mode && <div className="tool-choice"><span>AGENT MODE</span><strong>{fallback ? "Deterministic fallback · offline" : snapshot.agent_mode === "gemini" ? "Gemini · networked" : "Deterministic · offline"}</strong></div>}
        {fallback && <div className="fallback-notice" role="status"><strong>LOCAL FALLBACK USED</strong><span>{fallback.message}</span></div>}
        {typeof protectedPrompt === "string" && <Evidence label="TOKENIZED PROMPT SENT TO GEMINI" value={protectedPrompt} tone="protected" />}
        {agentArtifact && <div className="tool-choice"><span>TOOL SELECTED</span><strong>{String(agentArtifact.tool_name)}</strong></div>}
        <Evidence label="AGENT'S PREPARED REQUEST" value={agentArtifact?.payload} />
      </RunNode>

      <RunNode index={3} label="Veil privacy layer" type="veil" status={nodeStatus(events, nodeDefinitions[2].watches)} connectsToNext connectorLabel="PROTECTED PAYLOAD">
        <p className="node-explanation">Veil replaces detected values, then checks the exact outgoing payload.</p>
        <div className="privacy-receipt">
          <span className={`receipt-shield ${egress?.status === "complete" ? "is-safe" : egress?.status === "blocked" ? "is-blocked" : ""}`} aria-hidden="true">
            {egress?.status === "complete" ? "✓" : egress?.status === "blocked" ? "×" : "◇"}
          </span>
          <div>
            <strong>{egress?.status === "complete" ? "LEAK CHECK PASSED" : egress?.status === "blocked" ? "EGRESS BLOCKED" : "CHECKING BEFORE TOOL"}</strong>
            <span>{Number(audit?.unique_token_count ?? detections.length)} sensitive values protected · {egress?.status === "complete" ? "0 originals sent" : "helpdesk not reached"}</span>
          </div>
        </div>
        <Evidence label="PROTECTED COPY · VERIFIED FOR EGRESS" value={sanitizedPayload} tone="protected" />
        {egress?.status === "blocked" && <p className="blocked-note">{egress.message}</p>}
      </RunNode>

      <RunNode index={4} label="Helpdesk tool" type="tool" status={nodeStatus(events, nodeDefinitions[3].watches)} connectsToNext connectorLabel="TOOL REPLY">
        <p className="node-explanation">The offline helpdesk sees only the payload captured after Veil's check.</p>
        <Evidence label="EXACTLY WHAT THE TOOL RECEIVED" value={helpdeskPayload} tone="protected" />
        <Evidence label="TOOL'S TOKENIZED REPLY" value={tokenizedResponse} tone="tokenized" />
        {snapshot?.agent_mode === "gemini" && <Evidence label="TOKENIZED TOOL CONTEXT SENT TO GEMINI" value={modelToolContext} tone="protected" />}
        {!helpdeskPayload && <p className="not-reached">{egress?.status === "blocked" ? "Not reached — Veil stopped the call." : "Waiting for Veil's egress check…"}</p>}
      </RunNode>

      <RunNode index={5} label="Veil restoration" type="veil" status={nodeStatus(events, nodeDefinitions[4].watches)} connectsToNext connectorLabel="RESTORED CONTEXT">
        <p className="node-explanation">Only the trusted return path maps this run's tokens back.</p>
        <Evidence label="TRUSTED REPLY · VALUES RESTORED" value={restoredResponse} tone="restored" />
        {!restoredResponse && <p className="not-reached">Waiting for a safe tool reply.</p>}
      </RunNode>

      <RunNode index={6} label="Agent answer" type="agent" status={nodeStatus(events, nodeDefinitions[5].watches)}>
        <p className="node-explanation">{fallback ? "The deterministic local agent answered from Veil's restored response." : snapshot?.agent_mode === "gemini" ? "Veil restores only known tokens locally after Gemini drafts its answer." : "The offline agent answers using Veil's restored response."}</p>
        {typeof modelAnswer === "string" && <Evidence label="TOKENIZED MODEL ANSWER · BEFORE LOCAL RESTORATION" value={modelAnswer} tone="tokenized" />}
        {typeof agentAnswer === "string" ? (
          <div className="agent-answer-evidence">{agentAnswer}</div>
        ) : <p className="not-reached">The agent has not answered yet.</p>}
      </RunNode>
    </ol>
  );
}

function mergeSnapshotEvents(current: WorkflowEvent[], snapshot: WorkflowSnapshot) {
  return mergeEvents(current, snapshot.events);
}

export function WorkflowPage({ runId }: WorkflowPageProps) {
  const prefersReducedMotion = useReducedMotion();
  const [snapshot, setSnapshot] = useState<WorkflowSnapshot | null>(null);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [status, setStatus] = useState<RunStatus | "loading">("loading");
  const [error, setError] = useState<string | null>(null);
  const eventsRef = useRef(events);
  eventsRef.current = events;

  useEffect(() => {
    let active = true;
    const closeStream = subscribeToRun(
      runId,
      (event) => {
        if (!active) return;
        setEvents((current) => mergeEvents(current, [event]));
        setStatus("running");
      },
      (finishedStatus) => {
        if (!active) return;
        setStatus(finishedStatus);
        void getRun(runId).then((current) => {
          if (!active) return;
          setSnapshot(current);
          setEvents((eventsNow) => mergeSnapshotEvents(eventsNow, current));
        }).catch(() => undefined);
      },
      (message) => {
        if (active) setError(message);
      },
    );
    void getRun(runId).then((current) => {
      if (!active) return;
      setSnapshot(current);
      setEvents((existing) => mergeSnapshotEvents(existing, current));
      setStatus(current.status);
    }).catch((loadError: unknown) => {
      if (active) {
        setStatus("failed");
        setError(loadError instanceof Error ? loadError.message : "This workflow run could not be loaded.");
      }
    });
    return () => {
      active = false;
      closeStream();
    };
  }, [runId]);

  const [visibleEventCount, setVisibleEventCount] = useState(0);
  useEffect(() => {
    if (prefersReducedMotion) {
      setVisibleEventCount(events.length);
    }
  }, [events.length, prefersReducedMotion]);
  useEffect(() => {
    if (prefersReducedMotion) return;
    const timer = window.setInterval(() => {
      setVisibleEventCount((count) =>
        count < eventsRef.current.length ? count + 1 : count,
      );
    }, 120);
    return () => window.clearInterval(timer);
  }, [prefersReducedMotion]);

  const visibleEvents = events.slice(0, visibleEventCount);
  const visualStatus = status === "complete" && visibleEventCount < events.length ? "replaying" : status;
  const fallbackUsed = events.some((event) => event.stage === "agent_fallback" && event.status === "complete");
  const failedEvent = [...events].reverse().find((event) => event.status === "failed");
  const failureMessage = error ?? failedEvent?.message;

  return (
    <main className="page-shell workflow-shell">
      <header className="topbar">
        <Link aria-label="Veil home" className="brand" to="/">
          <span aria-hidden="true" className="brand-mark">V</span><span>veil</span>
        </Link>
        <Link className="text-link" to="/">Back to chat</Link>
      </header>

      <section className="surface-card workflow-card">
        <div className="workflow-heading">
          <div>
            <span className="eyebrow"><i aria-hidden="true" /> VEIL / LIVE PRIVACY TRACE</span>
            <h1>Every handoff,<br />in full view.</h1>
            <p className="intro-copy">Follow one message across Veil's trust boundary, from the agent's request to the helpdesk's exact receipt and the restored answer.</p>
          </div>
          <span className={`live-run-badge live-run-badge--${visualStatus}`}><span aria-hidden="true" />{visualStatus === "complete" ? "Trace complete" : visualStatus === "replaying" ? "Replaying trace" : visualStatus}</span>
        </div>

        <div className="run-overview">
          <span className="run-overview__id"><i aria-hidden="true">✳</i><span>RUN ID <code>{runId}</code></span></span>
          <span className="run-overview__progress"><strong>{visibleEvents.length}</strong><span>/ {snapshot?.event_count ?? "—"} events replayed</span></span>
          {snapshot?.audit && (
            <span className="run-overview__safety">
              {snapshot.audit.egress_verified ? "✓ Egress verified" : status === "blocked" ? "× Blocked before tool" : "◌ Safety check pending"}
            </span>
          )}
        </div>

        {failureMessage && <p className="error-banner" role="alert">{failureMessage}</p>}
        <RunEvidence events={visibleEvents} snapshot={snapshot} />
        <div className="workflow-caption">
          <span aria-hidden="true" className="caption-lock">◆</span>
          <p>Evidence comes from this run's actual Veil events and the payload captured by the local helpdesk.</p>
        </div>
      </section>
      <footer className="page-footer">Synthetic demo data · {fallbackUsed ? "Gemini selected · deterministic fallback used" : snapshot?.agent_mode === "gemini" ? "Gemini agent · networked" : "Offline deterministic agent"} · Offline simulated helpdesk</footer>
    </main>
  );
}
