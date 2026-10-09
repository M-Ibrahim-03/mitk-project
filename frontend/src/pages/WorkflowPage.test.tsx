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
  audit: { status: "allowed", detection_count: 2, unique_token_count: 2, leakage_count: 0, egress_verified: true },
};

describe("live workflow visualizer", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    vi.mocked(getRun).mockResolvedValue(snapshot);
  });

  it("shows actual message, protected tool payload, restored reply, and agent answer", async () => {
    render(
      <MemoryRouter>
        <WorkflowPage runId="run-demo-live" />
      </MemoryRouter>,
    );

    expect(await screen.findByText("My name is Riley Sample, email riley@example.test")).toBeInTheDocument();
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
    expect(screen.getByRole("listitem", { name: /veil privacy layer, blocked/i })).toBeInTheDocument();
    expect(screen.queryByText(/tool's tokenized reply/i)).not.toBeInTheDocument();
  });
});
