"""Tool-call boundary that sanitizes, verifies, dispatches, and restores."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from time import perf_counter
from uuid import uuid4

from veil.detection import PIIDetector
from veil.mock_tool import SimulatedTool
from veil.payload import (
    DetectionRecord,
    EgressBlocked,
    sanitize_payload,
    verify_egress,
)
from veil.token_vault import TokenVault


@dataclass
class TaskContext:
    """Short-lived mapping scope shared across calls in one agent task."""

    task_id: str
    vault: TokenVault
    closed: bool = False


@dataclass(frozen=True)
class AuditReceipt:
    status: str
    detection_count: int
    unique_token_count: int
    leakage_count: int
    restored_value_count: int
    added_latency_ms: float
    total_latency_ms: float
    egress_verified: bool
    blocked_reason: str | None = None


@dataclass(frozen=True)
class ToolCallResult:
    tool_name: str
    sanitized_payload: object
    tool_response: object | None
    restored_response: object | None
    detections: tuple[DetectionRecord, ...]
    audit: AuditReceipt

    def to_dict(self) -> dict[str, object]:
        return {
            "tool_name": self.tool_name,
            "sanitized_payload": self.sanitized_payload,
            "tool_response": self.tool_response,
            "restored_response": self.restored_response,
            "detections": [asdict(record) for record in self.detections],
            "audit": asdict(self.audit),
        }


class VeilGateway:
    def __init__(
        self,
        detector: PIIDetector | None = None,
        simulated_tool: SimulatedTool | None = None,
    ) -> None:
        self.detector = detector or PIIDetector()
        self.simulated_tool = simulated_tool or SimulatedTool()

    def start_task(self) -> TaskContext:
        return TaskContext(task_id=uuid4().hex, vault=TokenVault())

    def close_task(self, context: TaskContext) -> None:
        context.vault.clear()
        context.closed = True

    def call_tool(
        self, context: TaskContext, tool_name: str, payload: object
    ) -> ToolCallResult:
        if context.closed:
            raise RuntimeError("This Veil task context has already been cleared.")

        started = perf_counter()
        sanitized = sanitize_payload(payload, self.detector, context.vault)

        try:
            verify_egress(sanitized.payload, self.detector, context.vault)
            verify_egress(
                {"tool_name": tool_name}, self.detector, context.vault
            )
        except EgressBlocked as error:
            elapsed_ms = (perf_counter() - started) * 1000
            return ToolCallResult(
                tool_name=tool_name,
                sanitized_payload=sanitized.payload,
                tool_response=None,
                restored_response=None,
                detections=sanitized.records,
                audit=AuditReceipt(
                    status="blocked",
                    detection_count=len(sanitized.records),
                    unique_token_count=context.vault.token_count,
                    leakage_count=0,
                    restored_value_count=0,
                    added_latency_ms=round(elapsed_ms, 3),
                    total_latency_ms=round(elapsed_ms, 3),
                    egress_verified=False,
                    blocked_reason=str(error),
                ),
            )

        privacy_latency_ms = (perf_counter() - started) * 1000
        tool_response = self.simulated_tool.call(tool_name, sanitized.payload)
        restored_response = context.vault.restore(tool_response)
        total_latency_ms = (perf_counter() - started) * 1000

        return ToolCallResult(
            tool_name=tool_name,
            sanitized_payload=sanitized.payload,
            tool_response=tool_response,
            restored_response=restored_response,
            detections=sanitized.records,
            audit=AuditReceipt(
                status="allowed",
                detection_count=len(sanitized.records),
                unique_token_count=context.vault.token_count,
                leakage_count=0,
                restored_value_count=len(sanitized.records),
                added_latency_ms=round(privacy_latency_ms, 3),
                total_latency_ms=round(total_latency_ms, 3),
                egress_verified=True,
            ),
        )

