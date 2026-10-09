import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createRun, getRun, subscribeToRun } from "../api";
import type { WorkflowEvent, WorkflowSnapshot } from "../api";
import { ChatPage } from "./ChatPage";

vi.mock("../api", () => ({
  createRun: vi.fn(),
  getRun: vi.fn(),
  subscribeToRun: vi.fn(),
}));

const completedRun: WorkflowSnapshot = {
  run_id: "chat-run-1",
  status: "complete",
  events: [],
  event_count: 0,
  tool_payload: null,
  tool_response: null,
  restored_response: null,
  agent_answer: "Your ticket is in progress.",
  audit: { status: "allowed" },
};

describe("chat-to-agent interaction", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    vi.mocked(createRun).mockResolvedValue({ run_id: "chat-run-1", status: "queued" });
    vi.mocked(getRun).mockResolvedValue(completedRun);
    vi.mocked(subscribeToRun).mockImplementation(
      (_runId, onEvent, onComplete) => {
        const event: WorkflowEvent = {
          event_id: 0,
          run_id: "chat-run-1",
          stage: "request_received",
          status: "complete",
          message: "Received.",
        };
        onEvent(event);
        onComplete("complete");
        return vi.fn();
      },
    );
  });

  it("presents the introduction and message workspace as separate accessible regions", () => {
    render(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>,
    );

    expect(screen.queryByRole("region", { name: "Assistant introduction" })).not.toBeNull();
    expect(screen.queryByRole("region", { name: "Message workspace" })).not.toBeNull();
    expect(screen.getByRole("textbox", { name: /your message/i })).toBeInTheDocument();
    expect(screen.getAllByRole("textbox")).toHaveLength(1);
    expect(screen.queryByRole("group", { name: /contact details/i })).toBeNull();
    expect(screen.getByText(/valid ticket must exist.*local helpdesk.*accepts only TICKET-DEMO-1042.*include it in your message.*missing or other ticket IDs are rejected/i)).toBeInTheDocument();
    expect(screen.getByText(/checks selected email, phone, aadhaar, card, and bank identifier patterns/i)).toBeInTheDocument();
    expect(screen.getByText(/detection is limited and can miss other or obscured secrets/i)).toBeInTheDocument();
  });

  it("submits only the message, shows the agent answer, and links to the same run", async () => {
    render(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByRole("textbox", { name: /your message/i }), {
      target: { value: "Please check ticket TICKET-DEMO-1042. My name is Riley Sample." },
    });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findByText("Your ticket is in progress.")).toBeInTheDocument();
    expect(createRun).toHaveBeenCalledTimes(1);
    expect(createRun).toHaveBeenCalledWith({
      message: "Please check ticket TICKET-DEMO-1042. My name is Riley Sample.",
    });
    await waitFor(() => expect(getRun).toHaveBeenCalledWith("chat-run-1"));
    expect(screen.getByRole("link", { name: /view animated workflow/i })).toHaveAttribute(
      "href",
      "/runs/chat-run-1",
    );
  });

  it("shows ticket validation errors instead of silently re-enabling send", async () => {
    vi.mocked(createRun).mockRejectedValueOnce(
      new Error("Only the local synthetic ticket TICKET-DEMO-1042 is available."),
    );
    render(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByRole("textbox", { name: /your message/i }), {
      target: { value: "Check ticket TICKET-1000." },
    });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Only the local synthetic ticket TICKET-DEMO-1042 is available.",
    );
    expect(screen.getByRole("button", { name: /send message/i })).toBeEnabled();
  });

  it("shows the final workflow failure after the event stream closes", async () => {
    vi.mocked(getRun).mockResolvedValueOnce({
      ...completedRun,
      status: "failed",
      agent_answer: null,
      events: [{
        event_id: 3,
        run_id: "chat-run-1",
        stage: "workflow",
        status: "failed",
        message: "Gemini could not complete the ticket lookup. Use ticket TICKET-DEMO-1042.",
      }],
    });
    vi.mocked(subscribeToRun).mockImplementationOnce((_runId, _onEvent, onComplete) => {
      onComplete("failed");
      return vi.fn();
    });
    render(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByRole("textbox", { name: /your message/i }), {
      target: { value: "Check ticket TICKET-DEMO-1042." },
    });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Gemini could not complete the ticket lookup. Use ticket TICKET-DEMO-1042.",
    );
    expect(screen.getByRole("link", { name: /view failed workflow/i })).toHaveAttribute(
      "href",
      "/runs/chat-run-1",
    );
  });
});
