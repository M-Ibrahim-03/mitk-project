"""Bounded in-memory storage for local demonstration workflow runs."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field, replace
from threading import RLock
from time import monotonic
from typing import Literal

from veil.demo_flow import TicketDemoRun, WorkflowEvent

RunStatus = Literal["queued", "running", "complete", "blocked", "failed"]
TERMINAL_STATUSES = {"complete", "blocked", "failed"}


@dataclass
class WorkflowRunRecord:
    run_id: str
    agent_mode: str = "deterministic"
    created_at: float = field(default_factory=monotonic)
    status: RunStatus = "queued"
    events: list[WorkflowEvent] = field(default_factory=list)
    result: TicketDemoRun | None = None
    completed_at: float | None = None


class RunCapacityError(RuntimeError):
    """Raised when all run slots are occupied by active workflows."""


class RunStore:
    """Keep replayable run evidence in memory with expiry and capacity limits."""

    def __init__(self, *, ttl_seconds: float = 900, max_runs: int = 100) -> None:
        if ttl_seconds <= 0 or max_runs < 1:
            raise ValueError("Run store limits must be positive.")
        self.ttl_seconds = ttl_seconds
        self.max_runs = max_runs
        self._runs: OrderedDict[str, WorkflowRunRecord] = OrderedDict()
        self._lock = RLock()

    def create(
        self, run_id: str, *, agent_mode: str = "deterministic"
    ) -> WorkflowRunRecord:
        with self._lock:
            self._prune_expired()
            if run_id in self._runs:
                raise ValueError("Run ID already exists.")
            while len(self._runs) >= self.max_runs:
                removable_id = next(
                    (
                        stored_id
                        for stored_id, record in self._runs.items()
                        if record.status in TERMINAL_STATUSES
                    ),
                    None,
                )
                if removable_id is None:
                    raise RunCapacityError("All local workflow slots are busy.")
                del self._runs[removable_id]
            record = WorkflowRunRecord(run_id=run_id, agent_mode=agent_mode)
            self._runs[run_id] = record
            return record

    def mark_running(self, run_id: str) -> None:
        with self._lock:
            record = self._runs.get(run_id)
            if record is not None and record.status == "queued":
                record.status = "running"

    def append_event(self, event: WorkflowEvent) -> None:
        with self._lock:
            record = self._runs.get(event.run_id)
            if record is not None:
                record.events.append(event)

    def finish(self, run: TicketDemoRun) -> None:
        with self._lock:
            record = self._runs.get(run.run_id)
            if record is None:
                return
            record.result = run
            record.events = list(run.events)
            if run.result.audit.status == "blocked":
                record.status = "blocked"
            elif run.result.audit.status == "failed":
                record.status = "failed"
            else:
                record.status = "complete"
            record.completed_at = monotonic()

    def fail(self, run_id: str, event: WorkflowEvent) -> None:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                return
            record.events.append(event)
            record.status = "failed"
            record.completed_at = monotonic()

    def get(self, run_id: str) -> WorkflowRunRecord | None:
        with self._lock:
            self._prune_expired()
            record = self._runs.get(run_id)
            if record is None:
                return None
            return replace(record, events=list(record.events))

    def _prune_expired(self) -> None:
        now = monotonic()
        expired = [
            run_id
            for run_id, record in self._runs.items()
            if record.completed_at is not None
            and now - record.completed_at >= self.ttl_seconds
        ]
        for run_id in expired:
            del self._runs[run_id]
