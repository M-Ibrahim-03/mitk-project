"""Deterministic local agent used to tell the helpdesk demo story."""

from __future__ import annotations

from dataclasses import dataclass
import re

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
TICKET_ID_PATTERN = re.compile(r"\b(TICKET-[A-Z0-9]+-\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class RequesterDetails:
    """Synthetic contact details the trusted local agent received from the user."""

    name: str
    email: str
    phone: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "email": self.email, "phone": self.phone}


@dataclass(frozen=True)
class AgentRequest:
    """One user message and optional legacy structured contact fields."""

    message: str
    requester: RequesterDetails | None = None


@dataclass(frozen=True)
class AgentToolCall:
    """A tool request prepared by the local demo agent."""

    tool_name: str
    payload: dict[str, object]


class AgentRequestError(ValueError):
    """The local agent needs a supported ticket ID before it can use a tool."""


class LocalDemoAgent:
    """Prepare and explain one repeatable synthetic helpdesk request."""

    def build_ticket_lookup_call(
        self, request: AgentRequest | None = None
    ) -> AgentToolCall:
        if request is None:
            request = AgentRequest(
                message=DEMO_USER_REQUEST,
                requester=RequesterDetails(**DEMO_REQUESTER),
            )

        ticket_match = TICKET_ID_PATTERN.search(request.message)
        if ticket_match is None:
            payload: dict[str, object] = {
                "user_message": request.message,
                "question": "help with the user's support request",
            }
            if request.requester is not None:
                payload["requester"] = request.requester.to_dict()
            return AgentToolCall(tool_name="submit_support_request", payload=payload)

        payload = {
            "ticket_id": ticket_match.group(1).upper(),
            "user_message": request.message,
            "question": "ticket status and next update",
        }
        if request.requester is not None:
            payload["requester"] = request.requester.to_dict()
        return AgentToolCall(tool_name="lookup_helpdesk_ticket", payload=payload)

    def format_answer(self, tool_response: object) -> str:
        if not isinstance(tool_response, dict):
            return "I could not safely read the helpdesk reply."

        support_request = tool_response.get("support_request")
        if isinstance(support_request, dict):
            requester = tool_response.get("requester", {})
            if not isinstance(requester, dict):
                requester = {}
            name = requester.get("name")
            email = requester.get("email")
            reference_id = support_request.get("reference_id", "the demo helpdesk")
            message_echo = tool_response.get("message_echo", "")
            if not isinstance(message_echo, str):
                message_echo = ""
            greeting = f"{name}, " if isinstance(name, str) else "Your "
            answer = f"{greeting}support request was received as {reference_id}."
            if isinstance(email, str):
                answer += f" Contact on file: {email}."
            if message_echo:
                answer += f" Request details: {message_echo}"
            return answer

        if "ticket" not in tool_response:
            return "I could not find that demo ticket."

        ticket = tool_response["ticket"]
        requester = tool_response.get("requester", {})
        if not isinstance(ticket, dict):
            return "I could not safely read the demo ticket reply."
        if not isinstance(requester, dict):
            requester = {}

        name = requester.get("name")
        email = requester.get("email")
        greeting = f"{name}, " if isinstance(name, str) else "Your "
        answer = (
            f"{greeting}ticket {ticket.get('ticket_id')} is "
            f"{ticket.get('status')} with {ticket.get('team')}. "
            f"The next update is expected in {ticket.get('next_update')}."
        )
        if isinstance(email, str):
            answer += f" Contact on file: {email}."
        return answer
