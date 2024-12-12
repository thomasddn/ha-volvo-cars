"""Volvo Cars Data Coordinator."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any

from requests import ConnectTimeout, HTTPError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_FRIENDLY_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_REFRESH_TOKEN, CONF_VCC_API_KEY, CONF_VIN, DOMAIN, MANUFACTURER
from .volvo.api import VolvoCarsApi
from .volvo.auth import VolvoCarsAuthApi
from .volvo.models import (
    VolvoApiException,
    VolvoAuthException,
    VolvoCarsApiBaseModel,
    VolvoCarsValueField,
    VolvoCarsVehicle,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class VolvoCarsData:
    """Data for Volvo Cars integration."""

    coordinator: VolvoCarsDataCoordinator


type VolvoCarsConfigEntry = ConfigEntry[VolvoCarsData]


class VolvoCarsDataCoordinator(DataUpdateCoordinator[dict[str, VolvoCarsApiBaseModel]]):
    """Volvo Cars Data Coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        auth_api: VolvoCarsAuthApi,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=entry.data.get(CONF_FRIENDLY_NAME) or entry.entry_id,
            update_interval=timedelta(minutes=2, seconds=15),
        )

        self.entry = entry
        self._auth_api = auth_api

        self.api = VolvoCarsApi(
            async_get_clientsession(hass),
            entry.data[CONF_VIN],
            entry.data[CONF_VCC_API_KEY],
            entry.data[CONF_ACCESS_TOKEN],
        )

        self.vehicle: VolvoCarsVehicle
        self.device: DeviceInfo
        self.commands: list[str] = []

        self.supports_location: bool = False
        self.supports_doors: bool = False
        self.supports_tyres: bool = False
        self.supports_warnings: bool = False
        self.supports_windows: bool = False
        self.unsupported_keys: list[str] = []

    async def _async_setup(self) -> None:
        """Set up the coordinator.

        This method is called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        vehicle = await self.api.async_get_vehicle_details()

        if vehicle is None:
            _LOGGER.error("Unable to retrieve vehicle details.")
            raise VolvoApiException("Unable to retrieve vehicle details.")

        self.vehicle = vehicle

        self.device = DeviceInfo(
            identifiers={(DOMAIN, self.vehicle.vin)},
            manufacturer=MANUFACTURER,
            model=f"{self.vehicle.description.model} ({self.vehicle.model_year})",
            name=f"{MANUFACTURER} {self.vehicle.description.model} {self.vehicle.fuel_type} {self.vehicle.model_year}",
            serial_number=self.vehicle.vin,
        )

        self.hass.config_entries.async_update_entry(
            self.entry,
            title=f"{MANUFACTURER} {self.vehicle.description.model} ({self.vehicle.vin})",
        )

        # Check supported commands
        commands = await self.api.async_get_commands()
        self.commands = [command.command for command in commands if command]

        # Check if location is supported
        location = await self.api.async_get_location()
        self.supports_location = location.get("location") is not None

        # Check if doors are supported
        doors = await self.api.async_get_doors_status()
        self.supports_doors = not self._is_all_unspecified(doors)

        # Check if tyres are supported
        tyres = await self.api.async_get_tyre_states()
        self.supports_tyres = not self._is_all_unspecified(tyres)

        # Check if warnings are supported
        warnings = await self.api.async_get_warnings()
        self.supports_warnings = not self._is_all_unspecified(warnings)

        # Check if windows are supported
        windows = await self.api.async_get_window_states()
        self.supports_windows = not self._is_all_unspecified(windows)

        # Keep track of unsupported keys
        self.unsupported_keys.append("location")
        self.unsupported_keys += [
            key
            for key, value in (doors | tyres | warnings | windows).items()
            if value is None or value.value == "UNSPECIFIED"
        ]

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        future: asyncio.Future[dict[str, VolvoCarsApiBaseModel | None]] = (
            asyncio.Future()
        )
        future.set_result({})

        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with asyncio.timeout(30):
                data: dict[str, VolvoCarsApiBaseModel | None] = {}

                results = await asyncio.gather(
                    self.api.async_get_api_status(),
                    self.api.async_get_availability_status(),
                    self.api.async_get_brakes_status(),
                    self.api.async_get_diagnostics(),
                    self.api.async_get_doors_status()
                    if self.supports_doors
                    else future,
                    self.api.async_get_engine_status(),
                    self.api.async_get_engine_warnings(),
                    self.api.async_get_fuel_status()
                    if self.vehicle.has_combustion_engine()
                    else future,
                    self.api.async_get_location() if self.supports_location else future,
                    self.api.async_get_odometer(),
                    self.api.async_get_recharge_status()
                    if self.vehicle.has_battery_engine()
                    else future,
                    self.api.async_get_statistics(),
                    self.api.async_get_tyre_states() if self.supports_tyres else future,
                    self.api.async_get_warnings() if self.supports_warnings else future,
                    self.api.async_get_window_states()
                    if self.supports_windows
                    else future,
                )

                for result in results:
                    data |= result

        except VolvoAuthException as ex:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            _LOGGER.exception("Authentication failed")
            raise ConfigEntryAuthFailed("Authentication failed.") from ex
        except (ConnectTimeout, HTTPError) as ex:
            _LOGGER.exception("Connection failed")
            raise UpdateFailed("Unable to connect to Volvo API.") from ex
        else:
            return data

    @callback
    async def async_refresh_token(self, _: datetime | None = None) -> None:
        """Refresh token."""
        try:
            result = await self._auth_api.async_refresh_token(
                self.entry.data.get(CONF_REFRESH_TOKEN, "")
            )
        except VolvoAuthException as ex:
            _LOGGER.exception("Authentication failed")
            raise ConfigEntryAuthFailed("Authentication failed.") from ex
        except (ConnectTimeout, HTTPError) as ex:
            _LOGGER.exception("Connection failed")
            raise ConfigEntryNotReady("Unable to connect to Volvo API.") from ex

        if result.token:
            data = self.entry.data | {
                CONF_ACCESS_TOKEN: result.token.access_token,
                CONF_REFRESH_TOKEN: result.token.refresh_token,
            }
            self.hass.config_entries.async_update_entry(self.entry, data=data)
            self.api.update_access_token(result.token.access_token)

    def _is_all_unspecified(self, items: dict[str, VolvoCarsValueField | None]) -> bool:
        return all(
            item is None or item.value == "UNSPECIFIED" for item in items.values()
        )
