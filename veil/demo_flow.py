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
from veil.helpdesk import SimulatedHelpdeskTool, require_demo_ticket_id
from veil.payload import sanitize_payload, verify_egress


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
    agent_mode: Literal["deterministic", "gemini"]
    show_blocked_path: bool
    events: tuple[WorkflowEvent, ...]


def run_ticket_demo(
    request: AgentRequest | None = None,
    *,
    run_id: str | None = None,
    show_blocked_path: bool = False,
    additional_sensitive_values: tuple[str, ...] = (),
    on_event: WorkflowEventCallback | None = None,
    agent_mode: Literal["deterministic", "gemini"] = "deterministic",
    gemini_client: object | None = None,
) -> TicketDemoRun:
    """Run the synthetic agent → Veil → helpdesk → agent flow locally."""
    if agent_mode not in {"deterministic", "gemini"}:
        raise ValueError("Unsupported agent mode.")
    if agent_mode == "gemini" and show_blocked_path:
        raise ValueError("The blocked-path fault injection is offline-only.")
    agent = LocalDemoAgent()
    request = request or AgentRequest(
        message=DEMO_USER_REQUEST,
        requester=RequesterDetails(**DEMO_REQUESTER),
    )
    if agent_mode == "gemini":
        require_demo_ticket_id(request.message)
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
        "The local agent received the synthetic request.",
        {"message": request.message},
    )
    helpdesk = SimulatedHelpdeskTool()
    detector = (
        _MissFirstEmailDetector(additional_sensitive_values)
        if show_blocked_path
        else PIIDetector(extra_values=additional_sensitive_values)
    )
    gateway = VeilGateway(detector=detector, simulated_tool=helpdesk)
    task = gateway.start_task()

    protected_message = request.message
    if agent_mode == "gemini":
        try:
            protected_input = sanitize_payload(request.message, detector, task.vault)
        except Exception:
            gateway.close_task(task)
            raise
        if not isinstance(protected_input.payload, str):
            gateway.close_task(task)
            raise RuntimeError("Veil could not protect the model prompt.")
        protected_message = protected_input.payload
        emit(
            "model_input_protection",
            "complete",
            "Veil protected selected values before the synthetic prompt was sent to Gemini.",
            {"protected_prompt": protected_message, "detections": protected_input.records},
        )

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
        emit("agent_planning", "active", "The selected agent is choosing a helpdesk action.")
        if agent_mode == "gemini":
            from veil.gemini_agent import GeminiAgent, create_gemini_client

            selected_agent = GeminiAgent(gemini_client or create_gemini_client())
            agent_call = selected_agent.prepare_tool_call(protected_message)
        else:
            selected_agent = agent
            agent_call = agent.build_ticket_lookup_call(request)
        emit("agent_planning", "complete", f"The {agent_mode} agent selected a helpdesk action.")
        emit(
            "tool_call_prepared",
            "complete",
            "The agent prepared the tool arguments; Veil will check them before dispatch.",
            agent_call,
        )
        result = gateway.call_tool(
            task,
            agent_call.tool_name,
            agent_call.payload,
            on_progress=report_gateway_event,
        )
        tool_payload = helpdesk.received[0].payload if helpdesk.received else None
        if result.audit.status == "allowed" and agent_mode == "gemini":
            protected_result = sanitize_payload(result.tool_response, detector, task.vault)
            verify_egress(protected_result.payload, detector, task.vault)
            emit(
                "model_tool_context",
                "complete",
                "Veil checked the tool result before returning tokenized context to Gemini.",
                {
                    "user_message": protected_message,
                    "tool_result": protected_result.payload,
                },
            )
            answer = selected_agent.create_final_answer(
                protected_message,
                agent_call.tool_name,
                result.sanitized_payload,
                protected_result.payload,
            )
            emit(
                "agent_model_answer",
                "complete",
                "Gemini drafted an answer using protected context only.",
                answer,
            )
            agent_answer = task.vault.restore_text(answer)
        elif result.restored_response is not None:
            agent_answer = agent.format_answer(result.restored_response)
        else:
            agent_answer = None
    finally:
        gateway.close_task(task)

    if agent_answer is not None:
        emit(
            "agent_response",
            "complete",
            "The selected agent answered using Veil's trusted context.",
            agent_answer,
        )

    return TicketDemoRun(
        run_id=run_id,
        user_request=request.message,
        agent_call=agent_call,
        result=result,
        tool_payload=tool_payload,
        agent_answer=agent_answer,
        agent_mode=agent_mode,
        show_blocked_path=show_blocked_path,
        events=tuple(events),
    )
