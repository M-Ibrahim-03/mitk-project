import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { createRun, getRun, subscribeToRun, type RunStatus } from "../api";

const sampleMessage =
  "Please check ticket TICKET-DEMO-1042. My name is Riley Sample, my email is riley@example.test, and my phone is 111-222-3333. Tell me its status and next update.";

type RequesterFields = { name: string; email: string; phone: string };

export function ChatPage() {
  const [message, setMessage] = useState(sampleMessage);
  const [requester, setRequester] = useState<RequesterFields>({
    name: "Riley Sample",
    email: "riley@example.test",
    phone: "111-222-3333",
  });
  const [runId, setRunId] = useState<string | null>(null);
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
      const created = await createRun({ message, requester });
      setRunId(created.run_id);
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
    <main className="page-shell">
      <header className="topbar">
        <Link aria-label="Veil home" className="brand" to="/">
          <span aria-hidden="true" className="brand-mark">V</span>
          <span>veil</span>
        </Link>
        <span className="local-badge"><span aria-hidden="true" className="status-dot" /> Runs locally</span>
      </header>

      <section className="chat-card surface-card">
        <span className="eyebrow">YOUR PRIVATE HELPDESK ASSISTANT</span>
        <h1>Veil Assistant</h1>
        <p className="intro-copy">
          Ask for help in your own words. Veil protects selected sensitive details
          before the local helpdesk receives your request.
        </p>

        <form aria-label="Send a message to the local agent" className="chat-form" onSubmit={submitMessage}>
          <label htmlFor="chat-message">Your message</label>
          <textarea
            id="chat-message"
            name="message"
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Describe your support request…"
            rows={5}
            value={message}
          />

          <fieldset className="requester-fields">
            <legend>Contact details <span>(synthetic demo data)</span></legend>
            <label>
              Name
              <input
                aria-label="Synthetic name"
                autoComplete="off"
                onChange={(event) => setRequester({ ...requester, name: event.target.value })}
                value={requester.name}
              />
            </label>
            <label>
              Email
              <input
                aria-label="Synthetic email"
                autoComplete="off"
                onChange={(event) => setRequester({ ...requester, email: event.target.value })}
                value={requester.email}
              />
            </label>
            <label>
              Phone
              <input
                aria-label="Synthetic phone"
                autoComplete="off"
                onChange={(event) => setRequester({ ...requester, phone: event.target.value })}
                value={requester.phone}
              />
            </label>
          </fieldset>

          <p className="privacy-note">
            <span aria-hidden="true">◆</span> Synthetic data only. Veil detects
            selected types of sensitive details; it cannot recognize every
            possible secret.
          </p>
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

        {error && <p className="error-banner" role="alert">{error}</p>}
        {answer && (
          <section aria-live="polite" className="answer-card">
            <span className="eyebrow">ANSWER FROM YOUR LOCAL AGENT</span>
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
          <div className="blocked-result" role="status">
            Veil stopped this request before the helpdesk received it. <Link to={`/runs/${encodeURIComponent(runId)}`}>View why</Link>
          </div>
        )}
      </section>

      <footer className="page-footer">A local demonstration of privacy at the tool boundary.</footer>
    </main>
  );
}
