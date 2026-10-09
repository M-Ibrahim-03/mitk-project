from veil.helpdesk import DEMO_TICKET_ID, SimulatedHelpdeskTool, require_demo_ticket_id
from veil.demo_agent import DEMO_REQUESTER, LocalDemoAgent
from veil.demo_flow import run_ticket_demo
from veil.gateway import VeilGateway


def test_helpdesk_tool_looks_up_ticket_and_echoes_only_request_tokens() -> None:
    tool = SimulatedHelpdeskTool()
    payload = {
        "ticket_id": DEMO_TICKET_ID,
        "requester": {
            "name": "[[PERSON:demo-name]]",
            "email": "[[EMAIL:demo-email]]",
            "phone": "[[PHONE:demo-phone]]",
        },
        "question": "status and next update",
    }

    response = tool.call("lookup_helpdesk_ticket", payload)

    assert tool.received[0].payload == payload
    assert response["ticket"] == {
        "ticket_id": DEMO_TICKET_ID,
        "status": "In progress",
        "team": "Campus IT",
        "next_update": "10 minutes",
    }
    assert response["requester"] == payload["requester"]


def test_ticket_intake_accepts_repeated_mentions_of_one_known_ticket() -> None:
    message = f"Check {DEMO_TICKET_ID}; I mean {DEMO_TICKET_ID}."

    assert require_demo_ticket_id(message) == DEMO_TICKET_ID


def test_gateway_protects_ticket_request_and_agent_receives_restored_details() -> None:
    agent = LocalDemoAgent()
    tool_call = agent.build_ticket_lookup_call()
    tool = SimulatedHelpdeskTool()
    gateway = VeilGateway(simulated_tool=tool)
    task = gateway.start_task()

    result = gateway.call_tool(task, tool_call.tool_name, tool_call.payload)
    gateway.close_task(task)

    received_by_tool = tool.received[0].payload
    assert DEMO_TICKET_ID in repr(received_by_tool)
    for original in DEMO_REQUESTER.values():
        assert original not in repr(received_by_tool)
    assert result.audit.status == "allowed"
    assert result.audit.leakage_count == 0
    assert result.tool_response["requester"]["email"].startswith("[[EMAIL:")
    assert result.restored_response["requester"] == DEMO_REQUESTER
    assert "Maya Example" in agent.format_answer(result.restored_response)
    assert "maya@example.test" in agent.format_answer(result.restored_response)


def test_demo_can_show_verifier_blocking_before_tool_dispatch() -> None:
    demo = run_ticket_demo(show_blocked_path=True)

    assert demo.result.audit.status == "blocked"
    assert demo.result.audit.egress_verified is False
    assert demo.tool_payload is None
    assert demo.agent_answer is None



def test_helpdesk_accepts_free_form_support_request_and_echoes_protected_fields() -> None:
    tool = SimulatedHelpdeskTool()
    payload = {
        "user_message": "Please review [[CUSTOM_SENSITIVE:VTOKEN]].",
        "requester": {"name": "[[PERSON:VTOKEN]]", "email": "[[EMAIL:VTOKEN]]"},
    }

    response = tool.call("submit_support_request", payload)

    assert tool.received[0].payload == payload
    assert response["support_request"]["status"] == "received"
    assert response["requester"] == payload["requester"]
    assert response["message_echo"] == payload["user_message"]
