"""Small, explainable, pure-Python PII recognizers for the Veil MVP.

The MVP intentionally avoids compiled NLP extensions because the current
Windows execution environment blocks them. Person-name recognition is
context-aware and lexicon-based; it is less comprehensive than a full NER model.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Detection:
    start: int
    end: int
    entity_type: str
    confidence: float


EMAIL_RE = re.compile(
    r"(?<![A-Z0-9._%+-])[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+",
    re.IGNORECASE,
)

PHONE_RE = re.compile(
    r"(?<![\w])(?:\+\d{1,3}[\s.-]?)?"
    r"(?:\(?\d{2,4}\)?[\s.-]?)?"
    r"\d{3,5}[\s.-]\d{3,5}(?!\w)(?![\s.-]?\d)"
)
PHONE_CONTEXT_RE = re.compile(
    r"\b(?:phone|mobile|cell|callback|contact)(?:\s+(?:number|no\.?))?\s*"
    r"(?:is\s*)?[:=]?\s*(?P<number>\+?\d(?:[\s().-]?\d){7,14})"
    r"(?![\s.-]?\d)",
    re.IGNORECASE,
)
UNFORMATTED_PHONE_RE = re.compile(r"(?<!\w)\d{10}(?!\w)")

AADHAAR_CONTEXT_RE = re.compile(
    r"\b(?:aadhaar|aadhar|uid)\s*(?:card\s*)?"
    r"(?:number|no\.?|#)?\s*(?:is\s*)?[:=]?\s*"
    r"(?P<number>(?:\d[ -]?){11}\d)(?![\d])",
    re.IGNORECASE,
)
BANK_ACCOUNT_CONTEXT_RE = re.compile(
    r"\b(?:bank[ -]+account|account|acct\.?|a/c)\s*"
    r"(?:number|no\.?|#)?\s*(?:is\s*)?[:=]?\s*"
    r"(?P<number>(?:\d[ -]?){7,17}\d)(?![\d])",
    re.IGNORECASE,
)
UPI_CONTEXT_RE = re.compile(
    r"\b(?:upi(?:\s+(?:id|address))?|vpa)\s*(?:is\s*)?[:=]?\s*"
    r"(?P<value>[A-Z0-9][A-Z0-9._-]{1,63}@[A-Z0-9][A-Z0-9.-]{1,63})"
    r"(?![\w.-])",
    re.IGNORECASE,
)
PAYMENT_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?![\d])")
PAN_RE = re.compile(r"(?<![A-Z0-9])[A-Z]{5}\d{4}[A-Z](?![A-Z0-9])", re.IGNORECASE)
IFSC_RE = re.compile(r"(?<![A-Z0-9])[A-Z]{4}0[A-Z0-9]{6}(?![A-Z0-9])", re.IGNORECASE)
IBAN_START_RE = re.compile(r"(?<![A-Z0-9])[A-Z]{2}\d{2}", re.IGNORECASE)

STUDENT_ID_RE = re.compile(r"\bSTU-DEMO-\d{5}\b", re.IGNORECASE)

NAME_CONTEXT_RE = re.compile(
    r"(?i:\b(?:my\s+name\s+is|name\s*(?:is|:|=)|contact(?:\s+name)?\s*(?:is|:|=)?|"
    r"customer(?:\s+name)?\s*(?:is|:|=)?|person\s*(?:is|:|=)|"
    r"user\s*(?:is|:|=)|to))\s+"
    r"(?P<name>[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?"
    r"(?:\s+[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?){1,2})\b"
)
STRUCTURED_NAME_RE = re.compile(
    r"^\s*(?P<name>[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?"
    r"(?:\s+[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?){0,2})\s*$"
)

# Fictional names used by the local demo and synthetic evaluation set.
SYNTHETIC_NAME_LEXICON = (
    "Avery Example",
    "Riley Sample",
    "Jordan Demo",
    "Casey Test",
    "Morgan Placeholder",
)

ZERO_WIDTH_FORMAT_CHARS = frozenset("\u200b\u200c\u200d\ufeff")


def _normalize_detection_text(text: str) -> tuple[str, tuple[tuple[int, int], ...]]:
    """Normalize lookalike forms while retaining offsets into the source text."""
    normalized: list[str] = []
    source_spans: list[tuple[int, int]] = []
    for index, character in enumerate(text):
        if character in ZERO_WIDTH_FORMAT_CHARS:
            continue
        for normalized_character in unicodedata.normalize("NFKC", character):
            if normalized_character in ZERO_WIDTH_FORMAT_CHARS:
                continue
            normalized.append(normalized_character)
            source_spans.append((index, index + 1))
    return "".join(normalized), tuple(source_spans)


class PIIDetector:
    """Find selected PII types using deterministic local patterns."""

    _priority = {
        "CUSTOM_SENSITIVE": 10,
        "EMAIL": 9,
        "PAYMENT_CARD": 8,
        "AADHAAR": 8,
        "UPI_ID": 8,
        "IBAN": 8,
        "PAN": 7,
        "IFSC": 7,
        "BANK_ACCOUNT": 7,
        "STUDENT_ID": 6,
        "PHONE_NUMBER": 3,
        "PERSON": 2,
    }

    def __init__(
        self,
        extra_names: tuple[str, ...] = (),
        extra_values: tuple[str, ...] = (),
    ) -> None:
        names = (*SYNTHETIC_NAME_LEXICON, *extra_names)
        self._name_patterns = tuple(
            (
                name,
                re.compile(
                    rf"(?<!\w){re.escape(_normalize_detection_text(name)[0])}(?!\w)",
                    re.IGNORECASE,
                ),
            )
            for name in names
        )
        self._custom_value_patterns = tuple(
            (value, re.compile(re.escape(_normalize_detection_text(value)[0])))
            for value in dict.fromkeys(value for value in extra_values if value)
        )

    def detect(self, text: str, field_hint: str = "") -> list[Detection]:
        normalized_text, source_spans = _normalize_detection_text(text)
        normalized_hint = _normalize_detection_text(field_hint)[0]
        findings = self._detect_normalized(normalized_text, normalized_hint)
        if normalized_text == text:
            return findings

        mapped: list[Detection] = []
        for finding in findings:
            if finding.start >= finding.end or finding.end > len(source_spans):
                continue
            mapped.append(
                Detection(
                    start=source_spans[finding.start][0],
                    end=source_spans[finding.end - 1][1],
                    entity_type=finding.entity_type,
                    confidence=finding.confidence,
                )
            )
        return mapped

    def _detect_normalized(self, text: str, field_hint: str = "") -> list[Detection]:
        candidates: list[Detection] = []

        for _, pattern in self._custom_value_patterns:
            for match in pattern.finditer(text):
                candidates.append(
                    Detection(match.start(), match.end(), "CUSTOM_SENSITIVE", 1.0)
                )

        for match in EMAIL_RE.finditer(text):
            candidates.append(Detection(match.start(), match.end(), "EMAIL", 0.99))

        for match in AADHAAR_CONTEXT_RE.finditer(text):
            start, end = match.span("number")
            candidates.append(Detection(start, end, "AADHAAR", 0.99))

        for match in BANK_ACCOUNT_CONTEXT_RE.finditer(text):
            start, end = match.span("number")
            candidates.append(Detection(start, end, "BANK_ACCOUNT", 0.96))

        for match in UPI_CONTEXT_RE.finditer(text):
            start, end = match.span("value")
            candidates.append(Detection(start, end, "UPI_ID", 0.96))

        for match in PAYMENT_CARD_RE.finditer(text):
            if _passes_luhn(match.group()):
                candidates.append(
                    Detection(match.start(), match.end(), "PAYMENT_CARD", 0.99)
                )

        for match in PAN_RE.finditer(text):
            candidates.append(Detection(match.start(), match.end(), "PAN", 0.96))

        for match in IFSC_RE.finditer(text):
            candidates.append(Detection(match.start(), match.end(), "IFSC", 0.96))

        candidates.extend(_find_iban_detections(text))

        for match in PHONE_CONTEXT_RE.finditer(text):
            start, end = match.span("number")
            digits = sum(char.isdigit() for char in match.group("number"))
            if 8 <= digits <= 15:
                candidates.append(Detection(start, end, "PHONE_NUMBER", 0.96))

        for match in STUDENT_ID_RE.finditer(text):
            candidates.append(Detection(match.start(), match.end(), "STUDENT_ID", 0.99))

        for match in PHONE_RE.finditer(text):
            digits = sum(char.isdigit() for char in match.group())
            if 8 <= digits <= 15:
                candidates.append(
                    Detection(match.start(), match.end(), "PHONE_NUMBER", 0.92)
                )

        for match in UNFORMATTED_PHONE_RE.finditer(text):
            # A digit-only 10–15 digit value is ambiguous (it could be an
            # account number), so keep confidence lower and document this
            # format as a false-positive risk in the MVP.
            candidates.append(
                Detection(match.start(), match.end(), "PHONE_NUMBER", 0.78)
            )

        for _, pattern in self._name_patterns:
            for match in pattern.finditer(text):
                candidates.append(Detection(match.start(), match.end(), "PERSON", 0.96))

        for match in NAME_CONTEXT_RE.finditer(text):
            name = match.group("name")
            # Do not treat all-lowercase text as a person just because the
            # context regex itself is case-insensitive.
            if name and all(part[:1].isupper() for part in name.split()):
                candidates.append(
                    Detection(match.start("name"), match.end("name"), "PERSON", 0.84)
                )

        leaf = field_hint.rsplit(".", 1)[-1].lower()
        has_person_field_hint = leaf in {"person", "contact", "customer"} or bool(
            re.search(r"(?:^|[_-])(?:name|firstname|lastname|fullname)(?:$|[_-])", leaf)
        )
        if has_person_field_hint:
            match = STRUCTURED_NAME_RE.fullmatch(text)
            if match:
                candidates.append(
                    Detection(
                        match.start("name"),
                        match.end("name"),
                        "PERSON",
                        0.88,
                    )
                )

        # Keep the strongest non-overlapping match. This prevents a numeric
        # substring inside a synthetic identifier from also becoming a phone.
        candidates.sort(
            key=lambda item: (
                -self._priority[item.entity_type],
                item.start,
                -(item.end - item.start),
            )
        )
        selected: list[Detection] = []
        for candidate in candidates:
            if any(
                candidate.start < existing.end and existing.start < candidate.end
                for existing in selected
            ):
                continue
            selected.append(candidate)

        return sorted(selected, key=lambda item: (item.start, item.end))


def _passes_luhn(value: str) -> bool:
    digits = [int(char) for char in value if char.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False

    checksum = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def _passes_iban_checksum(value: str) -> bool:
    compact = "".join(char for char in value.upper() if char.isalnum())
    if not 15 <= len(compact) <= 34:
        return False

    rearranged = compact[4:] + compact[:4]
    remainder = 0
    for char in rearranged:
        digits = str(ord(char) - ord("A") + 10) if char.isalpha() else char
        for digit in digits:
            remainder = (remainder * 10 + int(digit)) % 97
    return remainder == 1


def _find_iban_detections(text: str) -> list[Detection]:
    """Find the shortest checksum-valid IBAN at each start, before prose."""
    findings: list[Detection] = []
    for start_match in IBAN_START_RE.finditer(text):
        start, cursor = start_match.start(), start_match.end()
        while cursor < len(text):
            character = text[cursor]
            if character.isalnum():
                cursor += 1
                continue
            if character == " ":
                candidate = text[start:cursor]
                if _passes_iban_checksum(candidate):
                    findings.append(Detection(start, cursor, "IBAN", 0.99))
                    break
                cursor += 1
                continue
            candidate = text[start:cursor]
            if _passes_iban_checksum(candidate):
                findings.append(Detection(start, cursor, "IBAN", 0.99))
            break
        else:
            candidate = text[start:cursor]
            if _passes_iban_checksum(candidate):
                findings.append(Detection(start, cursor, "IBAN", 0.99))
    return findings

