from time import monotonic, sleep

from fastapi.testclient import TestClient

from veil.api import app


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
