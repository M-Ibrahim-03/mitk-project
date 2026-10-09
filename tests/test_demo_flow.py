from veil.demo_agent import AgentRequest, RequesterDetails
from veil.demo_flow import run_ticket_demo


def make_request() -> AgentRequest:
    return AgentRequest(
        message=(
            "Please check ticket TICKET-DEMO-1042. My name is Riley Sample, "
            "my email is riley@example.test, and my phone is 111-222-3333. "
            "Tell me its status and next update."
        ),
        requester=RequesterDetails(
            name="Riley Sample",
            email="riley@example.test",
            phone="111-222-3333",
        ),
    )


def test_user_request_crosses_veil_and_returns_as_an_agent_answer() -> None:
    request = make_request()

    run = run_ticket_demo(request=request)

    assert run.result.audit.status == "allowed"
    assert run.result.audit.egress_verified is True
    assert run.result.audit.leakage_count == 0
    assert run.tool_payload == run.result.sanitized_payload
    for original in ("Riley Sample", "riley@example.test", "111-222-3333"):
        assert original not in repr(run.tool_payload)
    assert run.tool_payload["ticket_id"] == "TICKET-DEMO-1042"
    assert run.result.tool_response["requester"]["email"].startswith("[[EMAIL:")
    assert run.result.restored_response["requester"] == {
        "name": "Riley Sample",
        "email": "riley@example.test",
        "phone": "111-222-3333",
    }
    assert "Riley Sample" in run.agent_answer
    assert "riley@example.test" in run.agent_answer

    completed_stages = [
        event.stage for event in run.events if event.status == "complete"
    ]
    assert completed_stages == [
        "request_received",
        "agent_planning",
        "tool_call_prepared",
        "privacy_scan",
        "egress_gate",
        "helpdesk",
        "tool_response",
        "response_restore",
        "agent_response",
    ]
    assert len({event.run_id for event in run.events}) == 1


def test_unsafe_request_stops_at_egress_and_never_reaches_helpdesk() -> None:
    run = run_ticket_demo(request=make_request(), show_blocked_path=True)

    assert run.result.audit.status == "blocked"
    assert run.result.audit.egress_verified is False
    assert run.tool_payload is None
    assert run.result.tool_response is None
    assert run.result.restored_response is None
    assert run.agent_answer is None

    completed_stages = [
        event.stage for event in run.events if event.status == "complete"
    ]
    assert completed_stages == [
        "request_received",
        "agent_planning",
        "tool_call_prepared",
        "privacy_scan",
    ]
    assert run.events[-1].stage == "egress_gate"
    assert run.events[-1].status == "blocked"
    assert all(
        event.stage not in {"helpdesk", "tool_response", "response_restore", "agent_response"}
        for event in run.events
    )


def test_flow_notifies_observer_with_the_events_from_the_actual_run() -> None:
    observed_events = []

    run = run_ticket_demo(request=make_request(), on_event=observed_events.append)

    assert observed_events == list(run.events)
    assert observed_events[-1].stage == "agent_response"
    assert observed_events[-1].artifact == run.agent_answer



def test_free_form_message_and_user_marked_secret_cross_gateway_and_restore() -> None:
    message = "Please check this synthetic case phrase ZQX-731 for Riley Sample."
    request = AgentRequest(
        message=message,
        requester=RequesterDetails("Riley Sample", "riley@example.test", "111-222-3333"),
    )

    run = run_ticket_demo(
        request=request,
        additional_sensitive_values=("case phrase ZQX-731",),
    )

    assert run.agent_call.tool_name == "submit_support_request"
    assert run.result.audit.status == "allowed"
    assert "case phrase ZQX-731" not in repr(run.tool_payload)
    assert "riley@example.test" not in repr(run.tool_payload)
    assert "case phrase ZQX-731" in run.result.restored_response["message_echo"]
    assert "case phrase ZQX-731" in run.agent_answer
