import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

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
  agent_answer: "Riley Sample, your ticket is in progress.",
  audit: { status: "allowed" },
};

describe("chat-to-agent interaction", () => {
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

  it("submits once, shows the agent answer, and links to the same run", async () => {
    render(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByRole("textbox", { name: /your message/i }), {
      target: { value: "Please check ticket TICKET-DEMO-1042. My name is Riley Sample." },
    });
    fireEvent.change(screen.getByRole("textbox", { name: /synthetic email/i }), {
      target: { value: "riley@example.test" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findByText("Riley Sample, your ticket is in progress.")).toBeInTheDocument();
    expect(createRun).toHaveBeenCalledTimes(1);
    expect(createRun).toHaveBeenCalledWith(
      expect.objectContaining({
        message: "Please check ticket TICKET-DEMO-1042. My name is Riley Sample.",
        requester: expect.objectContaining({ email: "riley@example.test" }),
      }),
    );
    await waitFor(() => expect(getRun).toHaveBeenCalledWith("chat-run-1"));
    expect(screen.getByRole("link", { name: /view animated workflow/i })).toHaveAttribute(
      "href",
      "/runs/chat-run-1",
    );
  });
});
