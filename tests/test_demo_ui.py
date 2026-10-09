import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def demo_app(monkeypatch):
    project_root = Path(__file__).resolve().parent.parent
    local_temp = project_root / "work" / "streamlit-temp"
    local_temp.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TEMP", str(local_temp))
    monkeypatch.setenv("TMP", str(local_temp))
    monkeypatch.setattr(tempfile, "tempdir", str(local_temp))

    from streamlit.testing.v1 import AppTest

    return AppTest.from_file(str(project_root / "veil" / "demo.py"))


def test_custom_user_request_runs_through_veil_and_shows_actual_tool_payload(demo_app):
    app_test = demo_app.run(timeout=15)
    assert not app_test.exception

    app_test.text_area[0].set_value(
        "Please review this case phrase ZQX-731 for Riley Sample."
    )
    app_test.text_area[1].set_value("case phrase ZQX-731")
    app_test.text_input[0].set_value("Riley Sample")
    app_test.text_input[1].set_value("riley@example.test")
    app_test.text_input[2].set_value("111-222-3333")
    app_test.run(timeout=15)
    next(button for button in app_test.button if button.label == "Run workflow").click().run(timeout=15)

    assert not app_test.exception
    run = app_test.session_state["veil_ticket_demo"]
    assert run["result"]["audit"]["status"] == "allowed"
    assert [event["stage"] for event in run["events"] if event["status"] == "complete"] == [
        "request_received", "agent_planning", "tool_call_prepared", "privacy_scan",
        "egress_gate", "helpdesk", "tool_response", "response_restore", "agent_response",
    ]
    assert run["agent_call"]["tool_name"] == "submit_support_request"
    for original in (
        "Riley Sample", "riley@example.test", "111-222-3333", "case phrase ZQX-731"
    ):
        assert original not in repr(run["tool_payload"])
    assert "Riley Sample" in run["agent_answer"]
    assert "case phrase ZQX-731" in run["agent_answer"]
    assert any("What the helpdesk actually received" in item.value for item in app_test.markdown)
    rendered = "\n".join(item.value for item in app_test.markdown)
    assert "veil-flow" in rendered
    assert "veil-complete" in rendered
    assert "@keyframes veilPulse" in rendered
    assert "prefers-reduced-motion" in rendered
    labels = rendered
    assert "1. Agent prepares the helpdesk request" in labels
    assert "2. Veil checks and protects the request" in labels
    assert "3. Helpdesk receives the protected request" in labels
    assert "4. Veil restores the reply" in labels
    assert app_test.tabs == []


def test_editing_request_clears_old_workflow_trace(demo_app):
    app_test = demo_app.run(timeout=15)
    next(button for button in app_test.button if button.label == "Run workflow").click().run(timeout=15)
    assert "veil_ticket_demo" in app_test.session_state

    app_test.text_area[0].set_value("Please check ticket TICKET-DEMO-1042; new request.").run(timeout=15)

    assert "veil_ticket_demo" not in app_test.session_state


def test_blocked_workflow_marks_helpdesk_not_reached(demo_app):
    app_test = demo_app.run(timeout=15)
    next(button for button in app_test.button if button.label == "Show blocked example").click().run(timeout=15)

    assert not app_test.exception
    run = app_test.session_state["veil_ticket_demo"]
    assert run["result"]["audit"]["status"] == "blocked"
    assert run["tool_payload"] is None
    assert run["agent_answer"] is None
    assert run["events"][-1]["stage"] == "egress_gate"
    assert run["events"][-1]["status"] == "blocked"
    assert all(event["stage"] != "helpdesk" for event in run["events"])
    visible = "\n".join(item.value for item in app_test.markdown)
    assert "Helpdesk not reached" in visible
    assert any("helpdesk was not called" in item.value.lower() for item in app_test.error)
