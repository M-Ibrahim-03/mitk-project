"""End-to-end local helpdesk story for the Veil judging demo."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from veil.demo_agent import (
    DEMO_REQUESTER,
    DEMO_USER_REQUEST,
    AgentRequest,
    AgentToolCall,
    LocalDemoAgent,
    RequesterDetails,
)
from veil.detection import PIIDetector
from veil.gateway import ToolCallResult, VeilGateway
from veil.helpdesk import SimulatedHelpdeskTool


class _MissFirstEmailDetector(PIIDetector):
    """Demo-only fault injection so the egress verifier's block can be shown."""

    def __init__(self, extra_values: tuple[str, ...] = ()) -> None:
        super().__init__(extra_values=extra_values)
        self._skipped_values: set[str] = set()

    def detect(self, text: str, field_hint: str = ""):
        if "@" in text and text not in self._skipped_values:
            self._skipped_values.add(text)
            return []
        return super().detect(text, field_hint=field_hint)


@dataclass(frozen=True)
class WorkflowEvent:
    """One truthful status update from a single demo workflow run."""

    run_id: str
    stage: str
    status: Literal["queued", "active", "complete", "blocked", "failed"]
    message: str
    artifact: object | None = None


WorkflowEventCallback = Callable[[WorkflowEvent], None]


@dataclass(frozen=True)
class TicketDemoRun:
    run_id: str
    user_request: str
    agent_call: AgentToolCall
    result: ToolCallResult
    tool_payload: object | None
    agent_answer: str | None
    show_blocked_path: bool
    events: tuple[WorkflowEvent, ...]


def run_ticket_demo(
    request: AgentRequest | None = None,
    *,
    run_id: str | None = None,
    show_blocked_path: bool = False,
    additional_sensitive_values: tuple[str, ...] = (),
    on_event: WorkflowEventCallback | None = None,
) -> TicketDemoRun:
    """Run the synthetic agent → Veil → helpdesk → agent flow locally."""
    agent = LocalDemoAgent()
    request = request or AgentRequest(
        message=DEMO_USER_REQUEST,
        requester=RequesterDetails(**DEMO_REQUESTER),
    )
    run_id = run_id or uuid4().hex
    events: list[WorkflowEvent] = []

    def emit(
        stage: str,
        status: Literal["queued", "active", "complete", "blocked", "failed"],
        message: str,
        artifact: object | None = None,
    ) -> None:
        event = WorkflowEvent(run_id, stage, status, message, artifact)
        events.append(event)
        if on_event is not None:
            on_event(event)

    emit(
        "request_received",
        "complete",
        "The local agent received the synthetic request and contact fields.",
        {"message": request.message, "requester": request.requester.to_dict()},
    )
    emit("agent_planning", "active", "The local agent is choosing a helpdesk action.")
    agent_call = agent.build_ticket_lookup_call(request)
    emit("agent_planning", "complete", "The agent selected the helpdesk ticket tool.")
    emit(
        "tool_call_prepared",
        "complete",
        "The agent prepared the tool arguments; Veil will check them before dispatch.",
        agent_call,
    )

    helpdesk = SimulatedHelpdeskTool()
    detector = (
        _MissFirstEmailDetector(additional_sensitive_values)
        if show_blocked_path
        else PIIDetector(extra_values=additional_sensitive_values)
    )
    gateway = VeilGateway(detector=detector, simulated_tool=helpdesk)
    task = gateway.start_task()

    stage_messages = {
        "privacy_scan": "Veil is checking the outgoing request.",
        "egress_gate": "Veil is verifying the exact payload before dispatch.",
        "helpdesk": "The local helpdesk is handling the verified request.",
        "tool_response": "The helpdesk returned its reply with Veil tokens.",
        "response_restore": "Veil is restoring values for the trusted agent.",
    }

    def report_gateway_event(stage: str, status: str, artifact: object | None) -> None:
        message = stage_messages.get(stage, stage.replace("_", " ").title())
        if stage == "egress_gate" and status == "blocked":
            message = "Veil blocked the request; the helpdesk was not called."
        elif stage == "egress_gate" and status == "complete":
            message = "Veil verified the outgoing payload; the tool may be called."
        elif stage == "helpdesk" and status == "complete":
            message = "The helpdesk received the protected request."
            artifact = helpdesk.received[-1].payload if helpdesk.received else None
        elif stage == "response_restore" and status == "complete":
            message = "The restored response is back with the trusted agent."
        emit(stage, status, message, artifact)

    try:
        result = gateway.call_tool(
            task,
            agent_call.tool_name,
            agent_call.payload,
            on_progress=report_gateway_event,
        )
    finally:
        gateway.close_task(task)

    tool_payload = helpdesk.received[0].payload if helpdesk.received else None
    agent_answer = (
        agent.format_answer(result.restored_response)
        if result.restored_response is not None
        else None
    )
    if agent_answer is not None:
        emit(
            "agent_response",
            "complete",
            "The agent used Veil's restored reply to answer the user.",
            agent_answer,
        )

    return TicketDemoRun(
        run_id=run_id,
        user_request=agent_call.payload["user_message"],
        agent_call=agent_call,
        result=result,
        tool_payload=tool_payload,
        agent_answer=agent_answer,
        show_blocked_path=show_blocked_path,
        events=tuple(events),
    )
