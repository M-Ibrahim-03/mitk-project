import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getRun, subscribeToRun } from "../api";
import type { WorkflowSnapshot } from "../api";
import { WorkflowPage } from "./WorkflowPage";

vi.mock("../api", () => ({
  getRun: vi.fn(),
  subscribeToRun: vi.fn(() => vi.fn()),
}));

const snapshot: WorkflowSnapshot = {
  run_id: "run-demo-live",
  status: "complete",
  event_count: 8,
  events: [
    {
      event_id: 0,
      run_id: "run-demo-live",
      stage: "request_received",
      status: "complete",
      message: "User request received.",
      artifact: { message: "My name is Riley Sample, email riley@example.test", requester: {} },
    },
    {
      event_id: 1,
      run_id: "run-demo-live",
      stage: "tool_call_prepared",
      status: "complete",
      message: "Agent prepared a call.",
      artifact: { tool_name: "lookup_helpdesk_ticket", payload: { user_message: "email riley@example.test" } },
    },
    {
      event_id: 2,
      run_id: "run-demo-live",
      stage: "privacy_scan",
      status: "complete",
      message: "Veil protected the outgoing request.",
      artifact: {
        sanitized_payload: { user_message: "email [[EMAIL:VABCDEF1234]]" },
        detections: [{ category: "email" }, { category: "name" }],
      },
    },
    {
      event_id: 3,
      run_id: "run-demo-live",
      stage: "egress_gate",
      status: "complete",
      message: "Veil verified the outgoing request.",
      artifact: { user_message: "email [[EMAIL:VABCDEF1234]]" },
    },
    {
      event_id: 4,
      run_id: "run-demo-live",
      stage: "helpdesk",
      status: "complete",
      message: "Helpdesk received the protected request.",
      artifact: { user_message: "email [[EMAIL:VABCDEF1234]]" },
    },
    {
      event_id: 5,
      run_id: "run-demo-live",
      stage: "tool_response",
      status: "complete",
      message: "Helpdesk returned its tokenized reply.",
      artifact: { message_echo: "email [[EMAIL:VABCDEF1234]]" },
    },
    {
      event_id: 6,
      run_id: "run-demo-live",
      stage: "response_restore",
      status: "complete",
      message: "Veil restored the trusted response.",
      artifact: { message_echo: "email riley@example.test" },
    },
    {
      event_id: 7,
      run_id: "run-demo-live",
      stage: "agent_response",
      status: "complete",
      message: "The agent answered.",
      artifact: "Riley Sample, your request is received.",
    },
  ],
  tool_payload: { user_message: "email [[EMAIL:VABCDEF1234]]" },
  tool_response: { message_echo: "email [[EMAIL:VABCDEF1234]]" },
  restored_response: { message_echo: "email riley@example.test" },
  agent_answer: "Riley Sample, your request is received.",
  agent_mode: "deterministic",
  audit: { status: "allowed", detection_count: 2, unique_token_count: 2, leakage_count: 0, egress_verified: true },
};

describe("live workflow visualizer", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    vi.mocked(getRun).mockResolvedValue(snapshot);
  });

  it("keeps all six stages and their connectors visible while a run is replaying", () => {
    render(
      <MemoryRouter>
        <WorkflowPage runId="run-demo-live" />
      </MemoryRouter>,
    );

    const stages = ["User request", "AI agent", "Veil privacy layer", "Helpdesk tool", "Veil restoration", "Agent answer"];
    stages.forEach((stage) => {
      expect(screen.getByRole("listitem", { name: new RegExp(`${stage}, waiting`, "i") })).toBeInTheDocument();
    });
    const connectors = screen.getAllByTestId("workflow-connector");
    expect(connectors).toHaveLength(5);
    connectors.forEach((connector, index) => {
      expect(connector).toHaveAttribute("aria-hidden", "true");
      const route = connector.querySelector(".flow-connector__path");
      expect(route).not.toBeNull();
      expect(connector.querySelector(".flow-connector__arrowhead")).not.toBeNull();
      expect(connector.querySelector(".flow-connector__signal")).not.toBeNull();
      expect(route?.getAttribute("d")?.startsWith(index % 2 === 0 ? "M 72 35" : "M 28 35")).toBe(true);
      expect(route?.getAttribute("d")?.endsWith(index % 2 === 0 ? "40 100" : "60 100")).toBe(true);
    });
  });

  it("shows actual message, protected tool payload, restored reply, and agent answer", async () => {
    render(
      <MemoryRouter>
        <WorkflowPage runId="run-demo-live" />
      </MemoryRouter>,
    );

    expect(await screen.findByText("My name is Riley Sample, email riley@example.test")).toBeInTheDocument();
    const firstStage = await screen.findByRole("listitem", { name: /user request, complete/i });
    expect(within(firstStage).getByTestId("workflow-connector")).toHaveClass("flow-connector--flowing");
    expect(
      await screen.findByText("Riley Sample, your request is received.", {}, { timeout: 3000 }),
    ).toBeInTheDocument();
    const veil = screen.getByRole("listitem", { name: /veil privacy layer/i });
    expect(within(veil).getByText(/2 sensitive values protected/i)).toBeInTheDocument();
    const helpdesk = screen.getByRole("listitem", { name: /helpdesk/i });
    expect(within(helpdesk).getAllByText(/VABCDEF1234/i)).toHaveLength(2);
    expect(within(helpdesk).queryByText(/riley@example\.test/i)).not.toBeInTheDocument();
    expect(screen.getByText(/trusted reply · values restored/i)).toBeInTheDocument();
    expect(screen.queryByText(/visual preview/i)).not.toBeInTheDocument();
    expect(subscribeToRun).toHaveBeenCalledWith("run-demo-live", expect.any(Function), expect.any(Function), expect.any(Function));
  });

  it("shows a blocked run stopping at Veil with the helpdesk marked not reached", async () => {
    const blocked: WorkflowSnapshot = {
      ...snapshot,
      status: "blocked",
      events: snapshot.events.slice(0, 4).map((event, index) =>
        index === 3
          ? { ...event, status: "blocked", message: "Veil blocked residual sensitive data." }
          : event,
      ),
      event_count: 4,
      tool_payload: null,
      tool_response: null,
      restored_response: null,
      agent_answer: null,
      audit: { status: "blocked", egress_verified: false, leakage_count: 0 },
    };
    vi.mocked(getRun).mockResolvedValue(blocked);

    render(
      <MemoryRouter>
        <WorkflowPage runId="run-demo-live" />
      </MemoryRouter>,
    );

    expect(await screen.findByText("EGRESS BLOCKED")).toBeInTheDocument();
    expect(screen.getByText(/not reached — veil stopped the call/i)).toBeInTheDocument();
    const veil = screen.getByRole("listitem", { name: /veil privacy layer, blocked/i });
    expect(veil).toBeInTheDocument();
    expect(within(veil).getByTestId("workflow-connector")).not.toHaveClass("flow-connector--flowing");
    expect(screen.queryByText(/tool's tokenized reply/i)).not.toBeInTheDocument();
  });

  it("shows the Gemini mode, protected prompt, and tokenized model answer", async () => {
    vi.mocked(getRun).mockResolvedValue({
      ...snapshot,
      agent_mode: "gemini",
      events: [
        ...snapshot.events,
        {
          event_id: 8,
          run_id: "run-demo-live",
          stage: "model_input_protection",
          status: "complete",
          message: "Veil protected the prompt.",
          artifact: { protected_prompt: "Email [[EMAIL:VABCDEF1234]]", detections: [] },
        },
        {
          event_id: 9,
          run_id: "run-demo-live",
          stage: "agent_model_answer",
          status: "complete",
          message: "Gemini drafted an answer.",
          artifact: "Received for [[EMAIL:VABCDEF1234]]",
        },
        {
          event_id: 10,
          run_id: "run-demo-live",
          stage: "model_tool_context",
          status: "complete",
          message: "Veil checked the tool reply.",
          artifact: { message_echo: "Email [[EMAIL:VABCDEF1234]]" },
        },
      ],
      event_count: 11,
    });

    render(
      <MemoryRouter>
        <WorkflowPage runId="run-demo-live" />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Gemini · networked")).toBeInTheDocument();
    expect(await screen.findByText(/TOKENIZED PROMPT SENT TO GEMINI/i, {}, { timeout: 3000 })).toBeInTheDocument();
    expect((await screen.findAllByText(/EMAIL:VABCDEF1234/, {}, { timeout: 3000 })).length).toBeGreaterThanOrEqual(1);
    expect(await screen.findByText(/TOKENIZED MODEL ANSWER/i, {}, { timeout: 3000 })).toBeInTheDocument();
    expect(await screen.findByText(/TOKENIZED TOOL CONTEXT SENT TO GEMINI/i, {}, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getByText(/restores only known tokens locally/i)).toBeInTheDocument();
  });

  it("shows the local fallback as a successful Gemini-mode workflow", async () => {
    vi.mocked(getRun).mockResolvedValue({
      ...snapshot,
      agent_mode: "gemini",
      events: [
        ...snapshot.events,
        {
          event_id: 8,
          run_id: "run-demo-live",
          stage: "agent_fallback",
          status: "complete",
          message: "Gemini could not complete the request. The deterministic local agent is continuing this run.",
          artifact: { failed_at: "tool_proposal", fallback_agent: "deterministic" },
        },
      ],
      event_count: 9,
    });

    render(
      <MemoryRouter>
        <WorkflowPage runId="run-demo-live" />
      </MemoryRouter>,
    );

    expect(await screen.findByText(/local fallback used/i, {}, { timeout: 5000 })).toBeInTheDocument();
    expect(await screen.findByText("Deterministic fallback · offline", {}, { timeout: 5000 })).toBeInTheDocument();
    expect(await screen.findByText(/Riley Sample, your request is received\./, {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows a failed Gemini planning event on the run and marks its node failed", async () => {
    const failed: WorkflowSnapshot = {
      ...snapshot,
      status: "failed",
      agent_mode: "gemini",
      events: [
        snapshot.events[0],
        {
          event_id: 1,
          run_id: "run-demo-live",
          stage: "model_input_protection",
          status: "complete",
          message: "Veil protected the message.",
          artifact: { protected_prompt: "Check TICKET-DEMO-1042 and [[EMAIL:VABCDEF1234]]" },
        },
        {
          event_id: 2,
          run_id: "run-demo-live",
          stage: "agent_planning",
          status: "active",
          message: "Gemini is preparing a lookup.",
        },
        {
          event_id: 3,
          run_id: "run-demo-live",
          stage: "agent_planning",
          status: "failed",
          message: "The Gemini run could not complete. Check the ticket ID and Gemini connection, then try again.",
        },
      ],
      event_count: 4,
      agent_answer: null,
    };
    vi.mocked(getRun).mockResolvedValue(failed);

    render(
      <MemoryRouter>
        <WorkflowPage runId="run-demo-live" />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The Gemini run could not complete. Check the ticket ID and Gemini connection, then try again.",
    );
    expect(await screen.findByRole("listitem", { name: /AI agent, failed/i })).toBeInTheDocument();
  });
});
