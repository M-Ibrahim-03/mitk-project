import pytest

from veil.demo_flow import WorkflowEvent
from veil.run_registry import RunCapacityError, RunStore


def test_store_rejects_new_run_when_all_capacity_is_active() -> None:
    store = RunStore(max_runs=1)
    store.create("active-run")

    with pytest.raises(RunCapacityError):
        store.create("second-run")


def test_store_expires_terminal_run_and_keeps_active_run() -> None:
    store = RunStore(ttl_seconds=0.01, max_runs=2)
    store.create("active-run")
    store.create("finished-run")
    store.fail(
        "finished-run",
        WorkflowEvent("finished-run", "workflow", "failed", "Safe generic failure."),
    )

    import time

    time.sleep(0.02)

    assert store.get("finished-run") is None
    assert store.get("active-run") is not None


def test_store_returns_event_snapshot_that_does_not_change_after_read() -> None:
    store = RunStore()
    store.create("snapshot-run")
    first = WorkflowEvent("snapshot-run", "first", "complete", "First.")
    store.append_event(first)

    record_snapshot = store.get("snapshot-run")
    store.append_event(WorkflowEvent("snapshot-run", "second", "complete", "Second."))

    assert record_snapshot is not None
    assert record_snapshot.events == [first]
