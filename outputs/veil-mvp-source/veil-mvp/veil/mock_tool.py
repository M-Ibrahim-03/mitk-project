"""Offline simulated external tool used by the demo and tests."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass


@dataclass(frozen=True)
class CapturedToolCall:
    tool_name: str
    payload: object


class SimulatedTool:
    """Capture sanitized requests and echo them as a mock response."""

    def __init__(self) -> None:
        self.received: list[CapturedToolCall] = []

    def call(self, tool_name: str, payload: object) -> dict[str, object]:
        captured = deepcopy(payload)
        self.received.append(CapturedToolCall(tool_name, captured))
        return {
            "status": "accepted",
            "tool": tool_name,
            "echo": deepcopy(captured),
        }

