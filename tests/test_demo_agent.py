import pytest

from veil.demo_agent import (
    AgentRequest,
    AgentRequestError,
    LocalDemoAgent,
    RequesterDetails,
)


def test_agent_prepares_ticket_call_from_user_message_and_contact_fields() -> None:
    message = (
        "Please check ticket TICKET-DEMO-1042. My name is Riley Sample, "
        "my email is riley@example.test, and my phone is 111-222-3333. "
        "Tell me its status and next update."
    )
    requester = RequesterDetails(
        name="Riley Sample",
        email="riley@example.test",
        phone="111-222-3333",
    )

    tool_call = LocalDemoAgent().build_ticket_lookup_call(
        AgentRequest(message=message, requester=requester)
    )

    assert tool_call.tool_name == "lookup_helpdesk_ticket"
    assert tool_call.payload == {
        "ticket_id": "TICKET-DEMO-1042",
        "requester": {
            "name": "Riley Sample",
            "email": "riley@example.test",
            "phone": "111-222-3333",
        },
        "user_message": message,
        "question": "ticket status and next update",
    }


def test_agent_routes_free_form_message_to_support_when_ticket_id_is_missing() -> None:
    message = "Please help with my synthetic account access issue."
    request = AgentRequest(
        message=message,
        requester=RequesterDetails(
            name="Riley Sample",
            email="riley@example.test",
            phone="111-222-3333",
        ),
    )

    tool_call = LocalDemoAgent().build_ticket_lookup_call(request)

    assert tool_call.tool_name == "submit_support_request"
    assert tool_call.payload["user_message"] == message
    assert tool_call.payload["requester"] == request.requester.to_dict()


def test_agent_normalizes_ticket_id_case() -> None:
    request = AgentRequest(
        message="Please check ticket ticket-demo-1042.",
        requester=RequesterDetails(
            name="Riley Sample",
            email="riley@example.test",
            phone="111-222-3333",
        ),
    )

    tool_call = LocalDemoAgent().build_ticket_lookup_call(request)

    assert tool_call.payload["ticket_id"] == "TICKET-DEMO-1042"


def test_agent_formats_final_answer_from_restored_tool_response() -> None:
    restored_response = {
        "ticket": {
            "ticket_id": "TICKET-DEMO-1042",
            "status": "In progress",
            "team": "Campus IT",
            "next_update": "10 minutes",
        },
        "requester": {
            "name": "Riley Sample",
            "email": "riley@example.test",
            "phone": "111-222-3333",
        },
    }

    answer = LocalDemoAgent().format_answer(restored_response)

    assert answer == (
        "Riley Sample, ticket TICKET-DEMO-1042 is In progress with Campus IT. "
        "The next update is expected in 10 minutes. Contact on file: "
        "riley@example.test."
    )


def test_agent_formats_answer_from_restored_free_form_support_response() -> None:
    answer = LocalDemoAgent().format_answer(
        {
            "support_request": {"status": "received", "reference_id": "HD-DEMO-0001"},
            "requester": {"name": "Riley Sample", "email": "riley@example.test"},
            "message_echo": "Please help Riley Sample at riley@example.test.",
        }
    )

    assert "HD-DEMO-0001" in answer
    assert "Riley Sample" in answer
    assert "riley@example.test" in answer
    assert "Please help Riley Sample" in answer
