"""Offline campus helpdesk tool used by the judge-facing demo."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from veil.mock_tool import CapturedToolCall, SimulatedTool


DEMO_TICKET_ID = "TICKET-DEMO-1042"

DEMO_TICKETS: dict[str, dict[str, str]] = {
    DEMO_TICKET_ID: {
        "status": "In progress",
        "team": "Campus IT",
        "next_update": "10 minutes",
    }
}

_TICKET_ID_PATTERN = re.compile(r"\b(TICKET-[A-Z0-9]+-\d{4})\b", re.IGNORECASE)
VALID_TICKET_MESSAGE = (
    "Only tickets present in the local simulated helpdesk are accepted. "
    "Use the synthetic ticket ID TICKET-DEMO-1042."
)


def require_demo_ticket_id(message: str) -> str:
    """Return the one known synthetic ticket ID or reject the intake."""
    matches = {match.upper() for match in _TICKET_ID_PATTERN.findall(message)}
    if len(matches) != 1:
        raise ValueError(VALID_TICKET_MESSAGE)
    ticket_id = matches.pop()
    if ticket_id not in DEMO_TICKETS:
        raise ValueError(VALID_TICKET_MESSAGE)
    return ticket_id


class SimulatedHelpdeskTool(SimulatedTool):
    """Look up a fictional ticket by ID and echo only the protected requester fields."""

    def call(self, tool_name: str, payload: object) -> dict[str, Any]:
        captured = deepcopy(payload)
        self.received.append(CapturedToolCall(tool_name, captured))

        if not isinstance(payload, dict):
            return {"error": "unsupported_request"}

        requester = payload.get("requester", {})
        protected_requester = deepcopy(requester) if isinstance(requester, dict) else {}
        if tool_name == "submit_support_request":
            message = payload.get("user_message", "")
            return {
                "support_request": {
                    "status": "received",
                    "reference_id": "HD-DEMO-0001",
                },
                "requester": protected_requester,
                "message_echo": message if isinstance(message, str) else "",
            }

        if tool_name != "lookup_helpdesk_ticket":
            return {"error": "unsupported_request"}

        ticket_id = payload.get("ticket_id")
        ticket_details = DEMO_TICKETS.get(ticket_id) if isinstance(ticket_id, str) else None
        if ticket_details is None:
            return {
                "error": "ticket_not_found",
                "ticket_id": ticket_id,
                "requester": protected_requester,
            }

        return {
            "ticket": {"ticket_id": ticket_id, **ticket_details},
            "requester": protected_requester,
        }
