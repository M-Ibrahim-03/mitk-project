import { afterEach, describe, expect, it, vi } from "vitest";

import { createRun, subscribeToRun } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("local workflow API", () => {
  it("creates a run with only the user's message", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ run_id: "local-run-1", status: "queued" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const created = await createRun({ message: "Please check my ticket." });

    expect(created.run_id).toBe("local-run-1");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("/api/runs", expect.objectContaining({ method: "POST" }));
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      message: "Please check my ticket.",
    });
  });

  it("receives actual events and completion for the same run through EventSource", () => {
    class FakeEventSource {
      static latest: FakeEventSource;
      readonly listeners = new Map<string, (event: MessageEvent) => void>();
      readonly close = vi.fn();

      constructor(readonly url: string) {
        FakeEventSource.latest = this;
      }

      addEventListener(type: string, listener: EventListenerOrEventListenerObject) {
        this.listeners.set(type, listener as (event: MessageEvent) => void);
      }

      emit(type: string, data: object) {
        this.listeners.get(type)?.({ data: JSON.stringify(data) } as MessageEvent);
      }
    }
    vi.stubGlobal("EventSource", FakeEventSource);
    const onEvent = vi.fn();
    const onComplete = vi.fn();
    const onError = vi.fn();

    const close = subscribeToRun("run with spaces", onEvent, onComplete, onError);
    const event = { event_id: 2, run_id: "run with spaces", stage: "egress_gate", status: "complete" };
    FakeEventSource.latest.emit("workflow", event);
    FakeEventSource.latest.emit("run_complete", { run_id: "run with spaces", status: "complete" });

    expect(FakeEventSource.latest.url).toBe("/api/runs/run%20with%20spaces/events");
    expect(onEvent).toHaveBeenCalledWith(event);
    expect(onComplete).toHaveBeenCalledWith("complete");
    expect(onError).not.toHaveBeenCalled();
    close();
    expect(FakeEventSource.latest.close).toHaveBeenCalledOnce();
  });
});
