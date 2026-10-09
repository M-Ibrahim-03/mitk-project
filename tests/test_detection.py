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


def test_detects_context_name_before_conjunction_and_next_field() -> None:
    detector = PIIDetector()
    text = "My name is Jordan Sample and my email is jordan@example.test."

    found = detector.detect(text)

    assert [(item.entity_type, text[item.start : item.end]) for item in found] == [
        ("PERSON", "Jordan Sample"),
        ("EMAIL", "jordan@example.test"),
    ]


def test_detects_unformatted_synthetic_phone_number() -> None:
    detector = PIIDetector()
    text = "Callback number 0000000000"

    found = detector.detect(text)

    assert len(found) == 1
    assert found[0].entity_type == "PHONE_NUMBER"
    assert found[0].confidence >= 0.9
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


def test_detects_labeled_aadhaar_and_bank_account_numbers() -> None:
    detector = PIIDetector()
    text = "Aadhaar number: 0000 0000 0000; bank account: 123456789012."

    found = detector.detect(text)

    assert [
        (item.entity_type, text[item.start : item.end]) for item in found
    ] == [
        ("AADHAAR", "0000 0000 0000"),
        ("BANK_ACCOUNT", "123456789012"),
    ]


def test_detects_card_pan_ifsc_and_iban_formats() -> None:
    detector = PIIDetector()
    text = (
        "Card 4111 1111 1111 1111, PAN ABCDE1234F, "
        "IFSC DEMO0001234, IBAN GB82 WEST 1234 5698 7654 32."
    )

    found = detector.detect(text)

    assert [item.entity_type for item in found] == [
        "PAYMENT_CARD",
        "PAN",
        "IFSC",
        "IBAN",
    ]
    assert [text[item.start : item.end] for item in found] == [
        "4111 1111 1111 1111",
        "ABCDE1234F",
        "DEMO0001234",
        "GB82 WEST 1234 5698 7654 32",
    ]


def test_detects_spaced_iban_inside_sentence_without_absorbing_following_words() -> None:
    detector = PIIDetector()
    text = "IBAN GB82 WEST 1234 5698 7654 32 is synthetic."

    found = detector.detect(text)

    assert [(item.entity_type, text[item.start : item.end]) for item in found] == [
        ("IBAN", "GB82 WEST 1234 5698 7654 32")
    ]


def test_does_not_treat_an_unlabeled_long_identifier_as_a_phone_number() -> None:
    detector = PIIDetector()

    assert detector.detect("Reference 123456789012") == []


def test_does_not_classify_an_invalid_card_checksum_as_a_payment_card() -> None:
    detector = PIIDetector()

    assert all(
        item.entity_type != "PAYMENT_CARD"
        for item in detector.detect("Card 4111 1111 1111 1112")
    )


def test_detects_an_unformatted_phone_when_the_message_labels_it() -> None:
    detector = PIIDetector()
    text = "Mobile number: +91 9876543210"

    found = detector.detect(text)

    assert len(found) == 1
    assert found[0].entity_type == "PHONE_NUMBER"
    assert text[found[0].start : found[0].end] == "+91 9876543210"


def test_detects_email_with_invisible_unicode_and_preserves_original_span() -> None:
    detector = PIIDetector()
    text = "Contact synthetic riley@\u200bexample.test for updates."

    found = detector.detect(text)

    assert len(found) == 1
    assert found[0].entity_type == "EMAIL"
    assert text[found[0].start : found[0].end] == "riley@\u200bexample.test"


def test_detects_labeled_synthetic_upi_id_without_misclassifying_as_email() -> None:
    detector = PIIDetector()
    text = "UPI ID: riley.sample@demo-bank"

    found = detector.detect(text)

    assert len(found) == 1
    assert found[0].entity_type == "UPI_ID"
    assert text[found[0].start : found[0].end] == "riley.sample@demo-bank"
