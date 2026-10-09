"""Synthetic, exact-span evaluation for Veil's gateway boundary."""

from __future__ import annotations

import json
import platform
import re
import sys
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any

from veil.detection import PIIDetector
from veil.gateway import VeilGateway
from veil.mock_tool import SimulatedTool


DATA_PATH = Path(__file__).resolve().parent.parent / "data"
DEVELOPMENT_BENCHMARK_PATH = DATA_PATH / "benchmark.json"
HELDOUT_BENCHMARK_PATH = DATA_PATH / "benchmark-heldout.json"
PATH_PART_RE = re.compile(r"\.([^\.\[\]]+)|\[(\d+)\]")
DEFAULT_WARMUP_ITERATIONS = 20
DEFAULT_LATENCY_ITERATIONS = 100


def _string_fields(value: object, path: str = "$"):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _string_fields(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _string_fields(item, f"{path}.{key}")


def _all_strings(value: object):
    """Walk keys and values for an independent exact-literal boundary scan."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _all_strings(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                yield key
            yield from _all_strings(item)


def _get_path(value: object, path: str) -> object:
    current = value
    for key, index in PATH_PART_RE.findall(path[1:]):
        if key:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        else:
            if not isinstance(current, list):
                return None
            current = current[int(index)]
    return current


def _expected_spans(case: dict[str, Any]) -> set[tuple[str, int, int, str]]:
    fields = dict(_string_fields(case["payload"]))
    cursors: Counter[tuple[str, str]] = Counter()
    spans: set[tuple[str, int, int, str]] = set()
    for item in case["truth"]:
        path, value = item["path"], item["value"]
        text = fields.get(path)
        if text is None:
            raise ValueError(f"Truth path {path} does not point to text in {case['name']}")
        cursor_key = (path, value)
        start = text.find(value, cursors[cursor_key])
        if start < 0:
            raise ValueError(f"Truth value is missing at {path} in {case['name']}")
        end = start + len(value)
        cursors[cursor_key] = end
        spans.add((path, start, end, item["entity_type"]))
    return spans


def _percent(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(100 * numerator / denominator, 2)


def _f2_percent(true_positives: int, false_positives: int, false_negatives: int) -> float | None:
    precision_denominator = true_positives + false_positives
    recall_denominator = true_positives + false_negatives
    if precision_denominator == 0 or recall_denominator == 0:
        return None
    precision = true_positives / precision_denominator
    recall = true_positives / recall_denominator
    score = 5 * precision * recall / (4 * precision + recall)
    return round(100 * score, 2)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = max(0, min(len(sorted_values) - 1, int((percentile / 100) * len(sorted_values) + 0.999) - 1))
    return round(sorted_values[index], 3)


def _score_counts(true_positives: int, false_positives: int, false_negatives: int) -> dict[str, object]:
    return {
        "tp": true_positives,
        "fp": false_positives,
        "fn": false_negatives,
        "precision_percent": _percent(true_positives, true_positives + false_positives),
        "recall_percent": _percent(true_positives, true_positives + false_negatives),
        "f2_percent": _f2_percent(true_positives, false_positives, false_negatives),
    }


def _encoded_size(payload: object) -> int:
    return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _count_literal_leaks(payload: object, planted_values: Counter[str]) -> int:
    strings = tuple(_all_strings(payload))
    return sum(count * sum(text.count(value) for text in strings) for value, count in planted_values.items())


def _run_gateway(payload: object, *, gateway: VeilGateway) -> tuple[object, object, int]:
    """Run one local tool call and return the result, exact receipt, and call delta."""
    before = len(gateway.simulated_tool.received)
    context = gateway.start_task()
    try:
        result = gateway.call_tool(context, "synthetic_demo_tool", payload)
    finally:
        gateway.close_task(context)
    calls = gateway.simulated_tool.received[before:]
    receipt = calls[-1].payload if calls else None
    return result, receipt, len(calls)


def _load_cases(path: Path) -> list[dict[str, Any]]:
    cases = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise ValueError(f"Benchmark file {path.name} must contain a JSON array.")
    return cases


def evaluate_cases(
    cases: list[dict[str, Any]] | None = None,
    *,
    warmup_iterations: int = DEFAULT_WARMUP_ITERATIONS,
    latency_iterations: int = DEFAULT_LATENCY_ITERATIONS,
) -> dict[str, object]:
    """Evaluate a corpus, separately measuring warmed gateway-only latency."""
    if warmup_iterations < 0 or latency_iterations < 1:
        raise ValueError("Warm-up iterations must be non-negative and latency iterations positive.")
    if cases is None:
        cases = _load_cases(DEVELOPMENT_BENCHMARK_PATH)

    detector = PIIDetector()
    tool = SimulatedTool()
    gateway = VeilGateway(detector=detector, simulated_tool=tool)
    planted_by_type: Counter[str] = Counter()
    detected_by_type: Counter[str] = Counter()
    false_positives_by_type: Counter[str] = Counter()
    all_expected: set[tuple[str, int, int, str, str]] = set()
    all_actual: set[tuple[str, int, int, str, str]] = set()
    planted_count = detected_count = false_positive_count = 0
    leakage_count = restoration_total = restoration_correct = 0
    allowed_case_count = blocked_case_count = blocked_tool_call_count = 0
    receipt_scan_count = total_tool_call_count = 0
    latencies: list[float] = []
    payload_sizes = [_encoded_size(case["payload"]) for case in cases]
    warmup_call_count = 0

    for case in cases:
        payload = case["payload"]
        expected = _expected_spans(case)
        planted_count += len(expected)
        planted_by_type.update(span[3] for span in expected)
        expected_for_case = {
            (case["name"], path, start, end, entity_type)
            for path, start, end, entity_type in expected
        }
        all_expected.update(expected_for_case)

        actual: set[tuple[str, int, int, str, str]] = set()
        for path, text in _string_fields(payload):
            for item in detector.detect(text, field_hint=path):
                actual.add((case["name"], path, item.start, item.end, item.entity_type))
        all_actual.update(actual)
        true_positives = expected_for_case & actual
        false_positives = actual - expected_for_case
        false_negatives = expected_for_case - actual
        detected_count += len(true_positives)
        false_positive_count += len(false_positives)
        detected_by_type.update(item[4] for item in true_positives)
        false_positives_by_type.update(item[4] for item in false_positives)

        result, receipt, tool_call_count = _run_gateway(payload, gateway=gateway)
        total_tool_call_count += tool_call_count
        if result.audit.status == "allowed":
            allowed_case_count += 1
        elif result.audit.status == "blocked":
            blocked_case_count += 1
            blocked_tool_call_count += tool_call_count
        if receipt is not None:
            receipt_scan_count += 1
            planted_values = Counter(item["value"] for item in case["truth"])
            leakage_count += _count_literal_leaks(receipt, planted_values)

        if result.audit.status == "allowed":
            restoration_total += len(result.detections)
            expected_restored = {
                "status": "accepted",
                "tool": "synthetic_demo_tool",
                "echo": payload,
            }
            if result.restored_response == expected_restored:
                restoration_correct += len(result.detections)

        timing_tool = SimulatedTool()
        timing_gateway = VeilGateway(detector=detector, simulated_tool=timing_tool)
        for iteration in range(warmup_iterations + latency_iterations):
            timing_result, _, _ = _run_gateway(payload, gateway=timing_gateway)
            if iteration < warmup_iterations:
                warmup_call_count += 1
            else:
                latencies.append(timing_result.audit.added_latency_ms)

    entity_types = sorted(set(planted_by_type) | set(detected_by_type) | set(false_positives_by_type))
    detection_by_type: dict[str, dict[str, object]] = {}
    for entity_type in entity_types:
        tp = detected_by_type[entity_type]
        fp = false_positives_by_type[entity_type]
        fn = planted_by_type[entity_type] - tp
        detection_by_type[entity_type] = {
            "planted": planted_by_type[entity_type],
            "detected": tp,
            "missed": fn,
            "false_positives": fp,
            **_score_counts(tp, fp, fn),
        }

    global_tp = len(all_expected & all_actual)
    global_fp = len(all_actual - all_expected)
    global_fn = len(all_expected - all_actual)
    return {
        "case_count": len(cases),
        "negative_control_case_count": sum(not case["truth"] for case in cases),
        "planted_pii_instances": planted_count,
        "detected_pii_instances": detected_count,
        "detection_recall_percent": _percent(detected_count, planted_count),
        "detection_by_type": detection_by_type,
        "false_positive_count": false_positive_count,
        "precision_percent": _percent(detected_count, detected_count + false_positive_count),
        "detection_f2_percent": _f2_percent(global_tp, global_fp, global_fn),
        "leakage_count": leakage_count,
        "receipt_scan": {
            "scanned_tool_receipts": receipt_scan_count,
            "tool_call_count": total_tool_call_count,
            "allowed_case_count": allowed_case_count,
            "blocked_case_count": blocked_case_count,
            "blocked_tool_call_count": blocked_tool_call_count,
            "scan_scope": "exact captured simulated-tool payload, including object keys and values",
        },
        "restored_token_occurrences": restoration_correct,
        "token_occurrences_to_restore": restoration_total,
        "restoration_accuracy_percent": _percent(restoration_correct, restoration_total),
        "added_latency_p50_ms": _percentile(latencies, 50),
        "added_latency_p95_ms": _percentile(latencies, 95),
        "latency_sample_count": len(latencies),
        "warmup_call_count": warmup_call_count,
        "latency_scope": "gateway sanitize and egress verification",
        "latency_excludes": ["simulated tool", "response restoration", "Gemini", "network"],
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "payload_size_bytes": {
            "min": min(payload_sizes, default=0),
            "median": median(payload_sizes) if payload_sizes else 0,
            "max": max(payload_sizes, default=0),
            "total": sum(payload_sizes),
        },
        "disclaimer": "Synthetic benchmark only; results do not prove universal PII detection.",
    }


class _MissFirstEmailDetector(PIIDetector):
    """Fault injection for verifying the independent egress gate."""

    def __init__(self) -> None:
        super().__init__()
        self._missed = False

    def detect(self, text: str, field_hint: str = ""):
        if "@" in text and not self._missed:
            self._missed = True
            return []
        return super().detect(text, field_hint=field_hint)


def evaluate_blocked_path() -> dict[str, object]:
    """Prove a simulated first-pass miss is stopped before the tool call."""
    tool = SimulatedTool()
    gateway = VeilGateway(detector=_MissFirstEmailDetector(), simulated_tool=tool)  # type: ignore[arg-type]
    result, _, tool_call_count = _run_gateway(
        {"message": "Synthetic callback missed@example.test"}, gateway=gateway
    )
    return {
        "status": result.audit.status,
        "egress_verified": result.audit.egress_verified,
        "tool_call_count": tool_call_count,
        "receipt_count": len(tool.received),
        "blocked_reason": result.audit.blocked_reason,
    }


def evaluate_benchmarks(
    *,
    warmup_iterations: int = DEFAULT_WARMUP_ITERATIONS,
    latency_iterations: int = DEFAULT_LATENCY_ITERATIONS,
) -> dict[str, object]:
    """Run development, held-out, and fault-injected boundary evaluations."""
    suites = {
        "development": evaluate_cases(
            _load_cases(DEVELOPMENT_BENCHMARK_PATH),
            warmup_iterations=warmup_iterations,
            latency_iterations=latency_iterations,
        ),
        "heldout": evaluate_cases(
            _load_cases(HELDOUT_BENCHMARK_PATH),
            warmup_iterations=warmup_iterations,
            latency_iterations=latency_iterations,
        ),
    }
    return {"suites": suites, "blocked_path": evaluate_blocked_path()}


def main() -> None:
    print(json.dumps(evaluate_benchmarks(), indent=2))


if __name__ == "__main__":
    main()
