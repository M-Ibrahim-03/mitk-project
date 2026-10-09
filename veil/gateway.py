"""Tool-call boundary that sanitizes, verifies, dispatches, and restores."""

from __future__ import annotations

from collections.abc import Callable
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


GatewayProgressCallback = Callable[[str, str, object | None], None]


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
        self,
        context: TaskContext,
        tool_name: str,
        payload: object,
        *,
        on_progress: GatewayProgressCallback | None = None,
    ) -> ToolCallResult:
        if context.closed:
            raise RuntimeError("This Veil task context has already been cleared.")

        def report(stage: str, status: str, artifact: object | None = None) -> None:
            if on_progress is not None:
                on_progress(stage, status, artifact)

        started = perf_counter()
        report("privacy_scan", "active")
        try:
            sanitized = sanitize_payload(payload, self.detector, context.vault)
        except Exception:
            report("privacy_scan", "failed")
            report("egress_gate", "blocked")
            elapsed_ms = (perf_counter() - started) * 1000
            return self._failure_result(
                tool_name,
                status="blocked",
                elapsed_ms=elapsed_ms,
                reason="Veil could not safely inspect the outgoing request.",
            )
        report(
            "privacy_scan",
            "complete",
            {
                "sanitized_payload": sanitized.payload,
                "detections": sanitized.records,
            },
        )

        report("egress_gate", "active", sanitized.payload)
        try:
            verify_egress(sanitized.payload, self.detector, context.vault)
            verify_egress(
                {"tool_name": tool_name}, self.detector, context.vault
            )
        except EgressBlocked as error:
            report("egress_gate", "blocked", sanitized.payload)
            elapsed_ms = (perf_counter() - started) * 1000
            return self._failure_result(
                tool_name,
                status="blocked",
                elapsed_ms=elapsed_ms,
                reason=str(error),
                sanitized_payload=sanitized.payload,
                detections=sanitized.records,
                token_count=context.vault.token_count,
            )
        except Exception:
            report("egress_gate", "blocked")
            elapsed_ms = (perf_counter() - started) * 1000
            return self._failure_result(
                tool_name,
                status="blocked",
                elapsed_ms=elapsed_ms,
                reason="Veil could not verify the outgoing request.",
                sanitized_payload=sanitized.payload,
                detections=sanitized.records,
                token_count=context.vault.token_count,
            )

        report("egress_gate", "complete", sanitized.payload)
        privacy_latency_ms = (perf_counter() - started) * 1000
        report("helpdesk", "active", sanitized.payload)
        try:
            tool_response = self.simulated_tool.call(tool_name, sanitized.payload)
        except Exception:
            report("helpdesk", "failed")
            elapsed_ms = (perf_counter() - started) * 1000
            return self._failure_result(
                tool_name,
                status="failed",
                elapsed_ms=elapsed_ms,
                reason="The simulated helpdesk could not complete the request.",
                sanitized_payload=sanitized.payload,
                detections=sanitized.records,
                token_count=context.vault.token_count,
                egress_verified=True,
            )
        report("helpdesk", "complete")
        report("tool_response", "complete", tool_response)
        report("response_restore", "active")
        try:
            restored_response = context.vault.restore(tool_response)
        except Exception:
            report("response_restore", "failed")
            elapsed_ms = (perf_counter() - started) * 1000
            return self._failure_result(
                tool_name,
                status="failed",
                elapsed_ms=elapsed_ms,
                reason="Veil could not safely restore the helpdesk response.",
                sanitized_payload=sanitized.payload,
                detections=sanitized.records,
                token_count=context.vault.token_count,
                egress_verified=True,
                tool_response=tool_response,
            )
        report("response_restore", "complete", restored_response)
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



    @staticmethod
    def _failure_result(
        tool_name: str,
        *,
        status: str,
        elapsed_ms: float,
        reason: str,
        sanitized_payload: object | None = None,
        detections: tuple[DetectionRecord, ...] = (),
        token_count: int = 0,
        egress_verified: bool = False,
        tool_response: object | None = None,
    ) -> ToolCallResult:
        return ToolCallResult(
            tool_name=tool_name,
            sanitized_payload=sanitized_payload,
            tool_response=tool_response,
            restored_response=None,
            detections=detections,
            audit=AuditReceipt(
                status=status,
                detection_count=len(detections),
                unique_token_count=token_count,
                leakage_count=0,
                restored_value_count=0,
                added_latency_ms=round(elapsed_ms, 3),
                total_latency_ms=round(elapsed_ms, 3),
                egress_verified=egress_verified,
                blocked_reason=reason,
            ),
        )
