import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createRun, getRun, subscribeToRun } from "./api";
import { AppRoutes } from "./App";

vi.mock("./api", () => ({
  createRun: vi.fn(),
  getRun: vi.fn(async (runId: string) => ({
    run_id: runId,
    status: "complete",
    events: [],
    event_count: 0,
    tool_payload: null,
    tool_response: null,
    restored_response: null,
    agent_answer: null,
    audit: null,
  })),
  subscribeToRun: vi.fn(() => vi.fn()),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  );
}

describe("Veil page routes", () => {
  it("shows the simple synthetic chat form at the home route", () => {
    renderAt("/");

    expect(
      screen.getByRole("heading", { name: /veil assistant/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /your message/i })).toBeInTheDocument();
    expect(screen.getByText(/synthetic data only/i)).toBeInTheDocument();
  });

  it("shows the workflow page for the requested run ID", () => {
    renderAt("/runs/run-demo-123");

    expect(
      screen.getByRole("heading", { name: /every handoff/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("run-demo-123")).toBeInTheDocument();
    expect(
      screen.getByRole("list", { name: /workflow steps/i }).querySelectorAll("li"),
    ).toHaveLength(6);
    expect(screen.getByRole("listitem", { name: /veil privacy layer/i })).toBeInTheDocument();
    expect(screen.getByRole("listitem", { name: /helpdesk tool/i })).toBeInTheDocument();
  });

  it("shows a safe not-found page for unsupported routes", () => {
    renderAt("/not-a-veil-page");

    expect(screen.getByRole("heading", { name: /page not found/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /back to chat/i })).toHaveAttribute("href", "/");
  });

  it("does not start a backend run when either page is mounted", () => {
    renderAt("/");
    cleanup();
    renderAt("/runs/run-demo-123");

    expect(createRun).not.toHaveBeenCalled();
    expect(getRun).toHaveBeenCalledWith("run-demo-123");
    expect(subscribeToRun).toHaveBeenCalledWith(
      "run-demo-123",
      expect.any(Function),
      expect.any(Function),
      expect.any(Function),
    );
  });
});
