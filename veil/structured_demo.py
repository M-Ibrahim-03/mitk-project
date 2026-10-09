"""Reusable structured-payload example through Veil's generic tool gateway."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from veil.gateway import AuditReceipt, VeilGateway
from veil.mock_tool import SimulatedTool


@dataclass(frozen=True)
class StructuredPayloadDemoResult:
    original_payload: dict[str, object]
    sanitized_payload: object
    tool_receipt: object
    tokenized_response: object
    restored_response: object
    audit: AuditReceipt
    planted_values: tuple[str, ...]
    tool_call_count: int
    detection_types: tuple[str, ...]


def _sample_payload() -> tuple[dict[str, object], tuple[str, ...]]:
    values = (
        "Jordan Demo",
        "demo.user@example.test",
        "+91 00000 00000",
        "0000 0000 0000",
        "123456789012",
        "sample.user@demo-bank",
        "4111 1111 1111 1111",
        "ABCDE1234F",
        "DEMO0001234",
        "GB82 WEST 1234 5698 7654 32",
        "STU-DEMO-00042",
    )
    payload: dict[str, object] = {
        "request_id": "CASE-DEMO-0421",
        "requester": {
            "name": values[0],
            "email": values[1],
            "phone": values[2],
        },
        "records": [
            {"kind": "identity", "note": f"Aadhaar number: {values[3]}"},
            {"kind": "bank", "note": f"Bank account: {values[4]}"},
            {"kind": "payment", "note": f"UPI ID: {values[5]}"},
            {"kind": "card", "note": f"Card: {values[6]}"},
            {"kind": "tax", "note": f"PAN: {values[7]}"},
            {"kind": "routing", "note": f"IFSC: {values[8]}"},
            {"kind": "international", "note": f"IBAN {values[9]}"},
            {"kind": "student", "id": values[10]},
        ],
        "conversation": [
            f"My name is {values[0]}.",
            f"Please send a copy to {values[1]} and call {values[2]}.",
        ],
    }
    return payload, values


def run_structured_payload_demo() -> StructuredPayloadDemoResult:
    """Run nested JSON and natural-language values through a local mock tool."""
    payload, planted_values = _sample_payload()
    tool = SimulatedTool()
    gateway = VeilGateway(simulated_tool=tool)
    context = gateway.start_task()
    try:
        result = gateway.call_tool(context, "structured_demo_tool", payload)
    finally:
        gateway.close_task(context)

    if result.audit.status != "allowed" or len(tool.received) != 1:
        raise RuntimeError("Veil did not safely complete the structured example.")

    # The displayed receipt comes from the exact deep copy recorded at dispatch.
    receipt = deepcopy(tool.received[0].payload)
    return StructuredPayloadDemoResult(
        original_payload=payload,
        sanitized_payload=result.sanitized_payload,
        tool_receipt=receipt,
        tokenized_response=result.tool_response,
        restored_response=result.restored_response,
        audit=result.audit,
        planted_values=planted_values,
        tool_call_count=len(tool.received),
        detection_types=tuple(sorted({record.entity_type for record in result.detections})),
    )
