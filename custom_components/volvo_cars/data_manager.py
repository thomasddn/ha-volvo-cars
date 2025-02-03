"""Data Manager."""

from __future__ import annotations

import base64
import contextlib
from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Any, cast

from aiohttp import ClientError, ClientSession

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.json import save_json
from homeassistant.helpers.storage import STORAGE_DIR
from homeassistant.util.hass_dict import HassKey

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

VOLVO_CARS_KEY: HassKey[ApiDataManager] = HassKey(DOMAIN)


@dataclass
class ApiData:
    """API data."""

    client_id: str
    auth_header: dict[str, str]
    default_headers: dict[str, str]


class ApiDataManager:
    """Access helper data."""

    _ITERATIONS = 5
    _URLS = [
        "https://api.npoint.io/6e4e6a3859a4e1c83964",
        "https://api.jsonsilo.com/public/f2deaae1-0228-4b32-b520-fcef31bd8838",
    ]

    _api_data: ApiData | None = None

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize class."""

        self._hass = hass
        self._path = hass.config.path(STORAGE_DIR, f"{DOMAIN}.data")

        self._cleanup_callbacks: list[CALLBACK_TYPE] = []
        self._cleanup_callbacks.append(
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.shutdown)
        )
        self._cleanup_callbacks.append(self._delete_data_file)

    @classmethod
    def get_or_create(cls, hass: HomeAssistant) -> ApiDataManager:
        """Get the manager and create if necessary."""
        if (manager := hass.data.get(VOLVO_CARS_KEY)) is None:
            manager = cls(hass)
            hass.data[VOLVO_CARS_KEY] = manager

        return manager

    def shutdown(self, event: Event | None = None) -> None:
        """Shutdown data manager."""
        _LOGGER.debug("Shutting down data manager")
        self._api_data = None

        while self._cleanup_callbacks:
            cleanup_callback = self._cleanup_callbacks.pop()
            cleanup_callback()

    async def async_get_api_data(self, client: ClientSession) -> ApiData:
        """Get API data."""

        if self._api_data:
            return self._api_data

        data = await self._async_get_data(client)

        a = data["h"]["a"]
        p = data["h"]["p"]
        a_value: str = a["value"]

        client_id = self._deobfuscate_str(a_value.split(" ")[1]).split(":")[0]

        self._api_data = ApiData(
            client_id=client_id,
            auth_header={a["key"]: a_value},
            default_headers={p["key"]: p["value"]},
        )
        return self._api_data

    async def _async_get_data(self, client: ClientSession) -> dict[str, Any]:
        data = {}

        for url in self._URLS:
            with contextlib.suppress(ClientError, TimeoutError):
                data = await self._async_request_data(url, client)

                if data:
                    break

        if data:
            _LOGGER.debug("Saving data to local file %s", self._path)
            save_json(self._path, data)
        else:
            _LOGGER.debug("Loading data from remote failed")
            path = Path(self._path)

            if path.is_file():
                _LOGGER.debug("Reading data from local file %s", self._path)
                with Path.open(path) as file:
                    data = json.load(file)

            raise HomeAssistantError("Unable to load data")

        self._deobfuscate_dict(data)
        return data

    async def _async_request_data(
        self, url: str, client: ClientSession
    ) -> dict[str, Any]:
        _LOGGER.debug("Request [data]: %s", url)

        try:
            async with client.get(
                url, headers={"Content-Type": "application/json"}
            ) as response:
                _LOGGER.debug("Request [data] status: %s", response.status)
                json = await response.json()
                data = cast(dict[str, Any], json)
                _LOGGER.debug("Request [data] body: %s", data)
                response.raise_for_status()

                return data
        except (ClientError, TimeoutError) as ex:
            _LOGGER.debug("Request [data] error: %s", ex.__class__.__name__)
            raise

    def _deobfuscate_dict(self, data: dict[str, Any]) -> None:
        for key, value in data.items():
            if key in ("key", "value"):
                data[key] = self._deobfuscate_str(value, self._ITERATIONS)

            if isinstance(value, dict):
                self._deobfuscate_dict(value)

    def _deobfuscate_str(self, value: str, iterations: int = 1) -> str:
        b = bytes(f"{value}===", encoding="utf-8")
        for _ in range(iterations):
            b = base64.b64decode(b)

        return b.decode()

    def _delete_data_file(self) -> None:
        Path(self._path).unlink(missing_ok=True)
