"""Recursive JSON tokenization and trusted-path restoration."""

from __future__ import annotations

from dataclasses import dataclass

from veil.detection import Detection, PIIDetector
from veil.token_vault import TokenVault


@dataclass(frozen=True)
class DetectionRecord:
    entity_type: str
    confidence: float
    path: str
    token: str


@dataclass(frozen=True)
class SanitizedPayload:
    payload: object
    records: tuple[DetectionRecord, ...]


class EgressBlocked(RuntimeError):
    """Raised when a payload still contains detectable/protected data."""


def sanitize_payload(
    payload: object,
    detector: PIIDetector,
    vault: TokenVault,
) -> SanitizedPayload:
    records: list[DetectionRecord] = []

    def visit(value: object, path: str) -> object:
        if isinstance(value, str):
            detections = detector.detect(value, field_hint=path)
            sanitized = value
            replacements: list[tuple[Detection, str]] = []
            for detection in detections:
                original = value[detection.start : detection.end]
                token = vault.tokenize(original, detection.entity_type)
                records.append(
                    DetectionRecord(
                        entity_type=detection.entity_type,
                        confidence=detection.confidence,
                        path=path,
                        token=token,
                    )
                )
                replacements.append((detection, token))

            # Replace from right to left so earlier spans keep their offsets.
            for detection, token in reversed(replacements):
                sanitized = (
                    sanitized[: detection.start]
                    + token
                    + sanitized[detection.end :]
                )
            return sanitized

        if isinstance(value, list):
            return [visit(item, f"{path}[{index}]") for index, item in enumerate(value)]

        if isinstance(value, dict):
            sanitized_dict = {}
            for key, item in value.items():
                sensitive_key = isinstance(key, str) and detector.detect(key)
                safe_key_path = (
                    f"{path}.<sensitive-key>" if sensitive_key else f"{path}.{key}"
                )
                sanitized_dict[key] = visit(item, safe_key_path)
            return sanitized_dict

        return value

    sanitized_payload = visit(payload, "$")
    return SanitizedPayload(sanitized_payload, tuple(records))


def verify_egress(payload: object, detector: PIIDetector, vault: TokenVault) -> None:
    """Fail closed if PII is still detectable or a known original remains."""

    if vault.contains_original_in(payload):
        raise EgressBlocked("A protected original value remains in the payload.")

    def visit(value: object, path: str) -> None:
        if isinstance(value, str):
            findings = detector.detect(value, field_hint=path)
            if findings:
                raise EgressBlocked(
                    f"Residual {findings[0].entity_type} detected at {path}."
                )
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")
        elif isinstance(value, dict):
            for key, item in value.items():
                key_findings = detector.detect(key) if isinstance(key, str) else []
                if key_findings:
                    raise EgressBlocked(
                        f"Residual {key_findings[0].entity_type} detected in an object key under {path}."
                    )
                visit(item, f"{path}.{key}")

    visit(payload, "$")

