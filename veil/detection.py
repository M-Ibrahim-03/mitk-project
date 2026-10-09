"""Small, explainable, pure-Python PII recognizers for the Veil MVP.

The MVP intentionally avoids compiled NLP extensions because the current
Windows execution environment blocks them. Person-name recognition is
context-aware and lexicon-based; it is less comprehensive than a full NER model.
"""

from __future__ import annotations

import re
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
    r"\d{3,5}[\s.-]\d{3,5}(?!\w)"
)
UNFORMATTED_PHONE_RE = re.compile(r"(?<!\w)\d{10,15}(?!\w)")

STUDENT_ID_RE = re.compile(r"\bSTU-DEMO-\d{5}\b", re.IGNORECASE)

NAME_CONTEXT_RE = re.compile(
    r"\b(?:my\s+name\s+is|name\s*(?:is|:|=)|contact(?:\s+name)?\s*(?:is|:|=)?|"
    r"customer(?:\s+name)?\s*(?:is|:|=)?|person\s*(?:is|:|=)|"
    r"user\s*(?:is|:|=)|to)\s+"
    r"(?P<name>[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?"
    r"(?:\s+[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?){1,2})\b",
    re.IGNORECASE,
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


class PIIDetector:
    """Find selected PII types using deterministic local patterns."""

    _priority = {
        "CUSTOM_SENSITIVE": 6,
        "EMAIL": 5,
        "STUDENT_ID": 4,
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
            (name, re.compile(rf"(?<!\w){re.escape(name)}(?!\w)", re.IGNORECASE))
            for name in names
        )
        self._custom_value_patterns = tuple(
            (value, re.compile(re.escape(value)))
            for value in dict.fromkeys(value for value in extra_values if value)
        )

    def detect(self, text: str, field_hint: str = "") -> list[Detection]:
        candidates: list[Detection] = []

        for _, pattern in self._custom_value_patterns:
            for match in pattern.finditer(text):
                candidates.append(
                    Detection(match.start(), match.end(), "CUSTOM_SENSITIVE", 1.0)
                )

        for match in EMAIL_RE.finditer(text):
            candidates.append(Detection(match.start(), match.end(), "EMAIL", 0.99))

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

