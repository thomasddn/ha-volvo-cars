"""Helper data."""

import base64
import logging
from typing import Any, cast

from aiohttp import ClientSession

_LOGGER = logging.getLogger(__name__)


class DataCache:
    """Access helper data."""

    _DATA: dict[str, Any] | None = None
    _ITERATIONS = 5
    _URL = "https://api.jsonsilo.com/public/f2deaae1-0228-4b32-b520-fcef31bd8838"

    @classmethod
    async def async_get_data(cls, client: ClientSession) -> dict[str, Any]:
        """Get the data."""

        if cls._DATA:
            return cls._DATA

        data = await cls._async_request_data(client)
        cls._deobfuscate_dict(data)
        cls._DATA = data

        return cls._DATA

    @classmethod
    def deobfuscate_str(cls, value: str, iterations: int = 1) -> str:
        """Deobfuscate a string."""
        b = bytes(f"{value}===", encoding="utf-8")
        for _ in range(iterations):
            b = base64.b64decode(b)

        return b.decode()

    @classmethod
    async def _async_request_data(cls, client: ClientSession) -> dict[str, Any]:
        _LOGGER.debug("Request [data]")
        async with client.get(
            cls._URL, headers={"Content-Type": "application/json"}
        ) as response:
            _LOGGER.debug("Request [data] status: %s", response.status)
            json = await response.json()
            data = cast(dict[str, Any], json)
            _LOGGER.debug("Request [data] body: %s", data)
            response.raise_for_status()

            return data

    @classmethod
    def _deobfuscate_dict(cls, data: dict[str, Any]) -> None:
        for key, value in data.items():
            if key in ("key", "value"):
                data[key] = cls.deobfuscate_str(value, cls._ITERATIONS)

            if isinstance(value, dict):
                cls._deobfuscate_dict(value)
