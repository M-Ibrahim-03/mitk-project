import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { createRun, getRun, subscribeToRun, type RunStatus } from "../api";

const sampleMessage =
  "Please check ticket TICKET-DEMO-1042. My name is Riley Sample, my email is riley@example.test, and my phone is +91 90000 00000. Aadhaar: 0000 0000 0000; bank account: 123456789012; card: 4111 1111 1111 1111; PAN: ABCDE1234F; IFSC: DEMO0001234; IBAN: GB82 WEST 1234 5698 7654 32. Tell me its status and next update.";

export function ChatPage() {
  const [message, setMessage] = useState(sampleMessage);
  const [runId, setRunId] = useState<string | null>(null);
  const [agentMode, setAgentMode] = useState<"deterministic" | "gemini">("deterministic");
  const [runStatus, setRunStatus] = useState<RunStatus | "idle">("idle");
  const [answer, setAnswer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [eventCount, setEventCount] = useState(0);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  useEffect(() => () => unsubscribeRef.current?.(), []);

  async function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRunStatus("queued");
    setAnswer(null);
    setError(null);
    setRunId(null);
    setEventCount(0);

    try {
      const created = await createRun({ message });
      setRunId(created.run_id);
      setAgentMode(created.agent_mode ?? "deterministic");
      setRunStatus("running");
      unsubscribeRef.current = subscribeToRun(
        created.run_id,
        (workflowEvent) => {
          setEventCount((count) => Math.max(count, workflowEvent.event_id + 1));
          if (workflowEvent.stage === "agent_response" && typeof workflowEvent.artifact === "string") {
            setAnswer(workflowEvent.artifact);
          }
        },
        async (status) => {
          try {
            const snapshot = await getRun(created.run_id);
            setAnswer(snapshot.agent_answer);
            setRunStatus(status);
            if (status === "failed") {
              const failure = snapshot.events.find((workflowEvent) => workflowEvent.status === "failed");
              setError(failure?.message ?? "The local agent run could not complete. Please try again.");
            }
          } catch {
            setRunStatus("failed");
            setError("The workflow finished, but Veil could not load the final answer.");
          }
        },
        (messageFromServer) => {
          setRunStatus("failed");
          setError(messageFromServer);
        },
      );
    } catch (requestError) {
      setRunStatus("failed");
      setError(requestError instanceof Error ? requestError.message : "The local workflow could not start.");
    }
  }

  function resetConversation() {
    unsubscribeRef.current?.();
    unsubscribeRef.current = null;
    setRunId(null);
    setRunStatus("idle");
    setAnswer(null);
    setError(null);
    setEventCount(0);
  }

  const isBusy = runStatus === "queued" || runStatus === "running";

  return (
    <main className="page-shell chat-page">
      <header className="topbar">
        <Link aria-label="Veil home" className="brand" to="/">
          <span aria-hidden="true" className="brand-mark">V</span>
          <span>veil</span>
        </Link>
        <span className="local-badge"><span aria-hidden="true" className="status-dot" /> {agentMode === "gemini" ? "Gemini agent · local helpdesk" : "Offline local agent"}</span>
      </header>

      <section aria-label="Veil assistant chat" className="chat-card chat-card--glass">
        <section aria-label="Assistant introduction" className="chat-hero">
          <div className="chat-hero__copy">
            <span className="eyebrow">YOUR PRIVATE HELPDESK ASSISTANT</span>
            <h1>Veil Assistant</h1>
            <p className="intro-copy">
              Ask for help in your own words. Veil protects selected sensitive details
              before the local helpdesk receives your request.
            </p>
          </div>

          <aside className="chat-privacy-tile">
            <span aria-hidden="true" className="chat-privacy-tile__mark">◈</span>
            <p className="privacy-note">
              Synthetic data only. Veil checks selected email, phone, Aadhaar, card,
              and bank identifier patterns. Detection is limited and can miss other
              or obscured secrets.
            </p>
          </aside>
          <span aria-hidden="true" className="chat-hero__orb" />
        </section>

        <section aria-label="Message workspace" className="chat-workspace">
          <div className="chat-workspace__heading">
            <span className="chat-kicker">A LOCAL CONVERSATION</span>
            <h2>How can we help?</h2>
            <p>
              Use synthetic data. A valid ticket must exist in the local helpdesk;
              this demo accepts only TICKET-DEMO-1042. Include it in your message.
              Missing or other ticket IDs are rejected.
            </p>
          </div>

          <form aria-label="Send a message to the local agent" className="chat-form" onSubmit={submitMessage}>
            <div className="chat-message-tile">
              <label htmlFor="chat-message">Your message</label>
              <textarea
                id="chat-message"
                name="message"
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Describe your support request…"
                rows={5}
                value={message}
              />
            </div>

            <button className="primary-button" disabled={isBusy || !message.trim()} type="submit">
              {isBusy ? "Veil is handling your request…" : "Send message"}
              {!isBusy && <span aria-hidden="true">↗</span>}
            </button>
            {isBusy && (
              <p aria-live="polite" className="run-progress">
                <span className="status-dot" /> Receiving real workflow events · {eventCount} steps recorded
              </p>
            )}
          </form>
        </section>

        {error && (
          <p className="error-banner chat-feedback" role="alert">
            {error}
            {runId && runStatus === "failed" && (
              <> <Link to={`/runs/${encodeURIComponent(runId)}`}>View failed workflow</Link></>
            )}
          </p>
        )}
        {answer && (
          <section aria-label="Agent answer" aria-live="polite" className="answer-card">
            <span className="eyebrow">ANSWER FROM {agentMode === "gemini" ? "GEMINI" : "OFFLINE LOCAL AGENT"}</span>
            <p>{answer}</p>
            {runId && (
              <Link className="workflow-link" to={`/runs/${encodeURIComponent(runId)}`}>
                View animated workflow <span aria-hidden="true">→</span>
              </Link>
            )}
            <button className="secondary-button" onClick={resetConversation} type="button">Start another request</button>
          </section>
        )}
        {runStatus === "blocked" && runId && (
          <div className="blocked-result chat-feedback" role="status">
            Veil stopped this request before the helpdesk received it. <Link to={`/runs/${encodeURIComponent(runId)}`}>View why</Link>
          </div>
        )}
      </section>

      <footer className="page-footer">A local demonstration of privacy at the tool boundary.</footer>
    </main>
  );
}
