from veil.evaluation import evaluate_cases


def test_synthetic_benchmark_reports_detection_leakage_restoration_and_latency() -> None:
    result = evaluate_cases()

    assert result["case_count"] >= 4
    assert result["planted_pii_instances"] >= 10
    assert result["detection_recall_percent"] == 100.0
    assert result["leakage_count"] == 0
    assert result["restoration_accuracy_percent"] == 100.0
    assert result["latency_sample_count"] == result["case_count"]
    assert result["added_latency_p95_ms"] >= 0

