"""Deterministic local agent used to tell the helpdesk demo story."""

from __future__ import annotations

from dataclasses import dataclass

from veil.helpdesk import DEMO_TICKET_ID


DEMO_REQUESTER = {
    "name": "Maya Example",
    "email": "maya@example.test",
    "phone": "000-000-0000",
}

DEMO_USER_REQUEST = (
    f"Please check ticket {DEMO_TICKET_ID}. My name is Maya Example, "
    "my email is maya@example.test, and my phone is 000-000-0000. "
    "Tell me the status and when I should expect an update."
)


@dataclass(frozen=True)
class AgentToolCall:
    """A tool request prepared by the local demo agent."""

    tool_name: str
    payload: dict[str, object]


class LocalDemoAgent:
    """Prepare and explain one repeatable synthetic helpdesk request."""

    def build_ticket_lookup_call(self) -> AgentToolCall:
        return AgentToolCall(
            tool_name="lookup_helpdesk_ticket",
            payload={
                "ticket_id": DEMO_TICKET_ID,
                "requester": DEMO_REQUESTER.copy(),
                "user_message": DEMO_USER_REQUEST,
                "question": "ticket status and next update",
            },
        )

    def format_answer(self, tool_response: object) -> str:
        if not isinstance(tool_response, dict) or "ticket" not in tool_response:
            return "I could not find that demo ticket."

        ticket = tool_response["ticket"]
        requester = tool_response.get("requester", {})
        if not isinstance(ticket, dict) or not isinstance(requester, dict):
            return "I could not safely read the demo ticket reply."

        name = requester.get("name", "there")
        email = requester.get("email", "the address on file")
        return (
            f"{name}, ticket {ticket.get('ticket_id')} is "
            f"{ticket.get('status')} with {ticket.get('team')}. "
            f"The next update is expected in {ticket.get('next_update')}. "
            f"Contact on file: {email}."
        )
