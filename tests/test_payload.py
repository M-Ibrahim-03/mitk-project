from veil.detection import PIIDetector
from veil.payload import EgressBlocked, sanitize_payload, verify_egress
from veil.token_vault import TokenVault


def test_sanitizes_nested_values_and_reuses_tokens() -> None:
    detector = PIIDetector()
    vault = TokenVault()
    payload = {
        "recipient_email": "riley@example.test",
        "details": [
            "Please contact Riley Sample at riley@example.test.",
            {"phone": "+91 00000 00000", "age": 21},
        ],
    }

    result = sanitize_payload(payload, detector, vault)

    # The repeated email must map to one token in both fields.
    email_token = result.payload["recipient_email"]
    assert email_token.startswith("[[EMAIL:")
    assert email_token in result.payload["details"][0]
    assert "riley@example.test" not in repr(result.payload)
    assert result.payload["details"][1]["age"] == 21
    assert result.payload.keys() == payload.keys()
    assert vault.token_count == 3
    verify_egress(result.payload, detector, vault)


def test_restore_response_and_clear_vault() -> None:
    detector = PIIDetector()
    vault = TokenVault()
    result = sanitize_payload(
        {"text": "Reply to avery@example.test"}, detector, vault
    )
    token = result.payload["text"].split()[-1]

    restored = vault.restore({"echo": token})

    assert restored == {"echo": "avery@example.test"}
    vault.clear()
    assert vault.token_count == 0
    assert vault.restore_text(token) == token


def test_egress_guard_blocks_residual_pii_even_if_first_pass_missed_it() -> None:
    class MissOnceDetector:
        def __init__(self) -> None:
            self._seen: set[str] = set()
            self._real = PIIDetector()

        def detect(self, text: str, field_hint: str = "") -> list:
            key = f"{field_hint}:{text}"
            if key not in self._seen:
                self._seen.add(key)
                return []
            return self._real.detect(text, field_hint=field_hint)

    detector = MissOnceDetector()
    vault = TokenVault()
    result = sanitize_payload(
        {"email": "missed@example.test"},  # type: ignore[arg-type]
        detector,  # type: ignore[arg-type]
        vault,
    )
    try:
        verify_egress(result.payload, detector, vault)  # type: ignore[arg-type]
    except EgressBlocked as error:
        assert "Residual EMAIL" in str(error)
    else:
        raise AssertionError("The egress guard should block residual email PII")


def test_egress_guard_blocks_pii_embedded_in_a_json_key() -> None:
    try:
        verify_egress(
            {"avery@example.test": "safe value"}, PIIDetector(), TokenVault()
        )
    except EgressBlocked as error:
        assert "object key" in str(error)
        assert "avery@example.test" not in str(error)
    else:
        raise AssertionError("The egress guard should block PII inside JSON keys")

from veil.detection import PIIDetector
from veil.token_vault import TokenVault


def test_generated_token_cannot_match_the_phone_detector(monkeypatch) -> None:
    monkeypatch.setattr("veil.token_vault.secrets.token_hex", lambda _: "0000000000")
    token = TokenVault().tokenize("avery@example.test", "EMAIL")

    assert PIIDetector().detect(token) == []
