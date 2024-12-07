"""Volvo API utils."""

from collections.abc import Iterable, Mapping
from typing import Any

REDACTED = "**REDACTED**"


def redact_data(data: Mapping, to_redact: Iterable[Any]) -> dict:
    """Redact sensitive data in a dict."""

    redacted = {**data}

    for key, value in redacted.items():
        if value is None:
            continue
        if isinstance(value, str) and not value:
            continue
        if key in to_redact:
            redacted[key] = REDACTED
        elif isinstance(value, Mapping):
            redacted[key] = redact_data(value, to_redact)
        elif isinstance(value, list):
            redacted[key] = [redact_data(item, to_redact) for item in value]

    return redacted


def redact_url(url: str, vin: str) -> str:
    """Redact VIN from URL."""
    return url.replace(vin, REDACTED)
