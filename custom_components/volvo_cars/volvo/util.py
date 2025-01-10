"""Volvo API utils."""

import asyncio
from collections.abc import Callable, Coroutine, Iterable, Mapping
from typing import Any, TypeVar

REDACTED = "**REDACTED**"
T = TypeVar("T")


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


async def async_retry(
    func: Callable[[], Coroutine[Any, Any, T]],
    ex_type: type[Exception] | tuple[type[Exception], ...],
    retries: int,
    wait: int,
) -> T:
    """Retries an asynchronous function on specified exceptions, with a delay between attempts."""

    # 0 retries = 1 attempt
    attempts = retries + 1

    if attempts <= 1:
        return await func()

    last_exception: Exception

    for attempt in range(attempts):
        try:
            return await func()
        except Exception as ex:
            if not isinstance(ex, ex_type):
                raise

            last_exception = ex
            if attempt < attempts - 1:
                await asyncio.sleep(wait)

    raise last_exception
