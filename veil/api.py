"""FastAPI entry point for the Veil MVP and its local workflow UI."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from typing import Annotated, Any
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from veil.demo_agent import DEMO_REQUESTER, AgentRequest, RequesterDetails
from veil.demo_flow import WorkflowEvent, run_ticket_demo
from veil.gateway import VeilGateway
from veil.run_registry import RunCapacityError, RunStore

app = FastAPI(
    title="Veil Privacy Gateway",
    description="Local demo of reversible PII protection for agent tool calls.",
    version="0.1.0",
)
gateway = VeilGateway()
run_store = RunStore(ttl_seconds=900, max_runs=100)
run_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="veil-workflow")


class ToolCallRequest(BaseModel):
    tool_name: str = Field(default="simulated_tool", min_length=1, max_length=80)
    payload: Any


class DemoRequesterRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=120)] = DEMO_REQUESTER["name"]
    email: Annotated[str, Field(min_length=1, max_length=254)] = DEMO_REQUESTER["email"]
    phone: Annotated[str, Field(min_length=1, max_length=40)] = DEMO_REQUESTER["phone"]


class DemoRunRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=4000)]
    requester: DemoRequesterRequest = Field(default_factory=DemoRequesterRequest)
    additional_sensitive_values: list[
        Annotated[str, Field(min_length=1, max_length=256)]
    ] = Field(default_factory=list, max_length=20)


def _execute_demo_run(
    run_id: str,
    request: AgentRequest,
    additional_sensitive_values: tuple[str, ...],
) -> None:
    run_store.mark_running(run_id)
    try:
        run = run_ticket_demo(
            request=request,
            run_id=run_id,
            additional_sensitive_values=additional_sensitive_values,
            on_event=run_store.append_event,
        )
        run_store.finish(run)
    except Exception:
        run_store.fail(
            run_id,
            WorkflowEvent(
                run_id=run_id,
                stage="workflow",
                status="failed",
                message="The local workflow could not complete safely.",
            ),
        )


def _run_snapshot(record: Any) -> dict[str, object]:
    run = record.result
    events = [
        {**jsonable_encoder(event), "event_id": event_id}
        for event_id, event in enumerate(record.events)
    ]
    tool_event = next(
        (
            event
            for event in events
            if event["stage"] == "helpdesk" and event["status"] == "complete"
        ),
        None,
    )
    result = run.result if run is not None else None
    return {
        "run_id": record.run_id,
        "status": record.status,
        "events": events,
        "event_count": len(events),
        "tool_payload": tool_event["artifact"] if tool_event else None,
        "tool_response": jsonable_encoder(result.tool_response) if result else None,
        "restored_response": jsonable_encoder(result.restored_response) if result else None,
        "agent_answer": run.agent_answer if run else None,
        "audit": jsonable_encoder(result.audit) if result else None,
    }


@app.get("/health")
def health() -> dict[str, str]:
    """Return a small health response for setup checks."""
    return {"status": "ok", "service": "veil"}


@app.post("/api/runs", status_code=status.HTTP_202_ACCEPTED)
def create_workflow_run(request: DemoRunRequest) -> dict[str, str]:
    """Queue one local agent workflow; payload data is never sent outside Veil."""
    run_id = uuid4().hex
    try:
        run_store.create(run_id)
    except RunCapacityError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None

    agent_request = AgentRequest(
        message=request.message,
        requester=RequesterDetails(**request.requester.model_dump()),
    )
    run_executor.submit(
        _execute_demo_run,
        run_id,
        agent_request,
        tuple(request.additional_sensitive_values),
    )
    return {"run_id": run_id, "status": "queued"}


@app.get("/api/runs/{run_id}")
def read_workflow_run(run_id: str) -> dict[str, object]:
    """Read the current replayable event trace and artifacts for one run."""
    record = run_store.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Workflow run not found.")
    return _run_snapshot(record)


@app.get("/api/runs/{run_id}/events")
async def stream_workflow_events(
    run_id: str,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    """Replay this run's actual events and continue streaming until it finishes."""
    if run_store.get(run_id) is None:
        raise HTTPException(status_code=404, detail="Workflow run not found.")
    try:
        cursor = int(last_event_id) if last_event_id is not None else -1
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event cursor.") from None
    if cursor < -1:
        raise HTTPException(status_code=400, detail="Invalid event cursor.")

    async def event_stream():
        nonlocal cursor
        while True:
            record = run_store.get(run_id)
            if record is None:
                yield "event: run_error\ndata: {\"message\":\"Workflow run expired.\"}\n\n"
                return

            while cursor + 1 < len(record.events):
                cursor += 1
                event = record.events[cursor]
                payload = {**jsonable_encoder(event), "event_id": cursor}
                yield (
                    f"id: {cursor}\n"
                    "event: workflow\n"
                    f"data: {json.dumps(payload, separators=(',', ':'), ensure_ascii=False)}\n\n"
                )

            if record.status in {"complete", "blocked", "failed"}:
                completion = json.dumps(
                    {
                        "run_id": run_id,
                        "status": record.status,
                        "event_count": len(record.events),
                    },
                    separators=(",", ":"),
                )
                yield f"event: run_complete\ndata: {completion}\n\n"
                return
            await asyncio.sleep(0.05)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/tool-call")
def tool_call(request: ToolCallRequest) -> dict[str, object]:
    """Demonstrate the sanitized request boundary with the local mock tool."""
    context = gateway.start_task()
    try:
        return gateway.call_tool(context, request.tool_name, request.payload).to_dict()
    finally:
        gateway.close_task(context)

