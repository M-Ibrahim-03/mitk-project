import veil.evaluation as evaluation


SUPPORTED_ENTITY_TYPES = {
    "EMAIL",
    "PHONE_NUMBER",
    "PERSON",
    "STUDENT_ID",
    "AADHAAR",
    "BANK_ACCOUNT",
    "UPI_ID",
    "PAYMENT_CARD",
    "PAN",
    "IFSC",
    "IBAN",
}


def test_synthetic_benchmark_reports_detection_leakage_restoration_and_latency() -> None:
    result = evaluation.evaluate_cases(warmup_iterations=1, latency_iterations=2)

    assert result["case_count"] >= 20
    assert result["planted_pii_instances"] >= 22
    assert result["leakage_count"] == 0
    assert result["restoration_accuracy_percent"] is not None
    assert result["latency_sample_count"] == result["case_count"] * 2
    assert result["warmup_call_count"] == result["case_count"]
    assert result["added_latency_p95_ms"] >= 0
    assert result["latency_scope"] == "gateway sanitize and egress verification"
    assert result["runtime"]["python"]
    assert result["payload_size_bytes"]["max"] >= result["payload_size_bytes"]["min"]


def test_benchmark_suite_has_separate_development_and_heldout_results() -> None:
    result = evaluation.evaluate_benchmarks(
        warmup_iterations=1, latency_iterations=2
    )

    assert set(result["suites"]) == {"development", "heldout"}
    for suite in result["suites"].values():
        assert suite["case_count"] >= 20
        assert set(suite["detection_by_type"]) == SUPPORTED_ENTITY_TYPES
        assert suite["detection_recall_percent"] is not None
        assert suite["detection_f2_percent"] is not None
        assert suite["leakage_count"] == 0
        assert suite["negative_control_case_count"] >= 2
        for metrics in suite["detection_by_type"].values():
            assert {"tp", "fp", "fn", "precision_percent", "recall_percent", "f2_percent"} <= set(metrics)
            assert metrics["planted"] >= 2

    assert result["blocked_path"]["status"] == "blocked"
    assert result["blocked_path"]["tool_call_count"] == 0
    assert result["blocked_path"]["egress_verified"] is False


def test_evaluation_reports_per_type_detection_and_protects_normalized_values() -> None:
    text = "UPI ID: riley.sample@demo-bank; alternate riley@\u200bexample.test"
    result = evaluation.evaluate_cases(
        [
            {
                "name": "normalized_email_and_upi",
                "payload": {"message": text},
                "truth": [
                    {
                        "path": "$.message",
                        "value": "riley.sample@demo-bank",
                        "entity_type": "UPI_ID",
                    },
                    {
                        "path": "$.message",
                        "value": "riley@\u200bexample.test",
                        "entity_type": "EMAIL",
                    },
                ],
            }
        ]
    )

    assert result["leakage_count"] == 0
    assert result["restoration_accuracy_percent"] == 100.0
    assert result["detection_by_type"]["UPI_ID"]["tp"] == 1
    assert result["detection_by_type"]["UPI_ID"]["fp"] == 0
    assert result["detection_by_type"]["UPI_ID"]["fn"] == 0
    assert result["detection_by_type"]["UPI_ID"]["f2_percent"] == 100.0


def test_evaluator_scans_the_exact_captured_receipt_for_planted_values_anywhere() -> None:
    email = "receipt-canary@example.test"
    result = evaluation.evaluate_cases(
        [
            {
                "name": "nested_receipt_canary",
                "payload": {
                    "nested": [{"message": f"Contact {email}"}],
                    "safe": "no sensitive values here",
                },
                "truth": [
                    {
                        "path": "$.nested[0].message",
                        "value": email,
                        "entity_type": "EMAIL",
                    }
                ],
            }
        ],
        warmup_iterations=0,
        latency_iterations=1,
    )

    assert result["receipt_scan"]["tool_call_count"] == 1
    assert result["receipt_scan"]["scanned_tool_receipts"] == 1
    assert result["leakage_count"] == 0


def test_blocked_structured_key_case_reports_zero_tool_calls() -> None:
    result = evaluation.evaluate_cases(
        [
            {
                "name": "sensitive_object_key_fails_closed",
                "payload": {"key.user@example.test": "safe value"},
                "truth": [],
            }
        ],
        warmup_iterations=0,
        latency_iterations=1,
    )

    assert result["receipt_scan"]["allowed_case_count"] == 0
    assert result["receipt_scan"]["blocked_case_count"] == 1
    assert result["receipt_scan"]["tool_call_count"] == 0
    assert result["receipt_scan"]["blocked_tool_call_count"] == 0
    assert result["receipt_scan"]["scanned_tool_receipts"] == 0
