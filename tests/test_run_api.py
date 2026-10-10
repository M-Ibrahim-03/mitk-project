from time import monotonic, sleep

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

import veil.api as api
from veil.api import DemoRunRequest, create_workflow_run, read_workflow_run, app
from veil.demo_agent import AgentRequest
from veil.gemini_agent import AgentProtocolError


@pytest.fixture(autouse=True)
def api_tests_default_to_deterministic_mode(monkeypatch) -> None:
    """Keep the user's local Gemini setting from leaking into API tests."""
    monkeypatch.setenv("VEIL_AGENT_MODE", "deterministic")


def test_gemini_mode_without_server_key_queues_run_for_local_fallback(monkeypatch) -> None:
    monkeypatch.setenv("VEIL_AGENT_MODE", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    created = create_workflow_run(
        DemoRunRequest(message="Check ticket TICKET-DEMO-1042 for its synthetic status.")
    )
    assert created["agent_mode"] == "gemini"
    assert created["status"] == "queued"
    deadline = monotonic() + 3
    snapshot = None
    while monotonic() < deadline:
        snapshot = read_workflow_run(created["run_id"])
        if snapshot["status"] in {"complete", "blocked", "failed"}:
            break
        sleep(0.01)
    assert snapshot is not None
    assert snapshot["status"] == "complete"
    assert any(event["stage"] == "agent_fallback" for event in snapshot["events"])
    assert snapshot["agent_answer"]


def test_api_rejects_ticket_not_in_local_helpdesk_before_queuing(monkeypatch) -> None:
    monkeypatch.setenv("VEIL_AGENT_MODE", "deterministic")

    try:
        create_workflow_run(DemoRunRequest(message="Check ticket TICKET-1000."))
    except HTTPException as error:
        assert error.status_code == 422
        assert "TICKET-DEMO-1042" in error.detail
    else:
        raise AssertionError("Unknown ticket must be rejected before it is queued")


def test_failed_gemini_run_reports_only_safe_protocol_error(monkeypatch) -> None:
    run_id = "safe-gemini-failure"
    api.run_store.create(run_id, agent_mode="gemini")

    def fail_before_call(**_kwargs):
        raise AgentProtocolError("Gemini request failed")

    monkeypatch.setattr(api, "run_ticket_demo", fail_before_call)
    api._execute_demo_run(
        run_id,
        AgentRequest("Check ticket TICKET-DEMO-1042."),
        (),
        "gemini",
    )

    snapshot = read_workflow_run(run_id)
    failure = next(event for event in snapshot["events"] if event["status"] == "failed")
    assert failure["message"] == "Gemini request failed"


def test_create_run_and_read_same_run_with_protected_tool_payload() -> None:
    request = {
        "message": (
            "Please check ticket TICKET-DEMO-1042. My name is Jordan Sample. "
            "My email is jordan@example.test and phone is 222-333-4444."
        ),
        "requester": {
            "name": "Jordan Sample",
            "email": "jordan@example.test",
            "phone": "222-333-4444",
        },
    }

    with TestClient(app) as client:
        created = client.post("/api/runs", json=request)

        assert created.status_code == 202
        run_id = created.json()["run_id"]
        assert created.json()["status"] == "queued"

        deadline = monotonic() + 3
        snapshot = None
        while monotonic() < deadline:
            response = client.get(f"/api/runs/{run_id}")
            assert response.status_code == 200
            snapshot = response.json()
            if snapshot["status"] in {"complete", "blocked", "failed"}:
                break
            sleep(0.01)

    assert snapshot is not None
    assert snapshot["run_id"] == run_id
    assert snapshot["status"] == "complete"
    assert snapshot["agent_mode"] == "deterministic"
    assert snapshot["audit"]["status"] == "allowed"
    assert "Jordan Sample" in snapshot["agent_answer"]
    assert "jordan@example.test" in snapshot["agent_answer"]

    tool_event = next(
        event
        for event in snapshot["events"]
        if event["stage"] == "helpdesk" and event["status"] == "complete"
    )
    captured_payload = tool_event["artifact"]
    assert "Jordan Sample" not in repr(captured_payload)
    assert "jordan@example.test" not in repr(captured_payload)
    assert "222-333-4444" not in repr(captured_payload)
    assert captured_payload["requester"]["email"].startswith("[[EMAIL:")
    assert snapshot["tool_response"]["requester"]["email"].startswith("[[EMAIL:")
    assert snapshot["restored_response"]["requester"]["email"] == "jordan@example.test"

    assert {event["run_id"] for event in snapshot["events"]} == {run_id}


def test_message_only_run_protects_sensitive_text_before_helpdesk() -> None:
    message = (
        "Please check ticket TICKET-DEMO-1042. My name is Jordan Sample. "
        "Email jordan@example.test, phone +91 90000 00000, Aadhaar 0000 0000 0000, "
        "bank account 123456789012, card 4111 1111 1111 1111, PAN ABCDE1234F, "
        "IFSC DEMO0001234, and IBAN GB82 WEST 1234 5698 7654 32."
    )
    raw_values = (
        "Jordan Sample",
        "jordan@example.test",
        "+91 90000 00000",
        "0000 0000 0000",
        "123456789012",
        "4111 1111 1111 1111",
        "ABCDE1234F",
        "DEMO0001234",
        "GB82 WEST 1234 5698 7654 32",
    )

    request = DemoRunRequest.model_validate({"message": message})
    assert request.requester is None
    created = create_workflow_run(request)
    run_id = created["run_id"]
    deadline = monotonic() + 3
    snapshot = None
    while monotonic() < deadline:
        snapshot = read_workflow_run(run_id)
        if snapshot["status"] in {"complete", "blocked", "failed"}:
            break
        sleep(0.01)

    assert snapshot is not None
    assert snapshot["status"] == "complete"
    assert snapshot["audit"]["status"] == "allowed"
    assert snapshot["agent_mode"] == "deterministic"
    assert snapshot["audit"]["egress_verified"] is True
    assert set(snapshot["tool_payload"]) == {"ticket_id", "user_message", "question"}
    assert not any(value in snapshot["tool_payload"]["user_message"] for value in raw_values)
    protected_message = snapshot["tool_payload"]["user_message"]
    for token_type in (
        "PERSON",
        "EMAIL",
        "PHONE_NUMBER",
        "AADHAAR",
        "BANK_ACCOUNT",
        "PAYMENT_CARD",
        "PAN",
        "IFSC",
        "IBAN",
    ):
        assert f"[[{token_type}:" in protected_message

    received_event = next(
        event
        for event in snapshot["events"]
        if event["stage"] == "request_received"
    )
    assert set(received_event["artifact"]) == {"message"}


def test_read_missing_run_returns_not_found() -> None:
    with TestClient(app) as client:
        response = client.get("/api/runs/does-not-exist")

    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow run not found."


def test_event_stream_replays_run_and_resumes_after_last_event_id() -> None:
    request = {
        "message": "Please check TICKET-DEMO-1042. My email is stream@example.test.",
        "requester": {
            "name": "Stream Sample",
            "email": "stream@example.test",
            "phone": "333-444-5555",
        },
    }
    with TestClient(app) as client:
        created = client.post("/api/runs", json=request)
        run_id = created.json()["run_id"]
        deadline = monotonic() + 3
        while monotonic() < deadline:
            snapshot = client.get(f"/api/runs/{run_id}").json()
            if snapshot["status"] in {"complete", "blocked", "failed"}:
                break
            sleep(0.01)

        replay = client.get(f"/api/runs/{run_id}/events")
        resumed = client.get(
            f"/api/runs/{run_id}/events", headers={"Last-Event-ID": "3"}
        )

    assert replay.status_code == 200
    assert replay.headers["content-type"].startswith("text/event-stream")
    assert "id: 0\nevent: workflow\ndata:" in replay.text
    assert "event: run_complete\ndata:" in replay.text
    assert '"run_id":"' + run_id + '"' in replay.text
    resumed_ids = [
        int(line.removeprefix("id: "))
        for line in resumed.text.splitlines()
        if line.startswith("id: ")
    ]
    assert resumed_ids
    assert min(resumed_ids) == 4
    assert "event: run_complete\ndata:" in resumed.text
