"""Synthetic benchmark for Veil detection, egress, restoration, and latency."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any

from veil.detection import PIIDetector
from veil.gateway import VeilGateway
from veil.mock_tool import SimulatedTool


BENCHMARK_PATH = Path(__file__).resolve().parent.parent / "data" / "benchmark.json"
PATH_PART_RE = re.compile(r"\.([^\.\[\]]+)|\[(\d+)\]")


def _string_fields(value: object, path: str = "$"):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _string_fields(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _string_fields(item, f"{path}.{key}")


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


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = max(0, min(len(sorted_values) - 1, int((percentile / 100) * len(sorted_values) + 0.999) - 1))
    return round(sorted_values[index], 3)


def evaluate_cases(cases: list[dict[str, Any]] | None = None) -> dict[str, object]:
    if cases is None:
        cases = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))

    detector = PIIDetector()
    simulated_tool = SimulatedTool()
    gateway = VeilGateway(detector=detector, simulated_tool=simulated_tool)
    planted_count = detected_count = false_positive_count = 0
    leakage_count = restoration_total = restoration_correct = 0
    latencies: list[float] = []

    for case in cases:
        expected = _expected_spans(case)
        planted_count += len(expected)
        actual: set[tuple[str, int, int, str]] = set()
        for path, text in _string_fields(case["payload"]):
            for item in detector.detect(text, field_hint=path):
                actual.add((path, item.start, item.end, item.entity_type))

        true_positives = expected & actual
        detected_count += len(true_positives)
        false_positive_count += len(actual - expected)

        captured_before = len(simulated_tool.received)
        context = gateway.start_task()
        result = gateway.call_tool(context, "synthetic_demo_tool", case["payload"])
        latencies.append(result.audit.added_latency_ms)

        if len(simulated_tool.received) > captured_before:
            captured = simulated_tool.received[-1].payload
            planted_by_value = Counter(
                (item["path"], item["value"]) for item in case["truth"]
            )
            for (path, value), count in planted_by_value.items():
                outgoing_value = _get_path(captured, path)
                if isinstance(outgoing_value, str):
                    leakage_count += min(count, outgoing_value.count(value))

        if result.audit.status == "allowed":
            restoration_total += len(result.detections)
            expected_restored = {
                "status": "accepted",
                "tool": "synthetic_demo_tool",
                "echo": case["payload"],
            }
            if result.restored_response == expected_restored:
                restoration_correct += len(result.detections)

        gateway.close_task(context)

    precision_denominator = detected_count + false_positive_count
    return {
        "case_count": len(cases),
        "planted_pii_instances": planted_count,
        "detected_pii_instances": detected_count,
        "detection_recall_percent": _percent(detected_count, planted_count),
        "false_positive_count": false_positive_count,
        "precision_percent": _percent(detected_count, precision_denominator),
        "leakage_count": leakage_count,
        "restored_token_occurrences": restoration_correct,
        "token_occurrences_to_restore": restoration_total,
        "restoration_accuracy_percent": _percent(restoration_correct, restoration_total),
        "added_latency_p50_ms": _percentile(latencies, 50),
        "added_latency_p95_ms": _percentile(latencies, 95),
        "latency_sample_count": len(latencies),
        "disclaimer": "Synthetic benchmark only; results do not prove universal PII detection.",
    }


def main() -> None:
    print(json.dumps(evaluate_cases(), indent=2))


if __name__ == "__main__":
    main()

