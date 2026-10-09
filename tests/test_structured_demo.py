from veil.structured_demo import run_structured_payload_demo


def test_structured_payload_demo_shows_exact_protected_tool_receipt_and_restores() -> None:
    result = run_structured_payload_demo()

    receipt = result.tool_receipt
    assert result.tool_call_count == 1
    assert result.audit.status == "allowed"
    assert result.audit.egress_verified is True
    assert receipt == result.sanitized_payload
    assert result.restored_response["echo"] == result.original_payload
    assert result.tokenized_response["echo"] == receipt

    for original in result.planted_values:
        assert original not in repr(receipt)


def test_structured_payload_demo_uses_nested_objects_and_arrays() -> None:
    result = run_structured_payload_demo()

    assert isinstance(result.original_payload["requester"], dict)
    assert isinstance(result.original_payload["records"], list)
    assert result.audit.detection_count >= 10
    assert set(result.detection_types) == {
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
