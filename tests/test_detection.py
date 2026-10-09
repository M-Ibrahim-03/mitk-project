from veil.detection import PIIDetector


def test_detects_multiple_synthetic_pii_types_in_natural_language() -> None:
    detector = PIIDetector()
    text = (
        "Contact Avery Example at avery@example.test or phone +91 00000 00000. "
        "Student ID STU-DEMO-00127."
    )

    found = detector.detect(text)

    assert {item.entity_type for item in found} == {
        "PERSON",
        "EMAIL",
        "PHONE_NUMBER",
        "STUDENT_ID",
    }
    assert [text[item.start : item.end] for item in found] == [
        "Avery Example",
        "avery@example.test",
        "+91 00000 00000",
        "STU-DEMO-00127",
    ]


def test_detects_context_labelled_name_not_in_lexicon() -> None:
    detector = PIIDetector()
    text = "Customer name: Taylor Fictional"

    found = detector.detect(text)

    assert len(found) == 1
    assert found[0].entity_type == "PERSON"
    assert text[found[0].start : found[0].end] == "Taylor Fictional"


def test_detects_unformatted_synthetic_phone_number() -> None:
    detector = PIIDetector()
    text = "Callback number 0000000000"

    found = detector.detect(text)

    assert len(found) == 1
    assert found[0].entity_type == "PHONE_NUMBER"
    assert found[0].confidence < 0.9
    assert text[found[0].start : found[0].end] == "0000000000"


def test_detects_name_in_structured_name_field() -> None:
    detector = PIIDetector()
    text = "Taylor Fictional"

    found = detector.detect(text, field_hint="$.customer.full_name")

    assert len(found) == 1
    assert found[0].entity_type == "PERSON"
    assert text[found[0].start : found[0].end] == text


def test_leaves_unrelated_text_and_short_numbers_alone() -> None:
    detector = PIIDetector()

    assert detector.detect("Order 42 is ready for pickup.") == []




def test_detects_user_marked_custom_sensitive_value_exactly() -> None:
    secret = "case phrase ZQX-731"
    detector = PIIDetector(extra_values=(secret,))
    text = f"Please keep {secret} confidential."

    found = detector.detect(text)

    assert len(found) == 1
    assert found[0].entity_type == "CUSTOM_SENSITIVE"
    assert text[found[0].start:found[0].end] == secret
