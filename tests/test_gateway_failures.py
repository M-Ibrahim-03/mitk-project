import pytest

from veil.gateway import VeilGateway
from veil.mock_tool import SimulatedTool


class ExplodingDetector:
    def detect(self, text: str, field_hint: str = "") -> list:
        raise RuntimeError("private@example.test detector internals")


def test_detector_failure_fails_closed_without_exposing_input_or_dispatching() -> None:
    tool = SimulatedTool()
    gateway = VeilGateway(detector=ExplodingDetector(), simulated_tool=tool)  # type: ignore[arg-type]
    context = gateway.start_task()
    secret = "private@example.test"
    events: list[tuple[str, str, object | None]] = []

    result = gateway.call_tool(
        context,
        "lookup",
        {"email": secret},
        on_progress=lambda stage, status, artifact: events.append((stage, status, artifact)),
    )

    assert result.audit.status == "blocked"
    assert result.audit.egress_verified is False
    assert result.sanitized_payload is None
    assert result.tool_response is None and result.restored_response is None
    assert secret not in repr(result.to_dict())
    assert "private@example.test" not in repr(result.audit)
    assert tool.received == []
    assert events[-1][1] in {"blocked", "failed"}
    gateway.close_task(context)


def test_tool_exception_returns_failed_without_exception_details_or_fake_response() -> None:
    class BrokenTool(SimulatedTool):
        def call(self, tool_name: str, payload: object) -> object:
            raise RuntimeError("private@example.test from downstream")

    gateway = VeilGateway(simulated_tool=BrokenTool())
    context = gateway.start_task()
    events: list[tuple[str, str, object | None]] = []

    result = gateway.call_tool(
        context,
        "lookup",
        {"email": "avery@example.test"},
        on_progress=lambda stage, status, artifact: events.append((stage, status, artifact)),
    )

    assert result.audit.status == "failed"
    assert result.audit.egress_verified is True
    assert result.tool_response is None and result.restored_response is None
    assert "private@example.test" not in repr(result.to_dict())
    assert ("helpdesk", "failed", None) in events
    gateway.close_task(context)
