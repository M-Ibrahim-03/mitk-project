"""Offline campus helpdesk tool used by the judge-facing demo."""

from __future__ import annotations

from copy import deepcopy
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


class SimulatedHelpdeskTool(SimulatedTool):
    """Look up a fictional ticket by ID and echo only the protected requester fields."""

    def call(self, tool_name: str, payload: object) -> dict[str, Any]:
        captured = deepcopy(payload)
        self.received.append(CapturedToolCall(tool_name, captured))

        if tool_name != "lookup_helpdesk_ticket" or not isinstance(payload, dict):
            return {"error": "unsupported_request"}

        ticket_id = payload.get("ticket_id")
        ticket_details = DEMO_TICKETS.get(ticket_id) if isinstance(ticket_id, str) else None
        requester = payload.get("requester", {})
        protected_requester = deepcopy(requester) if isinstance(requester, dict) else {}

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
