"""Short-lived reversible token map for one agent task."""

from __future__ import annotations

import secrets


class TokenVault:
    """Map original values to opaque typed tokens in memory only."""

    def __init__(self) -> None:
        self._value_to_token: dict[str, str] = {}
        self._token_to_value: dict[str, str] = {}

    def tokenize(self, value: str, entity_type: str) -> str:
        existing = self._value_to_token.get(value)
        if existing is not None:
            return existing

        token = f"[[{entity_type}:V{secrets.token_hex(5).upper()}]]"
        self._value_to_token[value] = token
        self._token_to_value[token] = value
        return token

    def restore_text(self, text: str) -> str:
        for token, value in self._token_to_value.items():
            text = text.replace(token, value)
        return text

    def mask_known_tokens(self, text: str) -> str:
        """Hide only this task's issued tokens from residual-PII pattern scans."""
        for token in self._token_to_value:
            text = text.replace(token, "\ufffc" * len(token))
        return text

    def restore(self, value: object) -> object:
        if isinstance(value, str):
            return self.restore_text(value)
        if isinstance(value, list):
            return [self.restore(item) for item in value]
        if isinstance(value, dict):
            return {key: self.restore(item) for key, item in value.items()}
        return value

    def contains_original_in(self, value: object) -> bool:
        """Return whether any protected original is still in a JSON value."""
        strings = _string_values(value)
        return any(original in text for original in self._value_to_token for text in strings)

    @property
    def token_count(self) -> int:
        return len(self._token_to_value)

    def clear(self) -> None:
        self._value_to_token.clear()
        self._token_to_value.clear()


def _string_values(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _string_values(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                yield key
            yield from _string_values(item)
