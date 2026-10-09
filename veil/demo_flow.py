"""End-to-end local helpdesk story for the Veil judging demo."""

from __future__ import annotations

from dataclasses import dataclass

from veil.demo_agent import AgentToolCall, LocalDemoAgent
from veil.detection import PIIDetector
from veil.gateway import ToolCallResult, VeilGateway
from veil.helpdesk import SimulatedHelpdeskTool


class _MissFirstEmailDetector(PIIDetector):
    """Demo-only fault injection so the egress verifier's block can be shown."""

    def __init__(self) -> None:
        super().__init__()
        self._skipped_values: set[str] = set()

    def detect(self, text: str, field_hint: str = ""):
        if "@" in text and text not in self._skipped_values:
            self._skipped_values.add(text)
            return []
        return super().detect(text, field_hint=field_hint)


@dataclass(frozen=True)
class TicketDemoRun:
    user_request: str
    agent_call: AgentToolCall
    result: ToolCallResult
    tool_payload: object | None
    agent_answer: str | None
    show_blocked_path: bool


def run_ticket_demo(*, show_blocked_path: bool = False) -> TicketDemoRun:
    """Run the synthetic agent → Veil → helpdesk → agent flow locally."""
    agent = LocalDemoAgent()
    agent_call = agent.build_ticket_lookup_call()
    helpdesk = SimulatedHelpdeskTool()
    detector = _MissFirstEmailDetector() if show_blocked_path else PIIDetector()
    gateway = VeilGateway(detector=detector, simulated_tool=helpdesk)
    task = gateway.start_task()
    try:
        result = gateway.call_tool(task, agent_call.tool_name, agent_call.payload)
    finally:
        gateway.close_task(task)

    tool_payload = helpdesk.received[0].payload if helpdesk.received else None
    agent_answer = (
        agent.format_answer(result.restored_response)
        if result.restored_response is not None
        else None
    )
    return TicketDemoRun(
        user_request=agent_call.payload["user_message"],
        agent_call=agent_call,
        result=result,
        tool_payload=tool_payload,
        agent_answer=agent_answer,
        show_blocked_path=show_blocked_path,
    )
