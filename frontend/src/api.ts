export type RunStatus = "queued" | "running" | "complete" | "blocked" | "failed";

export interface DemoRunRequest {
  message: string;
  requester: {
    name: string;
    email: string;
    phone: string;
  };
  additional_sensitive_values?: string[];
}

export interface WorkflowEvent {
  event_id: number;
  run_id: string;
  stage: string;
  status: "queued" | "active" | "complete" | "blocked" | "failed";
  message: string;
  artifact?: unknown;
}

export interface WorkflowSnapshot {
  run_id: string;
  status: RunStatus;
  events: WorkflowEvent[];
  event_count: number;
  tool_payload: unknown;
  tool_response: unknown;
  restored_response: unknown;
  agent_answer: string | null;
  audit: Record<string, unknown> | null;
}

interface CreatedRun {
  run_id: string;
  status: "queued";
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = "The local workflow request failed.";
    try {
      const body = (await response.json()) as { detail?: string };
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // Keep a generic message if the local service returned no JSON detail.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export async function createRun(request: DemoRunRequest): Promise<CreatedRun> {
  const response = await fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  return readJson<CreatedRun>(response);
}

export async function getRun(runId: string): Promise<WorkflowSnapshot> {
  const response = await fetch(`/api/runs/${encodeURIComponent(runId)}`);
  return readJson<WorkflowSnapshot>(response);
}

export function subscribeToRun(
  runId: string,
  onEvent: (event: WorkflowEvent) => void,
  onComplete: (status: RunStatus) => void,
  onError: (message: string) => void,
): () => void {
  const source = new EventSource(
    `/api/runs/${encodeURIComponent(runId)}/events`,
  );
  let isClosed = false;
  const close = () => {
    if (!isClosed) {
      isClosed = true;
      source.close();
    }
  };

  source.addEventListener("workflow", (message) => {
    try {
      onEvent(JSON.parse((message as MessageEvent<string>).data) as WorkflowEvent);
    } catch {
      onError("Veil received an unreadable workflow update.");
    }
  });
  source.addEventListener("run_complete", (message) => {
    try {
      const completion = JSON.parse((message as MessageEvent<string>).data) as {
        status: RunStatus;
      };
      onComplete(completion.status);
      close();
    } catch {
      onError("Veil could not confirm that this workflow finished.");
      close();
    }
  });
  source.addEventListener("run_error", (message) => {
    const data = JSON.parse((message as MessageEvent<string>).data) as {
      message?: string;
    };
    onError(data.message ?? "This workflow is no longer available.");
    close();
  });

  return close;
}
