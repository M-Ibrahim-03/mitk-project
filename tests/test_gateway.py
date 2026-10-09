import asyncio

import httpx
import pytest

from veil.api import app
from veil.detection import PIIDetector
from veil.gateway import VeilGateway
from veil.mock_tool import SimulatedTool
from veil.payload import EgressBlocked, sanitize_payload


def test_gateway_sends_only_tokens_and_restores_trusted_response() -> None:
    mock_tool = SimulatedTool()
    gateway = VeilGateway(simulated_tool=mock_tool)
    context = gateway.start_task()
    original = "avery@example.test"

    result = gateway.call_tool(
        context,
        "send_message",
        {"to": original, "body": f"Hello Avery Example, reply to {original}."},
    )

    captured = mock_tool.received[0].payload
    assert original not in repr(captured)
    assert result.audit.status == "allowed"
    assert result.audit.leakage_count == 0
    assert result.audit.egress_verified is True
    assert original in repr(result.restored_response)
    assert result.audit.restored_value_count == result.audit.detection_count

    gateway.close_task(context)
    assert context.closed is True
    assert context.vault.token_count == 0


def test_gateway_exempts_only_tokens_issued_by_the_current_vault(monkeypatch) -> None:
    monkeypatch.setattr("veil.token_vault.secrets.token_hex", lambda _: "ABC0DEF123")
    mock_tool = SimulatedTool()
    gateway = VeilGateway(simulated_tool=mock_tool)
    context = gateway.start_task()

    result = gateway.call_tool(
        context, "send_message", {"email": "riley@example.test"}
    )

    assert result.sanitized_payload["email"] == "[[EMAIL:VABC0DEF123]]"
    assert result.audit.status == "allowed"
    assert mock_tool.received[0].payload["email"] == "[[EMAIL:VABC0DEF123]]"
    gateway.close_task(context)

    class MissFirstIfscDetector:
        def __init__(self) -> None:
            self.missed = False
            self.real = PIIDetector()

        def detect(self, text: str, field_hint: str = "") -> list:
            if text == "VABC0DEF123" and not self.missed:
                self.missed = True
                return []
            return self.real.detect(text, field_hint=field_hint)

    unregistered_tool = SimulatedTool()
    guarded_gateway = VeilGateway(
        detector=MissFirstIfscDetector(),  # type: ignore[arg-type]
        simulated_tool=unregistered_tool,
    )
    unregistered_context = guarded_gateway.start_task()

    unregistered_result = guarded_gateway.call_tool(
        unregistered_context, "send_message", {"message": "VABC0DEF123"}
    )

    assert unregistered_result.audit.status == "blocked"
    assert unregistered_tool.received == []
    guarded_gateway.close_task(unregistered_context)


def test_gateway_preserves_current_vault_tokens_when_rescanning_request(monkeypatch) -> None:
    monkeypatch.setattr("veil.token_vault.secrets.token_hex", lambda _: "ABC0DEF123")
    detector = PIIDetector()
    mock_tool = SimulatedTool()
    gateway = VeilGateway(detector=detector, simulated_tool=mock_tool)
    context = gateway.start_task()
    original_message = "Contact riley@example.test"
    protected_message = sanitize_payload(
        original_message, detector, context.vault
    ).payload

    result = gateway.call_tool(
        context, "send_message", {"message": protected_message}
    )

    assert result.audit.status == "allowed"
    assert result.sanitized_payload["message"] == protected_message
    assert result.restored_response["echo"]["message"] == original_message
    gateway.close_task(context)


def test_gateway_does_not_dispatch_if_egress_check_finds_residual_pii() -> None:
    class MissFirstDetector:
        def __init__(self) -> None:
            self.seen: set[str] = set()
            self.real = PIIDetector()

        def detect(self, text: str, field_hint: str = "") -> list:
            if "@" in text and text not in self.seen:
                self.seen.add(text)
                return []
            return self.real.detect(text, field_hint=field_hint)

    mock_tool = SimulatedTool()
    gateway = VeilGateway(
        detector=MissFirstDetector(),  # type: ignore[arg-type]
        simulated_tool=mock_tool,
    )
    context = gateway.start_task()

    result = gateway.call_tool(
        context, "send_message", {"to": "missed@example.test"}
    )

    assert result.audit.status == "blocked"
    assert result.audit.egress_verified is False
    assert result.restored_response is None
    assert mock_tool.received == []


def test_closed_task_context_cannot_be_reused() -> None:
    gateway = VeilGateway()
    context = gateway.start_task()
    gateway.close_task(context)

    with pytest.raises(RuntimeError, match="already been cleared"):
        gateway.call_tool(context, "lookup", {"query": "safe"})


def test_same_value_reuses_token_across_tool_calls_in_one_task() -> None:
    gateway = VeilGateway()
    context = gateway.start_task()

    first = gateway.call_tool(context, "first", {"email": "avery@example.test"})
    second = gateway.call_tool(context, "second", {"email": "avery@example.test"})

    assert first.sanitized_payload["email"] == second.sanitized_payload["email"]
    assert first.sanitized_payload["email"].startswith("[[EMAIL:")
    gateway.close_task(context)


def test_gateway_blocks_pii_in_tool_name() -> None:
    mock_tool = SimulatedTool()
    gateway = VeilGateway(simulated_tool=mock_tool)
    context = gateway.start_task()

    result = gateway.call_tool(context, "avery@example.test", {"query": "safe"})

    assert result.audit.status == "blocked"
    assert mock_tool.received == []
    gateway.close_task(context)


def test_http_tool_endpoint_runs_local_mock_gateway() -> None:
    async def post_call() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(
                "/tool-call",
                json={
                    "tool_name": "lookup",
                    "payload": {"email": "riley@example.test"},
                },
            )

    response = asyncio.run(post_call())

    assert response.status_code == 200
    body = response.json()
    assert body["audit"]["status"] == "allowed"
    assert "riley@example.test" not in str(body["sanitized_payload"])
    assert body["restored_response"]["echo"]["email"] == "riley@example.test"
